#!/usr/bin/env python3
"""Fail-closed review of tiny SM-P900 R7P0 BOOT + UK10 Mali backup report.

A matching report is only evidence that device recovery *reported* writing and
hashing the backup files to the owner's microSD. It is NOT proof that a restore
would succeed after power loss, NOR permission to flash the R15P0 experiment.
"""
import argparse
import json
from pathlib import Path
import re

HEADER = "ELHARIKA SM-P900 R7P0 UK10 VERIFIED DUAL BACKUP V1"
CURRENT_BOOT_SHA = "f5f60b64a023b5223d7af711bfbe239dc79248f9cded878cd17e034751594eb0"
CURRENT_MALI_SHA = "34af399a1090295a7138297b9352334c73d569212a4bd11be4b3254dafe26cde"
MAX_LENGTH = 16384


def parse(content):
    if not content.startswith(HEADER + "\n"):
        raise ValueError("Unknown or incomplete recovery report")
    record = {}
    for line in content.splitlines()[1:]:
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in record:
            raise ValueError("Duplicated field " + key)
        record[key] = value
    expected = {
        "device": "v1awifi",
        "bootloader_family": "P900",
        "boot_source_image_sha256": CURRENT_BOOT_SHA,
        "boot_partition_backup_bytes": "8388608",
        "boot_partition_backup_image_prefix_sha256": CURRENT_BOOT_SHA,
        "mali_source_path": "/system/vendor/lib/egl/libGLES_mali.so",
        "mali_backup_sha256": CURRENT_MALI_SHA,
        "backup_image": "BOOT.full-8MiB.backup",
        "backup_mali": "libGLES_mali.UK10.original.backup",
        "backup_verified": "YES",
        "rollback_tested_on_device": "NO",
        "boot_partition_modified": "NO",
        "system_partition_modified": "NO",
        "data_partition_modified": "NO",
        "flash_approved": "NO",
    }
    for name, value in expected.items():
        if record.get(name) != value:
            raise ValueError("Mismatching or absent guard: " + name)
    full_sha = record.get("boot_partition_backup_sha256", "")
    if not re.fullmatch("[0-9a-f]{64}", full_sha):
        raise ValueError("No valid full BOOT backup hash")
    path = record.get("mali_source_real_path", "")
    if not path.startswith(("/system/", "/system_root/", "/vendor/")) or ".." in path:
        raise ValueError("Invalid Mali source path")
    return {
        "status": "USER_RECOVERY_BACKUP_REPORT_PASSES_STATIC_CONSISTENCY",
        "model": "Samsung SM-P900/v1awifi",
        "boot_prefix_sha256": CURRENT_BOOT_SHA,
        "backup_full_boot_sha256": full_sha,
        "mali_sha256": CURRENT_MALI_SHA,
        "backup_report_contains_hashes": True,
        "backups_independently_rehashed_off_device": False,
        "rollback_tested_on_physical_device": False,
        "recommended_next_gate":
            "keep full backed-up files on microSD; verify restore program and paired r15 candidates offline",
        "install_approved": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("report", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if not 0 < a.report.stat().st_size < MAX_LENGTH:
        raise ValueError("Invalid report size")
    result = parse(a.report.read_text(errors="replace"))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
