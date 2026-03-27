from datetime import datetime, timedelta
import pandas as pd
import json
import random
import argparse



def easyGeneration(numOfWeeks, weeklyActivity):

    genTraceStart = datetime.strptime("1996-01-01", '%Y-%m-%d') 
    genTrace = {"week" : [], "usr" : [], "cac" : [], "jid" : [], "req" : [], "tstart" : [], "tstop" : [], 
                "npe" : [], "treq" : [], "uwall" : [], "reqcpu" : [], "ucpu" : [], "twait" : []} 

    for i in range(numOfWeeks):
        for user, weeks in weeklyActivity.items():
            # maybe try without avoiding empty weeks ! We'll have to see
            submissionWeeks = [subs for week, subs in weeks.items() if len(subs) > 0]
            randomUserWeeks = random.choice(submissionWeeks)
            for randomUserWeek in randomUserWeeks:
                ogStartDay = datetime.strptime(randomUserWeek[3], '%Y-%m-%d').weekday() # we get if it's a monday, thursday etc...
                ogStartTime = datetime.strptime(randomUserWeek[4], '%H:%M:%S').time() # and the time ! 
                ogEndDay = datetime.strptime(randomUserWeek[5], '%Y-%m-%d').weekday()
                ogEndTime = datetime.strptime(randomUserWeek[6], '%H:%M:%S').time()
                numDays = ogEndDay - ogStartDay
                newStartDay = genTraceStart + timedelta(days=ogStartDay) # if monday (0), then it's still 0, otherwise we shift the day
                newEndDay = newStartDay + timedelta(days=numDays)
                genTrace["week"].append(i)
                genTrace["usr"].append(user)
                genTrace["cac"].append(randomUserWeek[0])
                genTrace["jid"].append(randomUserWeek[1])
                genTrace["req"].append(randomUserWeek[2])
                genTrace["tstart"].append(datetime.combine(newStartDay, ogStartTime))
                genTrace["tstop"].append(datetime.combine(newEndDay, ogEndTime))
                genTrace["npe"].append(randomUserWeek[7])
                genTrace["treq"].append(randomUserWeek[8])
                genTrace["uwall"].append(randomUserWeek[9])
                genTrace["reqcpu"].append(randomUserWeek[10])
                genTrace["ucpu"].append(randomUserWeek[11])
                genTrace["twait"].append(randomUserWeek[12])
                
        genTraceStart += timedelta(days=6)

    df = pd.DataFrame(genTrace)
    print(df)




if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Create a synthetic trace for the reproduction of the tuning EASY backfilling queue paper.")
    parser.add_argument("-w", "--numberOfWeeks", type=int, help="Number of synthetic weeks to generate.", required=True)
    parser.add_argument("-m", "--generationMode", type=int, choices=[1, 2], help="User model to choose from: 1 easy one, 2 user modelling.")
    args = parser.parse_args()

    numOfWeeks, mode = args.numberOfWeeks, args.generationMode

    with open('weeklyActivity.json', 'r') as JSON:
        weeklyActivity = json.load(JSON)

    easyGeneration(numOfWeeks, weeklyActivity)




    