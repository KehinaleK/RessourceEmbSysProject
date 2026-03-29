# README — `easy.cpp`

## Overview

This file implements a **policy-aware EASY backfilling scheduler** for **Batsim EDC**.

It is based on the classic EASY scheduling idea:
1. choose jobs from the waiting queue according to a **primary policy**
2. start jobs immediately while they fit in the currently available resources
3. when the first job does not fit, reserve it as the **head job**
4. compute the earliest time when this reserved head job can start
5. try to **backfill** other jobs, but only if they do not delay the reserved head job

At the current stage, the scheduler is already structured to support different queue policies, but the active policies are still hardcoded to:

- `primary_policy = FCFS`
- `backfill_policy = FCFS`

So the current behavior is equivalent to **EASY-FCFS-FCFS**, but the code is now prepared for later experiments with other policy combinations.

---

## Main data structures

### `QueuePolicy`

```cpp
enum class QueuePolicy {
  FCFS,
  LCFS,
  SPF,
  LPF,
  SQF,
  LQF,
  EXP
};