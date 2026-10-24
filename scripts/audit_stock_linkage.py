#!/usr/bin/env python3
"""Static direct-dependency symbol inventory of stock libraries, never runtime approval."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from verify_stock_blobs import dump, digest, elf_info


def symbols(path):
    result = subprocess.run(['readelf','-W','--dyn-syms',str(path)],capture_output=True,text=True,
                            check=True,env={**os.environ,'LC_ALL':'C'})
    exports, strong, weak = set(), set(), set()
    for line in result.stdout.splitlines():
        c=line.split()
        if len(c)<8 or not re.fullmatch(r'\d+:',c[0]): continue
        name=c[7]
        if c[6]=='UND':
            (weak if c[4]=='WEAK' else strong).add(name)
        elif c[4] in ('GLOBAL','WEAK') and c[5] in ('DEFAULT','PROTECTED'):
            exports.add(name)
    return exports,strong,weak


def audit(image, sources):
    with tempfile.TemporaryDirectory(prefix='elharika-link-',dir='/tmp') as d:
        d=Path(d);cache={}
        def get(source):
            if source not in cache:
                p=d/str(len(cache))
                cache[source]=p if dump(image,source,p) else None
            return cache[source]
        prop=get('build.prop')
        if not prop: raise ValueError('Missing build.prop')
        props=dict(line.split('=',1) for line in prop.read_text().splitlines() if '=' in line and not line.startswith('#'))
        if (props.get('ro.product.model'),props.get('ro.product.device'))!=('SM-P900','v1awifi'):
            raise ValueError('Wrong device')
        results=[]
        for source in sources:
            p=get(source)
            if not p: raise ValueError('Missing requested library: '+source)
            info=elf_info(p)
            if not info or not info['arm32_little_endian']: raise ValueError('Expected ARM32 little-endian ELF')
            own,strong,weak=symbols(p)
            providers={};missing=[];ambiguous=[]
            for needed in info['needed']:
                if '/' in needed or needed in ('.','..'): raise ValueError('Unexpected dependency name')
                choices=[(candidate,get(candidate)) for candidate in ['lib/'+needed,'vendor/lib/'+needed]]
                choices=[(n,b) for n,b in choices if b is not None]
                if not choices: missing.append(needed)
                if len(choices)>1: ambiguous.append(needed)
                for name,binary in choices:
                    providers[name]=symbols(binary)[0]
            available=own.union(*(s for s in providers.values()))
            results.append({'source':source,'sha256':digest(p),'needed':info['needed'],
              'missing_direct_dependency_files':missing,'ambiguous_search_names':ambiguous,
              'strong_import_count':len(strong),'weak_import_count':len(weak),
              'unresolved_in_direct_stock_exports':sorted(strong-available),
              'provider_import_matches':{n:len(strong&s) for n,s in providers.items()},
              'exports_audio_effect_library_info': 'AELI' in own,
              'android11_compatible':'NOT_TESTED'})
        return {'device':'SM-P900','stock_build':props.get('ro.build.PDA'),
          'scope':'Static exact-symbol-name match against direct dependencies in STOCK image only. No transitive/global lookup, namespace, relocation, version binding, or runtime validation.',
          'results':results}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--system-image',type=Path,required=True)
    p.add_argument('--report',type=Path,required=True)
    p.add_argument('sources',nargs='+')
    a=p.parse_args()
    if a.report.resolve()==a.system_image.resolve(): p.error('Report cannot overwrite image')
    r=audit(a.system_image,a.sources)
    with a.report.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
