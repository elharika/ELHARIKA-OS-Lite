import gzip
import importlib.util
import lzma
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('kernel_baseline', SCRIPTS / 'inspect_r15_kernel_baseline.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
CONFIG = '# fixture\nCONFIG_MALI_T6XX_R15P0=y\n# CONFIG_USE_OF is not set\nCONFIG_CPU_32v7=y\n'


def kernel(config=CONFIG, version='de0cdcf1', raw=None):
    if raw is None:
        raw = (b'Linux version 3.4.113-g' + version.encode() + b' (fixture)\x00' +
               b'IKCFG_ST' + gzip.compress(config.encode(), mtime=0) + b'IKCFG_ED')
    payload = lzma.compress(raw, format=lzma.FORMAT_ALONE,
                            filters=[{'id': lzma.FILTER_LZMA1, 'dict_size': 1 << 25}])
    header = bytearray(64)
    struct.pack_into('<3I', header, 0x24, 0x016F2818, 0, len(header)+len(payload))
    return bytes(header) + payload


def boot(k):
    header = bytearray(2048)
    struct.pack_into('<I', header, 8, len(k))
    return bytes(header) + k


class KernelBaselineTests(unittest.TestCase):
    def test_extract_real_format_fixture(self):
        result, text = m.extract(kernel())
        self.assertEqual(text, CONFIG)
        self.assertEqual(result['symbols']['CONFIG_CPU_32v7'], 'y')
        self.assertEqual(result['appended_bytes'], 0)

    def test_same_source_and_config(self):
        with patch.object(m, 'analyze', return_value={'original_boot_sha256': 'fixture'}):
            report, text = m.inspect(boot(kernel()), kernel())
        self.assertTrue(report['same_source_and_config'])
        self.assertEqual(report['config_changed_count'], 0)
        self.assertFalse(report['flash_approved'])
        self.assertEqual(text, CONFIG)

    def test_source_and_config_drift_reported(self):
        with patch.object(m, 'analyze', return_value={'original_boot_sha256': 'fixture'}):
            report, _ = m.inspect(boot(kernel()), kernel(CONFIG.replace('32v7=y', '32v7=m'), '35d960ed'))
        self.assertFalse(report['same_source_and_config'])
        self.assertFalse(report['candidate_source_matches_original'])
        self.assertEqual(report['config_changed_count'], 1)

    def test_reject_wrong_original_source_or_of(self):
        for original in (kernel(version='35d960ed'), kernel(CONFIG.replace('# CONFIG_USE_OF is not set', 'CONFIG_USE_OF=y'))):
            with patch.object(m, 'analyze', return_value={'original_boot_sha256': 'fixture'}):
                with self.assertRaises(ValueError):
                    m.inspect(boot(original), kernel())

    def test_no_appended_data_assumption(self):
        with self.assertRaisesRegex(ValueError, 'Appended'):
            m.extract(kernel() + b'dtb')

    def test_missing_lzma_and_truncated_stream(self):
        for data in (b'x'*64, kernel()[:-8]):
            payload = bytearray(data)
            struct.pack_into('<3I', payload, 0x24, 0x016F2818, 0, len(payload))
            with self.assertRaises(ValueError):
                m.extract(payload)

    def test_ambiguous_config_markers(self):
        raw = b'Linux version fixture\x00IKCFG_STIKCFG_STIKCFG_ED'
        with self.assertRaisesRegex(ValueError, 'Ambiguous embedded'):
            m.extract(kernel(raw=raw))

    def test_missing_or_duplicate_config_symbols_rejected(self):
        for config in ('# nothing\n', 'CONFIG_X=y\nCONFIG_X=n\n', 'CONFIG_BROKEN\n'):
            with self.assertRaises(ValueError):
                m.config_values(config)

    def test_bounded_kernel_decompression(self):
        with patch.object(m, 'MAX_RAW', 32):
            with self.assertRaisesRegex(ValueError, 'decompression exceeds'):
                m.extract(kernel())

    def test_bounded_config_decompression(self):
        with patch.object(m, 'MAX_CONFIG', 8):
            with self.assertRaisesRegex(ValueError, 'config exceeds'):
                m.extract(kernel())

    def test_config_diff_counts_removed_added_changed(self):
        result = m.differences({'CONFIG_A':'y', 'CONFIG_B':'m'}, {'CONFIG_A':'n', 'CONFIG_C':'y'})
        self.assertEqual(len(result), 3)
        self.assertIsNone(result['CONFIG_B']['candidate'])
        self.assertIsNone(result['CONFIG_C']['original'])


if __name__ == '__main__':
    unittest.main()
