#!/usr/bin/env python3
"""Derive experimental exact-model source candidates; no compatibility approval."""
import argparse
import copy
import json
from pathlib import Path
from verify_stock_blobs import safe_path


def derive(baseline, overrides):
    if (baseline['identity']['model'],baseline['identity']['build']) != ('SM-P900','P900XXS0BPL4'):
        raise ValueError('Wrong stock identity')
    if baseline.get('profile',{}).get('name')!='experimental-minimal':
        raise ValueError('Requires derived minimal profile baseline')
    if (overrides.get('device'),overrides.get('build'))!=('SM-P900','P900XXS0BPL4'):
        raise ValueError('Wrong override identity')
    result=copy.deepcopy(baseline);records=result['comparison']['records']
    changed=[]
    for rule in overrides['overrides']:
        safe_path(rule['stock_source'])
        matches=[r for r in records if r['source']==rule['required_source']]
        if len(matches)!=1 or matches[0]['present_in_stock']:
            raise ValueError('Override must match one missing requirement')
        r=matches[0]
        r['original_requirement']=r['source']
        r['source']=rule['stock_source']
        # Keep the actual Bluetooth patch filename; never masquerade as a newer firmware.
        if r['destination'].endswith('.hcd'):r['destination']=rule['stock_source']
        r.update(sha256=rule['sha256'],sha1=rule['sha1'],bytes=rule['bytes'],present_in_stock=True,
                 upstream_sha1_match=False,android11_compatible='NOT_TESTED',candidate_only=True)
        changed.append(rule['required_source'])
    result['comparison']['present']=sum(r['present_in_stock'] for r in records)
    result['comparison']['missing']=[r['source'] for r in records if not r['present_in_stock']]
    result['profile']['name']='experimental-stock-candidates'
    result['profile']['candidate_replacements']=changed
    result['profile']['release_approved']=False
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('baseline',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args()
    overrides=json.loads((Path(__file__).resolve().parents[1]/'rom/stock-candidate-overrides.json').read_text())
    result=derive(json.loads(a.baseline.read_text()),overrides)
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
