import importlib.util
from pathlib import Path
import tempfile
import unittest

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "uk10_egl_buildid", root / "scripts/audit_uk10_device_buildid_and_egl_context.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class MaliBuildIdAndContextTest(unittest.TestCase):
    def test_distinct_caller_and_fault_site(self):
        self.assertNotEqual(m.CRASH_PC, m.CALLER_PC)
        self.assertIn(m.CRASH_PC, m.ARM_CODE)
        self.assertEqual(m.DEVICE_BUILD_ID, "1b2949cf031b30f20a970c511925875d")

    def test_unknown_elf_cannot_be_decoded(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "unrecognized.so"
            p.write_bytes(b"\x7fELF" + b"\0" * 180)
            with self.assertRaisesRegex(ValueError, "Refusing unpinned Mali blob"):
                m.audit(p)


if __name__ == "__main__":
    unittest.main()
