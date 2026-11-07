#!/usr/bin/env python3
"""Package a tiny *read-only* SM-P900 TWRP crash evidence collector.

Unlike a ROM update, this ZIP NEVER opens or mounts BOOT/SYSTEM/DATA raw
partitions, changes SELinux labels, or invokes Android. It reads existing
/data/tombstones after the user mounts Data through TWRP and writes ONE
small sanitized text file to an explicitly mounted microSD.
"""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import zipfile

SCRIPT = "diagnostics/twrp-export-existing-egl-tombstones.sh"
ZIPNAME = "ELHARIKA-SM-P900-READONLY-EGL-TOMBSTONES-TWRP.zip"
README = """ELHARIKA OS Lite SM-P900 — READ ONLY EGL TOMBSTONE EXPORT

This ZIP does NOT flash, repartition, change a ROM, mount partitions, reboot,
wipe, chmod, chown, execute Android code, or replace installed libraries.
It only scans existing Android native crash reports in Data.

1. In TWRP > Mount, check Data and Micro SDCard (if accessible).
2. TWRP > Install: choose this diagnostic ZIP from the Micro SDCard.
3. After it says "Read-only EGL scan completed", look in Micro SDCard:
   elharika-egl-crash-registers.txt
   If an older report (even an empty one) exists, the new output uses
   elharika-egl-crash-registers-01.txt, -02.txt etc. up to -10.txt.
   The screen prints the exact new report path and verified SHA256.
4. Send ONLY the NEW nonempty .txt report for Mali/eglSwapBuffers diagnosis.

If no matching tombstone was found, a nonempty text report will say so.
If Data is not mounted, the script stops before writing a report.
Old tombstones may have been removed or rotated.
The report is staged on microSD, checked for nonempty content and matching
SHA256, and then renamed. Old output files are never overwritten.
Do NOT format, wipe, reflash BOOT, or reinstall system.img.
This read-only tool is NOT a fix for the black screen.
"""


def validate_script(script):
    if not script.startswith("#!/sbin/sh\n"):
        raise ValueError("Expected TWRP shell interpreter")
    for required in (
        "getprop ro.product.device", "getprop ro.bootloader",
        "egl p", # replaced by explicit matcher below
    ):
        if required == "egl p":
            if "eglp_swap_buffers" not in script:
                raise ValueError("Missing EGL crash signature")
        elif required not in script:
            raise ValueError("Missing device guard " + required)
    for forbidden in (
        r"(?m)^\s*(?:mount|umount|dd|mkfs|reboot|flash_image|setprop|chcon|chmod|chown)\s",
        r"(?m)^\s*(?:rm|mv|cp)\s+.*(?:/system|/dev/block|/data)",
        r"(?m)^\s*.*(?:/dev/block|/proc/sysrq-trigger)",
        r"(?m)^\s*.*(?:eval|source)\s",
    ):
        if re.search(forbidden, script):
            raise ValueError("Unsafe diagnostic command: " + forbidden)
    subprocess.run(["sh", "-n"], input=script, text=True,
                   check=True, timeout=15)


def package(root, destination):
    root = Path(root)
    script = (root / SCRIPT).read_text()
    validate_script(script)
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / ZIPNAME
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, data, executable in (
            ("META-INF/com/google/android/update-binary", script, True),
            ("META-INF/com/google/android/updater-script", "# Read-only evidence exporter\n", False),
            ("README.txt", README, False),
        ):
            info = zipfile.ZipInfo(name, (2026, 11, 7, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100755 if executable else 0o100644) << 16
            bundle.writestr(info, data.encode())
    with zipfile.ZipFile(target) as bundle:
        if bundle.testzip() is not None:
            raise ValueError("Invalid diagnostic ZIP CRC")
        updater = bundle.getinfo("META-INF/com/google/android/update-binary")
        if ((updater.external_attr >> 16) & 0o111) != 0o111:
            raise ValueError("TWRP update-binary was not packaged executable")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    (destination / "SHA256SUMS.txt").write_text(f"{digest}  {ZIPNAME}\n")
    return {"name": ZIPNAME, "size": target.stat().st_size, "sha256": digest,
            "intent": "READ_ONLY_TOMBSTONE_EXPORT", "flash_approved": False}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    print(package(a.root, a.output))
