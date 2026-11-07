#!/usr/bin/env python3
"""Inventory actual graphics HAL placement in a built SM-P900 ext4 image.

Read-only inspection. No new Android build, ELF patch, APK, or install ZIP.
Missing modules are findings, not reasons to auto-copy another device's HAL.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

DIRECTORIES = (
    "/system/lib/hw", "/system/vendor/lib/hw",
    "/system/lib/egl", "/system/vendor/lib/egl",
)
INTERESTING = re.compile(
    r"(gralloc|hwcomposer|mali|egl|mapper|allocator|ion|exynos)", re.I
)
ENTRY = re.compile(r"^\s*/\d+/[0-7]+/\d+/\d+/([^/]+)/", re.M)
SM_P900_BOARD = "exynos5"
EXPECTED_GRALLOC = f"gralloc.{SM_P900_BOARD}.so"
EXPECTED_HWC = f"hwcomposer.{SM_P900_BOARD}.so"
MAX_SIZE = 100 * 1024 * 1024


def shell(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise ValueError(f"{args[0]} failed: {result.stderr[:200]}")
    return result.stdout


def parse_entries(output):
    return sorted({name for name in ENTRY.findall(output)
                   if name.endswith(".so") and INTERESTING.search(name)})


def inspect_module(image, source, temporary):
    if not source.startswith(DIRECTORIES) or ".." in Path(source).parts:
        raise ValueError("Unsafe graphics library path")
    target = temporary / (hashlib.sha256(source.encode()).hexdigest()[:12] + ".so")
    shell(["debugfs", "-R", f"dump {source} {target}", str(image)])
    if not target.is_file() or not (1024 <= target.stat().st_size <= MAX_SIZE):
        raise ValueError("Missing or implausible shared library: " + source)
    data = target.read_bytes()
    if data[:5] != b"\x7fELF\x01" or data[5:6] != b"\x01":
        raise ValueError("Unexpected ELF class or endianness: " + source)
    hdr = shell(["readelf", "-W", "-h", str(target)])
    if not re.search(r"Machine:\s*ARM", hdr):
        raise ValueError("Not ARM32 shared library: " + source)
    dynamic = shell(["readelf", "-W", "-d", str(target)])
    return {
        "path": source,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "needed": sorted(set(re.findall(
            r"\(NEEDED\).*Shared library: \[([^\]]+)\]", dynamic))),
        "soname": (re.findall(
            r"\(SONAME\).*Library soname: \[([^\]]+)\]", dynamic) or [None])[0],
    }


def summarize(entries):
    paths = {v["path"] for v in entries}
    suffix = lambda name: [p for p in sorted(paths) if p.endswith("/" + name)]
    gra = suffix(EXPECTED_GRALLOC)
    hwc = suffix(EXPECTED_HWC)
    mali = suffix("libGLES_mali.so")
    return {
        "board": "SM-P900/v1awifi",
        "expected_board_platform": SM_P900_BOARD,
        "gralloc_exynos5": gra,
        "hwcomposer_exynos5": hwc,
        "mali_egl": mali,
        "gralloc_default": suffix("gralloc.default.so"),
        "presence": {
            "board_gralloc": bool(gra),
            "board_hwcomposer": bool(hwc),
            "mali_egl": bool(mali),
        },
        "root_cause_proven": False,
        "bootanimation_swap_tested": False,
        "hardware_tested": False,
        "flash_approved": False,
    }


def inspect(image):
    image = Path(image).resolve()
    if not image.is_file():
        raise ValueError("Read-only ext4 image missing")
    evidence = {}
    paths = []
    for directory in DIRECTORIES:
        output = shell(["debugfs", "-R", "ls -p " + directory, str(image)])
        names = parse_entries(output)
        evidence[directory] = names
        paths.extend(f"{directory}/{name}" for name in names)
    if not paths:
        raise ValueError("No graphics libraries visible in expected locations")
    if len(paths) > 60:
        raise ValueError("Unexpected number of shared library candidates")
    details = []
    errors = []
    with tempfile.TemporaryDirectory(prefix="sm-p900-graphics-inventory-") as folder:
        for path in sorted(set(paths)):
            try:
                details.append(inspect_module(image, path, Path(folder)))
            except ValueError as exc:
                errors.append({"path": path, "error": str(exc)})
    return {
        "status": ("GRAPHICS_MODULE_INVENTORY_COMPLETE"
                   if not errors else "GRAPHICS_MODULE_INVENTORY_PARTIAL"),
        "directories": evidence, "libraries": details,
        "errors": errors, "derived": summarize(details),
        "runtime_egl_swap_fixed": False, "flash_approved": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("image", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    report = inspect(a.image)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "status": report["status"],
        "expected_modules": report["derived"]["presence"],
        "errors": report["errors"], "flash_approved": False,
    }))


if __name__ == "__main__":
    main()
