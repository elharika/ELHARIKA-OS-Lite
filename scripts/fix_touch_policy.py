#!/usr/bin/env python3
"""Keep the touchscreen command writable and the command list read-only."""
from pathlib import Path
import hashlib
import sys

EXPECTED_BLOBS = {
    "file_contexts": "141cfaa92f7e03669db16dfbf4599217a6926420",
    "hal_lineage_touch_default.te": "b68fec4ce778927051993124e82fd6d54ffddda7",
}
BEFORE = {
    "file_contexts": "/sys/devices/virtual/sec/tsp/cmd    u:object_r:sysfs_sec_touchscreen:s0",
    "hal_lineage_touch_default.te": "# hal_lineage_touch_default.te\n\nallow hal_lineage_touch_default {\n    sysfs_homebutton_writable\n    sysfs_sec_touchkey\n    sysfs_sec_touchscreen\n}:dir r_dir_perms;\n\nallow hal_lineage_touch_default {\n    sysfs_homebutton_writable\n    sysfs_sec_touchkey\n    sysfs_sec_touchscreen\n}:file rw_file_perms;\n",
}
AFTER = {
    "file_contexts": "/sys/devices/virtual/sec/tsp/cmd    u:object_r:sysfs_touchscreen_writable:s0",
    "hal_lineage_touch_default.te": "# hal_lineage_touch_default.te\n\nallow hal_lineage_touch_default {\n    sysfs_homebutton_writable\n    sysfs_sec_touchkey\n    sysfs_sec_touchscreen\n}:dir r_dir_perms;\n\nallow hal_lineage_touch_default {\n    sysfs_homebutton_writable\n    sysfs_sec_touchkey\n    sysfs_touchscreen_writable\n}:file rw_file_perms;\n\nallow hal_lineage_touch_default sysfs_sec_touchscreen:file r_file_perms;\n",
}

def blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def apply(root):
    directory = Path(root) / "sepolicy/vendor"
    updates = {}
    for name, sha in EXPECTED_BLOBS.items():
        path = directory / name
        data = path.read_bytes()
        current = data.decode()
        before, after = BEFORE[name], AFTER[name]
        if current.count(after) == 1 and current.count(before) == 0:
            continue
        if blob_sha(data) != sha or current.count(before) != 1:
            raise ValueError("Unexpected pinned touch policy: " + name)
        updates[path] = current.replace(before, after, 1)
    for path, content in updates.items():
        path.write_text(content)
    return len(updates)

if __name__ == "__main__":
    print("Touch policy files updated:", apply(sys.argv[1]))
