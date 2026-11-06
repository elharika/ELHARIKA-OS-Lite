import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).resolve().parents[1] / 'scripts/fix_r7p0_kbuild.py'
spec = importlib.util.spec_from_file_location('fix_r7p0_kbuild', p)
fixer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixer)


class KbuildRepairTests(unittest.TestCase):
    def test_missing_symbols_would_exclude_core_and_platform(self):
        old = ('ifeq ($(CONFIG_MALI_R7P0),m)\n'
               'else ifeq ($(CONFIG_MALI_R7P0),y)\n'
               'obj-$(CONFIG_MALI_R7P0) += mali_kbase.o\n')
        new, changed = fixer.patch_main(old)
        self.assertTrue(changed)
        self.assertEqual(new.count('CONFIG_MALI_T6XX_R7P0'), 3)
        self.assertNotIn('CONFIG_MALI_R7P0', new)
        same, second = fixer.patch_main(new)
        self.assertEqual(new, same)
        self.assertFalse(second)

    def test_platform_source_uses_exynos5420_not_unset_platform_name(self):
        src = ('obj-y += mali_kbase_platform.o\n'
               'obj-y += gpu_exynos$(platform_name).o\n')
        new, changed = fixer.patch_platform(src)
        self.assertTrue(changed)
        self.assertIn('obj-y += gpu_exynos5420.o', new)
        self.assertFalse(fixer.patch_platform(new)[1])

    def test_fail_closed_on_unknown_or_partial_rules(self):
        for text in ('obj-$(CONFIG_MALI_R7P0) += mali_kbase.o\n',
                     'obj-$(CONFIG_MALI_T6XX_R7P0) += mali_kbase.o\n',
                     'obj-$(CONFIG_MALI_R7P0) += mali_kbase.o\nobj-$(CONFIG_MALI_T6XX_R7P0) += mali_kbase.o\n'):
            with self.assertRaises(ValueError):
                fixer.patch_main(text)
        with self.assertRaises(ValueError):
            fixer.patch_platform('obj-y += gpu_exynos$(platform_name).o\n')


if __name__ == '__main__':
    unittest.main()
