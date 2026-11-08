import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "isolated_wacom_lcd_sync", ROOT / "scripts" / "experimental_disable_wacom_lcd_sync_r15.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Minimal fixture mirrors exactly the required pinned source spelling.
SOURCE = (
    "static irqreturn_t wacom_interrupt(int irq, void *dev_id)\n"
    "{\n\twacom_i2c_coord(wac_i2c);\n}\n"
    "static void wacom_i2c_sync_lcd_freq(struct wacom_i2c *wac_i2c)\n{}\n"
    "INIT_WORK(&wac_i2c->lcd_freq_work, wacom_i2c_lcd_freq_work);\n"
    "INIT_DELAYED_WORK(&wac_i2c->lcd_freq_done_work, wacom_i2c_finish_lcd_freq_work);\n"
    + mod.OLD + "\n"
)


class WacomIsolationTests(unittest.TestCase):
    def test_pinned_original_changes_only_optional_toggle(self):
        out, changed = mod.transform(SOURCE)
        self.assertTrue(changed)
        self.assertEqual(out, SOURCE.replace(mod.OLD, mod.NEW))
        self.assertIn("wacom_i2c_coord(wac_i2c)", out)
        self.assertIn("wacom_i2c_sync_lcd_freq", out)
        self.assertNotIn(mod.OLD, out)

    def test_idempotent(self):
        out, changed = mod.transform(SOURCE)
        again, changed2 = mod.transform(out)
        self.assertEqual(out, again)
        self.assertFalse(changed2)

    def test_reject_changed_upstream(self):
        with self.assertRaises(ValueError):
            mod.transform(SOURCE.replace("system_rev >= LCD_FREQ_SUPPORT_HWID", "system_rev > LCD_FREQ_SUPPORT_HWID"))

    def test_reject_repeated_enablement(self):
        with self.assertRaises(ValueError):
            mod.transform(SOURCE + mod.OLD)

    def test_reject_missing_critical_irq_anchor(self):
        with self.assertRaises(ValueError):
            mod.transform(SOURCE.replace("wacom_i2c_coord(wac_i2c);", ""))

    def test_pinned_revision_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.object(mod.subprocess, "check_output", return_value="badrevision\n"):
                with self.assertRaisesRegex(ValueError, "Wrong kernel commit"):
                    mod.apply(Path(td))

    def test_symlink_refused_and_real_file_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / mod.REL
            src.parent.mkdir(parents=True)
            target = root / "source-original"
            target.write_text(SOURCE)
            src.symlink_to(target)
            with patch.object(mod.subprocess, "check_output", return_value=mod.EXPECTED_REV + "\n"):
                with self.assertRaisesRegex(ValueError, "symlink"):
                    mod.apply(root)
            self.assertEqual(target.read_text(), SOURCE)

    def test_check_mode_fails_on_unmodified_and_passes_after_patch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / mod.REL
            src.parent.mkdir(parents=True)
            src.write_text(SOURCE)
            with patch.object(mod.subprocess, "check_output", return_value=mod.EXPECTED_REV + "\n"):
                with self.assertRaisesRegex(ValueError, "Expected patched"):
                    mod.apply(root, check=True)
                a = mod.apply(root)
                self.assertTrue(a["changed"])
                b = mod.apply(root, check=True)
                self.assertFalse(b["changed"])
                self.assertFalse(b["hardware_tested"])
                self.assertFalse(b["flash_approved"])


if __name__ == "__main__":
    unittest.main()
