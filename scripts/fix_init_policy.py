#!/usr/bin/env python3
"""Limit init input sysfs access to reads and attribute changes on pinned SM-P900 policy."""
import argparse
import hashlib
from pathlib import Path

PIN = "92a8d2dc38bf02cb9be4b741d3800d740b6150fd"
OLD = "    sysfs_input\n"
ANCHOR = "allow init sysfs_input:lnk_file read;"
NEW = "allow init sysfs_input:file { r_file_perms setattr };\n" + ANCHOR

def blob(text):
    data = text.encode()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def transform(text):
    if NEW in text and OLD not in text:
        restored = text.replace(NEW, ANCHOR, 1).replace("    sysfs_ausb\n", "    sysfs_ausb\n" + OLD, 1)
        if blob(restored) == PIN:
            return text
    if blob(text) != PIN or text.count(OLD) != 1 or text.count(ANCHOR) != 1:
        raise ValueError("Unexpected init policy; review pinned source")
    return text.replace(OLD, "", 1).replace(ANCHOR, NEW, 1)

def apply(root):
    path = Path(root) / "sepolicy/vendor/init.te"
    old = path.read_text()
    new = transform(old)
    if old != new:
        path.write_text(new)
    return int(old != new)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("common_tree", type=Path)
    print("Updated init policy files:", apply(parser.parse_args().common_tree))
