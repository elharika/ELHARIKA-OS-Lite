#!/usr/bin/env python3
"""Read-only SM-P900 built system image audit; never authorizes flashing.

Uses debugfs to inspect the *expanded ext4 image* and readelf for proprietary
binary headers. Does not redistribute any extracted executable or library.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

MANIFEST = "/system/vendor/etc/vintf/manifest.xml"
MALI = "/system/vendor/lib/egl/libGLES_mali.so"
EXPECTED_PAIRED_MALI_SHA256 = "34af399a1090295a7138297b9352334c73d569212a4bd11be4b3254dafe26cde"
MAX_BLOB_SIZE = 100 * 1024 * 1024


def run(cmd):
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, timeout=60)
    if result.returncode:
        raise ValueError(f"Command failed: {cmd[0]}: {result.stderr[:400]}")
    return result.stdout


def debugfs_cat(image, path):
    if path not in (MANIFEST,):
        raise ValueError("Only the pinned manifest may be read as text")
    return run(["debugfs", "-R", "cat " + path, str(image)])


def dump_binary(image, path, output):
    if not (path == MALI or path.startswith("/system/vendor/lib/hw/")):
        raise ValueError("Unreviewed binary extraction path")
    run(["debugfs", "-R", "dump " + path + " " + str(output), str(image)])
    if not output.is_file() or output.stat().st_size < 1024 or output.stat().st_size > MAX_BLOB_SIZE:
        raise ValueError("Missing or invalid vendor binary: " + path)


def validate_manifest(text):
    root = ET.fromstring(text)
    touch = [h for h in root.findall("hal") if h.findtext("name") == "vendor.lineage.touch"]
    if len(touch) != 1:
        raise ValueError("Expected one vendor.lineage.touch HAL")
    interfaces = [i.findtext("name") for i in touch[0].findall("interface")]
    if "IKeyDisabler" in interfaces or interfaces.count("ITouchscreenGesture") != 1:
        raise ValueError("Missing or unexpected touch interfaces")
    return interfaces


def metadata_from_elf(path):
    raw = path.read_bytes()
    if raw[:5] != b"\x7fELF\x01" or raw[5:6] != b"\x01":
        raise ValueError("Not 32-bit little endian ELF: " + path.name)
    header = run(["readelf", "-W", "-h", str(path)])
    if not re.search(r"Machine:\s*ARM", header):
        raise ValueError("Not an ARM ELF shared library")
    dynamic = run(["readelf", "-W", "-d", str(path)])
    versions = run(["readelf", "-W", "-V", str(path)])
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size": len(raw),
        "needed": re.findall(r"\(NEEDED\).*Shared library: \[([^\]]+)\]", dynamic),
        "soname": (re.findall(r"\(SONAME\).*Library soname: \[([^\]]+)\]", dynamic) or [None])[0],
        "version_needed_libraries": sorted(set(re.findall(r"File:\s+([^\s]+)", versions))),
        "contains_surfaceless_egl_extension": b"EGL_KHR_surfaceless_context" in raw,
    }


def audit(image, sparse_report, staged_report):
    image = Path(image).resolve()
    sparse = json.loads(Path(sparse_report).read_text())
    staged = json.loads(Path(staged_report).read_text())
    if sparse.get("status") != "SPARSE_STRUCTURE_VALID_NOT_HARDWARE_TESTED" or sparse.get("flash_approved") is not False:
        raise ValueError("Unexpected sparse image report")
    if not image.is_file() or image.stat().st_size != sparse.get("expanded_size"):
        raise ValueError("Expanded ext4 image does not match validated sparse geometry")
    if staged.get("IKeyDisabler_advertised") is not False or staged.get("ITouchscreenGesture_advertised") is not True:
        raise ValueError("Unexpected staged VINTF guard results")
    manifest = debugfs_cat(image, MANIFEST)
    interfaces = validate_manifest(manifest)
    with tempfile.TemporaryDirectory(prefix="sm-p900-graphics-audit-") as tmp:
        dest = Path(tmp)
        mali_dest = dest / "libGLES_mali.so"
        dump_binary(image, MALI, mali_dest)
        mali = metadata_from_elf(mali_dest)
        # The installed tablet was tested with this exact UK10 r7p0 Mali blob.
        # A different new system blob is NOT approved for use with that boot.
        paired = mali["sha256"] == EXPECTED_PAIRED_MALI_SHA256
        # Root path for legacy HALs; missing /hw is logged but never treated
        # as proof of compatibility.
        hw_list = run(["debugfs", "-R", "ls -p /system/vendor/lib/hw", str(image)])
        hw_names = sorted(set(re.findall(r"(?:gralloc|hwcomposer)[A-Za-z0-9_.-]*\.so", hw_list)))
        libraries = []
        for name in hw_names[:12]:
            p = dest / name
            dump_binary(image, "/system/vendor/lib/hw/" + name, p)
            details = metadata_from_elf(p)
            libraries.append({"name": name, **details})
    return {
        "status": "OFFLINE_SYSTEM_MANIFEST_AND_GRAPHICS_INSPECTED_NOT_DEVICE_TESTED",
        "manifest": MANIFEST, "touch_interfaces": interfaces,
        "mali": mali,
        "mali_paired_with_installed_r7p0_boot": paired,
        "hw_libraries": libraries,
        "requires_coherent_egl_gralloc_hwc_ion_review": True,
        "hardware_tested": False,
        "egl_swap_fixed": False,
        "flash_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expanded_ext4", type=Path)
    parser.add_argument("sparse_report", type=Path)
    parser.add_argument("staged_touch_report", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    a = parser.parse_args()
    result = audit(a.expanded_ext4, a.sparse_report, a.staged_touch_report)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"],
                      "mali_paired": result["mali_paired_with_installed_r7p0_boot"],
                      "flash_approved": result["flash_approved"]}))


if __name__ == "__main__":
    main()
