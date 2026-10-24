#!/usr/bin/env python3
"""Export extraction lists from the experimental stock baseline, without blobs."""
import argparse
import json
from pathlib import Path
import re
from verify_stock_blobs import safe_path

TREES={'android_device_samsung_universal5420-common','android_device_samsung_v1a-common','android_device_samsung_v1awifi'}

def export(baseline,output):
    if baseline.get('profile',{}).get('name')!='experimental-stock-candidates':
        raise ValueError('Expected candidate baseline')
    if baseline['comparison']['missing']:raise ValueError('Unresolved source paths')
    groups={name:{} for name in TREES}
    for r in baseline['comparison']['records']:
        source=safe_path(r['source']);destination=safe_path(r['destination'])
        if r['tree'] not in TREES:raise ValueError('Unexpected source tree')
        if not re.fullmatch('[0-9a-f]{40}',r.get('sha1','')):raise ValueError('Missing verified source SHA-1')
        entry=source+(':'+destination if source!=destination else '')+'|'+r['sha1']
        previous=groups[r['tree']].get(destination)
        if previous and previous!=entry:raise ValueError('Conflicting destination')
        groups[r['tree']][destination]=entry
    output.mkdir(parents=True,exist_ok=False)
    for name,entries in sorted(groups.items()):
        folder=output/name;folder.mkdir()
        (folder/'proprietary-files.txt').write_text(
            '# EXPERIMENTAL SM-P900 P900XXS0BPL4 sources. NOT RUNTIME VALIDATED.\n'
            '# Derived from the audited upstream device lists; original attribution is retained in project documentation.\n'
            '# SHA-1 pins identify source bytes only; SHA-256 verification precedes staging.\n'+
            '\n'.join(entries[k] for k in sorted(entries))+'\n')
    return sum(len(entries) for entries in groups.values())

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('baseline',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();print(export(json.loads(a.baseline.read_text()),a.output),'candidate extraction entries exported')
