#!/usr/bin/env python3
"""Check actual pinned source transformation; no claim of Android build success."""
import argparse
from pathlib import Path
import shutil
import tempfile
import xml.etree.ElementTree as ET
from apply_device_fixes import apply

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('source', type=Path)
a = p.parse_args()
patchdir = Path(__file__).resolve().parents[1] / 'patches/minimal-profile'
with tempfile.TemporaryDirectory() as d:
    source = Path(d) / 'source'
    shutil.copytree(a.source, source)
    original = (source/'proprietary-files.txt').read_text()
    assert apply(source, patchdir).startswith('applied;')
    assert apply(source, patchdir) == 'already applied'
    current = (source/'proprietary-files.txt').read_text()
    entries = lambda s: {line for line in s.splitlines() if line and not line.startswith('#')}
    removed = entries(original) - entries(current)
    assert len(removed) == 6, removed
    assert not (entries(current) - entries(original))
    for fragment in ['aptX','libaudioroute','widevine','libwvhidl','libwvdrmengine']:
        assert fragment not in current
    for fragment in ['libGLES_mali','libexynoscamera','bcm4350','libstlport','liblvverx','liblvvetx']:
        assert fragment in current
    root = ET.parse(source/'manifest.xml').getroot()
    assert not any('widevine' in (node.text or '') for node in root.iter())
    assert any(node.text == 'android.hardware.drm' for node in root.iter('name'))
    product = (source/'device-common.mk').read_text()
    assert '    libaudioroute \\' in product
    assert 'android.hardware.drm@1.3-service.clearkey' in product
    target = source/'manifest.xml'
    target.write_text(target.read_text()+'\n<!-- local modification -->\n')
    before = target.read_bytes()
    try: apply(source, patchdir)
    except ValueError: pass
    else: raise AssertionError('Source drift was accepted')
    assert target.read_bytes() == before
print('PASS: exact patch, idempotence, six removed entries, DRM consistency, core entries retained, source drift rejection')
