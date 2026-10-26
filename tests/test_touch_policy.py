from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fix_touch_policy as policy

class TouchPolicyTests(unittest.TestCase):
    def test_exact_command_and_no_partial_edits(self):
        original = policy.EXPECTED_BLOBS
        try:
            with tempfile.TemporaryDirectory() as temp:
                directory = Path(temp) / "sepolicy/vendor"
                directory.mkdir(parents=True)
                sources = {}
                for name, before in policy.BEFORE.items():
                    sources[name] = "# fixture\n" + before + "\n"
                    (directory / name).write_text(sources[name])
                policy.EXPECTED_BLOBS = {name: policy.blob_sha(text.encode())
                                         for name, text in sources.items()}
                (directory / "hal_lineage_touch_default.te").write_text("modified")
                with self.assertRaises(ValueError): policy.apply(temp)
                self.assertEqual((directory / "file_contexts").read_text(), sources["file_contexts"])
                (directory / "hal_lineage_touch_default.te").write_text(sources["hal_lineage_touch_default.te"])
                self.assertEqual(policy.apply(temp), 2)
                self.assertEqual(policy.apply(temp), 0)
                self.assertIn("sysfs_touchscreen_writable:s0", (directory / "file_contexts").read_text())
                self.assertIn("sysfs_sec_touchscreen:file r_file_perms", (directory / "hal_lineage_touch_default.te").read_text())
        finally:
            policy.EXPECTED_BLOBS = original
