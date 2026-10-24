from pathlib import Path
import sys,tempfile,unittest,json
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_sync_manifest import overlay
from bounded_sync import run

class SyncTests(unittest.TestCase):
    def test_collision_removed_and_pins_kept(self):
        base=ET.fromstring('<manifest><project name="old" path="device/samsung/v1awifi"/></manifest>')
        hardware=ET.fromstring('<manifest><project name="new" path="device/samsung/v1awifi" revision="'+('a'*40)+'"/></manifest>')
        out=overlay(base,hardware)
        self.assertEqual(out.find('remove-project').get('name'),'old')
        self.assertEqual(out.find('project').get('revision'),'a'*40)
        self.assertEqual(out.find('project').get('remote'),'elharika-hardware')
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
