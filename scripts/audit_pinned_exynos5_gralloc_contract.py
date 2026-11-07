#!/usr/bin/env python3
"""Audit the pinned Exynos5 Gralloc source ABI assumptions.

Source inspection only: this is NOT a binary ABI compatibility verdict.
Used to prevent misleading 'AFBC is definitely enabled' conclusions.
"""
import argparse
import hashlib
import json
from pathlib import Path

EXPECTED = {
    "gralloc_makefile": (
        "LOCAL_MODULE := gralloc.$(TARGET_BOARD_PLATFORM)",
        "MALI_AFBC_GRALLOC := 1",
        "-DMALI_AFBC_GRALLOC=$(MALI_AFBC_GRALLOC)",
        "ifneq ($(TARGET_SOC), exynos5420)",
    ),
    "handle_header": (
        "struct private_handle_t : public native_handle",
        "PRIV_FLAGS_USES_ION    = 0x00000020",
        "PRIV_FLAGS_USES_UMP    = 0x00000002",
        "static const int sNumFds = 3;",
        "static const int sMagic = 0x3141592;",
        "int     fd;",
        "int     fd1;",
        "int     fd2;",
        "uint64_t base __attribute__((aligned(8)));",
    ),
    "format_chooser": (
        'property_get("ddk.set.afbc", value, "0");',
        "afbc_prop = atoi(value);",
        "if(afbc_prop == 0)",
        "return 0;",
        "GRALLOC_ARM_INTFMT_AFBC",
    ),
}


def audit(parts):
    if set(parts) != set(EXPECTED):
        raise ValueError("All pinned upstream graphics source files required")
    for component, patterns in EXPECTED.items():
        for pattern in patterns:
            if pattern not in parts[component]:
                raise ValueError("Pinned source changed: " + component + " -> " + pattern)
    chooser = parts["format_chooser"]
    zero_test = chooser.index("if(afbc_prop == 0)")
    if "return 0;" not in chooser[zero_test:zero_test + 140]:
        raise ValueError("AFBC property does not gate compression as expected")
    return {
        "status": "EXYNOS5_SOURCE_ABI_ASSUMPTIONS_RECORDED_NO_BINARY_PROOF",
        "source_sha256": {
            name: hashlib.sha256(source.encode()).hexdigest()
            for name, source in parts.items()
        },
        "gralloc_board": "exynos5",
        "device_soc": "exynos5420",
        "compiled_with_afbc_support": True,
        "afbc_enabled_by_default_in_source": False,
        "afbc_can_be_enabled_by_property": "ddk.set.afbc",
        "runtime_afbc_property_verified": False,
        "native_handle_fd_capacity": 3,
        "native_handle_fd_count_varies_by_allocation": True,
        "ion_and_ump_flags_defined": True,
        "expected_ion_private_flag": "0x00000020",
        "native_handle_binary_layout_proven_compatible_with_mali": False,
        "actual_mali_egl_swap_working": False,
        "safe_to_flash": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("gralloc_makefile", type=Path)
    p.add_argument("handle_header", type=Path)
    p.add_argument("format_chooser", type=Path)
    p.add_argument("--out", type=Path, required=True)
    x = p.parse_args()
    inputs = {name: getattr(x, name).read_text() for name in EXPECTED}
    result = audit(inputs)
    x.out.parent.mkdir(parents=True, exist_ok=True)
    x.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
