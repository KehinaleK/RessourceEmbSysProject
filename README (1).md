# HPC Scheduling with Batsim – EASY Backfilling

This project implements and evaluates job scheduling policies in HPC systems using **Batsim**.  
The focus is on a refactored implementation of the **EASY backfilling scheduler**, extended with support for multiple queue policies.

---

## Overview

The project contains:

- A working implementation of the **EASY scheduler** (`easy.cpp`)
- Support for multiple queue ordering policies (FCFS, SPF, LPF, etc.)
- A real workload derived from the **KTH-SP2 trace**
- A minimal platform configuration for simulation
- A Python script to convert raw workload logs into Batsim format

The goal of this stage was to:

1. Refactor the EASY scheduler to support different policies
2. Convert a real HPC workload into Batsim-compatible format
3. Run a first working simulation and verify correctness

---

## Project Structure

```text
assets/
  kth_machine.xml           # Platform definition (compute nodes)
  kth_subset_jobs.json      # Workload (converted from KTH trace)
  more_jobs.json            # Additional workload (optional / legacy)
build/                      # Build artifacts (generated)
data/
  KTH-SP2-1996.txt          # Original workload trace
out/
  jobs.csv
  schedule.csv              # Output from previous runs
results_easy_kth/
  jobs.csv
  schedule.csv              # Output of EASY scheduler run
scripts/
  kth_to_batsim.py          # Workload conversion script
src/
  batsim_edc.h
  easy.cpp                  # Main scheduler implementation
analyze_easy.ipynb          # Analysis notebook
meson.build                 # Build configuration
```

---

## What Was Done

### 1. Scheduler Implementation

`src/easy.cpp` implements the full EASY backfilling logic:

- **Primary scheduling phase** – assigns available resources to queued jobs
- **Reservation** – guarantees a start time for the blocked head-of-queue job
- **Backfilling phase** – fills idle resources with eligible smaller jobs

Supported queue ordering policies:

| Policy | Description |
|--------|-------------|
| `FCFS` | First-Come-First-Served |
| `LCFS` | Last-Come-First-Served |
| `SPF`  | Shortest Processing First |
| `LPF`  | Longest Processing First |
| `SQF`  | Smallest resource request first |
| `LQF`  | Largest resource request first |
| `EXP`  | Expansion Factor |

**Currently active configuration:**

```
primary_policy  = FCFS
backfill_policy = FCFS
```

Current behavior: **EASY-FCFS-FCFS**

---

### 2. Workload Preparation

**Source:** `data/KTH-SP2-1996.txt`

Steps performed:
- Extract a subset of jobs from the trace
- Parse submission time, number of processors (`npe`), and requested time (`treq`)
- Convert into Batsim JSON format

**Output:** `assets/kth_subset_jobs.json`

Each job entry has the following structure:

```json
{
  "id": "...",
  "subtime": ...,
  "res": ...,
  "profile": "...",
  "walltime": ...
}
```

---

### 3. Platform Definition

**File:** `assets/kth_machine.xml`

Defines:
- A cluster of compute nodes
- A master node (required by Batsim)
- Network topology

The platform was simplified to ensure compatibility with the workload.

---

### 4. Build Process

Inside the Batsim container:

```bash
cd /outside
meson setup --reconfigure build
ninja -C build
```

This produces:

```
build/libeasy.so
```

---

### 5. Running the Simulation

```bash
batsim \
  -p assets/kth_machine.xml \
  -w assets/kth_subset_jobs.json \
  -l ./build/libeasy.so 0 '' \
  -m master_host \
  -e results_easy_kth/
```

| Flag | Description |
|------|-------------|
| `-p` | Platform file |
| `-w` | Workload JSON |
| `-l` | Scheduler shared library |
| `0`  | Binary protocol mode |
| `-m` | Required master node name |
| `-e` | Output directory |

---

### 6. Simulation Output

Results are stored in `results_easy_kth/`:

```
results_easy_kth/
  jobs.csv
  schedule.csv
```

Metrics observed in logs:
- Makespan
- Mean waiting time
- Turnaround time
- Slowdown
- Machine utilization

The simulation completed successfully with all jobs processed.

---

## Current Limitations

### 1. Workload Quality
- Some jobs are killed due to walltime mismatch
- Conversion from the KTH trace is approximate
- Needs better mapping between `treq`, runtime, and walltime

### 2. Policies Not Yet Configurable
- Policies are implemented but currently hardcoded
- Next step: pass policy via configuration instead of editing source code

### 3. No Threshold Mechanism
- The threshold-based prioritization (from the reference paper) is not implemented
- Needs: modify queue ordering logic in `easy.cpp`

### 4. No Automated Experiments
- Currently running single simulations manually
- Needs: a batch-run script and cross-policy comparison tooling

---

## Next Steps

1. Add runtime/threshold-based prioritization
2. Enable dynamic selection of scheduling policies (no recompile required)
3. Improve workload realism and walltime accuracy
4. Automate batch experiments across policy combinations
5. Compare and analyze results across all policy variants

---

## Status

| Component | Status |
|-----------|--------|
| Scheduler compiles | ✅ |
| Workload loads | ✅ |
| Simulation runs | ✅ |
| Results generated | ✅ |
| Full experimental framework | ⏳ In progress |
| Final research alignment | ⏳ In progress |

> This is a working prototype. Core functionality is verified, but the experimental and evaluation framework is still being developed.
