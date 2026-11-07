#!/usr/bin/env python3
"""Package exact R15P0 experimental BOOT and donor Mali for OFFLINE REVIEW ONLY.

Output is intentionally NOT a TWRP OTA: no updater-script/update-binary,
no partition modification, and no automatic/implicit flash permission.
"""
import hashlib
import json
import re
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

BOOT_SHA = "7d15b15e127e4b31841e1081efac31d2c298c2748dbc5d55889a3e8d45e20d14"
BOOT_SIZE = 5462032
MALI_SHA = "a00166d28cbd0213c88daadb437534310de09da4bf9fcc64f8e2207e22d76839"
MALI_SIZE = 26858432
MALI_BUILD_ID = "541f48d27481c7fc59e3b9ebd6929c33"
MALI_DDK = b"U:r15p0-00rel0"
ARCHIVE_NAME = "ELHARIKA-SM-P900-R15P0-MATCHED-CANDIDATE-NOT-INSTALLABLE.zip"
SAMSUNG_TRAILER = b"SEANDROIDENFORCE"

README = """ELHARIKA OS Lite — SM-P900 — staged R15P0 pair, NOT INSTALLABLE

This ZIP intentionally lacks META-INF/com/google/android/update-binary and
updater-script. It cannot be used as a TWRP installer and must NOT be flashed.
It does NOT contain a full Android system image.

Contents:
- REFERENCE-BOOT-r15p0.img — original Android 11 development BOOT from
  GitHub workflow 42067803567; not proven to boot a visible UI.
- DONOR-libGLES_mali-r15p0.so — original source-verified r15p0 DDK Mali ELF,
  sha256 a00166d2..., static linker dependencies checked on Android 11.
- manifest.json — exact metadata and known missing runtime gates.

WHY NOT READY TO FLASH: The user's currently installed R7P0/UK10 pair has a
Mali EGL black screen. A physically tested, complete BOOT+Mali rollback is
required before any trial; neither donor UK ioctl support nor graphics frame
swap has been verified in vivo. Never flash the donor ELF alone over R7 BOOT.
"""


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as src:
        while chunk := src.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def verify(boot, mali):
    boot, mali = Path(boot), Path(mali)
    if boot.stat().st_size != BOOT_SIZE or sha256_file(boot) != BOOT_SHA:
        raise ValueError("BOOT is not the exact pinned original R15P0 reference")
    b = boot.read_bytes()
    if b[:8] != b"ANDROID!" or not b.endswith(SAMSUNG_TRAILER):
        raise ValueError("Unexpected Android/Samsung BOOT format")
    ks, _, rs, _, ss, _, _, page, version, _ = struct.unpack_from("<10I", b, 8)
    if not (0 < ks < len(b) and 0 < rs < len(b) and ss == 0 and
            page == 2048 and version == 0):
        raise ValueError("Unexpected BOOT header fields")
    if mali.stat().st_size != MALI_SIZE or sha256_file(mali) != MALI_SHA:
        raise ValueError("Mali ELF is not the verified SM-P900 R15P0 donor")
    with mali.open("rb") as src:
        elf_header = src.read(64)
    if not (elf_header[:6] == b"\x7fELF\x01\x01" and
            struct.unpack_from("<H", elf_header, 18)[0] == 40):
        raise ValueError("Not little-endian ARM32 ELF")
    data = mali.read_bytes()
    if MALI_DDK not in data:
        raise ValueError("Proprietary R15P0 DDK source marker absent")
    notes = subprocess.run(["readelf", "-W", "-n", str(mali)],
                           capture_output=True, text=True, check=True, timeout=20).stdout
    build_ids = re.findall(r"Build ID:\s*([0-9a-fA-F]+)", notes)
    if build_ids != [MALI_BUILD_ID]:
        raise ValueError("Donor Mali ELF BuildId changed")
    return {
        "status": "PINNED_R15P0_PAIR_STAGED_NO_FLASH_APPROVAL",
        "device": "SM-P900/v1awifi",
        "boot_sha256": BOOT_SHA,
        "boot_size": BOOT_SIZE,
        "donor_mali_sha256": MALI_SHA,
        "donor_mali_size": MALI_SIZE,
        "donor_mali_build_id": MALI_BUILD_ID,
        "donor_mali_ddk": MALI_DDK.decode(),
        "current_installed_pair": "R7P0_KBUILD_FIXED+UK10_CONFIRMED_BLACK_SCREEN",
        "missing_gates": [
            "physical microSD backup of full BOOT and original UK10 Mali",
            "verified recovery rollback for both components",
            "live kernel UK ioctl handshake compatibility",
            "first EGL buffer-swap frame visibly presented",
        ],
        "contains_install_script": False,
        "has_passed_static_elf_dependency_closure": True,
        "real_device_boot_verified": False,
        "flash_approved": False,
    }


def package(boot, mali, output):
    result = verify(boot, mali)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    dest = output / ARCHIVE_NAME
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=1) as archive:
        archive.write(boot, "REFERENCE-BOOT-r15p0.img")
        archive.write(mali, "DONOR-libGLES_mali-r15p0.so")
        archive.writestr("manifest.json", json.dumps(result, indent=2) + "\n")
        archive.writestr("DO-NOT-FLASH-README.txt", README)
    with zipfile.ZipFile(dest) as archive:
        if archive.testzip() is not None:
            raise ValueError("Staged ZIP CRC mismatch")
        names = archive.namelist()
        if len(names) != 4 or any(s.startswith("META-INF/") for s in names):
            raise ValueError("Accidentally created flashable OTA ZIP")
    digest = sha256_file(dest)
    (output / "SHA256SUMS.txt").write_text(f"{digest}  {ARCHIVE_NAME}\n")
    return {**result, "bundle_sha256": digest, "bundle_bytes": dest.stat().st_size}


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("Usage: stage_r15p0_pair_nonflash.py BOOT MALI OUT_DIR")
    r = package(*sys.argv[1:])
    print(json.dumps({
        "status": r["status"], "bundle_sha256": r["bundle_sha256"],
        "contains_install_script": False, "flash_approved": False
    }, indent=2))
