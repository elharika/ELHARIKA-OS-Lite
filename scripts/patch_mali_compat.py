#!/usr/bin/env python3
"""Attach narrow compatibility libraries to the exact SM-P900 Mali prebuilt.

The patch is fail-closed: the stock blob hash, ARM architecture, SONAME and
legacy imports must all match before DT_NEEDED or generated build rules change.
No ELF validation is disabled.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

from verify_stock_blobs import digest, elf_info

MALI_SHA256 = '6bdde99d255444cf59374558736c85de5413125f63f4035237d6556c0f91047d'
MALI_DESTINATION = 'vendor/lib/egl/libGLES_mali.so'
MALI_NEEDED = 'libelharika_mali_compat.so'
MALI_MODULE = 'libelharika_mali_compat'
MALI_AEABI_NEEDED = 'libelharika_aeabi_compat.so'
MALI_AEABI_MODULE = 'libelharika_aeabi_compat'
MALI_AEABI_SYMBOLS = {
    '__aeabi_idiv',
    '__aeabi_ldivmod',
    '__aeabi_uidiv',
    '__aeabi_uidivmod',
    '__aeabi_uldivmod',
    '__popcountsi2',
}
MALI_WRAPPER_SYMBOLS = {
    '__aeabi_d2lz',
    '__aeabi_d2ulz',
    '__aeabi_f2lz',
    '__aeabi_f2ulz',
    '__aeabi_l2d',
    '__aeabi_l2f',
    '__aeabi_llsr',
    '__aeabi_ul2d',
    '__aeabi_ul2f',
}
MALI_REQUIRED_SYMBOLS = MALI_AEABI_SYMBOLS | MALI_WRAPPER_SYMBOLS | {
    '__popcount_tab',
    'get_process_name',
}


def patch_android_bp_text(text: str) -> str:
    """Add both Mali compatibility dependencies and the source-built shim."""
    blocks = list(re.finditer(r'cc_prebuilt_library_shared\s*\{.*?\n\}', text, flags=re.S))
    matches = [m for m in blocks if 'name: "libGLES_mali"' in m.group(0)]
    if len(matches) != 1:
        raise ValueError(f'Expected one libGLES_mali prebuilt block, found {len(matches)}')
    block_match = matches[0]
    block = block_match.group(0)
    shared_match = re.search(r'(?m)^\s*shared_libs:\s*(\[[^\n]*\]),\s*$', block)
    if not shared_match:
        raise ValueError('libGLES_mali block has no single-line shared_libs list')
    shared = json.loads(shared_match.group(1))
    for module in (MALI_MODULE, MALI_AEABI_MODULE):
        if module in shared:
            raise ValueError(module + ' was already present before Mali patching')
        shared.append(module)
    shared = sorted(set(shared))
    replacement = '    shared_libs: ' + json.dumps(shared) + ','
    patched_block = block[:shared_match.start()] + replacement + block[shared_match.end():]
    text = text[:block_match.start()] + patched_block + text[block_match.end():]

    if f'name: "{MALI_MODULE}"' in text:
        raise ValueError('Mali compat module already exists before patching')
    text += '''\n// Exact SM-P900 Android 5 Mali compatibility shim; runtime untested.\ncc_library_shared {\n    name: "libelharika_mali_compat",\n    owner: "elharika",\n    srcs: [\n        "compat/mali_legacy_compat.c",\n        "compat/mali_aeabi_exports.S",\n    ],\n    whole_static_libs: ["libclang_rt.builtins-arm-android"],\n    // compiler-rt embeds strong ARM EABI aliases for these same nine routines.\n    // Retain our explicit exported trampolines and verify them in the build gate.\n    ldflags: ["-Wl,--allow-multiple-definition"],\n    compile_multilib: "32",\n    vendor: true,\n    stl: "none",\n    cflags: ["-Wall", "-Wextra", "-Werror"],\n}\n'''
    return text


def add_mali_compat_dependency(path: Path):
    original = path.read_bytes()
    if hashlib.sha256(original).hexdigest() != MALI_SHA256:
        raise ValueError('Unexpected SM-P900 Mali blob bytes')
    before = elf_info(path)
    imports = {s['name'] for s in (before or {}).get('undefined_symbols', [])}
    missing = sorted(MALI_REQUIRED_SYMBOLS - imports)
    before_needed = set((before or {}).get('needed', []))
    if (not before or not before['arm32_little_endian'] or
            before.get('soname') != 'libGLES_mali.so' or missing or
            MALI_NEEDED in before_needed or MALI_AEABI_NEEDED in before_needed):
        raise ValueError('Unexpected SM-P900 Mali ELF: missing=' + ','.join(missing))
    subprocess.run(['patchelf', '--add-needed', MALI_NEEDED, str(path)],
                   check=True, timeout=30)
    subprocess.run(['patchelf', '--add-needed', MALI_AEABI_NEEDED, str(path)],
                   check=True, timeout=30)
    after = elf_info(path)
    expected_needed = before_needed | {MALI_NEEDED, MALI_AEABI_NEEDED}
    if (not after or not after['arm32_little_endian'] or
            after.get('soname') != before.get('soname') or
            set(after.get('needed', [])) != expected_needed or
            after.get('undefined_symbols') != before.get('undefined_symbols')):
        raise ValueError('Patched Mali ELF failed structural audit')
    return {
        'file': MALI_DESTINATION,
        'change': 'Add explicit Mali conversion shim and audited ARM EABI bridge dependencies',
        'before_sha256': hashlib.sha256(original).hexdigest(),
        'after_sha256': digest(path),
        'required_symbols': sorted(MALI_REQUIRED_SYMBOLS),
        'runtime_tested': False,
    }


def rewrite_checksums(root: Path):
    checksum = root / 'SHA256SUMS'
    if checksum.exists():
        checksum.unlink()
    files = sorted(p for p in root.rglob('*') if p.is_file())
    checksum.write_text(''.join(
        hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.relative_to(root).as_posix() + '\n'
        for p in files
    ))


def patch_tree(root: Path, report_path: Path):
    root = root.resolve()
    universal = root / 'samsung' / 'universal5420-common'
    bp = universal / 'Android.bp'
    vendor_mk = universal / 'universal5420-common-vendor.mk'
    mali = universal / 'proprietary' / MALI_DESTINATION
    compat_dir = universal / 'compat'
    source_root = Path(__file__).resolve().parents[1] / 'rom' / 'compat'
    sources = [source_root / 'mali_legacy_compat.c', source_root / 'mali_aeabi_exports.S']
    assembly_report = root / 'assembly-report.json'

    for required in (bp, vendor_mk, mali, assembly_report, *sources):
        if not required.is_file():
            raise ValueError('Missing required Mali compatibility input: ' + str(required))

    fixup = add_mali_compat_dependency(mali)

    original_bp = bp.read_text()
    patched_bp = patch_android_bp_text(original_bp)
    if 'check_elf_files: false' in patched_bp or 'allow_undefined_symbols: true' in patched_bp:
        raise ValueError('Refusing Mali patch with ELF validation bypass')
    bp.write_text(patched_bp)

    mk_text = vendor_mk.read_text()
    package_line = 'PRODUCT_PACKAGES += ' + MALI_MODULE
    if package_line in mk_text:
        raise ValueError('Mali compat PRODUCT_PACKAGES entry already present before patching')
    vendor_mk.write_text(mk_text + package_line + '\n')

    compat_dir.mkdir(parents=True, exist_ok=True)
    for source in sources:
        destination = compat_dir / source.name
        if destination.exists():
            raise ValueError('Mali compat source unexpectedly already exists: ' + source.name)
        shutil.copyfile(source, destination)

    report = json.loads(assembly_report.read_text())
    report.setdefault('fixups', []).append(fixup)
    report['mali_compat'] = {
        'module': MALI_MODULE,
        'compiler_builtins': 'libclang_rt.builtins-arm-android',
        'explicit_aeabi_bridge': MALI_AEABI_MODULE,
        'exported_wrapper_symbols': sorted(MALI_WRAPPER_SYMBOLS),
        'process_name_compat': True,
        'elf_checks_enabled': True,
        'hardware_tested': False,
    }
    assembly_report.write_text(json.dumps(report, indent=2) + '\n')

    result = {
        'status': 'MALI_COMPAT_PATCHED_STRUCTURAL_ONLY',
        'blob_sha256': MALI_SHA256,
        'needed': sorted([MALI_NEEDED, MALI_AEABI_NEEDED]),
        'required_symbols': sorted(MALI_REQUIRED_SYMBOLS),
        'exported_wrapper_symbols': sorted(MALI_WRAPPER_SYMBOLS),
        'elf_checks_enabled': True,
        'runtime_tested': False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    rewrite_checksums(root)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('vendor_root', type=Path)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    print(json.dumps(patch_tree(args.vendor_root, args.report), indent=2))


if __name__ == '__main__':
    main()
