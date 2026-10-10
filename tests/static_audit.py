from pathlib import Path
import hashlib
import json
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
original=(ROOT/'legacy/Phase21_Original.html').read_text('utf-8')
build=(ROOT/'Marorong_Card_War_Phase35_3D_Prototype.html').read_text('utf-8')
a=BeautifulSoup(original,'html.parser');b=BeautifulSoup(build,'html.parser')
scripts_a=a.select('script'); scripts_b=b.select('script')
assert len(scripts_a)==2,len(scripts_a)
assert len(scripts_b)==3,len(scripts_b)
assert scripts_a[0].string==scripts_b[0].string, 'Card database changed'
assert scripts_a[1].string==scripts_b[1].string, 'Gameplay JavaScript changed'
assert b.select_one('#mcw3d-extension-js') is not None
assert b.select_one('#mcw3d-extension-css') is not None
assert 'localStorage.setItem' in scripts_a[1].string
cards=json.loads(scripts_a[0].string)
assert 'cards' in cards and 'factions' in cards
assert len(cards['cards'])==244,len(cards['cards'])
assert len(cards['factions'])==10,len(cards['factions'])
manifest=json.loads((ROOT/'build-manifest.json').read_text('utf-8'))
assert hashlib.sha256(original.encode('utf-8')).hexdigest()==manifest['source_sha256']
assert hashlib.sha256(build.encode('utf-8')).hexdigest()==manifest['output_sha256']
print('STATIC AUDIT PASS - original game script byte-for-byte unchanged; 244 cards, 10 factions; SHA256 matches.')
