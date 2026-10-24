#!/usr/bin/env python3
"""Read-only ext4 extraction and ELF inventory; never certifies runtime compatibility."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile


def safe_path(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_./@+:-]+', value):
        raise ValueError('Invalid image path')
    p = PurePosixPath(value)
    if p.is_absolute() or '..' in p.parts or value in ('', '.'):
        raise ValueError('Path must stay inside the system image')
    return value


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def dump(image, source, target):
    # Generated destination names cannot inject debugfs command syntax.
    source = safe_path(source)
    if not re.fullmatch(r'[A-Za-z0-9_./-]+', str(target)):
        raise ValueError('Unsafe temporary destination')
    result = subprocess.run(['debugfs', '-R', f'dump /{source} {target}', str(image)],
                            capture_output=True, text=True, timeout=120)
    # debugfs can return zero even for a missing inode.
    return result.returncode == 0 and target.is_file()


def elf_info(path):
    with open(path, 'rb') as f:
        header = f.read(20)
    if header[:4] != b'\x7fELF':
        return None
    if len(header) < 20 or header[5] not in (1, 2):
        raise ValueError('Truncated or invalid ELF header')
    machine = int.from_bytes(header[18:20], 'little' if header[5] == 1 else 'big')
    result = subprocess.run(['readelf', '-W', '-d', '--dyn-syms', str(path)],
                            capture_output=True, text=True, timeout=30,
                            env={**os.environ, 'LC_ALL': 'C'})
    if result.returncode:
        raise ValueError('readelf failed: ' + result.stderr[:300])
    needed = re.findall(r'\(NEEDED\).*?\[([^\]]+)\]', result.stdout)
    undefined = []
    for line in result.stdout.splitlines():
        cols = line.split()
        if len(cols) >= 8 and cols[6] == 'UND':
            undefined.append({'name': cols[7], 'binding': cols[4]})
    return {'class': header[4], 'machine': machine, 'endianness': header[5],
            'arm32_little_endian': header[4] == 1 and header[5] == 1 and machine == 40,
            'needed': sorted(set(needed)), 'undefined_symbols': undefined}


def verify(image, baseline, output):
    expected = baseline['identity']
    if expected['model'] != 'SM-P900' or expected['device'] != 'v1awifi':
        raise ValueError('Baseline must target SM-P900/v1awifi')
    records = baseline['comparison']['records']
    for record in records:
        safe_path(record['source'])
    with tempfile.TemporaryDirectory(prefix='elharika-', dir='/tmp') as tmp:
        tmp = Path(tmp)
        prop = tmp / 'build.prop'
        if not dump(image, 'build.prop', prop):
            raise ValueError('Missing build.prop; supply expanded system ext4 image')
        props = dict(line.split('=', 1) for line in prop.read_text().splitlines()
                     if '=' in line and not line.lstrip().startswith('#'))
        for key, value in [('ro.product.model', 'SM-P900'), ('ro.product.device', 'v1awifi'),
                           ('ro.build.PDA', expected['build'])]:
            if props.get(key) != value:
                raise ValueError('Image identity mismatch: ' + key)
        results = []
        for i, record in enumerate(records):
            path = tmp / str(i)
            item = {'source': record['source'], 'android11_compatible': 'NOT_TESTED'}
            item['present'] = dump(image, record['source'], path)
            if item['present']:
                item['sha256'] = digest(path)
                item['baseline_match'] = item['sha256'] == record.get('sha256')
                item['elf'] = elf_info(path)
            results.append(item)
        present_names = {PurePosixPath(r['source']).name for r in results if r['present']}
        for item in results:
            if item.get('elf'):
                item['elf']['needed_not_in_extracted_set'] = sorted(
                    set(item['elf']['needed']) - present_names)
        report = {'identity': expected, 'runtime_compatibility': 'NOT_TESTED',
                  'note': 'Missing dependencies may be supplied by Android. Names alone do not prove symbol or linker namespace compatibility.',
                  'records': results}
        output.write_text(json.dumps(report, indent=2) + '\n')
        # Nonzero prevents this inventory being mistaken for validated integration.
        return 0 if all(r['present'] and r.get('baseline_match') for r in results) else 2


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--system-image', type=Path, required=True)
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    args = p.parse_args()
    if args.report.resolve() in (args.system_image.resolve(), args.baseline.resolve()):
        p.error('Report must not overwrite either input')
    return verify(args.system_image, json.loads(args.baseline.read_text()), args.report)


if __name__ == '__main__':
    raise SystemExit(main())
