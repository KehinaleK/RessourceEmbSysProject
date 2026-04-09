#!/bin/bash

PRIMARY=$1
BACKFILLING=$2
THRESHOLD=$3

# To ensure we give all needed args
if [[ $# -ne 3 ]]; then
    echo "PRIMARY, BACKFILLING and THRESHOLD FLAG must be provided"
    echo "Usage: ./run.sh PRIMARY BACKFILLING THRESHOLD"
    echo "Example: ./run.sh FCFS SPF 1"
    echo "         ./run.sh FCFS SPF 0"
    exit 1
fi

OUTPUTDIR="outputs/${PRIMARY}_${BACKFILLING}_T${THRESHOLD}"
LOGDIR="logs/${PRIMARY}_${BACKFILLING}_T${THRESHOLD}"
mkdir -p "$OUTPUTDIR"
mkdir -p "$LOGDIR"

echo "Simulation will run with ${PRIMARY} policy and ${BACKFILLING} policy!"
echo "Threshold flag is ${THRESHOLD}."
echo "Logs will be saved in ${LOGDIR} and outputs in ${OUTPUTDIR}."

batsim \
  -p assets/plateform.xml \
  -w assets/testInput.json \
  -l ./build/libeasy_tuning.so "$PRIMARY $BACKFILLING $THRESHOLD" \
  -e "$OUTPUTDIR/" \
  > "$LOGDIR/log.txt"