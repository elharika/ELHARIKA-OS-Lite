import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "r15pair", root / "scripts/stage_r15p0_pair_nonflash.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class R15StagingSafetyTests(unittest.TestCase):
    def test_pinned_artifacts_exact_sha_guards(self):
        self.assertEqual(m.BOOT_SIZE, 5462032)
        self.assertEqual(m.MALI_SIZE, 26858432)
        self.assertEqual(m.MALI_DDK, b"U:r15p0-00rel0")
        self.assertEqual(len(m.BOOT_SHA), 64)
        self.assertEqual(len(m.MALI_SHA), 64)

    def test_wrong_boot_prevents_candidate_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "boot.img", Path(tmp) / "libGLES_mali.so"
            a.write_bytes(b"ANDROID!" + b"\0" * 2048)
            b.write_bytes(b"\x7fELF" + b"\0" * 1024)
            with self.assertRaisesRegex(ValueError, "exact pinned original"):
                m.verify(a, b)

    def test_staged_archive_has_no_twrp_updater_or_flash_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            boot, mali = Path(tmp) / "boot", Path(tmp) / "mali"
            boot.write_bytes(b"fake BOOT")
            mali.write_bytes(b"fake Mali")
            with patch.object(m, "verify", return_value={
                "status": "PINNED_R15P0_PAIR_STAGED_NO_FLASH_APPROVAL",
                "real_device_boot_verified": False,
                "contains_install_script": False,
                "flash_approved": False
            }):
                result = m.package(boot, mali, Path(tmp) / "out")
            self.assertFalse(result["flash_approved"])
            self.assertFalse(result["contains_install_script"])
            with zipfile.ZipFile(Path(tmp) / "out" / m.ARCHIVE_NAME) as z:
                self.assertEqual(len(z.namelist()), 4)
                self.assertFalse(any(s.startswith("META-INF/") for s in z.namelist()))
                self.assertIn("DO-NOT-FLASH-README.txt", z.namelist())
                self.assertIn(b"NOT INSTALLABLE", z.read("DO-NOT-FLASH-README.txt"))


if __name__ == "__main__":
    unittest.main()
