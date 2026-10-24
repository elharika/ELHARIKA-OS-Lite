#!/usr/bin/env python3
"""Conservative performance profile validator. No ROM build is implied."""
import json
from pathlib import Path
p = Path("config/performance-profile.json")
d = json.loads(p.read_text())
assert d["target"] == "v1awifi"
assert d["thermal_policy"] == "preserve-vendor-protections"
assert d["cpu_policy"] == "preserve-stock-governor-until-measured"
assert d["graphics_policy"] == "do-not-force-GPU-flags"
assert d["status"].startswith("design-profile-only")
assert all(0 < value <= 1 for value in d["animation_scales"].values())
assert 256 <= d["zram"]["candidate_mib"] <= 1536
print("PASS: safe design profile validated; device performance untested")
