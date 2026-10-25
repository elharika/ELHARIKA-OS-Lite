from pathlib import Path
import sys
import tempfile
import unittest
import subprocess
import re
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from prepare_product import prepare, ENV_OLD, ENV_NEW, product_environment, mobicore_selection, camera_selection
PROJECT = Path(__file__).resolve().parents[1]

class ProductSetupTests(unittest.TestCase):
    def test_real_product_sources_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'build').mkdir()
            (root / 'build/envsetup.sh').write_text(ENV_OLD)
            for fixture, destination in [('mobicore', 'hardware/samsung_slsi/exynos5420/mobicore/daemon/Android.mk'), ('camera', 'device/samsung/universal5420-common/camera/Android.mk')]:
                path = root / destination
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text((PROJECT/'tests/fixtures'/f'{fixture}.mk').read_text())
            target = prepare(PROJECT, root)
            self.assertIn('ElharikaPenTools', (target/'elharika_v1awifi.mk').read_text())
            self.assertTrue((target/'apps/pen/src/main/java/org/elharika/pen/InkView.java').is_file())
            self.assertTrue((target/'apps/launcher/src/main/res/values-ar/strings.xml').is_file())
            with self.assertRaises(ValueError): prepare(PROJECT, root)
            self.assertEqual((root/'build/envsetup.sh').read_text(), ENV_NEW)

    def test_source_selection_and_changed_input_rejection(self):
        for fixture, patch in [('mobicore', mobicore_selection), ('camera', camera_selection)]:
            original = (PROJECT/'tests/fixtures'/f'{fixture}.mk').read_text()
            result = patch(original)
            self.assertEqual(patch(result), result)
            self.assertIn('ifneq ($(TARGET_DEVICE),v1awifi)', result)
            with self.assertRaises(ValueError): patch(original + '# changed')
        with self.assertRaises(ValueError): product_environment('unexpected input')
        self.assertEqual(product_environment(ENV_NEW), ENV_NEW)

    def test_make_selects_one_provider_for_exact_device(self):
        for fixture, patch, excluded in [
            ('camera', camera_selection, {'libexynoscamera'}),
            ('mobicore', mobicore_selection, {'libMcClient', 'libMcRegistry', 'mcDriverDaemon'}),
        ]:
            text = patch((PROJECT/'tests/fixtures'/f'{fixture}.mk').read_text())
            # Evaluate actual Make conditionals; avoid executing Android compilation.
            text = re.sub(r'^include \$\(BUILD_(SHARED_LIBRARY|EXECUTABLE)\)$',
                          '$(info MODULE=$(LOCAL_MODULE))', text, flags=re.M)
            text = re.sub(r'^include .*$', '', text, flags=re.M)
            text += '\n.PHONY: all\nall: ; @:\n'
            for device in ['v1awifi', 'another_device']:
                result = subprocess.run(['make', '--no-print-directory', '-f', '-', 'TARGET_DEVICE='+device],
                                        input=text, text=True, capture_output=True, check=True)
                modules = set(re.findall(r'^MODULE=(.*)$', result.stdout, re.M))
                self.assertEqual(bool(modules & excluded), device != 'v1awifi')
                if fixture == 'mobicore': self.assertIn('libPaApi', modules)

    def test_missing_platform_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with self.assertRaises(ValueError): prepare(PROJECT, root)
            self.assertFalse((root/'vendor').exists())

if __name__ == '__main__': unittest.main()
