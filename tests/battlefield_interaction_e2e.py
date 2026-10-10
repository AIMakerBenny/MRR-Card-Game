"""Phase 47 real Chromium WebGL pointer-to-legacy-input regression.
No synthetic game-state changes: all placements and selections use native game UI.
"""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
import threading
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
assert (ROOT/'vendor/three.module.js').exists()
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
  with sync_playwright() as p:
    opts={'headless':True,'args':['--no-sandbox','--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']}
    if Path('/usr/bin/chromium').exists():opts['executable_path']='/usr/bin/chromium'
    browser=p.chromium.launch(**opts)
    page=browser.new_page(viewport={'width':1920,'height':1080})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.add_init_script('''() => {
      let seed=Number(new URLSearchParams(location.search).get('qa_seed'))||198704;
      Math.random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};
    }''')
    url=f'http://127.0.0.1:{server.server_port}/Marorong_Card_War_Phase53_3D_Prototype.html'
    affordable=[]
    for seed in range(198704,198728):
      page.goto(url+f'?qa_seed={seed}')
      page.locator('#newGame').click();page.locator('#launchGame').click()
      page.get_by_role('button',name='이 손패로 시작').click()
      cards=page.locator('.hand-slot').evaluate_all('''els=>els.map((e,i)=>({
        index:i,cost:Number(e.querySelector('.cost-bubble')?.textContent||99),
        board:/type-(몬스터|시설|영웅유닛)/.test(e.querySelector('.card-ui')?.className||'')
      }))''')
      affordable=[v for v in cards if v['board'] and v['cost']<=2]
      if affordable:break
    assert affordable,'Cannot test lawful native placement'
    hand_before=page.locator('.hand-slot').count()
    page.locator('.hand-slot').nth(affordable[0]['index']).evaluate('(e)=>e.click()')
    targets=page.locator('#arena .slot.legal')
    assert targets.count()>0
    target_key=targets.first.get_attribute('data-slot')
    assert target_key
    legal_count=targets.count()
    before_3d=page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}''')
    page.locator('#mrr-battlefield-open').click()
    page.wait_for_function('MRRBattlefield.state.open && MRRBattlefield.state.scene.frames>2',timeout=19000)
    state=page.evaluate('MRRBattlefield.state.scene')
    assert state['revision']>=47 and state['projection']=='PerspectiveCamera',state
    assert state['slotCount']==30 and state['legalCount']==legal_count,state
    assert state['pickableCount']>=30 and state['shadows'],state
    assert page.locator('#mrr-battlefield-stage canvas').count()==1
    page.screenshot(path=str(ROOT/'tests/phase47_legal_targets_fhd.png'))
    pt=page.evaluate('(key)=>MRRBattlefield.scene.projectSlot(key)',target_key)
    assert pt and pt['x']>0 and pt['y']>0,pt
    page.mouse.move(pt['x'],pt['y'])
    page.mouse.click(pt['x'],pt['y'])
    page.wait_for_function('MRRBattlefield.state.scene.publicCardCount>=1',timeout=7000)
    assert page.locator('#arena [data-slot="'+target_key+'"] .board-card').count()==1,'Raycast target failed to issue one legal native placement'
    displayed_name=page.locator('#arena [data-slot="'+target_key+'"] .card-name').inner_text().strip()
    # After a native placement, the new 3D mesh is slightly raised above the
    # previously clicked empty tile. Move the real pointer onto its new face.
    new_card_pt=page.evaluate('(key)=>MRRBattlefield.scene.projectCard(key)',target_key)
    assert new_card_pt
    for dx,dy in [(0,0),(0,-12),(-12,0),(12,0),(0,12)]:
      page.mouse.move(new_card_pt['x']+dx,new_card_pt['y']+dy)
      page.wait_for_timeout(90)
      if page.locator('#mrr-battlefield-cardtip strong').count() and page.locator('#mrr-battlefield-cardtip strong').text_content()==displayed_name:
        break
    assert page.locator('#mrr-battlefield-cardtip strong').count() and page.locator('#mrr-battlefield-cardtip strong').text_content()==displayed_name,'Native card face hover info did not update'
    assert page.locator('.hand-slot').count()==hand_before-1,'Native placement not processed exactly once'
    assert page.locator('#arena .board-card').count()==1,'Duplicate placement during 3D selection'
    assert page.evaluate('MRRBattlefield.state.scene.legalCount')==0
    after_placement=page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}''')
    assert before_3d!=after_placement,'Native game was not advanced by legal 3D click'
    pt=page.evaluate('(key)=>MRRBattlefield.scene.projectCard(key)',target_key)
    assert pt
    # Perspective overlap can put a neighboring hit mesh at the projected
    # center on some SwiftShader frames. Probe actual nearby pointer pixels.
    hit=False
    for dx,dy in [(0,0),(0,-12),(-12,0),(12,0),(0,12),(-8,-8),(8,-8)]:
      page.mouse.move(pt['x']+dx,pt['y']+dy)
      page.wait_for_timeout(100)
      if page.evaluate('(key)=>MRRBattlefield.state.scene.hoveredKey===key',target_key):
        hit=True
        pt={'x':pt['x']+dx,'y':pt['y']+dy}
        break
    assert hit,'Raycaster did not register any pixel around the real public card'
    assert page.locator('#mrr-battlefield-cardtip.visible').count()==1
    assert page.evaluate('MRRBattlefield.state.scene.cardMeshCount')==1
    assert after_placement==page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}'''),'Hover caused game mutation'
    page.screenshot(path=str(ROOT/'tests/phase47_card_hover_fhd.png'))
    page.mouse.click(pt['x'],pt['y'])
    page.wait_for_function('(key)=>MRRBattlefield.state.scene.selectedKey===key',arg=target_key,timeout=6000)
    assert page.locator('#arena [data-slot="'+target_key+'"].selected-slot').count()==1
    def native_disabled(q):
      return page.locator(q).count()==0 or page.locator(q).is_disabled()
    assert page.locator('#mrr-battlefield-attack').is_disabled()==native_disabled('#inspectBody button[data-actor="attack"]')
    assert page.locator('#mrr-battlefield-move').is_disabled()==native_disabled('#inspectBody button[data-actor="move"]')
    assert page.evaluate('MRRBattlefield.state.scene.attackTargetCount')==page.locator('#arena .slot.attack-target').count()
    assert page.locator('#mrr-battlefield-cardtip').count()==1
    page.screenshot(path=str(ROOT/'tests/phase47_card_selected_fhd.png'))
    # Dragging over the card rotates the camera and does NOT trigger another click.
    selected=page.evaluate('MRRBattlefield.state.scene.selectedKey')
    stage=page.locator('#mrr-battlefield-stage').bounding_box()
    px=stage['x']+stage['width']*.64;py=stage['y']+stage['height']*.42
    page.mouse.move(px,py);page.mouse.down();page.mouse.move(px+80,py+31,steps=5);page.mouse.up()
    page.wait_for_function('Math.abs(MRRBattlefield.state.scene.yaw)>.1')
    assert page.evaluate('MRRBattlefield.state.scene.selectedKey')==selected
    assert page.locator('#arena .board-card').count()==1
    page.locator('#mrr-battlefield-reset').click()
    for w,h in [(1366,768),(390,844)]:
      page.set_viewport_size({'width':w,'height':h})
      page.wait_for_timeout(600)
      assert page.locator('#mrr-battlefield-stage canvas').evaluate('e=>e.width>100 && e.height>100')
      assert page.evaluate('MRRBattlefield.state.scene.slotCount')==30
      assert page.evaluate('MRRBattlefield.state.scene.cardMeshCount')==1
      page.screenshot(path=str(ROOT/f'tests/phase47_card_selected_{w}x{h}.png'))
    assert after_placement==page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}''')
    page.locator('#mrr-battlefield-close').click()
    assert not page.evaluate('MRRBattlefield.state.open')
    assert page.evaluate('MRRBattlefield.scene===null')
    assert page.locator('#mrr-battlefield-stage canvas').count()==0
    assert page.evaluate("document.activeElement?.id==='mrr-battlefield-open'")
    page.locator('#mrr-battlefield-open').click()
    page.wait_for_function('MRRBattlefield.state.open && MRRBattlefield.state.scene.frames>2',timeout=18000)
    assert page.locator('#mrr-battlefield-stage canvas').count()==1
    page.keyboard.press('Escape')
    page.wait_for_function('!MRRBattlefield.state.open',timeout=5000)
    assert page.evaluate('MRRBattlefield.scene===null')
    assert not errors,errors
    print('PHASE47 PASS - real 3D slot raycast, single native placement, card hover/selection, true legality mirroring, safe orbit, 3 viewport screenshots and GPU cleanup')
    browser.close()
finally:
  server.shutdown();server.server_close()
