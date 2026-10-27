import tempfile
import unittest
from pathlib import Path
from scripts.fix_camera_hosting import OLD, NEW, transform, apply

class CameraHostingTests(unittest.TestCase):
    def test_changes_only_host_selection(self):
        original = "# Camera\n" + OLD + "\n# Other settings\n"
        changed = transform(original)
        self.assertEqual(changed, "# Camera\n" + NEW + "\n# Other settings\n")
        self.assertEqual(transform(changed), changed)

    def test_reject_ambiguous_configuration(self):
        for text in ("", OLD + "\n" + OLD, OLD + "\n" + NEW, OLD.replace("true", "maybe")):
            with self.assertRaises(ValueError):
                transform(text)

    def test_reject_unknown_provider_before_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            provider = root / "hardware/camera/provider/CameraProvider.cpp"
            provider.parent.mkdir(parents=True)
            provider.write_text("unreviewed provider")
            board = root / "BoardConfigCommon.mk"
            board.write_text(OLD)
            with self.assertRaises(ValueError):
                apply(root)
            self.assertEqual(board.read_text(), OLD)
