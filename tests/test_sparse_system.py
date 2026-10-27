import hashlib
from pathlib import Path
import struct
import tempfile
import unittest

from scripts.verify_sparse_system import validate

HEADER = lambda blocks, chunks: struct.pack("<I4H4I", 0xED26FF3A, 1, 0, 28, 12, 4096, blocks, chunks, 0)
CHUNK = lambda kind, blocks, payload=b"": struct.pack("<2H2I", kind, 0, blocks, 12+len(payload))+payload

class SparseImageTests(unittest.TestCase):
    def check_image(self, data, valid):
        with tempfile.TemporaryDirectory() as root:
            image = Path(root) / "system.img"
            image.write_bytes(data)
            if not valid:
                with self.assertRaises(ValueError):
                    validate(image)
            else:
                result = validate(image)
                self.assertEqual(result["sha256"], hashlib.sha256(data).hexdigest())
                self.assertEqual(result["expanded_size"], 3*4096)
                self.assertFalse(result["flash_approved"])

    def test_raw_fill_hole(self):
        data = HEADER(3, 3)+CHUNK(0xCAC1, 1, b"x"*4096)+CHUNK(0xCAC2, 1, b"abcd")+CHUNK(0xCAC3, 1)
        self.check_image(data, True)

    def test_malformed_and_truncated(self):
        base = HEADER(3, 3)+CHUNK(0xCAC1, 1, b"x"*4096)+CHUNK(0xCAC2, 1, b"abcd")+CHUNK(0xCAC3, 1)
        for data in (base+b"tail", base[:-12], base[:55], HEADER(3, 1)+CHUNK(0xCAC3, 2),
                     HEADER(3, 1)+CHUNK(0xCAC5, 3), HEADER(1, 1)+CHUNK(0xCAC1, 1, b"x")):
            self.check_image(data, False)

    def test_partition_limit(self):
        self.check_image(HEADER(600000, 1)+CHUNK(0xCAC3, 600000), False)
