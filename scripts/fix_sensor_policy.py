#!/usr/bin/env python3
"""Keep sensor input reads while removing broad writes on the exact pinned policy."""
import argparse
from pathlib import Path
from harden_sepolicy import ORIGINAL, REMOVALS

BASE = ORIGINAL["hal_sensors_default.te"].replace(REMOVALS["hal_sensors_default.te"], "")
OLD = "allow hal_sensors_default sysfs_input:file rw_file_perms;"
NEW = "allow hal_sensors_default sysfs_input:file r_file_perms;"
TARGET = BASE.replace(OLD, NEW)

def transform(text):
    if text == TARGET:
        return text
    if text != BASE:
        raise ValueError("Unexpected sensor policy; apply harden_sepolicy first")
    return TARGET

def apply(root):
    path = Path(root) / "sepolicy/vendor/hal_sensors_default.te"
    old = path.read_text()
    new = transform(old)
    if new != old:
        path.write_text(new)
    return int(new != old)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("common_tree", type=Path)
    print("Updated sensor policy:", apply(parser.parse_args().common_tree))
