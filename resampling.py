from collections import defaultdict, Counter
from datetime import datetime, timedelta
from statistics import mean
import pandas as pd
import json
import random
import argparse



def importDataFromFile(file):

    """
    Return all of the trace as a dict where keys are users
    and values are list of list where each list is a submission,
    so the equivalent of a row in the og file.
    """

    data = defaultdict(list)
    counts = Counter()
    columns = []

    with open(file) as f:
        for idx, line in enumerate(f.readlines()):
            if idx == 0:
                columns == [elem.strip() for elem in line.split()]
                continue
            line = [elem.strip() for elem in line.split()]
            if len(line) > 0:
                data[line[0]].append(line[1:])
                counts[line[0]] += 1

    return data

def getUserTypeInfo(data):

    """
    Uses the data imported from the file to get multiple info:
    """
   
    permanentUsers = []
    temporaryUsers = []
    allDates = []
    userSpans = {}
    
    for user, subs in data.items():
        dates = []
        for sub in subs:
            dateStart = sub[3]
            dateEnd = sub[5]
            dates.append(dateStart)
            dates.append(dateEnd)
            allDates.append(dateStart)
            allDates.append(dateEnd)
        dates = sorted(datetime.strptime(x, '%Y-%m-%d') for x in dates)
        firstSub = dates[0]
        lastSub = dates[-1]
        diff = (lastSub - firstSub).days
        userSpans[user] = [diff, firstSub, lastSub]

    totalDays = 333
    # first day = 1996-09-30 and last one = 1997-08-29
    for user, span in userSpans.items():
        # first, we check if the first selection was made between the 1997-08-13 bc 5% of all days (333) is 16
        if span[1] > datetime.strptime("1997-08-13", '%Y-%m-%d'):
            continue
        # then ! we check if the last submission was made before the 1996-10-16
        if span[2] < datetime.strptime("1996-10-16", '%Y-%m-%d'):
            continue
        if span[0] / totalDays > 0.5:
            permanentUsers.append(user)
        else:
            temporaryUsers.append(user)

    temporaryUsersAvg = getAverageNumberOfTemporaryUsersAWeek(temporaryUsers, data)
    
    return permanentUsers, temporaryUsers, temporaryUsersAvg


def userActivityPerWeek(userData, allWeeksStarts):


    """weeklyActivity = { user : {week : [[sub], [sub]], week2 : [[sub]]}}"""

    weeklyActivity = {}

    for user, subs in userData.items():
        weeklyActivity[user] = {}
        for week in allWeeksStarts:
            weekStart = week[0]
            weekEnd = week[1]
            weeklyActivity[user][weekStart.strftime('%Y-%m-%d')] = []
            for sub in subs:
                # Check if a user submission is in the week in question
                if weekStart <= datetime.strptime(sub[3], '%Y-%m-%d') <= weekEnd:
                    # If yes, then, we add the submission to the weekly activities
                    # of the user
                    weeklyActivity[user][weekStart.strftime('%Y-%m-%d')].append(sub)

    return weeklyActivity

def getAllWeeksStarts():

    # total of 47 weeks ! 
    traceStart = datetime.strptime("1996-09-30", '%Y-%m-%d') # a monday 
    traceEnd = datetime.strptime("1997-08-29", '%Y-%m-%d') # a friday   
    allWeeksStarts = []
   
    while traceStart < traceEnd:
        allWeeksStarts.append((traceStart, traceStart + timedelta(days=6)))
        traceStart += timedelta(days=7)

    return allWeeksStarts

def getAverageNumberOfTemporaryUsersAWeek(temporaryUsers, data):

    

    temporaryUsersAverage = []

    i = 0
    for week in allWeeksStarts:
        # print("############# WEEK ", i)
        numTemporaryUsers = 0
        weekStart = week[0]
        weekEnd = week[1]
        # print(weekStart)
        # print(weekEnd)
        for user in temporaryUsers:
            subs = data[user]
            for sub in subs:
                if weekStart <= datetime.strptime(sub[3], '%Y-%m-%d') <= weekEnd or weekStart <= datetime.strptime(sub[5], '%Y-%m-%d') <= weekEnd:
                    #print(f"User {user} appears with submission {datetime.strptime(sub[3], '%Y-%m-%d')} and { datetime.strptime(sub[5], '%Y-%m-%d')}")
                    numTemporaryUsers += 1
                    break

        temporaryUsersAverage.append(numTemporaryUsers)
        i += 1

    return mean(temporaryUsersAverage), allWeeksStarts    

def complexGeneration(numOfWeeks, permanentUsers, TemporaryUsers, userData, temporaryUsersAvg):

    # To initialise, we first get permanent users and temporary ones.
    # As per the original resampling paper "The defaults are the number of long-term users
    # in the original log, and the average number of temporary users present in a
    # single week of the original log."
    NotImplemented

def easyGeneration(numOfWeeks, weeklyActivity):

    genTraceStart = datetime.strptime("1996-01-01", '%Y-%m-%d') 
    genTrace = {"usr" : [], "cac" : [], "jid" : [], "req" : [], "tstart" : [], "tstop" : [], "npe" : [], 
                "treq" : [], "uwall" : [], "reqcpu" : [], "ucpu" : [], "twait" : []} 

    for i in range(numOfWeeks):
        for user in weeklyActivity:
            weeks = user.values()
            submissionWeeks = [week for week in weeks if len(week.values) > 0]
            randomUserWeek = random.choice(submissionWeeks)
            print(randomUserWeek)







if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Create a synthetic trace for the reproduction of the tuning EASY backfilling queue paper.")
    parser.add_argument("-w", "--numberOfWeeks", type=int, help="Number of synthetic weeks to generate.", required=True)
    parser.add_argument("-m", "--generationMode", type=int, choices=[1, 2], help="User model to choose from: 1 easy one, 2 user modelling.")
    args = parser.parse_args()

    numOfWeeks, mode = args.numberOfWeeks, args.generationMode
    
    userData = importDataFromFile('KTH-SP2-1996-0.txt')
    allWeeksStarts = getAllWeeksStarts()
    # permanentUsers, temporaryUsers, temporaryUsersAvg, allWeeksStarts = getUserTypeInfo(userData)
    weeklyActivity = userActivityPerWeek(userData, allWeeksStarts)
    json.dumps(weeklyActivity)

    with open('weeklyActivity.json', 'w') as fp:
        json.dump(weeklyActivity, fp)

    easyGeneration(numOfWeeks, weeklyActivity)


