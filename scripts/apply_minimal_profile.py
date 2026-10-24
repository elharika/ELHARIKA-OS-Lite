#!/usr/bin/env python3
"""Apply experimental no-aptX/no-Widevine profile to pinned common device sources."""
import argparse
from pathlib import Path
from apply_device_fixes import apply

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    a = p.parse_args()
    print(apply(a.source, Path(__file__).resolve().parents[1] / 'patches/minimal-profile'))
