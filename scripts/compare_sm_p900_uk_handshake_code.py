#!/usr/bin/env python3
"""Compare donor ELF with an *actual known UK10.0* handshake callsite.

A positive exact multi-instruction signature indicates compatible compiled
handshake code ancestry; a negative result says UNKNOWN, not an older API.
Does not patch proprietary code, execute code, or authorize a ROM flash.
"""
import argparse
import hashlib
import json
from pathlib import Path

DONOR_SHA256 = "a00166d28cbd0213c88daadb437534310de09da4bf9fcc64f8e2207e22d76839"
KNOWN_UK10_SHA256 = "a66179ef65c26a797b814e3d9cf0ab2b7f07e0d32c641f463820c0a0c49f1ee9"
# Pinned UK10 native Mali callsite, proven by source-specific disassembly.
UK10_CALLSITE = 0x265e6c
UK10_OPCODES = {
    0x00: ("mov", "r0, #0xa"),
    0x0c: ("mov", "ip, #0"),
    0x18: ("strh", "r0, [sp, #4]"),
    0x28: ("strh", "ip, [sp, #6]"),
}


def elf_text(path, expected_sha):
    from elftools.elf.elffile import ELFFile
    p = Path(path)
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    if sha != expected_sha:
        raise ValueError("Refusing non-pinned proprietary Mali ELF")
    with p.open("rb") as stream:
        elf = ELFFile(stream)
        if elf.elfclass != 32 or elf["e_machine"] != "EM_ARM" or not elf.little_endian:
            raise ValueError("Expected ARM32 little endian ELF")
        section = elf.get_section_by_name(".text")
        if section is None:
            raise ValueError("No .text to inspect")
        return section.data(), int(section["sh_addr"])


def exact_offset_matches(blob, components):
    """Find all byte-for-byte compiled callsite operand patterns by offsets."""
    if not components:
        raise ValueError("Empty instruction pattern")
    components = sorted(components.items())
    first_offset, first_bytes = components[0]
    if first_offset < 0:
        raise ValueError("Invalid offset")
    hits = []
    start = 0
    while len(hits) < 500:
        off = blob.find(first_bytes, start)
        if off < 0:
            break
        anchor = off - first_offset
        if anchor >= 0 and all(
            anchor + rel + len(data) <= len(blob) and
            blob[anchor + rel:anchor + rel + len(data)] == data
            for rel, data in components
        ):
            hits.append(anchor)
        start = off + 1
    return hits


def audit(donor, uk10):
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
    src, addr = elf_text(uk10, KNOWN_UK10_SHA256)
    donor_text, donor_addr = elf_text(donor, DONOR_SHA256)
    decoder = Cs(CS_ARCH_ARM, CS_MODE_ARM)
    # Derive exact known UK10 instruction bytes only *after* validating
    # actual source ELF code, register operands and callsite address.
    parts = {}
    for rel, (mnem, ops) in UK10_OPCODES.items():
        pc = UK10_CALLSITE + rel
        offset = pc - addr
        if not (0 <= offset < len(src) - 4):
            raise ValueError("Known callsite outside source text")
        raw = src[offset:offset + 4]
        decoded = list(decoder.disasm(raw, pc))
        if len(decoded) != 1 or decoded[0].mnemonic != mnem or decoded[0].op_str != ops:
            raise ValueError("Known UK10 callsite does not match pinned evidence")
        parts[rel] = raw
    hits = exact_offset_matches(donor_text, parts)
    return {
        "status": "PINNED_UK10_HANDSHAKE_PATTERN_COMPARED_NO_RUNTIME_ABI_PROOF",
        "donor_elf_sha256": DONOR_SHA256,
        "uk10_elf_sha256": KNOWN_UK10_SHA256,
        "reference_uk10_request": [10, 0],
        "reference_uk10_code_checked": True,
        "donor_exact_uk10_handshake_instruction_pattern_matches": len(hits),
        "donor_virtual_code_offsets": [hex(donor_addr + h) for h in hits],
        "donor_definitely_requests_uk10_at_runtime": False,
        "negative_result_proves_uk5": False,
        "kernel_userspace_abi_compatible": False,
        "requires_call_graph_and_ioctl_validation": True,
        "flash_approved": False,
        "hardware_boot_tested": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("donor", type=Path)
    p.add_argument("uk10", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    r = audit(a.donor, a.uk10)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(r, indent=2) + "\n")
    print(json.dumps({
        "status": r["status"],
        "exact_uk10_code_pattern_count": r["donor_exact_uk10_handshake_instruction_pattern_matches"],
        "flash_approved": False,
    }, indent=2))


if __name__ == "__main__":
    main()
