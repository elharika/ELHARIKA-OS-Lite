import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from stage_stock_vendor import stage
import test_stock_blobs


class StagingTests(unittest.TestCase):
    def fixture(self, root):
        image, baseline = test_stock_blobs.StockTests().fixture(root)
        baseline['comparison']['records'][0]['destination'] = 'vendor/lib/probe.so'
        return image, baseline

    def test_stage_deduplicate_and_preserve_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image, b = self.fixture(root)
            b['comparison']['records'].append(dict(b['comparison']['records'][0]))
            b['comparison']['records'].append({'source':'lib/missing.so','destination':'lib/missing.so'})
            out = root / 'staged'
            result = stage(image, b, out)
            self.assertEqual(result['staged_count'], 1)
            self.assertEqual(result['missing'], ['lib/missing.so'])
            self.assertEqual(result['identical_duplicate_entries_removed'], ['vendor/lib/probe.so'])
            self.assertTrue((out / 'proprietary/vendor/lib/probe.so').is_file())
            self.assertEqual(json.loads((out / 'staging.json').read_text())['status'], 'INCOMPLETE_NOT_FLASHABLE')
            with self.assertRaises(ValueError): stage(image, b, out)

    def test_corruption_leaves_no_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image, b = self.fixture(root)
            b['comparison']['records'][0]['sha256'] = '0' * 64
            out = root / 'staged'
            with self.assertRaises(ValueError): stage(image, b, out)
            self.assertFalse(out.exists())

    def test_conflicting_destinations_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image, b = self.fixture(root)
            b['comparison']['records'].append({'source':'lib/other.so','destination':'vendor/lib/probe.so'})
            with self.assertRaisesRegex(ValueError, 'Conflicting'): stage(image, b, root / 'staged')

    def test_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image, b = self.fixture(root)
            b['comparison']['records'][0]['destination'] = '../escape'
            with self.assertRaises(ValueError): stage(image, b, root / 'staged')

if __name__ == '__main__': unittest.main()
