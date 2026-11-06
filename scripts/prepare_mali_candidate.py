#!/usr/bin/env python3
"""Prepare an exact-model UK10 Mali candidate; never flashes a device.

Requires capstone, pyelftools, patchelf, debugfs. Input vendor repository:
Valera1978/android_vendor_samsung_v1awifi at 4079dd66fc6955adb208a0633220f4b72faaf82d.
Proprietary binaries retain their original ownership; no relicensing is implied.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM

CANDIDATE_SHA = 'a66179ef65c26a797b814e3d9cf0ab2b7f07e0d32c641f463820c0a0c49f1ee9'
ORIGINAL_SHA = '3bc453470f2f6711d463f3fff9b115011cbcefcbb1355be9af147857d892e433'
SHIM_SHA = '740ba30081b184a7878d05c4014e541d8090c28d37e88f832fa5234c39452519'


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            digest.update(chunk)
    return digest.hexdigest()


def info(path):
    with Path(path).open('rb') as f:
        elf = ELFFile(f)
        if elf.elfclass != 32 or not elf.little_endian or elf['e_machine'] != 'EM_ARM':
            raise ValueError('Not ARM32 LE: ' + str(path))
        dyn = list(elf.get_section_by_name('.dynamic').iter_tags())
        symbols = list(elf.get_section_by_name('.dynsym').iter_symbols())
        return {
            'needed': [t.needed for t in dyn if t.entry.d_tag == 'DT_NEEDED'],
            'defined': {s.name for s in symbols if s['st_shndx'] != 'SHN_UNDEF'
                        and s['st_info']['bind'] in ('STB_GLOBAL', 'STB_WEAK')},
            'required': {s.name for s in symbols if s['st_shndx'] == 'SHN_UNDEF'
                         and s['st_info']['bind'] == 'STB_GLOBAL'},
            'text': elf.get_section_by_name('.text').data(),
            'text_base': elf.get_section_by_name('.text')['sh_addr'],
            'textrel': any(t.entry.d_tag == 'DT_TEXTREL' or
                           (t.entry.d_tag == 'DT_FLAGS' and t.entry.d_val & 4) for t in dyn),
        }


def extract(image, source, destination):
    subprocess.run(['debugfs', '-R', 'dump ' + source + ' ' + str(destination), str(image)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return destination.exists() and destination.read_bytes()[:4] == b'\x7fELF'


def prepare(candidate, system_image, output):
    if sha(candidate) != CANDIDATE_SHA:
        raise ValueError('Unexpected exact-model candidate bytes')
    before = info(candidate)
    if before['textrel']:
        raise ValueError('Refusing text relocation requirement')
    # Exact source initializes the UK version pair to 10.0 at this ARM callsite.
    lo, hi = 0x265e64, 0x265e9c
    instructions = list(Cs(CS_ARCH_ARM, CS_MODE_ARM).disasm(
        before['text'][lo-before['text_base']:hi-before['text_base']], lo))
    decoded = {i.address: (i.mnemonic, i.op_str) for i in instructions}
    for address, expected in {
        0x265e6c: ('mov', 'r0, #0xa'),
        0x265e78: ('mov', 'ip, #0'),
        0x265e84: ('strh', 'r0, [sp, #4]'),
        0x265e94: ('strh', 'ip, [sp, #6]'),
        0x265e98: ('bl', '#0x26556c'),
    }.items():
        if decoded.get(address) != expected:
            raise ValueError('Unknown UK10 callsite')
    output.mkdir(parents=True, exist_ok=True)
    original = output / 'original-libGLES_mali.so'
    if not extract(system_image, '/system/vendor/lib/egl/libGLES_mali.so', original):
        raise ValueError('Missing original installed Mali')
    if sha(original) != ORIGINAL_SHA:
        raise ValueError('System image is not the diagnosed build')
    with tempfile.TemporaryDirectory(prefix='elharika-mali-') as temporary:
        root = Path(temporary)
        shim = root / 'libelharika_mali_compat.so'
        if not extract(system_image, '/system/vendor/lib/' + shim.name, shim) or sha(shim) != SHIM_SHA:
            raise ValueError('Missing exact installed process-name bridge')
        patched = output / 'candidate-libGLES_mali.so'
        shutil.copyfile(candidate, patched)
        subprocess.run(['patchelf', '--add-needed', shim.name, str(patched)], check=True)
        after = info(patched)
        if (after['text'] != before['text'] or after['textrel'] or
                after['required'] != before['required'] or
                set(after['needed']) != set(before['needed']) | {shim.name}):
            raise ValueError('Dependency-only patch audit failed')
        defined = set(after['defined'])
        queue, seen = list(after['needed']), set()
        while queue:
            name = queue.pop()
            if name in seen:
                continue
            seen.add(name)
            if Path(name).name != name:
                raise ValueError('Unexpected library path')
            path = root / name
            if not path.exists():
                for directory in ('/system/apex/com.android.runtime/lib/bionic/',
                                  '/system/lib/', '/system/vendor/lib/'):
                    if extract(system_image, directory + name, path):
                        break
                else:
                    raise ValueError('Missing required library: ' + name)
            dependency = info(path)
            defined.update(dependency['defined'])
            queue.extend(dependency['needed'])
        missing = sorted(after['required'] - defined)
        if missing:
            raise ValueError('Unresolved strong imports: ' + ', '.join(missing))
    result = {
        'status': 'STATIC_VALIDATED_HARDWARE_UNTESTED',
        'device': 'SM-P900/v1awifi',
        'source': 'Valera1978/android_vendor_samsung_v1awifi',
        'source_commit': '4079dd66fc6955adb208a0633220f4b72faaf82d',
        'source_path': 'proprietary/vendor/lib/egl/libGLES_mali.so',
        'source_sha256': CANDIDATE_SHA,
        'original_sha256': ORIGINAL_SHA,
        'candidate_sha256': sha(patched),
        'installed_shim_sha256': SHIM_SHA,
        'requested_uk_version': [10, 0],
        'pinned_r15p0_kernel_response': [10, 0],
        'required_imports': len(after['required']),
        'unresolved_strong_imports': missing,
        'dependencies_audited': sorted(seen),
        'text_unchanged': True,
        'text_relocations': False,
        'limits': ['Symbol-name closure is not runtime linker namespace validation',
                   'Successful EGL initialization and UI boot require device testing',
                   'Proprietary blob ownership and redistribution terms remain unchanged'],
    }
    (output / 'candidate-review.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('system_image', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.candidate, args.system_image, args.output), indent=2))
