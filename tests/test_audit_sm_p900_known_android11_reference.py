import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

p = Path(__file__).resolve().parents[1] / "scripts/audit_sm_p900_known_android11_reference.py"
spec = importlib.util.spec_from_file_location("published_android11_reference", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

CONFIG = "CONFIG_MALI_T6XX_R15P0=y\n# CONFIG_MALI_T6XX_R7P0 is not set\n"
KBUILD = 'MALI_RELEASE_NAME ?= "r15p0-00rel0"\n'
BOARD = "BOARD_USES_EXYNOS5_COMMON_GRALLOC := true\n"
PROPS = ("ro.surface_flinger.running_without_sync_framework = true\n"
         "ro.surface_flinger.max_frame_buffer_acquired_buffers = 3\n")


class SourceReferenceTests(unittest.TestCase):
    def test_build_id_parser_accepts_only_one(self):
        self.assertEqual(m.build_id_of("Build ID: aB01ce\n"), "ab01ce")
        with self.assertRaises(ValueError):
            m.build_id_of("not a GNU build ID")

    def test_reference_pair_metadata_and_no_flash(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "libGLES_mali.so"
            file.write_bytes(b"\x7fELF\x01\x01" + b"\0" * 150_000)
            outputs = [
                "Machine: ARM\n",
                "Build ID: 1B2949CF031B30F20A970C511925875D\n",
                "0x00000001 (NEEDED) Shared library: [libc.so]\n",
                "Version symbols section .gnu.version contains 0 entries\n",
            ]
            with patch.object(m.subprocess, "run", side_effect=[
                subprocess.CompletedProcess(args="readelf", returncode=0, stdout=value, stderr="")
                for value in outputs
            ]):
                result = m.examine(CONFIG, KBUILD, BOARD, PROPS, file)
            self.assertTrue(result["same_build_id_as_crashing_uk10"])
            self.assertEqual(result["reference_kernel"], "MALI_R15P0")
            self.assertFalse(result["safe_to_flash"])

    def test_refuse_mixed_kernel_generation(self):
        with self.assertRaisesRegex(ValueError, "not R15P0"):
            m.examine("CONFIG_MALI_T6XX_R7P0=y\n", KBUILD, BOARD, PROPS, Path("/missing"))
        with self.assertRaisesRegex(ValueError, "accidentally selects R7P0"):
            m.examine(CONFIG.replace("# CONFIG_MALI_T6XX_R7P0 is not set",
                                     "CONFIG_MALI_T6XX_R7P0=y"),
                      KBUILD, BOARD, PROPS, Path("/missing"))

    def test_refuse_missing_board_gralloc(self):
        with self.assertRaisesRegex(ValueError, "gralloc selection"):
            m.examine(CONFIG, KBUILD, "BOARD_USES_EXYNOS5_COMMON_GRALLOC := false",
                      PROPS, Path("/missing"))


if __name__ == "__main__":
    unittest.main()
