import importlib.util
from pathlib import Path
import tempfile
import unittest

path = Path(__file__).resolve().parents[1] / "scripts/audit_uk10_swap_crash.py"
spec = importlib.util.spec_from_file_location("uk10_swap_audit", path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Uk10SwapAuditTests(unittest.TestCase):
    def test_fixed_pc_inside_reported_fault_symbol(self):
        self.assertEqual(m.CRASH_PC - m.FAULT_OFFSET, 0x262ea4)
        self.assertEqual(m.FAULT_SYMBOL, "eglp_swap_buffers")

    def test_unknown_proprietary_blob_refused_before_disassembly(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "unknown.so"
            file.write_bytes(b"ELF" + b"\0" * 100)
            with self.assertRaisesRegex(ValueError, "Unknown candidate Mali blob"):
                m.audit(file)


if __name__ == "__main__":
    unittest.main()
