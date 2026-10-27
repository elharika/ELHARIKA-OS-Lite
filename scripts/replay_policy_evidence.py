#!/usr/bin/env python3
"""Replay trusted CI SELinux evidence without downloading an Android checkout.

Only run with artifacts from a reviewed build: this executes their host binaries.
Success checks policy compilation/assertions, not device runtime compatibility.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


def replay(evidence, output):
    evidence = evidence.resolve()
    output.mkdir(parents=True, exist_ok=True)
    inputs = evidence / 'selinux-inputs'
    host = evidence / 'policy-host'
    files = [inputs / n for n in ('policy.conf', 'policy_2.conf')]
    binaries = [host / 'bin' / n for n in ('checkpolicy', 'sepolicy-analyze')]
    for path in files + binaries:
        if not path.is_file():
            raise ValueError(f'Missing CI evidence: {path}')
    hashes = {str(p.relative_to(evidence)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in files + binaries}
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = str(host / 'lib64')
    env['ASAN_OPTIONS'] = 'detect_leaks=0'
    stages = []
    with tempfile.TemporaryDirectory(prefix='elharika-policy-') as tmp:
        compiled = str(Path(tmp) / 'policy.bin')
        commands = [
            [str(binaries[0]), '-M', '-c', '30', '-o', compiled, str(files[0])],
            [str(binaries[1]), compiled, 'neverallow', '-w', '-f', str(files[1])],
        ]
        for name, command in zip(('checkpolicy', 'sepolicy-analyze'), commands):
            result = subprocess.run(command, env=env, capture_output=True, text=True,
                                    timeout=180, check=False)
            log = result.stdout + result.stderr
            (output / (name + '.log')).write_text(log)
            stages.append({'stage': name, 'returncode': result.returncode,
                           'violations': re.findall(r'^libsepol.report_failure: (.+)$', log, re.M)})
            if result.returncode:
                break
    success = len(stages) == 2 and all(s['returncode'] == 0 for s in stages)
    report = {'policy_checks_passed': success, 'hardware_tested': False,
              'flash_approved': False, 'sha256': hashes, 'stages': stages}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0 if success else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    raise SystemExit(replay(args.evidence, args.output))
