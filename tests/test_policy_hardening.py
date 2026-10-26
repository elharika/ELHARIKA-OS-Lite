from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from harden_sepolicy import ORIGINAL, REMOVALS, apply

class PolicyHardeningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / "sepolicy/vendor"
        self.directory.mkdir(parents=True)
        for name, source in ORIGINAL.items():
            (self.directory / name).write_text(source)

    def test_exact_inputs_and_idempotence(self):
        self.assertEqual(apply(self.root), 3)
        self.assertEqual(apply(self.root), 0)
        for name, source in ORIGINAL.items():
            self.assertEqual((self.directory / name).read_text(),
                             source.replace(REMOVALS[name], ""))
            self.assertEqual(source.count(REMOVALS[name]), 1)
        self.assertIn('sensors_data_file:file create_file_perms',
                      (self.directory / 'hal_sensors_default.te').read_text())

    def test_modified_source_rejected_without_partial_writes(self):
        (self.directory / "cbd.te").write_text("unexpected")
        with self.assertRaises(ValueError):
            apply(self.root)
        self.assertEqual((self.directory / "system_server.te").read_text(),
                         ORIGINAL["system_server.te"])

if __name__ == "__main__":
    unittest.main()
