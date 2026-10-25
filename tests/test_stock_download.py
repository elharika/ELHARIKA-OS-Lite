from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from download_stock_input import confirmation_url

class ConfirmationTests(unittest.TestCase):
    def test_valid_form(self):
        html='<form id="download-form" action="https://drive.usercontent.google.com/download"><input name="id" value="abc"><input name="confirm" value="t"></form>'
        self.assertIn('id=abc',confirmation_url(html,'abc'))
    def test_wrong_host_or_id(self):
        for host,file_id in [('evil.example','abc'),('drive.usercontent.google.com','wrong')]:
            html=f'<form id="download-form" action="https://{host}/download"><input name="id" value="{file_id}"></form>'
            with self.assertRaises(ValueError):confirmation_url(html,'abc')
if __name__=='__main__':unittest.main()
