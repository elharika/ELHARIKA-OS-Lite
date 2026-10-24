#!/usr/bin/env python3
"""Stage hash-verified SM-P900 files for integration; not a vendor build or ROM."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
from verify_stock_blobs import digest, dump, safe_path


def stage(image, baseline, output):
    identity = baseline['identity']
    if (identity.get('model'), identity.get('device'), identity.get('build')) != (
            'SM-P900', 'v1awifi', 'P900XXS0BPL4'):
        raise ValueError('Only the inspected SM-P900 stock baseline is accepted')
    records = []
    destinations = {}
    duplicates = []
    for r in baseline['comparison']['records']:
        safe_path(r['source'])
        dest = safe_path(r['destination'])
        if dest in destinations:
            previous = destinations[dest]
            if (r['source'], r.get('sha256')) != (previous['source'], previous.get('sha256')):
                raise ValueError('Conflicting destination: ' + dest)
            duplicates.append(dest)
            continue
        destinations[dest] = r
        records.append(r)
    if output.exists():
        raise ValueError('Output must not exist')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Temporary staging keeps incomplete results out of the final directory.
    with tempfile.TemporaryDirectory(prefix='elharika-stage-', dir='/tmp') as temporary:
        temporary = Path(temporary)
        prop = temporary / 'build.prop'
        if not dump(image, 'build.prop', prop):
            raise ValueError('No system build.prop')
        props = dict(line.split('=', 1) for line in prop.read_text().splitlines()
                     if '=' in line and not line.lstrip().startswith('#'))
        for key, value in [('ro.product.model', 'SM-P900'), ('ro.product.device', 'v1awifi'),
                           ('ro.build.PDA', 'P900XXS0BPL4')]:
            if props.get(key) != value:
                raise ValueError('Wrong image identity: ' + key)
        package = temporary / 'package'
        package.mkdir()
        staged, missing = [], []
        for index, r in enumerate(records):
            candidate = temporary / str(index)
            if not dump(image, r['source'], candidate):
                missing.append(r['source'])
                continue
            checksum = digest(candidate)
            if checksum != r.get('sha256'):
                raise ValueError('Unexpected blob bytes: ' + r['source'])
            destination = package / 'proprietary' / r['destination']
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(candidate, destination)
            staged.append({'source': r['source'], 'destination': r['destination'],
                           'sha256': checksum, 'bytes': destination.stat().st_size,
                           'runtime_compatibility': 'NOT_TESTED'})
        report = {'identity': identity, 'status': 'INCOMPLETE_NOT_FLASHABLE',
                  'staged_count': len(staged), 'missing': missing, 'files': staged,
                  'identical_duplicate_entries_removed': duplicates}
        (package / 'staging.json').write_text(json.dumps(report, indent=2) + '\n')
        (package / 'SHA256SUMS').write_text(''.join(
            f"{r['sha256']}  proprietary/{r['destination']}\n" for r in staged))
        (package / 'README.txt').write_text(
            'Development staging only. Not an Android vendor partition or flashable package.\n'
            'No missing file substitutions, HAL declarations, executable modes or SELinux labels are inferred.\n'
            'Review licenses before redistribution. Android integration and device tests are pending.\n')
        shutil.copytree(package, output)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--system-image', type=Path, required=True)
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    report = stage(a.system_image, json.loads(a.baseline.read_text()), a.output)
    print(json.dumps({'staged': report['staged_count'], 'missing': report['missing'],
                      'status': report['status']}, indent=2))
