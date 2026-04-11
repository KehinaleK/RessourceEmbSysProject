import os
import numpy as np
from utils import *
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


ROOT_DIR = "../../../outputs/train/T0"

POLICY_ORDER = ["EXP", "FCFS", "LCFS", "LPF", "LQF", "SPF", "SQF"]

COLOURS, MARKERS = getColoursMarkers()


def parse_policy_pair(folder_name: str):
    parts = folder_name.replace("-", "_").split("_")
    if len(parts) < 2:
        return None
    return parts[0].upper(), parts[1].upper()

def getDeciles(file_path):
    df = pd.read_csv(file_path)
    df["week"] = df["job_id"].astype(str).str[:9]
    weekly_avg = df.groupby("week")["waiting_time"].mean().values
    return np.percentile(weekly_avg, 10), np.percentile(weekly_avg, 90)

rows = []

for subdir in sorted(os.listdir(ROOT_DIR)):
    folder = os.path.join(ROOT_DIR, subdir)
    schedule_path = os.path.join(folder, "schedule.json")
    jobs_path = os.path.join(folder, "jobs.csv")
    pair = parse_policy_pair(subdir)
    primary, backfilling = pair
    p10, p90 = getDeciles(jobs_path)

    data = importData(schedule_path)

    rows.append({
        "primary": primary,
        "backfilling": backfilling,
        "avg": data["mean_waiting_time"],
        "max": data["max_waiting_time"],
        "p10": p10,
        "p90": p90,
    })

baseline = None
for row in rows:
    if row["primary"] == "FCFS" and row["backfilling"] == "FCFS":
        baseline = row
        break

baseline_avg = baseline["avg"]
baseline_max = baseline["max"]

for row in rows:
    row["x"] = row["avg"] - baseline_avg
    row["y"] = row["max"] - baseline_max
    row["p10_rel"] = row["p10"] - baseline_avg
    row["p90_rel"] = row["p90"] - baseline_avg
    row["xerr_low"] = row["x"] - row["p10_rel"]
    row["xerr_high"] = row["p90_rel"] - row["x"]

fig, ax = plt.subplots(figsize=(11.5, 7))
ax.grid(True, alpha=0.3)

for row in rows:
    c = COLOURS[row["primary"]]
    m = MARKERS[row["backfilling"]]

    ax.errorbar(
        row["x"],
        row["y"],
        xerr=[[row["xerr_low"]], [row["xerr_high"]]],
        fmt="none",
        ecolor=c,
        elinewidth=2,
        capsize=3,
        alpha=0.9,
        zorder=1
    )

    if m in ["+", "x"]:
        ax.scatter(
            row["x"], row["y"],
            marker=m,
            color=c,
            s=120,
            linewidths=1.2,
            alpha=0.95,
            zorder=3
        )
    else:
        ax.scatter(
            row["x"], row["y"],
            marker=m,
            facecolors="none",
            edgecolors=c,
            s=120,
            linewidths=1.2,
            alpha=0.95,
            zorder=3
        )

ax.axvline(0, color="gray", linewidth=1, alpha=0.6)
ax.axhline(0, color="gray", linewidth=1, alpha=0.6)

ax.set_xlabel("AvgWait cost relative to FCFS–FCFS")
ax.set_ylabel("MaxWait cost relative to FCFS–FCFS")

backfillHandles = []
for name in POLICY_ORDER:
    m = MARKERS[name]
    if name in {"LCFS", "LPF"}:
        h = Line2D(
            [0], [0],
            marker=m,
            linestyle="None",
            color="black",
            markersize=11,
            label=name.lower()
        )
    else:
        h = Line2D(
            [0], [0],
            marker=m,
            linestyle="None",
            color="black",
            markerfacecolor="none",
            markeredgecolor="black",
            markersize=11,
            label=name.lower()
        )
    backfillHandles.append(h)

primaryHandles = [
    Line2D(
        [0], [0],
        marker="o",
        linestyle="-",
        color=COLOURS[name],
        markerfacecolor=COLOURS[name],
        markeredgecolor=COLOURS[name],
        linewidth=2,
        markersize=9,
        label=name.lower()
    )
    for name in POLICY_ORDER
]

legend1 = ax.legend(
    handles=backfillHandles,
    title="Backfilling",
    loc="upper left",
    bbox_to_anchor=(1.05, 1),
    frameon=False)

legend2 = ax.legend(
    handles=primaryHandles,
    title="Primary",
    loc="upper left",
    bbox_to_anchor=(1.05, 0.5),
    frameon=False ) 

ax.add_artist(legend1)

plt.tight_layout()
plt.show()