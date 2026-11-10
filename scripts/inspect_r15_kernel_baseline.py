#!/usr/bin/env python3
"""Bounded R15 kernel provenance/config inspection. No BOOT repack or flashing."""
import argparse
import hashlib
import json
import lzma
from pathlib import Path
import re
import struct
import zlib

from audit_r15_wacom_boot_pair_readonly import analyze, inspect_zimage

SOURCE_REV = 'de0cdcf10dcca77b400f15d83c1edf4f264a0f02'
MAX_RAW = 64 * 1024 * 1024
MAX_CONFIG = 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def config_values(text):
    result = {}
    for line in text.splitlines():
        unset = re.fullmatch(r'# (CONFIG_[A-Za-z0-9_]+) is not set', line)
        setting = re.fullmatch(r'(CONFIG_[A-Za-z0-9_]+)=(.+)', line)
        if not unset and not setting:
            if line.startswith('CONFIG_') or line.startswith('# CONFIG_'):
                raise ValueError('Malformed kernel config line')
            continue
        name, value = (unset[1], 'n') if unset else setting.groups()
        if name in result:
            raise ValueError('Duplicate kernel config symbol: ' + name)
        result[name] = value
    if not result:
        raise ValueError('No kernel config symbols')
    return result


def extract(kernel):
    info = inspect_zimage(kernel)
    if info['appended_bytes']:
        raise ValueError('Appended kernel data requires separate DTB validation')
    # This exact SM-P900 baseline uses LZMA-alone. Bound both candidate count
    # and output size; do not use an unbounded subprocess decompressor.
    marker = b'\x5d\x00\x00\x00'
    pos = -1
    decoded = None
    for _ in range(32):
        pos = kernel.find(marker, pos + 1)
        if pos < 0:
            break
        try:
            decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE, memlimit=128*1024*1024)
            candidate = decoder.decompress(kernel[pos:], max_length=MAX_RAW + 1)
        except lzma.LZMAError:
            continue
        if len(candidate) > MAX_RAW:
            raise ValueError('Kernel decompression exceeds bound')
        if decoder.eof and b'Linux version ' in candidate and b'IKCFG_ST' in candidate:
            decoded = candidate
            break
    if decoded is None:
        raise ValueError('No bounded LZMA kernel with embedded config')
    if decoded.count(b'IKCFG_ST') != 1 or decoded.count(b'IKCFG_ED') != 1:
        raise ValueError('Ambiguous embedded config markers')
    start = decoded.index(b'IKCFG_ST') + 8
    end = decoded.index(b'IKCFG_ED')
    if end <= start:
        raise ValueError('Invalid embedded config bounds')
    gzip = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        config = gzip.decompress(decoded[start:end], MAX_CONFIG + 1)
    except zlib.error as error:
        raise ValueError('Invalid embedded config gzip') from error
    if len(config) > MAX_CONFIG or not gzip.eof or gzip.unused_data or gzip.unconsumed_tail:
        raise ValueError('Embedded config exceeds bound or has trailing/truncated data')
    text = config.decode('utf-8')
    symbols = config_values(text)
    banners = re.findall(rb'Linux version [^\x00\n]+', decoded)
    if len(banners) != 1:
        raise ValueError('Ambiguous kernel version banner')
    return dict(kernel_sha256=sha(kernel), kernel_bytes=len(kernel),
                linux_banner=banners[0].decode('ascii'), config_sha256=sha(config),
                compressed_image_bytes=info['compressed_image_bytes'],
                appended_bytes=info['appended_bytes'], symbols=symbols), text


def differences(before, after):
    return {key: {'original': before.get(key), 'candidate': after.get(key)}
            for key in sorted(before.keys() | after.keys())
            if before.get(key) != after.get(key)}


def inspect(boot, candidate):
    pair = analyze(boot, candidate)  # authenticates original BOOT bytes
    size = struct.unpack_from('<I', boot, 8)[0]
    original, config = extract(boot[2048:2048+size])
    new, _ = extract(candidate)
    if '3.4.113-g' + SOURCE_REV[:8] not in original['linux_banner']:
        raise ValueError('Unexpected original kernel provenance')
    if original['symbols'].get('CONFIG_USE_OF') != 'n':
        raise ValueError('Original kernel is not the expected legacy board boot')
    delta = differences(original['symbols'], new['symbols'])
    source_matches = '3.4.113-g' + SOURCE_REV[:8] in new['linux_banner']
    return dict(status='KERNEL_BASELINE_STATIC_COMPARISON_ONLY',
                original_boot_sha256=pair['original_boot_sha256'],
                original={k:v for k,v in original.items() if k != 'symbols'},
                candidate={k:v for k,v in new.items() if k != 'symbols'},
                expected_kernel_source_revision=SOURCE_REV,
                candidate_source_matches_original=source_matches,
                config_changed_count=len(delta), config_differences=delta,
                same_source_and_config=source_matches and not delta,
                legacy_board_config_without_appended_dtb=True,
                dtb_structure_validated=False, hardware_tested=False,
                flash_approved=False), config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original_boot', type=Path)
    parser.add_argument('candidate_zimage', type=Path)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--original-config', required=True, type=Path)
    args = parser.parse_args()
    inputs = {args.original_boot.resolve(), args.candidate_zimage.resolve()}
    outputs = {args.report.resolve(), args.original_config.resolve()}
    if inputs & outputs or len(outputs) != 2:
        parser.error('Outputs must be distinct from each other and inputs')
    report, config = inspect(args.original_boot.read_bytes(), args.candidate_zimage.read_bytes())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.original_config.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    args.original_config.write_text(config)
    print(json.dumps({k:v for k,v in report.items() if k != 'config_differences'}, indent=2))


if __name__ == '__main__':
    main()
