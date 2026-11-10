#!/usr/bin/env python3
"""Stage a non-installable BOOT candidate with original ramdisk/header and rollback bytes.

Never writes a partition or generates a TWRP installer. Hardware test is separate.
Legacy image-id algorithm follows pinned Lineage mkbootimg ed76fccb92950d0d1fba31cc5777944a5a636c23.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
from zipfile import ZipFile, ZIP_DEFLATED

from audit_mali_boot_pair import parse_boot
from inspect_r15_kernel_baseline import inspect, sha


def image_id(kernel, ramdisk):
    digest = hashlib.sha1()
    for payload in (kernel, ramdisk, b'', b''):  # kernel, ramdisk, second, legacy dt
        digest.update(payload)
        digest.update(struct.pack('<I', len(payload)))
    return digest.digest() + bytes(12)


def repack(original, kernel, expected_kernel_sha):
    if not re.fullmatch('[0-9a-f]{64}', expected_kernel_sha) or sha(kernel) != expected_kernel_sha:
        raise ValueError('Candidate zImage SHA256 differs from authenticated build artifact')
    baseline, _ = inspect(original, kernel)
    if not baseline['same_source_and_config']:
        raise ValueError('Candidate kernel source/config differ from original BOOT')
    before = parse_boot(original)
    page = 2048
    align = lambda n: (n+page-1)//page*page
    ks = before['kernel_bytes']
    rs = before['ramdisk_bytes']
    ro = page + align(ks)
    old_kernel = original[page:page+ks]
    ramdisk = original[ro:ro+rs]
    if original[576:608] != image_id(old_kernel, ramdisk):
        raise ValueError('Original BOOT image-id algorithm not verified')
    header = bytearray(original[:page])
    struct.pack_into('<I', header, 8, len(kernel))
    header[576:608] = image_id(kernel, ramdisk)
    candidate = (bytes(header) + kernel + bytes(align(len(kernel))-len(kernel)) +
                 ramdisk + bytes(align(rs)-rs) + b'SEANDROIDENFORCE')
    after = parse_boot(candidate)
    if before['ramdisk_sha256'] != after['ramdisk_sha256'] or before['boot_header_semantics'] != after['boot_header_semantics'] or before['board_and_cmdline'] != after['board_and_cmdline']:
        raise ValueError('Repacked BOOT altered ramdisk, addresses, board or command line')
    # No unexplained header changes; only kernel_size and the 32-byte image id.
    restored_header = bytearray(candidate[:page])
    restored_header[8:12] = original[8:12]
    restored_header[576:608] = original[576:608]
    if restored_header != original[:page]:
        raise ValueError('Unexpected BOOT header mutation')
    if sha(candidate) == sha(original):
        raise ValueError('Kernel unchanged; no experiment to stage')
    return candidate, dict(status='STAGED_BOOT_CANDIDATE_NOT_DEVICE_TESTED',
                           original=before, candidate=after,
                           kernel_baseline=baseline, ramdisk_unchanged=True,
                           header_addresses_board_cmdline_preserved=True,
                           samsung_trailer_preserved=True, header_image_id_recomputed=True,
                           contains_twrp_installer=False, hardware_tested=False,
                           flash_approved=False)


def stage(original_path, kernel_path, expected_sha, output):
    if output.exists() or output.is_symlink():
        raise ValueError('Output must not exist')
    original = original_path.read_bytes()
    candidate, report = repack(original, kernel_path.read_bytes(), expected_sha)
    entries = {
        'BOOT-CANDIDATE-NOT-DEVICE-TESTED.img': candidate,
        'ORIGINAL-R15P0-BOOT.img': original,
        'comparison.json': (json.dumps(report, indent=2)+'\n').encode(),
        'READ-ME-FIRST.txt': (
            'ENGINEERING STAGING ARCHIVE ONLY. NOT A TWRP UPDATE ZIP.\n'
            'No installer or partition-writing command is included.\n'
            'Candidate retains the exact original R15 ramdisk and header semantics.\n'
            'Only the optional Wacom LCD-frequency feedback was isolated in source.\n'
            'This does not prove the S Pen freeze is fixed. Hardware is untested.\n'
            'Original BOOT bytes are included for engineering rollback preparation.\n'
            'Do not install this ZIP in TWRP or flash an image from it without\n'
            'a separately validated device-specific trial and recovery procedure.\n'
        ).encode(),
    }
    entries['SHA256SUMS'] = ''.join(f'{sha(data)}  {name}\n' for name,data in entries.items()).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, 'x', compression=ZIP_DEFLATED, allowZip64=False) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    with ZipFile(output) as archive:
        if archive.testzip() is not None or set(archive.namelist()) != set(entries):
            raise ValueError('Staged ZIP verification failed')
        for name, data in entries.items():
            if archive.read(name) != data:
                raise ValueError('Staged payload changed')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original_boot', type=Path)
    parser.add_argument('compiled_zimage', type=Path)
    parser.add_argument('--kernel-sha256', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    report = stage(args.original_boot, args.compiled_zimage, args.kernel_sha256, args.output)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
