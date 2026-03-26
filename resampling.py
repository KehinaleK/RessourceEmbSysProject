from collections import defaultdict, Counter
from datetime import datetime, date

data = defaultdict(list)
counts = Counter()
columns = []



with open('KTH-SP2-1996-0.txt') as f:

    for idx, line in enumerate(f.readlines()):
        if idx == 0:
            columns == [elem.strip() for elem in line.split()]
            continue
        line = [elem.strip() for elem in line.split()]
        if len(line) > 0:
            data[line[0]].append(line[1:])
            counts[line[0]] += 1

def get_user_type(data):
   
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

    allDates = sorted(datetime.strptime(x, '%Y-%m-%d') for x in allDates)
    totalDays = (allDates[-1] - allDates[0]).days
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

    print(len(userSpans), len(permanentUsers), len(temporaryUsers))
    return permanentUsers, temporaryUsers

permanentUsers, temporaryUsers = get_user_type(data)






