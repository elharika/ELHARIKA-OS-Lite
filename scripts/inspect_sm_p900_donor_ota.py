#!/usr/bin/env python3
"""Read-only inspect an UNOFFICIAL SM-P900 Android 11 reference OTA ZIP.

This only inventories packaging, boot-image magic, image layout, and SHA256.
It does NOT install, unpack proprietary libraries into any delivered artifact,
execute its update script, approve flashing, or assert actual boot success.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

KNOWN_DEVICE = "v1awifi"
BOOT_MAGIC = b"ANDROID!"
MAX_METADATA = 2_000_000


def sha256_stream(f):
    digest = hashlib.sha256()
    while True:
        data = f.read(2 * 1024 * 1024)
        if not data:
            break
        digest.update(data)
    return digest.hexdigest()


def inspect(path):
    path = Path(path)
    if not path.is_file() or not path.name.endswith("-v1awifi.zip"):
        raise ValueError("Only date-named SM-P900 v1awifi donor archives are accepted")
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if not members or len(members) > 15000:
            raise ValueError("Unexpected OTA archive member count")
        names = [m.filename for m in members]
        if len(set(names)) != len(names):
            raise ValueError("Duplicated ZIP entries")
        for m in members:
            p = PurePosixPath(m.filename)
            if p.is_absolute() or ".." in p.parts:
                raise ValueError("Unsafe path in OTA ZIP")
            if m.file_size > 6_000_000_000:
                raise ValueError("Implausibly large OTA component")
        boot = next((m for m in members if m.filename == "boot.img"), None)
        if boot is None or not (1_000_000 <= boot.file_size <= 8_388_608):
            raise ValueError("Missing or unexpected SM-P900 boot.img")
        with archive.open(boot) as raw:
            magic = raw.read(8)
            if magic != BOOT_MAGIC:
                raise ValueError("Not an Android boot image")
            boot_hash = hashlib.sha256(magic)
            while data := raw.read(2 * 1024 * 1024):
                boot_hash.update(data)
        candidates = [m for m in members
                      if m.filename in ("system.img", "system.new.dat",
                                        "system.new.dat.br", "system.transfer.list",
                                        "payload.bin", "vendor.img")]
        if not candidates:
            raise ValueError("No recognized Android system image payload")
        payload = [
            {"name": m.filename, "uncompressed_size": m.file_size,
             "compressed_size": m.compress_size}
            for m in candidates
        ]
        scripts = [m.filename for m in members if
                   m.filename.endswith("updater-script") or
                   m.filename == "META-INF/com/android/metadata"]
        return {
            "status": "SAME_DEVICE_REFERENCE_OTA_STRUCTURE_CHECKED_NOT_FLASH_APPROVED",
            "source_zip": path.name,
            "zip_sha256": sha256_stream(path.open("rb")),
            "entry_count": len(members),
            "boot_image": {"bytes": boot.file_size,
                           "sha256": boot_hash.hexdigest(),
                           "android_magic": True},
            "system_payload": payload,
            "install_metadata_entries": scripts,
            "has_separate_vendor_img": "vendor.img" in names,
            "can_compare_built_mali_elf_yet": False,
            "not_a_verified_build_for_user_device": True,
            "must_not_mix_with_existing_r7p0_trial": True,
            "requires_complete_boot_system_vendor_pair": True,
            "flash_approved": False,
        }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("ota", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    result = inspect(a.ota)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
