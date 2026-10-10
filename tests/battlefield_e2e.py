"""Phase46 genuine Chromium/SwiftShader WebGL multi-card perspective scene test."""
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
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.add_init_script('''() => {
      let seed=Number(new URLSearchParams(location.search).get('qa_seed'))||198704;
      Math.random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};
    }''')
    url=f'http://127.0.0.1:{server.server_port}/Marorong_Card_War_Phase55_3D_Prototype.html'
    legal=[]
    for seed in range(198704,198728):
      page.goto(url+f'?qa_seed={seed}')
      page.locator('#newGame').click();page.locator('#launchGame').click()
      page.get_by_role('button',name='이 손패로 시작').click()
      choices=page.locator('.hand-slot').evaluate_all('''els=>els.map((e,i)=>({
        index:i,cost:Number(e.querySelector('.cost-bubble')?.textContent||99),
        board:/type-(몬스터|시설|영웅유닛)/.test(e.querySelector('.card-ui')?.className||'')
      }))''')
      legal=[x for x in choices if x['board'] and x['cost']<=2]
      if legal:break
    assert legal,'No lawful public card placement in deterministic openings'
    assert page.locator('#arena [data-slot]').count()==30
    page.locator('.hand-slot').nth(legal[0]['index']).evaluate('(e)=>e.click()')
    assert page.locator('.slot.legal').count()>0
    page.locator('.slot.legal').first.evaluate('(e)=>e.click()')
    assert page.locator('#arena .board-card').count()>=1
    original=page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}''')
    name=page.locator('#arena .board-card .card-name').first.inner_text().strip()
    assert name
    page.locator('#mrr-battlefield-open').click()
    page.wait_for_function('MRRBattlefield.state.open && MRRBattlefield.state.scene.frames>3',timeout=17000)
    state=page.evaluate('MRRBattlefield.state.scene')
    assert state['revision']>=46 and state['projection']=='PerspectiveCamera',state
    assert state['slotCount']==30 and state['shadows'],state
    assert state['publicCardCount']>=1 and state['cardMeshCount']==state['publicCardCount'],state
    assert state['rendererAlive'],state
    assert page.locator('#mrr-battlefield-stage canvas').count()==1
    assert page.locator('#mrr-battlefield-stage canvas').evaluate('e=>e.width>500 && e.height>350')
    page.wait_for_timeout(300)
    page.screenshot(path=str(ROOT/'tests/phase46_battlefield_1920x1080.png'))
    # Actual pointer camera interaction is live, without writing game state.
    box=page.locator('#mrr-battlefield-stage').bounding_box()
    mx=box['x']+box['width']*.65;my=box['y']+box['height']*.45
    page.mouse.move(mx,my);page.mouse.down();page.mouse.move(mx+95,my+40,steps=6);page.mouse.up()
    page.wait_for_function('Math.abs(MRRBattlefield.state.scene.yaw)>.12')
    page.mouse.wheel(0,190)
    page.wait_for_function('MRRBattlefield.state.scene.distance>29')
    page.locator('#mrr-battlefield-reset').click()
    page.wait_for_function('Math.abs(MRRBattlefield.state.scene.yaw)<.001 && MRRBattlefield.state.scene.distance===29')
    for w,h in [(1366,768),(390,844)]:
      page.set_viewport_size({'width':w,'height':h})
      page.wait_for_timeout(600)
      assert page.locator('#mrr-battlefield-stage canvas').evaluate('e=>e.width>100 && e.height>100')
      assert page.evaluate('MRRBattlefield.state.scene.slotCount')==30
      page.screenshot(path=str(ROOT/f'tests/phase46_battlefield_{w}x{h}.png'))
    page.locator('#mrr-battlefield-close').click()
    assert not page.evaluate('MRRBattlefield.state.open')
    assert page.evaluate('MRRBattlefield.scene===null')
    assert page.locator('#mrr-battlefield-stage canvas').count()==0
    assert page.evaluate("document.activeElement?.id==='mrr-battlefield-open'")
    for i in range(2):
      page.locator('#mrr-battlefield-open').click()
      page.wait_for_function('MRRBattlefield.state.open && MRRBattlefield.state.scene.frames>2',timeout=17000)
      assert page.locator('#mrr-battlefield-stage canvas').count()==1
      page.keyboard.press('Escape')
      page.wait_for_function('!MRRBattlefield.state.open',timeout=5000)
      assert page.evaluate('MRRBattlefield.scene===null')
    assert original==page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}'''), 'Read-only 3D presentation mutated original game'
    assert page.locator('#arena [data-slot]').count()==30
    assert not errors,errors
    print('PHASE46 PASS: perspective world, 30 mirrored slots, public multi-card display, camera, 3 viewport screenshots, unchanged original game, zero orphan scenes')
    browser.close()
finally:
  server.shutdown()
  server.server_close()
