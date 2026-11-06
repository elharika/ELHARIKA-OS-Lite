import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / "scripts/fix_blocking_optional_touch_hal.py"
spec = importlib.util.spec_from_file_location("touch_mitigation", path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

JAVA = """case FEATURE_KEY_DISABLE:
                    return IKeyDisabler.getService(true);
                case FEATURE_TOUCHSCREEN_GESTURES:
                    return ITouchscreenGesture.getService(true);
"""
MANIFEST = """<manifest>
  <hal><name>vendor.lineage.touch</name>
        <interface>
            <name>IKeyDisabler</name>
            <instance>default</instance>
        </interface>
        <interface>
            <name>ITouchscreenGesture</name>
            <instance>default</instance>
        </interface>
  </hal>
</manifest>
"""


class TouchMitigationTest(unittest.TestCase):
    def test_sdk_request_is_disabled_without_disabling_gestures(self):
        after, changed = m.patch_java(JAVA)
        self.assertTrue(changed)
        self.assertIn(m.NEW_CALL, after)
        self.assertIn("ITouchscreenGesture.getService(true)", after)
        self.assertNotIn(m.OLD_CALL, after)
        self.assertEqual(m.patch_java(after), (after, False))

    def test_manifest_removes_only_unregistered_interface(self):
        after, changed = m.patch_manifest(MANIFEST)
        self.assertTrue(changed)
        self.assertNotIn("IKeyDisabler", after)
        self.assertIn(m.GESTURE_INTERFACE, after)
        self.assertEqual(m.patch_manifest(after), (after, False))

    def test_refuses_unknown_and_incomplete_sources(self):
        with self.assertRaises(ValueError):
            m.patch_java(JAVA.replace("getService(true)", "getService(false)", 1))
        with self.assertRaises(ValueError):
            m.patch_manifest(MANIFEST.replace("ITouchscreenGesture", "FakeGesture"))

    def test_full_patch_requires_locked_revisions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            j = root / "lineage-sdk" / m.JAVA
            v = root / m.DEVICE_MANIFEST
            j.parent.mkdir(parents=True)
            v.parent.mkdir(parents=True)
            j.write_text(JAVA)
            v.write_text(MANIFEST)
            with patch.object(m.subprocess, "check_output", side_effect=[m.SDK_REVISION, m.DEVICE_REVISION]):
                result = m.apply(root)
            self.assertTrue(result["sdk_java_changed"])
            self.assertTrue(result["manifest_changed"])
            with patch.object(m.subprocess, "check_output", side_effect=[m.SDK_REVISION, "wrong_revision"]):
                with self.assertRaises(ValueError):
                    m.apply(root)
            self.assertIn(m.NEW_CALL, j.read_text())
            self.assertNotIn("IKeyDisabler", v.read_text())


if __name__ == "__main__":
    unittest.main()
