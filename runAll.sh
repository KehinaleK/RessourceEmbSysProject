#!/bin/bash

POLICIES=("FCFS" "LCFS" "SPF" "LPF" "SQF" "LQF" "EXP")

for THRESHOLD in 0 1; do
    for P1 in "${POLICIES[@]}"; do
        for P2 in "${POLICIES[@]}"; do
            echo "Running: $P1 / $P2 | THRESHOLD=$THRESHOLD"
            ./run.sh $P1 $P2 $THRESHOLD
        done
    done
done