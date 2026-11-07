import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "r7_backup_pkg", ROOT / "scripts/package_sm_p900_pretrial_backup.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class PreTrialBackupSafety(unittest.TestCase):
    def test_real_script_is_exactly_r7_uk10_and_read_only(self):
        source = (ROOT / m.SCRIPT).read_text()
        m.inspect(source)
        self.assertIn("CURRENT_BOOT_IMAGE_LEN=5437456", source)
        self.assertIn("FULL_BOOT_BYTES=8388608", source)
        self.assertIn("boot_partition_backup_sha256=", source)
        self.assertIn("rollback_tested_on_device=NO", source)
        self.assertIn("backup_verified=YES", source)
        self.assertIn('MALI=/system/vendor/lib/egl/libGLES_mali.so', source)
        self.assertIn("CURRENT_MALI_SHA=34af399a1090295a7138297b9352334c73d569212a4bd11be4b3254dafe26cde", source)
        self.assertIn('MALI_BACKUP_SHA=$(sha256sum "$STAGE/libGLES_mali.UK10.original.backup"', source)

    def test_dangerous_partition_writes_are_refused(self):
        src = (ROOT / m.SCRIPT).read_text()
        for attack in (
            "\ndd if=/dev/zero of=/dev/block/mmcblk0p9\n",
            "\nmount -o rw /system\n",
            "\nreboot\n",
            "\ncat /tmp/source > /system/vendor/lib/egl/libGLES_mali.so\n",
            "\nhead -c 1 /dev/zero > /dev/block/mmcblk0p9\n",
        ):
            with self.subTest(attack=attack.strip()):
                with self.assertRaises(ValueError):
                    m.inspect(src + attack)

    def test_refuse_different_installed_mali_sha(self):
        src = (ROOT / m.SCRIPT).read_text().replace(
            "34af399a1090295a7138297b9352334c73d569212a4bd11be4b3254dafe26cde",
            "0" * 64,
        )
        with self.assertRaisesRegex(ValueError, "Missing backup safety"):
            m.inspect(src)

    def test_zip_has_no_flashable_images_and_verified_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            report = m.package(ROOT, out)
            self.assertFalse(report["flash_approved"])
            self.assertTrue(report["no_partition_writes"])
            self.assertLess(report["bytes"], 20000)
            zpath = out / m.ZIP
            with zipfile.ZipFile(zpath) as z:
                self.assertEqual(
                    set(z.namelist()),
                    {"META-INF/com/google/android/update-binary",
                     "META-INF/com/google/android/updater-script", "README.txt"}
                )
                self.assertIsNone(z.testzip())
                self.assertIn(b"FULL_BOOT_BYTES=8388608", z.read(
                    "META-INF/com/google/android/update-binary"))
            self.assertIn(report["sha256"], (out / "SHA256SUMS.txt").read_text())


if __name__ == "__main__":
    unittest.main()
