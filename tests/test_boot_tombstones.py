import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('bootlogs', Path(__file__).resolve().parents[1]/'scripts/analyze_boot_tombstones.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

class BootLogTests(unittest.TestCase):
    def test_crashes_empty_files_and_links_are_distinguished(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory)/'logs.tgz'
            with tarfile.open(archive, 'w:gz') as out:
                for name, data in [('data/tombstones/tombstone_00', b"pid: 4 >>> /system/bin/surfaceflinger <<<\nAbort message: 'EGL failed'\n"),
                                   ('data/tombstones/tombstone_01', b''),
                                   ('../secret', b'NEVER_READ')]:
                    info = tarfile.TarInfo(name); info.size = len(data); out.addfile(info, io.BytesIO(data))
                link = tarfile.TarInfo('data/tombstones/tombstone_02'); link.type = tarfile.SYMTYPE
                link.linkname = '/etc/passwd'; out.addfile(link)
            r = mod.analyze(archive)
            self.assertEqual(r['nonempty_tombstones'], 1)
            self.assertEqual(r['empty_tombstones'], 1)
            self.assertEqual(r['crash_groups'][0]['process'], '/system/bin/surfaceflinger')
            self.assertFalse(r['hardware_approved'])

    def test_size_budget_rejects_header_before_reading_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory)/'large.tgz'
            with tarfile.open(archive, 'w:gz') as out:
                info = tarfile.TarInfo('data/tombstones/tombstone_00')
                data = bytes(mod.MAX_FILE + 1); info.size = len(data)
                out.addfile(info, io.BytesIO(data))
            with self.assertRaisesRegex(ValueError, 'Oversized'):
                mod.analyze(archive)

if __name__ == '__main__': unittest.main()
