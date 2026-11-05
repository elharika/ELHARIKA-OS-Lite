#!/usr/bin/env python3
"""Exercise ARM EABI helper syscalls under QEMU with user xattrs, not SELinux."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

helper = str(Path(sys.argv[1]).resolve())
with tempfile.TemporaryDirectory() as directory:
    root=Path(directory); reference=root/'reference'; target=root/'target'
    reference.write_bytes(b'reference'); target.write_bytes(b'preserve-target-data')
    attribute='user.elharika-label-test'; label=b'u:object_r:system_file:s0\0'
    os.setxattr(reference,attribute,label)
    def run(destination):
        return subprocess.run(['qemu-arm',helper,str(reference),str(destination)],capture_output=True)
    result=run(target)
    assert result.returncode == 0, result.stderr
    assert os.getxattr(target,attribute) == label
    assert target.read_bytes() == b'preserve-target-data'
    os.setxattr(reference,attribute,b'foreign-label\0')
    assert run(target).returncode != 0
    assert os.getxattr(target,attribute) == label
    os.setxattr(reference,attribute,label)
    result=run(root/'missing')
    assert result.returncode != 0 and b'errno/status=2' in result.stderr, result.stderr
print('ARM EABI user-xattr copy, readback, bad-reference rejection and errno reporting passed under QEMU.')
print('This does not verify SELinux labeling under the tablet recovery kernel.')
