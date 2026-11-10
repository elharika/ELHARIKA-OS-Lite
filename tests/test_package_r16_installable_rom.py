import contextlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'tests'))
import audit_r15_wacom_boot_pair_readonly as auditor
from test_stage_r15_wacom_boot_candidate import original_boot, kernel
from stage_r15_wacom_boot_candidate import repack
spec=importlib.util.spec_from_file_location('r16package',ROOT/'scripts/package_r16_installable_rom.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class R16PackagingTests(unittest.TestCase):
    def fixture(self,root):
        old=original_boot();k=kernel(version='de0cdcf1-dirty')
        with patch.object(auditor,'ORIGINAL_SHA',m.digest(old)):
            new,_=repack(old,k,m.digest(k))
        source=root/'source.zip';staging=root/'stage.zip';system=b'fixture-system-payload'
        manifest={'full_raw_system_sha256':m.digest(system),'donor_r15_mali_sha256':'a00166d28cbd0213c88daadb437534310de09da4bf9fcc64f8e2207e22d76839'}
        with ZipFile(source,'w') as z:
            for name,data in [('META-INF/com/google/android/update-binary',b'old installer'),('META-INF/com/google/android/updater-script',b'#'),('system.ext4',system),('boot.img',old),('README.txt',b'old notes'),('verification.json',json.dumps(manifest).encode())]:
                z.writestr(name,data)
        with ZipFile(staging,'w') as z:
            z.writestr('BOOT-CANDIDATE-NOT-DEVICE-TESTED.img',new)
            z.writestr('ORIGINAL-R15P0-BOOT.img',old)
        return source,staging,old,new,k,system

    @contextlib.contextmanager
    def pins(self,source,old,new,k,system):
        values={'SOURCE_ZIP_SHA':m.file_sha(source),'SYSTEM_SHA':m.digest(system),'SYSTEM_BYTES':len(system),'OLD_BOOT_SHA':m.digest(old),'NEW_BOOT_SHA':m.digest(new),'KERNEL_SHA':m.digest(k)}
        with contextlib.ExitStack() as stack:
            for name,value in values.items():stack.enter_context(patch.object(m,name,value))
            stack.enter_context(patch.object(auditor,'ORIGINAL_SHA',m.digest(old)))
            yield

    def test_full_rom_and_restore_preserve_exact_payloads_and_write_scope(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);source,staging,old,new,k,system=self.fixture(root)
            before=m.file_sha(source)
            with self.pins(source,old,new,k,system):
                results=m.package(source,staging,root/'out')
                with self.assertRaisesRegex(ValueError,'already exist'):
                    m.package(source,staging,root/'out')
            self.assertEqual(before,m.file_sha(source))
            self.assertEqual(len(results),2)
            with ZipFile(root/'out'/m.ROM_NAME) as z:
                self.assertEqual(z.read('system.ext4'),system)
                self.assertEqual(z.read('boot.img'),new)
                installer=z.read('META-INF/com/google/android/update-binary').decode()
                self.assertLess(installer.index('sha256sum -c SHA256SUMS'),installer.index('dd if="$WORK/system.ext4"'))
                self.assertLess(installer.index('BOOT backup verification failed'),installer.index('dd if="$WORK/system.ext4"'))
                self.assertIn('[ "$PWR" -ge 50 ]',installer)
                self.assertIn('SYSTEM capacity incompatible',installer)
                self.assertNotIn('of="$DATA"',installer)
                self.assertEqual((z.getinfo('META-INF/com/google/android/update-binary').external_attr>>16)&0o777,0o755)
                self.assertTrue(all(i.extract_version<=20 for i in z.infolist()))
                self.assertFalse(json.loads(z.read('verification.json'))['stable_release'])
            with ZipFile(root/'out'/m.RESTORE_NAME) as z:
                self.assertEqual(z.read('boot.img'),old)
                restore=z.read('META-INF/com/google/android/update-binary').decode()
                self.assertNotIn('of="$SYSTEM"',restore)
                self.assertIn('[ "$CURRENT" =',restore)
                self.assertLess(restore.index('Wrong payload SHA256'),restore.index('dd if="$WORK/boot.img"'))

    def test_unknown_source_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);source,staging,old,new,k,system=self.fixture(root)
            with self.assertRaisesRegex(ValueError,'source full-ROM ZIP hash'):
                m.package(source,staging,root/'out')
            self.assertFalse((root/'out').exists())

    def test_corrupt_staging_boot_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);source,staging,old,new,k,system=self.fixture(root)
            with ZipFile(staging,'w') as z:
                z.writestr('BOOT-CANDIDATE-NOT-DEVICE-TESTED.img',new+b'bad')
                z.writestr('ORIGINAL-R15P0-BOOT.img',old)
            with self.pins(source,old,new,k,system):
                with self.assertRaisesRegex(ValueError,'Corrected BOOT differs'):
                    m.package(source,staging,root/'out')
            self.assertFalse((root/'out').exists())

    def test_streamed_system_mismatch_leaves_no_rom(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);source,staging,old,new,k,system=self.fixture(root)
            with self.pins(source,old,new,k,system),patch.object(m,'SYSTEM_SHA','0'*64):
                # Keep the manifest check valid but simulate corrupt bytes read
                # after source authentication, exercising the streaming gate.
                real=m.validate_boots
                def validated(*args):
                    with patch.object(m,'SYSTEM_SHA',m.digest(system)):
                        return real(*args)
                with patch.object(m,'validate_boots',side_effect=validated):
                    with self.assertRaisesRegex(ValueError,'SYSTEM content hash mismatch'):
                        m.package(source,staging,root/'out')
            self.assertFalse((root/'out'/m.ROM_NAME).exists())
            self.assertFalse((root/'out'/m.ROM_NAME).with_suffix('.partial').exists())

    def test_guard_scripts_reject_wrong_device_without_writing(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);getprop=root/'getprop';getprop.write_text('#!/bin/sh\necho wrong-device\n');getprop.chmod(0o755)
            old=original_boot();new=kernel()
            with patch.object(m,'SYSTEM_BYTES',100):
                full=m.full_installer(old,new)
            undo=m.render((ROOT/'installer/r16-boot-restore.in').read_text(),dict(OLD_BYTES=10,OLD_SHA='0'*64,NEW_BYTES=20,NEW_SHA='1'*64))
            import os
            # Tool names are resolved before model checks; harmless wrappers
            # let the installer reach that gate on a host lacking recovery tools.
            for name in ['blockdev','unzip','sha256sum','dd','head','awk','wc','tr','sync','mktemp','rm','cat','readlink','df','mkdir']:
                p=root/name;p.write_text('#!/bin/sh\nexit 99\n');p.chmod(0o755)
            for script in [full,undo]:
                f=root/'installer';f.write_text(script)
                result=subprocess.run(['/bin/sh',str(f),'3','1','/external_sd/trial.zip'],capture_output=True,text=True,env={**os.environ,'PATH':str(root)})
                self.assertNotEqual(result.returncode,0)
                self.assertIn('STOP:' if script==undo else 'ERROR:',result.stdout)
                self.assertNotIn('Writing',result.stdout)


if __name__=='__main__':unittest.main()
