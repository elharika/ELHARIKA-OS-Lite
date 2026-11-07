import importlib.util
from pathlib import Path
import unittest

script = Path(__file__).resolve().parents[1] / "scripts/audit_system_image_offline.py"
spec = importlib.util.spec_from_file_location("offline_graphics", script)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

BASE = """<manifest version="1.0" type="device">
<hal format="hidl"><name>vendor.lineage.touch</name>
<interface><name>ITouchscreenGesture</name><instance>default</instance></interface>
</hal>
</manifest>"""


class OfflineGraphicsTest(unittest.TestCase):
    def test_manifest_keeps_only_real_touch_hal(self):
        self.assertEqual(m.validate_manifest(BASE), ["ITouchscreenGesture"])

    def test_reject_advertised_missing_service(self):
        text = BASE.replace("</hal>", "<interface><name>IKeyDisabler</name><instance>default</instance></interface></hal>")
        with self.assertRaises(ValueError):
            m.validate_manifest(text)

    def test_reject_missing_gesture_service(self):
        with self.assertRaises(ValueError):
            m.validate_manifest(BASE.replace("ITouchscreenGesture", "IKeyDisabler"))

    def test_reject_duplicate_touch_hal(self):
        with self.assertRaises(ValueError):
            m.validate_manifest(BASE.replace("</manifest>", '<hal><name>vendor.lineage.touch</name></hal></manifest>'))

    def test_reject_unreviewed_blob_paths(self):
        with self.assertRaises(ValueError):
            m.dump_binary(Path("/not-mounted"), "/system/bin/sh", Path("/tmp/test-binary"))


if __name__ == "__main__":
    unittest.main()
