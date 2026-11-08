import importlib.util
from pathlib import Path
import unittest

file = Path(__file__).resolve().parents[1] / "scripts/audit_sm_p900_donor_graphics_pair.py"
spec = importlib.util.spec_from_file_location("same_device_donor", file)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

GPU = """CONFIG_MALI_T6XX=y
# CONFIG_MALI_T6XX_R7P0 is not set
CONFIG_MALI_T6XX_R15P0=y
CONFIG_ION_EXYNOS=y
"""
PROPS = """debug.hwc.winupdate=0
ro.surface_flinger.running_without_sync_framework = true
ro.surface_flinger.max_frame_buffer_acquired_buffers = 3
"""
TOUCH = """<manifest><hal><name>vendor.lineage.touch</name>
<interface><name>IKeyDisabler</name></interface>
<interface><name>ITouchscreenGesture</name></interface>
</hal></manifest>"""


class SameDeviceDonorSafety(unittest.TestCase):
    def test_source_reference_is_not_flash_authorization(self):
        data = m.audit(GPU, GPU, PROPS, PROPS, TOUCH,
                       m.DONOR_VENDOR_MALI_GIT_BLOB_SHA1)
        self.assertEqual(data["donor_defconfig_gpu"], "CONFIG_MALI_T6XX_R15P0=y")
        self.assertEqual(data["last_physically_tested_ELHARIKA_boot_gpu"],
                         "CONFIG_MALI_T6XX_R7P0=y")
        self.assertTrue(data["donor_and_previous_graphics_properties_identical"])
        self.assertTrue(data["donor_declares_missing_IKeyDisabler"])
        self.assertFalse(data["flash_approved"])
        self.assertFalse(data["Mali_eglSwapBuffers_working_on_user_device"])

    def test_donor_kernel_changed_to_r7p0_is_rejected(self):
        incorrect = GPU.replace("# CONFIG_MALI_T6XX_R7P0 is not set",
                                "CONFIG_MALI_T6XX_R7P0=y")
        with self.assertRaisesRegex(ValueError, "conflicting Mali"):
            m.audit(incorrect, GPU, PROPS, PROPS, TOUCH,
                    m.DONOR_VENDOR_MALI_GIT_BLOB_SHA1)

    def test_unreviewed_binary_blob_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "not the reviewed"):
            m.audit(GPU, GPU, PROPS, PROPS, TOUCH, "a"*40)

    def test_old_missing_touch_hal_is_not_a_boot_fix(self):
        no_decl = TOUCH.replace("<name>IKeyDisabler</name>", "")
        with self.assertRaisesRegex(ValueError, "unexpectedly different"):
            m.audit(GPU, GPU, PROPS, PROPS, no_decl,
                    m.DONOR_VENDOR_MALI_GIT_BLOB_SHA1)

    def test_modified_properties_report_difference_not_compatibility(self):
        data = m.audit(GPU, GPU, PROPS+"extra=value\n", PROPS, TOUCH,
                       m.DONOR_VENDOR_MALI_GIT_BLOB_SHA1)
        self.assertFalse(data["donor_and_previous_graphics_properties_identical"])
        self.assertFalse(data["flash_approved"])


if __name__ == "__main__":
    unittest.main()
