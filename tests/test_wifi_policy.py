from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fix_wifi_policy as policy

class WifiPolicyTests(unittest.TestCase):
    def test_exact_relabel_and_fail_closed(self):
        original = policy.FILES
        try:
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "sepolicy/vendor"
                root.mkdir(parents=True)
                sources = {}
                for name, (_, before, after) in original.items():
                    source = "# pinned fixture\n" + before + "\n"
                    sources[name] = source
                    (root / name).write_text(source)
                policy.FILES = {name: (policy.blob_sha(source.encode()), before, after)
                                for name, source in sources.items()
                                for _, before, after in [original[name]]}
                self.assertEqual(policy.apply(temp), 2)
                self.assertEqual(policy.apply(temp), 0)
                self.assertIn("sysfs_wifi_writable", (root / "file_contexts").read_text())
                (root / "hal_wifi_default.te").write_text("unexpected")
                with self.assertRaises(ValueError): policy.apply(temp)
        finally:
            policy.FILES = original
