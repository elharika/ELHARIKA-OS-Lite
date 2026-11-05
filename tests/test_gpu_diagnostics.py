import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gpu_pack', ROOT/'scripts/package_gpu_diagnostics.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

class GpuDiagnosticsTests(unittest.TestCase):
    def test_builds_distinct_reversible_packages(self):
        with tempfile.TemporaryDirectory() as temp:
            mod.build(Path(temp))
            for action in ('INSTALL','REMOVE'):
                with zipfile.ZipFile(Path(temp)/('ELHARIKA-SM-P900-GPU-DIAGNOSTICS-'+action+'.zip')) as z:
                    s = z.read('META-INF/com/google/android/update-binary').decode()
                    self.assertIn(mod.SF_SHA, s)
                    self.assertNotIn('@ACTION@', s)
                    self.assertIn('GPU-CAPTURE-v1', s)
                    self.assertEqual('gpu-capture.sh' in z.namelist(), action == 'INSTALL')
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

if __name__ == '__main__': unittest.main()
