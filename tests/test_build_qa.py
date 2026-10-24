from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import rom_preflight
import collect_device_qa


class BuildQATests(unittest.TestCase):
    def test_empty_tree_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            r = rom_preflight.inspect(Path(d))
            self.assertEqual(r['status'], 'BLOCKED')
            self.assertIn('missing:build/envsetup.sh', r['blockers'])
            self.assertFalse(r['hardware_tested'])

    def test_unpinned_manifest_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'elharika-platform-lock.xml').write_text('<manifest><project name="test" revision="main"/></manifest>')
            r = rom_preflight.inspect(p)
            self.assertIn('platform lock must contain commit-pinned projects', r['blockers'])

    def test_wrong_device_leaves_no_output(self):
        with tempfile.TemporaryDirectory() as d, patch.object(collect_device_qa, 'command', return_value={'stdout':'SM-P905\n'}):
            p = Path(d) / 'out'
            with self.assertRaises(ValueError): collect_device_qa.collect(p)
            self.assertFalse(p.exists())

    def test_recovery_does_not_call_android_services(self):
        calls = []
        def fake(argv, timeout=30):
            calls.append(argv)
            value = {'ro.product.model':'SM-P900','ro.product.device':'v1awifi','ro.twrp.version':'3.x'}.get(argv[-1], '')
            return {'stdout':value,'stderr':'','returncode':0}
        with tempfile.TemporaryDirectory() as d, patch.object(collect_device_qa, 'command', side_effect=fake):
            r = collect_device_qa.collect(Path(d) / 'out')
            self.assertTrue(r['recovery_detected'])
            self.assertFalse(any('dumpsys' in c for c in calls))
            self.assertTrue(all('shell' in c for c in calls))

if __name__ == '__main__': unittest.main()
