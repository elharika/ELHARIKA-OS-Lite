import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from fix_modem_policy import BASE, TARGET, transform


class ModemPolicyTests(unittest.TestCase):
    def test_narrow_permissions_and_idempotence(self):
        changed = transform(BASE)
        self.assertEqual(transform(changed), changed)
        self.assertEqual(changed, TARGET)
        self.assertNotIn('    sysfs_sec_switch\n', changed)
        self.assertIn('allow cbd sysfs_sec_switch:file r_file_perms;', changed)
        self.assertIn('    sysfs_usb_power_writable\n', changed)
        self.assertIn('allow cbd sysfs_sec_switch:dir r_dir_perms;', changed)

    def test_reject_source_drift(self):
        for text in (BASE + '# drift', TARGET + '# drift'):
            with self.assertRaises(ValueError):
                transform(text)
