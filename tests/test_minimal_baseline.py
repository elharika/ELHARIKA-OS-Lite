import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from minimal_vendor_baseline import derive,REMOVED

class MinimalBaselineTests(unittest.TestCase):
    def test_real_baseline_four_missing_and_original_untouched(self):
        original=json.loads((Path(__file__).resolve().parents[1]/'reports/stock-P900XXS0BPL4-vendor-comparison.json').read_text())
        before=copy.deepcopy(original)
        result=derive(original)
        self.assertEqual(original,before)
        self.assertEqual(len(result['comparison']['missing']),4)
        self.assertEqual(result['comparison']['required_entries'],144)
        self.assertEqual(result['comparison']['present'],140)
        self.assertFalse(REMOVED & {r['source'] for r in result['comparison']['records']})
        self.assertEqual(result['profile']['runtime_compatibility'],'NOT_TESTED')
    def test_wrong_device(self):
        with self.assertRaises(ValueError): derive({'identity':{'model':'SM-P905','device':'viennalte'}})

if __name__=='__main__': unittest.main()
