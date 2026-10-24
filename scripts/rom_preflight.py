#!/usr/bin/env python3
"""Inventory an Android build worker; readiness is not a compatibility certification."""
import argparse
import json
import os
from pathlib import Path
import platform
import re
import shutil
import xml.etree.ElementTree as ET

REQUIRED = [
 'build/envsetup.sh', 'build/soong/soong_ui.bash',
 'vendor/elharika/AndroidProducts.mk', 'vendor/elharika/elharika_v1awifi.mk',
 'vendor/elharika/apps/pen/Android.bp', 'vendor/elharika/apps/launcher/Android.bp',
 'device/samsung/v1awifi/AndroidProducts.mk',
 'device/samsung/v1awifi/lineage_v1awifi.mk',
 'device/samsung/universal5420-common/BoardConfigCommon.mk',
 'kernel/samsung/exynos5420/Makefile',
 'vendor/samsung/v1awifi/v1awifi-vendor.mk',
 'vendor/samsung/v1a-common/v1a-common-vendor.mk',
 'vendor/samsung/universal5420-common/universal5420-common-vendor.mk',
 'vendor/lineage/config/common_full_tablet_wifionly.mk',
]


def inspect(root, min_disk_gib=200, min_ram_gib=16):
    if not root.is_dir():
        raise ValueError('Android source directory does not exist')
    memory = {}
    if Path('/proc/meminfo').is_file():
        for line in Path('/proc/meminfo').read_text().splitlines():
            key, value = line.split(':', 1)
            memory[key] = int(value.split()[0]) * 1024
    free = shutil.disk_usage(root).free
    ram = memory.get('MemTotal', 0)
    cpu = len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else (os.cpu_count() or 1)
    missing = [p for p in REQUIRED if not (root / p).is_file()]
    blockers = ['missing:' + p for p in missing]
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'AMD64'):
        blockers.append('requires Linux x86_64 worker')
    if free < min_disk_gib * 1024**3:
        blockers.append('disk below project planning threshold')
    if ram < min_ram_gib * 1024**3:
        blockers.append('RAM below project planning threshold')
    for tool in ['git', 'make', 'python3', 'repo']:
        if not shutil.which(tool): blockers.append('missing tool:' + tool)
    locked = root / 'elharika-platform-lock.xml'
    if not locked.is_file():
        blockers.append('missing full platform lock: run repo manifest -r -o elharika-platform-lock.xml after sync')
    else:
        projects = ET.parse(locked).getroot().findall('project')
        if not projects or any(not re.fullmatch('[0-9a-f]{40}', p.get('revision', '')) for p in projects):
            blockers.append('platform lock must contain commit-pinned projects')
    board = root / 'device/samsung/universal5420-common/BoardConfigCommon.mk'
    if board.is_file() and re.search(r'^\s*SELINUX_IGNORE_NEVERALLOWS\s*:?=\s*true', board.read_text(), re.M):
        blockers.append('upstream neverallow bypass still enabled; apply reviewed device fixes')
    return {'status': 'BLOCKED' if blockers else 'PREFLIGHT_PASSED_NOT_HARDWARE_VALIDATED',
            'machine': platform.machine(), 'cpu_available': cpu,
            'disk_free_bytes': free, 'ram_total_bytes': ram,
            'suggested_jobs': max(1, min(cpu, max(1, int(ram / 1024**3) // 4))),
            'planning_thresholds': {'disk_gib': min_disk_gib, 'ram_gib': min_ram_gib,
                'note': 'Conservative project defaults, not measured Android 11 minimums or proof of sufficient capacity.'},
            'blockers': blockers, 'hardware_tested': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('android_root', type=Path)
    p.add_argument('--report', type=Path, required=True)
    a = p.parse_args()
    report = inspect(a.android_root)
    a.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    raise SystemExit(2 if report['blockers'] else 0)
