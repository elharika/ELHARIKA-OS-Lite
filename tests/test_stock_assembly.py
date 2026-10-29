from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from assemble_vendor_tree import relocate_trustlets,add_aeabi_compat_dependency

class AssemblyFixupTests(unittest.TestCase):
    def test_equal_length_exact_path_only(self):
        original=b'ELF\0/system/app/mcRegistry\0unchanged'
        patched=relocate_trustlets(original)
        self.assertEqual(len(original),len(patched))
        self.assertEqual(patched,b'ELF\0/vendor/app/mcRegistry\0unchanged')
    def test_missing_repeated_or_already_patched_rejected(self):
        for data in (b'none',b'/system/app /system/app',b'/vendor/app',b'/system/app /vendor/app'):
            with self.assertRaises(ValueError):relocate_trustlets(data)
    def test_libstlport_rejects_unverified_bytes_without_patching(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'libstlport.so';path.write_bytes(b'not exact stock')
            with self.assertRaisesRegex(ValueError,'Unexpected SM-P900 libstlport bytes'):
                add_aeabi_compat_dependency(path)
            self.assertEqual(path.read_bytes(),b'not exact stock')

if __name__=='__main__':unittest.main()

