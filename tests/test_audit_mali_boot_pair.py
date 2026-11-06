import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

spec = importlib.util.spec_from_file_location(
    'audit_pair',
    Path(__file__).resolve().parents[1] / 'scripts/audit_mali_boot_pair.py')
audit_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_mod)


def make_boot(kernel=b'K' * 1024, ramdisk=b'R' * 800, board=b'v1awifi'):
    page = 2048
    blob = bytearray(page)
    blob[:8] = b'ANDROID!'
    struct.pack_into('<10I', blob, 8, len(kernel), 0x10008000, len(ramdisk), 0x11000000,
                     0, 0, 0x10000100, page, 0, 369099138)
    blob[48:48 + len(board)] = board
    padding = lambda n: (-n) % page
    return bytes(blob) + kernel + bytes(padding(len(kernel))) + ramdisk + bytes(padding(len(ramdisk))) + audit_mod.TRAILER


def make_zip(path, data):
    with ZipFile(path, 'w') as z:
        z.writestr('boot.img', data)
        z.writestr('SHA256SUMS', f'{audit_mod.digest(data)}  boot.img\n')


class PairTests(unittest.TestCase):
    def test_parses_valid_legacy_samsung_boot(self):
        r = audit_mod.parse_boot(make_boot())
        self.assertEqual(r['ramdisk_bytes'], 800)
        self.assertEqual(r['kernel_bytes'], 1024)

    def test_rejects_corruption_and_missing_trailer(self):
        with self.assertRaisesRegex(ValueError, 'trailer'):
            audit_mod.parse_boot(make_boot()[:-16])
        with self.assertRaisesRegex(ValueError, 'magic'):
            audit_mod.parse_boot(b'BADMAGIC' + make_boot()[8:])

    def test_exact_pair(self):
        before, after = make_boot(), make_boot(kernel=b'N' * 1024)
        with tempfile.TemporaryDirectory() as root:
            a, b = Path(root) / 'old.zip', Path(root) / 'new.zip'
            make_zip(a, before); make_zip(b, after)
            with patch.object(audit_mod, 'ORIGINAL_SHA', audit_mod.digest(before)), patch.object(audit_mod, 'R7P0_SHA', audit_mod.digest(after)):
                r = audit_mod.audit(a, b)
                self.assertTrue(r['ramdisk_unchanged'])
                self.assertTrue(r['boot_cmdline_unchanged'])
                self.assertFalse(r['flash_approved'])

    def test_rejects_ramdisk_changes(self):
        before, after = make_boot(), make_boot(kernel=b'N' * 1024, ramdisk=b'X' * 800)
        with tempfile.TemporaryDirectory() as root:
            a, b = Path(root) / 'old.zip', Path(root) / 'new.zip'
            make_zip(a, before); make_zip(b, after)
            with patch.object(audit_mod, 'ORIGINAL_SHA', audit_mod.digest(before)), patch.object(audit_mod, 'R7P0_SHA', audit_mod.digest(after)):
                with self.assertRaisesRegex(ValueError, 'Ramdisk changed'):
                    audit_mod.audit(a, b)

    def test_rejects_cmdline_changes(self):
        before, after = make_boot(), make_boot(kernel=b'N' * 1024, board=b'v1awifi2')
        with tempfile.TemporaryDirectory() as root:
            a, b = Path(root) / 'old.zip', Path(root) / 'new.zip'
            make_zip(a, before); make_zip(b, after)
            with patch.object(audit_mod, 'ORIGINAL_SHA', audit_mod.digest(before)), patch.object(audit_mod, 'R7P0_SHA', audit_mod.digest(after)):
                with self.assertRaisesRegex(ValueError, 'boot command line'):
                    audit_mod.audit(a, b)

if __name__ == '__main__':
    unittest.main()
