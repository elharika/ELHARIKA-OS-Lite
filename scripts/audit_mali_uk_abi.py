#!/usr/bin/env python3
"""Reproduce the exact shipped SM-P900 Mali UK 5.1 initialization audit.

Requires pyelftools and capstone. Read-only; never patches driver version bytes.
This deliberately recognizes one SHA-256 pinned binary, not arbitrary Mali DDks.
Exit 1 means the shipped r15p0 kernel pairing has a proven ABI blocker.
"""
import argparse
import hashlib
import json
from pathlib import Path

PINNED_SHA = '3bc453470f2f6711d463f3fff9b115011cbcefcbb1355be9af147857d892e433'
CHECKS = {
    0x252992: '052701262b46014601aaadf80470adf80660fff732f9',
    0x251c6c: 'b6f800c03846b6f802e002a93d6010220293adf810c0adf812e0fff7afffb0b9029aa2b9bdf810003388834216d0bdf812204ff0ff31308028467280396085f79ae90120b8e7',
    0x251cc8: 'bdf8122071889142e3d8',
}


def audit(path):
    from elftools.elf.elffile import ELFFile
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != PINNED_SHA:
        raise ValueError('Unknown Mali binary; refusing fixed-address interpretation')
    with path.open('rb') as stream:
        elf = ELFFile(stream)
        if elf.elfclass != 32 or not elf.little_endian or elf['e_machine'] != 'EM_ARM':
            raise ValueError('Expected ARM32 little-endian ELF')
        section = elf.get_section_by_name('.text')
        data, base = section.data(), section['sh_addr']
    disassembler = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    evidence = []
    for address, expected_hex in CHECKS.items():
        expected = bytes.fromhex(expected_hex)
        actual = data[address-base:address-base+len(expected)]
        if actual != expected:
            raise ValueError('Unexpected instruction bytes at ' + hex(address))
        decoded = list(disassembler.disasm(actual, address))
        if sum(i.size for i in decoded) != len(actual):
            raise ValueError('Incomplete Thumb decoding')
        evidence.append({'address': hex(address), 'bytes': expected_hex,
                         'instructions': [hex(i.address) + ': ' + i.mnemonic + ' ' + i.op_str
                                          for i in decoded]})
    return {
        'status': 'BLOCKED_MALI_UK_ABI_MISMATCH',
        'binary_sha256': digest,
        'requested_uk_version': [5, 1],
        'kernel_revision': 'de0cdcf10dcca77b400f15d83c1edf4f264a0f02',
        'kernel_driver': 'drivers/gpu/arm/t6xx/r15p0',
        'kernel_supported_major_versions': [6, 7, 8, 9, 10],
        'kernel_response_to_major_5': [10, 6],
        'kernel_evidence': 'mali_kbase_core_linux.c:kbase_api_handshake; mali_kbase_uku.h',
        'interpretation': 'Caller requests 5.1; major mismatch closes fd and fails initialization.',
        'evidence': evidence,
        'limits': 'Static pinned-binary/source audit corroborated by r3 traces; no repaired hardware boot.',
        'remedy_constraint': 'Match complete kernel/userspace ABI; never fake a supported version.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mali_library', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = audit(args.mali_library)
    text = json.dumps(result, indent=2) + '\n'
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text)
    print(text, end='')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
