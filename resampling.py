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
    df.to_csv("analysis/ResampleTrace.csv")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Create a synthetic trace for the reproduction of the tuning EASY backfilling queue paper.")
    parser.add_argument("-w", "--numberOfWeeks", type=int, help="Number of synthetic weeks to generate.", required=True)
    args = parser.parse_args()

    numOfWeeks = args.numberOfWeeks

    with open('weeklyActivity.json', 'r') as JSON:
        weeklyActivity = json.load(JSON)

    easyGeneration(numOfWeeks, weeklyActivity)




    