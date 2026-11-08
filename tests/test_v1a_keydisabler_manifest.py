"""Offline tests of the pinned SM-P900 VINTF boot-stall workaround."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fix_v1a_keydisabler_manifest as patch

# Real, pinned 848-byte upstream file (git blob 2d09473dbce87ff3ef979b5709bb4b72e901abee).
PINNED_MANIFEST = b'''<manifest version="1.0" type="device">
    <hal format="hidl">
        <name>vendor.lineage.touch</name>
        <transport>hwbinder</transport>
        <version>1.0</version>
        <interface>
            <name>IKeyDisabler</name>
            <instance>default</instance>
        </interface>
        <interface>
            <name>ITouchscreenGesture</name>
            <instance>default</instance>
        </interface>
    </hal>
    <hal format="hidl">
        <name>vendor.lineage.livedisplay</name>
        <transport>hwbinder</transport>
        <version>2.0</version>
        <interface>
            <name>IDisplayModes</name>
            <instance>default</instance>
        </interface>
        <interface>
            <name>IReadingEnhancement</name>
            <instance>default</instance>
        </interface>
    </hal>
</manifest>
'''


class V1aKeyDisablerManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "manifest.xml"
        self.path.write_bytes(PINNED_MANIFEST)

    def test_upstream_file_matches_pinned_blob(self):
        self.assertEqual(len(PINNED_MANIFEST), 848)
        self.assertEqual(patch.digest(PINNED_MANIFEST), patch.BEFORE_SHA256)
        git_blob = b"blob " + str(len(PINNED_MANIFEST)).encode() + b"\0" + PINNED_MANIFEST
        self.assertEqual(hashlib.sha1(git_blob).hexdigest(),
                         "2d09473dbce87ff3ef979b5709bb4b72e901abee")

    def test_exact_pinned_patch_and_idempotence(self):
        with self.assertRaisesRegex(ValueError, "not patched"):
            patch.apply(self.root, check=True)
        self.assertEqual(self.path.read_bytes(), PINNED_MANIFEST)
        self.assertIn("applied", patch.apply(self.root))
        modified = self.path.read_bytes()
        self.assertEqual(patch.digest(modified), patch.AFTER_SHA256)
        self.assertIn("verified", patch.apply(self.root, check=True))
        self.assertIn("verified", patch.apply(self.root))
        self.assertEqual(self.path.read_bytes(), modified)
        self.assertNotIn(b"IKeyDisabler", modified)
        root = ET.fromstring(modified)
        touch = next(h for h in root.findall("hal")
                     if h.findtext("name") == "vendor.lineage.touch")
        self.assertEqual([i.findtext("name") for i in touch.findall("interface")],
                         ["ITouchscreenGesture"])
        livedisplay = next(h for h in root.findall("hal")
                           if h.findtext("name") == "vendor.lineage.livedisplay")
        self.assertEqual([i.findtext("name") for i in livedisplay.findall("interface")],
                         ["IDisplayModes", "IReadingEnhancement"])
        self.assertEqual(modified, PINNED_MANIFEST.replace(patch.BLOCK, b"", 1))

    def test_unexpected_content_does_not_write(self):
        altered = PINNED_MANIFEST + b"<!-- local change -->\n"
        self.path.write_bytes(altered)
        with self.assertRaisesRegex(ValueError, "Unexpected"):
            patch.apply(self.root)
        self.assertEqual(self.path.read_bytes(), altered)

    def test_symlink_not_modified(self):
        outside = self.root / "original.xml"
        outside.write_bytes(PINNED_MANIFEST)
        self.path.unlink()
        self.path.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "unsafe"):
            patch.apply(self.root)
        self.assertEqual(outside.read_bytes(), PINNED_MANIFEST)

    def test_absent_manifest_fails(self):
        self.path.unlink()
        with self.assertRaisesRegex(ValueError, "Missing"):
            patch.apply(self.root)


if __name__ == "__main__":
    unittest.main()
