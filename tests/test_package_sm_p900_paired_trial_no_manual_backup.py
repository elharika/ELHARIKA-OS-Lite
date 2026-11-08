import importlib.util
from pathlib import Path
from hashlib import sha256
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "pairtrial", ROOT / "scripts/package_sm_p900_paired_trial_no_manual_backup.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class PairedTrialSafetyTests(unittest.TestCase):
    def test_template_embeds_exact_target_hashes_and_no_data_writes(self):
        for mode in ("INSTALL", "RESTORE"):
            sh = m.updater_for(mode)
            self.assertIn(f"MODE='{mode}'", sh)
            self.assertIn("v1awifi", sh)
            self.assertIn("ro.build.version.sdk=30", sh)
            self.assertIn("50% or more", sh)
            self.assertIn("PREV_MALI_SHA", sh)
            self.assertIn('cat "$WORK/orig-full-boot.img" > "$BOOT"', sh)
            self.assertIn("WRITING=1", sh)
            self.assertIn("COMMITTED=1", sh)
            self.assertNotIn("of=\"$SYSTEM\"", sh)
            self.assertNotIn("/dev/block/mmcblk0p9", sh)
        self.assertNotEqual(m.COMPONENTS["r7_boot"][1], m.COMPONENTS["r15_boot"][1])
        self.assertNotEqual(m.COMPONENTS["old_mali"][1], m.COMPONENTS["r15_mali"][1])

    def test_untrusted_sources_rejected_before_creating_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "wrong.so"
            fake.write_bytes(b"wrong")
            sources = {key: fake for key in m.COMPONENTS}
            with self.assertRaisesRegex(ValueError, "Incorrect exact pinned"):
                m.verify_source_files(sources)

    def test_both_zip_structure_and_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            src = {}
            for key in m.COMPONENTS:
                src[key] = p / key
                src[key].write_bytes((key * 10).encode())
            synthetic = {key: (src[key].stat().st_size, sha256(src[key].read_bytes()).hexdigest())
                         for key in m.COMPONENTS}
            with patch.dict(m.COMPONENTS, synthetic):
                with patch.object(m, "verify_source_files", return_value=True):
                    results = m.build(src, p / "out")
            self.assertEqual(len(results), 2)
            self.assertEqual({v["operation"] for v in results}, {"INSTALL", "RESTORE"})
            self.assertTrue(all(v["hardware_tested"] is False for v in results))
            for row in results:
                with zipfile.ZipFile(p / "out" / row["file"]) as z:
                    self.assertIsNone(z.testzip())
                    self.assertEqual(len(z.namelist()), 6)
                    self.assertIn("META-INF/com/google/android/update-binary", z.namelist())
                    self.assertNotIn("system.img", z.namelist())
                    self.assertIn(f"MODE='{row['operation']}'", z.read(
                        "META-INF/com/google/android/update-binary").decode())


if __name__ == "__main__":
    unittest.main()
