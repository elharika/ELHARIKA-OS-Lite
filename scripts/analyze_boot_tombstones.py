#!/usr/bin/env python3
"""Summarize native boot crashes without extracting archives or dumping memory."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import tarfile

MAX_FILE = 2 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
MAX_MEMBERS = 1000

def analyze(archive):
    groups = Counter(); evidence = []; empty = 0; consumed = 0
    with tarfile.open(archive, 'r|gz') as stream:
        for index, item in enumerate(stream):
            if index >= MAX_MEMBERS:
                raise ValueError('Too many archive members')
            if not item.isfile() or not re.fullmatch(r'data/tombstones/tombstone_\d+', item.name):
                continue
            if item.size > MAX_FILE or item.size < 0:
                raise ValueError('Oversized tombstone')
            consumed += item.size
            if consumed > MAX_TOTAL:
                raise ValueError('Tombstone read budget exceeded')
            entry = stream.extractfile(item)
            data = entry.read(MAX_FILE + 1) if entry else b''
            if len(data) != item.size:
                raise ValueError('Truncated tombstone')
            if not data:
                empty += 1; continue
            text = data.decode('utf-8', errors='replace')
            process = re.search(r'>>> (.*?) <<<', text)
            abort = re.search(r"^Abort message: '(.*)'$", text, re.M)
            key = (process.group(1) if process else 'UNKNOWN',
                   abort.group(1) if abort else 'NO_ABORT_MESSAGE')
            groups[key] += 1
            selected = []
            for line in text.splitlines():
                if re.search(r'(libEGL\s*: loaded |eglInitialize\(.*failed|F RenderEngine:)', line):
                    if line not in selected:
                        selected.append(line)
            if len(evidence) < 3:
                evidence.append({'member': item.name, 'process': key[0], 'abort': key[1],
                                 'graphics_log': selected[:12]})
    digest = hashlib.sha256()
    with Path(archive).open('rb') as source:
        for chunk in iter(lambda: source.read(1048576), b''):
            digest.update(chunk)
    return {'archive_sha256': digest.hexdigest(), 'empty_tombstones': empty,
            'nonempty_tombstones': sum(groups.values()),
            'crash_groups': [{'process': p, 'abort': a, 'reports': n}
                             for (p, a), n in groups.most_common()],
            'selected_evidence': evidence, 'hardware_approved': False,
            'warning': 'Crash signatures locate a failure; they do not prove its underlying cause.'}

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive', type=Path); p.add_argument('report', type=Path)
    a = p.parse_args()
    result = analyze(a.archive)
    a.report.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
