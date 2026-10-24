#!/usr/bin/env python3
import json
from pathlib import Path
p = Path("config/performance-profile.json")
v = json.loads(p.read_text(encoding="utf-8"))
assert v["target"] == "v1awifi"
assert v["status"].startswith("design-profile-only")
assert all(0 < x <= 1 for x in v["animation_scales"].values())
assert 256 <= v["zram"]["candidate_mib"] <= 1536
assert v["thermal_policy"] == "preserve-vendor-protections"
assert v["cpu_policy"] == "preserve-stock-governor-until-measured"
assert v["graphics_policy"] == "do-not-force-GPU-flags"
print("Performance profile schema checks passed; no device performance claim.")
