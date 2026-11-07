import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

root = Path(__file__).resolve().parents[1]
module_path = root / "scripts/package_r15p0_pair_readonly_preflight.py"
spec = importlib.util.spec_from_file_location("sm_p900_r15_pair_preflight", module_path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class PairPreflightTests(unittest.TestCase):
    def test_strict_read_only_script_guards(self):
        source = (root / m.SCRIPT).read_text()
        m.verify(source)
        self.assertIn("boot_status=%s", source)
        self.assertIn("mali_status=%s", source)
        self.assertIn("MALI_STATUS=UNKNOWN_DO_NOT_FLASH", source)
        self.assertIn("BOOT_STATUS=UNKNOWN_DO_NOT_FLASH", source)
        self.assertIn("bootloader_family=P900", source)
        self.assertIn('STAGED=$(mktemp "$SD/.elharika', source)
        self.assertNotIn('cat "$TMP" > "$TARGET"', source)
        self.assertNotIn("mount -t ", source)

    def test_refuse_raw_partition_writes(self):
        source = (root / m.SCRIPT).read_text()
        for bad in ("\ndd if=/dev/zero of=/dev/block/mmcblk0p9\n",
                    '\ncat "$TMP" > "$BOOT"\n',
                    '\ncat "$TMP" > "$MALI_PATH"\n',
                    "\nmount -o rw /system\n",
                    "\nreboot\n"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    m.verify(source + bad)

    def test_fail_if_known_hash_is_missing(self):
        source = (root / m.SCRIPT).read_text()
        with self.assertRaisesRegex(ValueError, "Missing preflight guard"):
            m.verify(source.replace(
                "7d15b15e127e4b31841e1081efac31d2c298c2748dbc5d55889a3e8d45e20d14",
                "0" * 64,
            ))

    def test_tiny_twrp_zip_has_no_flash_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            report = m.package(root, directory)
            self.assertFalse(report["flash_approved"])
            self.assertTrue(report["readonly"])
            zip_path = directory / m.ZIPNAME
            self.assertLess(zip_path.stat().st_size, 16000)
            with zipfile.ZipFile(zip_path) as z:
                self.assertIsNone(z.testzip())
                self.assertEqual(sorted(z.namelist()), sorted([
                    "META-INF/com/google/android/update-binary",
                    "META-INF/com/google/android/updater-script",
                    "README.txt",
                ]))
                self.assertNotIn("boot.img", z.namelist())
                self.assertNotIn("libGLES_mali.so", z.namelist())
                self.assertTrue(z.read("META-INF/com/google/android/update-binary").startswith(b"#!/sbin/sh\n"))


if __name__ == "__main__":
    unittest.main()
