import importlib.util
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pack', ROOT/'scripts/package_experimental.py')
pack = importlib.util.module_from_spec(spec); spec.loader.exec_module(pack)

class PackagingTests(unittest.TestCase):
    def test_capacity_boundaries_and_reported_device_size(self):
        # Exercise the actual installer helper. Integers never reach sh/test.
        template = (ROOT/'installer/update-binary.in').read_text()
        helper = template.split('system_capacity_ok() {', 1)[1].split('\n}', 1)[0]
        script = 'system_capacity_ok() {'+helper+'\n}\nsystem_capacity_ok "$1" "$2"\n'
        for actual, required, succeeds in [
            ('2491416576', '2299998208', True),
            ('2299998208', '2299998208', True),
            ('2299998207', '2299998208', False),
            ('2147483647', '2299998208', False),
            ('4294967296', '2299998208', True),
            ('4294967297', '2299998208', False),
            ('', '2299998208', False), ('bad', '2299998208', False),
            ('2.491416576e9', '2299998208', False),
            ('99999999999999999999', '2299998208', False),
            ('2491416576', '0', False), ('2491416576', '-1', False),
        ]:
            with self.subTest(actual=actual, required=required):
                result = subprocess.run(['/bin/sh', '-s', '--', actual, required],
                                        input=script, text=True, capture_output=True)
                self.assertEqual(result.returncode == 0, succeeds, result.stderr)

    def test_sparse_content_and_holes(self):
        with tempfile.TemporaryDirectory() as temp:
            src = Path(temp)/'s'; dst = Path(temp)/'r'
            bs = 4096
            body = (struct.pack('<2H2I', 0xcac1, 0, 1, 12+bs)+b'R'*bs+
                    struct.pack('<2H2I', 0xcac2, 0, 1, 16)+b'abcd'+
                    struct.pack('<2H2I', 0xcac3, 0, 1, 12))
            header = struct.pack('<I4H4I', 0xed26ff3a, 1, 0, 28, 12, bs, 3, 3, 0)
            src.write_bytes(header+body)
            original = pack.EXPANDED
            try:
                pack.EXPANDED = 3*bs
                pack.expand(src, dst)
                self.assertEqual(dst.read_bytes(), b'R'*bs+b'abcd'*(bs//4)+bytes(bs))
                src.write_bytes(header+body[:-1])
                with self.assertRaises(ValueError): pack.expand(src, dst)
            finally: pack.EXPANDED = original

    def test_mismatched_input_refused_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp); (d/'system.img').write_bytes(b'bad'); (d/'boot.img').write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError, 'hashes'):
                pack.package(d, d, d, d, d/'output')
            self.assertFalse((d/'output').exists())

    def test_foreign_device_and_unverified_bootloader_cannot_write(self):
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp); prop = d/'getprop'
            prop.write_text('#!/bin/sh\ncase "$1" in ro.product.device) echo "$DEVICE";; ro.bootloader) echo "$BOOTLOADER";; esac\n')
            prop.chmod(0o755)
            for tool in ('blockdev','dd'):
                fake = d/tool
                fake.write_text('#!/bin/sh\necho invoked >> "$MARKER"\nexit 1\n'); fake.chmod(0o755)
            script = d/'installer.sh'
            script.write_text((ROOT/'installer/update-binary.in').read_text())
            marker = d/'marker'
            for device, bootloader, expected in [('v1a3g','P901XX','Only v1awifi'),
                                                 ('v1awifi','P905XX','bootloader identity')]:
                with (d/'ui').open('w') as log:
                    env = dict(os.environ, PATH=str(d)+':'+os.environ['PATH'], DEVICE=device,
                               BOOTLOADER=bootloader, MARKER=str(marker))
                    result = subprocess.run(['/bin/sh', str(script), '3', str(log.fileno()), '/external_sd/test.zip'],
                                            pass_fds=(log.fileno(),), env=env, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, (d/'ui').read_text())
                self.assertFalse(marker.exists(), 'No block operation allowed before identity verification')

if __name__ == '__main__': unittest.main()
