import json

def importData(resultFile):

    with open(resultFile, 'r') as JSON:
       return json.load(JSON)


def getColoursMarkers():

    COLOURS = {
        "EXP":  "#1b9e77",
        "FCFS": "#d95f02",
        "LCFS": "#7570b3",
        "LPF":  "#e7298a",
        "LQF":  "#66a61e",
        "SPF":  "#e6ab02",
        "SQF":  "#a6761d",
    }

    MARKERS = {
        "EXP": "o",
        "FCFS": "^",
        "LCFS": "+",
        "LPF": "x",
        "LQF": "D",
        "SPF": "v",
        "SQF": "s",
    }

    return COLOURS, MARKERS




