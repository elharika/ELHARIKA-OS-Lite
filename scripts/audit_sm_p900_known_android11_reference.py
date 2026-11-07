#!/usr/bin/env python3
"""Audit a published SM-P900 Android 11 reference GPU pair, read-only.

Reference source is pinned to salih4187's lineage-18.1 device, kernel and vendor
commits. This checks GPU generation, ELF metadata and device BoardConfig.
It NEVER treats matching version strings as proof of physical device boot.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

PINNED = {
    "kernel": "35d960ed3c2de3d5558b782257053599cded659e",
    "vendor": "8f5241f7637477d3ecae65c67b9315d343257fad",
    "device_common": "22e5a28343d78578c4d604f3f26fcc709c9435f2",
}
PREVIOUS_TESTED_MALI_BUILID = "1b2949cf031b30f20a970c511925875d"


def build_id_of(readelf_notes):
    result = re.findall(r"Build ID:\s*([0-9a-fA-F]+)", readelf_notes)
    if len(result) != 1:
        raise ValueError("Missing or ambiguous GNU Build ID")
    return result[0].lower()


def examine(config, kbuild, board, properties, blob_path):
    if "CONFIG_MALI_T6XX_R15P0=y" not in config.splitlines():
        raise ValueError("Reference kernel is not R15P0")
    if "# CONFIG_MALI_T6XX_R7P0 is not set" not in config.splitlines():
        raise ValueError("Reference accidentally selects R7P0")
    if 'MALI_RELEASE_NAME ?= "r15p0-00rel0"' not in kbuild:
        raise ValueError("R15P0 kernel Kbuild release string changed")
    if "BOARD_USES_EXYNOS5_COMMON_GRALLOC := true" not in board:
        raise ValueError("Reference gralloc selection changed")
    for required in (
        "ro.surface_flinger.running_without_sync_framework = true",
        "ro.surface_flinger.max_frame_buffer_acquired_buffers = 3",
    ):
        if required not in properties:
            raise ValueError("Reference display property removed: " + required)
    blob = Path(blob_path)
    if not blob.is_file() or not (100_000 < blob.stat().st_size < 60_000_000):
        raise ValueError("Missing or implausible reference EGL userspace blob")
    with blob.open("rb") as inp:
        head = inp.read(52)
    if head[:6] != b"\x7fELF\x01\x01":
        raise ValueError("Reference EGL blob is not 32-bit little-endian ELF")
    def run(*args):
        proc = subprocess.run(args, text=True, capture_output=True, timeout=45)
        if proc.returncode:
            raise ValueError(f"readelf failed: {proc.stderr[:180]}")
        return proc.stdout
    header = run("readelf", "-W", "-h", str(blob))
    if not re.search(r"Machine:\s*ARM", header):
        raise ValueError("Reference EGL userspace is not ARM32")
    notes = run("readelf", "-W", "-n", str(blob))
    needed = run("readelf", "-W", "-d", str(blob))
    versions = run("readelf", "-W", "-V", str(blob))
    bid = build_id_of(notes)
    # Ubuntu 22.04 CI uses Python 3.10; hashlib.file_digest requires 3.11.
    hasher = hashlib.sha256()
    with blob.open("rb") as binary:
        while True:
            chunk = binary.read(1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
    sha = hasher.hexdigest()
    dependencies = re.findall(r"\(NEEDED\).*Shared library: \[([^\]]+)\]", needed)
    return {
        "status": "SM_P900_ANDROID11_REFERENCE_GPU_ELF_INSPECTED_NO_DEVICE_QA",
        "source_commits": PINNED,
        "reference_kernel": "MALI_R15P0",
        "reference_r7p0_disabled": True,
        "board_gralloc": "exynos5",
        "surface_flinger_properties": {
            "running_without_sync_framework": True,
            "max_frame_buffer_acquired_buffers": 3,
        },
        "reference_libgles_mali_sha256": sha,
        "reference_libgles_mali_bytes": blob.stat().st_size,
        "reference_egl_build_id": bid,
        "previous_crashing_uk10_build_id": PREVIOUS_TESTED_MALI_BUILID,
        "same_build_id_as_crashing_uk10": bid == PREVIOUS_TESTED_MALI_BUILID,
        "needed": dependencies,
        "elf_version_need": sorted(set(re.findall(r"File:\s+([^\s]+)", versions))),
        "reference_userspace_source": "salih4187/android_vendor_samsung_universal5420-common",
        "reference_release_proven_to_boot_here": False,
        "compatible_with_current_r7p0_boot": False,
        "safe_to_flash": False,
        "notes": "Must preserve complete R15P0 kernel+vendor graphics pair; a single replaced libGLES or boot image is not sufficient.",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kernel-config", type=Path, required=True)
    p.add_argument("--r15-kbuild", type=Path, required=True)
    p.add_argument("--board", type=Path, required=True)
    p.add_argument("--properties", type=Path, required=True)
    p.add_argument("--egl", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    x = p.parse_args()
    out = examine(x.kernel_config.read_text(), x.r15_kbuild.read_text(),
                  x.board.read_text(), x.properties.read_text(), x.egl)
    x.report.parent.mkdir(parents=True, exist_ok=True)
    x.report.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
