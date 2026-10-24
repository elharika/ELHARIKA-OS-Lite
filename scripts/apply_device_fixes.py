#!/usr/bin/env python3
"""Apply reviewed configuration fixes only to exact pinned upstream file contents."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

PATCH_DIR = Path(__file__).resolve().parents[1] / 'patches/universal5420-common'


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply(source, patch_dir=PATCH_DIR):
    source = source.resolve()
    manifest = json.loads((patch_dir / 'manifest.json').read_text())
    records = manifest['files']
    for item in records:
        target = (source / item['path']).resolve()
        if not target.is_relative_to(source) or not target.is_file():
            raise ValueError('Missing or unsafe source path: ' + item['path'])
    hashes = [checksum(source / r['path']) for r in records]
    if hashes == [r['after_sha256'] for r in records]:
        return 'already applied'
    if hashes != [r['before_sha256'] for r in records]:
        raise ValueError('Source differs from pinned files; no changes made')
    patch = (patch_dir / '0001-policy-and-audio-config.patch').resolve()
    subprocess.run(['git', 'apply', '--check', str(patch)], cwd=source, check=True)
    subprocess.run(['git', 'apply', str(patch)], cwd=source, check=True)
    if [checksum(source / r['path']) for r in records] != [r['after_sha256'] for r in records]:
        raise ValueError('Post-apply verification failed')
    return 'applied; full Android policy compilation and device tests still required'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='device/samsung/universal5420-common directory')
    args = parser.parse_args()
    print(apply(args.source))
