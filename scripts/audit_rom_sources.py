#!/usr/bin/env python3
"""Fail-closed SM-P900 source/vendor readiness audit; stdlib only.

The current build does not sync a static vendor repository. Instead it
reconstructs the narrow SM-P900 vendor tree from a hash-verified stock image
inside CI. This audit accepts either model, but the dynamic model is considered
ready only when every required pipeline input/script is present.
"""
from pathlib import Path
import xml.etree.ElementTree as ET
import sys

manifest = Path("rom/roomservice.xml")
if not manifest.is_file():
    sys.exit("Missing manifest")

root = ET.parse(manifest).getroot()
projects = {x.get("path"): x for x in root.findall("project")}

required_projects = {
    "device/samsung/v1awifi": "SM-P900 device tree",
    "device/samsung/v1a-common": "SM-P900 common device tree",
    "device/samsung/universal5420-common": "Exynos5420 common device tree",
    "kernel/samsung/exynos5420": "Exynos5420 kernel",
}
missing = [label for path, label in required_projects.items() if path not in projects]

# A static vendor project is optional because CI can assemble the exact-model
# vendor tree from a verified stock system image. Keep this fail-closed: every
# prerequisite below must exist before the dynamic path counts as available.
static_vendor = "vendor/samsung/v1awifi" in projects
vendor_pipeline = [
    Path("reports/stock-P900XXS0BPL4-vendor-comparison.json"),
    Path("scripts/download_stock_input.py"),
    Path("scripts/unpack_stock_system.py"),
    Path("scripts/minimal_vendor_baseline.py"),
    Path("scripts/stock_candidate_baseline.py"),
    Path("scripts/stage_stock_vendor.py"),
    Path("scripts/assemble_vendor_tree.py"),
    Path("scripts/generate_vendor_rules.py"),
    Path("scripts/verify_stock_blobs.py"),
]
missing_vendor_pipeline = [str(p) for p in vendor_pipeline if not p.is_file()]
if not static_vendor and missing_vendor_pipeline:
    missing.append("SM-P900 vendor source path (static vendor project or complete verified-stock assembly pipeline)")

if missing:
    print("ROM BUILD BLOCKED: missing required source projects/inputs:")
    for label in missing:
        print(" -", label)
    if missing_vendor_pipeline:
        print("Missing dynamic vendor pipeline files:")
        for path in missing_vendor_pipeline:
            print(" -", path)
    sys.exit(2)

vendor_mode = "static manifest project" if static_vendor else "verified stock assembly pipeline"
print(f"Required source inputs present; vendor mode: {vendor_mode}.")
print("This is a source-readiness check only; it is NOT proof of build or runtime compatibility.")
