#!/usr/bin/env python3
"""Build a one-HTML playable extension with a byte-preserving legacy engine."""
from pathlib import Path
import hashlib
import json
ROOT = Path(__file__).resolve().parent
original = (ROOT/'legacy/Phase21_Original.html').read_bytes()
sha = hashlib.sha256(original).hexdigest()
source = original.decode('utf-8')
assert source.count('</head>') == 1 and source.count('</body>') == 1
css = (ROOT/'src/depth.css').read_text(encoding='utf-8')
scene = (ROOT/'src/scene.js').read_text(encoding='utf-8')
boot = (ROOT/'src/boot.js').read_text(encoding='utf-8')
assert '</script' not in scene.lower() and '</script' not in boot.lower()
source = source.replace('<title>MARORONG CARD WAR · Phase 21 UI Fixed</title>', '<title>MARORONG CARD WAR · Phase 31 3D Prototype</title>')
source = source.replace('</head>',f'<style id="mcw3d-extension-css">\n{css}\n</style>\n</head>')
source = source.replace('</body>', f'<script type="module" id="mcw3d-extension-js">\n{scene}\n{boot}\n</script>\n</body>')
output = ROOT/'Marorong_Card_War_Phase31_3D_Prototype.html'
output.write_text(source, encoding='utf-8')
manifest = {
    'build': 'Phase31 Portrait Identity 01',
    'source': 'Phase21_UI_Fixed',
    'source_sha256': sha,
    'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
    'three_version': '0.160.1',
    'changes_to_rules': False,
    'runtime': 'Legacy playable offline; optional WebGL Three.js from vendored or CDN module; CSS depth fallback',
}
(ROOT/'build-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
print('BUILD PASS')
print('SOURCE_SHA256',sha)
print('OUTPUT_SHA256',manifest['output_sha256'])
print('FILE',output.name,'BYTES',output.stat().st_size)
