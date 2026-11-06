import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'scripts/fix_missing_keydisabler_hal.py'
spec = importlib.util.spec_from_file_location('fix_hal', path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class KeyDisablerTests(unittest.TestCase):
    def test_only_optional_unregistered_interface_removed(self):
        before = ('<manifest><hal><name>vendor.lineage.touch</name>\n' +
                  mod.BEFORE + mod.GESTURE + '</hal></manifest>')
        after, changed = mod.patch_manifest(before)
        self.assertTrue(changed)
        self.assertNotIn('IKeyDisabler', after)
        self.assertIn('ITouchscreenGesture', after)
        again, changed = mod.patch_manifest(after)
        self.assertFalse(changed)
        self.assertEqual(again, after)

    def test_unknown_layout_is_rejected(self):
        with self.assertRaises(ValueError):
            mod.patch_manifest('<manifest><hal><name>vendor.lineage.touch</name></hal></manifest>')

if __name__ == '__main__': unittest.main()
