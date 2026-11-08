#!/usr/bin/env python3
"""Read-only verifier for two *exact* Samsung SM-P900 experimental boot artifacts.

This does not establish hardware compatibility or authorize flashing.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from zipfile import ZipFile

ORIGINAL_SHA = "7d15b15e127e4b31841e1081efac31d2c298c2748dbc5d55889a3e8d45e20d14"
R7P0_SHA = "8ea5680c61359867f848efd44bdef2175bc9106efb249c0bef4d22ee4c17656e"
TRAILER = b"SEANDROIDENFORCE"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def parse_boot(blob):
    if len(blob) < 2048 or len(blob) > 8388608 or blob[:8] != b"ANDROID!":
        raise ValueError("Invalid SM-P900 Android boot image size or magic")
    kernel_size, k_addr, ramdisk_size, r_addr, second_size, s_addr, tags, page_size, version, os_version = struct.unpack_from('<10I', blob, 8)
    if page_size != 2048 or version != 0 or second_size != 0 or not kernel_size or not ramdisk_size:
        raise ValueError("Unexpected SM-P900 boot header")
    align = lambda n: ((n + page_size - 1) // page_size) * page_size
    ramdisk_pos = page_size + align(kernel_size)
    end = ramdisk_pos + align(ramdisk_size)
    if len(blob) != end + len(TRAILER) or blob[end:] != TRAILER:
        raise ValueError("Incorrect Samsung trailer or boot payload bounds")
    return {
        "image_sha256": digest(blob),
        "image_bytes": len(blob),
        "kernel_sha256": digest(blob[page_size:page_size + kernel_size]),
        "kernel_bytes": kernel_size,
        "ramdisk_sha256": digest(blob[ramdisk_pos:ramdisk_pos + ramdisk_size]),
        "ramdisk_bytes": ramdisk_size,
        "boot_header_semantics": [k_addr, r_addr, s_addr, tags, page_size, version, os_version],
        "board_and_cmdline": digest(blob[48:576] + blob[608:1632]),
    }


def load_archive(path):
    with ZipFile(path) as z:
        if z.testzip() is not None:
            raise ValueError("ZIP entry corrupted: " + str(path))
        names = z.namelist()
        if names.count('boot.img') != 1 or names.count('SHA256SUMS') != 1:
            raise ValueError("Expected exactly one boot.img and SHA256SUMS")
        blob = z.read('boot.img')
        expected_line = f"{digest(blob)}  boot.img"
        if expected_line not in z.read('SHA256SUMS').decode().splitlines():
            raise ValueError("Manifest SHA256 mismatch")
        return parse_boot(blob)


def audit(original, candidate):
    before, after = load_archive(original), load_archive(candidate)
    if before['image_sha256'] != ORIGINAL_SHA or after['image_sha256'] != R7P0_SHA:
        raise ValueError("Unexpected boot artifacts; exact pinned images only")
    if before['ramdisk_sha256'] != after['ramdisk_sha256']:
        raise ValueError("Ramdisk changed unexpectedly")
    if before['boot_header_semantics'] != after['boot_header_semantics']:
        raise ValueError("Boot addresses/layout changed")
    if before['board_and_cmdline'] != after['board_and_cmdline']:
        raise ValueError("Board or boot command line changed")
    if before['kernel_sha256'] == after['kernel_sha256']:
        raise ValueError("Kernel did not change")
    return {
        'status': 'ARTIFACT_PAIR_STATIC_VALIDATION_PASSED',
        'model': 'SM-P900/v1awifi',
        'before': before,
        'candidate': after,
        'ramdisk_unchanged': True,
        'boot_cmdline_unchanged': True,
        'kernel_changed': True,
        'flash_approved': False,
        'hardware_boot_tested': False,
        'notes': [
            'This verifies byte-level package consistency, not current tablet partition state.',
            'Mali UK10 userspace / r7p0 kernel runtime compatibility is not proven.',
            'No TWRP flash is authorized by this report; preserve a verified recovery path first.',
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('original', type=Path)
    p.add_argument('candidate', type=Path)
    p.add_argument('--report', required=True, type=Path)
    x = p.parse_args()
    result = audit(x.original, x.candidate)
    x.report.parent.mkdir(parents=True, exist_ok=True)
    x.report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
