#!/usr/bin/env python3
"""Build a one-HTML playable extension with a byte-preserving legacy engine."""
from pathlib import Path
import hashlib
import json
from src.card_art_bundle import bundle
ROOT = Path(__file__).resolve().parent
original = (ROOT/'legacy/Phase21_Original.html').read_bytes()
sha = hashlib.sha256(original).hexdigest()
source = original.decode('utf-8')
assert source.count('</head>') == 1 and source.count('</body>') == 1
css = (ROOT/'src/depth.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/integrated.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/phase56.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/pc-batch-polish.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/phase68-hand-fan.css').read_text(encoding='utf-8')
scene = (ROOT/'src/scene.js').read_text(encoding='utf-8')
cinema = (ROOT/'src/cinema.js').read_text(encoding='utf-8')
battlefield = (ROOT/'src/battlefield.js').read_text(encoding='utf-8')
integrated = (ROOT/'src/integrated.js').read_text(encoding='utf-8')
boot = (ROOT/'src/boot.js').read_text(encoding='utf-8')
owner_art_registry, owner_art_ids = bundle(ROOT)
card_art_identity = (ROOT/'src/card_art_identity.js').read_text(encoding='utf-8')
assert '</script' not in integrated.lower() and '</script' not in scene.lower() and '</script' not in cinema.lower() and '</script' not in battlefield.lower() and '</script' not in boot.lower() and '</script' not in card_art_identity.lower()
source = source.replace('<title>MARORONG CARD WAR · Phase 21 UI Fixed</title>', '<title>MARORONG CARD WAR · Phase 69 PC Battlefield Zones</title>')
source = source.replace('</head>',f'<style id="mcw3d-extension-css">\n{css}\n</style>\n</head>')
source = source.replace('</body>', f'<script type="module" id="mcw3d-extension-js">\n{owner_art_registry}{card_art_identity}\n{scene}\n{cinema}\n{battlefield}\n{integrated}\n{boot}\n</script>\n</body>')
output = ROOT/'Marorong_Card_War_Phase69_3D_Prototype.html'
output.write_text(source, encoding='utf-8')
# Retain the prior artifact path for pre-existing, unmodified regression scripts.
(ROOT/'Marorong_Card_War_Phase55_3D_Prototype.html').write_bytes(output.read_bytes())
(ROOT/'Marorong_Card_War_Phase56_3D_Prototype.html').write_bytes(output.read_bytes())
(ROOT/'Marorong_Card_War_Phase57_3D_Prototype.html').write_bytes(output.read_bytes())
(ROOT/'Marorong_Card_War_Phase58_3D_Prototype.html').write_bytes(output.read_bytes())
(ROOT/'Marorong_Card_War_Phase59_3D_Prototype.html').write_bytes(output.read_bytes())
(ROOT/'Marorong_Card_War_Phase63_3D_Prototype.html').write_bytes(output.read_bytes())
(ROOT/'Marorong_Card_War_Phase64_3D_Prototype.html').write_bytes(output.read_bytes())
(ROOT/'Marorong_Card_War_Phase65_3D_Prototype.html').write_bytes(output.read_bytes())
(ROOT/'Marorong_Card_War_Phase66_3D_Prototype.html').write_bytes(output.read_bytes())
(ROOT/'Marorong_Card_War_Phase67_3D_Prototype.html').write_bytes(output.read_bytes())
(ROOT/'Marorong_Card_War_Phase68_3D_Prototype.html').write_bytes(output.read_bytes())
manifest = {
    'build': 'Phase69 PC battlefield territory and native slot legibility',
    'source': 'Phase21_UI_Fixed',
    'source_sha256': sha,
    'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
    'three_version': '0.160.1',
    'changes_to_rules': False,
    'pc_batch_phases': [60,61,62,63,64,65,66,67,68,69],
    'pc_zone_contrast_revision': 69,
    'pc_native_hand_fan_revision': 68,
    'pc_hand_fan_open_height': 'clamp(194px,24vh,270px)',
    'pc_card_focus_revision': 67,
    'pc_card_idle_scale': 1.30,
    'pc_card_focus_scale': 1.52,
    'pc_native_context_dedup_revision': 66,
    'pc_native_command_dock_revision': 65,
    'owner_art_on_visible_native_cards': True,
    'context_actions_delegate_to_native': True,
    'artwork_master_size': [1200, 960],
    'artwork_canvas_region': {'x':56,'y':199,'width':400,'height':320},
    'artwork_state': 'owner_art_ready' if owner_art_ids else 'awaiting owner-provided artwork',
    'embedded_artwork_ids': list(owner_art_ids),
    'embedded_artwork_count': len(owner_art_ids),
    'runtime': 'Legacy playable offline; optional WebGL Three.js from vendored or CDN module; CSS depth fallback',
}
(ROOT/'build-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
print('BUILD PASS')
print('SOURCE_SHA256',sha)
print('OUTPUT_SHA256',manifest['output_sha256'])
print('FILE',output.name,'BYTES',output.stat().st_size)
