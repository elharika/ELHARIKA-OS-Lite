from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from prepare_product import prepare
PROJECT = Path(__file__).resolve().parents[1]

class ProductSetupTests(unittest.TestCase):
    def test_real_product_sources_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'build').mkdir()
            (root / 'build/envsetup.sh').write_text('# fixture only, not Android\n')
            target = prepare(PROJECT, root)
            self.assertIn('ElharikaPenTools', (target/'elharika_v1awifi.mk').read_text())
            self.assertTrue((target/'apps/pen/src/main/java/org/elharika/pen/InkView.java').is_file())
            self.assertTrue((target/'apps/launcher/src/main/res/values-ar/strings.xml').is_file())
            with self.assertRaises(ValueError): prepare(PROJECT, root)
            self.assertEqual((root/'build/envsetup.sh').read_text(), '# fixture only, not Android\n')

    def test_missing_platform_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with self.assertRaises(ValueError): prepare(PROJECT, root)
            self.assertFalse((root/'vendor').exists())

if __name__ == '__main__': unittest.main()
