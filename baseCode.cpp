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
};

//ressources
int available_hosts = 4; //c'est juste un exemple 

//primary queue of jobs 
std::vector<SchedJob*> primary_queue; 
//backfilling queue      
std::vector<SchedJob*> backfilling_queue;

//jobs that are running
std::vector<SchedJob*> running_jobs;

// 3 principle actions 

//job arrive
void job_arrive(SchedJob* job){
    primary_queue.push_back(job);
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
void schedule() {
    //While there is jobs in the queue
    while (!primary_queue.empty())
    {
        //FCFS
        SchedJob* first_job = primary_queue.front();

        //verify if we have the ressources needed for the job
        if (first_job->nb_hosts > available_hosts){
            break;
        }
        
        //run the job
        primary_queue.erase(primary_queue.begin());
        running_jobs.push_back(first_job);

        std::cout << "This job is running: " << first_job->job_id << std::endl;/* code */
    }
    

    
    
}
