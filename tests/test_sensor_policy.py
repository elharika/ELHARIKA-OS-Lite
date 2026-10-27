import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from fix_sensor_policy import BASE, TARGET, transform

class SensorPolicyTests(unittest.TestCase):
    def test_narrow_input_and_keep_writable_sensor_type(self):
        changed = transform(BASE)
        self.assertEqual(changed, TARGET)
        self.assertEqual(transform(changed), changed)
        self.assertIn("sysfs_input:file r_file_perms;", changed)
        self.assertNotIn("sysfs_input:file rw_file_perms;", changed)
        self.assertIn("sensors_data_file:file create_file_perms;", changed)

    def test_reject_source_drift(self):
        for text in (BASE+"# unknown", TARGET+"# unknown"):
            with self.assertRaises(ValueError):
                transform(text)
