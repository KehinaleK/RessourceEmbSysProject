# RessourceEmbSysProject
Repository for the Ressource for Embedded Systems project. 
This project aims at reproducing some of the experiments from the [Tuning EASY-Backfilling Queues paper](https://www.researchgate.net/publication/323419965_Tuning_EASY-Backfilling_Queues).

## Resampling

When it comes to the resampling method used to reproduce the experiment, we based it on the paper that was quoted in the one we chose. Our paper does not detail MUCH how they resample they data, although it is similar on surface-level to the one we based our logic on. There is no confirmation that the authors of our paper did proceed with every single step, but, we did (in case).
These steps are common in other works about resampling, however, we do not exclude the possibility that some steps may have been misinterpreted. In the situations where doubt arose, we chose what we saw in other papers and what felt more logical for our projet.

In [Resampling with Feedback: A New Paradigm of Using Workload Data for Performance Evaluation (Extended Version)](https://dl.acm.org/doi/10.1007/978-3-030-88224-2_1) authors propose the following method. 

### User categorisation

The authors start by selecting pools of users based on their activities: 
- Users whose submissions only span over the first or last 5% of the trace are excluded from the data. 
- Users are divided into **long term users** and **temporary users**. Long term users are users whose **submission span (date_of_last_submission - date_of_last_submission) are greater than total_days / 2 are considered long term users**. Users whose **submission spans are lower than than average are considered temporary users**.
### Initialisation


Once users are categorised, we initialise a set of active users:
- The **default number of long term users per week is the same one as the number of long term users present in the whole original trace**. 
- The **number of temporary users per week is the same one as the number of average temporary users per week in the original trace**.