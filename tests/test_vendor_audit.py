from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_assembled_vendor import expected_alias_rule


class VendorAuditRuleTests(unittest.TestCase):
    def test_soundfx_alias_matches_generated_android_mk_path(self):
        self.assertEqual(
            expected_alias_rule(
                'vendor/lib/soundfx/liblvverx.so',
                'libLifevibes_lvverx.so',
            ),
            '$(TARGET_OUT_VENDOR)/lib/soundfx/libLifevibes_lvverx.so: '
            '$(TARGET_OUT_VENDOR)/lib/soundfx/liblvverx.so',
        )

    def test_gps_alias_matches_generated_android_mk_path(self):
        self.assertEqual(
            expected_alias_rule(
                'vendor/lib/hw/gps.universal5420.so',
                'gps.samsungAdonisandroid.so',
            ),
            '$(TARGET_OUT_VENDOR)/lib/hw/gps.samsungAdonisandroid.so: '
            '$(TARGET_OUT_VENDOR)/lib/hw/gps.universal5420.so',
        )

    def test_non_vendor_alias_rejected(self):
        with self.assertRaises(ValueError):
            expected_alias_rule('system/lib/bad.so', 'legacy.so')


if __name__ == '__main__':
    unittest.main()
