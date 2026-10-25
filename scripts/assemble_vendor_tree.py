#!/usr/bin/env python3
"""Assemble an experimental vendor source tree locally. Never flashes or publishes blobs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from generate_vendor_rules import generate,TREES
from verify_stock_blobs import safe_path


def relocate_trustlets(data):
    old=b'/system/app';new=b'/vendor/app'
    if data.count(old)!=1 or new in data:
        raise ValueError('Unexpected daemon trustlet path; no automatic fixup')
    result=data.replace(old,new)
    if len(result)!=len(data):raise ValueError('Fixup changed ELF size')
    return result


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
