from collections import defaultdict, Counter
from datetime import datetime, timedelta
from statistics import mean
import pandas as pd
import json

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


def getUserInfoFromFile(userInfoFile):

    with open(userInfoFile, 'r') as JSON:
        UserModelling = json.load(JSON)

    return UserModelling


def getUserInfoFromResample(resampledData, T, P):

    totalJobs = 0
    allJobs = []
    usersJobs = []
    temporaryUserJobs = []
    permanentUserJobs = []
    allUsers = []
    allTemporaryUsers = []
    allPermanentUsers = []

    for week, data in resampledData.items():
        numJobs = 0
        numTUsers = 0
        numPUsers = 0
        numUsers = 0
        for user, subs in data.items():
            if user not in allUsers:
                allUsers.append(user)
            totalJobs += len(subs)
            numJobs += len(subs)
            numUsers += 1
            if user in T:
                numTUsers += 1
                if user not in allTemporaryUsers:
                    allTemporaryUsers.append(user)
            if user in P:
                numPUsers += 1
                if user not in allPermanentUsers:
                    allPermanentUsers.append(user)

        allJobs.append(numJobs)
        usersJobs.append(numUsers)
        temporaryUserJobs.append(numTUsers)
        permanentUserJobs.append(numPUsers)

    return len(allUsers), len(allPermanentUsers), len(allTemporaryUsers), totalJobs, mean(allJobs), mean(usersJobs), mean(permanentUserJobs), mean(temporaryUserJobs)



if __name__ == "__main__":


    sampleStats = []
    fileSuffixes = ["50_1", "50_2", "50_3", "50_4", "50_5"]
    userModelling = getUserInfoFromFile("UserModelling.json")
    temporaryUsers = userModelling["T"]
    permanentUsers = userModelling["P"]

    TraceInfo = {"TotalUsers" : 0, "TotalT" : 0, "TotalP" : 0,
                    "TotalJobs"  : 0, "AvgJobsPerWeek" : 0, "AvgUsersPerWeek" : 0,
                    "AvgTPerWeek" : 0, "AvgPPerWeek" : 0,}

    for file_suffixe in fileSuffixes:
      
        userData = importDataFromFileCSV(f'analysis/resampling/ResampleTrace{file_suffixe}.csv')
       
        totalUsers, totalP, totalT, totalJobs, AvgJobsPerWeek, avgUsersPerWeek, avgPPerWeek, avgTPerWeek = getUserInfoFromResample(userData, temporaryUsers, permanentUsers)
        TraceInfo["TotalUsers"] += totalUsers
        TraceInfo["TotalP"] += totalP
        TraceInfo["TotalT"] += totalT
        TraceInfo["TotalJobs"] += totalJobs
        TraceInfo["AvgJobsPerWeek"] += AvgJobsPerWeek
        TraceInfo["AvgUsersPerWeek"] += avgUsersPerWeek
        TraceInfo["AvgTPerWeek"] += avgTPerWeek
        TraceInfo["AvgPPerWeek"] += avgPPerWeek

    
    # We average the stats over the number of samples we have
    TraceInfo["TotalUsers"] = TraceInfo["TotalUsers"] // len(fileSuffixes)
    TraceInfo["TotalP"] = TraceInfo["TotalP"] // len(fileSuffixes)
    TraceInfo["TotalT"] = TraceInfo["TotalT"] // len(fileSuffixes)
    TraceInfo["TotalJobs"] = TraceInfo["TotalJobs"] // len(fileSuffixes)
    TraceInfo["AvgJobsPerWeek"] = TraceInfo["AvgJobsPerWeek"] // len(fileSuffixes)
    TraceInfo["AvgUsersPerWeek"] = TraceInfo["AvgUsersPerWeek"] // len(fileSuffixes)
    TraceInfo["AvgTPerWeek"] = TraceInfo["AvgTPerWeek"] // len(fileSuffixes)
    TraceInfo["AvgPPerWeek"] = TraceInfo["AvgPPerWeek"] // len(fileSuffixes) 

    with open(f'resamplesTraceStats.json', 'w') as fp:
        json.dump(TraceInfo, fp)





