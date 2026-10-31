import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from generate_vendor_rules import SENSOR_SHA256, SENSOR_SYMBOLS
from audit_assembled_vendor import COMPAT_NEEDED, COMPAT_PATHS


class SensorAeabiBridgeTests(unittest.TestCase):
    def test_exact_stock_sensor_blob_is_pinned(self):
        self.assertEqual(
            SENSOR_SHA256,
            '4e7ab23e9fe49e2650c3f52a17f3d7433b76c4c89733b02d9a7e5dcc742db848',
        )

    def test_sensor_ldivmod_is_backed_by_explicit_bridge(self):
        path = 'vendor/lib/sensors.universal5420.so'
        self.assertEqual(SENSOR_SYMBOLS, {'__aeabi_ldivmod'})
        self.assertIn(path, COMPAT_PATHS)
        self.assertEqual(COMPAT_PATHS[path], SENSOR_SYMBOLS)
        self.assertEqual(COMPAT_NEEDED, 'libelharika_aeabi_compat.so')

    def test_no_elf_validation_bypass_is_introduced(self):
        # Check the rule generator, not the audit checker: the audit checker
        # intentionally contains the forbidden strings because it rejects them.
        generator = (ROOT / 'scripts/generate_vendor_rules.py').read_text()
        self.assertNotIn('check_elf_files: false', generator)
        self.assertNotIn('allow_undefined_symbols: true', generator)

        audit = (ROOT / 'scripts/audit_assembled_vendor.py').read_text()
        self.assertIn("if 'check_elf_files: false' in bp_text", audit)
        self.assertIn("if 'LOCAL_CHECK_ELF_FILES := false' in mk_text", audit)


if __name__ == '__main__':
    unittest.main()
