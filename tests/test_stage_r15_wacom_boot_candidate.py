import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'tests'))
from test_inspect_r15_kernel_baseline import kernel, CONFIG
import audit_r15_wacom_boot_pair_readonly as auditor
spec=importlib.util.spec_from_file_location('stage_boot',ROOT/'scripts/stage_r15_wacom_boot_candidate.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def original_boot():
    k=kernel();r=b'ramdisk-fixture'
    p=2048;align=lambda n:(n+p-1)//p*p
    h=bytearray(p);h[:8]=b'ANDROID!'
    struct.pack_into('<10I',h,8,len(k),0x10008000,len(r),0x11000000,0,0,0x10000100,p,0,0)
    h[576:608]=m.image_id(k,r)
    return bytes(h)+k+bytes(align(len(k))-len(k))+r+bytes(align(len(r))-len(r))+b'SEANDROIDENFORCE'


class BootStagingTests(unittest.TestCase):
    def test_repack_preserves_ramdisk_and_addresses(self):
        old=original_boot();new=kernel(version='de0cdcf1-dirty')
        with patch.object(auditor,'ORIGINAL_SHA',m.sha(old)):
            candidate,report=m.repack(old,new,m.sha(new))
        self.assertTrue(report['ramdisk_unchanged'])
        self.assertFalse(report['flash_approved'])
        self.assertEqual(m.parse_boot(candidate)['ramdisk_sha256'],m.parse_boot(old)['ramdisk_sha256'])
        self.assertNotEqual(m.sha(candidate),m.sha(old))

    def test_changed_config_or_source_blocked(self):
        old=original_boot()
        for new in (kernel(version='35d960ed'),kernel(CONFIG+'CONFIG_DIFFERENT=y\n')):
            with patch.object(auditor,'ORIGINAL_SHA',m.sha(old)):
                with self.assertRaisesRegex(ValueError,'source/config'):
                    m.repack(old,new,m.sha(new))

    def test_missing_build_hash_or_unchanged_kernel_blocked(self):
        old=original_boot();new=kernel()
        with patch.object(auditor,'ORIGINAL_SHA',m.sha(old)):
            for checksum in ('wrong','0'*64):
                with self.assertRaisesRegex(ValueError,'SHA256'):
                    m.repack(old,new,checksum)
            with self.assertRaisesRegex(ValueError,'unchanged'):
                m.repack(old,new,m.sha(new))

    def test_unverified_original_image_id_blocked(self):
        old=bytearray(original_boot());old[576]=old[576]^1;old=bytes(old)
        new=kernel(version='de0cdcf1-dirty')
        with patch.object(auditor,'ORIGINAL_SHA',m.sha(old)):
            with self.assertRaisesRegex(ValueError,'image-id'):
                m.repack(old,new,m.sha(new))

    def test_zip_noninstallable_and_original_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);old=root/'old.img';new=root/'zImage';out=root/'staged.zip'
            old.write_bytes(original_boot());new.write_bytes(kernel(version='de0cdcf1-dirty'))
            with patch.object(auditor,'ORIGINAL_SHA',m.sha(old.read_bytes())):
                m.stage(old,new,m.sha(new.read_bytes()),out)
            with ZipFile(out) as archive:
                self.assertEqual(archive.read('ORIGINAL-R15P0-BOOT.img'),old.read_bytes())
                self.assertFalse(any(n.startswith('META-INF/') for n in archive.namelist()))
                self.assertIsNone(archive.testzip())
            with self.assertRaisesRegex(ValueError,'must not exist'):
                m.stage(old,new,m.sha(new.read_bytes()),out)


if __name__=='__main__':
    unittest.main()
