#!/usr/bin/env python3
"""Package ONLY the pinned, verified SM-P900 experimental system/boot pair.

This is not a release approval and cannot establish hardware compatibility.
"""
import argparse
import hashlib
import json
import lzma
from pathlib import Path
import shutil
import struct
import subprocess
import xml.etree.ElementTree as ET
import zipfile

SYSTEM_SHA = 'fd145e39215b7839d3a414a23a58bcd7cec2707b551e409fecd2b8c44b663f61'
BOOT_SHA = '7d15b15e127e4b31841e1081efac31d2c298c2748dbc5d55889a3e8d45e20d14'
EXPANDED = 2299998208
NAME = 'ELHARIKA-OS-Lite-11-SM-P900-EXPERIMENTAL-TWRP.zip'

def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            digest.update(chunk)
    return digest.hexdigest()

def lock(path):
    return {p.get('path', p.get('name')): (p.get('name'), p.get('revision'))
            for p in ET.parse(path).getroot().findall('project')}

def expand(source, target):
    """Expand validated sparse input; initialize skipped blocks as zero holes."""
    with source.open('rb') as src, target.open('wb') as out:
        def read(n):
            b = src.read(n)
            if len(b) != n:
                raise ValueError('Truncated sparse image')
            return b
        magic, major, minor, fh, ch, bs, blocks, chunks, crc = struct.unpack('<I4H4I', read(28))
        if (magic, major, fh, ch, bs, blocks * bs) != (0xed26ff3a, 1, 28, 12, 4096, EXPANDED):
            raise ValueError('Unexpected pinned sparse geometry')
        seen = 0
        for _ in range(chunks):
            kind, reserved, n, total = struct.unpack('<2H2I', read(12))
            size = n * bs
            if reserved or seen + n > blocks:
                raise ValueError('Invalid chunk bounds')
            if kind == 0xcac1 and total == ch + size:
                remaining = size
                while remaining:
                    data = read(min(remaining, 1048576)); out.write(data); remaining -= len(data)
            elif kind == 0xcac2 and total == ch + 4:
                pattern = read(4) * (bs // 4)
                for _ in range(n):
                    out.write(pattern)
            elif kind == 0xcac3 and total == ch:
                out.seek(size, 1)
            elif kind == 0xcac4 and n == 0 and total == ch + 4:
                read(4)
            else:
                raise ValueError('Invalid sparse chunk')
            seen += n
        if seen != blocks or src.read(1):
            raise ValueError('Invalid sparse ending')
        out.truncate(EXPANDED)

def boot_fstab(image):
    data = image.read_bytes()
    if data[:8] != b'ANDROID!' or data[-16:] != b'SEANDROIDENFORCE':
        raise ValueError('Invalid boot wrapper')
    ks, _, rs = struct.unpack_from('<3I', data, 8)
    page = struct.unpack_from('<I', data, 36)[0]
    if page != 2048 or len(data) > 8388608:
        raise ValueError('Invalid boot geometry')
    off = page + ((ks + page - 1) // page) * page
    ramdisk = lzma.decompress(data[off:off + rs])
    i = 0; fstab = None
    while i + 110 <= len(ramdisk):
        header = ramdisk[i:i+110]
        if header[:6] != b'070701':
            raise ValueError('Invalid ramdisk cpio')
        size = int(header[54:62], 16); ns = int(header[94:102], 16)
        name = ramdisk[i+110:i+110+ns-1].decode()
        start = (i+110+ns+3)//4*4
        if name == 'fstab.universal5420':
            fstab = ramdisk[start:start+size].decode()
        i = (start+size+3)//4*4
        if name == 'TRAILER!!!':
            break
    if not fstab or not any(line.split()[:3] == ['/dev/block/platform/dw_mmc.0/by-name/SYSTEM', '/system', 'ext4']
                            and 'first_stage_mount' in line for line in fstab.splitlines()):
        raise ValueError('Missing expected first-stage SYSTEM mount')
    return fstab

def package(system_dir, boot_dir, se, be, output):
    system = system_dir / 'system.img'; boot = boot_dir / 'boot.img'
    if sha(system) != SYSTEM_SHA or sha(boot) != BOOT_SHA:
        raise ValueError('Input hashes do not match successful builds')
    if lock(se / 'platform-lock.xml') != lock(be / 'platform-lock.xml'):
        raise ValueError('Boot and system platform revisions differ')
    for evidence in (se, be):
        limitations = json.loads((evidence / 'bringup-limitations.json').read_text())
        if limitations['profile'] != 'BOOT_BRINGUP_ONLY' or limitations['hardware_tested'] is not False:
            raise ValueError('Unexpected build profile')
    fstab = boot_fstab(boot)
    output.mkdir(parents=True, exist_ok=True)
    raw = output / 'system.ext4'
    expand(system, raw)
    result = subprocess.run(['e2fsck', '-fn', str(raw)], capture_output=True, text=True)
    (output / 'filesystem-check.log').write_text(result.stdout + result.stderr)
    if result.returncode != 0:
        raise ValueError('Filesystem validation failed')
    # Verify that the filesystem itself identifies the intended product/API.
    prop = subprocess.run(['debugfs', '-R', 'cat /system/build.prop', str(raw)],
                          check=True, capture_output=True, text=True).stdout
    for expected in ('ro.product.system.device=v1awifi', 'ro.build.version.sdk=30'):
        if expected not in prop:
            raise ValueError('Wrong product/API in filesystem: ' + expected)
    template = (Path(__file__).resolve().parents[1] / 'installer/update-binary.in').read_text()
    values = {'SYSTEM_SIZE': str(EXPANDED), 'BOOT_SIZE': str(boot.stat().st_size),
              'SYSTEM_SHA': sha(raw), 'BOOT_SHA': BOOT_SHA,
              'REQUIRED_KB': str((EXPANDED + boot.stat().st_size)//1024 + 131072)}
    for k, v in values.items():
        template = template.replace('@'+k+'@', v)
    if '@SYSTEM_' in template or '@BOOT_' in template:
        raise ValueError('Unexpanded installer placeholders')
    readme = ('EXPERIMENTAL FIRST-BOOT CANDIDATE, SM-P900/v1awifi ONLY.\n'
              'Hardware untested. Camera and GPS disabled. S Pen, GPU, Wi-Fi and boot unverified.\n'
              'Android 11 userdebug/testkeys, SELinux PERMISSIVE in inherited kernel command line.\n'
              'Not a security-maintained production release; do not use sensitive accounts/data.\n'
              'Requires TWRP on exact SM-P900, ro.product.device=v1awifi, P900 bootloader,\n'
              'unmounted SYSTEM, and at least 2.5 GB free on removable microSD.\n'
              'Back up Boot/System/Data/EFS to external storage first; preserve stock firmware.\n'
              'Install this ZIP itself. The outer GitHub artifact ZIP is only a download container.\n'
              'Writes only SYSTEM and BOOT. Does not wipe Data or repartition.\n'
              'Installer verifies input hashes and block readback. This does not prove bootability.\n'
              'If it fails, stay in recovery and save /tmp/recovery.log; do not wipe more partitions.\n'
              'System build: 41862679569. Matching boot build: 42067803567.\n'
              'Sources and licenses: https://github.com/elharika/ELHARIKA-OS-Lite\n')
    report = {'status': 'EXPERIMENTAL_INSTALLER_BUILT_HARDWARE_UNTESTED',
              'flash_approved': False, 'system_run': 41862679569, 'boot_run': 42067803567,
              'matching_platform_lock': True, 'system_sparse_sha256': SYSTEM_SHA,
              'system_raw_sha256': values['SYSTEM_SHA'], 'boot_sha256': BOOT_SHA,
              'expanded_system_bytes': EXPANDED, 'filesystem_e2fsck_exit': result.returncode,
              'selinux_kernel_cmdline': 'permissive', 'build_type': 'userdebug/testkeys',
              'installer_hardware_tested': False,
              'disabled': ['camera', 'GPS'], 'hardware_tests': 'NOT_TESTED'}
    (output / 'package-validation.json').write_text(json.dumps(report, indent=2)+'\n')
    (output / 'README.txt').write_text(readme)
    (output / 'boot-fstab.txt').write_text(fstab)
    archive = output / NAME
    # ZIP32 supports sizes through 4 GiB. Python's conservative 2 GiB default
    # would otherwise emit ZIP64 for our 2.3 GB raw image; older recovery ZIP
    # parsers may reject ZIP64. Every entry and the archive remain below 4 GiB.
    old_limit = zipfile.ZIP64_LIMIT
    zipfile.ZIP64_LIMIT = 0xffffffff
    try:
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, allowZip64=False, compresslevel=6) as z:
            def add(name, content, mode=0o644):
                info = zipfile.ZipInfo(name, (2026,11,5,0,0,0))
                info.external_attr = (0o100000 | mode) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                if isinstance(content, Path):
                    info.file_size = content.stat().st_size
                    with content.open('rb') as src, z.open(info, 'w') as dst:
                        shutil.copyfileobj(src, dst, 1048576)
                else:
                    z.writestr(info, content)
            add('META-INF/com/google/android/update-binary', template, 0o755)
            add('META-INF/com/google/android/updater-script', '# Shell installer in update-binary\n')
            add('system.ext4', raw); add('boot.img', boot)
            add('README.txt', readme)
            add('package-validation.json', json.dumps(report, indent=2))
    finally:
        zipfile.ZIP64_LIMIT = old_limit
    with zipfile.ZipFile(archive) as z:
        if any(i.extract_version > 20 for i in z.infolist()):
            raise ValueError('Unexpected ZIP64 or unsupported compression')
        if z.testzip() is not None:
            raise ValueError('Installer ZIP failed CRC verification')
    (output / (NAME+'.sha256')).write_text(sha(archive)+'  '+NAME+'\n')
    raw.unlink()
    return report

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ('system-dir', 'boot-dir', 'system-evidence', 'boot-evidence', 'output'):
        p.add_argument('--'+arg, required=True, type=Path)
    a = p.parse_args()
    print(json.dumps(package(a.system_dir, a.boot_dir, a.system_evidence, a.boot_evidence, a.output), indent=2))
