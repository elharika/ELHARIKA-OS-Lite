#!/usr/bin/env python3
"""Fail-closed SM-P900 source manifest readiness audit; stdlib only."""
from pathlib import Path
import xml.etree.ElementTree as ET
import sys
p = Path("rom/roomservice.xml")
if not p.is_file():
    sys.exit("Missing manifest")
root = ET.parse(p).getroot()
projects = {x.get("path"): x for x in root.findall("project")}
required = {
    "device/samsung/v1awifi": "SM-P900 device tree",
    "kernel/samsung/exynos5420": "Exynos5420 kernel",
    "vendor/samsung/v1awifi": "SM-P900 vendor tree",
}
missing = [label for path, label in required.items() if path not in projects]
if missing:
    print("ROM BUILD BLOCKED: missing required source projects:")
    for label in missing:
        print(" -", label)
    sys.exit(2)
print("Required manifest entries present; this is NOT proof of build compatibility.")
