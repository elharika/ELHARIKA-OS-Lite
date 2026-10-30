from pathlib import Path
import sys,tempfile,unittest,json
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_sync_manifest import overlay, REQUIRED_PLATFORM_PROJECTS
from bounded_sync import run

class SyncTests(unittest.TestCase):
    def _hardware(self):
        return ET.fromstring('<manifest><project name="new" path="device/samsung/v1awifi" revision="'+('a'*40)+'"/></manifest>')

    def test_collision_removed_and_pins_kept(self):
        base=ET.fromstring('<manifest><project name="old" path="device/samsung/v1awifi"/></manifest>')
        out=overlay(base,self._hardware())
        self.assertEqual(out.find('remove-project').get('name'),'old')
        hardware=[p for p in out.findall('project') if p.get('path')=='device/samsung/v1awifi'][0]
        self.assertEqual(hardware.get('revision'),'a'*40)
        self.assertEqual(hardware.get('remote'),'elharika-hardware')

    def test_reduced_manifest_readds_only_pinned_kernel_configs(self):
        base=ET.fromstring('<manifest><project name="LineageOS/android_build" path="build/make"/></manifest>')
        out=overlay(base,self._hardware())
        required=[p for p in out.findall('project') if p.get('path')=='kernel/configs']
        self.assertEqual(len(required),1)
        self.assertEqual(required[0].get('name'),'kernel/configs')
        self.assertEqual(required[0].get('remote'),'elharika-aosp')
        self.assertEqual(required[0].get('revision'),REQUIRED_PLATFORM_PROJECTS[0]['revision'])
        self.assertIsNone(required[0].get('groups'))

    def test_full_manifest_does_not_duplicate_kernel_configs(self):
        pin=REQUIRED_PLATFORM_PROJECTS[0]['revision']
        base=ET.fromstring('<manifest><project name="kernel/configs" path="kernel/configs" remote="aosp" revision="'+pin+'"/></manifest>')
        out=overlay(base,self._hardware())
        self.assertFalse(any(p.get('path')=='kernel/configs' for p in out.findall('project')))

    def test_required_platform_project_is_fully_pinned(self):
        for project in REQUIRED_PLATFORM_PROJECTS:
            self.assertRegex(project['revision'],r'^[0-9a-f]{40}$')

    def test_unpinned_rejected(self):
        with self.assertRaises(ValueError):overlay(ET.Element('manifest'),ET.fromstring('<manifest><project name="x" path="device/samsung/v1awifi" revision="main"/></manifest>'))

    def test_process_failure_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            self.assertEqual(run([sys.executable,'-c','raise SystemExit(7)'],root,root/'evidence',1,1),2)
            r=json.loads((root/'evidence/sync-result.json').read_text())
            self.assertEqual(r['status'],'SYNC_ERROR');self.assertEqual(r['returncode'],7)
            self.assertFalse(r['android_compiled'])

if __name__=='__main__':unittest.main()
