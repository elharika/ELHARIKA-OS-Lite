#!/usr/bin/env python3
"""Fail-closed comparison of SM-P900 graphics inputs with a public Android 11 donor.

NO flashing, modifying proprietary binaries or rebuilding Android.
Checks source *pairing*, not a claim of a functioning finished ROM.
"""
import argparse
import json
from pathlib import Path
import re

DONOR_BRANCH = "salih4187/lineage-18.1"
DONOR_KERNEL_REV = "35d960ed3c2de3d5558b782257053599cded659e"
DONOR_DEVICE_COMMON_REV = "22e5a28343d78578c4d604f3f26fcc709c9435f2"
DONOR_V1A_REV = "ff8fb2eed9ff6a2a6b723c44681cf0f3344c07a9"
DONOR_MALI_VENDOR_TREE_REV = "8f5241f7637477d3ecae65c67b9315d343257fad"
DONOR_VENDOR_MALI_GIT_BLOB_SHA1 = "860898a5a59142f9917dcad28f5e05a9796d03b2"
TESTED_TABLET_R7P0_MALI_SHA256 = "34af399a1090295a7138297b9352334c73d569212a4bd11be4b3254dafe26cde"
BUILT_SYSTEM_IMAGE_MALI_SHA256 = "3bc453470f2f6711d463f3fff9b115011cbcefcbb1355be9af147857d892e433"
BOOTANIMATION_EGL_CRASH_PC = "0x00263458"


def config_has(config, field):
    return re.search(r"(?m)^" + re.escape(field) + r"=y$", config) is not None


def audit(donor_defconfig, previous_defconfig, donor_props, previous_props,
          donor_touch_manifest, donor_mali_git_sha):
    if donor_mali_git_sha != DONOR_VENDOR_MALI_GIT_BLOB_SHA1:
        raise ValueError("Donor proprietary Mali Git blob is not the reviewed version")
    # Never compare names alone: read exact config lines from both revisions.
    if not config_has(donor_defconfig, "CONFIG_MALI_T6XX_R15P0"):
        raise ValueError("Donor no longer selects r15p0")
    if config_has(donor_defconfig, "CONFIG_MALI_T6XX_R7P0"):
        raise ValueError("Donor enables two conflicting Mali driver versions")
    if not config_has(previous_defconfig, "CONFIG_MALI_T6XX_R15P0"):
        raise ValueError("Previous baseline Mali config changed")
    if not config_has(donor_defconfig, "CONFIG_ION_EXYNOS"):
        raise ValueError("Donor Exynos ION support absent")
    if donor_props != previous_props:
        props_same = False
    else:
        props_same = True
    for key in ("debug.hwc.winupdate=0",
                "ro.surface_flinger.running_without_sync_framework = true",
                "ro.surface_flinger.max_frame_buffer_acquired_buffers = 3"):
        if key not in donor_props:
            raise ValueError("Expected donor graphics property missing: " + key)
    if "<name>vendor.lineage.touch</name>" not in donor_touch_manifest:
        raise ValueError("Touch manifest not available")
    if "<name>IKeyDisabler</name>" not in donor_touch_manifest:
        raise ValueError("Touch HAL declaration unexpectedly different")
    if "<name>ITouchscreenGesture</name>" not in donor_touch_manifest:
        raise ValueError("Gesture HAL lost in donor")
    return {
        "status": "SAME_DEVICE_DONOR_SOURCE_REVIEWED_NOT_A_FLASH_IMAGE",
        "model": "Samsung SM-P900 (v1awifi)",
        "donor_kernel_ref": DONOR_KERNEL_REV,
        "donor_v1a_common_ref": DONOR_V1A_REV,
        "donor_common_ref": DONOR_DEVICE_COMMON_REV,
        "donor_mali_vendor_ref": DONOR_MALI_VENDOR_TREE_REV,
        "donor_mali_blob_git_sha1": donor_mali_git_sha,
        "donor_defconfig_gpu": "CONFIG_MALI_T6XX_R15P0=y",
        "previous_defconfig_gpu": "CONFIG_MALI_T6XX_R15P0=y",
        "last_physically_tested_ELHARIKA_boot_gpu": "CONFIG_MALI_T6XX_R7P0=y",
        "last_physically_tested_ELHARIKA_userspace_sha256": TESTED_TABLET_R7P0_MALI_SHA256,
        "built_ELHARIKA_system_image_userspace_sha256": BUILT_SYSTEM_IMAGE_MALI_SHA256,
        "donor_and_previous_graphics_properties_identical": props_same,
        "donor_declares_missing_IKeyDisabler": True,
        "donor_declares_ITouchscreenGesture": True,
        "reported_bootanimation_fault_pc": BOOTANIMATION_EGL_CRASH_PC,
        "note": "Donor files form a coherent *source baseline*; changing kernel alone or copying one blob is unsafe. Real installed donor ROM binary versions are not verified.",
        "next_safe_gate": "Inspect a version-matched donor boot/system package and compare pinned Mali/ION/Gralloc/HWC SHA hashes before any experimental image.",
        "candidate_tested_on_user_device": False,
        "Mali_eglSwapBuffers_working_on_user_device": False,
        "flash_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("donor_defconfig", type=Path)
    parser.add_argument("previous_defconfig", type=Path)
    parser.add_argument("donor_props", type=Path)
    parser.add_argument("previous_props", type=Path)
    parser.add_argument("donor_touch_manifest", type=Path)
    parser.add_argument("--mali-git-sha", required=True)
    parser.add_argument("--out", required=True, type=Path)
    x = parser.parse_args()
    r = audit(*(getattr(x, attr).read_text() for attr in
                ("donor_defconfig", "previous_defconfig", "donor_props",
                 "previous_props", "donor_touch_manifest")),
              donor_mali_git_sha=x.mali_git_sha)
    x.out.parent.mkdir(parents=True, exist_ok=True)
    x.out.write_text(json.dumps(r, indent=2) + "\n")
    print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
