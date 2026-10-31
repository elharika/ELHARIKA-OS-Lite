#!/usr/bin/env python3
"""Generate candidate Android build rules from hash-verified stock files. No ELF check bypass."""
import argparse
import json
from pathlib import Path,PurePosixPath
import re
import shutil
from verify_stock_blobs import digest,elf_info,safe_path

TREES={f'android_device_samsung_{n}':n for n in ('universal5420-common','v1a-common','v1awifi')}
STLPORT_SHA256='9b81b3116f93661c5bb614b84ce5b571ae552b57ebff4fa00f5f06442a7abc6a'
SENSOR_SHA256='4e7ab23e9fe49e2650c3f52a17f3d7433b76c4c89733b02d9a7e5dcc742db848'
AEABI_SYMBOLS={'__aeabi_ldivmod','__aeabi_uldivmod'}
SENSOR_SYMBOLS={'__aeabi_ldivmod'}
AUDIO_SYMBOLS={'__aeabi_idiv','__aeabi_idivmod','__aeabi_ldivmod',
               '__aeabi_uidiv','__aeabi_uidivmod','__popcountsi2'}
SONAME_FIXUPS={
    'vendor/lib/soundfx/liblvverx.so': ('3bcaa67077d80db7deb7dd6849e0abb4772ccdb238752a2de133cd140288685a', 'libLifevibes_lvverx.so'),
    'vendor/lib/soundfx/liblvvetx.so': ('18e517b4533cf4f53f3b911b3b635f65f7d9bfcc766f073e9646ed7e486238a2', 'libLifevibes_lvvetx.so'),
    'vendor/lib/hw/gps.universal5420.so': ('09b2705e668d7db54d355c24e7c5cec6f817faa788e25a62dc52f186d8261269', 'gps.samsungAdonisandroid.so'),
}

def generate(baseline,stage,output):
    if baseline.get('profile',{}).get('name')!='experimental-stock-candidates':raise ValueError('Wrong profile')
    if (baseline.get('identity',{}).get('model'),baseline.get('identity',{}).get('build'))!=('SM-P900','P900XXS0BPL4'):
        raise ValueError('Wrong stock image identity')
    groups={n:[] for n in TREES.values()};seen={};modules=set();aliases={n:[] for n in TREES.values()}
    unexpected_sonames=[]
    for r in baseline['comparison']['records']:
        dest=safe_path(r['destination']);path=stage/'proprietary'/dest
        if r['tree'] not in TREES:raise ValueError('Unexpected device tree')
        if dest in seen:
            if seen[dest]!=r['sha256']:raise ValueError('Conflicting destination')
            continue
        seen[dest]=r['sha256']
        if not path.is_file() or digest(path)!=r['sha256']:raise ValueError('Missing or changed blob: '+dest)
        info=elf_info(path)
        owner=TREES[r['tree']]
        if info:
            if not info['arm32_little_endian']:raise ValueError('Wrong ELF architecture')
            parts=PurePosixPath(dest).parts
            vendor=parts[0]=='vendor';relative=parts[1:] if vendor else parts
            if relative[0] not in ('lib','bin'):raise ValueError('Unsupported ELF install location')
            shared=relative[0]=='lib'
            if shared and not relative[-1].endswith('.so'):raise ValueError('Unsupported library suffix')
            name=relative[-1][:-3] if shared else relative[-1]
            if name in modules:raise ValueError('Duplicate module: '+name)
            modules.add(name)
            soname=info.get('soname')
            stem=None
            if shared and soname and soname!=relative[-1]:
                # The assembly step changes only pinned source copies to the
                # install filename. Keep an alias for legacy SONAME consumers.
                if SONAME_FIXUPS.get(dest)==(r['sha256'],soname):
                    aliases[owner].append((dest,soname))
                else:
                    unexpected_sonames.append(dest+' -> '+soname)
            needed=[]
            for lib in info['needed']:
                if not re.fullmatch(r'[A-Za-z0-9_.+-]+\.so',lib):raise ValueError('Review versioned dependency: '+lib)
                needed.append(lib[:-3])
            if dest=='vendor/lib/libstlport.so':
                imports={s['name'] for s in info['undefined_symbols']}
                if (owner!='universal5420-common' or r['sha256']!=STLPORT_SHA256
                        or not AEABI_SYMBOLS.issubset(imports)
                        or 'libelharika_aeabi_compat' in needed):
                    raise ValueError('Unexpected SM-P900 libstlport ABI')
                needed.append('libelharika_aeabi_compat')
            if dest in ('vendor/lib/soundfx/liblvverx.so','vendor/lib/soundfx/liblvvetx.so'):
                imports={s['name'] for s in info['undefined_symbols']}
                if (owner!='universal5420-common' or
                        SONAME_FIXUPS[dest]!=(r['sha256'],soname) or
                        not AUDIO_SYMBOLS.issubset(imports) or
                        'libelharika_aeabi_compat' in needed):
                    raise ValueError('Unexpected SM-P900 Lifevibes ABI: '+dest)
                needed.append('libelharika_aeabi_compat')
            if dest=='vendor/lib/sensors.universal5420.so':
                imports={s['name'] for s in info['undefined_symbols']}
                if (owner!='v1awifi' or r['sha256']!=SENSOR_SHA256
                        or not SENSOR_SYMBOLS.issubset(imports)
                        or 'libelharika_aeabi_compat' in needed):
                    raise ValueError('Unexpected SM-P900 sensors HAL ABI')
                needed.append('libelharika_aeabi_compat')
            # Legacy source HALs are Android.mk modules. Soong cannot depend on
            # Make-only modules; define their consumers in Make as well.
            if name in ('libexynoscamera', 'gpsd'):
                block = 'include $(CLEAR_VARS)\n'
                block += 'LOCAL_MODULE := ' + name + '\n'
                block += 'LOCAL_MODULE_OWNER := samsung\n'
                block += 'LOCAL_SRC_FILES := proprietary/' + dest + '\n'
                block += 'LOCAL_MODULE_CLASS := ' + ('SHARED_LIBRARIES' if shared else 'EXECUTABLES') + '\n'
                if shared: block += 'LOCAL_MODULE_SUFFIX := .so\n'
                block += 'LOCAL_MULTILIB := 32\nLOCAL_STRIP_MODULE := false\nLOCAL_CHECK_ELF_FILES := true\n'
                block += 'LOCAL_SHARED_LIBRARIES := ' + ' '.join(sorted(set(needed))) + '\n'
                if vendor: block += 'LOCAL_VENDOR_MODULE := true\n'
                if len(relative)>2: block += 'LOCAL_MODULE_RELATIVE_PATH := ' + '/'.join(relative[1:-1]) + '\n'
                block += 'include $(BUILD_PREBUILT)\n'
                groups[owner].append((dest,name,block))
                continue
            block=('cc_prebuilt_library_shared' if shared else 'cc_prebuilt_binary')+' {\n'
            block+=f'    name: {json.dumps(name)},\n    owner: "samsung",\n'
            block+=f'    srcs: [{json.dumps("proprietary/"+dest)}],\n'
            block+='    compile_multilib: "32",\n    strip: { none: true },\n    check_elf_files: true,\n'
            block+='    shared_libs: '+json.dumps(sorted(set(needed)))+',\n'
            if vendor:block+='    vendor: true,\n'
            if len(relative)>2:block+='    relative_install_path: '+json.dumps('/'.join(relative[1:-1]))+',\n'
            block+='}\n'
            groups[owner].append((dest,name,block))
        else:groups[owner].append((dest,None,None))
    if unexpected_sonames:
        raise ValueError('Unexpected SONAME: '+', '.join(unexpected_sonames))
    output.mkdir(parents=True,exist_ok=False)
    for owner,items in groups.items():
        directory=output/'samsung'/owner;directory.mkdir(parents=True)
        bp='// Generated experimental SM-P900 prebuilts; no runtime approval.\n'
        mk='# Generated experimental SM-P900 vendor rules. NOT FLASHABLE.\n'
        legacy = 'LOCAL_PATH := $(call my-dir)\n\n'
        for dest,name,block in items:
            if block:
                if block.startswith('include $(CLEAR_VARS)'): legacy += block+'\n'
                else: bp+=block+'\n'
                mk+='PRODUCT_PACKAGES += '+name+'\n'
            else:
                if dest.startswith('vendor/'):
                    target='$(TARGET_COPY_OUT_VENDOR)/'+dest[len('vendor/'):]
                else:target='$(TARGET_COPY_OUT_SYSTEM)/'+dest
                mk+=f'PRODUCT_COPY_FILES += vendor/samsung/{owner}/proprietary/{dest}:{target}\n'
        if owner=='universal5420-common':
            bp+='''// Exact SM-P900 legacy ARM EABI dependency; not a runtime approval.
cc_library_shared {
    name: "libelharika_aeabi_compat",
    owner: "elharika",
    srcs: ["compat/aeabi_divmod.S"],
    compile_multilib: "32",
    vendor: true,
    stl: "none",
}
'''
            mk+='PRODUCT_PACKAGES += libelharika_aeabi_compat\n'
            (directory/'compat').mkdir()
            for filename in ('aeabi_divmod.S','LICENSE.TXT'):
                shutil.copyfile(Path(__file__).resolve().parents[1]/'rom/compat'/filename,
                                directory/'compat'/filename)
        if aliases[owner]:
            legacy+='ifeq ($(TARGET_DEVICE),v1awifi)\n'
            for dest,soname in aliases[owner]:
                actual='$(TARGET_OUT_VENDOR)/'+dest[len('vendor/'):]
                alias='$(TARGET_OUT_VENDOR)/'+str(PurePosixPath(dest).parent)[len('vendor/'):]+'/'+soname
                legacy+=alias+': '+actual+'\n\t@mkdir -p $(dir $@)\n\tln -sfn '+PurePosixPath(dest).name+' $@\n'
                legacy+='ALL_DEFAULT_INSTALLED_MODULES += '+alias+'\n'
            legacy+='endif\n'
        (directory/'Android.mk').write_text(legacy)
        (directory/'Android.bp').write_text(bp)
        (directory/(owner+'-vendor.mk')).write_text(mk)
        (directory/'BoardConfigVendor.mk').write_text('# No additional board overrides. Experimental stock candidate set.\n')
    return {'files':len(seen),'elf_modules':len(modules),'non_elf_copy_entries':len(seen)-len(modules),'status':'GENERATED_NOT_ANDROID_COMPILED','elf_checks_enabled':True}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('baseline',type=Path);p.add_argument('stage',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();print(json.dumps(generate(json.loads(a.baseline.read_text()),a.stage,a.output),indent=2))

