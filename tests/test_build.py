import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build import amount, build, estimate, read_editions


class Records(unittest.TestCase):
    def test_growing_edition_preserves_old_receipts_and_routes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for folder in ['data','web','config']:
                shutil.copytree(ROOT/folder,root/folder)
            shutil.copy(ROOT/'tool.json',root)
            editions=read_editions(root)
            file_key,latest=editions[-1]
            added=copy.deepcopy(latest['results'][0])
            added.update(id='another-source',name='A source with <punctuation>')
            latest['results'].append(added)
            (root/'data/editions'/(file_key+'.json')).write_text(json.dumps(latest))
            build(root)
            out=root/'dist'
            self.assertIn('<link rel="canonical" href="https://coolcode.ca/slowweb/">',(out/'index.html').read_text())
            profiles=(out/'records').rglob('index.html')
            expected={p.parent.relative_to(out).as_posix()+'/' for p in profiles}
            self.assertEqual(expected,{node.text.removeprefix('https://coolcode.ca/slowweb/') for node in ET.parse(out/'sitemap.xml').findall('.//{*}loc')})
            self.assertIn('records/another-source/',expected)
            self.assertIn('&lt;punctuation&gt;',(out/'records/another-source/index.html').read_text())
            self.assertEqual(json.loads((out/'data/status.json').read_text())['receipt_count'],sum(len(ed['results']) for _,ed in editions))
            for route in expected:
                self.assertIn(f'<link rel="canonical" href="https://coolcode.ca/slowweb/{route}">',(out/route/'index.html').read_text())
    def test_partial_or_inaccessible_document_has_no_speed_claim(self):
        row={'outcome':'completed','network':{'encoded_bytes':7000,'finished':1,'all_observed_responses_finished':True}}
        self.assertEqual(estimate(row,56),'1.0 s')
        row['outcome']='unavailable'
        self.assertEqual(estimate(row,56),'Unavailable')
        row['outcome']='completed'
        row['network']['all_observed_responses_finished']=False
        self.assertIn('partial',amount(row))
        self.assertEqual(estimate(row,56),'Unavailable')
