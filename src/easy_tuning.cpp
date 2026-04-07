#include <cstdint>
#include <list>
#include <string>
#include <unordered_map>
#include <vector>
#include <algorithm>
#include <limits>
#include <cstdio>
#include <cmath>
#include <iostream>

#include <batprotocol.hpp>
#include <intervalset.hpp>
#include "batsim_edc.h"

using namespace batprotocol;



// All available sorting policies for the queues
enum class QueuePolicy {
    FCFS,  // First-Come-First-Served : oldest job first
    LCFS,  // Last-Come-First-Served  : newest job first
    SPF,   // Shortest-Processing-First : shortest walltime first
    LPF,   // Longest-Processing-First  : longest walltime first
    SQF,   // Smallest-resource-requirement-First : fewest hosts first
    LQF,   // Largest-resource-requirement-First  : most hosts first
    EXP    // Expansion Factor : (wait + walltime) / walltime
};

// A job waiting in the queue
struct SchedJob {
    std::string job_id;
    uint32_t    nb_hosts      = 0;
    double      walltime      = 0.0;   // required for EASY backfilling
    double      submit_time   = 0.0;   // when the job was submitted
    uint64_t    arrival_order = 0;     // used to break ties between jobs with same submit_time
};

// Information about a currently running job
struct RunningInfo {
    IntervalSet alloc;                 // which hosts it is using
    double      expected_end = 0.0;   // estimated finish time (now + walltime)
};

// Lightweight copy of a job used only for sorting
// Safe to use even if the original list is modified
struct JobView {
    std::string job_id;
    uint32_t    nb_hosts      = 0;
    double      walltime      = 0.0;
    double      submit_time   = 0.0;
    uint64_t    arrival_order = 0;
};



static MessageBuilder * mb            = nullptr;
static bool             format_binary = true;

// Waiting queue (list for fast removal in the middle)
static std::list<SchedJob> jobs;

// Currently running jobs (dictionary : job_id -> RunningInfo)
static std::unordered_map<std::string, RunningInfo> running_alloc;

// Currently free hosts on the platform
static IntervalSet free_hosts;

static uint32_t platform_nb_hosts  = 0;
static uint64_t next_arrival_order = 0;

// Active sorting policies
static QueuePolicy primary_policy  = QueuePolicy::FCFS;
static QueuePolicy backfill_policy = QueuePolicy::FCFS;


// Higher score = job has waited long relative to its size
static double compute_exp_score(double now, const JobView & job) {
    double wait = now - job.submit_time;
    if (job.walltime <= 0.0) return 0.0;
    return (wait + job.walltime) / job.walltime;
}


// Returns true if job A should come before job B
static bool compare_jobs(const JobView & a, const JobView & b,
                          QueuePolicy policy, double now)
{
    switch (policy) {

        case QueuePolicy::FCFS:
            // Oldest submit_time first
            return (a.submit_time != b.submit_time)
                   ? a.submit_time < b.submit_time
                   : a.arrival_order < b.arrival_order;

        case QueuePolicy::LCFS:
            // Newest submit_time first
            return (a.submit_time != b.submit_time)
                   ? a.submit_time > b.submit_time
                   : a.arrival_order < b.arrival_order;

        case QueuePolicy::SPF:
            // Shortest walltime first
            return (a.walltime != b.walltime)
                   ? a.walltime < b.walltime
                   : a.arrival_order < b.arrival_order;

        case QueuePolicy::LPF:
            // Longest walltime first
            return (a.walltime != b.walltime)
                   ? a.walltime > b.walltime
                   : a.arrival_order < b.arrival_order;

        case QueuePolicy::SQF:
            // Fewest hosts requested first
            return (a.nb_hosts != b.nb_hosts)
                   ? a.nb_hosts < b.nb_hosts
                   : a.arrival_order < b.arrival_order;

        case QueuePolicy::LQF:
            // Most hosts requested first
            return (a.nb_hosts != b.nb_hosts)
                   ? a.nb_hosts > b.nb_hosts
                   : a.arrival_order < b.arrival_order;

        case QueuePolicy::EXP: {
            double sa = compute_exp_score(now, a);
            double sb = compute_exp_score(now, b);
            return (sa != sb)
                   ? sa > sb
                   : a.arrival_order < b.arrival_order;
        }

        default:
            return (a.submit_time != b.submit_time)
                   ? a.submit_time < b.submit_time
                   : a.arrival_order < b.arrival_order;
    }
}


// Returns the earliest time when nb_hosts_needed hosts will be free
static double compute_reservation_time(double now, uint32_t nb_hosts_needed) {

    if (nb_hosts_needed == 0) return now;
    if (free_hosts.size() >= nb_hosts_needed) return now;

    struct EndEvent { double t; IntervalSet alloc; };
    std::vector<EndEvent> ends;
    ends.reserve(running_alloc.size());

    for (const auto & kv : running_alloc)
        ends.push_back({ kv.second.expected_end, kv.second.alloc });

    if (ends.empty()) return std::numeric_limits<double>::infinity();

    std::sort(ends.begin(), ends.end(),
        [](const EndEvent & a, const EndEvent & b){ return a.t < b.t; });

    IntervalSet tmp_free = free_hosts;
    for (const auto & e : ends) {
        tmp_free = tmp_free + e.alloc;
        if (tmp_free.size() >= nb_hosts_needed)
            return e.t;
    }

    return std::numeric_limits<double>::infinity();
}


// Allocates hosts, notifies Batsim, saves running info
static void start_job(double now, const SchedJob & job) {
    IntervalSet alloc = free_hosts.left(job.nb_hosts);
    free_hosts = free_hosts - alloc;

    std::string host_str = alloc.to_string_hyphen();
    std::replace(host_str.begin(), host_str.end(), ',', ' ');

    mb->add_execute_job(job.job_id, host_str);

    RunningInfo info;
    info.alloc = alloc;
    info.expected_end = now + job.walltime;

    running_alloc.emplace(job.job_id, std::move(info));

    std::cout << "[LAUNCH] " << job.job_id
              << " | hosts=" << job.nb_hosts
              << " | alloc=" << host_str
              << " | expected_end=" << (now + job.walltime) << "\n";
}
// STEP 7 : EASY Backfilling algorithm
static void schedule_easy(double now) {

    if (jobs.empty()) return;

    std::vector<JobView> primary_view;
    primary_view.reserve(jobs.size());

    for (const auto & j : jobs)
        primary_view.push_back({ j.job_id, j.nb_hosts, j.walltime,
                                  j.submit_time, j.arrival_order });

    std::sort(primary_view.begin(), primary_view.end(),
        [now](const JobView & a, const JobView & b){
            return compare_jobs(a, b, primary_policy, now);
        });

    std::string blocked_head_id;
    bool        found_blocked = false;

    for (const auto & view : primary_view) {

        auto it = std::find_if(jobs.begin(), jobs.end(),
            [&](const SchedJob & j){ return j.job_id == view.job_id; });

        if (it == jobs.end()) continue;

        if (it->nb_hosts <= free_hosts.size()) {
            start_job(now, *it);
            jobs.erase(it);
        } else {
            blocked_head_id = it->job_id;
            found_blocked   = true;
            break;
        }
    }

    if (jobs.empty() || !found_blocked) return;

    auto head_it = std::find_if(jobs.begin(), jobs.end(),
        [&](const SchedJob & j){ return j.job_id == blocked_head_id; });

    if (head_it == jobs.end()) return;

    double reservation_time = compute_reservation_time(now, head_it->nb_hosts);

    if (!std::isfinite(reservation_time)) {
        std::cout << "[REJECT] " << blocked_head_id << "\n";
        mb->add_reject_job(blocked_head_id);
        jobs.erase(head_it);
        return;
    }

    std::cout << "[RESERVE] " << blocked_head_id
              << " reserved at t=" << reservation_time << "\n";

    std::vector<JobView> backfill_view;

    for (const auto & j : jobs) {
        if (j.job_id != blocked_head_id)
            backfill_view.push_back({ j.job_id, j.nb_hosts, j.walltime,
                                       j.submit_time, j.arrival_order });
    }

    std::sort(backfill_view.begin(), backfill_view.end(),
        [now](const JobView & a, const JobView & b){
            return compare_jobs(a, b, backfill_policy, now);
        });

    for (const auto & view : backfill_view) {

        auto it = std::find_if(jobs.begin(), jobs.end(),
            [&](const SchedJob & j){ return j.job_id == view.job_id; });

        if (it == jobs.end()) continue;

        bool fits_resources = (it->nb_hosts <= free_hosts.size());
        bool finishes_in_time =
            (it->walltime > 0.0) && ((now + it->walltime) <= reservation_time);

        if (fits_resources && finishes_in_time) {
            std::cout << "[BACKFILL] " << it->job_id << "\n";
            start_job(now, *it);
            jobs.erase(it);
        }
    }
}


// ===================== I changed this =====================
// Had to change those because otherwise the function names were not recognised by batsim
// no pb with the external ones! only those in the edc file. 

extern "C" uint8_t batsim_edc_init(
    const uint8_t * data,
    uint32_t size,
    uint32_t * flags,
    uint8_t ** reply_data,
    uint32_t * reply_size)
{
    (void)data;
    (void)size;

    if (flags == nullptr || reply_data == nullptr || reply_size == nullptr) {
        std::printf("Invalid init pointers\n");
        return 1;
    }

    *flags = BATSIM_EDC_FORMAT_BINARY;
    format_binary = true;

    mb = new MessageBuilder(!format_binary);

    mb->clear(0.0);
    mb->add_edc_hello("easy_scheduler", "1.0.0");
    mb->finish_message(0.0);

    serialize_message(*mb, !format_binary,
        const_cast<const uint8_t **>(reply_data), reply_size);

    return 0;
}

extern "C" uint8_t batsim_edc_deinit() {
    delete mb;
    mb = nullptr;
    jobs.clear();
    running_alloc.clear();
    platform_nb_hosts  = 0;
    next_arrival_order = 0;
    return 0;
}

extern "C" uint8_t batsim_edc_take_decisions(
    const uint8_t *  what_happened,
    uint32_t         what_happened_size,
    uint8_t **       decisions,
    uint32_t *       decisions_size)
{
    (void) what_happened_size;

    auto * parsed = deserialize_message(*mb, !format_binary, what_happened);
    double now    = parsed->now();
    mb->clear(now);

    auto nb_events = parsed->events()->size();
    for (unsigned int i = 0; i < nb_events; ++i) {
        auto event = (*parsed->events())[i];

        switch (event->event_type()) {

            case fb::Event_SimulationBeginsEvent: {
                auto simu = event->event_as_SimulationBeginsEvent();
                platform_nb_hosts = simu->computation_host_number();

                if (platform_nb_hosts > 0)
                    free_hosts = IntervalSet(
                        IntervalSet::ClosedInterval(0, platform_nb_hosts - 1));
            } break;

            case fb::Event_JobSubmittedEvent: {
                auto parsed_job = event->event_as_JobSubmittedEvent();

                SchedJob job;
                job.job_id        = parsed_job->job_id()->str();
                job.nb_hosts      = parsed_job->job()->resource_request();
                job.walltime      = parsed_job->job()->walltime().value_or(-1.0);
                job.submit_time   = now;
                job.arrival_order = next_arrival_order++;

                if (job.nb_hosts <= platform_nb_hosts)
                    jobs.push_back(std::move(job));
            } break;

            case fb::Event_JobCompletedEvent: {
                auto jc  = event->event_as_JobCompletedEvent();
                auto jid = jc->job_id()->str();

                auto it = running_alloc.find(jid);
                if (it != running_alloc.end()) {
                    free_hosts = free_hosts + it->second.alloc;
                    running_alloc.erase(it);
                }
            } break;

            default: break;
        }
    }

    schedule_easy(now);

    mb->finish_message(now);
    serialize_message(*mb, !format_binary,
        const_cast<const uint8_t **>(decisions), decisions_size);

    return 0;
}