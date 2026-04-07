import os
import json
import argparse
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from collections import defaultdict
from statistics import mean

def importData(resultFile):

    with open(resultFile, 'r') as JSON:
       return json.load(JSON)

import matplotlib.pyplot as plt
import numpy as np

def generalisationPlotStarter(trainDebugDict, testDebugDict, anchorValueTrain, anchorValueTest):
  
    train_anchor = anchorValueTrain[0]["AvgWaitTime"]
    test_anchor = anchorValueTest[0]["AvgWaitTime"]
    policyCombinations = sorted(set(trainDebugDict.keys()) & set(testDebugDict.keys()))

    train_relative = []
    test_relative = []
    labels = []
    percentageChanges = {}
    primaryMarkers = {
        "EXP": "o",
        "FCFS": "^",
        "LCFS": "*",
        "LPF": "X",
        "LQF": "D",
        "SPF": "v",   
        "SQF": "s"
    }

    backfillingColours = {
        "EXP": "#856793",
        "FCFS": "#3d7afd",
        "LCFS": "#ca6641",
        "LPF": "#75b84f",
        "LQF": "#ffdf22",
        "SPF": "#fe86a4",
        "SQF": "#be0119"
    }


    for key in policyCombinations:
        trainVal = trainDebugDict[key]["AvgWaitTime"]
        testVal = testDebugDict[key]["AvgWaitTime"]

        # to get the average increase/decrease cmpared to anchor policy (fcfs - fcfs)
        if key == "FCFS_FCFS":
            percent = 0
        else:
            percent = (testVal - trainVal) / trainVal * 100

        percentageChanges[key] = percent
        train_relative.append(trainVal - train_anchor)
        test_relative.append(testVal - test_anchor)
        labels.append(key)

    print(labels)
    fig, ax = plt.subplots(figsize=(7, 8))

    x_train = 0.3
    x_test = 0.7

    ax.axvline(x=x_train, color='gray', alpha=0.5)
    ax.axvline(x=x_test, color='gray', alpha=0.5)
    ax.grid(axis='y', zorder = 0, color='gray', alpha = 0.5)


    # Plot to connect the points
    for i, key in enumerate(labels):
        left_policy, right_policy = key.split("_")
        marker = primaryMarkers.get(left_policy)
        color = backfillingColours.get(right_policy)

        y1 = train_relative[i]
        y2 = test_relative[i]

        # for the line colour, so based on the bf policy
        ax.plot([x_train, x_test], [y1, y2],
                color=color,
                linewidth=1.5,
                alpha=0.8)

        # markers for the primary one
        ax.scatter(x_train, y1,
                marker=marker,
                facecolors='none',   
                edgecolors='black',
                s=60,
                linewidths=0.8,
                zorder=3)
        # and for the second one
        ax.scatter(x_test, y2,
                marker=marker,
                facecolors='none',    
                edgecolors='black',
                s=60,
                linewidths=0.8,
                zorder=3)


    ax.set_xlim(0, 1)
    ax.set_xticks([x_train, x_test])
    ax.set_xticklabels(["train", "test"])
    ax.set_ylabel("Difference from anchor AvgWaitTime")
    ax.set_title("Generalisation relative to FCFS anchor")

    print(percentageChanges)
    print(mean([value for value in percentageChanges.values()]))

    
    primary_handles = []
    for policy, marker in primaryMarkers.items():
        primary_handles.append(
            Line2D([0], [0],
                marker=marker,
                color='black',
                linestyle='None',
                markersize=6,
                markerfacecolor='none',
                markeredgewidth=0.8,
                label=policy)
        )

        bf_handles = []
        for policy, color in backfillingColours.items():
            bf_handles.append(
                Line2D([0], [0],
                    color=color,
                    linewidth=1.5,
                    label=policy)
            )

    legend1 = ax.legend(handles=primary_handles,
                        title="Primary Policy",
                        loc='upper left',
                        bbox_to_anchor=(1.05, 1))
    legend2 = ax.legend(handles=bf_handles,
                        title="Backfilling Policy",
                        loc='upper left',
                        bbox_to_anchor=(1.05, 0.5))

  
    ax.add_artist(legend1)
    plt.tight_layout()
    plt.show()



if __name__ == "__main__":

    # parser = argparse.ArgumentParser(description="Create a synthetic trace for the reproduction of the tuning EASY backfilling queue paper.")
    # parser.add_argument("-w", "--numberOfWeeks", type=int, help="Number of synthetic weeks to generate.", required=True)
    # args = parser.parse_args()

    # numOfWeeks = args.numberOfWeeks

    trainResults = "../../outputs/train"
    testResults = "../../outputs/test"

    filesTrainResults = []
    filesTestResults = []

    for subdir in os.listdir(trainResults):
        resultFile = [file for file in os.listdir(f"{trainResults}/{subdir}") if file == "schedule.json"][0]
        filesTrainResults.append(f"{trainResults}/{subdir}/{resultFile}")

    for subdir in os.listdir(testResults):
        resultFile = [file for file in os.listdir(f"{testResults}/{subdir}") if file == "schedule.json"][0]
        filesTestResults.append(f"{testResults}/{subdir}/{resultFile}")
    

    filesTrainResults = filesTrainResults
    filesTestResults = filesTestResults


    TrainResultsMetrics = defaultdict(dict)
    for file in filesTrainResults:  
        results = importData(file)

        TrainResultsMetrics[file.split("/")[4]]["MaxWaitTime"] = results["max_waiting_time"]
        TrainResultsMetrics[file.split("/")[4]]["AvgWaitTime"] = results["mean_waiting_time"]

    TestResultsMetrics = defaultdict(dict)
    for file in filesTestResults:  
        results = importData(file)

        TestResultsMetrics[file.split("/")[4]]["MaxWaitTime"] = results["max_waiting_time"]
        TestResultsMetrics[file.split("/")[4]]["AvgWaitTime"] = results["mean_waiting_time"]


    TraindebugDict = {key : value for key, value in TrainResultsMetrics.items()}
    TestdebugDict = {key : value for key, value in TestResultsMetrics.items()}

    anchorValueTrain = [value for key, value in TrainResultsMetrics.items() if "FCFS" == key.split("_")[0] and "FCFS" == key.split("_")[1]]
    anchorValueTest = [value for key, value in TestResultsMetrics.items() if "FCFS" == key.split("_")[0] and "FCFS" == key.split("_")[1]]
    
    generalisationPlotStarter(TraindebugDict, TestdebugDict, anchorValueTrain, anchorValueTest)