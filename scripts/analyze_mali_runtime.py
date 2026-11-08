#!/usr/bin/env python3
"""Classify GPU capture evidence without treating kernel probe as successful boot."""
import argparse
import gzip
import json
from pathlib import Path
import re
import tarfile

MARKERS = {
    "gpu_probe": re.compile(r"Mali-T62x MP6 r0p1"),
    "gpu_file": re.compile(r"/dev/mali0"),
    "renderengine_gpu": re.compile(r"RenderEngine: renderer\s+: Mali-T628"),
    "bootanimation_crash": re.compile(r"Fatal signal 11 .*BootAnimation"),
    "bootanimation_swap_crash": re.compile(r"libGLES_mali\.so \(eglp_swap_buffers"),
    "hwc_disconnect": re.compile(r"HWComposer: isConnected failed for display 0: Invalid display"),
    "touch_hal_missing": re.compile(r"vendor\.lineage\.touch@1\.0::IKeyDisabler/default is not registered"),
    "boot_completed": re.compile(r"boot_completed.*\b1\b|BOOT_COMPLETED", re.IGNORECASE),
}


def inspect_archive(path):
    needed = {"collector.log", "logcat-final.txt", "android-kernel-config.gz"}
    allow = needed | {"logcat.txt.1", "logcat.txt", "surfaceflinger-strace-1.txt"}
    with tarfile.open(path, "r:gz") as tar:
        data = {}
        for item in tar:
            name = Path(item.name).name
            if name in allow:
                if not item.isfile() or item.size > 12000000 or name in data:
                    raise ValueError("Unexpected archive member: " + name)
                data[name] = tar.extractfile(item).read()
    if not needed.issubset(data):
        raise ValueError("Capture is missing critical evidence")
    config = gzip.decompress(data["android-kernel-config.gz"]).decode("utf-8", "replace")
    collector = data["collector.log"].decode("utf-8", "replace")
    logs = "\n".join(data[k].decode("utf-8", "replace") for k in (
        "logcat.txt.1", "logcat.txt", "logcat-final.txt") if k in data)
    markers = {k: bool(p.search(collector + "\n" + logs)) for k, p in MARKERS.items()}
    if not markers["gpu_file"] or not markers["gpu_probe"]:
        verdict = "GPU_DEVICE_ABSENT_OR_UNVERIFIED"
    elif markers["bootanimation_crash"] and markers["bootanimation_swap_crash"]:
        verdict = "GPU_INITIALIZED_EGL_SWAP_CRASH"
    elif markers["touch_hal_missing"] and not markers["boot_completed"]:
        verdict = "TOUCH_HAL_MISSING_BOOT_UNVERIFIED"
    elif markers["boot_completed"] and not markers["bootanimation_crash"]:
        verdict = "BOOT_COMPLETED_LOGGED_VISUAL_OUTPUT_UNVERIFIED"
    else:
        verdict = "INSUFFICIENT_EVIDENCE"
    trace = data.get("surfaceflinger-strace-1.txt", b"").decode("utf-8", "replace")
    return {
        "verdict": verdict,
        "kernel_r7p0_enabled": "CONFIG_MALI_T6XX_R7P0=y" in config.splitlines(),
        "observed": markers,
        "successful_gpu_ioctl": bool(re.search(r"ioctl\([^\n]*</dev/mali0>[^\n]*\) = 0", trace)),
        "flash_approved": False, "ui_boot_proven": False,
        "warning": "GPU probe/EGL initialization alone cannot prove frame presentation or home UI works."
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    result = inspect_archive(args.archive)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(result["verdict"])


if __name__ == "__main__":
    main()
