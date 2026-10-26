#!/usr/bin/env python3
"""Relabel only the BCM Wi-Fi firmware selector as writable."""
import hashlib
from pathlib import Path
import sys

FILES = {
    "file_contexts": (
        "c0c1ffdb2d356df595c48f08ec41e7f2474cca9a",
        "/sys/module/dhd/parameters/firmware_path    u:object_r:sysfs_wifi:s0",
        "/sys/module/dhd/parameters/firmware_path    u:object_r:sysfs_wifi_writable:s0",
    ),
    "hal_wifi_default.te": (
        "4bb635e6aa8162ffc08c3f31edd51f21eb07496d",
        "allow hal_wifi_default sysfs_wifi:file rw_file_perms;",
        "allow hal_wifi_default sysfs_wifi_writable:file rw_file_perms;",
    ),
}
def blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def apply(root):
    root = Path(root) / "sepolicy/vendor"
    updates = {}
    for name, (sha, before, after) in FILES.items():
        path = root / name
        raw = path.read_bytes()
        source = raw.decode()
        if source.count(after) == 1 and source.count(before) == 0:
            continue
        if blob_sha(raw) != sha or source.count(before) != 1:
            raise ValueError("Unexpected pinned policy: " + name)
        updates[path] = source.replace(before, after, 1)
    for path, updated in updates.items():
        path.write_text(updated)
    return len(updates)

if __name__ == "__main__":
    print("Wi-Fi policy files updated:", apply(sys.argv[1]))
