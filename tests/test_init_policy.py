import unittest
from pathlib import Path
from scripts.fix_init_policy import transform

class InitPolicyTests(unittest.TestCase):
    def test_pinned_input_and_idempotence(self):
        original = (Path(__file__).parent / "fixtures/init_policy.te").read_text()
        changed = transform(original)
        self.assertEqual(transform(changed), changed)
        self.assertIn("allow init sysfs_input:file { r_file_perms setattr };", changed)
        self.assertNotIn("    sysfs_input\n", changed)
        self.assertIn("    sysfs_usb_power_writable\n", changed)

    def test_reject_source_drift(self):
        original = (Path(__file__).parent / "fixtures/init_policy.te").read_text()
        with self.assertRaises(ValueError):
            transform(original + "# unknown revision\n")
        with self.assertRaises(ValueError):
            transform(transform(original) + "# unknown revision\n")
