#!/usr/bin/env python3
"""Package a TWRP diagnostics-only ZIP to save the existing R7/UK10 pair.

NO BOOT/SYSTEM installation code is present. All binary backups are created
locally by the device's TWRP and remain in the user's own external microSD.
"""
import hashlib
import re
import subprocess
import sys
import zipfile
from pathlib import Path

SCRIPT = "diagnostics/twrp-backup-current-r7-uk10-before-r15-trial.sh"
ZIP = "ELHARIKA-SM-P900-R7P0-UK10-VERIFIED-BACKUP-ONLY-TWRP.zip"
README = """SM-P900 verified pre-r15 trial backup: R7P0 BOOT + UK10 Mali

This is a recovery BACKUP tool, NOT a ROM or trial flasher.
There are NO filesystem/partition writes except a new directory on external microSD.

Requires:
- TWRP product v1awifi and P900 bootloader
- Mount System READ ONLY and Micro SDCard from TWRP > Mount
- At least 128 MiB free on Micro SDCard
- Current BOOT SHA256 (5,437,456 bytes) f5f60b64...
- Current installed /system/vendor/lib/egl/libGLES_mali.so SHA256 34af399a...

To execute: TWRP > Install > this ZIP file.
Look in external Micro SDCard folder ELHARIKA-R7P0-UK10-BACKUP-01/
(or a later unused number).
Only a SUCCESSFUL and VERIFIED backup folder contains ALL 3 files:
1. BOOT.full-8MiB.backup (8,388,608 bytes, complete BOOT partition)
2. libGLES_mali.UK10.original.backup (original 27 MB Mali ELF)
3. VERIFIED_BACKUP.txt (small textual SHA256 report)
Do not rename, delete or lose either binary; the TXT alone cannot restore.

Send only VERIFIED_BACKUP.txt to diagnose readiness for a reversible paired
r15p0 hardware trial. No paired trial is installed by this ZIP.
If the installer aborts, retain any hidden staging folder as incomplete and
do not treat it as a verified backup. No Wipe, Format or Restore needed.
"""
REQUIRED = (
    "BOOT_LINK=/dev/block/platform/dw_mmc.0/by-name/BOOT",
    "MALI=/system/vendor/lib/egl/libGLES_mali.so",
    "CURRENT_BOOT_SHA=f5f60b64a023b5223d7af711bfbe239dc79248f9cded878cd17e034751594eb0",
    "CURRENT_MALI_SHA=34af399a1090295a7138297b9354c73d569212a4bd11be4b3254dafe26cde",
    "FULL_BOOT_BYTES=8388608",
    'head -c "$FULL_BOOT_BYTES" "$BOOT" > "$STAGE/BOOT.full-8MiB.backup"',
    'cat "$MALI_REAL" > "$STAGE/libGLES_mali.UK10.original.backup"',
    'mv "$STAGE" "$FINAL"',
    "backup_verified=YES",
    "flash_approved=NO",
)
DANGER = re.compile(
    r"(?m)^\s*(?:mount|umount|reboot|dd|flash_image|mkfs(?:\.\w+)?|"
    r"fastboot|odin|setprop|chmod|chown|chcon|restorecon|blockdev\s+--set)\b"
)


def inspect(script):
    if not script.startswith("#!/sbin/sh\n"):
        raise ValueError("TWRP script header missing")
    for line in REQUIRED:
        if line not in script:
            raise ValueError("Missing backup safety preflight: " + line)
    if DANGER.search(script):
        raise ValueError("Backup script contains a forbidden mutating command")
    for line in script.splitlines():
        if line.lstrip().startswith("#"):
            continue
        if re.search(r"(?:>|>>)\s*['\"]?(?:/dev/block|/system/|/vendor/|/data/)", line):
            raise ValueError("Attempted protected partition write")
    subprocess.run(["sh", "-n"], input=script, text=True, check=True, timeout=10)


def package(root, target):
    root, target = Path(root), Path(target)
    script = (root / SCRIPT).read_text()
    inspect(script)
    target.mkdir(parents=True, exist_ok=True)
    path = target / ZIP
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename, data, is_exe in (
            ("META-INF/com/google/android/update-binary", script, True),
            ("META-INF/com/google/android/updater-script", "# Read-only backup only\n", False),
            ("README.txt", README, False),
        ):
            item = zipfile.ZipInfo(filename, (2026, 11, 7, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.create_system = 3
            item.external_attr = (0o100755 if is_exe else 0o100644) << 16
            archive.writestr(item, data.encode())
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == 3
        assert all("boot.img" not in f and ".so" not in f for f in archive.namelist())
        updater = archive.getinfo("META-INF/com/google/android/update-binary")
        assert updater.external_attr >> 16 & 0o111 == 0o111
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    (target / "SHA256SUMS.txt").write_text(f"{sha}  {ZIP}\n")
    return {"name": ZIP, "sha256": sha, "bytes": path.stat().st_size,
            "no_partition_writes": True, "flash_approved": False}


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: package_sm_p900_pretrial_backup.py REPO_ROOT OUTPUT_DIR")
    print(package(sys.argv[1], sys.argv[2]))
