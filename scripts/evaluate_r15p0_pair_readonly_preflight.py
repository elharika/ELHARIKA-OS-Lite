#!/usr/bin/env python3
"""Evaluate an exact SM-P900 TWRP read-only BOOT/Mali pairing report.

This validates actual SHA fingerprints and never authorizes an install.
The observed state is useful for choosing whether a matched R15P0 lab trial
is even worth preparing. It is not GPU, Android boot, or rollback verification.
"""
import argparse
import json
from pathlib import Path

HEADER = "ELHARIKA SM-P900 READ-ONLY R15P0 PAIR PREFLIGHT"
R7_SHA = "f5f60b64a023b5223d7af711bfbe239dc79248f9cded878cd17e034751594eb0"
R15_SHA = "7d15b15e127e4b31841e1081efac31d2c298c2748dbc5d55889a3e8d45e20d14"
UK10_SHA = "34af399a1090295a7138297b9352334c73d569212a4bd11be4b3254dafe26cde"
UK5_SHA = "3bc453470f2f6711d463f3fff9b115011cbcefcbb1355be9af147857d892e433"
DONOR_SHA = "a00166d28cbd0213c88daadb437534310de09da4bf9fcc64f8e2207e22d76839"
MAX_BYTES = 16384


def parse(text):
    if not text.startswith(HEADER + "\n"):
        raise ValueError("Unrecognized SM-P900 pair evidence")
    record = {}
    for line in text.splitlines()[1:]:
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name in record:
            raise ValueError("Duplicated field " + name)
        record[name] = value
    for name, expected in {
        "device": "v1awifi",
        "bootloader_family": "P900",
        "boot_partition_modified": "NO",
        "system_partition_modified": "NO",
        "data_partition_modified": "NO",
        "flash_approved": "NO",
        "physical_boot_verified": "NO",
    }.items():
        if record.get(name) != expected:
            raise ValueError("Missing or unexpected no-flash guard " + name)
    r7_match = record.get("boot_r7_prefix_sha256") == R7_SHA
    r15_match = record.get("boot_r15_prefix_sha256") == R15_SHA
    boot_status = record.get("boot_status")
    mali_status = record.get("mali_status")
    mali_sha = record.get("mali_sha256")
    if r7_match and r15_match:
        raise ValueError("Inconsistent simultaneous boot SHA matches")
    if boot_status == "CURRENT_R7P0_KBUILD_FIXED" and not r7_match:
        raise ValueError("r7p0 boot identity contradicts SHA")
    if boot_status == "ORIGINAL_R15P0_REFERENCE" and not r15_match:
        raise ValueError("r15p0 boot identity contradicts SHA")
    if boot_status not in ("CURRENT_R7P0_KBUILD_FIXED",
                           "ORIGINAL_R15P0_REFERENCE",
                           "UNKNOWN_DO_NOT_FLASH"):
        raise ValueError("Invalid BOOT identity")
    if boot_status == "UNKNOWN_DO_NOT_FLASH" and (r7_match or r15_match):
        raise ValueError("Incorrectly labeled known BOOT identity")
    valid_mali = {
        "TESTED_UK10_TRIAL": UK10_SHA,
        "BLOCKED_UK5_BASE": UK5_SHA,
        "PINNED_DONOR_R15P0": DONOR_SHA,
        "NOT_VISIBLE_MOUNT_SYSTEM_READ_ONLY": "NOT_VISIBLE",
    }
    if mali_status in valid_mali and mali_sha != valid_mali[mali_status]:
        raise ValueError("Mali reported SHA does not match classified binary")
    if mali_status not in valid_mali and mali_status != "UNKNOWN_DO_NOT_FLASH":
        raise ValueError("Invalid Mali identity")
    if mali_status == "UNKNOWN_DO_NOT_FLASH" and mali_sha in (UK10_SHA, UK5_SHA, DONOR_SHA):
        raise ValueError("Known Mali SHA inaccurately classified")

    if boot_status == "CURRENT_R7P0_KBUILD_FIXED" and mali_status == "TESTED_UK10_TRIAL":
        decision = "CURRENT_FAILURE_PAIR_CONFIRMED_BACKUP_REVIEW_ONLY"
    elif boot_status == "ORIGINAL_R15P0_REFERENCE" and mali_status == "PINNED_DONOR_R15P0":
        decision = "R15P0_DONOR_PAIR_FINGERPRINTS_MATCH_BOOT_UNVERIFIED"
    elif mali_status == "NOT_VISIBLE_MOUNT_SYSTEM_READ_ONLY":
        decision = "INCOMPLETE_READ_ONLY_SYSTEM_MOUNT_NEEDED"
    else:
        decision = "UNKNOWN_OR_MIXED_GPU_PAIR_DO_NOT_CHANGE"
    return {
        "status": "SM_P900_PAIR_PREFLIGHT_READ_ONLY_ANALYZED",
        "device": "SM-P900/v1awifi",
        "boot_status": boot_status,
        "mali_status": mali_status,
        "decision": decision,
        "safe_to_plan_candidate_review":
            decision == "CURRENT_FAILURE_PAIR_CONFIRMED_BACKUP_REVIEW_ONLY",
        "physical_egl_swap_verified": False,
        "boot_completed_verified": False,
        "rollback_proven_on_device": False,
        "flash_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.report.stat().st_size > MAX_BYTES:
        raise ValueError("Unexpectedly large diagnostic report")
    report = parse(args.report.read_text(errors="replace"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
