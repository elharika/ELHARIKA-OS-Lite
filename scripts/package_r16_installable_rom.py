#!/usr/bin/env python3
"""Package exact touch-fixed R15 SYSTEM with corrected original-baseline Wacom BOOT.

Build-time verification only. Does not certify runtime stability or flash hardware.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import zipfile

from stage_r15_wacom_boot_candidate import repack

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ZIP_SHA = '615b8a179e66305c30d8dea183206457d9e1db151cd4313a915440f24caa33f9'
SYSTEM_SHA = 'a0a8abc0d59651ab46c3a99ee41e2181559a14316b7fde645580684f89d3ae10'
SYSTEM_BYTES = 2299998208
OLD_BOOT_SHA = '7d15b15e127e4b31841e1081efac31d2c298c2748dbc5d55889a3e8d45e20d14'
NEW_BOOT_SHA = 'a4c0773787ccd9c4d1a4da592ebf204512f882717d76d23b6cf1411fb32b3022'
KERNEL_SHA = '8b920c96019869aa531b50fcad791b96f3aaf2d518bb4542883d1ce773379937'
ROM_NAME = 'ELHARIKA-OS-SM-P900-Android11-R16-SPEN-TEST-TWRP.zip'
RESTORE_NAME = 'ELHARIKA-SM-P900-R16-RESTORE-R15-BOOT-TWRP.zip'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def render(template, values):
    for key, value in values.items():
        token = '@' + key + '@'
        if token not in template:
            raise ValueError('Missing installer token: ' + token)
        template = template.replace(token, str(value))
    if re.search(r'@[A-Z_]+@', template):
        raise ValueError('Unresolved installer token')
    subprocess.run(['sh', '-n'], input=template, text=True, check=True)
    return template


def full_installer(old, new):
    template = (ROOT/'installer/update-binary.in').read_text()
    template = template.replace("ui 'Camera and GPS disabled. Boot and S Pen operation are not verified.'",
        "ui 'R16: original-baseline Wacom LCD-sync isolation. Physical stability not yet tested.'\n"
        "ui 'Camera and GPS remain unsupported. Existing DATA will not be wiped.'")
    template = template.replace("case \"$ZIP\" in /external_sd/*|/external_sdcard/*)",
                                "case \"$ZIP\" in /external_sd/*|/external_sd1/*|/external_sdcard/*)")
    template = template.replace('for tool in getprop readlink blockdev unzip sha256sum dd head wc df awk sync tr mkdir rm;',
                                'for tool in getprop readlink blockdev unzip sha256sum dd head wc df awk sync tr mkdir rm cat mktemp;')
    anchor='DIR=${ZIP%/*}\n'
    if template.count(anchor) != 1:
        raise ValueError('Installer free-space anchor drift')
    template = template.replace(anchor, """[ -r /sys/class/power_supply/battery/capacity ] || die 'Battery reading unavailable'
PWR=$(cat /sys/class/power_supply/battery/capacity)
case "$PWR" in ''|*[!0-9]*) die 'Invalid battery reading';; esac
[ "$PWR" -ge 50 ] || die 'Charge battery to at least 50 percent'
DIR=${ZIP%/*}
""")
    anchor="ui 'Preflight passed. Writing SYSTEM; keep power connected.'"
    if template.count(anchor) != 1:
        raise ValueError('Installer write anchor drift')
    template = template.replace(anchor, """# Durable automatic BOOT backup before either partition is written.
BACKUP=$(mktemp -d "$DIR/ELHARIKA-BEFORE-R16-BOOT.XXXXXX") || die 'Cannot create BOOT backup'
head -c 8388608 "$BOOT" > "$BACKUP/boot-partition.img" || die 'BOOT backup failed'
[ "$(wc -c < "$BACKUP/boot-partition.img" | tr -d '[:space:]')" = 8388608 ] || die 'Incomplete BOOT backup'
BACKUP_SHA=$(sha256sum "$BACKUP/boot-partition.img" | awk '{print $1}')
[ "$(head -c 8388608 "$BOOT" | sha256sum | awk '{print $1}')" = "$BACKUP_SHA" ] || die 'BOOT backup verification failed'
echo "$BACKUP_SHA  boot-partition.img" > "$BACKUP/SHA256SUMS"
ui "Automatic BOOT backup retained at $BACKUP"
""" + anchor)
    return render(template, dict(SYSTEM_SIZE=SYSTEM_BYTES, SYSTEM_SHA=SYSTEM_SHA,
        BOOT_SIZE=len(new), BOOT_SHA=NEW_BOOT_SHA,
        REQUIRED_KB=(SYSTEM_BYTES+len(new)+8388608)//1024+131072))


def add(archive, name, data, mode=0o644):
    info = ZipInfo(name, (2026,11,10,0,0,0))
    info.external_attr=(0o100000|mode)<<16
    info.create_system=3
    info.compress_type=ZIP_DEFLATED
    archive.writestr(info, data)


def validate_boots(source, staging):
    if file_sha(source) != SOURCE_ZIP_SHA:
        raise ValueError('Unknown source full-ROM ZIP hash')
    with ZipFile(source) as z:
        expected = {'META-INF/com/google/android/update-binary','META-INF/com/google/android/updater-script',
                    'system.ext4','boot.img','README.txt','verification.json'}
        if len(z.namelist()) != len(expected) or set(z.namelist()) != expected:
            raise ValueError('Unexpected source ROM members')
        if z.getinfo('system.ext4').file_size != SYSTEM_BYTES:
            raise ValueError('Unexpected source SYSTEM geometry')
        old = z.read('boot.img')
        manifest = json.loads(z.read('verification.json'))
        if manifest.get('full_raw_system_sha256') != SYSTEM_SHA or manifest.get('donor_r15_mali_sha256') != 'a00166d28cbd0213c88daadb437534310de09da4bf9fcc64f8e2207e22d76839':
            raise ValueError('Source SYSTEM/Mali provenance differs')
    if digest(old) != OLD_BOOT_SHA:
        raise ValueError('Source BOOT differs')
    with ZipFile(staging) as z:
        new = z.read('BOOT-CANDIDATE-NOT-DEVICE-TESTED.img')
        if z.read('ORIGINAL-R15P0-BOOT.img') != old:
            raise ValueError('Staging original BOOT differs')
    if digest(new) != NEW_BOOT_SHA:
        raise ValueError('Corrected BOOT differs from independently validated candidate')
    ks = int.from_bytes(new[8:12], 'little')
    rebuilt, baseline = repack(old, new[2048:2048+ks], KERNEL_SHA)
    if rebuilt != new:
        raise ValueError('Candidate reconstruction differs')
    return old, new, manifest, baseline


def package(source, staging, out):
    source, staging, out = Path(source), Path(staging), Path(out)
    old, new, previous, baseline = validate_boots(source, staging)
    out.mkdir(parents=True, exist_ok=True)
    rom, restore = out/ROM_NAME, out/RESTORE_NAME
    if rom.exists() or restore.exists():
        raise ValueError('Deliverables already exist; refusing overwrite')
    installer = full_installer(old, new)
    undo = render((ROOT/'installer/r16-boot-restore.in').read_text(),
                  dict(OLD_BYTES=len(old),OLD_SHA=OLD_BOOT_SHA,NEW_BYTES=len(new),NEW_SHA=NEW_BOOT_SHA))
    notes = '''ELHARIKA OS Lite — SM-P900 / v1awifi — Android 11 R16 S Pen trial

This ZIP is installable from TWRP. Hardware boot and S Pen drawing have NOT been
validated with this kernel. It is not a guaranteed stable or problem-free ROM.
The candidate uses the original kernel source/config and isolates optional
Wacom LCD frequency feedback. Pressure/coordinate handlers are not changed.
SYSTEM is byte-identical to the latest R15P0 + Touch Fix + One UI image.
Camera/GPS remain unsupported. No verified current security patch is claimed.

INSTALL:
1. Use SM-P900 Wi-Fi / v1awifi only, working TWRP and battery at least 50%.
2. Copy this ROM ZIP AND the RESTORE-R15-BOOT ZIP to external microSD.
3. Keep at least 2.5 GiB free after copying the ZIPs. In TWRP Mount, uncheck System.
4. TWRP > Install > select the R16-SPEN-TEST-TWRP ZIP > confirm flash.
5. Wait for SYSTEM and BOOT readback checks to finish, then Reboot > System.
Do not wipe/format Data, EFS, Recovery or bootloader for this update.
The installer creates and retains a verified full BOOT backup on microSD.
On a write/readback error, stay in TWRP; rerun the full verified ROM ZIP.

ROLLBACK:
If R16 fails to boot or drawing freezes, return to TWRP and install the separate
RESTORE-R15-BOOT ZIP. It changes BOOT only and restores the previous R15 kernel.
It checks the current BOOT hash; an unknown/partially written BOOT is refused.
In that case first rerun the full R16 ROM successfully, then apply the restore.
Rollback returns to the previous ROM behavior, including its known pen issue;
it is not a claim of S Pen stability. SYSTEM and Data remain unchanged.
First check normal boot and finger input. Do not keep forcing freezes to test.
'''
    report = dict(status='INSTALLABLE_TWRP_HARDWARE_NOT_VALIDATED', model='SM-P900/v1awifi',
        android_version=11, source_full_rom_sha256=SOURCE_ZIP_SHA, system_sha256=SYSTEM_SHA,
        system_bytes=SYSTEM_BYTES, corrected_boot_sha256=NEW_BOOT_SHA, original_boot_sha256=OLD_BOOT_SHA,
        kernel_source_and_config_match_original=True, source_system_unchanged=True,
        optional_wacom_lcd_sync_disabled=True, source_manifest=previous,
        compiled_baseline=baseline, writes=['SYSTEM','BOOT'], wipes_data=False,
        automatic_boot_backup=True, rollback_writes=['BOOT'],
        known_limitations=['Camera unsupported','GPS unsupported','Physical S Pen fix unproven'],
        hardware_tested=False, stable_release=False)
    temporary=rom.with_suffix('.partial')
    old_limit=zipfile.ZIP64_LIMIT
    zipfile.ZIP64_LIMIT=0xffffffff
    try:
        with ZipFile(source) as src, ZipFile(temporary,'x',compression=ZIP_DEFLATED,compresslevel=5,allowZip64=False) as dst:
            add(dst,'META-INF/com/google/android/update-binary',installer,0o755)
            add(dst,'META-INF/com/google/android/updater-script','# Guarded SM-P900 R16 SYSTEM+BOOT installer\n')
            info=ZipInfo('system.ext4',(2026,11,10,0,0,0));info.compress_type=ZIP_DEFLATED
            info.create_system=3;info.external_attr=0o100644<<16;info.file_size=SYSTEM_BYTES
            h=hashlib.sha256();count=0
            with src.open('system.ext4') as source_stream, dst.open(info,'w') as target_stream:
                for block in iter(lambda:source_stream.read(1024*1024),b''):
                    h.update(block);count+=len(block);target_stream.write(block)
            if h.hexdigest()!=SYSTEM_SHA or count!=SYSTEM_BYTES:
                raise ValueError('Source SYSTEM content hash mismatch')
            add(dst,'boot.img',new)
            add(dst,'INSTALLATION.txt',notes)
            add(dst,'verification.json',json.dumps(report,indent=2)+'\n')
        with ZipFile(temporary) as z:
            if z.testzip() is not None or any(i.extract_version>20 for i in z.infolist()):
                raise ValueError('TWRP ZIP integrity/ZIP32 check failed')
        temporary.rename(rom)
        with ZipFile(restore,'x',compression=ZIP_DEFLATED,allowZip64=False) as z:
            add(z,'META-INF/com/google/android/update-binary',undo,0o755)
            add(z,'META-INF/com/google/android/updater-script','# Exact R16 to R15 BOOT restore\n')
            add(z,'boot.img',old)
            add(z,'INSTALLATION.txt',notes)
        with ZipFile(restore) as z:
            if z.testzip() is not None:raise ValueError('Restore ZIP CRC failed')
    finally:
        zipfile.ZIP64_LIMIT=old_limit
        if temporary.exists(): temporary.unlink()
    (out/'ELHARIKA-R16-INSTALLATION.txt').write_text(notes)
    (out/'ELHARIKA-R16-VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
    result={p.name:dict(bytes=p.stat().st_size,sha256=file_sha(p)) for p in [rom,restore]}
    (out/'ELHARIKA-R16-SHA256SUMS.txt').write_text(''.join(f"{r['sha256']}  {n}\n" for n,r in result.items()))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source_rom',type=Path);p.add_argument('staged_boot',type=Path);p.add_argument('output_dir',type=Path)
    a=p.parse_args();print(json.dumps(package(a.source_rom,a.staged_boot,a.output_dir),indent=2))
