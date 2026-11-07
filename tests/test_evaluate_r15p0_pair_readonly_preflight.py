import importlib.util
from pathlib import Path
import unittest

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "sm_p900_r15_preflight_eval",
    root / "scripts/evaluate_r15p0_pair_readonly_preflight.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def evidence(boot="CURRENT_R7P0_KBUILD_FIXED", mali="TESTED_UK10_TRIAL",
             r7=None, r15=None, mali_sha=None):
    r7 = m.R7_SHA if r7 is None else r7
    r15 = "0" * 64 if r15 is None else r15
    mali_sha = {
        "TESTED_UK10_TRIAL": m.UK10_SHA,
        "PINNED_DONOR_R15P0": m.DONOR_SHA,
        "BLOCKED_UK5_BASE": m.UK5_SHA,
        "NOT_VISIBLE_MOUNT_SYSTEM_READ_ONLY": "NOT_VISIBLE",
    }.get(mali, "1" * 64) if mali_sha is None else mali_sha
    return f"""{m.HEADER}
device=v1awifi
bootloader_family=P900
boot_status={boot}
boot_r7_prefix_sha256={r7}
boot_r15_prefix_sha256={r15}
mali_status={mali}
mali_path=/system/system/vendor/lib/egl/libGLES_mali.so
mali_sha256={mali_sha}
boot_partition_modified=NO
system_partition_modified=NO
data_partition_modified=NO
flash_approved=NO
physical_boot_verified=NO
This is diagnostic evidence only.
"""


class MatchedGpuPairProofTests(unittest.TestCase):
    def test_current_experiment_only_allows_backup_review(self):
        v = m.parse(evidence())
        self.assertEqual(v["decision"], "CURRENT_FAILURE_PAIR_CONFIRMED_BACKUP_REVIEW_ONLY")
        self.assertTrue(v["safe_to_plan_candidate_review"])
        self.assertFalse(v["flash_approved"])
        self.assertFalse(v["rollback_proven_on_device"])

    def test_matched_r15_source_does_not_claim_working_android(self):
        v = m.parse(evidence(
            boot="ORIGINAL_R15P0_REFERENCE", mali="PINNED_DONOR_R15P0",
            r7="0"*64, r15=m.R15_SHA))
        self.assertEqual(v["decision"], "R15P0_DONOR_PAIR_FINGERPRINTS_MATCH_BOOT_UNVERIFIED")
        self.assertFalse(v["flash_approved"])
        self.assertFalse(v["physical_egl_swap_verified"])

    def test_mixed_pair_is_not_safe_to_flash(self):
        v = m.parse(evidence(mali="BLOCKED_UK5_BASE"))
        self.assertEqual(v["decision"], "UNKNOWN_OR_MIXED_GPU_PAIR_DO_NOT_CHANGE")
        self.assertFalse(v["safe_to_plan_candidate_review"])

    def test_unmounted_system_only_requests_readonly_visibility(self):
        v = m.parse(evidence(mali="NOT_VISIBLE_MOUNT_SYSTEM_READ_ONLY"))
        self.assertEqual(v["decision"], "INCOMPLETE_READ_ONLY_SYSTEM_MOUNT_NEEDED")
        self.assertFalse(v["flash_approved"])

    def test_mismatched_sha_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "contradicts SHA"):
            m.parse(evidence(r7="0"*64))
        with self.assertRaisesRegex(ValueError, "Mali reported SHA"):
            m.parse(evidence(mali_sha="1"*64))

    def test_mutated_guard_or_duplicates_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "no-flash guard"):
            m.parse(evidence().replace("flash_approved=NO", "flash_approved=YES"))
        with self.assertRaisesRegex(ValueError, "Duplicated field"):
            m.parse(evidence() + "mali_sha256=000\n")

    def test_unrecognized_device_rejected(self):
        with self.assertRaisesRegex(ValueError, "no-flash guard"):
            m.parse(evidence().replace("device=v1awifi", "device=other"))


if __name__ == "__main__":
    unittest.main()
