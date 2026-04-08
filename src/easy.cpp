
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
// Example: 20.0 * 3600.0  →  20-hour threshold as used in the paper.
static double threshold_seconds = 0.0;


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
            // Highest expansion factor first (most urgent job)
            double sa = compute_exp_score(now, a);
            double sb = compute_exp_score(now, b);
            return (sa != sb)
                   ? sa > sb
                   : a.arrival_order < b.arrival_order;
        }

        default:
            // Fallback to FCFS
            return (a.submit_time != b.submit_time)
                   ? a.submit_time < b.submit_time
                   : a.arrival_order < b.arrival_order;
    }
}


// Returns the earliest time when nb_hosts_needed hosts will be free
static double compute_reservation_time(double now, uint32_t nb_hosts_needed) {

    // Job needs no hosts -> it can start right now
    if (nb_hosts_needed == 0) return now;

    // Already enough free hosts -> it can start right now
    if (free_hosts.size() >= nb_hosts_needed) return now;

    // Collect all predicted job completions
    struct EndEvent { double t; IntervalSet alloc; };
    std::vector<EndEvent> ends;
    ends.reserve(running_alloc.size());

    for (const auto & kv : running_alloc)
        ends.push_back({ kv.second.expected_end, kv.second.alloc });

    // No running jobs but not enough free hosts -> impossible
    if (ends.empty()) return std::numeric_limits<double>::infinity();

    // Sort completions from earliest to latest
    std::sort(ends.begin(), ends.end(),
        [](const EndEvent & a, const EndEvent & b){ return a.t < b.t; });

    // Simulate progressive host liberation
    IntervalSet tmp_free = free_hosts;
    for (const auto & e : ends) {
        tmp_free = tmp_free + e.alloc;        // hosts freed at time e.t
        if (tmp_free.size() >= nb_hosts_needed)
            return e.t;                        // enough hosts -> return this time
    }

    // Even after all jobs finish, not enough hosts -> job can never run
    return std::numeric_limits<double>::infinity();
}


// Allocates hosts, notifies Batsim, saves running info
static void start_job(double now, const SchedJob & job) {

    // Take the first nb_hosts free hosts
    IntervalSet alloc = free_hosts.left(job.nb_hosts);

    // Remove them from the free hosts pool
    free_hosts = free_hosts - alloc;

    // Tell Batsim to execute the job on these hosts
    mb->add_execute_job(job.job_id, alloc.to_string_hyphen());

    // Save running info for later (when the job completes)
    RunningInfo info;
    info.alloc        = alloc;
    info.expected_end = now + job.walltime;
    running_alloc.emplace(job.job_id, std::move(info));

    std::cout << "[LAUNCH] " << job.job_id
              << " | hosts=" << job.nb_hosts
              << " | expected_end=" << info.expected_end << "\n";
}


// STEP 7 : EASY Backfilling algorithm
static void schedule_easy(double now) {

    if (jobs.empty()) return;

    //  Step A : build sorted primary view 
    std::vector<JobView> primary_view;
    primary_view.reserve(jobs.size());

    for (const auto & j : jobs)
        primary_view.push_back({ j.job_id, j.nb_hosts, j.walltime,
                                  j.submit_time, j.arrival_order });

     std::sort(primary_view.begin(), primary_view.end(),
        [now](const JobView & a, const JobView & b){
            return compare_jobs(a, b, primary_policy, now);
        });

    // Jobs that have waited longer than threshold_seconds are promoted
    // to the head of the primary queue, ordered by FCFS among themselves.
    // When threshold_seconds <= 0 this block is entirely skipped.
    if (threshold_seconds > 0.0) {
        // Separate jobs into "over threshold" and "under threshold"
        std::stable_partition(primary_view.begin(), primary_view.end(),
            [now](const JobView & j) {
                return (now - j.submit_time) > threshold_seconds;
            });

        auto promoted_end = std::find_if(primary_view.begin(), primary_view.end(),
            [now](const JobView & j) {
                return (now - j.submit_time) <= threshold_seconds;
            });

        std::stable_sort(primary_view.begin(), promoted_end,
            [](const JobView & a, const JobView & b) {
                return (a.submit_time != b.submit_time)
                       ? a.submit_time < b.submit_time
                       : a.arrival_order < b.arrival_order;
            });
    }

    //  Step B : launch jobs that fit immediately
    std::string blocked_head_id;
    bool        found_blocked = false;

    for (const auto & view : primary_view) {

        // Find the real job in the list by its id
        auto it = std::find_if(jobs.begin(), jobs.end(),
            [&](const SchedJob & j){ return j.job_id == view.job_id; });

        if (it == jobs.end()) continue;  // already launched, skip

        if (it->nb_hosts <= free_hosts.size()) {
            // Job fits -> launch it and remove from queue
            start_job(now, *it);
            jobs.erase(it);
        } else {
            // First job that does not fit -> becomes the priority head
            blocked_head_id = it->job_id;
            found_blocked   = true;
            break;
        }
    }

    // No blocked job -> nothing more to do
    if (jobs.empty() || !found_blocked) return;

    // Step C : compute reservation time for the blocked head 
    auto head_it = std::find_if(jobs.begin(), jobs.end(),
        [&](const SchedJob & j){ return j.job_id == blocked_head_id; });

    if (head_it == jobs.end()) return;

    double reservation_time = compute_reservation_time(now, head_it->nb_hosts);

    if (!std::isfinite(reservation_time)) {
        // Job requests more hosts than the platform has -> reject it
        std::cout << "[REJECT] " << blocked_head_id
                  << " — cannot ever run on this platform.\n";
        mb->add_reject_job(blocked_head_id);
        jobs.erase(head_it);
        return;
    }

    std::cout << "[RESERVE] " << blocked_head_id
              << " reserved at t=" << reservation_time << "\n";

    //  Step D : build sorted backfill candidate list 
    std::vector<JobView> backfill_view;

    for (const auto & j : jobs) {
        // Exclude the priority head -> it waits for its reservation
        if (j.job_id != blocked_head_id)
            backfill_view.push_back({ j.job_id, j.nb_hosts, j.walltime,
                                       j.submit_time, j.arrival_order });
    }

    std::sort(backfill_view.begin(), backfill_view.end(),
        [now](const JobView & a, const JobView & b){
            return compare_jobs(a, b, backfill_policy, now);
        });

    // Step E : backfill compatible jobs 
    for (const auto & view : backfill_view) {

        auto it = std::find_if(jobs.begin(), jobs.end(),
            [&](const SchedJob & j){ return j.job_id == view.job_id; });

        if (it == jobs.end()) continue;  // already launched, skip

        // Condition 1 : job fits in currently free hosts
        bool fits_resources = (it->nb_hosts <= free_hosts.size());

        // Condition 2 : job finishes before the priority head needs its hosts
        bool finishes_in_time =
            (it->walltime > 0.0) && ((now + it->walltime) <= reservation_time);

        if (fits_resources && finishes_in_time) {
            std::cout << "[BACKFILL] " << it->job_id << "\n";
            start_job(now, *it);
            jobs.erase(it);
        }
    }
}


// Batsim EDC interface

// Called once at the start -> initialize the message builder
uint8_t batsim_edc_init(const uint8_t * data, uint32_t size, uint32_t flags) {

    format_binary = ((flags & BATSIM_EDC_FORMAT_BINARY) != 0);

    if ((flags & (BATSIM_EDC_FORMAT_BINARY | BATSIM_EDC_FORMAT_JSON)) != flags) {
        std::printf("Unknown flags, cannot initialize.\n");
        return 1;  // error
    }

    mb = new MessageBuilder(!format_binary);
    (void) data;
    (void) size;
    return 0;  // success
}

// Called once at the end -> free all memory
uint8_t batsim_edc_deinit() {
    delete mb;
    mb = nullptr;
    jobs.clear();
    running_alloc.clear();
    platform_nb_hosts  = 0;
    next_arrival_order = 0;
    return 0;
}

// Called at every event during the simulation
uint8_t batsim_edc_take_decisions(
    const uint8_t *  what_happened,
    uint32_t         what_happened_size,
    uint8_t **       decisions,
    uint32_t *       decisions_size)
{
    (void) what_happened_size;

    // Decode the message received from Batsim
    auto * parsed = deserialize_message(*mb, !format_binary, what_happened);
    double now    = parsed->now();
    mb->clear(now);

    // Process all events in the message
    auto nb_events = parsed->events()->size();
    for (unsigned int i = 0; i < nb_events; ++i) {
        auto event = (*parsed->events())[i];

        std::printf("[EVENT] %s\n",
            batprotocol::fb::EnumNamesEvent()[event->event_type()]);

        switch (event->event_type()) {

            // Batsim says hello -> we reply with our name and version
            case fb::Event_EDCHelloEvent: {
                mb->add_edc_hello("easy_scheduler", "1.0.0");
            } break;

            // Simulation starts -> initialize free hosts
            case fb::Event_SimulationBeginsEvent: {
                auto simu         = event->event_as_SimulationBeginsEvent();
                platform_nb_hosts = simu->computation_host_number();
                

                if (platform_nb_hosts > 0)
                    free_hosts = IntervalSet(
                        IntervalSet::ClosedInterval(0, platform_nb_hosts - 1));

                std::cout << "[INIT] Platform has "
                          << platform_nb_hosts << " hosts\n";
            } break;

            // A new job arrives -> add it to the waiting queue
            case fb::Event_JobSubmittedEvent: {
                auto parsed_job = event->event_as_JobSubmittedEvent();

                SchedJob job;
                job.job_id        = parsed_job->job_id()->str();
                job.nb_hosts      = parsed_job->job()->resource_request();
                job.walltime = parsed_job->job()->walltime();
                job.submit_time   = now;
                job.arrival_order = next_arrival_order++;

                std::cout << "[SUBMIT] " << job.job_id
                          << " | hosts=" << job.nb_hosts
                          << " | walltime=" << job.walltime << "\n";

                if (job.nb_hosts > platform_nb_hosts) {
                    // Job requests more hosts than the platform has -> reject immediately
                    std::cout << "[REJECT] " << job.job_id
                              << " — requests too many hosts.\n";
                    mb->add_reject_job(job.job_id);
                } else {
                    jobs.push_back(std::move(job));
                }
            } break;

            // A job finished -> free its hosts
            case fb::Event_JobCompletedEvent: {
                auto jc  = event->event_as_JobCompletedEvent();
                auto jid = jc->job_id()->str();

                auto it = running_alloc.find(jid);
                if (it != running_alloc.end()) {
                    // Give back the hosts to the free pool
                    free_hosts = free_hosts + it->second.alloc;
                    running_alloc.erase(it);

                    std::cout << "[COMPLETE] " << jid
                              << " | free hosts=" << free_hosts.size() << "\n";
                }
            } break;

            default: break;
        }
    }

    // Make scheduling decisions
    schedule_easy(now);

    // Send decisions to Batsim
    mb->finish_message(now);
    serialize_message(*mb, !format_binary,
        const_cast<const uint8_t **>(decisions), decisions_size);
    return 0;
}