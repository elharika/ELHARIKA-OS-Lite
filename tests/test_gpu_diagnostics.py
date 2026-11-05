import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import struct
import time
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gpu_pack', ROOT/'scripts/package_gpu_diagnostics.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

class GpuDiagnosticsTests(unittest.TestCase):
    def test_builds_distinct_reversible_packages(self):
        with tempfile.TemporaryDirectory() as temp:
            # Structural ELF fixture only; never used as an executable or deliverable.
            helper = Path(temp)/'fixture-arm'
            data = bytearray(128)
            data[:16] = b'\x7fELF\x01\x01\x01'+bytes(9)
            struct.pack_into('<HHIIIIIHHHHHH',data,16,2,40,1,0x10054,52,0,0x5000000,52,32,1,0,0,0)
            struct.pack_into('<8I',data,52,1,0,0x10000,0x10000,128,128,5,4096)
            data[88:105] = b'security.selinux\0'
            helper.write_bytes(data)
            mod.build(Path(temp),helper)
            for action in ('INSTALL','REMOVE'):
                with zipfile.ZipFile(Path(temp)/('ELHARIKA-SM-P900-GPU-DIAGNOSTICS-'+action+'-r3.zip')) as z:
                    s = z.read('META-INF/com/google/android/update-binary').decode()
                    self.assertIn(mod.SF_SHA, s)
                    self.assertNotIn('@ACTION@', s)
                    self.assertIn('GPU-CAPTURE-v1', s)
                    self.assertEqual('gpu-capture.sh' in z.namelist(), action == 'INSTALL')
                    self.assertEqual('label-copy' in z.namelist(), action == 'INSTALL')
                    self.assertFalse(z.testzip())

    def test_foreign_device_cannot_mount_or_write(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp)
            (d/'getprop').write_text('#!/bin/sh\necho foreign_device\n'); (d/'getprop').chmod(0o755)
            for name in ('mount','umount','chcon'):
                f=d/name;f.write_text('#!/bin/sh\necho invoked >> "$MARKER"\nexit 1\n');f.chmod(0o755)
            with (d/'ui').open('w') as ui:
                r=subprocess.run(['/bin/sh', str(ROOT/'diagnostics/update-binary.in'), '3', str(ui.fileno()), '/external_sd/diag.zip'],
                    pass_fds=(ui.fileno(),), env=dict(os.environ,PATH=str(d)+':'+os.environ['PATH'],MARKER=str(d/'marker')),capture_output=True)
            self.assertNotEqual(r.returncode,0)
            self.assertIn('Only SM-P900', (d/'ui').read_text())
            self.assertFalse((d/'marker').exists())

    def test_native_helper_copies_exact_label_and_refuses_wrong_reference(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp); helper=d/'label-copy-host'
            subprocess.run(['gcc','-DLABEL_COPY_TEST','-Os','-nostdlib','-static','-fno-pie','-no-pie',
                '-fno-builtin','-fno-stack-protector','-Wall','-Wextra','-Werror',
                '-Wl,--build-id=none','-Wl,-e,_start',str(ROOT/'diagnostics/label-copy.c'),'-o',str(helper)],check=True)
            ref=d/'reference';target=d/'target';ref.write_bytes(b'ref');target.write_bytes(b'unchanged-content')
            attribute='user.elharika-label-test'; label=b'u:object_r:system_file:s0\0'
            os.setxattr(ref,attribute,label)
            r=subprocess.run([str(helper),str(ref),str(target)],capture_output=True)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(os.getxattr(target,attribute),label)
            self.assertEqual(target.read_bytes(),b'unchanged-content')
            os.setxattr(ref,attribute,b'u:object_r:wrong_type:s0\0')
            r=subprocess.run([str(helper),str(ref),str(target)],capture_output=True)
            self.assertNotEqual(r.returncode,0)
            self.assertEqual(os.getxattr(target,attribute),label)
            os.setxattr(ref,attribute,label)
            r=subprocess.run([str(helper),str(ref),str(d/'missing')],capture_output=True)
            self.assertNotEqual(r.returncode,0)
            self.assertIn(b'errno/status=2',r.stderr)
            with self.assertRaises(ValueError): mod.validate_helper(helper)

    def test_trace_watcher_checks_executable_and_does_not_repeat_same_pid(self):
        template=(ROOT/'diagnostics/gpu-capture.sh').read_text()
        body=template.split('trace_surfaceflinger() {',1)[1].split('\n}',1)[0]
        function='trace_surfaceflinger() {'+body+'\n}\ntrace_surfaceflinger "$@"\n'
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp); marker=d/'marker'
            prop=d/'getprop';prop.write_text('#!/bin/sh\necho "$TEST_PID"\n');prop.chmod(0o755)
            tracer=d/'strace';tracer.write_text('#!/bin/sh\n[ "$1" = -V ] && exit 0\necho "$*" >> "$MARKER"\n');tracer.chmod(0o755)
            target=subprocess.Popen(['sleep','10'])
            try:
                executable=None
                for _ in range(30):
                    try:
                        executable=os.readlink('/proc/'+str(target.pid)+'/exe');break
                    except (PermissionError,FileNotFoundError):time.sleep(0.01)
                if executable is None:
                    if os.environ.get('GITHUB_ACTIONS') == 'true':
                        self.fail('GitHub runner must execute the real child /proc executable guard test')
                    self.skipTest('Host sandbox prevents reading child /proc/PID/exe; execute this test on the GitHub Linux runner')
                env=dict(os.environ,PATH=str(d)+':'+os.environ['PATH'],TEST_PID=str(target.pid),MARKER=str(marker))
                r=subprocess.run(['/bin/sh','-s','--',str(d),executable,str(tracer),'3'],input=function,text=True,env=env,capture_output=True)
                self.assertEqual(r.returncode,0,r.stderr)
                self.assertEqual(len(marker.read_text().splitlines()),1)
                self.assertIn('-p '+str(target.pid),marker.read_text())
                marker.unlink()
                r=subprocess.run(['/bin/sh','-s','--',str(d),'/wrong/executable',str(tracer),'3'],input=function,text=True,env=env,capture_output=True)
                self.assertEqual(r.returncode,0,r.stderr)
                self.assertFalse(marker.exists())
                self.assertIsNone(target.poll(), 'Watcher must not kill its target')
            finally:
                target.terminate();target.wait()

if __name__ == '__main__': unittest.main()
