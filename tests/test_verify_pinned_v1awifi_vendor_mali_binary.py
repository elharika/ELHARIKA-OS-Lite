import importlib.util
from pathlib import Path
import tempfile
import unittest

p = Path(__file__).resolve().parents[1] / "scripts/verify_pinned_v1awifi_vendor_mali_binary.py"
spec = importlib.util.spec_from_file_location("donor_mali_elf", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class DonorMaliELFSafetyTests(unittest.TestCase):
    def test_known_hash_guards_are_distinct(self):
        self.assertNotEqual(m.BAD_UK5_SYSTEM_SHA256, m.TESTED_R7P0_UK10_SHA256)
        self.assertNotEqual(m.STOCK_P900_SHA256, m.BAD_UK5_SYSTEM_SHA256)
        self.assertEqual(len(m.DONOR_GIT_BLOB_SHA1), 40)

    def test_uk5_marker_exact_positive_and_negative(self):
        raw = b"header" + m.UK5_PROVEN_HANDSHAKE_BYTES + b"footer"
        self.assertEqual(m.find_uk5_signature_offsets(raw), [6])
        self.assertEqual(m.find_uk5_signature_offsets(raw[:-1].replace(b"0527", b"ffff")), [6])
        self.assertEqual(m.find_uk5_signature_offsets(b"header" + bytes.fromhex("05270126") + b"footer"), [])

    def test_invalid_binary_cannot_claim_compatibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "libGLES_mali.so"
            f.write_bytes(b"\x7fELF" + b"\x00" * 1024)
            with self.assertRaisesRegex(ValueError, "size"):
                m.audit(f)

    def test_unreviewed_large_blob_refused_by_git_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "libGLES_mali.so"
            f.write_bytes(b"\x7fELF\x01\x01" + b"\x00" * 1_100_000)
            with self.assertRaisesRegex(ValueError, "Git object"):
                m.audit(f)


if __name__ == "__main__":
    unittest.main()
