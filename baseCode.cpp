#include <cstdint>
#include <list>
#include <vector>
#include <string>
#include <iostream>

#include <batprotocol.hpp>
#include <intervalset.hpp>

#include "batsim_edc.h"

using namespace batprotocol;

// struct job
struct SchedJob {
    std::string job_id;
    uint8_t nb_hosts;
    double duration;
};

//batsim variables
MessageBuilder * mb = nullptr;
bool format_binary = true;
uint32_t platform_nb_hosts = 0;
uint32_t available_hosts = 0;


//primary queue of jobs 
std::vector<SchedJob*> primary_queue; 
//backfilling queue      
std::vector<SchedJob*> backfilling_queue;

//jobs that are running
std::vector<SchedJob*> running_jobs;

// Add batsim_edc_init
uint8_t batsim_edc_init(const uint8_t * data, uint32_t size, uint32_t flags) {
    format_binary = ((flags & BATSIM_EDC_FORMAT_BINARY) != 0);

    if ((flags & (BATSIM_EDC_FORMAT_BINARY | BATSIM_EDC_FORMAT_JSON)) != flags) {
        printf("Unkown flags used, cannot initialize.\n");
        return 1;
    }

    mb = new MessageBuilder(!format_binary);

    //ignore init data
    (void) data;
    (void) size;

    return 0;
}

//principle function to send msg EDCHelloEvent
uint8_t batsim_edc_take_decisions(
    const uint8_t * what_happened,
    uint32_t what_happened_size,
    uint8_t ** decisions,
    u_int32_t * decisions_size)
{
    //read the msg
    auto * parsed = deserialize_message(*mb, !format_binary, what_happened);

    //rest respond msg
    mb->clear(parsed->now());

    //traverse all events
    auto nb_events = parsed->events()->size();
    for(unsigned int i = 0; i < nb_events; ++i) {
        auto event = (*parsed->events())[i];

        switch (event->event_type()) 
        {
        case fb::Event_EDCHelloEvent: {
            mb->add_edc_hello("my_scheduler", "1.0");
        } break;

        //simulation begins event
        case fb::Event_SimulationBeginsEvent: {
            auto simu = event->event_as_SimulationBeginsEvent();

            platform_nb_hosts = simu->computation_host_number();
            available_hosts = platform_nb_hosts;
        } break;

        //connect job_arrive
        case fb::Event_JobSubmittedEvent: {
            auto parsed_job = event->event_as_JobSubmittedEvent();

            //create a job
            SchedJob* job = new SchedJob();
            job->job_id = parsed_job->job_id()->str();
            job->nb_hosts = parsed_job->job()->resource_request();

            //appel
            job_arrive(job);
        } break;

        //connect job_finished
        case fb::Event_JobCompletedEvent: {
            auto completed = event->event_as_JobCompletedEvent();

            std::string job_id = completed->job_id()->str();

            //find job in runnings_jobs
            for (auto job : running_jobs) {
                if (job->job_id == job_id) {
                    job_finished(job);
                    break;
                }
            }
        } break;
        
        default:
            break;
        }
    }

    //Activate the scuduler
    auto jobs_to_run = schedule();

    for (auto job : jobs_to_run) {
        IntervalSet hosts(IntervalSet::ClosedInterval(0, job->nb_hosts - 1));

        mb->add_execute_job(job->job_id, hosts.to_string_hyphen());
    }

    //send respond
    mb->finish_message(parsed->now());
    serialize_message(*mb, !format_binary, const_cast<const uint8_t **>(decisions), decisions_size);

    return 0;

}

//job arrive
void job_arrive(SchedJob* job){
    primary_queue.push_back(job);
    backfilling_queue.push_back(job);
    std::cout << "This job arrived :" << job->job_id << " and it needs :" << (int)job->nb_hosts << "hosts" << std::endl;
}

//job finish 
void job_finished(SchedJob* job){
    //go through all running jobs
    for(auto i = running_jobs.begin(); i != running_jobs.end(); ++i){
        //if we find job that finished
        if (*i == job) {
            std::cout << "This job has finished : " << job->job_id << std::endl;
            available_hosts += job->nb_hosts;
            running_jobs.erase(i);
            delete job;
            break;
        }
    }
 
}

//decide what we excute 
std::vector<SchedJob*> schedule() {
    std::vector<SchedJob*> launched_jobs;

    if (primary_queue.empty())     return launched_jobs;

    SchedJob* first_job = primary_queue.front();

    if (first_job->nb_hosts <= available_hosts){
        primary_queue.erase(primary_queue.begin());
        backfilling_queue.erase(primary_queue.begin());

        running_jobs.push_back(first_job);
        available_hosts -= first_job->nb_hosts;

        std::cout << "Running: " << first_job->job_id << std::endl;

        launched_jobs.push_back(first_job); 
        return launched_jobs;

    }

    //bachfilling
    for (auto i = backfilling_queue.begin(); i != backfilling_queue.end(); ) {
        SchedJob* job = *i;

        // don't take priority job
        if (job == first_job) {
            ++i;
            continue;
        }

        if (job->nb_hosts <= available_hosts) {
            running_jobs.push_back(job);
            available_hosts -= job->nb_hosts;

            std::cout << "Running (BACKFILL): " << job->job_id << std::endl;

            launched_jobs.push_back(job);

            i = backfilling_queue.erase(i);

            auto i2 = std::find(primary_queue.begin(), primary_queue.end(), job);
            if (i2 != primary_queue.end())
                primary_queue.erase(i2);
        }
        else {
            ++i;
        }
    }

    return launched_jobs;
}
    

    
