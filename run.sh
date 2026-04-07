#!/bin/bash

PRIMARY=$1
BACKFILLING=$2

# To ensure we give both!

if [ -z "$PRIMARY" ] || [ -z "$BACKFILL" ]; then
    echo "Policies for both PRIMARY and BACKFILLING QUEUES MUST BE PROVIDED"
    echo "Usage: ./run.sh PRIMARY BACKFILLING"
    echo "Example: ./run.sh FCFS SPF"
    exit 1
fi

OUTPUTDIR = "outputs/${PRIMARY}_${BACKFILLING}"
LOGDIR = "logs/${PRIMARY}_${BACKFILLING}"
mkdir "$OUTPUTDIR"

echo "Simulation will run with ${PRIMARY} policy and ${BACKFILLING} policy!"
echo "Logs will be saved in ${LOGDIR} and outputs in ${OUTPUTDIR}."


batsim \
  -p assets/plateform.xml \
  -w assets/jobs.json \
  -l ./build/libeasy_tuning.so "$PRIMARY $BACKFILL" \
  -e "$OUTDIR" \
  > "$LOGDIR/log.txt"

