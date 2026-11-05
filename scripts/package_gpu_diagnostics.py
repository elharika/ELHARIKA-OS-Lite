#!/usr/bin/env python3
"""Build tiny reversible diagnostic ZIPs; does not build or fix a ROM."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import zipfile

SF_SHA = 'daf54072c758c5f52a70283dcc8ac22e6f157600a0b8c555639802c606e9110d'

def build(output):
    root = Path(__file__).resolve().parents[1]
    payload = {name: (root/'diagnostics'/name).read_bytes() for name in ('gpu-capture.sh','gpu-capture.rc')}
    template = (root/'diagnostics/update-binary.in').read_text()
    for script in (template, payload['gpu-capture.sh'].decode()):
        subprocess.run(['sh','-n'], input=script, text=True, check=True)
    output.mkdir(parents=True, exist_ok=True)
    readme = '''SM-P900/v1awifi only, exact diagnosed Android 11 system build.
This is temporary diagnostic instrumentation, NOT a black-screen fix or ROM.
It adds only /system/bin/elharika-gpu-capture.sh and
/system/etc/init/elharika-gpu-capture.rc and a one-boot request in Cache.
It does not replace Boot, GPU libraries, permissions, SELinux policy, or partitions.
Installation/removal has NOT been hardware-tested. Backups and recovery required.
Uncheck System in TWRP Mount before installing either ZIP. Do not wipe anything.
Install ELHARIKA-SM-P900-GPU-DIAGNOSTICS-INSTALL.zip from TWRP Install.
Reboot System ONCE, wait 90 seconds even if screen remains black, return to TWRP.
In Mount, enable Cache, then use Terminal:
tar -czf /external_sd/elharika-gpu-diagnostics.tgz -C /cache elharika-gpu-diagnostics
Send that archive for analysis. It contains runtime logs, not just tombstone tails.
Install ELHARIKA-SM-P900-GPU-DIAGNOSTICS-REMOVE.zip to remove instrumentation.
Removal preserves captured logs. Capture request is consumed once only.
No paid runner or device connection is needed to build these ZIPs.
'''
    (output/'README.txt').write_text(readme)
    lines = []
    for action in ('install','remove'):
        script = template
        values = {'ACTION': action, 'SURFACEFLINGER_SHA': SF_SHA,
                  'SCRIPT_SHA': hashlib.sha256(payload['gpu-capture.sh']).hexdigest(),
                  'RC_SHA': hashlib.sha256(payload['gpu-capture.rc']).hexdigest()}
        for key, value in values.items(): script = script.replace('@'+key+'@', value)
        if any('@'+key+'@' in script for key in values):
            raise ValueError('Unexpanded installer token')
        subprocess.run(['sh','-n'], input=script, text=True, check=True)
        archive = output/('ELHARIKA-SM-P900-GPU-DIAGNOSTICS-'+action.upper()+'.zip')
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            def add(name, data, mode=0o644):
                info = zipfile.ZipInfo(name, (2026,11,5,0,0,0))
                info.external_attr = (0o100000 | mode) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, data)
            add('META-INF/com/google/android/update-binary', script, 0o755)
            add('META-INF/com/google/android/updater-script', '# Shell diagnostic installer\n')
            add('README.txt', readme)
            if action == 'install':
                for name, data in payload.items(): add(name, data)
        with zipfile.ZipFile(archive) as z:
            if z.testzip(): raise ValueError('ZIP CRC verification failed')
        lines.append(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name)
    (output/'SHA256SUMS').write_text('\n'.join(lines)+'\n')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('output', type=Path)
    build(p.parse_args().output)
