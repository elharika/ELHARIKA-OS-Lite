import tempfile
import unittest
from pathlib import Path

from scripts.fix_core_data_labels import REPLACEMENTS, PIN, apply, git_blob

FIXTURE = Path(__file__).parent / "fixtures/common_file.te"

class CoreDataLabelTests(unittest.TestCase):
    def test_pinned_idempotent_and_preserves_other_types(self):
        original = FIXTURE.read_text()
        self.assertEqual(git_blob(original.encode()), PIN)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sepolicy/vendor/file.te"
            path.parent.mkdir(parents=True)
            path.write_text(original)
            self.assertEqual(apply(tmp), 1)
            updated = path.read_text()
            for old, new in REPLACEMENTS:
                self.assertNotIn(old, updated)
                self.assertIn(new, updated)
            self.assertIn("type camera_vendor_data_file, data_file_type, file_type;", updated)
            self.assertEqual(apply(tmp), 0)
            self.assertEqual(path.read_text(), updated)

    def test_reject_source_drift_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sepolicy/vendor/file.te"
            path.parent.mkdir(parents=True)
            changed = FIXTURE.read_text() + "# drift\n"
            path.write_text(changed)
            with self.assertRaises(ValueError):
                apply(tmp)
            self.assertEqual(path.read_text(), changed)
