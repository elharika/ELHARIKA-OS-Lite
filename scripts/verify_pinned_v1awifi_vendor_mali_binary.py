#!/usr/bin/env python3
"""Read-only pinned SM-P900 donor Mali binary comparison without ROM download.

The expected donor artifact is from the *exact same device's* public Android 11
vendor source. This audit reports identity and dynamic ELF dependencies only.
It NEVER treats matching a source ROM repository as proof of working graphics.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

DONOR_GIT_BLOB_SHA1 = "860898a5a59142f9917dcad28f5e05a9796d03b2"
DONOR_SOURCE_COMMIT = "8f5241f7637477d3ecae65c67b9315d343257fad"
BAD_UK5_SYSTEM_SHA256 = "3bc453470f2f6711d463f3fff9b115011cbcefcbb1355be9af147857d892e433"
TESTED_R7P0_UK10_SHA256 = "34af399a1090295a7138297b9352334c73d569212a4bd11be4b3254dafe26cde"
STOCK_P900_SHA256 = "6bdde99d255444cf59374558736c85de5413125f63f4035237d6556c0f91047d"
MAX_SIZE = 45_000_000


def run(args):
    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, timeout=30)
    if proc.returncode != 0:
        raise ValueError(f"{args[0]} failed: {proc.stderr[:180]}")
    return proc.stdout


def audit(path):
    path = Path(path)
    data = path.read_bytes()
    if not 1_000_000 < len(data) < MAX_SIZE:
        raise ValueError("Unexpected Mali binary size")
    git_sha = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
    if git_sha != DONOR_GIT_BLOB_SHA1:
        raise ValueError("Donor blob does not match exact upstream pinned Git object")
    if data[:5] != b"\x7fELF\x01" or data[5:6] != b"\x01":
        raise ValueError("Expected ARM32 little-endian ELF")
    head = run(["readelf", "-W", "-h", str(path)])
    if not re.search(r"Machine:\s*ARM", head):
        raise ValueError("Expected 32-bit ARM ELF")
    dynamic = run(["readelf", "-W", "-d", str(path)])
    note = run(["readelf", "-W", "-n", str(path)])
    buildid = re.findall(r"Build ID:\s+([0-9a-fA-F]+)", note)
    sha = hashlib.sha256(data).hexdigest()
    matches_bad_system = sha == BAD_UK5_SYSTEM_SHA256
    matches_r7p0_trial = sha == TESTED_R7P0_UK10_SHA256
    matches_stock = sha == STOCK_P900_SHA256
    return {
        "status": "PINNED_SM_P900_DONOR_MALI_ELF_IDENTIFIED_NO_FLASH_APPROVAL",
        "donor_vendor_source_commit": DONOR_SOURCE_COMMIT,
        "donor_mali_git_sha1": git_sha,
        "donor_mali_sha256": sha,
        "donor_mali_size": len(data),
        "build_id": buildid[0].lower() if buildid else None,
        "elf_needed": re.findall(r"\(NEEDED\).*Shared library: \[([^\]]+)\]", dynamic),
        "elf_soname": (re.findall(r"\(SONAME\).*Library soname: \[([^\]]+)\]", dynamic) or [None])[0],
        "is_identical_to_uk5_abi_blocked_ELHARIKA_system": matches_bad_system,
        "is_identical_to_r7p0_uk10_tested_device": matches_r7p0_trial,
        "is_identical_to_stock_android5_0_2": matches_stock,
        "known_uk5_mismatch": matches_bad_system,
        "uk_api_version_proven_for_arbitrary_donor_binary": False,
        "donor_kernel_source_selects_r15p0": True,
        "donor_kernel_elf_abi_compatibility_proven": False,
        "any_new_flash_approved": False,
        "device_boot_tested": False,
        "conclusion": (
            "Donor uses SAME known UK5-mismatch Mali ELF as blocked ELHARIKA system"
            if matches_bad_system else
            "Different donor Mali ELF; verify handshake ABI and all dependencies before considering a matched ROM"
        ),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("pinned_binary", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    result = audit(a.pinned_binary)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        "status": result["status"],
        "sha256": result["donor_mali_sha256"],
        "same_as_uk5_blocked": result["is_identical_to_uk5_abi_blocked_ELHARIKA_system"],
        "same_as_r7p0_uk10": result["is_identical_to_r7p0_uk10_tested_device"],
        "flash_approved": False,
    }, indent=2))


if __name__ == "__main__":
    main()
