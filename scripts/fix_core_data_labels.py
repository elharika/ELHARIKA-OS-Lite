#!/usr/bin/env python3
"""Mark pinned /data labels as core data for Android 11 sepolicy_tests."""
import argparse
import hashlib
from pathlib import Path

PIN = "8d29dbc5f3d6590206534f3c25fc2d954f220730"
REPLACEMENTS = [["type audit_data_file, data_file_type, file_type;","type audit_data_file, data_file_type, file_type, core_data_file_type;"],
    ["type gps_data_file, file_type, data_file_type, data_file_type;","type gps_data_file, file_type, data_file_type, data_file_type, core_data_file_type;"],
    ["type security_data_file, file_type, data_file_type;","type security_data_file, file_type, data_file_type, core_data_file_type;"],
    ["type sensors_data_file, file_type, data_file_type;","type sensors_data_file, file_type, data_file_type, core_data_file_type;"],
    ["type vcs_data_file, file_type, data_file_type;","type vcs_data_file, file_type, data_file_type, core_data_file_type;"]]

def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def transform(text):
    target = text
    for old, new in REPLACEMENTS:
        if target.count(old) != 1:
            raise ValueError("Unrecognized pinned /data type: " + old)
        target = target.replace(old, new, 1)
    if text == target:
        return text
    if git_blob(text.encode()) != PIN:
        raise ValueError("Unexpected common file.te revision")
    return target

def apply(root):
    path = Path(root) / "sepolicy/vendor/file.te"
    original = path.read_text()
    # Permit repeated execution only if reversing the exact known patch yields the pinned blob.
    if all(new in original for _, new in REPLACEMENTS):
        reverted = original
        for old, new in REPLACEMENTS:
            if reverted.count(new) != 1:
                raise ValueError("Ambiguous core data policy")
            reverted = reverted.replace(new, old, 1)
        if git_blob(reverted.encode()) != PIN:
            raise ValueError("Unexpected patched common file.te revision")
        return 0
    result = transform(original)
    path.write_text(result)
    return 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("common_tree", type=Path)
    print("Core data labels updated:", apply(parser.parse_args().common_tree))
