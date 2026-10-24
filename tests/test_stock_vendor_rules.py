import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from generate_vendor_rules import generate

class VendorRuleTests(unittest.TestCase):
    def fixture(self,root):
        stage=root/'stage';f=stage/'proprietary/vendor/lib/egl/probe.so';f.parent.mkdir(parents=True);f.write_bytes(b'fixture')
        b={'profile':{'name':'experimental-stock-candidates'},'comparison':{'records':[{
          'tree':'android_device_samsung_universal5420-common','destination':'vendor/lib/egl/probe.so','sha256':hashlib.sha256(b'fixture').hexdigest()}]}}
        return b,stage
    def test_elf_uses_checked_module_not_copy(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);b,stage=self.fixture(root)
            with patch('generate_vendor_rules.elf_info',return_value={'arm32_little_endian':True,'needed':['libc.so']}):
                result=generate(b,stage,root/'out')
            bp=(root/'out/samsung/universal5420-common/Android.bp').read_text()
            mk=(root/'out/samsung/universal5420-common/universal5420-common-vendor.mk').read_text()
            self.assertIn('check_elf_files: true',bp);self.assertIn('relative_install_path: "egl"',bp)
            self.assertNotIn('PRODUCT_COPY_FILES',mk);self.assertEqual(result['elf_modules'],1)
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
