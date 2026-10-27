#!/usr/bin/env python3
"""Run an Android build command with time/disk safeguards and evidence capture."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time


def tune_github_parallelism(command):
    """Use the public GitHub runner more fully for the expensive image build only."""
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return command, False
    tuned = list(command)
    marker = "m -j2 bootimage systemimage"
    replacement = "m -j4 bootimage systemimage"
    for index, value in enumerate(tuned):
        if marker in value:
            tuned[index] = value.replace(marker, replacement, 1)
            return tuned, True
    return tuned, False


def run(command, root, evidence, minutes, reserve_gib):
    evidence.mkdir(parents=True, exist_ok=True)
    command, parallelism_tuned = tune_github_parallelism(command)
    start = time.monotonic()
    samples = []
    reason = None
    log_path = evidence / "build.log"
    with log_path.open("w") as log:
        process = subprocess.Popen(
            command,
            cwd=root,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=os.environ.copy(),
        )
        try:
            while process.poll() is None:
                elapsed = time.monotonic() - start
                free = shutil.disk_usage(root).free
                samples.append({"elapsed_seconds": round(elapsed, 1), "free_bytes": free})
                if free < reserve_gib * 1024**3:
                    reason = "DISK_RESERVE_REACHED"
                elif elapsed >= minutes * 60:
                    reason = "TIME_BUDGET_REACHED"
                if reason:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                    break
                time.sleep(5)
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
    status = reason or ("BUILD_COMPLETE" if process.returncode == 0 else "BUILD_ERROR")
    report = {
        "status": status,
        "returncode": process.returncode,
        "elapsed_seconds": round(time.monotonic() - start, 1),
        "reserve_gib": reserve_gib,
        "budget_minutes": minutes,
        "parallelism_tuned": parallelism_tuned,
        "samples": samples,
        "final_free_bytes": shutil.disk_usage(root).free,
        "android_compiled": status == "BUILD_COMPLETE",
    }
    (evidence / "build-result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "samples"}, indent=2))
    return 0 if status == "BUILD_COMPLETE" else 2


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--minutes", type=float, default=25)
    p.add_argument("--reserve-gib", type=float, default=8)
    p.add_argument("command", nargs=argparse.REMAINDER)
    a = p.parse_args()
    cmd = a.command[1:] if a.command[:1] == ["--"] else a.command
    if not cmd or a.minutes <= 0 or a.reserve_gib < 1:
        p.error("Command, positive time budget and at least 1 GiB reserve required")
    raise SystemExit(run(cmd, a.root.resolve(), a.evidence.resolve(), a.minutes, a.reserve_gib))
