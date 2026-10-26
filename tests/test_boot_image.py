import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("bootcheck", Path(__file__).resolve().parents[1]/"scripts/verify_boot_image.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class BootImageTests(unittest.TestCase):
    def test_layout_and_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kernel, ramdisk, image = [root/n for n in ("kernel", "ramdisk.img", "boot.img")]
            kernel.write_bytes(b"kernel")
            ramdisk.write_bytes(b"ramdisk")
            header = b"ANDROID!" + struct.pack("<10I", 6, 0x10008000, 7, 0x11000000, 0, 0, 0x10000100, 2048, 0, 0)
            valid = header.ljust(2048, b"\0") + b"kernel".ljust(2048, b"\0") + b"ramdisk".ljust(2048, b"\0") + b"SEANDROIDENFORCE"
            image.write_bytes(valid)
            self.assertFalse(module.verify(image, kernel, ramdisk)["flash_approved"])
            for corrupt in (valid[:-1], b"BADMAGIC"+valid[8:], valid[:2048]+b"X"+valid[2049:], valid+b"extra"):
                image.write_bytes(corrupt)
                with self.assertRaises(ValueError):
                    module.verify(image, kernel, ramdisk)
            image.write_bytes(valid)
            kernel.write_bytes(b"other")
            with self.assertRaises(ValueError):
                module.verify(image, kernel, ramdisk)
