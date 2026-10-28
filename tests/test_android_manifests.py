import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANDROID = "{http://schemas.android.com/apk/res/android}"

class AndroidManifestTests(unittest.TestCase):
    def test_aapt2_package_and_activity_match_source(self):
        for module, package in (("launcher", "org.elharika.launcher"),
                                ("pen", "org.elharika.pen")):
            with self.subTest(module=module):
                source = ROOT / "apps" / module / "src/main"
                manifest = ET.parse(source / "AndroidManifest.xml").getroot()
                self.assertEqual(manifest.tag, "manifest")
                self.assertEqual(manifest.get("package"), package)
                activity = manifest.find("./application/activity")
                self.assertEqual(activity.get(ANDROID + "name"), ".MainActivity")
                java = source / "java" / Path(*package.split(".")) / "MainActivity.java"
                self.assertIn("package " + package + ";", java.read_text())
