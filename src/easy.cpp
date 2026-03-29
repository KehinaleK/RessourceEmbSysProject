// easy.cpp - EASY backfilling for Batsim EDC (batprotocol + intervalset)

#include <cstdint>
#include <list>
#include <string>
#include <unordered_map>
#include <vector>
#include <algorithm>
#include <limits>
#include <cstdio>
#include <cmath>

#include <batprotocol.hpp>
#include <intervalset.hpp>

#include "batsim_edc.h"

using namespace batprotocol;

enum class QueuePolicy {
  FCFS,  // First-Come-First-Served
  LCFS,  // Last-Come-First-Served
  SPF,   // Shortest-Processing-First (walltime)
  LPF,   // Longest-Processing-First (walltime)
  SQF,   // Smallest-Resource-Requirement-First (nb_hosts)
  LQF,   // Largest-Resource-Requirement-First (nb_hosts)
  EXP    // Expansion Factor: (wait + walltime) / walltime
};

//This structure stores the information needed for each waiting job.
struct SchedJob {
  std::string job_id;
  uint32_t nb_hosts = 0;
  double walltime = 0.0;      // REQUIRED for EASY reservation/backfilling
  double submit_time = 0.0;   // When the job was submitted
  uint64_t arrival_order = 0; // Global submission order (used for tie-breaking)
};

//This structure stores information about running jobs.
struct RunningInfo {
  IntervalSet alloc;
  double expected_end = 0.0; // now + walltime at dispatch time
};

// Safe view of a job used for ordering and scheduling (copy, not reference)
struct JobView {
  std::string job_id;
  uint32_t nb_hosts = 0;
  double walltime = 0.0;
  double submit_time = 0.0;
  uint64_t arrival_order = 0;
};

MessageBuilder * mb = nullptr;
bool format_binary = true;

//Global scheduler state - jobs remain here until they are either started or rejected
std::list<SchedJob> jobs; // Waiting queue
IntervalSet free_hosts;

//running jobs
std::unordered_map<std::string, RunningInfo> running_alloc;
uint32_t platform_nb_hosts = 0;

// Policy-aware scheduler parameters
static QueuePolicy primary_policy = QueuePolicy::FCFS;
static QueuePolicy backfill_policy = QueuePolicy::FCFS;
static uint64_t next_arrival_order = 0;

static double INF_TIME() {
  return std::numeric_limits<double>::infinity();
}

static double compute_reservation_time_for_head(double now, uint32_t head_req) {
  // Earliest time when head_req hosts will be available, assuming running jobs end at expected_end.
  // This is a simple time-sweep on predicted completions.

  if (head_req == 0) return now;

  // If already enough free: reservation is now.
  if (free_hosts.size() >= head_req) return now;

  // Collect running job completion events: (end_time, alloc)
  struct EndEvent { double t; IntervalSet alloc; };
  std::vector<EndEvent> ends;
  ends.reserve(running_alloc.size());

  for (const auto & kv : running_alloc) {
    ends.push_back({kv.second.expected_end, kv.second.alloc});
  }

  if (ends.empty()) {
    // Nothing running, but not enough free -> inconsistent state; treat as "never".
    return INF_TIME();
  }

  std::sort(ends.begin(), ends.end(), [](const EndEvent & a, const EndEvent & b) {
    return a.t < b.t;
  });

  IntervalSet tmp_free = free_hosts;
  for (const auto & e : ends) {
    tmp_free = tmp_free + e.alloc; // union back hosts freed at time e.t
    if (tmp_free.size() >= head_req) {
      return e.t;
    }
  }

  // Even after all predicted ends, not enough. Shouldn't happen unless platform_nb_hosts < head_req.
  return INF_TIME();
}

template <typename JobType>
static double compute_exp_score(double now, const JobType & job) {
  // Expansion Factor (EXP): (wait_time + walltime) / walltime
  // Higher score = job has waited longer relative to its size (more priority)
  double wait = now - job.submit_time;
  if (job.walltime <= 0.0) return 0.0;
  return (wait + job.walltime) / job.walltime;
}

static bool compare_jobs_by_policy(const JobView & a, const JobView & b, 
                                    QueuePolicy policy, double now) {
  // Comparator for JobView objects (safe copies, not references to list elements)
  // Returns true if 'a' should come before 'b' in the queue
  // Tie-breaker: always consistent and stable via arrival_order < arrival_order
  
  switch (policy) {
    case QueuePolicy::FCFS:
      // Earlier submit_time comes first
      if (a.submit_time != b.submit_time) {
        return a.submit_time < b.submit_time;
      }
      return a.arrival_order < b.arrival_order;
      
    case QueuePolicy::LCFS:
      // Later submit_time comes first (reverse of FCFS)
      if (a.submit_time != b.submit_time) {
        return a.submit_time > b.submit_time;
      }
      return a.arrival_order < b.arrival_order;
      
    case QueuePolicy::SPF:
      // Shorter walltime comes first
      if (a.walltime != b.walltime) {
        return a.walltime < b.walltime;
      }
      return a.arrival_order < b.arrival_order;
      
    case QueuePolicy::LPF:
      // Longer walltime comes first (reverse of SPF)
      if (a.walltime != b.walltime) {
        return a.walltime > b.walltime;
      }
      return a.arrival_order < b.arrival_order;
      
    case QueuePolicy::SQF:
      // Smaller resource requirement (fewer hosts) comes first
      if (a.nb_hosts != b.nb_hosts) {
        return a.nb_hosts < b.nb_hosts;
      }
      return a.arrival_order < b.arrival_order;
      
    case QueuePolicy::LQF:
      // Larger resource requirement (more hosts) comes first (reverse of SQF)
      if (a.nb_hosts != b.nb_hosts) {
        return a.nb_hosts > b.nb_hosts;
      }
      return a.arrival_order < b.arrival_order;
      
    case QueuePolicy::EXP:
      // Higher Expansion Factor comes first (older/larger jobs have priority)
      {
        double score_a = compute_exp_score(now, a);
        double score_b = compute_exp_score(now, b);
        if (score_a != score_b) {
          return score_a > score_b;
        }
        return a.arrival_order < b.arrival_order;
      }
      
    default:
      // Fallback to FCFS
      if (a.submit_time != b.submit_time) {
        return a.submit_time < b.submit_time;
      }
      return a.arrival_order < b.arrival_order;
  }
}

static void start_job(double now, const SchedJob & job) {
  IntervalSet alloc = free_hosts.left(job.nb_hosts);
  free_hosts = free_hosts - alloc;

  mb->add_execute_job(job.job_id, alloc.to_string_hyphen());

  RunningInfo info;
  info.alloc = alloc;
  info.expected_end = now + job.walltime;

  running_alloc.emplace(job.job_id, std::move(info));
}

static void schedule_easy(double now) {
  if (jobs.empty()) return;

  // ========== STEP A: Build primary-policy ordered view of waiting jobs ==========
  std::vector<JobView> primary_queue;
  for (const auto & job : jobs) {
    primary_queue.push_back({
      job.job_id,
      job.nb_hosts,
      job.walltime,
      job.submit_time,
      job.arrival_order
    });
  }

  // Sort primary queue according to primary_policy
  std::sort(primary_queue.begin(), primary_queue.end(),
    [now](const JobView & a, const JobView & b) {
      return compare_jobs_by_policy(a, b, primary_policy, now);
    });

  // ========== STEP B: Dispatch jobs from primary queue while they fit immediately ==========
  std::string reserved_head_id;
  bool found_blocked_head = false;

  for (const auto & view : primary_queue) {
    // Find job in list by ID
    auto job_it = std::find_if(jobs.begin(), jobs.end(),
      [&](const SchedJob & j) { return j.job_id == view.job_id; });
    
    if (job_it == jobs.end()) {
      // Job already started; skip it
      continue;
    }

    const SchedJob & job = *job_it;
    
    if (job.nb_hosts <= free_hosts.size()) {
      // Job fits - start it immediately
      start_job(now, job);
      jobs.erase(job_it);
    } else {
      // First job that doesn't fit becomes the reserved head
      reserved_head_id = job.job_id;
      found_blocked_head = true;
      break;
    }
  }

  if (jobs.empty()) return;

  if (!found_blocked_head) {
    // All jobs fit immediately (shouldn't happen given we broke on non-fit, but safety check)
    return;
  }

  // ========== STEP C: Compute reservation time for the blocked head job ==========
  auto head_it = std::find_if(jobs.begin(), jobs.end(),
    [&](const SchedJob & j) { return j.job_id == reserved_head_id; });
  
  if (head_it == jobs.end()) {
    // Head disappeared (shouldn't happen)
    return;
  }

  double reservation_time = compute_reservation_time_for_head(now, head_it->nb_hosts);
  
  if (!std::isfinite(reservation_time)) {
    // Can't ever start reserved head, so reject it
    mb->add_reject_job(reserved_head_id);
    jobs.erase(head_it);
    return;
  }

  // ========== STEP D: Build backfill-policy ordered view (excluding reserved head) ==========
  std::vector<JobView> backfill_queue;
  for (const auto & job : jobs) {
    if (job.job_id != reserved_head_id) {
      backfill_queue.push_back({
        job.job_id,
        job.nb_hosts,
        job.walltime,
        job.submit_time,
        job.arrival_order
      });
    }
  }

  // Sort backfill queue according to backfill_policy
  std::sort(backfill_queue.begin(), backfill_queue.end(),
    [now](const JobView & a, const JobView & b) {
      return compare_jobs_by_policy(a, b, backfill_policy, now);
    });

  // ========== STEP E: Backfill jobs that fit and finish before reservation_time ==========
  for (const auto & view : backfill_queue) {
    // Find job in list by ID
    auto job_it = std::find_if(jobs.begin(), jobs.end(),
      [&](const SchedJob & j) { return j.job_id == view.job_id; });
    
    if (job_it == jobs.end()) {
      // Job already started; skip it
      continue;
    }

    const SchedJob & job = *job_it;
    
    // Check backfill conditions:
    // 1. walltime must be valid
    // 2. job must fit in current free hosts
    // 3. job must finish before reservation time
    if (job.walltime > 0.0 &&
        job.nb_hosts <= free_hosts.size() &&
        (now + job.walltime) <= reservation_time) {
      start_job(now, job);
      jobs.erase(job_it);
    }
  }
}

uint8_t batsim_edc_init(const uint8_t * data, uint32_t size, uint32_t flags) {
  format_binary = ((flags & BATSIM_EDC_FORMAT_BINARY) != 0);
  if ((flags & (BATSIM_EDC_FORMAT_BINARY | BATSIM_EDC_FORMAT_JSON)) != flags) {
    std::printf("Unknown flags used, cannot initialize myself.\n");
    return 1;
  }

  mb = new MessageBuilder(!format_binary);

  (void) data;
  (void) size;
  return 0;
}

uint8_t batsim_edc_deinit() {
  delete mb;
  mb = nullptr;

  jobs.clear();
  running_alloc.clear();
  platform_nb_hosts = 0;
  next_arrival_order = 0; // Reset for next simulation
  // free_hosts will be overwritten on next SimulationBegins
  return 0;
}

uint8_t batsim_edc_take_decisions(
  const uint8_t * what_happened,
  uint32_t what_happened_size,
  uint8_t ** decisions,
  uint32_t * decisions_size)
{
  (void) what_happened_size;

  auto * parsed = deserialize_message(*mb, !format_binary, what_happened);
  double now = parsed->now();
  mb->clear(now);

  auto nb_events = parsed->events()->size();
  for (unsigned int i = 0; i < nb_events; ++i) {
    auto event = (*parsed->events())[i];

    std::printf("easy received event type='%s'\n",
      batprotocol::fb::EnumNamesEvent()[event->event_type()]);

    switch (event->event_type()) {
      case fb::Event_BatsimHelloEvent: {
        mb->add_edc_hello("easy", "0.1.0");
      } break;

      case fb::Event_SimulationBeginsEvent: {
        auto simu_begins = event->event_as_SimulationBeginsEvent();
        platform_nb_hosts = simu_begins->computation_host_number();

        if (platform_nb_hosts > 0) {
          free_hosts = IntervalSet(IntervalSet::ClosedInterval(0, platform_nb_hosts - 1));
        }
      } break;

      case fb::Event_JobSubmittedEvent: {
        auto parsed_job = event->event_as_JobSubmittedEvent();

        SchedJob job;
        job.job_id = parsed_job->job_id()->str();
        job.nb_hosts = parsed_job->job()->resource_request();

        // IMPORTANT: this must exist / be filled by your workload.
        // In most Batsim workloads, this is "walltime".
        job.walltime = parsed_job->job()->walltime();
        
        // Policy-aware: capture submission time and arrival order
        job.submit_time = now;
        job.arrival_order = next_arrival_order++;

        if (job.nb_hosts > platform_nb_hosts) {
          mb->add_reject_job(job.job_id);
        } else {
          jobs.push_back(std::move(job));
        }
      } break;

      case fb::Event_JobCompletedEvent: {
        auto jc = event->event_as_JobCompletedEvent();
        std::string jid = jc->job_id()->str();

        auto it = running_alloc.find(jid);
        if (it != running_alloc.end()) {
          free_hosts = free_hosts + it->second.alloc;
          running_alloc.erase(it);
        }
      } break;

      default: break;
    }
  }

  // Make scheduling decisions (EASY)
  schedule_easy(now);

  mb->finish_message(now);
  serialize_message(*mb, !format_binary, const_cast<const uint8_t **>(decisions), decisions_size);
  return 0;
}