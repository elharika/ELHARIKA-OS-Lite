#!/usr/bin/env python3
"""Package one read-only, non-ROM SM-P900 TWRP preflight ZIP.

This tiny diagnostic can never flash, mount, remount, erase, install a kernel,
or replace Android libraries. All output is a named microSD text report.
"""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import zipfile

SCRIPT = "diagnostics/twrp-r15p0-pair-readonly-preflight.sh"
ZIPNAME = "ELHARIKA-SM-P900-R15P0-READONLY-PAIR-PREFLIGHT-TWRP.zip"
README = """ELHARIKA OS Lite: SM-P900 r15p0 / r7p0 matching READ-ONLY preflight

NOT AN ANDROID ROM. DOES NOT FLASH OR RESTART ANDROID.
Does not mount, unmount, format, write BOOT, SYSTEM or DATA, or modify Mali.

1. In TWRP > Mount: select Micro SDCard.
2. To read Mali library too, mount System READ ONLY (uncheck any writable mount).
3. TWRP > Install: choose this INNER ZIP.
4. The report is in microSD:
      elharika-r15-matched-pair-preflight.txt
   or -01.txt, -02.txt, etc if previous report exists.
5. Send the NEW report here for fingerprint confirmation.
If 'MALI: NOT_VISIBLE_MOUNT_SYSTEM_READ_ONLY', you can rerun after mounting
System read-only; no wipe, no reflash and no additional boot necessary.

This report is useful only as a preflight. It cannot establish GPU compatibility
or certify a flash image.
"""

SENTINELS = (
    "getprop ro.product.device",
    "getprop ro.bootloader",
    "f5f60b64a023b5223d7af711bfbe239dc79248f9cded878cd17e034751594eb0",
    "7d15b15e127e4b31841e1081efac31d2c298c2748dbc5d55889a3e8d45e20d14",
    "34af399a1090295a7138297b9352334c73d569212a4bd11be4b3254dafe26cde",
    "3bc453470f2f6711d463f3fff9b115011cbcefcbb1355be9af147857d892e433",
    "a00166d28cbd0213c88daadb437534310de09da4bf9fcc64f8e2207e22d76839",
    "boot_partition_modified=NO",
    "system_partition_modified=NO",
    "flash_approved=NO",
    'head -c "$R15_SIZE" "$BOOT" > "$BOOT_TEMP"',
    'head -c "$R7_SIZE" "$BOOT_TEMP" > "$TMP"',
    'cat "$TMP" > "$STAGED"',
    'mv "$STAGED" "$TARGET"',
)
DANGEROUS_LINES = re.compile(
    r"(?m)^\s*(?:mount|umount|reboot|dd|flash_image|mkfs(?:\.\w+)?|"
    r"fastboot|odin|setprop|chmod|chown|chcon|restorecon|blockdev)\s"
)


def verify(source):
    if not source.startswith("#!/sbin/sh\n"):
        raise ValueError("Not a TWRP shell script")
    for required in SENTINELS:
        if required not in source:
            raise ValueError("Missing preflight guard: " + required)
    if DANGEROUS_LINES.search(source):
        raise ValueError("Unsafe command found in read-only collector")
    if re.search(r"(?m)^\s*(?:cat|head)\b[^\n]*>\s*\"\$BOOT\"", source):
        raise ValueError("Possible BOOT partition write")
    if re.search(r"(?m)^\s*(?:cat|head)\b[^\n]*>\s*\"\$MALI_PATH\"", source):
        raise ValueError("Possible vendor library overwrite")
    subprocess.run(["sh", "-n"], input=source, text=True, timeout=10, check=True)


def package(root, output):
    root, output = Path(root), Path(output)
    source = (root / SCRIPT).read_text()
    verify(source)
    output.mkdir(parents=True, exist_ok=True)
    target = output / ZIPNAME
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, payload, executable in (
            ("META-INF/com/google/android/update-binary", source, True),
            ("META-INF/com/google/android/updater-script",
             "# Read-only preflight, no system modifications\n", False),
            ("README.txt", README, False),
        ):
            info = zipfile.ZipInfo(name, (2026, 11, 7, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (0o100755 if executable else 0o100644) << 16
            z.writestr(info, payload.encode())
    with zipfile.ZipFile(target) as z:
        if z.testzip() is not None:
            raise ValueError("ZIP CRC verification failed")
        updater = z.getinfo("META-INF/com/google/android/update-binary")
        if (updater.external_attr >> 16) & 0o111 != 0o111:
            raise ValueError("TWRP update-binary not executable")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    (output / "SHA256SUMS.txt").write_text(f"{digest}  {ZIPNAME}\n")
    return {"sha256": digest, "size": target.stat().st_size,
            "readonly": True, "flash_approved": False}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("out", type=Path)
    x = p.parse_args()
    print(package(x.root, x.out))
