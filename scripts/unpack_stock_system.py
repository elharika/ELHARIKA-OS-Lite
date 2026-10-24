#!/usr/bin/env python3
"""Extract only system.img from the hash-pinned SM-P900 stock ZIP and expand it."""
import argparse
import hashlib
from pathlib import Path
import shutil
import struct
import tarfile
import zipfile

SHA256 = 'c5f281c6bec43ef6396adac3300b109e0e4d6f454a55fb4971cb068b010ad0c9'
AP = 'AP_P900XXS0BPL4_CL8087559_QB11789287_REV00_user_low_ship.tar.md5'
MAX_IMAGE = 4 * 1024**3


def exact(f, size):
    data = f.read(size)
    if len(data) != size:
        raise ValueError('Truncated sparse image')
    return data


def expand(source, target):
    with open(source, 'rb') as src, open(target, 'xb') as dst:
        magic, major, minor, fh, ch, block, count, chunks, crc = struct.unpack('<I4H4I', exact(src, 28))
        if magic != 0xed26ff3a or major != 1 or fh < 28 or ch < 12 or block == 0 or block % 4:
            raise ValueError('Invalid sparse header')
        if block * count > MAX_IMAGE:
            raise ValueError('Oversized sparse output')
        exact(src, fh - 28)
        written = 0
        for _ in range(chunks):
            kind, reserved, blocks, total = struct.unpack('<2H2I', exact(src, 12))
            exact(src, ch - 12)
            size = blocks * block
            payload = total - ch
            if payload < 0 or written + blocks > count:
                raise ValueError('Invalid chunk bounds')
            if kind == 0xcac1 and payload == size:
                left = size
                while left:
                    data = exact(src, min(left, 1024**2))
                    dst.write(data)
                    left -= len(data)
            elif kind == 0xcac2 and payload == 4:
                pattern = exact(src, 4)
                left = size
                while left:
                    n = min(left, 1024**2)
                    dst.write(pattern * (n // 4))
                    left -= n
            elif kind == 0xcac3 and payload == 0:
                dst.seek(size, 1)
            elif kind == 0xcac4 and payload == 4 and blocks == 0:
                exact(src, 4)  # CRC not independently validated; pinned ZIP hash checked first.
            else:
                raise ValueError('Unsupported or malformed sparse chunk')
            written += blocks
        if written != count or src.read(1):
            raise ValueError('Sparse length mismatch')
        dst.truncate(count * block)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('zip', type=Path)
    p.add_argument('output', type=Path, help='New output directory; refuses existing paths')
    args = p.parse_args()
    h = hashlib.sha256()
    with args.zip.open('rb') as f:
        for chunk in iter(lambda: f.read(1024**2), b''):
            h.update(chunk)
    if h.hexdigest() != SHA256:
        p.error('ZIP does not match the inspected SM-P900 stock archive')
    args.output.mkdir(parents=True, exist_ok=False)
    sparse = args.output / 'system.sparse'
    with zipfile.ZipFile(args.zip) as z:
        with z.open(AP) as ap, tarfile.open(fileobj=ap, mode='r|') as tar:
            found = False
            for member in tar:
                if member.name == 'system.img':
                    if found or not member.isfile() or member.size > MAX_IMAGE:
                        raise ValueError('Invalid system member')
                    with sparse.open('xb') as out:
                        shutil.copyfileobj(tar.extractfile(member), out, 1024**2)
                    found = True
            if not found:
                raise ValueError('No system.img in pinned AP archive')
    expand(sparse, args.output / 'system.ext4')
    print('Extracted system image only. No bootloader, PIT or recovery extracted. No flash performed.')


if __name__ == '__main__':
    main()
