#!/usr/bin/env python3
"""Select the pinned kernel's r7p0 DDK for an UNTESTED SM-P900 boot experiment.

Edits a defconfig only; it never creates a boot image or flashes a device.
The source lock protects against applying the change to an unrelated kernel.
"""
import argparse
import json
from pathlib import Path
import subprocess

KERNEL_COMMIT = 'de0cdcf10dcca77b400f15d83c1edf4f264a0f02'
DEFCONFIG = 'arch/arm/configs/lineageos_v1awifi_defconfig'


def patch_defconfig(text):
    if text.count('CONFIG_MALI_T6XX=y\n') != 1:
        raise ValueError('Unexpected Mali T6xx base config')
    old = ('# CONFIG_MALI_T6XX_R7P0 is not set\n',
           'CONFIG_MALI_T6XX_R15P0=y\n')
    new = ('CONFIG_MALI_T6XX_R7P0=y\n',
           '# CONFIG_MALI_T6XX_R15P0 is not set\n')
    if all(text.count(x) == 1 for x in new) and all(x not in text for x in old):
        return text, False
    if any(text.count(x) != 1 for x in old) or any(x in text for x in new):
        raise ValueError('Unknown, conflicting or partially selected Mali DDK')
    result = text.replace(old[0], new[0], 1).replace(old[1], new[1], 1)
    return result, True


def select(android_root):
    root = Path(android_root).resolve()
    kernel = root / 'kernel/samsung/exynos5420'
    if not kernel.is_dir():
        raise ValueError('Expected pinned kernel directory')
    revision = subprocess.check_output(['git', '-C', str(kernel), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != KERNEL_COMMIT:
        raise ValueError('Unexpected kernel revision: ' + revision)
    kconfig = (kernel / 'drivers/gpu/arm/t6xx/Kconfig').read_text()
    for item in ('config MALI_T6XX_R7P0', 'config MALI_T6XX_R15P0',
                 'source "drivers/gpu/arm/t6xx/r7p0/Kconfig"'):
        if item not in kconfig:
            raise ValueError('Pinned kernel does not contain expected r7p0 DDK choice')
    path = kernel / DEFCONFIG
    old_text = path.read_text()
    new_text, did_change = patch_defconfig(old_text)
    if did_change:
        path.write_text(new_text)
    return {
        'status': 'DEFCONFIG_SELECTED_NOT_COMPILED_NOT_HARDWARE_TESTED',
        'kernel_commit': revision,
        'target': 'v1awifi',
        'selected_ddk': 'r7p0',
        'changed': did_change,
        'defconfig': str(path.relative_to(root)),
        'requires_compiled_config_assert': True,
        'requires_paired_userspace_validation': True,
        'flash_approved': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('android_root', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    a = parser.parse_args()
    result = select(a.android_root)
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
