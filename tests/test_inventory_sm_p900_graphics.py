import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "scripts/inventory_sm_p900_graphics.py"
spec = importlib.util.spec_from_file_location("graphics_inventory", path)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


class GraphicsInventoryTests(unittest.TestCase):
    def test_debugfs_directory_parse(self):
        listing = (
            "/12/040755/0/0/./0/\n"
            "/182/0100644/0/0/gralloc.exynos5.so/83920/\n"
            "/184/0100644/0/0/hwcomposer.exynos5.so/9000/\n"
            "/188/0100644/0/0/gralloc.default.so/12000/\n"
            "/191/0100644/0/0/unrelated.so/200/\n"
        )
        self.assertEqual(g.parse_entries(listing), [
            "gralloc.default.so", "gralloc.exynos5.so", "hwcomposer.exynos5.so"])

    def test_distinguish_default_from_board_specific_hal(self):
        data = [
            {"path": "/system/vendor/lib/hw/gralloc.default.so"},
            {"path": "/system/lib/hw/gralloc.exynos5.so"},
            {"path": "/system/lib/hw/hwcomposer.exynos5.so"},
            {"path": "/system/vendor/lib/egl/libGLES_mali.so"}
        ]
        result = g.summarize(data)
        self.assertTrue(result["presence"]["board_gralloc"])
        self.assertTrue(result["presence"]["board_hwcomposer"])
        self.assertTrue(result["presence"]["mali_egl"])
        self.assertFalse(result["flash_approved"])
        self.assertFalse(result["root_cause_proven"])

    def test_gralloc_default_is_not_proof_of_board_hal(self):
        result = g.summarize([
            {"path": "/system/vendor/lib/hw/gralloc.default.so"}])
        self.assertFalse(result["presence"]["board_gralloc"])
        self.assertFalse(result["presence"]["board_hwcomposer"])

    def test_readonly_path_guard(self):
        with self.assertRaises(ValueError):
            g.inspect_module(Path("/nonexistent.ext4"), "/system/bin/sh", Path("/tmp"))


if __name__ == "__main__":
    unittest.main()
