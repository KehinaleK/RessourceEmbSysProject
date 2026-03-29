import json
from datetime import datetime
from pathlib import Path

INPUT_FILE = Path("data/KTH-SP2-1996.txt")
OUTPUT_FILE = Path("assets/kth_subset_jobs.json")
MAX_JOBS = 50
MAX_RESOURCES = 100


def parse_duration_to_seconds(s: str) -> int:
    s = s.strip().lower()

    if "h" not in s:
        raise ValueError(f"Unsupported duration format: {s}")

    hours_part, minutes_part = s.split("h", 1)
    hours = int(hours_part) if hours_part else 0
    minutes = int(minutes_part) if minutes_part else 0

    return hours * 3600 + minutes * 60


def read_jobs(input_file: Path):
    parsed_jobs = []

    with input_file.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    for line_idx, raw_line in enumerate(lines[1:], start=2):
        stripped = raw_line.strip()
        if not stripped:
            continue

        parts = stripped.split()
        if len(parts) < 10:
            continue

        try:
            jid = parts[2]
            tstart_date = parts[4]
            tstart_time = parts[5]
            npe_str = parts[8]
            treq_str = parts[9]

            submit_dt = datetime.strptime(
                f"{tstart_date} {tstart_time}",
                "%Y-%m-%d %H:%M:%S"
            )

            res = int(npe_str)
            walltime = parse_duration_to_seconds(treq_str)

            if res <= 0 or res > MAX_RESOURCES:
                continue
            if walltime <= 0:
                continue

            parsed_jobs.append({
                "jid": jid,
                "submit_dt": submit_dt,
                "res": res,
                "walltime": walltime
            })

        except Exception as e:
            print(f"Skipping line {line_idx}: {e}")
            continue

    return parsed_jobs


def build_batsim_workload(input_file: Path, output_file: Path, max_jobs: int):
    parsed_jobs = read_jobs(input_file)

    if not parsed_jobs:
        raise RuntimeError("No valid jobs parsed.")

    # Sort by actual submission datetime
    parsed_jobs.sort(key=lambda j: j["submit_dt"])

    # Take only the first max_jobs after sorting
    parsed_jobs = parsed_jobs[:max_jobs]

    base_submit_dt = parsed_jobs[0]["submit_dt"]

    jobs = []
    profiles = {}

    for idx, job in enumerate(parsed_jobs):
        subtime = (job["submit_dt"] - base_submit_dt).total_seconds()

        job_id = f"job_{idx}_{job['jid']}"
        profile_id = f"profile_{idx}"

        jobs.append({
            "id": job_id,
            "subtime": subtime,
            "res": job["res"],
            "profile": profile_id,
            "walltime": job["walltime"]
        })

        profiles[profile_id] = {
            "type": "delay",
            "delay": job["walltime"]
        }

    workload = {
        "description": f"KTH-SP2 subset converted to Batsim workload ({len(jobs)} jobs)",
        "nb_res": MAX_RESOURCES,
        "jobs": jobs,
        "profiles": profiles
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(workload, f, indent=2)

    print(f"Generated {len(jobs)} jobs into {output_file}")


if __name__ == "__main__":
    build_batsim_workload(INPUT_FILE, OUTPUT_FILE, MAX_JOBS)