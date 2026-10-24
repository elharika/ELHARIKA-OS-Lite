import copy
import json
from pathlib import Path
import sys
import unittest
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from export_candidate_lists import export
from minimal_vendor_baseline import derive as minimal
from stock_candidate_baseline import derive
ROOT=Path(__file__).resolve().parents[1]

class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.base=minimal(json.loads((ROOT/'reports/stock-P900XXS0BPL4-vendor-comparison.json').read_text()))
        self.rules=json.loads((ROOT/'rom/stock-candidate-overrides.json').read_text())
    def test_candidates_keep_real_bt_filename_and_remain_unapproved(self):
        before=copy.deepcopy(self.base)
        r=derive(self.base,self.rules)
        self.assertEqual(self.base,before)
        self.assertEqual(r['comparison']['missing'],[])
        self.assertFalse(r['profile']['release_approved'])
        changed=[x for x in r['comparison']['records'] if x.get('candidate_only')]
        self.assertEqual(len(changed),4)
        bt=next(x for x in changed if x['source'].endswith('.hcd'))
        self.assertTrue(bt['destination'].endswith('bcm4350_V0301.0591.hcd'))
        self.assertTrue(all(x['android11_compatible']=='NOT_TESTED' for x in changed))
    def test_export_real_lists(self):
        result=derive(self.base,self.rules)
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'lists'
            self.assertEqual(export(result,out),143)
            self.assertEqual(len(list(out.glob('*/proprietary-files.txt'))),3)
            common=(out/'android_device_samsung_universal5420-common/proprietary-files.txt').read_text()
            self.assertNotIn('libaptX',common)
            self.assertNotIn('libwvhidl',common)
            self.assertIn('bcm4350_V0301.0591.hcd',common)
            with self.assertRaises(FileExistsError):export(result,out)

    def test_wrong_image_and_duplicate_rule_rejected(self):
        bad=copy.deepcopy(self.base);bad['identity']['model']='SM-P905'
        with self.assertRaises(ValueError):derive(bad,self.rules)
        self.rules['overrides'].append(self.rules['overrides'][0])
        with self.assertRaises(ValueError):derive(self.base,self.rules)

if __name__=='__main__':unittest.main()
