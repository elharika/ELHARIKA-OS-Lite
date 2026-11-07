#!/usr/bin/env python3
"""Guarded SM-P900-only mitigation for a missing HIDL touch service in Android 11.

The pinned Lineage SDK calls IKeyDisabler.getService(true), potentially waiting
indefinitely when this optional device feature is not implemented. Keep gesture
support intact. This is a SOURCE patch, not a device or system image change.
"""
import argparse
import json
from pathlib import Path
import subprocess

SDK_REVISION = "5f1b14d27249f8b7f035060005e07ac9388e5470"
DEVICE_REVISION = "4ae15a9b02c6efb1ffe956ab386fce9b3606ea94"
JAVA = "sdk/src/java/lineageos/hardware/LineageHardwareManager.java"
DEVICE_MANIFEST = "device/samsung/v1a-common/manifest.xml"
OLD_CALL = "return IKeyDisabler.getService(true);"
NEW_CALL = "return null; // SM-P900: IKeyDisabler HAL absent; never wait for optional service."
DISPATCH_PREFIX = "                case FEATURE_KEY_DISABLE:\n                    "
OLD_INTERFACE = """        <interface>
            <name>IKeyDisabler</name>
            <instance>default</instance>
        </interface>
"""
GESTURE_INTERFACE = """        <interface>
            <name>ITouchscreenGesture</name>
            <instance>default</instance>
        </interface>
"""


def patch_java(content):
    # The real pinned SDK contains THREE cases for FEATURE_KEY_DISABLE:
    # isSupported, get, and set. Only the HIDL getter may be changed here.
    if content.count("private IBase getHIDLService(int feature)") != 1:
        raise ValueError("Unknown SDK HIDL dispatcher")
    before = DISPATCH_PREFIX + OLD_CALL
    after = DISPATCH_PREFIX + NEW_CALL
    if content.count(after) == 1 and before not in content and OLD_CALL not in content:
        return content, False
    if content.count(before) != 1 or content.count(OLD_CALL) != 1 or NEW_CALL in content:
        raise ValueError("Unexpected or partially patched SDK service call")
    if content.count("ITouchscreenGesture.getService(true)") != 1:
        raise ValueError("Gesture HAL dispatcher missing; refusing SDK patch")
    return content.replace(before, after, 1), True


def patch_manifest(content):
    if content.count("<name>vendor.lineage.touch</name>") != 1:
        raise ValueError("Unknown touch manifest")
    if content.count(GESTURE_INTERFACE) != 1:
        raise ValueError("TouchscreenGesture HAL must remain declared")
    if OLD_INTERFACE not in content and "IKeyDisabler" not in content:
        return content, False
    if content.count(OLD_INTERFACE) != 1:
        raise ValueError("Unexpected IKeyDisabler manifest layout")
    return content.replace(OLD_INTERFACE, "", 1), True


def apply(android_root):
    android = Path(android_root).resolve()
    for rel, expected in (("lineage-sdk", SDK_REVISION),
                          ("device/samsung/v1a-common", DEVICE_REVISION)):
        got = subprocess.check_output(
            ["git", "-C", str(android / rel), "rev-parse", "HEAD"], text=True
        ).strip()
        if got != expected:
            raise ValueError(f"Unexpected pinned revision at {rel}: {got}")
    java = android / "lineage-sdk" / JAVA
    manifest = android / DEVICE_MANIFEST
    for path in (java, manifest):
        if not path.is_file():
            raise ValueError("Missing pinned input file: " + str(path))
    # Validate both transformations before modifying either file.
    java_out, java_changed = patch_java(java.read_text())
    manifest_out, manifest_changed = patch_manifest(manifest.read_text())
    if java_changed:
        java.write_text(java_out)
    if manifest_changed:
        manifest.write_text(manifest_out)
    return {
        "status": "OPTIONAL_TOUCH_HAL_SOURCE_PATCHED_NOT_BUILT_NOT_DEVICE_TESTED",
        "sdk_revision": SDK_REVISION,
        "device_revision": DEVICE_REVISION,
        "sdk_java_changed": java_changed,
        "manifest_changed": manifest_changed,
        "key_disabler_request_disabled_for_trial": True,
        "touchscreen_gesture_preserved": True,
        "requires_system_image_build": True,
        "flash_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("android_root", type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    report = apply(args.android_root)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
