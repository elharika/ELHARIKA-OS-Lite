#!/usr/bin/env python3
"""Package pinned SM-P900 r15 matched-pair experimental TWRP install + r7 restore.

NO user-supplied/manual backup prerequisite. Contains two independent whole
paired ZIPs with strict start-state SHA checks and in-process undo on error.
This is experimental hardware-unverified software; never claim fixed boot.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "installer/r15p0-paired-update-binary.in"
COMPONENTS = {
    "r7_boot": (5437456, "f5f60b64a023b5223d7af711bfbe239dc79248f9cded878cd17e034751594eb0"),
    "old_mali": (24554805, "34af399a1090295a7138297b9352334c73d569212a4bd11be4b3254dafe26cde"),
    "r15_boot": (5462032, "7d15b15e127e4b31841e1081efac31d2c298c2748dbc5d55889a3e8d45e20d14"),
    "r15_mali": (26858432, "a00166d28cbd0213c88daadb437534310de09da4bf9fcc64f8e2207e22d76839"),
}
INSTALL = "ELHARIKA-SM-P900-R15P0-PAIRED-INSTALL-EXPERIMENTAL.zip"
RESTORE = "ELHARIKA-SM-P900-R7P0-UK10-PAIRED-RESTORE.zip"
README = """ELHARIKA OS Lite — Samsung SM-P900 only

TWO INDEPENDENT TWRP ZIPs:
1. R15P0-PAIRED-INSTALL-EXPERIMENTAL: flashes source-pinned BOOT r15p0
   and proprietary Mali r15p0 TOGETHER, ONLY from exactly diagnosed r7p0/UK10.
2. R7P0-UK10-PAIRED-RESTORE: restores the earlier known r7p0+UK10 pair
   if the R15 trial yields the same black screen; the old pair was already
   BLACK-SCREENED, so this is not a working Android ROM.

NO MANUAL USER BACKUP IS REQUIRED by the installer, per owner's request.
The installer keeps short-lived on-microSD undo bytes and tries to restore
both pieces if a same-session write fails. Sudden power loss can still leave
partial writes. Recovery/TWRP must remain available to use the RESTORE ZIP.

REQUIRED: battery >=50%, external microSD >=128 MiB free, TWRP Mount >
UNSELECT System (otherwise installer aborts), stable power.
Only on Samsung SM-P900 (v1awifi). No wipe, Data or Recovery modification.
Never extract the internal BOOT or Mali and flash separately.

These ZIPs have NOT been tested on real hardware. Successful checksum
verification is not proof EGL, GPU or launcher works. If INSTALL succeeds
but screen remains black, return to TWRP and run RESTORE instead of retrying
the same INSTALL ZIP.
"""


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def verify_source_files(files):
    for key, (size, digest) in COMPONENTS.items():
        path = Path(files[key])
        if path.stat().st_size != size or sha256_file(path) != digest:
            raise ValueError(f"Incorrect exact pinned source {key}")
        with path.open("rb") as fh:
            signature = fh.read(20)
        if key.endswith("_boot") and not signature.startswith(b"ANDROID!"):
            raise ValueError(f"Bad Android BOOT header: {key}")
        if key.endswith("mali") and not signature.startswith(b"\x7fELF\x01\x01"):
            raise ValueError(f"Not ARM32 Mali ELF: {key}")
    with Path(files["r15_mali"]).open("rb") as f:
        if b"U:r15p0-00rel0" not in f.read():
            raise ValueError("Pinned donor Mali DDK version banner changed")
    return True


def updater_for(mode):
    if mode not in ("INSTALL", "RESTORE"):
        raise ValueError("Invalid paired mode")
    boot_key = "r15_boot" if mode == "INSTALL" else "r7_boot"
    mali_key = "r15_mali" if mode == "INSTALL" else "old_mali"
    boot_bytes, boot_sha = COMPONENTS[boot_key]
    _, mali_sha = COMPONENTS[mali_key]
    src = TEMPLATE.read_text()
    for key, value in (
        ("@MODE@", mode),
        ("@TARGET_BOOT_SHA@", boot_sha),
        ("@TARGET_BOOT_BYTES@", str(boot_bytes)),
        ("@TARGET_MALI_SHA@", mali_sha),
    ):
        if src.count(key) != 1:
            raise ValueError(f"Wrong installer template marker {key}")
        src = src.replace(key, value)
    if "@" + "MODE@" in src:
        raise ValueError("Leftover substitution")
    if not src.startswith("#!/sbin/sh\n"):
        raise ValueError("Invalid TWRP update-binary")
    # Script deliberately writes only to the resolved BOOT block and existing
    # Mali inode. No Data, recovery, system image replacement or bootloader.
    for critical in (
        "BOOT=$(readlink -f /dev/block/platform/dw_mmc.0/by-name/BOOT)",
        "SYSTEM=$(readlink -f /dev/block/platform/dw_mmc.0/by-name/SYSTEM)",
        'cat "$WORK/new-mali.so" > "$ELF"',
        'dd if="$WORK/new-boot.img" of="$BOOT" bs=1048576',
        "WRITING=1", "COMMITTED=1", "getprop ro.product.device",
        "ro.build.version.sdk=30", "PREV_BOOT_SHA",
    ):
        if critical not in src:
            raise ValueError(f"Critical paired flash safeguard missing: {critical}")
    subprocess.run(["sh", "-n"], input=src, text=True, check=True, timeout=10)
    return src


def build_one(mode, files, target):
    install = mode == "INSTALL"
    boot_key = "r15_boot" if install else "r7_boot"
    mali_key = "r15_mali" if install else "old_mali"
    filename = INSTALL if install else RESTORE
    updater = updater_for(mode)
    meta = {
        "status": "EXPERIMENTAL_TWRP_PAIRED_INSTALL_HW_UNTESTED" if install
                  else "TWRP_PAIRED_RESTORE_TO_PREVIOUS_BLACKSCREEN_PAIR",
        "device": "SM-P900 / v1awifi",
        "operation": mode,
        "installed_boot_sha256": COMPONENTS[boot_key][1],
        "installed_mali_sha256": COMPONENTS[mali_key][1],
        "original_r7_boot_sha256": COMPONENTS["r7_boot"][1],
        "original_uk10_mali_sha256": COMPONENTS["old_mali"][1],
        "r15_donor_elf_DDK": "U:r15p0-00rel0",
        "no_manual_backup_required": True,
        "temporary_in_process_undo": True,
        "physical_boot_tested": False,
        "known_current_android_display": "BLACK_SCREEN",
        "risk_note": "Not guaranteed. An interrupted flash may require recovery.",
        "writes_partitions": ["BOOT", "SYSTEM:/system/vendor/lib/egl/libGLES_mali.so"],
        "never_writes": ["DATA", "RECOVERY", "EFS", "PIT", "BOOTLOADER"],
    }
    path = Path(target) / filename
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as z:
        def put_string(name, txt, executable=False):
            item = zipfile.ZipInfo(name, (2026, 11, 7, 0, 0, 0))
            item.create_system = 3
            item.external_attr = ((0o100755 if executable else 0o100644) << 16)
            item.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(item, txt.encode())
        put_string("META-INF/com/google/android/update-binary", updater, True)
        put_string("META-INF/com/google/android/updater-script", "# SM-P900 only; logic in update-binary\n")
        z.write(files[boot_key], "payload/boot.img")
        z.write(files[mali_key], "payload/libGLES_mali.so")
        put_string("manifest.json", json.dumps(meta, indent=2) + "\n")
        put_string("README.txt", README)
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None or len(z.namelist()) != 6:
            raise ValueError(f"{mode} ZIP CRC/structure failed")
        script = z.read("META-INF/com/google/android/update-binary").decode()
        if mode + "'" not in script and f"MODE='{mode}'" not in script:
            raise ValueError("Wrong mode embedded")
        for key, member in ((boot_key, "payload/boot.img"),
                            (mali_key, "payload/libGLES_mali.so")):
            h = hashlib.sha256()
            with z.open(member) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    h.update(chunk)
            if h.hexdigest() != COMPONENTS[key][1]:
                raise ValueError(f"{mode} ZIP member SHA invalid: {key}")
    return {"file": filename, "sha256": sha256_file(path), "size": path.stat().st_size,
            "operation": mode, "hardware_tested": False}


def build(files, out):
    verify_source_files(files)
    target = Path(out)
    target.mkdir(parents=True, exist_ok=True)
    artifacts = [build_one(m, files, target) for m in ("INSTALL", "RESTORE")]
    (target / "SHA256SUMS.txt").write_text(
        "".join(f"{item['sha256']}  {item['file']}\n" for item in artifacts)
    )
    (target / "README-START-HERE.txt").write_text(README)
    (target / "PAIR-MANIFEST.json").write_text(json.dumps(artifacts, indent=2) + "\n")
    return artifacts


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--r7-boot", required=True, type=Path)
    p.add_argument("--uk10-mali", required=True, type=Path)
    p.add_argument("--r15-boot", required=True, type=Path)
    p.add_argument("--r15-mali", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    print(json.dumps(build({
        "r7_boot": a.r7_boot, "old_mali": a.uk10_mali,
        "r15_boot": a.r15_boot, "r15_mali": a.r15_mali,
    }, a.out), indent=2))


if __name__ == "__main__":
    main()
