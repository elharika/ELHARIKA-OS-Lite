#!/usr/bin/env python3
"""Compare exact pinned UK10 source ELF build ID to SM-P900 crash BuildId.

Forensic metadata only. Emits restricted ARM context around the fault and
nearby caller; never changes, republishes, or injects the proprietary blob.
"""
import argparse
import hashlib
import json
from pathlib import Path

PINNED_SHA256 = "a66179ef65c26a797b814e3d9cf0ab2b7f07e0d32c641f463820c0a0c49f1ee9"
DEVICE_BUILD_ID = "1b2949cf031b30f20a970c511925875d"
CRASH_PC = 0x263458
CALLER_PC = 0x476210
ARM_CODE = {
    0x26344C: ("ldmib", "r2, {r1, r3}"),
    0x263450: ("sub", "r8, r3, #1"),
    0x263458: ("ldr", "r1, [r1, r8, lsl #4]"),
}


def build_id_of(elf):
    for section in elf.iter_sections():
        if not hasattr(section, "iter_notes"):
            continue
        for entry in section.iter_notes():
            if entry["n_type"] == "NT_GNU_BUILD_ID" and entry["n_name"] == "GNU":
                val = entry["n_desc"]
                return val.hex() if isinstance(val, bytes) else str(val).lower()
    return None


def decode_at(data, start, centre, before=8, after=8):
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
    if not (start <= centre - before * 4 and centre + after * 4 < start + len(data)):
        raise ValueError("Requested PC outside executable section")
    decoder = Cs(CS_ARCH_ARM, CS_MODE_ARM)
    window_start = centre - before * 4
    offset = window_start - start
    seq = list(decoder.disasm(data[offset:offset + (before + after + 1) * 4], window_start))
    if len(seq) != before + after + 1 or any(x.size != 4 for x in seq):
        raise ValueError("Incomplete ARM32 instruction context")
    return seq


def audit(path):
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != PINNED_SHA256:
        raise ValueError("Refusing unpinned Mali blob")
    from elftools.elf.elffile import ELFFile
    with path.open("rb") as binary:
        elf = ELFFile(binary)
        if elf.elfclass != 32 or not elf.little_endian or elf["e_machine"] != "EM_ARM":
            raise ValueError("Unexpected candidate architecture")
        got_build_id = build_id_of(elf)
        if not got_build_id:
            raise ValueError("No ELF GNU BuildId: cannot compare crash binary")
        text = elf.get_section_by_name(".text")
        if text is None:
            raise ValueError("Missing .text")
        code = text.data()
        base = int(text["sh_addr"])
        low = decode_at(code, base, CRASH_PC, 8, 8)
        for addr, (op, arg) in ARM_CODE.items():
            item = next((i for i in low if i.address == addr), None)
            if item is None or item.mnemonic != op or item.op_str != arg:
                raise ValueError("Pinned ARM opcode pattern changed at critical PC")
        # A small window around the distinct EGL caller frame. The caller
        # backtrace is not proof of which exact BL site preceded the crash.
        high = decode_at(code, base, CALLER_PC, 5, 5)
        indexed_instruction = next(i for i in low if i.address == CRASH_PC)
        return {
            "status": "PINNED_SOURCE_BINARY_METADATA_CHECKED",
            "sha256": digest,
            "candidate_build_id": got_build_id,
            "device_crash_build_id": DEVICE_BUILD_ID,
            "candidate_build_id_matches_device": got_build_id == DEVICE_BUILD_ID,
            "build_id_does_not_replace_deployed_sha": True,
            "fault_pc": f"0x{CRASH_PC:08x}",
            "faulting_instruction": {
                "mnemonic": indexed_instruction.mnemonic,
                "operands": indexed_instruction.op_str,
            },
            "pre_fault_context": [
                {"pc": f"0x{x.address:08x}", "opcode": x.mnemonic, "operands": x.op_str}
                for x in low if x.address < CRASH_PC
            ],
            "caller_pc": f"0x{CALLER_PC:08x}",
            "caller_context": [
                {"pc": f"0x{x.address:08x}", "opcode": x.mnemonic, "operands": x.op_str}
                for x in high
            ],
            "caller_frame_is_separate_from_fault": True,
            "observed_device_register_pattern": {
                "sample_count": 5,
                "r1_minus_r2_bytes": 32,
                "r3_minus_r1_bytes": 48,
                "r8_is_r3_minus_one": True,
                "fault_address_matches_indexed_read_all_samples": True,
            },
            "independent_execution_path_proven": False,
            "root_cause_proven": False,
            "hardware_boot_verified": False,
            "flash_approved": False,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.candidate)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
