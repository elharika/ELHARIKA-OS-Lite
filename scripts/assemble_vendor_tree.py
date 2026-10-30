#!/usr/bin/env python3
"""Assemble an experimental vendor source tree locally. Never flashes or publishes blobs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import subprocess
from generate_vendor_rules import generate,TREES,STLPORT_SHA256,AEABI_SYMBOLS,SONAME_FIXUPS
from verify_stock_blobs import safe_path,elf_info,digest


def relocate_trustlets(data):
    old=b'/system/app';new=b'/vendor/app'
    if data.count(old)!=1 or new in data:
        raise ValueError('Unexpected daemon trustlet path; no automatic fixup')
    result=data.replace(old,new)
    if len(result)!=len(data):raise ValueError('Fixup changed ELF size')
    return result


def add_aeabi_compat_dependency(path):
    """Add the only explicit legacy dependency, retaining the original audit."""
    original=path.read_bytes()
    if hashlib.sha256(original).hexdigest()!=STLPORT_SHA256:
        raise ValueError('Unexpected SM-P900 libstlport bytes')
    before=elf_info(path)
    if (not before or not before['arm32_little_endian'] or
            before['soname']!='libstlport.so' or
            not AEABI_SYMBOLS.issubset({s['name'] for s in before['undefined_symbols']}) or
            'libelharika_aeabi_compat.so' in before['needed']):
        raise ValueError('Unexpected SM-P900 libstlport ELF')
    subprocess.run(['patchelf','--add-needed','libelharika_aeabi_compat.so',str(path)],
                   check=True,timeout=30)
    after=elf_info(path)
    if (not after or after['soname']!=before['soname'] or
            not after['arm32_little_endian'] or
            set(after['needed'])!=set(before['needed'])|{'libelharika_aeabi_compat.so'} or
            after['undefined_symbols']!=before['undefined_symbols']):
        raise ValueError('Patched libstlport ELF failed structural audit')
    return {'file':'vendor/lib/libstlport.so',
            'change':'Add explicit libelharika_aeabi_compat.so DT_NEEDED for two ARM EABI symbols',
            'before_sha256':hashlib.sha256(original).hexdigest(),
            'after_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'runtime_tested':False}


def normalize_pinned_soname(path, destination):
    """Normalize a verified stock copy; retain its old name as an install alias."""
    expected_sha, old_soname = SONAME_FIXUPS[destination]
    if digest(path) != expected_sha:
        raise ValueError('Unexpected stock ELF hash: ' + destination)
    before = elf_info(path)
    new_soname = Path(destination).name
    if (not before or not before['arm32_little_endian'] or
            before['soname'] != old_soname or old_soname == new_soname):
        raise ValueError('Unexpected stock ELF SONAME: ' + destination)
    subprocess.run(['patchelf', '--set-soname', new_soname, str(path)],
                   check=True, timeout=30)
    after = elf_info(path)
    if (not after or not after['arm32_little_endian'] or
            after['soname'] != new_soname or
            after['needed'] != before['needed'] or
            after['undefined_symbols'] != before['undefined_symbols']):
        raise ValueError('SONAME patch changed ELF dependencies: ' + destination)
    return {'file':destination, 'change':f'SONAME {old_soname} -> {new_soname}',
            'before_sha256':expected_sha, 'after_sha256':digest(path),
            'runtime_tested':False}


def assemble(baseline,stage,output):
    if output.exists():raise ValueError('Output must be new')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent,prefix='elharika-vendor-') as tmp:
        root=Path(tmp)/'tree'
        summary=generate(baseline,stage,root)
        copied=set()
        for r in baseline['comparison']['records']:
            dest=safe_path(r['destination']);owner=TREES[r['tree']]
            if dest in copied:continue
            copied.add(dest)
            target=root/'samsung'/owner/'proprietary'/dest
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(stage/'proprietary'/dest,target)
        daemon=root/'samsung/universal5420-common/proprietary/vendor/bin/mcDriverDaemon'
        old=daemon.read_bytes();new=relocate_trustlets(old);daemon.write_bytes(new)
        summary['fixups']=[{'file':'vendor/bin/mcDriverDaemon','change':'/system/app -> /vendor/app (same byte length)',
                          'before_sha256':hashlib.sha256(old).hexdigest(),'after_sha256':hashlib.sha256(new).hexdigest()}]
        stlport=root/'samsung/universal5420-common/proprietary/vendor/lib/libstlport.so'
        summary['fixups'].append(add_aeabi_compat_dependency(stlport))
        for dest in SONAME_FIXUPS:
            record=next(r for r in baseline['comparison']['records'] if r['destination']==dest)
            owner=TREES[record['tree']]
            path=root/'samsung'/owner/'proprietary'/dest
            summary['fixups'].append(normalize_pinned_soname(path,dest))
        # Explicit dependency on Mali output, not an unrelated LOCAL_INSTALLED_MODULE.
        links='''# Experimental SM-P900 OpenCL aliases; runtime untested.
ifeq ($(TARGET_DEVICE),v1awifi)
ELHARIKA_OPENCL_LINKS := $(addprefix $(TARGET_OUT_VENDOR)/lib/,libOpenCL.so libOpenCL.so.1 libOpenCL.so.1.1)
$(ELHARIKA_OPENCL_LINKS): $(TARGET_OUT_VENDOR)/lib/egl/libGLES_mali.so
\t@mkdir -p $(dir $@)
\tln -sfn /vendor/lib/egl/libGLES_mali.so $@
ALL_DEFAULT_INSTALLED_MODULES += $(ELHARIKA_OPENCL_LINKS)
endif
'''
        makefile=root/'samsung/universal5420-common/Android.mk'
        makefile.write_text(makefile.read_text()+'\n'+links)
        summary.update(status='ASSEMBLED_NOT_ANDROID_COMPILED',hardware_tested=False)
        (root/'assembly-report.json').write_text(json.dumps(summary,indent=2)+'\n')
        files=sorted(p for p in root.rglob('*') if p.is_file())
        (root/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(root).as_posix()+'\n' for p in files))
        root.rename(output)
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('baseline',type=Path);p.add_argument('stage',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();print(json.dumps(assemble(json.loads(a.baseline.read_text()),a.stage,a.output),indent=2))

