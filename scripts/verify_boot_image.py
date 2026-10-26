#!/usr/bin/env python3
"""Structural verification only: never certifies hardware boot or flash safety."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

def verify(image, kernel, ramdisk):
    data = image.read_bytes()
    if len(data) < 1632 or len(data) > 8388608:
        raise ValueError("Invalid SM-P900 boot image size")
    if data[:8] != b"ANDROID!":
        raise ValueError("Missing Android boot magic")
    ks, ka, rs, ra, ss, sa, tags, page, version, osv = struct.unpack_from("<10I", data, 8)
    if page != 2048 or version != 0 or ss != 0:
        raise ValueError("Unexpected pinned legacy boot layout")
    if not ks or not rs:
        raise ValueError("Missing kernel or ramdisk")
    align = lambda n: (n + page - 1) // page * page
    ro = page + align(ks)
    end = ro + align(rs)
    if len(data) != end + 16 or data[end:] != b"SEANDROIDENFORCE":
        # Samsung trailer is 16 bytes; reject truncation and unexplained payloads.
        raise ValueError("Invalid Samsung trailer or component bounds")
    if data[page:page+ks] != kernel.read_bytes():
        raise ValueError("Packaged kernel differs from built kernel")
    if data[ro:ro+rs] != ramdisk.read_bytes():
        raise ValueError("Packaged ramdisk differs from built ramdisk")
    return dict(status="STRUCTURALLY_VALID_NOT_HARDWARE_TESTED",
                size=len(data), sha256=hashlib.sha256(data).hexdigest(),
                kernel_size=ks, ramdisk_size=rs, flash_approved=False)

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("product", type=Path)
    p.add_argument("report", type=Path)
    a = p.parse_args()
    result = verify(a.product/"boot.img", a.product/"kernel", a.product/"ramdisk.img")
    a.report.write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result))
