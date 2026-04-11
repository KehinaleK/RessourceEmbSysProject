import matplotlib.pyplot as plt
import numpy as np
import json

with open("ogTraceStats.json", 'r') as JSON:
        ogTraceStats = json.load(JSON)
with open("resamplesTraceStats.json", 'r') as JSON:
        resampleTraceStats = json.load(JSON)


# Overall numbers
labels_totals = ["TotalUsers", "TotalT", "TotalP"]

values1_totals = [ogTraceStats[k] for k in labels_totals]
values2_totals = [resampleTraceStats[k] for k in labels_totals]

x = np.arange(len(labels_totals))
width = 0.35

plt.figure()
plt.bar(x - width/2, values1_totals, width, label="OG Trace", color="#665fd1")
plt.bar(x + width/2, values2_totals, width, label="Resampled Trace", color="#de0c62")

plt.xticks(x, ["Total Users", "Total Temp Users", "Total LongTerm Users"])
plt.ylabel("Counts")
plt.title("Total Metrics Comparison")
plt.legend()

plt.tight_layout()
plt.show()


# To get weekly avg comparisons ! 
labels_avg = ["AvgUsersPerWeek", "AvgTPerWeek", "AvgPPerWeek"]

values1_avg = [ogTraceStats[k] for k in labels_avg]
values2_avg = [resampleTraceStats[k] for k in labels_avg]

x = np.arange(len(labels_avg))

plt.figure()
plt.bar(x - width/2, values1_avg, width, label="OG Trace", color="#665fd1")
plt.bar(x + width/2, values2_avg, width, label="Resampled Trace", color="#de0c62")

plt.xticks(x, ["Avg Users", "Avg Temp Users", "Avg LongTerm Users"])
plt.ylabel("Average per Week")
plt.title("Weekly Averages Comparison")
plt.legend()

plt.tight_layout()
plt.show()