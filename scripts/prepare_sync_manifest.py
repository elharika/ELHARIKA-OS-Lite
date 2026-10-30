#!/usr/bin/env python3
"""Build the pinned local manifest needed for the SM-P900 Android 11 source tree."""
import argparse
import copy
import re
import xml.etree.ElementTree as ET
from pathlib import Path

# Reduced repo groups save tens of GB, but Soong still parses generated VTS/HIDL
# modules during the product graph. Re-add the exact VTS-group projects from the
# last known-good full Android 11 sync, plus suite_harness, without restoring CTS
# or the full PDK groups. Every project is pinned to its captured revision.
REQUIRED_PLATFORM_PROJECTS = ({'name': 'kernel/configs',
  'path': 'kernel/configs',
  'remote': 'elharika-aosp',
  'revision': 'e4102999005f8f3c8db1fdacfba80a2c581a72f1'},
 {'name': 'kernel/tests',
  'path': 'kernel/tests',
  'remote': 'elharika-aosp',
  'revision': '0b69217c71fdb04e6e2dea74443ebe3e4391104a'},
 {'name': 'platform/external/linux-kselftest',
  'path': 'external/linux-kselftest',
  'remote': 'elharika-aosp',
  'revision': '96e90b20779b769488086463fd3db9d6a70744ea'},
 {'name': 'platform/external/ltp',
  'path': 'external/ltp',
  'remote': 'elharika-aosp',
  'revision': 'b506acbca227f177bf3534ff0b32404078c000fb'},
 {'name': 'platform/external/python/enum34',
  'path': 'external/python/enum34',
  'remote': 'elharika-aosp',
  'revision': 'de9878e3b12f11d41ae97ee16c62ac7dcbb8e69f'},
 {'name': 'platform/external/python/futures',
  'path': 'external/python/futures',
  'remote': 'elharika-aosp',
  'revision': '89a8fe6ab75db54c27ab073acda54b57b3a1187b'},
 {'name': 'platform/external/python/google-api-python-client',
  'path': 'external/python/google-api-python-client',
  'remote': 'elharika-aosp',
  'revision': '4c93867c0a194da55c6e6958046754aa70fbc2f0'},
 {'name': 'platform/external/python/httplib2',
  'path': 'external/python/httplib2',
  'remote': 'elharika-aosp',
  'revision': '31f091c0ae1c78c65214d8c6c94938e00fe9f6e2'},
 {'name': 'platform/external/python/oauth2client',
  'path': 'external/python/oauth2client',
  'remote': 'elharika-aosp',
  'revision': '48bbe85f5376bdd485cbe92d8abea459c31d6034'},
 {'name': 'platform/external/python/parse_type',
  'path': 'external/python/parse_type',
  'remote': 'elharika-aosp',
  'revision': 'b3dec94033e2397772f630e456ee4ed148da0b49'},
 {'name': 'platform/external/python/pyasn1',
  'path': 'external/python/pyasn1',
  'remote': 'elharika-aosp',
  'revision': '3840362825124737bc1b9fb4bf45f937de64fb38'},
 {'name': 'platform/external/python/pyasn1-modules',
  'path': 'external/python/pyasn1-modules',
  'remote': 'elharika-aosp',
  'revision': 'c340f08f61bbea0a35f7030eba6c67b93cbd43e2'},
 {'name': 'platform/external/python/rsa',
  'path': 'external/python/rsa',
  'remote': 'elharika-aosp',
  'revision': '50feeefb8baf91ea1f81ba16428c270706f6d1ca'},
 {'name': 'platform/external/python/setuptools',
  'path': 'external/python/setuptools',
  'remote': 'elharika-aosp',
  'revision': '513ec3d6bb6f7786d02caf51720497a118b8f4be'},
 {'name': 'platform/external/python/six',
  'path': 'external/python/six',
  'remote': 'elharika-aosp',
  'revision': 'bc5b71ea687cbe1a5675215e617d1f4b310cc4e5'},
 {'name': 'platform/external/python/uritemplates',
  'path': 'external/python/uritemplates',
  'remote': 'elharika-aosp',
  'revision': 'e9b8a40534df1b0de66ee1d6581ce657a6f9eee9'},
 {'name': 'platform/external/yapf',
  'path': 'external/yapf',
  'remote': 'elharika-aosp',
  'revision': '45d923c40605a71867d174abcd04a1db76945651'},
 {'name': 'platform/test/framework',
  'path': 'test/framework',
  'remote': 'elharika-aosp',
  'revision': 'c44480ac572c0eeaded19fa1c70833fcac21bfd0'},
 {'name': 'platform/test/vti/dashboard',
  'path': 'test/vti/dashboard',
  'remote': 'elharika-aosp',
  'revision': 'a9bd47e4caa21d535fb89c0e6efe23fa08d25847'},
 {'name': 'platform/test/vti/fuzz_test_serving',
  'path': 'test/vti/fuzz_test_serving',
  'remote': 'elharika-aosp',
  'revision': '6319e3d94c65669050c49c6ca570096d41823b82'},
 {'name': 'platform/test/vti/test_serving',
  'path': 'test/vti/test_serving',
  'remote': 'elharika-aosp',
  'revision': 'bdaf2327fefdb061abb03896d0eed6e776a7d6d7'},
 {'name': 'platform/test/vts',
  'path': 'test/vts',
  'remote': 'elharika-aosp',
  'revision': 'f001416f91f7f02a7a042bd0c52f0c62394fa78c'},
 {'name': 'platform/test/vts-testcase/fuzz',
  'path': 'test/vts-testcase/fuzz',
  'remote': 'elharika-aosp',
  'revision': '43fcddcde333cac6b365ea32f0fecc3a2c9d7ff8'},
 {'name': 'platform/test/vts-testcase/hal',
  'path': 'test/vts-testcase/hal',
  'remote': 'elharika-aosp',
  'revision': '430829c9435b28f605cac28b930586281ec674f7'},
 {'name': 'platform/test/vts-testcase/hal-trace',
  'path': 'test/vts-testcase/hal-trace',
  'remote': 'elharika-aosp',
  'revision': '2695892568f8fade958ec0ec172df8f295ae4112'},
 {'name': 'platform/test/vts-testcase/kernel',
  'path': 'test/vts-testcase/kernel',
  'remote': 'elharika-aosp',
  'revision': '86e06938eddc05ef961d0f398369d222c6d60d34'},
 {'name': 'platform/test/vts-testcase/nbu',
  'path': 'test/vts-testcase/nbu',
  'remote': 'elharika-aosp',
  'revision': '0712e2a442364af77a0b1dda0adf922d1d1447bc'},
 {'name': 'platform/test/vts-testcase/performance',
  'path': 'test/vts-testcase/performance',
  'remote': 'elharika-aosp',
  'revision': 'f0e5dcee43de6f9c44a3872721087d96eaa48273'},
 {'name': 'platform/test/vts-testcase/security',
  'path': 'test/vts-testcase/security',
  'remote': 'elharika-aosp',
  'revision': 'fff787f02b16ddd7a40d6252f06c6c8a5f5fff4c'},
 {'name': 'platform/test/vts-testcase/vndk',
  'path': 'test/vts-testcase/vndk',
  'remote': 'elharika-aosp',
  'revision': '66a450e3cc08e79d346047280113d8d690918118'},
 {'name': 'platform/tools/acloud',
  'path': 'tools/acloud',
  'remote': 'elharika-aosp',
  'revision': '24d4a06dd195458321c206fbacd8333e129d1af7'},
 {'name': 'platform/test/suite_harness',
  'path': 'test/suite_harness',
  'remote': 'elharika-aosp',
  'revision': '3a5b1207c2177d72db24da78aba86574d95c26f8'})


def overlay(platform, hardware):
    out = ET.Element('manifest')
    ET.SubElement(out, 'remote', {'name': 'elharika-hardware', 'fetch': 'https://github.com/'})
    ET.SubElement(out, 'remote', {'name': 'elharika-aosp', 'fetch': 'https://android.googlesource.com/'})

    projects = platform.findall('project')
    removed = set()
    paths = set()

    # The upstream declarations can remain in the manifest even when repo group
    # filtering omits them from sync. Remove first, then add one fully pinned
    # no-groups declaration so repo cannot see duplicate paths.
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
