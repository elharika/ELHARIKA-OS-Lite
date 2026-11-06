#!/usr/bin/env python3
"""Package a statically audited SM-P900 Mali trial and exact restoration ZIP."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

from prepare_mali_candidate import ORIGINAL_SHA, sha


def package(root, output):
    review = json.loads((root / 'candidate-review.json').read_text())
    if (review['status'] != 'STATIC_VALIDATED_HARDWARE_UNTESTED' or
            review['requested_uk_version'] != [10, 0] or review['unresolved_strong_imports'] or
            not review['text_unchanged'] or review['text_relocations']):
        raise ValueError('Candidate did not pass static audit')
    original = root / 'original-libGLES_mali.so'
    candidate = root / 'candidate-libGLES_mali.so'
    if sha(original) != ORIGINAL_SHA or sha(candidate) != review['candidate_sha256']:
        raise ValueError('Payload hash mismatch')
    template = (Path(__file__).resolve().parents[1] / 'installer/mali-update-binary.in').read_text()
    output.mkdir(parents=True, exist_ok=True)
    outputs = []
    for action, old, new in [('INSTALL', original, candidate), ('RESTORE', candidate, original)]:
        script = template.replace('@ACTION@', action.lower()).replace('@EXPECTED_SHA@', sha(old)).replace('@REPLACEMENT_SHA@', sha(new))
        if '@EXPECTED_' in script or '@REPLACEMENT_' in script:
            raise ValueError('Unexpanded installer')
        subprocess.run(['sh', '-n'], input=script.encode(), check=True)
        path = output / ('ELHARIKA-SM-P900-MALI-UK10-TRIAL-' + action + '-r1.zip')
        with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            entries = {'META-INF/com/google/android/update-binary': script.encode(),
                       'META-INF/com/google/android/updater-script': b'# Experimental SM-P900 Mali trial\n',
                       'replacement.so': new.read_bytes(), 'rollback.so': old.read_bytes(),
                       'candidate-review.json': (root / 'candidate-review.json').read_bytes()}
            for name, data in entries.items():
                info = zipfile.ZipInfo(name, (2026, 11, 6, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = (0o100755 if name.endswith('update-binary') else 0o100644) << 16
                archive.writestr(info, data)
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise ValueError('ZIP CRC failed')
        outputs.append(path)
    (output / 'SHA256SUMS').write_text(''.join(sha(p) + '  ' + p.name + '\n' for p in outputs))
    return outputs


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prepared', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    for path in package(args.prepared, args.output):
        print(path)
