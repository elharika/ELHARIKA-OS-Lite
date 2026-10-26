from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fix_graphics_policy as gfx

class GraphicsPolicyTests(unittest.TestCase):
    def test_relabel_and_reject_changed_input(self):
        original = gfx.RULES
        try:
            with tempfile.TemporaryDirectory() as temp:
                directory = Path(temp) / "sepolicy/vendor"
                directory.mkdir(parents=True)
                sources = {}
                for name, (_, before, after) in original.items():
                    sources[name] = ("# hal_graphics_composer_default.te\n\n" if name.endswith(".te") else "# file_contexts\n") + before + "\n"
                    (directory / name).write_text(sources[name])
                gfx.RULES = {name: (gfx.blob_sha(text.encode()), before, after)
                             for name, text in sources.items()
                             for _, before, after in [original[name]]}
                self.assertEqual(gfx.apply(temp), 2)
                self.assertEqual(gfx.apply(temp), 0)
                self.assertIn("video_device:s0", (directory / "file_contexts").read_text())
                self.assertNotIn("audio_device:chr_file", (directory / "hal_graphics_composer_default.te").read_text())
                (directory / "file_contexts").write_text("tampered")
                with self.assertRaises(ValueError): gfx.apply(temp)
        finally:
            gfx.RULES = original
