#!/usr/bin/env python3
"""Derive a separate experimental stock list; never edits the original audit."""
import argparse
import copy
import json
from pathlib import Path

REMOVED = {
 'lib/libaptX_encoder.so', 'lib/libaudioroute.so',
 'vendor/bin/hw/android.hardware.drm@1.1-service.widevine',
 'vendor/etc/init/android.hardware.drm@1.1-service.widevine.rc',
 'vendor/lib/libwvhidl.so', 'vendor/lib/mediadrm/libwvdrmengine.so',
}

def derive(baseline):
    if baseline['identity']['model'] != 'SM-P900' or baseline['identity']['device'] != 'v1awifi':
        raise ValueError('Wrong baseline device')
    result = copy.deepcopy(baseline)
    records = result['comparison']['records']
    found = {r['source'] for r in records} & REMOVED
    if found != REMOVED: raise ValueError('Expected full baseline entries are missing')
    records = [r for r in records if r['source'] not in REMOVED]
    result['comparison'] = {
      'stock_build': baseline['comparison']['stock_build'],
      'required_entries': len(records),
      'present': sum(r['present_in_stock'] for r in records),
      'missing': [r['source'] for r in records if not r['present_in_stock']],
      'records': records,
    }
    result['profile'] = {'name':'experimental-minimal', 'runtime_compatibility':'NOT_TESTED',
       'omitted_optional_features':['aptX encoding','Widevine protected content'],
       'source_build_required':['libaudioroute'], 'removed_blob_paths': sorted(REMOVED)}
    return result

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('baseline',type=Path)
    p.add_argument('output',type=Path)
    a = p.parse_args()
    result = derive(json.loads(a.baseline.read_text()))
    with a.output.open('x') as f: json.dump(result,f,indent=2); f.write('\n')
