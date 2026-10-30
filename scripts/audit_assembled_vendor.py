#!/usr/bin/env python3
"""Fail-closed structural audit for the assembled SM-P900 vendor ELF set.

This does not claim runtime compatibility. It verifies that every candidate ELF is
32-bit ARM, all known stock SONAME mismatches were normalized, the EABI bridge is
attached only to the three audited blobs, and Android build rules keep ELF checks
enabled. A JSON report is written for CI evidence.
"""
import argparse
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

from generate_vendor_rules import AEABI_SYMBOLS, AUDIO_SYMBOLS, SONAME_FIXUPS
from verify_stock_blobs import digest, elf_info

EXPECTED_ELF_COUNT = 14
COMPAT_NEEDED = 'libelharika_aeabi_compat.so'
COMPAT_PATHS = {
    'vendor/lib/libstlport.so': AEABI_SYMBOLS,
    'vendor/lib/soundfx/liblvverx.so': AUDIO_SYMBOLS,
    'vendor/lib/soundfx/liblvvetx.so': AUDIO_SYMBOLS,
}


def dynamic_tags(path: Path):
    result = subprocess.run(
        ['readelf', '-W', '-d', str(path)], capture_output=True, text=True,
        timeout=30, check=False,
    )
    if result.returncode:
        raise ValueError(f'readelf -d failed for {path}: {result.stderr[:240]}')
    return {
        'textrel': '(TEXTREL)' in result.stdout,
        'rpath_or_runpath': bool(re.search(r'\((?:RPATH|RUNPATH)\)', result.stdout)),
    }


def expected_alias_rule(dest: str, old_soname: str) -> str:
    """Return the exact Android.mk alias rule emitted by generate_vendor_rules."""
    path = PurePosixPath(dest)
    if not dest.startswith('vendor/'):
        raise ValueError('SONAME alias destination must live under vendor/: ' + dest)
    relative = dest[len('vendor/'):]
    parent = str(PurePosixPath(relative).parent)
    target = '$(TARGET_OUT_VENDOR)/' + (parent + '/' if parent != '.' else '') + old_soname
    source = '$(TARGET_OUT_VENDOR)/' + relative
    return f'{target}: {source}'


def audit(root: Path, report: Path):
    root = root.resolve()
    if not (root / 'SHA256SUMS').is_file():
        raise ValueError('Assembled vendor tree is missing SHA256SUMS')

    records = []
    seen_destinations = set()
    for owner_dir in sorted((root / 'samsung').iterdir()):
        proprietary = owner_dir / 'proprietary'
        if not proprietary.is_dir():
            continue
        for path in sorted(p for p in proprietary.rglob('*') if p.is_file()):
            info = elf_info(path)
            if not info:
                continue
            dest = path.relative_to(proprietary).as_posix()
            if dest in seen_destinations:
                raise ValueError('Duplicate ELF destination: ' + dest)
            seen_destinations.add(dest)
            if not info['arm32_little_endian']:
                raise ValueError('Non ARM32 little-endian ELF: ' + dest)

            name = PurePosixPath(dest).name
            if name.endswith('.so') and info.get('soname') not in (None, name):
                raise ValueError(f'Unnormalized SONAME: {dest} -> {info.get("soname")}')

            imports = {s['name'] for s in info.get('undefined_symbols', [])}
            needed = set(info.get('needed', []))
            if dest in COMPAT_PATHS:
                missing = sorted(COMPAT_PATHS[dest] - imports)
                if missing:
                    raise ValueError(f'Expected legacy imports missing from {dest}: {missing}')
                if COMPAT_NEEDED not in needed:
                    raise ValueError('EABI bridge missing from DT_NEEDED: ' + dest)
            elif COMPAT_NEEDED in needed:
                raise ValueError('Unexpected EABI bridge dependency: ' + dest)

            tags = dynamic_tags(path)
            records.append({
                'tree': owner_dir.name,
                'destination': dest,
                'sha256': digest(path),
                'soname': info.get('soname'),
                'needed': sorted(needed),
                'undefined_symbol_count': len(info.get('undefined_symbols', [])),
                **tags,
            })

    if len(records) != EXPECTED_ELF_COUNT:
        raise ValueError(f'Expected {EXPECTED_ELF_COUNT} ELF modules, found {len(records)}')

    # The three pinned original SONAMEs must be preserved as runtime aliases.
    alias_checks = []
    for dest, (_, old_soname) in SONAME_FIXUPS.items():
        matched = [r for r in records if r['destination'] == dest]
        if len(matched) != 1:
            raise ValueError('Pinned SONAME fixup ELF missing: ' + dest)
        owner = matched[0]['tree']
        makefile = (root / 'samsung' / owner / 'Android.mk').read_text()
        rule = expected_alias_rule(dest, old_soname)
        if rule not in makefile:
            raise ValueError('Legacy SONAME alias rule missing: ' + rule)
        alias_checks.append({'destination': dest, 'legacy_soname': old_soname, 'rule': rule})

    bp_text = '\n'.join(p.read_text() for p in sorted((root / 'samsung').glob('*/Android.bp')))
    mk_text = '\n'.join(p.read_text() for p in sorted((root / 'samsung').glob('*/Android.mk')))
    if 'check_elf_files: false' in bp_text or 'allow_undefined_symbols: true' in bp_text:
        raise ValueError('Broad Soong ELF validation bypass found')
    if 'LOCAL_CHECK_ELF_FILES := false' in mk_text:
        raise ValueError('Broad Make ELF validation bypass found')
    soong_checked = bp_text.count('check_elf_files: true')
    make_checked = mk_text.count('LOCAL_CHECK_ELF_FILES := true')
    if soong_checked + make_checked != EXPECTED_ELF_COUNT:
        raise ValueError(
            f'Expected {EXPECTED_ELF_COUNT} checked prebuilt ELF rules, got '
            f'{soong_checked} Soong + {make_checked} Make'
        )

    result = {
        'status': 'STRUCTURAL_PREFLIGHT_OK_RUNTIME_UNTESTED',
        'elf_modules': len(records),
        'soong_elf_checks': soong_checked,
        'make_elf_checks': make_checked,
        'soname_aliases': alias_checks,
        'records': records,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('vendor_root', type=Path)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    result = audit(args.vendor_root, args.report)
    print(json.dumps({k: result[k] for k in ('status', 'elf_modules', 'soong_elf_checks', 'make_elf_checks')}, indent=2))


if __name__ == '__main__':
    main()
