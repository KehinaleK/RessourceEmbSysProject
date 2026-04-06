from datetime import datetime, timedelta
import pandas as pd
import json
import random
import argparse

def easyGeneration(numOfWeeks, weeklyActivity):

    genTraceStart = datetime.strptime("1996-01-01", '%Y-%m-%d') 
    genTrace = {"week" : [], "usr" : [], "cac" : [], "jid" : [], "req" : [], "tstart" : [], "tstop" : [], 
                "npe" : [], "treq" : [], "uwall" : [], "reqcpu" : [], "ucpu" : [], "twait" : []} 

    idSuffixe = 0
    for i in range(numOfWeeks):
        for user, weeks in weeklyActivity.items():
            # If we get an empty week, then we go onto the next user.
            submissionWeeks = [subs for week, subs in weeks.items()]
            randomUserWeeks = random.choice(submissionWeeks)
            if len(randomUserWeeks) == 0:
                continue
            for randomUserWeek in randomUserWeeks:
                ogStartDay = datetime.strptime(randomUserWeek[3], '%Y-%m-%d').weekday() # we get if it's a monday, thursday etc...
                ogStartTime = datetime.strptime(randomUserWeek[4], '%H:%M:%S').time() # and the time ! 
                ogEndDay = datetime.strptime(randomUserWeek[5], '%Y-%m-%d').weekday()
                ogEndTime = datetime.strptime(randomUserWeek[6], '%H:%M:%S').time()
                numDays = ogEndDay - ogStartDay
                newStartDay = genTraceStart + timedelta(days=ogStartDay) # if monday (0), then it's still 0, otherwise we shift the day
                newEndDay = newStartDay + timedelta(days=numDays)
                newStartDayStr = newStartDay.strftime('%Y-%m-%d')
                genTrace["week"].append(i)
                genTrace["usr"].append(user)
                genTrace["cac"].append(randomUserWeek[0])
                genTrace["jid"].append(newStartDayStr.replace("-", "") + str(idSuffixe))
                genTrace["req"].append(randomUserWeek[2])
                genTrace["tstart"].append(datetime.combine(newStartDay, ogStartTime))
                genTrace["tstop"].append(datetime.combine(newEndDay, ogEndTime))
                genTrace["npe"].append(randomUserWeek[7])
                genTrace["treq"].append(randomUserWeek[8])
                genTrace["uwall"].append(randomUserWeek[9])
                genTrace["reqcpu"].append(randomUserWeek[10])
                genTrace["ucpu"].append(randomUserWeek[11])
                genTrace["twait"].append(randomUserWeek[12])
                idSuffixe += 1
                
        genTraceStart += timedelta(days=6)

    df = pd.DataFrame(genTrace)
    # df.to_csv("analysis/ResampleTrace.csv")

    return genTrace

def convertToSeconds(timeStr):
    parts = timeStr.strip().split("h")
    parts = [part for part in parts if part]

    if len(parts) == 2:
        hours = int(parts[0])
        minutes = int(parts[1])
    else:
        hours = 0
        minutes = int(parts[0])

    return hours * 3600 + minutes * 60
def saveToBatsimFormat(genTrace):

    jobs_tmp = []

    for submission in range(len(genTrace["jid"])):
        waitingTimeInSeconds = convertToSeconds(genTrace["twait"][submission])
        startTime = genTrace["tstart"][submission]
        submittingTime = startTime - timedelta(seconds=waitingTimeInSeconds)
        walltimeInSeconds = convertToSeconds(genTrace["treq"][submission])

        jobs_tmp.append({
            "id": genTrace["jid"][submission],
            "submit_datetime": submittingTime,
            "walltime": walltimeInSeconds,
            "res": int(genTrace["npe"][submission]),
        })

    # Submission times must start at 0 so we shift everything
    origin = min(job["submit_datetime"] for job in jobs_tmp)

    jobs = []
    profiles = {}

    for job in jobs_tmp:
        walltime = int(job["walltime"])
        profile_name = f"delay_{walltime}"

        if profile_name not in profiles:
            profiles[profile_name] = {
                "type": "delay",
                "delay": walltime
            }

        jobs.append({
            "id": job["id"],
            "subtime": int((job["submit_datetime"] - origin).total_seconds()),
            "walltime": walltime,
            "res": int(job["res"]),
            "profile": profile_name
        })

    jobs.sort(key=lambda x: (x["subtime"], x["id"]))

    batsim_workload = {
        "nb_res": 128,
        "jobs": jobs,
        "profiles": profiles
    }

    with open("jobs.json", "w") as f:
        json.dump(batsim_workload, f, indent=2)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Create a synthetic trace for the reproduction of the tuning EASY backfilling queue paper.")
    parser.add_argument("-w", "--numberOfWeeks", type=int, help="Number of synthetic weeks to generate.", required=True)
    args = parser.parse_args()

    numOfWeeks = args.numberOfWeeks

    with open('weeklyActivity.json', 'r') as JSON:
        weeklyActivity = json.load(JSON)

    genTrace = easyGeneration(numOfWeeks, weeklyActivity)
    saveToBatsimFormat(genTrace)




    