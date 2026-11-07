#!/usr/bin/env python3
"""Offline link-closure preflight for exact SM-P900 r15p0 donor Mali ELF.

Uses an already-built, exact-SHA, expanded Android 11 system.ext4; never
rewrites an image, compiles Android, alters the user tablet, or approves flash.
Dynamic loading/SONAME namespaces and GPU swap still require physical proof.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile


DONOR_SHA = "a00166d28cbd0213c88daadb437534310de09da4bf9fcc64f8e2207e22d76839"
EXPERIMENTAL_BUILT_SYSTEM_SHA = "a0e5904b2bb20bfb350090bef50e465514a482d71c67870a86d9711ebdc03ead"
EXPECTED_EXPANDED_BYTES = 2299998208
SEARCH_DIRS = (
    "/system/apex/com.android.runtime/lib/bionic/",
    "/system/lib/",
    "/system/vendor/lib/",
    "/system/lib/hw/",
    "/system/vendor/lib/hw/",
)
ROOT_BOARD_HAL_MODULES = ("gralloc.exynos5.so", "hwcomposer.exynos5.so")
NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.+-]+\.so$")
MAX_DEPS = 150


def inspect(donor, ext4, source_digest):
    donor = Path(donor)
    ext4 = Path(ext4)
    if hashlib.sha256(donor.read_bytes()).hexdigest() != DONOR_SHA:
        raise ValueError("Unrecognized donor Mali binary")
    if source_digest != EXPERIMENTAL_BUILT_SYSTEM_SHA:
        raise ValueError("Unrecognized system image SHA provenance")
    if not ext4.is_file() or ext4.stat().st_size != EXPECTED_EXPANDED_BYTES:
        raise ValueError("Wrong expanded Android11 filesystem")
    from prepare_mali_candidate import info, extract
    with tempfile.TemporaryDirectory(prefix="elharika-r15p0-closure-") as work:
        root = Path(work)
        donor_meta = info(donor)
        if donor_meta["textrel"]:
            raise ValueError("Donor Mali requires unsupported text relocations")
        defined = set(donor_meta["defined"])
        required = set(donor_meta["required"])
        queue = list(donor_meta["needed"]) + list(ROOT_BOARD_HAL_MODULES)
        done = set()
        absent = []
        modules = {}
        while queue:
            name = queue.pop(0)
            if name in done:
                continue
            if len(done) >= MAX_DEPS:
                raise ValueError("Too many dynamic library dependencies")
            if not NAME_PATTERN.fullmatch(name):
                raise ValueError("Unsafe ELF DT_NEEDED basename: " + name)
            done.add(name)
            target = root / name
            found = None
            for folder in SEARCH_DIRS:
                if extract(ext4, folder + name, target):
                    found = folder + name
                    break
            if found is None:
                absent.append(name)
                continue
            dep = info(target)
            modules[name] = {
                "source_path": found,
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "needed": sorted(set(dep["needed"])),
                "strong_import_count": len(dep["required"]),
            }
            defined.update(dep["defined"])
            required.update(dep["required"])
            queue.extend(dep["needed"])
        unresolved = sorted(required - defined)
        # A passing symbol check does NOT prove ELF linker namespaces, Gralloc
        # handle ABI, ION ioctl compatibility, HWComposer, or eglSwapBuffers.
        static_pass = not absent and not unresolved
        return {
            "status": ("STATIC_SYMBOL_CLOSURE_PASSED_NOT_HARDWARE_TESTED"
                       if static_pass else "STATIC_LINK_DEPENDENCIES_BLOCKED"),
            "donor_mali_sha256": DONOR_SHA,
            "donor_mali_ddk": "U:r15p0-00rel0",
            "system_image_sha256": source_digest,
            "system_unmodified": True,
            "root_exynos5_modules": list(ROOT_BOARD_HAL_MODULES),
            "donor_mali_needed": sorted(set(donor_meta["needed"])),
            "donor_mali_strong_imports": len(donor_meta["required"]),
            "checked_dependency_count": len(done),
            "checked_binaries": modules,
            "missing_dependencies": sorted(set(absent)),
            "unresolved_strong_imports": unresolved[:150],
            "unresolved_strong_count": len(unresolved),
            "static_symbols_resolved": static_pass,
            "runtime_linker_namespace_verified": False,
            "vendor_hal_native_handle_abi_verified": False,
            "kernel_uk_handshake_verified_on_device": False,
            "egl_swap_or_launcher_verified": False,
            "flash_approved": False,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("donor", type=Path)
    parser.add_argument("system_ext4", type=Path)
    parser.add_argument("--system-sha256", required=True)
    parser.add_argument("--out", required=True, type=Path)
    a = parser.parse_args()
    r = inspect(a.donor, a.system_ext4, a.system_sha256)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(r, indent=2) + "\n")
    print(json.dumps({
        "status": r["status"],
        "missing_dependencies": r["missing_dependencies"],
        "unresolved_strong_count": r["unresolved_strong_count"],
        "flash_approved": False,
    }))


if __name__ == "__main__":
    main()
