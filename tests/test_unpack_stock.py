import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('unpack', Path(__file__).resolve().parents[1] / 'scripts/unpack_stock_system.py')
unpack = importlib.util.module_from_spec(spec)
spec.loader.exec_module(unpack)

class SparseTests(unittest.TestCase):
    def header(self, count=3, chunks=3):
        return struct.pack('<I4H4I', 0xed26ff3a, 1, 0, 28, 12, 4, count, chunks, 0)

    def run_expand(self, content):
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d)/'sparse', Path(d)/'ext4'
            src.write_bytes(content)
            unpack.expand(src, dst)
            return dst.read_bytes()

    def test_raw_fill_hole(self):
        content = self.header() + struct.pack('<2H2I', 0xcac1, 0, 1, 16) + b'RAW!'
        content += struct.pack('<2H2I', 0xcac2, 0, 1, 16) + b'FILL'
        content += struct.pack('<2H2I', 0xcac3, 0, 1, 12)
        self.assertEqual(self.run_expand(content), b'RAW!FILL'+b'\0'*4)

    def test_truncated_rejected(self):
        with self.assertRaises(ValueError):
            self.run_expand(self.header())

    def test_output_bound_rejected(self):
        with self.assertRaises(ValueError):
            self.run_expand(self.header(count=0xffffffff))

    def test_chunk_overflow_rejected(self):
        with self.assertRaises(ValueError):
            self.run_expand(self.header(count=1, chunks=1)+struct.pack('<2H2I',0xcac3,0,2,12))

if __name__ == '__main__':
    unittest.main()
