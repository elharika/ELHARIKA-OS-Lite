import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import subprocess
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from generate_vendor_rules import generate
from verify_stock_blobs import elf_info

class VendorRuleTests(unittest.TestCase):
    def fixture(self,root):
        stage=root/'stage';f=stage/'proprietary/vendor/lib/egl/probe.so';f.parent.mkdir(parents=True);f.write_bytes(b'fixture')
        b={'identity':{'model':'SM-P900','build':'P900XXS0BPL4'},'profile':{'name':'experimental-stock-candidates'},'comparison':{'records':[{
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
    def test_soundfx_soname_keeps_original_bytes_and_installs_alias(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);baseline,stage=self.fixture(root)
            dest='vendor/lib/soundfx/liblvverx.so'
            fixture=stage/'proprietary'/dest
            fixture.parent.mkdir(parents=True)
            fixture.write_bytes(b'fixture-audio')
            baseline['comparison']['records'][0]['destination']=dest
            baseline['comparison']['records'][0]['sha256']=hashlib.sha256(fixture.read_bytes()).hexdigest()
            with patch('generate_vendor_rules.elf_info',return_value={
                    'arm32_little_endian':True,'needed':['libc.so'],
                    'soname':'libLifevibes_lvverx.so'}):
                generate(baseline,stage,root/'out')
            vendor=root/'out/samsung/universal5420-common'
            bp=(vendor/'Android.bp').read_text()
            mk=(vendor/'Android.mk').read_text()
            self.assertIn('stem: "libLifevibes_lvverx"',bp)
            self.assertIn('check_elf_files: true',bp)
            self.assertIn('$(TARGET_OUT_VENDOR)/lib/soundfx/liblvverx.so: $(TARGET_OUT_VENDOR)/lib/soundfx/libLifevibes_lvverx.so',mk)
            self.assertEqual(fixture.read_bytes(),b'fixture-audio')

    def test_unexpected_soname_and_wrong_model_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);baseline,stage=self.fixture(root)
            with patch('generate_vendor_rules.elf_info',return_value={
                    'arm32_little_endian':True,'needed':[],'soname':'bad.so'}):
                with self.assertRaisesRegex(ValueError,'Unexpected SONAME'):
                    generate(baseline,stage,root/'out')
            baseline['identity']['model']='SM-P905'
            with self.assertRaisesRegex(ValueError,'Wrong stock image identity'):
                generate(baseline,stage,root/'out')

    def test_gps_soname_preserves_hal_filename_alias(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);baseline,stage=self.fixture(root)
            dest='vendor/lib/hw/gps.universal5420.so'
            fixture=stage/'proprietary'/dest
            fixture.parent.mkdir(parents=True)
            fixture.write_bytes(b'fixture-gps')
            baseline['comparison']['records'][0]['destination']=dest
            baseline['comparison']['records'][0]['tree']='android_device_samsung_v1awifi'
            baseline['comparison']['records'][0]['sha256']=hashlib.sha256(fixture.read_bytes()).hexdigest()
            with patch('generate_vendor_rules.elf_info',return_value={
                    'arm32_little_endian':True,'needed':['libc.so'],
                    'soname':'gps.samsungAdonisandroid.so'}):
                generate(baseline,stage,root/'out')
            vendor=root/'out/samsung/v1awifi'
            self.assertIn('stem: "gps.samsungAdonisandroid"',(vendor/'Android.bp').read_text())
            self.assertIn('$(TARGET_OUT_VENDOR)/lib/hw/gps.universal5420.so: $(TARGET_OUT_VENDOR)/lib/hw/gps.samsungAdonisandroid.so',(vendor/'Android.mk').read_text())
            self.assertEqual(fixture.read_bytes(),b'fixture-gps')

    def test_readelf_detects_real_soname(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            source=root/'fixture.c';source.write_text('int fixture(void) { return 7; }\n')
            library=root/'fixture.so'
            subprocess.run(['cc','-shared','-fPIC','-Wl,-soname,libLifevibes_lvverx.so',
                            '-o',str(library),str(source)],check=True)
            self.assertEqual(elf_info(library)['soname'],'libLifevibes_lvverx.so')

    def test_stlport_requires_exact_stock_hash_and_aeabi_imports(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);baseline,stage=self.fixture(root)
            baseline['comparison']['records'][0]['destination']='vendor/lib/libstlport.so'
            stock=stage/'proprietary/vendor/lib/libstlport.so'
            stock.parent.mkdir(parents=True,exist_ok=True)
            stock.write_bytes(b'fixture-stlport')
            baseline['comparison']['records'][0]['sha256']=hashlib.sha256(stock.read_bytes()).hexdigest()
            with patch('generate_vendor_rules.elf_info',return_value={
                    'arm32_little_endian':True,'needed':['libc.so'],
                    'soname':'libstlport.so',
                    'undefined_symbols':[{'name':s} for s in ('__aeabi_ldivmod','__aeabi_uldivmod')]}):
                with self.assertRaisesRegex(ValueError,'Unexpected SM-P900 libstlport ABI'):
                    generate(baseline,stage,root/'out')

if __name__=='__main__':unittest.main()

