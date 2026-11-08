import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).resolve().parents[1] / "scripts/audit_pinned_exynos5_gralloc_contract.py"
spec = importlib.util.spec_from_file_location("exynos5_gralloc_contract", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def synthetic():
    return {name: "\n".join(parts) for name, parts in m.EXPECTED.items()}


class Exynos5GrallocSourceTests(unittest.TestCase):
    def test_source_default_off_is_not_runtime_property_proof(self):
        s = m.audit(synthetic())
        self.assertTrue(s["compiled_with_afbc_support"])
        self.assertFalse(s["afbc_enabled_by_default_in_source"])
        self.assertFalse(s["runtime_afbc_property_verified"])
        self.assertFalse(s["native_handle_binary_layout_proven_compatible_with_mali"])
        self.assertFalse(s["safe_to_flash"])

    def test_missing_afbc_property_guard_rejected(self):
        parts = synthetic()
        parts["format_chooser"] = parts["format_chooser"].replace("if(afbc_prop == 0)", "if(afbc_prop == 1)")
        with self.assertRaisesRegex(ValueError, "Pinned source changed"):
            m.audit(parts)

    def test_missing_ion_field_rejected(self):
        parts = synthetic()
        parts["handle_header"] = parts["handle_header"].replace("PRIV_FLAGS_USES_ION", "PRIV_FLAGS_USES_OTHER")
        with self.assertRaisesRegex(ValueError, "Pinned source changed"):
            m.audit(parts)


if __name__ == "__main__":
    unittest.main()
