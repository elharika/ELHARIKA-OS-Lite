import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("egl_tombstone_package", root / "scripts/build_egl_tombstone_readonly_zip.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ReadOnlyTombstonePackageTests(unittest.TestCase):
    def test_twrp_collector_is_read_only_shell(self):
        source = (root / m.SCRIPT).read_text()
        m.validate_script(source)
        self.assertIn("egl p".replace(" ", "") + "_swap_buffers", source)
        self.assertIn("/data/tombstones", source)
        self.assertIn("elharika-egl-crash-registers.txt", source)
        self.assertIn('case "$path" in *.pb) continue ;; esac', source)
        self.assertIn('DATA_MOUNTED=$(awk', source)
        self.assertIn('[ "$DATA_MOUNTED" = 1 ] || fail', source)
        self.assertIn('[ "$COUNT" -lt 5 ] || continue', source)
        self.assertIn('Data mount was verified by recovery;', source)
        self.assertNotIn("mount -t ", source)
        self.assertNotIn("printf --", source)
        self.assertNotIn("dd if=", source)

    def test_reject_unsafe_injection_and_missing_model(self):
        src = (root / m.SCRIPT).read_text()
        with self.assertRaises(ValueError):
            m.validate_script(src + "\nmount -o rw /dev/block/mmcblk0p1 /system\n")
        with self.assertRaises(ValueError):
            m.validate_script(src.replace("getprop ro.product.device", "getprop ro.unverified.model"))

    def test_package_contents_and_crc(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "out"
            report = m.package(root, destination)
            self.assertFalse(report["flash_approved"])
            self.assertEqual(report["intent"], "READ_ONLY_TOMBSTONE_EXPORT")
            zip_path = destination / m.ZIPNAME
            self.assertTrue(zip_path.exists())
            with zipfile.ZipFile(zip_path) as z:
                self.assertIsNone(z.testzip())
                files = z.namelist()
                self.assertEqual(sorted(files), sorted([
                    "META-INF/com/google/android/update-binary",
                    "META-INF/com/google/android/updater-script",
                    "README.txt",
                ]))
                self.assertEqual(z.read(files[0])[:2], b"#!")
            self.assertIn(report["sha256"], (destination / "SHA256SUMS.txt").read_text())


if __name__ == "__main__":
    unittest.main()
