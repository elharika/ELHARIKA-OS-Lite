#!/usr/bin/env python3
"""Select split cameraserver with the existing pinned HAL1 HIDL provider.
Development candidate: camera capture/recording still require device validation.
"""
import argparse
import hashlib
from pathlib import Path

OLD = "TARGET_HAS_LEGACY_CAMERA_HAL1 := true"
NEW = "TARGET_HAS_LEGACY_CAMERA_HAL1 := false"
PROVIDER_BLOB = "bb0030030931446bd79926745ba3bdddbe7ed8bc"

def transform(board):
    lines = [line for line in board.splitlines() if "TARGET_HAS_LEGACY_CAMERA_HAL1" in line]
    if lines == [NEW]:
        return board
    if lines != [OLD]:
        raise ValueError("Unexpected camera hosting configuration")
    return board.replace(OLD, NEW, 1)

def apply(root):
    root = Path(root)
    provider = (root / "hardware/camera/provider/CameraProvider.cpp").read_bytes()
    digest = hashlib.sha1(b"blob " + str(len(provider)).encode() + b"\0" + provider).hexdigest()
    if digest != PROVIDER_BLOB:
        raise ValueError("Unreviewed camera provider revision")
    product = (root / "device-common.mk").read_text()
    for module in ("android.hardware.camera.provider@2.4-impl.exynos5420",
                   "android.hardware.camera.provider@2.4-service",
                   "camera.device@1.0-impl.exynos5420", "camera.universal5420"):
        if module not in product:
            raise ValueError("Missing required HAL1 provider module: " + module)
    board = root / "BoardConfigCommon.mk"
    old = board.read_text()
    new = transform(old)
    if new != old:
        board.write_text(new)
    return int(new != old)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("common_tree", type=Path)
    print("Updated camera hosting:", apply(parser.parse_args().common_tree))
