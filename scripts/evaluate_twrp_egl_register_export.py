#!/usr/bin/env python3
"""Evaluate the focused read-only TWRP EGL tombstone TXT (no device modification).

The exported text contains only selected fatal signal, fault address, registers,
PC and Mali frames. Correlate the exact ARM indexed LDR rather than guessing
whether a GPU, gralloc or window-swap bug created a bad pointer.
"""
import argparse
import json
from pathlib import Path
import re

from inspect_egl_fault_registers import parse_tombstone

MAX_INPUT = 128 * 1024
SPLIT = re.compile(r"(?m)^--- MATCH \d+ : [^\n]* ---\s*$")
TITLE = "ELHARIKA EGL / SM-P900 / READ ONLY TOMBSTONE SCAN"


def evaluate(source):
    if not source.startswith(TITLE):
        raise ValueError("Unrecognized SM-P900 read-only report")
    if "NO_MATCHING_TOMBSTONE_FOUND" in source:
        return {
            "status": "PRIOR_TOMBSTONE_ABSENT_NOT_A_GPU_FIX",
            "matches": [],
            "next_action": "Inspect whether Android Data was mounted/decrypted in TWRP; no new flash.",
            "hardware_fixed": False,
            "flash_approved": False,
        }
    pieces = SPLIT.split(source)
    if len(pieces) < 2:
        raise ValueError("No valid MATCH section found")
    if len(pieces) > 6:
        raise ValueError("Unexpected number of crash records")
    matches = []
    for index, block in enumerate(pieces[1:], start=1):
        parsed = parse_tombstone(block)
        parsed["export_match_index"] = index
        matches.append(parsed)
    if not matches:
        raise ValueError("No crash records")
    complete = [x for x in matches if x["status"] == "EGL_INDEXED_READ_REGISTER_CORRELATION"]
    zero = [x for x in complete if x["zero_count_underflow_observed"]]
    addr_agree = [x for x in complete if x["fault_address_matches_ldr"]]
    return {
        "status": "TOMBSTONE_ARM_REGISTER_CORRELATION_COMPLETE" if len(complete) == len(matches)
                  else "TOMBSTONE_ARM_REGISTER_CORRELATION_PARTIAL",
        "matches": matches,
        "with_all_required_registers": len(complete),
        "fault_address_matches_indexed_load": len(addr_agree),
        "zero_count_underflow_observed": len(zero),
        "zero_count_root_cause_proven": False,
        "requires_gralloc_mali_abi_followup": True,
        "hardware_fixed": False,
        "flash_approved": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("report", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.report.stat().st_size > MAX_INPUT:
        raise ValueError("TWRP crash report unexpectedly large")
    report = evaluate(args.report.read_text(errors="replace"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"],
                      "complete": report.get("with_all_required_registers", 0),
                      "flash_approved": False}, indent=2))


if __name__ == "__main__":
    main()
