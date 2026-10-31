from pathlib import Path
import sys,tempfile,unittest,json
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_sync_manifest import overlay, REQUIRED_PLATFORM_PROJECTS
from bounded_sync import run

class SyncTests(unittest.TestCase):
    def _hardware(self):
        return ET.fromstring('<manifest><project name="new" path="device/samsung/v1awifi" revision="'+('a'*40)+'"/></manifest>')

    def _required_by_path(self):
        return {p['path']: p for p in REQUIRED_PLATFORM_PROJECTS}

    def test_collision_removed_and_pins_kept(self):
        base=ET.fromstring('<manifest><project name="old" path="device/samsung/v1awifi"/></manifest>')
        out=overlay(base,self._hardware())
        removes=[p for p in out.findall('remove-project') if p.get('name')=='old']
        self.assertEqual(len(removes),1)
        hardware=[p for p in out.findall('project') if p.get('path')=='device/samsung/v1awifi'][0]
        self.assertEqual(hardware.get('revision'),'a'*40)
        self.assertEqual(hardware.get('remote'),'elharika-hardware')

    def _assert_required_replaced_once(self, out, path):
        expected=self._required_by_path()[path]
        required=[p for p in out.findall('project') if p.get('path')==path]
        removes=[p for p in out.findall('remove-project') if p.get('name')==expected['name']]
        self.assertEqual(len(required),1)
        self.assertEqual(len(removes),1)
        self.assertEqual(removes[0].get('optional'),'true')
        self.assertEqual(required[0].get('name'),expected['name'])
        self.assertEqual(required[0].get('remote'),expected['remote'])
        self.assertEqual(required[0].get('revision'),expected['revision'])
        self.assertIsNone(required[0].get('groups'))

    def test_reduced_manifest_readds_complete_pinned_build_closure(self):
        base=ET.fromstring('<manifest><project name="LineageOS/android_build" path="build/make"/></manifest>')
        out=overlay(base,self._hardware())
        paths=[p.get('path') for p in out.findall('project')]
        expected=set(self._required_by_path())
        self.assertEqual(set(paths[:-1]),expected)
        self.assertEqual(len(paths[:-1]),len(expected))
        for path in expected:
            self._assert_required_replaced_once(out,path)

    def test_full_manifest_replaces_not_duplicates_required_projects(self):
        body=''.join(
            '<project name="'+p['name']+'" path="'+p['path']+'" remote="aosp" revision="'+p['revision']+'" groups="pdk,vts"/>'
            for p in REQUIRED_PLATFORM_PROJECTS
        )
        base=ET.fromstring('<manifest>'+body+'</manifest>')
        out=overlay(base,self._hardware())
        for path in self._required_by_path():
            self._assert_required_replaced_once(out,path)

    def test_required_platform_projects_are_exact_and_fully_pinned(self):
        projects=self._required_by_path()
        self.assertEqual(len(REQUIRED_PLATFORM_PROJECTS),37)
        self.assertEqual(len(projects),37)
        expected_critical={
            'kernel/configs':'e4102999005f8f3c8db1fdacfba80a2c581a72f1',
            'frameworks/base':'2f5cf1e4fc1e8b1480d3c27a855f95d6d45429f4',
            'packages/modules/NetworkStack':'88d4fd9cd4e49102d92cd7e6d8e270284e00e76e',
            'cts':'c554ab005261d4cd194b9a19aa5dd68c72d7df6e',
            'frameworks/ex':'5050934c425fa1c775d31a1c2ab7bbe6f8fe5bc6',
            'tools/dexter':'6426a69b96ebca6b9e15494d9f2bb0ec5cfffccd',
            'test/suite_harness':'3a5b1207c2177d72db24da78aba86574d95c26f8',
            'test/vts':'f001416f91f7f02a7a042bd0c52f0c62394fa78c',
            'test/vts-testcase/fuzz':'43fcddcde333cac6b365ea32f0fecc3a2c9d7ff8',
            'test/vts-testcase/hal':'430829c9435b28f605cac28b930586281ec674f7',
        }
        for path,revision in expected_critical.items():
            self.assertEqual(projects[path]['revision'],revision)
        self.assertEqual(projects['frameworks/base']['name'],'LineageOS/android_frameworks_base')
        self.assertEqual(projects['frameworks/base']['remote'],'elharika-github')
        self.assertEqual(projects['cts']['name'],'LineageOS/android_cts')
        self.assertEqual(projects['cts']['remote'],'elharika-github')
        self.assertEqual(projects['packages/modules/NetworkStack']['name'],'platform/packages/modules/NetworkStack')
        self.assertEqual(projects['packages/modules/NetworkStack']['remote'],'elharika-aosp')
        names=set()
        for project in REQUIRED_PLATFORM_PROJECTS:
            self.assertRegex(project['revision'],r'^[0-9a-f]{40}$')
            self.assertIn(project['remote'],{'elharika-aosp','elharika-github'})
            self.assertNotIn(project['name'],names)
            names.add(project['name'])

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
