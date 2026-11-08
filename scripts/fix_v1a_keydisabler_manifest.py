#!/usr/bin/env python3
"""Remove a dead optional KeyDisabler VINTF declaration from the pinned SM-P900 tree.

This prevents the Android framework from waiting for an advertised but
conditionally unregistered HIDL interface. It does not disable raw S Pen input,
replace Wacom firmware, modify any kernel driver, or validate hardware behavior.
"""

import argparse
import hashlib
from pathlib import Path

# exynos5420/android_device_samsung_v1a-common @
# 4ae15a9b02c6efb1ffe956ab386fce9b3606ea94, manifest.xml (848 bytes).
BEFORE_SHA256 = "b4ab6238f14a062b665fcd77743a5aa482f8b9527e52fad6096db146b55f6bed"
AFTER_SHA256 = "5022809939e12eefd9449c4098724af9b084935bd51b862b19fea13e0d6c69a1"
BLOCK = (b"        <interface>\n"
         b"            <name>IKeyDisabler</name>\n"
         b"            <instance>default</instance>\n"
         b"        </interface>\n")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def apply(source: Path, check: bool = False) -> str:
    root = source.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Expected the device/samsung/v1a-common directory")
    target = root / "manifest.xml"
    if target.is_symlink() or not target.is_file():
        raise ValueError("Missing or unsafe v1a-common/manifest.xml")
    before = target.read_bytes()
    current_sha = digest(before)
    if current_sha == AFTER_SHA256:
        return "verified: unsupported IKeyDisabler declaration is absent"
    if current_sha != BEFORE_SHA256:
        raise ValueError("Unexpected v1a-common/manifest.xml; no file modified")
    if check:
        raise ValueError("Pinned v1a-common manifest is not patched")
    if before.count(BLOCK) != 1:
        raise ValueError("Pinned KeyDisabler interface block not found exactly once")
    after = before.replace(BLOCK, b"", 1)
    if digest(after) != AFTER_SHA256:
        raise ValueError("Post-patch hash does not match expected manifest")
    target.write_bytes(after)
    return "applied: removed only IKeyDisabler HIDL declaration"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="device/samsung/v1a-common checkout")
    parser.add_argument("--check", action="store_true", help="verify patched manifest only; no writes")
    args = parser.parse_args()
    print(apply(args.source, check=args.check))


if __name__ == "__main__":
    main()
