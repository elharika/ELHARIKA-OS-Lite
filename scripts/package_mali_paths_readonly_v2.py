#!/usr/bin/env python3
"""Package tiny non-flashing SM-P900 TWRP System/Mali path diagnosis."""
from pathlib import Path
import hashlib
import re
import subprocess
import sys
import zipfile

SCRIPT = "diagnostics/twrp-mali-system-paths-readonly-v2.sh"
ZIPNAME = "ELHARIKA-SM-P900-MALI-SYSTEM-PATHS-READONLY-V2-TWRP.zip"
README = """SM-P900 read-only Mali path / System mount diagnostic v2

This tiny package does NOT flash BOOT, replace libGLES_mali.so, write System,
format Data, or reboot the tablet. It only reads already-mounted paths and
saves a sanitized TXT report on external microSD.

TWRP > Mount > Micro SDCard and System (prefer read-only; DO NOT FORMAT).
TWRP > Install > select THIS diagnostic ZIP.
Look on external microSD for:
  elharika-mali-paths-report.txt
or elharika-mali-paths-report-01.txt etc if a prior report exists.
Send the TXT report for checking. If no known System mount is visible, enable
System in TWRP > Mount and retry. No Android boot, wipe or restore necessary.
"""

GUARDS = (
    "getprop ro.product.device",
    "getprop ro.bootloader",
    "NO_RECOGNIZED_SYSTEM_MOUNT",
    "KNOWN_SYSTEM_OR_VENDOR_MOUNT_VISIBLE",
    "readlink -f",
    'MALI_STATUS=TESTED_R7P0_UK10_LIBRARY',
    'MALI_STATUS=OLDER_UK5_MISMATCH',
    'MALI_STATUS=PINNED_R15P0_DONOR_LIBRARY',
    'STAGED=$(mktemp "$SD/.elharika-mali-path-stage.XXXXXX")',
    'cat "$TMP" > "$STAGED"',
    'mv "$STAGED" "$TARGET"',
    "boot_partition_modified=NO",
    "system_partition_modified=NO",
    "flash_approved=NO",
)
DANGEROUS = re.compile(
    r"(?m)^\s*(?:dd|mount|umount|reboot|flash_image|mkfs(?:\.\w+)?|"
    r"fastboot|odin|setprop|chmod|chown|chcon|restorecon|blockdev)\s"
)


def validate(source):
    if not source.startswith("#!/sbin/sh\n"):
        raise ValueError("Not executable TWRP script")
    for x in GUARDS:
        if x not in source:
            raise ValueError("Missing fail-closed guard: " + x)
    if DANGEROUS.search(source):
        raise ValueError("Read-only guarantee broken")
    if re.search(r"(?m)^\s*(?:cat|head)\b[^\n]*>\s*['\"]?(?:/system|/vendor|/dev/block)", source):
        raise ValueError("Potential partition write")
    subprocess.run(["sh", "-n"], input=source, text=True, check=True, timeout=10)


def package(root, output):
    root, output = Path(root), Path(output)
    script = (root / SCRIPT).read_text()
    validate(script)
    output.mkdir(parents=True, exist_ok=True)
    target = output / ZIPNAME
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as bundle:
        for name, source, executable in (
            ("META-INF/com/google/android/update-binary", script, True),
            ("META-INF/com/google/android/updater-script", "# Diagnostic only\n", False),
            ("README.txt", README, False),
        ):
            item = zipfile.ZipInfo(name, (2026, 11, 7, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.create_system = 3
            item.external_attr = (0o100755 if executable else 0o100644) << 16
            bundle.writestr(item, source.encode())
    with zipfile.ZipFile(target) as z:
        if z.testzip() is not None:
            raise ValueError("Bad ZIP CRC")
        executable = z.getinfo("META-INF/com/google/android/update-binary")
        if (executable.external_attr >> 16) & 0o111 != 0o111:
            raise ValueError("Updater permissions invalid")
        if any("boot.img" in path or "libGLES_mali.so" in path for path in z.namelist()):
            raise ValueError("Installer contains a flashable component")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    (output / "SHA256SUMS.txt").write_text(f"{digest}  {ZIPNAME}\n")
    return {"name": ZIPNAME, "size": target.stat().st_size, "sha256": digest,
            "status": "READ_ONLY_REPORT_ONLY", "flash_approved": False}


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: package_mali_paths_readonly_v2.py ROOT OUT")
    print(package(sys.argv[1], sys.argv[2]))
