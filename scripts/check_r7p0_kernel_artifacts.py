#!/usr/bin/env python3
"""Fail closed if a compiled r7p0 kernel lacks its GPU registration code."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

FLAGS = ('CONFIG_MALI_T6XX_R7P0=y',
         '# CONFIG_MALI_T6XX_R15P0 is not set',
         'CONFIG_SOC_EXYNOS5420=y')


def inspect(kernel_obj):
    root = Path(kernel_obj)
    config = root / '.config'
    if not config.is_file():
        raise ValueError('Kernel .config missing')
    lines = config.read_text().splitlines()
    for flag in FLAGS:
        if lines.count(flag) != 1:
            raise ValueError('Expected kernel flag not enabled: ' + flag)
    objects = [root / 'drivers/gpu/arm/t6xx/r7p0/mali_kbase.o',
               root / 'drivers/gpu/arm/t6xx/r7p0/platform/exynos/gpu_exynos5420.o',
               root / 'vmlinux']
    checksums = {}
    for path in objects:
        if not path.is_file() or path.stat().st_size < 4096:
            raise ValueError('Missing/empty GPU binary: ' + str(path))
        checksums[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in (objects[0], objects[2]):
        nm = subprocess.check_output(['nm', str(path)], text=True)
        if not re.search(r'\skbase_platform_driver\s*$', nm, flags=re.M):
            raise ValueError('kbase_platform_driver symbol not linked: ' + str(path))
    return {'status': 'STATIC_OBJECTS_AND_LINKED_SYMBOL_VERIFIED',
            'config': list(FLAGS), 'sha256': checksums,
            'hardware_tested': False, 'flash_approved': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kernel_obj', type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    result = inspect(args.kernel_obj)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
