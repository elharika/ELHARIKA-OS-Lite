import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).resolve().parents[1] / "scripts/inspect_egl_fault_registers.py"
spec = importlib.util.spec_from_file_location("egl_fault_registers", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

HEADER = """signal 11 (SIGSEGV), code 1 (SEGV_MAPERR), fault addr {fault}
    r0 00000000  r1 {r1}  r2 00002000  r3 {r3}
    r4 11111111  r5 22222222  r6 33333333  r7 44444444
    r8 {r8}  r9 00000000  sl 00000000  fp 00000000
    #00 pc 00263458  /vendor/lib/egl/libGLES_mali.so (eglp_swap_buffers+1460)
"""

def make(fault="0x00000ff0", r1="00001000", r3="00000000", r8="ffffffff"):
    return HEADER.format(fault=fault, r1=r1, r3=r3, r8=r8)


class CrashRegisterTests(unittest.TestCase):
    def test_zero_count_underflow_is_detectable(self):
        v = m.parse_tombstone(make())
        self.assertTrue(v["fault_address_matches_ldr"])
        self.assertTrue(v["r8_matches_r3_minus_one"])
        self.assertTrue(v["zero_count_underflow_observed"])
        self.assertFalse(v["root_cause_proven"])

    def test_nonzero_count_is_not_underflow(self):
        v = m.parse_tombstone(make("0x00001010", "00001000", "00000002", "00000001"))
        self.assertTrue(v["fault_address_matches_ldr"])
        self.assertFalse(v["zero_count_underflow_observed"])

    def test_invalid_address_reports_disagreement(self):
        v = m.parse_tombstone(make("0x00004000"))
        self.assertFalse(v["fault_address_matches_ldr"])

    def test_partial_snapshot_no_fabricated_registers(self):
        v = m.parse_tombstone(make().replace("r8 ffffffff", "r8 --"))
        self.assertEqual(v["status"], "INCOMPLETE_TOMBSTONE_REGISTERS")

    def test_refuse_other_crash_site(self):
        with self.assertRaises(ValueError):
            m.parse_tombstone(make().replace("00263458", "00112233"))


if __name__ == "__main__":
    unittest.main()
