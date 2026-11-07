#!/usr/bin/env python3
"""Evaluate the actual SM-P900 BootAnimation EGL fault from one tombstone.

Diagnostic only, does not patch proprietary Mali code or modify Android.
"""
import argparse
import json
from pathlib import Path
import re

FAULT_PC = 0x263458
REGISTERS = ("r1", "r2", "r3", "r8")


def parse_tombstone(text):
    if "SIGSEGV" not in text or "eglp_swap_buffers" not in text:
        raise ValueError("Expected BootAnimation Mali crash signature")
    if len(re.findall(r"\bsignal 11\b", text)) != 1:
        raise ValueError("Supply exactly one native SIGSEGV tombstone")
    pcs = [int(s, 16) for s in re.findall(r"\bpc\s+(?:0x)?([0-9a-fA-F]{6,8})\b", text)]
    if FAULT_PC not in pcs:
        raise ValueError("Tombstone not from the confirmed SM-P900 crash PC")
    fault_match = re.search(r"\bfault addr\s+(?:0x)?([0-9a-fA-F]{1,8})\b", text)
    values = {}
    for name in REGISTERS:
        captures = re.findall(r"\b" + name + r"\s+([0-9a-fA-F]{8})\b", text)
        if len(captures) > 1 and len(set(captures)) > 1:
            raise ValueError("Conflicting register snapshots; isolate one crash")
        if captures:
            values[name] = int(captures[0], 16)
    if fault_match is None or not all(x in values for x in REGISTERS):
        return {
            "status": "INCOMPLETE_TOMBSTONE_REGISTERS",
            "registers_present": sorted(values),
            "fault_addr_present": fault_match is not None,
            "crash_pc": f"0x{FAULT_PC:08x}",
            "root_cause_proven": False,
            "flash_approved": False,
        }
    effective = (values["r1"] + (values["r8"] << 4)) & 0xffffffff
    reported = int(fault_match.group(1), 16)
    predicted_r8 = (values["r3"] - 1) & 0xffffffff
    r1_r2_delta = (values["r1"] - values["r2"]) & 0xffffffff
    r3_r1_delta = (values["r3"] - values["r1"]) & 0xffffffff
    r3_r2_delta = (values["r3"] - values["r2"]) & 0xffffffff
    # These offsets are *observed* register relationships, not proven
    # structure member offsets. ARM r3 here looks pointer-like, not a count.
    pointer_window = (r1_r2_delta, r3_r1_delta, r3_r2_delta) == (32, 48, 80)
    return {
        "status": "EGL_INDEXED_READ_REGISTER_CORRELATION",
        "crash_pc": f"0x{FAULT_PC:08x}",
        "register_values": {name: f"0x{values[name]:08x}" for name in REGISTERS},
        "fault_addr": f"0x{reported:08x}",
        "calculated_ldr_address": f"0x{effective:08x}",
        "fault_address_matches_ldr": effective == reported,
        "r8_matches_r3_minus_one": values["r8"] == predicted_r8,
        "zero_count_underflow_observed": values["r3"] == 0 and values["r8"] == 0xffffffff,
        "register_deltas_bytes": {
            "r1_minus_r2": r1_r2_delta,
            "r3_minus_r1": r3_r1_delta,
            "r3_minus_r2": r3_r2_delta,
        },
        "repeating_nearby_pointer_pattern": pointer_window,
        "r3_as_count_proven": False,
        "possible_table_pointer_or_count_corruption": True,
        "root_cause_proven": False,
        "flash_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tombstone", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.tombstone.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("Oversized tombstone")
    report = parse_tombstone(args.tombstone.read_text(errors="replace"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
