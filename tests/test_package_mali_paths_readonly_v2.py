import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "mali_paths_package", root / "scripts/package_mali_paths_readonly_v2.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SystemMountProbeTests(unittest.TestCase):
    def test_readonly_guards_and_mount_diagnostics(self):
        script = (root / module.SCRIPT).read_text()
        module.validate(script)
        self.assertIn('awk -v target="$d"', script)
        self.assertIn('readlink -f "$candidate"', script)
        self.assertIn('case "$real" in', script)
        self.assertIn("NO_RECOGNIZED_SYSTEM_MOUNT", script)
        self.assertIn("FILE_NOT_FOUND_IN_KNOWN_PATHS", script)
        self.assertIn("printf 'visible_egl_directory=%s", script)
        self.assertNotIn("head -c", script)
        self.assertNotIn("mount -o rw", script)

    def test_refuse_writing_partitions(self):
        original = (root / module.SCRIPT).read_text()
        for dangerous in ("\nmount -o rw /system\n",
                          "\ndd if=/dev/zero of=/dev/block/mmcblk0p7\n",
                          "\nreboot\n",
                          "\ncat /tmp/data > /vendor/lib/egl/libGLES_mali.so\n"):
            with self.subTest(command=dangerous.strip()):
                with self.assertRaises(ValueError):
                    module.validate(original + dangerous)

    def test_package_is_small_and_unflashable(self):
        with tempfile.TemporaryDirectory() as dir:
            output = Path(dir)
            report = module.package(root, output)
            self.assertFalse(report["flash_approved"])
            self.assertLess(report["size"], 16000)
            with zipfile.ZipFile(output / module.ZIPNAME) as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual(set(archive.namelist()), {
                    "META-INF/com/google/android/update-binary",
                    "META-INF/com/google/android/updater-script",
                    "README.txt",
                })
                self.assertNotIn("boot.img", archive.namelist())
                self.assertEqual(archive.read("META-INF/com/google/android/update-binary")[:2], b"#!")


if __name__ == "__main__":
    unittest.main()
