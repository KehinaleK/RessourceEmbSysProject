import os
from utils import *
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from collections import defaultdict


def generalisationPlotStarter(trainDebugDict, testDebugDict, anchorValueTrain, anchorValueTest):
  
    train_anchor = anchorValueTrain[0]["AvgWaitTime"]
    test_anchor = anchorValueTest[0]["AvgWaitTime"]
    policyCombinations = sorted(set(trainDebugDict.keys()) & set(testDebugDict.keys()))

    train_relative = []
    test_relative = []
    labels = []
    percentageChanges = {}
    COLOURS, MARKERS = getColoursMarkers()

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


    fig, ax = plt.subplots(figsize=(7, 8))

    x_train = 0.25
    x_test = 0.75

    ax.axvline(x=x_train, color='gray', alpha=0.5)
    ax.axvline(x=x_test, color='gray', alpha=0.5)
    ax.grid(axis='y', zorder = 0, color='gray', alpha = 0.5)


    # Plot to connect the points
    for i, key in enumerate(labels):
        left_policy, right_policy = key.split("_")
        marker = MARKERS.get(right_policy)
        color = COLOURS.get(left_policy)
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
    ax.set_title("Generalisation relative to FCFS anchor without T\nAvg Decrease = -32%")
    
    primary_handles = []
    for policy, colour in COLOURS.items():
        primary_handles.append(
              Line2D([0], [0],
               color=colour,
               linewidth=1.5,
               label=policy))

        bf_handles = []
        for policy, marker in MARKERS.items():
            bf_handles.append(
            Line2D([0], [0],
               marker=marker,
               color='black',
               linestyle='None',
               markersize=6,
               markerfacecolor='none',
               markeredgewidth=0.8,
               label=policy))


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

    trainResults = "../../../outputs/train/T0"
    testResults = "../../../outputs/test/T0"

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

        TrainResultsMetrics[file.split("/")[6].replace("_T0", "")]["MaxWaitTime"] = results["max_waiting_time"]
        TrainResultsMetrics[file.split("/")[6].replace("_T0", "")]["AvgWaitTime"] = results["mean_waiting_time"]

    TestResultsMetrics = defaultdict(dict)
    for file in filesTestResults:  
        results = importData(file)

        TestResultsMetrics[file.split("/")[6].replace("_T0", "")]["MaxWaitTime"] = results["max_waiting_time"]
        TestResultsMetrics[file.split("/")[6].replace("_T0", "")]["AvgWaitTime"] = results["mean_waiting_time"]


    TraindebugDict = {key : value for key, value in TrainResultsMetrics.items()}
    TestdebugDict = {key : value for key, value in TestResultsMetrics.items()}

    anchorValueTrain = [value for key, value in TrainResultsMetrics.items() if "FCFS" == key.split("_")[0] and "FCFS" == key.split("_")[1]]
    anchorValueTest = [value for key, value in TestResultsMetrics.items() if "FCFS" == key.split("_")[0] and "FCFS" == key.split("_")[1]]
    
    generalisationPlotStarter(TraindebugDict, TestdebugDict, anchorValueTrain, anchorValueTest)