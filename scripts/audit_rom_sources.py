#!/usr/bin/env python3
"""Audit pinned device sources and the SM-P900 vendor generation route."""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

manifest = Path("rom/roomservice.xml")
if not manifest.is_file():
    sys.exit("Missing manifest")
projects = {entry.get("path"): entry for entry in ET.parse(manifest).getroot().findall("project")}
required = {
    "device/samsung/v1awifi": "SM-P900 device tree",
    "kernel/samsung/exynos5420": "Exynos5420 kernel",
}
missing = [label for path, label in required.items() if path not in projects]

# The licensed stock blobs are staged at build time, not committed as a
# repository project. Require the inputs and the actual CI integration route.
if "vendor/samsung/v1awifi" not in projects:
    pipeline = (
        Path("scripts/download_stock_input.py"),
        Path("scripts/unpack_stock_system.py"),
        Path("scripts/minimal_vendor_baseline.py"),
        Path("scripts/stock_candidate_baseline.py"),
        Path("scripts/stage_stock_vendor.py"),
        Path("scripts/assemble_vendor_tree.py"),
        Path("scripts/generate_vendor_rules.py"),
        Path("reports/stock-P900XXS0BPL4-vendor-comparison.json"),
    )
    missing.extend(str(path) for path in pipeline if not path.is_file())
    workflow = Path(".github/workflows/android11-build-probe.yml")
    if not workflow.is_file():
        missing.append(str(workflow))
    else:
        build = workflow.read_text()
        for invocation in ("stage_stock_vendor.py", "assemble_vendor_tree.py",
                           "SHA256SUMS", "elharika-vendor"):
            if invocation not in build:
                missing.append(f"build workflow vendor integration: {invocation}")
if missing:
    print("ROM BUILD BLOCKED: missing required source inputs:")
    for label in missing:
        print(" -", label)
    sys.exit(2)
print("Required source routes present; this is NOT proof of build compatibility.")
