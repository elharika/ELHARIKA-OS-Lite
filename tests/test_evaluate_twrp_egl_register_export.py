import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("egl_export_eval", ROOT / "scripts/evaluate_twrp_egl_register_export.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

BASIC = """ELHARIKA EGL / SM-P900 / READ ONLY TOMBSTONE SCAN
No system, boot, data or recovery partition changes were made.
Source selection requires both BootAnimation and eglp_swap_buffers.

--- MATCH 1 : /data/tombstones/tombstone_06 ---
>>> /system/bin/bootanimation <<<
signal 11 (SIGSEGV), code 1 (SEGV_MAPERR), fault addr 0x00000ff0
    r0 00000000  r1 00001000  r2 00002000  r3 00000000
    r8 ffffffff  r9 00000000  sl 00000000  fp 00000000
    #00 pc 00263458 /vendor/lib/egl/libGLES_mali.so (eglp_swap_buffers+1460)

"""


class FocusedReportTests(unittest.TestCase):
    def test_parse_one_complete_zero_count_crash(self):
        result = m.evaluate(BASIC)
        self.assertEqual(result["status"], "TOMBSTONE_ARM_REGISTER_CORRELATION_COMPLETE")
        self.assertEqual(result["with_all_required_registers"], 1)
        self.assertEqual(result["zero_count_underflow_observed"], 1)
        self.assertEqual(result["fault_address_matches_indexed_load"], 1)
        self.assertFalse(result["zero_count_root_cause_proven"])
        self.assertFalse(result["flash_approved"])

    def test_five_independent_synthetic_pointer_faults(self):
        blocks = [m.TITLE, "Source selection requires both BootAnimation and eglp_swap_buffers."]
        for i in range(5):
            r2 = 0x20001000 + i * 0x1000
            r1, r3 = r2 + 0x20, r2 + 0x50
            r8 = r3 - 1
            fault = (r1 + (r8 << 4)) & 0xffffffff
            blocks.append(f"""--- MATCH {i+1} : /data/tombstones/tombstone_{i:02d} ---
>>> /system/bin/bootanimation <<<
signal 11 (SIGSEGV), code 1 (SEGV_MAPERR), fault addr 0x{fault:08x}
    r0 00000000  r1 {r1:08x}  r2 {r2:08x}  r3 {r3:08x}
    r8 {r8:08x}  r9 00000000
    #00 pc 00263458 /vendor/lib/egl/libGLES_mali.so (eglp_swap_buffers+1460)
""")
        report = m.evaluate("\n".join(blocks))
        self.assertEqual(report["with_all_required_registers"], 5)
        self.assertEqual(report["fault_address_matches_indexed_load"], 5)
        self.assertEqual(report["repeating_nearby_pointer_pattern"], 5)
        self.assertEqual(report["zero_count_underflow_observed"], 0)
        self.assertTrue(report["pointer_count_semantics_unverified"])
        self.assertFalse(report["flash_approved"])

    def test_absent_tombstone_does_not_claim_success(self):
        v = m.evaluate(m.TITLE + "\nNO_MATCHING_TOMBSTONE_FOUND\n")
        self.assertEqual(v["status"], "PRIOR_TOMBSTONE_ABSENT_NOT_A_GPU_FIX")
        self.assertFalse(v["hardware_fixed"])

    def test_mixed_complete_and_incomplete_crash(self):
        second = BASIC.split("--- MATCH 1", 1)[1].replace(
            "r8 ffffffff", "r8 missing")
        both = BASIC + "\n--- MATCH 2" + second
        res = m.evaluate(both)
        self.assertEqual(res["status"], "TOMBSTONE_ARM_REGISTER_CORRELATION_PARTIAL")
        self.assertEqual(res["with_all_required_registers"], 1)

    def test_refuse_unrecognized_text(self):
        with self.assertRaises(ValueError):
            m.evaluate("fake report")


if __name__ == "__main__":
    unittest.main()
