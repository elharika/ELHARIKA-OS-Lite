import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from patch_mali_compat import (
    MALI_MODULE,
    MALI_NEEDED,
    MALI_REQUIRED_SYMBOLS,
    MALI_SHA256,
    patch_android_bp_text,
)


class MaliCompatTests(unittest.TestCase):
    def test_exact_stock_blob_and_observed_imports_are_pinned(self):
        self.assertEqual(
            MALI_SHA256,
            '6bdde99d255444cf59374558736c85de5413125f63f4035237d6556c0f91047d',
        )
        self.assertEqual(MALI_NEEDED, 'libelharika_mali_compat.so')
        self.assertEqual(MALI_MODULE, 'libelharika_mali_compat')
        self.assertEqual(
            MALI_REQUIRED_SYMBOLS,
            {
                '__aeabi_d2lz', '__aeabi_d2ulz', '__aeabi_f2lz', '__aeabi_f2ulz',
                '__aeabi_idiv', '__aeabi_l2d', '__aeabi_l2f', '__aeabi_ldivmod',
                '__aeabi_llsr', '__aeabi_uidiv', '__aeabi_uidivmod', '__aeabi_ul2d',
                '__aeabi_ul2f', '__aeabi_uldivmod', '__popcount_tab', '__popcountsi2',
                'get_process_name',
            },
        )

    def test_generated_rule_patch_keeps_elf_validation_enabled(self):
        original = '''// generated\ncc_prebuilt_library_shared {\n    name: "libGLES_mali",\n    owner: "samsung",\n    srcs: ["proprietary/vendor/lib/egl/libGLES_mali.so"],\n    compile_multilib: "32",\n    strip: { none: true },\n    check_elf_files: true,\n    shared_libs: ["libc", "libcutils"],\n    vendor: true,\n    relative_install_path: "egl",\n}\n'''
        patched = patch_android_bp_text(original)
        self.assertIn('"libelharika_mali_compat"', patched)
        self.assertIn('whole_static_libs: ["libclang_rt.builtins-arm-android"]', patched)
        self.assertIn('check_elf_files: true', patched)
        self.assertNotIn('check_elf_files: false', patched)
        self.assertNotIn('allow_undefined_symbols: true', patched)

    def test_compat_source_exports_removed_legacy_interfaces(self):
        source = (ROOT / 'rom/compat/mali_legacy_compat.c').read_text()
        self.assertIn('const unsigned char __popcount_tab[256]', source)
        self.assertIn('const char* get_process_name(void)', source)
        self.assertIn('/proc/self/cmdline', source)


if __name__ == '__main__':
    unittest.main()
