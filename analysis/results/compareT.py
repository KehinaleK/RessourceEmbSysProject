import os
import json
from collections import defaultdict
import matplotlib.pyplot as plt

directoryTrain = "../../outputs/train/T0"
directoryTrainT = "../../outputs/train/T1"

files = []
filesT = []

for f in os.listdir(directoryTrain):
    files.append(f"{directoryTrain}/{f}/schedule.json")

dictMetrics = defaultdict(dict)
for f in files:
    with open(f, "r") as file:
        data = json.load(file)

    key = f.split("/")[-2].replace("_T0", "")
    # if key.split("_")[0] != "SQF":
    dictMetrics[key]["AvgTime"] = data["mean_waiting_time"]
    dictMetrics[key]["MaxTime"] = data["max_waiting_time"]

for f in os.listdir(directoryTrainT):
    filesT.append(f"{directoryTrainT}/{f}/schedule.json")

dictMetricsT = defaultdict(dict)
for f in filesT:
    with open(f, "r") as file:
        dataT = json.load(file)

    key = f.split("/")[-2].replace("_T1", "")
    # if key.split("_")[0] != "SQF":
    dictMetricsT[key]["AvgTime"] = dataT["mean_waiting_time"]
    dictMetricsT[key]["MaxTime"] = dataT["max_waiting_time"]


baseline_key = "FCFS_FCFS"
baseline_avg = dictMetrics[baseline_key]["AvgTime"]
baseline_max = dictMetrics[baseline_key]["MaxTime"]

rows = []
common_keys = sorted(set(dictMetrics.keys()) & set(dictMetricsT.keys()))

for key in common_keys:
    primary = key.split("_")[0]

    rows.append({
        "key": key,
        "primary": primary,
        "avg_noT": dictMetrics[key]["AvgTime"],
        "max_noT": dictMetrics[key]["MaxTime"],
        "avg_T": dictMetricsT[key]["AvgTime"],
        "max_T": dictMetricsT[key]["MaxTime"],
    })

colors = {
    "EXP": "#137e6d",
    "FCFS": "#dc4d01",
    "LCFS": "#665fd1",
    "LPF": "#de0c62",
    "LQF": "#63a950",
    "SPF": "#f9bc08",
    "SQF": "#a87900"
}

plt.figure(figsize=(10, 7))
already_in_legend = set()

for row in rows:
    c = colors.get(row["primary"], "gray")

    plt.plot(
        [row["avg_noT"], row["avg_T"]],
        [row["max_noT"], row["max_T"]],
        color="gray",
        alpha=0.35,
        linewidth=1
    )

    plt.scatter(
        row["avg_noT"],
        row["max_noT"],
        color=c,
        alpha=0.25,
        s=60
    )

    label = row["primary"] if row["primary"] not in already_in_legend else None
    plt.scatter(
        row["avg_T"],
        row["max_T"],
        color=c,
        alpha=0.95,
        s=60,
        label=label
    )

    already_in_legend.add(row["primary"])

plt.scatter(
    baseline_avg,
    baseline_max,
    color="black",
    s=120,
    marker="x",
    linewidths=2,
    label="FCFS_FCFS baseline"
)


plt.xlabel("Mean AvgWait")
plt.ylabel("Max MaxWait")
plt.title("Thresholded vs unthresholded policies (absolute values)")
plt.legend(title="Primary")
plt.tight_layout()
plt.show()