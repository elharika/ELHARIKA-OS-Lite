#!/usr/bin/env python3
"""Bounded experimental SM-P900 R15P0 Wacom LCD-sync isolation, never a flash fix.

Target: salih4187/android_kernel_samsung_exynos5420 @35d960ed3c2de3d5558b782257053599cded659e
Only make the optional *display-frequency feedback* inert at stylus probe.
Never edit coordinate IRQ, pressure, touch, booster, GPU, DTS or firmware paths.
"""
import argparse
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

EXPECTED_REV = "35d960ed3c2de3d5558b782257053599cded659e"
REL = Path("drivers/input/wacom/wacom_i2c.c")
OLD = (
    "\tif (likely(system_rev >= LCD_FREQ_SUPPORT_HWID))\n"
    "\t\twac_i2c->use_lcd_freq_sync = true;"
)
NEW = (
    "\tif (likely(system_rev >= LCD_FREQ_SUPPORT_HWID))\n"
    "\t\twac_i2c->use_lcd_freq_sync = false; /* SM-P900 experiment: isolate LCD frequency feedback */"
)
ANCHORS = (
    "static void wacom_i2c_sync_lcd_freq(struct wacom_i2c *wac_i2c)",
    "INIT_WORK(&wac_i2c->lcd_freq_work, wacom_i2c_lcd_freq_work);",
    "INIT_DELAYED_WORK(&wac_i2c->lcd_freq_done_work, wacom_i2c_finish_lcd_freq_work);",
    "static irqreturn_t wacom_interrupt(int irq, void *dev_id)",
    "wacom_i2c_coord(wac_i2c);",
)
STATUS = "R15P0_WACOM_LCD_FREQ_FEEDBACK_DISABLED_FOR_EXPERIMENT_NOT_FLASHABLE"


def transform(contents: str):
    if any(contents.count(anchor) != 1 for anchor in ANCHORS):
        raise ValueError("Pinned Wacom source anchors missing or repeated")
    if contents.count(OLD) == 1 and NEW not in contents:
        patched = contents.replace(OLD, NEW, 1)
        assert patched.replace(NEW, OLD, 1) == contents
        return patched, True
    if contents.count(NEW) == 1 and OLD not in contents:
        return contents, False
    raise ValueError("Unexpected Wacom enablement source; refusing to patch")


def apply(root: Path, check: bool = False):
    root = root.resolve()
    got = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    if got != EXPECTED_REV:
        raise ValueError(f"Wrong kernel commit: {got}")
    path = root / REL
    if path.is_symlink() or not path.is_file():
        raise ValueError("Wacom source missing or symlink")
    before = path.read_bytes()
    if b"\r\n" in before or b"\x00" in before:
        raise ValueError("Unexpected Wacom source encoding")
    st = os.stat(path, follow_symlinks=False)
    if not stat.S_ISREG(st.st_mode):
        raise ValueError("Wacom target not a regular file")
    result, changed = transform(before.decode("utf-8"))
    if check:
        if changed:
            raise ValueError("Expected patched source but still original")
    elif changed:
        path.write_text(result)
    return dict(
        status=STATUS,
        source_revision=EXPECTED_REV,
        path=str(REL),
        check_mode=check,
        changed=changed,
        optional_lcd_sync_enabled=False,
        coordinate_irq_source_untouched=True,
        S_Pen_pressure_and_button_source_untouched=True,
        gpu_source_untouched=True,
        hardware_tested=False,
        kernel_compiled=False,
        boot_image_built=False,
        flash_approved=False,
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("kernel_root", type=Path)
    p.add_argument("--check", action="store_true")
    p.add_argument("--report", type=Path)
    args = p.parse_args()
    report = apply(args.kernel_root, check=args.check)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as e:
        sys.exit(f"Wacom LCD sync patch REFUSED: {e}")
