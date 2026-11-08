#!/usr/bin/env python3
"""Do not advertise an unregistered optional IKeyDisabler HAL in SM-P900 trial.

Pinned v1a-common tree has one touch HAL providing ITouchscreenGesture.
Captured boot logs show that IKeyDisabler/default is never registered.
Only the missing IKeyDisabler declaration is dropped; touch gesture HAL remains.
"""
import argparse
import json
from pathlib import Path
import subprocess

TREE_REVISION = '4ae15a9b02c6efb1ffe956ab386fce9b3606ea94'
RELATIVE_PATH = 'device/samsung/v1a-common/manifest.xml'
BEFORE = '''        <interface>
            <name>IKeyDisabler</name>
            <instance>default</instance>
        </interface>
'''
GESTURE = '''        <interface>
            <name>ITouchscreenGesture</name>
            <instance>default</instance>
        </interface>
'''


def patch_manifest(content):
    if content.count('<name>vendor.lineage.touch</name>') != 1 or content.count(GESTURE) != 1:
        raise ValueError('Unexpected Samsung touch HAL layout')
    if content.count(BEFORE) == 0:
        if 'IKeyDisabler' in content:
            raise ValueError('Unknown IKeyDisabler variant; refusing modification')
        return content, False
    if content.count(BEFORE) != 1:
        raise ValueError('Ambiguous IKeyDisabler declaration')
    return content.replace(BEFORE, '', 1), True


def apply(root):
    android = Path(root).resolve()
    source = android / 'device/samsung/v1a-common'
    actual = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != TREE_REVISION:
        raise ValueError('Unexpected pinned v1a-common revision: ' + actual)
    path = android / RELATIVE_PATH
    before = path.read_text()
    after, changed = patch_manifest(before)
    if changed:
        path.write_text(after)
    return {'status': 'OPTIONAL_MISSING_HAL_DECLARATION_REMOVED_FROM_BUILD_TREE',
            'device': 'SM-P900/v1awifi', 'revision': actual,
            'disabled_optional_interface': 'vendor.lineage.touch@1.0::IKeyDisabler/default',
            'preserved_interface': 'vendor.lineage.touch@1.0::ITouchscreenGesture/default',
            'changed': changed, 'flash_approved': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('android_root', type=Path)
    p.add_argument('--report', type=Path, required=True)
    a = p.parse_args()
    result = apply(a.android_root)
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
