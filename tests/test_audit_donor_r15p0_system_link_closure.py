import importlib.util
from pathlib import Path
import tempfile
import unittest

p = Path(__file__).resolve().parents[1] / "scripts/audit_donor_r15p0_system_link_closure.py"
spec = importlib.util.spec_from_file_location("donor_r15p0_linker", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class NativeLinkPreflightSafety(unittest.TestCase):
    def test_only_expected_pinned_system_and_donor_are_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            donor = Path(tmp) / "candidate.so"
            ext4 = Path(tmp) / "system.ext4"
            donor.write_bytes(b"wrong-mali")
            ext4.write_bytes(b"wrong-image")
            with self.assertRaisesRegex(ValueError, "Unrecognized donor"):
                m.inspect(donor, ext4, m.EXPERIMENTAL_BUILT_SYSTEM_SHA)
            self.assertEqual(m.ROOT_BOARD_HAL_MODULES,
                             ("gralloc.exynos5.so", "hwcomposer.exynos5.so"))

    def test_untrusted_library_basename_rejected_by_pattern(self):
        self.assertIsNone(m.NAME_PATTERN.fullmatch("../../libm.so"))
        self.assertIsNone(m.NAME_PATTERN.fullmatch("/system/lib/libc.so"))
        self.assertIsNotNone(m.NAME_PATTERN.fullmatch("android.hardware.graphics.mapper@2.0.so"))
        self.assertEqual(m.EXPECTED_EXPANDED_BYTES, 2299998208)


if __name__ == "__main__":
    unittest.main()
