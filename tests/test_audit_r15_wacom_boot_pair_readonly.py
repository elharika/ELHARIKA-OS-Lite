import importlib.util
import struct
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("audit_pair",ROOT/"scripts/audit_r15_wacom_boot_pair_readonly.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def fixture(ks=b"z"*3500, rs=b"r"*1700, trailer=m.SAMSUNG_TRAILER):
    page=2048
    header=bytearray(page)
    header[:8]=b"ANDROID!"
    struct.pack_into("<10I",header,8,len(ks),0x40008000,len(rs),0x42000000,0,0,0x40000100,page,0,0)
    return (bytes(header)+ks+bytes(m.rounded(len(ks),page)-len(ks))+
            rs+bytes(m.rounded(len(rs),page)-len(rs))+trailer)

class PairAuditTest(unittest.TestCase):
    def test_valid_is_never_flash_approved(self):
        old=fixture();new=b"new zImage payload"
        with patch.object(m,"ORIGINAL_SHA",m.digest(old)):
            r=m.analyze(old,new)
        self.assertFalse(r["flash_approved"])
        self.assertFalse(r["boot_repacking_proven_safe"])
        self.assertFalse(r["dtb_structure_validated"])
        self.assertEqual(r["experimental_kernel_sha256"],m.digest(new))
        self.assertEqual(r["ramdisk_bytes"],1700)

    def test_hash_drift_rejected(self):
        with self.assertRaisesRegex(ValueError,"SHA changed"):
            m.analyze(fixture(),b"zImage")

    def test_boot_trailer_rejected(self):
        old=fixture(trailer=b"unsupported trailer")
        with patch.object(m,"ORIGINAL_SHA",m.digest(old)):
            with self.assertRaisesRegex(ValueError,"trailer"):
                m.analyze(old,b"zImage")

    def test_header_rejected(self):
        old=bytearray(fixture());old[8:12]=(0).to_bytes(4,"little")
        with patch.object(m,"ORIGINAL_SHA",m.digest(old)):
            with self.assertRaisesRegex(ValueError,"header"):
                m.analyze(bytes(old),b"zImage")

    def test_untrusted_image_refused(self):
        old=fixture()
        with patch.object(m,"ORIGINAL_SHA",m.digest(old)):
            with self.assertRaisesRegex(ValueError,"zImage absent"):
                m.analyze(old,b"")

    def test_read_only_payloads(self):
        old=fixture()
        with patch.object(m,"ORIGINAL_SHA",m.digest(old)):
            result=m.analyze(old,b"a"*4200)
        self.assertEqual(m.digest(old),result["original_boot_sha256"])
        self.assertTrue(result["zimage_is_standalone_not_boot"])
        self.assertEqual(result["user_spen_drawing_on_experimental_kernel"],"NOT_TESTED")

if __name__=="__main__":
    unittest.main()
