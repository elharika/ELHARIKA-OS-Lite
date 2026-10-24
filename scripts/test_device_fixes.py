#!/usr/bin/env python3
"""Integration test against a pristine checkout of the pinned common device source."""
import argparse
from pathlib import Path
import shutil
import tempfile
import uuid
import xml.etree.ElementTree as ET
from apply_device_fixes import apply

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('source', type=Path)
a = p.parse_args()
with tempfile.TemporaryDirectory() as tmp:
    dst = Path(tmp) / 'source'
    shutil.copytree(a.source, dst)
    assert apply(dst).startswith('applied;')
    assert apply(dst) == 'already applied'
    root = ET.parse(dst / 'configs/audio/audio_effects.xml').getroot()
    ids = [e.attrib['uuid'] for e in root.iter() if 'uuid' in e.attrib]
    assert len(ids) == 17 and len(set(ids)) == 17
    assert all(str(uuid.UUID(s)) == s for s in ids)
    board = dst / 'BoardConfigCommon.mk'
    assert 'SELINUX_IGNORE_NEVERALLOWS := false' in board.read_text()
    board.write_text(board.read_text() + '\n# local change\n')
    before = {f: f.read_bytes() for f in dst.rglob('*') if f.is_file()}
    try:
        apply(dst)
    except ValueError:
        pass
    else:
        raise AssertionError('Modified source was accepted')
    assert all(f.read_bytes() == b for f, b in before.items())
print('PASS: apply, idempotence, 17 UUIDs, neverallow setting, drift rejection without writes')
