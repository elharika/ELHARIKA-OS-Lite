import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

p = Path(__file__).resolve().parents[1] / "scripts/inspect_sm_p900_donor_ota.py"
spec = importlib.util.spec_from_file_location("donor_ota_metadata", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def package(path, wrong_magic=False, device="v1awifi"):
    path = Path(path) / ("e-2.3-r-20260227-UNOFFICIAL-" + device + ".zip")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("boot.img", (b"INVALID!" if wrong_magic else b"ANDROID!") + b"\0"*1_100_000)
        z.writestr("system.transfer.list", "4\n1\n0\n0\n")
        z.writestr("system.new.dat.br", b"\0"*512)
    return path


class DonorArchiveTests(unittest.TestCase):
    def test_compatible_archive_metadata_is_not_flash_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            result = m.inspect(package(temp))
            self.assertTrue(result["boot_image"]["android_magic"])
            self.assertEqual(len(result["system_payload"]), 2)
            self.assertFalse(result["flash_approved"])
            self.assertTrue(result["must_not_mix_with_existing_r7p0_trial"])
            self.assertFalse(result["can_compare_built_mali_elf_yet"])

    def test_other_device_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                m.inspect(package(temp, device="v2awifi"))

    def test_invalid_boot_magic_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                m.inspect(package(temp, wrong_magic=True))

    def test_no_system_payload_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "e-2.3-r-20260227-UNOFFICIAL-v1awifi.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("boot.img", b"ANDROID!" + b"\0"*1_100_000)
            with self.assertRaises(ValueError):
                m.inspect(archive)


if __name__ == "__main__":
    unittest.main()
