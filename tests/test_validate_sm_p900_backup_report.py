import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validated_twrp_backup", ROOT / "scripts/validate_sm_p900_backup_report.py"
)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def fake_report():
    return "\n".join([
        m.HEADER, "device=v1awifi", "bootloader_family=P900",
        "boot_source_image_sha256=" + m.CURRENT_BOOT_SHA,
        "boot_partition_backup_bytes=8388608",
        "boot_partition_backup_sha256=" + ("1" * 64),
        "boot_partition_backup_image_prefix_sha256=" + m.CURRENT_BOOT_SHA,
        "mali_source_path=/system/vendor/lib/egl/libGLES_mali.so",
        "mali_source_real_path=/system/vendor/lib/egl/libGLES_mali.so",
        "mali_backup_sha256=" + m.CURRENT_MALI_SHA,
        "backup_image=BOOT.full-8MiB.backup",
        "backup_mali=libGLES_mali.UK10.original.backup",
        "backup_verified=YES", "rollback_tested_on_device=NO",
        "boot_partition_modified=NO", "system_partition_modified=NO",
        "data_partition_modified=NO", "flash_approved=NO",
        "",
    ])


class ValidateBackupReportTests(unittest.TestCase):
    def test_good_report_does_not_certify_rollback(self):
        report = m.parse(fake_report())
        self.assertTrue(report["backup_report_contains_hashes"])
        self.assertFalse(report["backups_independently_rehashed_off_device"])
        self.assertFalse(report["rollback_tested_on_physical_device"])
        self.assertFalse(report["install_approved"])

    def test_unexpected_boot_source_fails(self):
        with self.assertRaisesRegex(ValueError, "boot_source_image_sha256"):
            m.parse(fake_report().replace(m.CURRENT_BOOT_SHA, "0" * 64))

    def test_false_rollback_claim_fails(self):
        with self.assertRaisesRegex(ValueError, "rollback_tested_on_device"):
            m.parse(fake_report().replace("rollback_tested_on_device=NO",
                                          "rollback_tested_on_device=YES"))

    def test_weak_or_incomplete_backup_marker_fails(self):
        with self.assertRaisesRegex(ValueError, "backup_verified"):
            m.parse(fake_report().replace("backup_verified=YES", "backup_verified=NO"))

    def test_duplicate_report_fields_fail(self):
        with self.assertRaisesRegex(ValueError, "Duplicated"):
            m.parse(fake_report() + "flash_approved=YES\n")

    def test_traversing_mali_source_fails(self):
        with self.assertRaisesRegex(ValueError, "Invalid Mali source"):
            m.parse(fake_report().replace(
                "mali_source_real_path=/system/vendor/lib/egl/libGLES_mali.so",
                "mali_source_real_path=/system/../../cache/other.so"))


if __name__ == "__main__":
    unittest.main()
