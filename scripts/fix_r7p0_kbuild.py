#!/usr/bin/env python3
"""Repair pinned Exynos5420 r7p0 kernel's unreferenced Kbuild symbols.

Source-only; requires the exact known upstream revision and previously selected
r7p0 defconfig. Does not flash a device or assert runtime GPU compatibility.
"""
import argparse
import json
from pathlib import Path
import subprocess

KERNEL_COMMIT = 'de0cdcf10dcca77b400f15d83c1edf4f264a0f02'
KBUILD = 'drivers/gpu/arm/t6xx/r7p0/Kbuild'
PLATFORM_KBUILD = 'drivers/gpu/arm/t6xx/r7p0/platform/exynos/Kbuild'
DEFCONFIG = 'arch/arm/configs/lineageos_v1awifi_defconfig'


def patch_main(content):
    old = 'CONFIG_MALI_R7P0'
    new = 'CONFIG_MALI_T6XX_R7P0'
    if content.count(old) == 0 and content.count(new) == 4:
        return content, False
    if content.count(old) != 4 or content.count(new) != 0:
        raise ValueError('Unexpected r7p0 Kbuild variables / already partially patched')
    targets = (
        'ifeq ($(CONFIG_MALI_R7P0),m)',
        'else ifeq ($(CONFIG_MALI_R7P0),y)',
        'obj-$(CONFIG_MALI_R7P0) += platform/',
        'obj-$(CONFIG_MALI_R7P0) += mali_kbase.o',
    )
    if any(content.count(x) != 1 for x in targets):
        raise ValueError('r7p0 Kbuild layout does not match locked upstream')
    return content.replace(old, new), True


def patch_platform(content):
    old = 'obj-y += gpu_exynos$(platform_name).o'
    new = 'obj-y += gpu_exynos5420.o'
    if content.count(new) == 1 and old not in content:
        return content, False
    if content.count(old) != 1 or new in content:
        raise ValueError('Unexpected Exynos platform Kbuild')
    if 'obj-y += mali_kbase_platform.o' not in content:
        raise ValueError('Missing platform registration object')
    return content.replace(old, new), True


def fix(root):
    root = Path(root).resolve()
    kernel = root / 'kernel/samsung/exynos5420'
    if not kernel.is_dir():
        raise ValueError('Pinned Exynos5420 kernel missing')
    actual_commit = subprocess.check_output(
        ['git', '-C', str(kernel), 'rev-parse', 'HEAD'], text=True).strip()
    if actual_commit != KERNEL_COMMIT:
        raise ValueError('Unexpected kernel revision: ' + actual_commit)
    config = (kernel / DEFCONFIG).read_text()
    for line in ('CONFIG_MALI_T6XX=y', 'CONFIG_MALI_T6XX_R7P0=y',
                 '# CONFIG_MALI_T6XX_R15P0 is not set',
                 'CONFIG_SOC_EXYNOS5420=y',
                 'CONFIG_MALI_PLATFORM_THIRDPARTY_NAME="exynos"'):
        if config.splitlines().count(line) != 1:
            raise ValueError('Missing exact SM-P900 r7p0 config: ' + line)
    main_path = kernel / KBUILD
    platform_path = kernel / PLATFORM_KBUILD
    main_text, main_change = patch_main(main_path.read_text())
    platform_text, platform_change = patch_platform(platform_path.read_text())
    gpu_source = platform_path.parent / 'gpu_exynos5420.c'
    if not gpu_source.is_file():
        raise ValueError('Exynos5420 GPU source missing')
    if main_change:
        main_path.write_text(main_text)
    if platform_change:
        platform_path.write_text(platform_text)
    return {
        'status': 'KBUILD_RULES_PATCHED_NOT_COMPILED_NOT_TESTED_ON_DEVICE',
        'kernel_commit': actual_commit,
        'target': 'v1awifi/Exynos5420',
        'main_kbuild_changed': main_change,
        'platform_kbuild_changed': platform_change,
        'main_obj_selector': 'obj-$(CONFIG_MALI_T6XX_R7P0) += mali_kbase.o',
        'platform_obj_selector': 'obj-y += gpu_exynos5420.o',
        'requires_compiled_object_proof': True,
        'flash_approved': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('android_root', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = fix(args.android_root)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
