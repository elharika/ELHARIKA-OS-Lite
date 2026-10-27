#!/usr/bin/env python3
"""Restrict the inherited modem policy's read-only switch label on Wi-Fi SM-P900."""
import argparse
from pathlib import Path
from harden_sepolicy import ORIGINAL, REMOVALS

BASE = ORIGINAL["cbd.te"].replace(REMOVALS["cbd.te"], "")
OLD = "    sysfs_sec_switch\n"
READ = "allow cbd sysfs_sec_switch:file r_file_perms;\n"
TARGET = BASE.replace(OLD, "").replace("allow cbd sysfs_sec_switch:dir r_dir_perms;\n",
                                      "allow cbd sysfs_sec_switch:dir r_dir_perms;\n" + READ)

def transform(text):
    if text == TARGET:
        return text
    if text != BASE:
        raise ValueError("Unexpected modem policy; apply harden_sepolicy first")
    return TARGET

def apply(root):
    path = Path(root) / "sepolicy/vendor/cbd.te"
    old = path.read_text()
    new = transform(old)
    if new != old:
        path.write_text(new)
    return int(new != old)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("common_tree", type=Path)
    print("Updated modem policy:", apply(parser.parse_args().common_tree))
