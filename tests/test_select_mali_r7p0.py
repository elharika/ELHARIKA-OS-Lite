import importlib.util
from pathlib import Path
import unittest

script = Path(__file__).resolve().parents[1] / 'scripts/select_mali_r7p0.py'
spec = importlib.util.spec_from_file_location('sel_mali', script)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class SelectMaliTests(unittest.TestCase):
    def test_switch_and_idempotency(self):
        old = 'CONFIG_MALI_T6XX=y\n# CONFIG_MALI_T6XX_R7P0 is not set\nCONFIG_MALI_T6XX_R15P0=y\n'
        after, changed = mod.patch_defconfig(old)
        self.assertTrue(changed)
        self.assertIn('CONFIG_MALI_T6XX_R7P0=y', after)
        self.assertNotIn('CONFIG_MALI_T6XX_R15P0=y', after)
        again, changed = mod.patch_defconfig(after)
        self.assertEqual(again, after)
        self.assertFalse(changed)

    def test_unknown_kernel_config_is_rejected(self):
        for config in ('CONFIG_MALI_T6XX_R7P0=y\nCONFIG_MALI_T6XX_R15P0=y\n',
                       'CONFIG_MALI_T6XX=y\nCONFIG_MALI_T6XX_R15P0=y\n',
                       'CONFIG_MALI_T6XX=y\n# CONFIG_MALI_T6XX_R7P0 is not set\n'):
            with self.subTest(config=config), self.assertRaises(ValueError):
                mod.patch_defconfig(config)

if __name__ == '__main__':
    unittest.main()
