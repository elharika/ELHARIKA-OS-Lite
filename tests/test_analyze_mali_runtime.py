import gzip
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

p = Path(__file__).resolve().parents[1] / "scripts/analyze_mali_runtime.py"
spec = importlib.util.spec_from_file_location("mali_runtime", p)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def capture(path, collector="", logs="", config="CONFIG_MALI_T6XX_R7P0=y\n", trace=""):
    files = {
        "elharika-gpu-diagnostics/collector.log": collector.encode(),
        "elharika-gpu-diagnostics/logcat-final.txt": logs.encode(),
        "elharika-gpu-diagnostics/android-kernel-config.gz": gzip.compress(config.encode()),
        "elharika-gpu-diagnostics/surfaceflinger-strace-1.txt": trace.encode()
    }
    with tarfile.open(path, "w:gz") as tar:
        for name, contents in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(contents)
            tar.addfile(info, io.BytesIO(contents))


class TestGpuRuntimeAudit(unittest.TestCase):
    def test_egl_swap_crash_is_not_boot_success(self):
        with tempfile.TemporaryDirectory() as d:
            a = Path(d) / "a.tgz"
            capture(a, "/dev/mali0\nMali-T62x MP6 r0p1", 
                "RenderEngine: renderer  : Mali-T628\n"
                "Fatal signal 11 (SIGSEGV) in tid (BootAnimation)\n"
                "/lib/egl/libGLES_mali.so (eglp_swap_buffers+1460)\n",
                trace="ioctl(9</dev/mali0>, something) = 0")
            r = module.inspect_archive(a)
            self.assertEqual(r["verdict"], "GPU_INITIALIZED_EGL_SWAP_CRASH")
            self.assertTrue(r["successful_gpu_ioctl"])
            self.assertFalse(r["ui_boot_proven"])

    def test_no_gpu_is_not_success(self):
        with tempfile.TemporaryDirectory() as d:
            a = Path(d) / "a.tgz"
            capture(a, "/dev/mali0: missing", "EGL_NOT_INITIALIZED")
            self.assertEqual(module.inspect_archive(a)["verdict"], "GPU_DEVICE_ABSENT_OR_UNVERIFIED")

    def test_missing_hal_does_not_prove_boot(self):
        with tempfile.TemporaryDirectory() as d:
            a = Path(d) / "a.tgz"
            capture(a, "/dev/mali0\nMali-T62x MP6 r0p1",
                "vendor.lineage.touch@1.0::IKeyDisabler/default is not registered")
            self.assertEqual(module.inspect_archive(a)["verdict"], "TOUCH_HAL_MISSING_BOOT_UNVERIFIED")

    def test_incomplete_archive_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            a = Path(d) / "a.tgz"
            with tarfile.open(a, "w:gz"): pass
            with self.assertRaises(ValueError):
                module.inspect_archive(a)


if __name__ == "__main__":
    unittest.main()
