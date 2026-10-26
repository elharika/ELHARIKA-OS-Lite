#!/usr/bin/env python3
"""Correct video16's video label without granting graphics access to audio."""
from pathlib import Path
import hashlib
import sys

RULES = {
    "file_contexts": (
        "5d0e747ce66adb6bdfa088b48de8baac7c8c1d93",
        "/dev/video16             u:object_r:audio_device:s0",
        "/dev/video16             u:object_r:video_device:s0",
    ),
    "hal_graphics_composer_default.te": (
        "c41741aed80737b167d52799fb51f6c94cb6518d",
        "allow hal_graphics_composer_default audio_device:chr_file rw_file_perms;\n\n",
        "",
    ),
}
def blob_sha(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def apply(root):
    directory = Path(root) / "sepolicy/vendor"
    updates = {}
    for name, (expected, before, after) in RULES.items():
        path = directory / name
        raw = path.read_bytes()
        content = raw.decode()
        if before and content.count(before) == 0:
            # Idempotence requires the exact transformed upstream file.
            original = content.replace(after, before, 1) if after else None
            if original is not None and blob_sha(original.encode()) == expected:
                continue
            if after == "" and content.startswith("# hal_graphics_composer_default.te\n\n"):
                candidate = content.replace("# hal_graphics_composer_default.te\n\n",
                                            "# hal_graphics_composer_default.te\n\n" + before, 1)
                if blob_sha(candidate.encode()) == expected:
                    continue
            raise ValueError("Unexpected transformed policy: " + name)
        if blob_sha(raw) != expected or content.count(before) != 1:
            raise ValueError("Unexpected pinned policy: " + name)
        updates[path] = content.replace(before, after, 1)
    for path, content in updates.items():
        path.write_text(content)
    return len(updates)

if __name__ == "__main__":
    print("Graphics policy files updated:", apply(sys.argv[1]))
