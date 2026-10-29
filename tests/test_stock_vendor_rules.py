import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from generate_vendor_rules import generate

class VendorRuleTests(unittest.TestCase):
    def fixture(self,root,destination='vendor/lib/egl/probe.so'):
        stage=root/'stage';f=stage/'proprietary'/destination;f.parent.mkdir(parents=True);f.write_bytes(b'fixture')
        b={'profile':{'name':'experimental-stock-candidates'},'comparison':{'records':[{
          'tree':'android_device_samsung_universal5420-common','destination':destination,'sha256':hashlib.sha256(b'fixture').hexdigest()}]}}
        return b,stage
    def test_elf_uses_checked_module_not_copy(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);b,stage=self.fixture(root)
            with patch('generate_vendor_rules.elf_info',return_value={'arm32_little_endian':True,'needed':['libc.so']}):
                result=generate(b,stage,root/'out')
            bp=(root/'out/samsung/universal5420-common/Android.bp').read_text()
            mk=(root/'out/samsung/universal5420-common/universal5420-common-vendor.mk').read_text()
            self.assertIn('check_elf_files: true',bp);self.assertIn('relative_install_path: "egl"',bp)
            self.assertNotIn('allow_undefined_symbols: true',bp)
            self.assertNotIn('PRODUCT_COPY_FILES',mk);self.assertEqual(result['elf_modules'],1)
            self.assertEqual(result['elf_check_exceptions'],[])
            self.assertEqual(result['undefined_symbol_exceptions'],[])
    def test_stlport_allows_only_known_undefined_symbols_case(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);b,stage=self.fixture(root,'vendor/lib/libstlport.so')
            with patch('generate_vendor_rules.elf_info',return_value={'arm32_little_endian':True,'needed':['libc.so','libm.so','libstdc++.so']}):
                result=generate(b,stage,root/'out')
            bp=(root/'out/samsung/universal5420-common/Android.bp').read_text()
            self.assertIn('name: "libstlport"',bp)
            self.assertIn('check_elf_files: true',bp)
            self.assertIn('allow_undefined_symbols: true',bp)
            self.assertEqual(result['undefined_symbol_exceptions'],['vendor/lib/libstlport.so'])
            self.assertEqual(result['elf_check_exceptions'],[])
    def test_lvverx_disables_elf_check_only_for_exact_stock_path(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);b,stage=self.fixture(root,'vendor/lib/soundfx/liblvverx.so')
            with patch('generate_vendor_rules.elf_info',return_value={'arm32_little_endian':True,'needed':['libc.so']}):
                result=generate(b,stage,root/'out')
            bp=(root/'out/samsung/universal5420-common/Android.bp').read_text()
            self.assertIn('name: "liblvverx"',bp)
            self.assertIn('check_elf_files: false',bp)
            self.assertNotIn('allow_undefined_symbols: true',bp)
            self.assertEqual(result['undefined_symbol_exceptions'],[])
            self.assertEqual(result['elf_check_exceptions'][0]['path'],'vendor/lib/soundfx/liblvverx.so')
    def test_similar_name_does_not_inherit_legacy_exception(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);b,stage=self.fixture(root,'vendor/lib/soundfx/liblvverx2.so')
            with patch('generate_vendor_rules.elf_info',return_value={'arm32_little_endian':True,'needed':['libc.so']}):
                result=generate(b,stage,root/'out')
            bp=(root/'out/samsung/universal5420-common/Android.bp').read_text()
            self.assertIn('check_elf_files: true',bp)
            self.assertNotIn('allow_undefined_symbols: true',bp)
            self.assertEqual(result['elf_check_exceptions'],[])
    def test_tampered_blob_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);b,stage=self.fixture(root);b['comparison']['records'][0]['sha256']='0'*64
            with self.assertRaises(ValueError):generate(b,stage,root/'out')
            self.assertFalse((root/'out').exists())
    def test_wrong_architecture_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);b,stage=self.fixture(root)
            with patch('generate_vendor_rules.elf_info',return_value={'arm32_little_endian':False}):
                with self.assertRaises(ValueError):generate(b,stage,root/'out')
            self.assertFalse((root/'out').exists())

if __name__=='__main__':unittest.main()
