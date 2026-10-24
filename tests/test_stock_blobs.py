import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('blobs', Path(__file__).resolve().parents[1] / 'scripts/verify_stock_blobs.py')
blobs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(blobs)


class StockTests(unittest.TestCase):
    def test_paths_reject_escape_and_command_injection(self):
        for path in ['../boot.img', '/boot.img', 'a/../../b', 'a b', 'a\nb', '"', '.']:
            with self.assertRaises(ValueError):
                blobs.safe_path(path)
        self.assertEqual(blobs.safe_path('vendor/lib/libGLES_mali.so'), 'vendor/lib/libGLES_mali.so')

    def fixture(self, root, wrong=False):
        tree = root / 'tree'
        (tree / 'vendor/lib').mkdir(parents=True)
        (tree / 'build.prop').write_text('ro.product.model=' + ('SM-P901' if wrong else 'SM-P900') +
            '\nro.product.device=v1awifi\nro.build.PDA=P900XXS0BPL4\n')
        payload = tree / 'vendor/lib/probe.so'
        subprocess.run(['cc', '-shared', '-fPIC', '-x', 'c', '-', '-o', str(payload)],
                       input='#include <stdio.h>\nvoid probe(void) { puts("test"); }', text=True, check=True)
        image = root / 'system.ext4'
        with image.open('wb') as f:
            f.truncate(16 * 1024 * 1024)
        subprocess.run(['mkfs.ext4', '-q', '-F', '-d', str(tree), str(image)], check=True)
        baseline = {'identity': {'model': 'SM-P900', 'device': 'v1awifi', 'build': 'P900XXS0BPL4'},
                    'comparison': {'records': [{'source': 'vendor/lib/probe.so', 'sha256': blobs.digest(payload)}]}}
        return image, baseline

    def test_read_only_extraction_and_elf_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image, baseline = self.fixture(root)
            before = blobs.digest(image)
            report = root / 'report.json'
            self.assertEqual(blobs.verify(image, baseline, report), 0)
            self.assertEqual(blobs.digest(image), before)
            result = json.loads(report.read_text())
            elf = result['records'][0]['elf']
            self.assertFalse(elf['arm32_little_endian'])
            self.assertIn('libc.so.6', elf['needed'])
            self.assertTrue(any(s['name'].startswith('puts') for s in elf['undefined_symbols']))
            self.assertEqual(result['runtime_compatibility'], 'NOT_TESTED')

    def test_missing_and_mismatch_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image, baseline = self.fixture(root)
            baseline['comparison']['records'][0]['sha256'] = '0' * 64
            baseline['comparison']['records'].append({'source': 'lib/missing.so'})
            report = root / 'report.json'
            self.assertEqual(blobs.verify(image, baseline, report), 2)
            records = json.loads(report.read_text())['records']
            self.assertFalse(records[0]['baseline_match'])
            self.assertFalse(records[1]['present'])

    def test_wrong_model_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image, baseline = self.fixture(root, wrong=True)
            with self.assertRaisesRegex(ValueError, 'identity mismatch'):
                blobs.verify(image, baseline, root / 'report.json')


if __name__ == '__main__':
    unittest.main()
