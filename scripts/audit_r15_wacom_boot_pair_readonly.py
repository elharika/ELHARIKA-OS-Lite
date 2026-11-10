#!/usr/bin/env python3
"""Inspect pinned known-visible-launcher R15 boot and experimental Wacom zImage.

No rewriting, repacking, flashing, or kernel binary publication. Data-only JSON.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

ORIGINAL_SHA = "7d15b15e127e4b31841e1081efac31d2c298c2748dbc5d55889a3e8d45e20d14"
SAMSUNG_TRAILER = b"SEANDROIDENFORCE"

def digest(data):
    return hashlib.sha256(data).hexdigest()

def rounded(x, page):
    return (x + page - 1) // page * page

def inspect_zimage(data):
    # ARM boot protocol: little-endian magic/start/end at offsets 0x24..0x2f.
    # End-start covers the compressed image; appended DTBs are separate bytes.
    if len(data) < 48 or len(data) > 8 * 1024 * 1024:
        raise ValueError("Experimental zImage absent or unexpected geometry")
    magic, start, end = struct.unpack_from("<3I", data, 0x24)
    if magic != 0x016F2818 or end <= start or end - start < 48 or end - start > len(data):
        raise ValueError("Invalid ARM zImage magic or compressed-image bounds")
    return {"compressed_image_bytes": end - start,
            "appended_bytes": len(data) - (end - start)}

def analyze(boot_bytes, zimage_bytes):
    if digest(boot_bytes) != ORIGINAL_SHA:
        raise ValueError("Original R15P0 launcher-bootable BOOT SHA changed")
    if len(boot_bytes) < 48 or len(boot_bytes) > 8 * 1024 * 1024 or boot_bytes[:8] != b"ANDROID!":
        raise ValueError("Not an Android boot image")
    zimage_info = inspect_zimage(zimage_bytes)
    ks, ka, rs, ra, ss, sa, tags, page, version, osv = struct.unpack_from("<10I", boot_bytes, 8)
    if page != 2048 or version != 0 or ss != 0 or ks == 0 or rs == 0:
        raise ValueError("Unexpected legacy Samsung boot header")
    ro = page + rounded(ks, page)
    end = ro + rounded(rs, page)
    if len(boot_bytes) != end + len(SAMSUNG_TRAILER) or boot_bytes[end:] != SAMSUNG_TRAILER:
        raise ValueError("Boot trailer or boundaries differ from known R15 build")
    original_kernel = boot_bytes[page:page + ks]
    ramdisk = boot_bytes[ro:ro + rs]
    if len(original_kernel) != ks or len(ramdisk) != rs:
        raise ValueError("Short kernel or ramdisk")
    # FDT table-like markers are only hints: a bare occurrence is NOT a DTB parse.
    original_fdt = [pos for pos in range(max(0, ks-1048576), ks-3)
                    if original_kernel[pos:pos+4] == b"\xd0\x0d\xfe\xed"]
    new_fdt = [pos for pos in range(max(0, len(zimage_bytes)-1048576), len(zimage_bytes)-3)
               if zimage_bytes[pos:pos+4] == b"\xd0\x0d\xfe\xed"]
    report = {
        "status": "READ_ONLY_PAIR_METADATA_NOT_BOOT_BUILD",
        "original_boot_sha256": ORIGINAL_SHA,
        "original_boot_bytes": len(boot_bytes),
        "original_kernel_sha256": digest(original_kernel),
        "original_kernel_bytes": ks,
        "experimental_kernel_sha256": digest(zimage_bytes),
        "experimental_kernel_bytes": len(zimage_bytes),
        "experimental_arm_zimage_header": zimage_info,
        "kernel_size_delta_bytes": len(zimage_bytes)-ks,
        "legacy_header_page_size": page,
        "kernel_load_address": ka,
        "ramdisk_load_address": ra,
        "tags_load_address": tags,
        "ramdisk_sha256": digest(ramdisk),
        "ramdisk_bytes": rs,
        "samsung_boot_trailer_present": True,
        "old_kernel_fdt_magic_offsets_last_mib": original_fdt,
        "new_kernel_fdt_magic_offsets_last_mib": new_fdt,
        "kernel_payloads_byte_identical": original_kernel == zimage_bytes,
        "zimage_is_standalone_not_boot": True,
        "boot_repacking_proven_safe": False,
        "dtb_structure_validated": False,
        "bootloader_and_rollback_verified_on_device": False,
        "user_spen_drawing_on_prior_rom": "FAIL_FREEZE",
        "user_spen_drawing_on_experimental_kernel": "NOT_TESTED",
        "flash_approved": False,
    }
    return report

def main():
    p = argparse.ArgumentParser()
    p.add_argument("original_boot", type=Path)
    p.add_argument("experimental_zimage", type=Path)
    p.add_argument("--report", required=True, type=Path)
    a=p.parse_args()
    result=analyze(a.original_boot.read_bytes(),a.experimental_zimage.read_bytes())
    a.report.parent.mkdir(exist_ok=True, parents=True)
    a.report.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))

if __name__ == "__main__":
    main()
