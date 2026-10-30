#!/usr/bin/env python3
"""Build the pinned local manifest needed for the SM-P900 Android 11 source tree."""
import argparse
import copy
import re
import xml.etree.ElementTree as ET
from pathlib import Path

# Reduced repo groups save tens of GB, but a few build-critical projects are
# tagged upstream as pdk/cts/vts and therefore disappear even though ordinary
# Soong product graph setup still references their module types/rules.
# Keep only the exact projects proven necessary by failed preflights, pinned to
# revisions captured from the last known-good full Android 11 sync.
REQUIRED_PLATFORM_PROJECTS = (
    {
        'name': 'kernel/configs',
        'path': 'kernel/configs',
        'remote': 'elharika-aosp',
        'revision': 'e4102999005f8f3c8db1fdacfba80a2c581a72f1',
    },
    {
        'name': 'platform/test/suite_harness',
        'path': 'test/suite_harness',
        'remote': 'elharika-aosp',
        'revision': '3a5b1207c2177d72db24da78aba86574d95c26f8',
    },
)


def overlay(platform, hardware):
    out = ET.Element('manifest')
    ET.SubElement(out, 'remote', {'name': 'elharika-hardware', 'fetch': 'https://github.com/'})
    ET.SubElement(out, 'remote', {'name': 'elharika-aosp', 'fetch': 'https://android.googlesource.com/'})

    projects = platform.findall('project')
    removed = set()
    paths = set()

    # These projects can still exist in the upstream manifest while repo group
    # filtering omits them from the actual sync. Adding a second declaration at
    # the same path causes repo to abort. Remove the upstream declaration first,
    # then re-add exactly one fully pinned declaration without pdk/cts/vts groups.
    for required in REQUIRED_PLATFORM_PROJECTS:
        ET.SubElement(
            out,
            'remove-project',
            {'name': required['name'], 'optional': 'true'},
        )
        removed.add(required['name'])
        out.append(ET.Element('project', required))

    for project in hardware.findall('project'):
        path = project.get('path')
        name = project.get('name')
        rev = project.get('revision', '')
        if not path or not name or not re.fullmatch('[0-9a-f]{40}', rev):
            raise ValueError('Hardware projects must be fully pinned')
        if path in paths:
            raise ValueError('Duplicate hardware path')
        paths.add(path)
        for existing in projects:
            if existing.get('path', existing.get('name')) == path or existing.get('name') == name:
                old = existing.get('name')
                if old not in removed:
                    ET.SubElement(out, 'remove-project', {'name': old})
                    removed.add(old)
        p = copy.deepcopy(project)
        p.set('remote', 'elharika-hardware')
        out.append(p)

    if 'device/samsung/v1awifi' not in paths:
        raise ValueError('SM-P900 target missing')
    return out


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('platform', type=Path)
    p.add_argument('hardware', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    root = overlay(ET.parse(a.platform).getroot(), ET.parse(a.hardware).getroot())
    ET.indent(root)
    with a.output.open('xb') as f:
        ET.ElementTree(root).write(f, encoding='utf-8', xml_declaration=True)
