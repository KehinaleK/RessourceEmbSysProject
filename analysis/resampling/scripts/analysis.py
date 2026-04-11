from collections import defaultdict, Counter
from datetime import datetime, timedelta
from statistics import mean
import pandas as pd
import json

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

def importDataFromFileCSV(file):


    data = defaultdict(lambda: defaultdict(list))

    df = pd.read_csv(file)

    week_col = "week"
    user_col = "usr"

    for _, row in df.iterrows():
        week = int(row[week_col])
        user = str(row[user_col])
        values = row.drop(labels=[week_col, user_col]).tolist()

        data[week][user].append(values)

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

    usersAvg, temporaryUsersAvg, permanentUsersAvg = getAverageNumberOfTypeUsersAWeek(temporaryUsers, permanentUsers, data)
    
    return usersAvg, permanentUsers, permanentUsersAvg, temporaryUsers, temporaryUsersAvg,

def saveUserModelling(permanentUsers, temporaryUsers, temporaryUsersAvg):

    userMod = {"totalU" : len(permanentUsers) + len(temporaryUsers), "AvgT" : temporaryUsersAvg, 
               "P" : permanentUsers, "T" : temporaryUsers}
    with open('UserModelling.json', 'w') as fp:
        json.dump(userMod, fp)

def userActivityPerWeek(userData, allWeeksStarts):


    """weeklyActivity = { user : {week : [[sub], [sub]], week2 : [[sub]]}}"""

    weeklyActivity = {}
    weeklyNbJobs = {}

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

def getAverageNumberOfTypeUsersAWeek(temporaryUsers, permanentUsers, data):

    temporaryUsersAverage = []
    permanentUsersAverage = []
    usersAverage = []

    allWeeksStarts = getAllWeeksStarts()

    i = 0
    for week in allWeeksStarts:
        # print("############# WEEK ", i)
        numTemporaryUsers = 0
        numPermanentUsers = 0
        numUsers = 0
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
                    numUsers += 1
                    break
        for user in permanentUsers:
            subs = data[user]
            for sub in subs:
                if weekStart <= datetime.strptime(sub[3], '%Y-%m-%d') <= weekEnd or weekStart <= datetime.strptime(sub[5], '%Y-%m-%d') <= weekEnd:
                    #print(f"User {user} appears with submission {datetime.strptime(sub[3], '%Y-%m-%d')} and { datetime.strptime(sub[5], '%Y-%m-%d')}")
                    numPermanentUsers += 1
                    numUsers += 1
                    break
        
       
        usersAverage.append(numUsers)
        temporaryUsersAverage.append(numTemporaryUsers)
        permanentUsersAverage.append(numPermanentUsers)
        i += 1

    return mean(usersAverage), mean(temporaryUsersAverage), mean(permanentUsersAverage) 


def getAverageNumberJobs(temporaryUsers, permanentUsers, data):

    users = temporaryUsers + permanentUsers
    jobsAverage = []
    totalJobs = 0
    allWeeksStarts = getAllWeeksStarts()

    i = 0
    for week in allWeeksStarts:

        numjobs = 0
        weekStart = week[0]
        weekEnd = week[1]
     
        for user in users:
            subs = data[user]
            for sub in subs:
                if weekStart <= datetime.strptime(sub[3], '%Y-%m-%d') <= weekEnd or weekStart <= datetime.strptime(sub[5], '%Y-%m-%d') <= weekEnd:
                    #print(f"User {user} appears with submission {datetime.strptime(sub[3], '%Y-%m-%d')} and { datetime.strptime(sub[5], '%Y-%m-%d')}")
                    numjobs += 1
                    totalJobs += 1

       
        jobsAverage.append(numjobs)
        i += 1

    return totalJobs, mean(jobsAverage)



def getUserInfoFromFile(userInfoFile):

    with open(userInfoFile, 'r') as JSON:
        UserModelling = json.load(JSON)

    return UserModelling

def getUserInfoFromResample(resampleData):

    totalJobs = 0
    allJobs = []
    temporaryUserJobs = []
    permanentUserJobs = []

    for week, data in resampleData.items():
        
        for user, subs in data.items():
            totalsubs += len(subs)




if __name__ == "__main__":

    totalsubs = 0
    userData = importDataFromFile('KTH-SP2-1996-0.txt')
    # userData = importDataFromFileCSV('analysis/resampling/ResampleTrace50_2.csv')


    ogTraceInfo = {"TotalUsers" : 0, "TotalT" : 0, "TotalP" : 0,
                   "TotalJobs"  : 0, "AvgJobsPerWeek" : 0, "AvgUsersPerWeek" : 0,
                   "AvgTPerWeek" : 0, "AvgPPerWeek" : 0,}
    

    userModelling = getUserInfoFromFile("UserModelling.json")
    # for week, usrData in userData.items():
    #     print(week)
                

        
    # FOR THE OG TRACE
    userAvg, permanentUsers, permanendUsersAvg, temporaryUsers, temporaryUsersAvg = getUserTypeInfo(userData)
    totalJobs, jobsAvg = getAverageNumberJobs(temporaryUsers, permanentUsers, userData)
    ogTraceInfo["TotalUsers"] = len(permanentUsers) + len(temporaryUsers)
    ogTraceInfo["TotalP"] = len(permanentUsers)
    ogTraceInfo["TotalT"] = len(temporaryUsers)
    ogTraceInfo["TotalJobs"] = totalJobs
    ogTraceInfo["AvgJobsPerWeek"] = jobsAvg
    ogTraceInfo["AvgUsersPerWeek"] = userAvg
    ogTraceInfo["AvgTPerWeek"] = temporaryUsersAvg
    ogTraceInfo["AvgPPerWeek"] = permanendUsersAvg
    with open('ogTraceStats.json', 'w') as fp:
        json.dump(ogTraceInfo, fp)



    # FOR THE RESAMPLED TRACES

    # saveUserModelling(permanentUsers, temporaryUsers, temporaryUsersAvg)
    # weeklyActivity = userActivityPerWeek(userData, allWeeksStarts)
    # json.dumps(weeklyActivity)

    # with open('weeklyActivity.json', 'w') as fp:
    #     json.dump(weeklyActivity, fp)

