import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).resolve().parents[1] / "scripts/review_offline_mali_pair.py"
spec = importlib.util.spec_from_file_location("mali_pair_review", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def data(sha):
    return {
        "status": "OFFLINE_SYSTEM_MANIFEST_AND_GRAPHICS_INSPECTED_NOT_DEVICE_TESTED",
        "mali": {"sha256": sha, "needed": ["libc.so"], "version_needed_libraries": ["libm.so"]},
        "mali_paired_with_installed_r7p0_boot": sha == m.KNOWN_TESTED_MALI_SHA,
        "hw_libraries": [], "flash_approved": False
    }


def gate(matched):
    return {
        "status": "EXT4_AND_GRAPHICS_AUDITED_NO_HARDWARE_TEST",
        "image_sha256": "a" * 64,
        "filesystem_e2fsck_ok": True,
        "touch_vintf_ok": True,
        "paired_mali_for_current_r7p0_runtime": matched,
        "flash_approved": False
    }


class PairTests(unittest.TestCase):
    def test_mismatched_image_is_blocked(self):
        s = m.inspect(data("b" * 64), gate(False))
        self.assertEqual(s["safety_state"], "BLOCKED_SYSTEM_GPU_MISMATCH")
        self.assertFalse(s["flash_approved"])

    def test_even_matched_image_needs_egl_swap_proof(self):
        s = m.inspect(data(m.KNOWN_TESTED_MALI_SHA), gate(True))
        self.assertEqual(s["safety_state"], "BLOCKED_UNRESOLVED_EGL_SWAP_CRASH")
        self.assertFalse(s["flash_approved"])

    def test_refuse_falsified_pairing_or_approval(self):
        with self.assertRaises(ValueError):
            m.inspect(data("b" * 64), gate(True))
        a = data("b" * 64)
        a["flash_approved"] = True
        with self.assertRaises(ValueError):
            m.inspect(a, gate(False))


if __name__ == "__main__":
    unittest.main()
