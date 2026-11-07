#!/usr/bin/env python3
"""Review prior offline image evidence; never authorize real hardware flashing."""
import argparse
import json
from pathlib import Path

KNOWN_TESTED_MALI_SHA = "34af399a1090295a7138297b9352334c73d569212a4bd11be4b3254dafe26cde"


def inspect(graphics, gate):
    if graphics.get("status") != "OFFLINE_SYSTEM_MANIFEST_AND_GRAPHICS_INSPECTED_NOT_DEVICE_TESTED":
        raise ValueError("Missing complete offline graphics audit")
    if gate.get("status") != "EXT4_AND_GRAPHICS_AUDITED_NO_HARDWARE_TEST":
        raise ValueError("Missing ext4 filesystem evidence")
    if gate.get("filesystem_e2fsck_ok") is not True or gate.get("touch_vintf_ok") is not True:
        raise ValueError("Missing filesystem or touch manifest verification")
    if graphics.get("flash_approved") is not False or gate.get("flash_approved") is not False:
        raise ValueError("Upstream incorrectly asserted flash approval")
    mali = graphics.get("mali", {})
    actual = mali.get("sha256")
    if not isinstance(actual, str) or len(actual) != 64:
        raise ValueError("Unknown Mali library digest")
    matched = actual == KNOWN_TESTED_MALI_SHA
    if matched != graphics.get("mali_paired_with_installed_r7p0_boot"):
        raise ValueError("Contradictory graphics report pairing flag")
    if matched != gate.get("paired_mali_for_current_r7p0_runtime"):
        raise ValueError("Contradictory gate pairing flag")
    return {
        "system_image_sha256": gate.get("image_sha256"),
        "system_filesystem_verified": True,
        "vintf_touch_declared_correctly": True,
        "built_system_mali_sha256": actual,
        "currently_installed_r7p0_mali_sha256": KNOWN_TESTED_MALI_SHA,
        "mali_userspace_pair_matches": matched,
        "other_graphics_binaries": [
            {"name": lib["name"], "sha256": lib["sha256"], "needed": lib["needed"]}
            for lib in graphics.get("hw_libraries", [])
        ],
        "mali_needed": mali.get("needed", []),
        "mali_version_needed_libraries": mali.get("version_needed_libraries", []),
        "mali_contains_surfaceless_egl_extension": mali.get("contains_surfaceless_egl_extension"),
        "safety_state": (
            "BLOCKED_SYSTEM_GPU_MISMATCH"
            if not matched else "BLOCKED_UNRESOLVED_EGL_SWAP_CRASH"
        ),
        "physical_boot_verified": False,
        "bootanimation_egl_swap_fixed": False,
        "flash_approved": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("graphics_report", type=Path)
    p.add_argument("offline_gate", type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    result = inspect(json.loads(a.graphics_report.read_text()), json.loads(a.offline_gate.read_text()))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
