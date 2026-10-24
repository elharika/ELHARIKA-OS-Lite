#!/usr/bin/env python3
"""Collect bounded, read-only SM-P900 diagnostics via ADB, including recovery mode."""
import argparse
import json
from pathlib import Path
import subprocess
import time


def command(argv, timeout=30):
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return {'returncode': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr}
    except subprocess.TimeoutExpired:
        return {'returncode': 124, 'stdout': '', 'stderr': 'Command timed out'}


def collect(output, serial=None):
    if output.exists(): raise ValueError('Output directory must be new')
    adb = ['adb'] + (['-s', serial] if serial else [])
    model = command(adb + ['shell', 'getprop', 'ro.product.model'])
    device = command(adb + ['shell', 'getprop', 'ro.product.device'])
    if model['stdout'].strip() != 'SM-P900' or device['stdout'].strip() != 'v1awifi':
        raise ValueError('ADB identity must be SM-P900/v1awifi; no diagnostics collected')
    state = command(adb + ['shell', 'getprop', 'ro.bootmode'])['stdout'].strip()
    recovery = command(adb + ['shell', 'getprop', 'ro.twrp.version'])['stdout'].strip()
    probes = {
      'input_devices': ['cat', '/proc/bus/input/devices'],
      'input_capabilities': ['getevent', '-lp'],
      'memory': ['cat', '/proc/meminfo'],
      'kernel': ['uname', '-a'],
      'mounts': ['cat', '/proc/mounts'],
      'selinux': ['getenforce'],
      'boot_completed': ['getprop', 'sys.boot_completed'],
    }
    if not recovery and state != 'recovery':
        probes.update({
          'battery': ['dumpsys', 'battery'], 'thermal': ['dumpsys', 'thermalservice'],
          'input': ['dumpsys', 'input'], 'graphics': ['dumpsys', 'SurfaceFlinger'],
          'sensors': ['dumpsys', 'sensorservice'], 'audio': ['dumpsys', 'media.audio_flinger'],
        })
    output.mkdir(parents=True)
    results = {name: command(adb + ['shell'] + args) for name, args in probes.items()}
    report = {'model': 'SM-P900', 'device': 'v1awifi',
              'captured_unix': int(time.time()), 'recovery_detected': bool(recovery or state == 'recovery'),
              'note': 'Read-only observations, not functional PASS results. No reboot, flash, input injection or settings changes.',
              'probes': results}
    (output / 'device-observations.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--serial', help='Select a device when more than one is connected')
    a = p.parse_args()
    r = collect(a.output, a.serial)
    print('Saved read-only observations; functional tests remain NOT_TESTED.')
