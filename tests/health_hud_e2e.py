"""Phase52 native public DOM HP and action-state 3D HUD Chromium QA."""
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
  with sync_playwright() as pw:
    opts={'headless':True,'args':['--no-sandbox','--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']}
    if Path('/usr/bin/chromium').exists():opts['executable_path']='/usr/bin/chromium'
    browser=pw.chromium.launch(**opts)
    page=browser.new_page(viewport={'width':1920,'height':1080})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.add_init_script('''() => {
      let seed=198704;Math.random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};
    }''')
    url=f'http://127.0.0.1:{server.server_port}/Marorong_Card_War_Phase52_3D_Prototype.html'
    page.goto(url)
    page.locator('#newGame').click();page.locator('#launchGame').click()
    page.get_by_role('button',name='이 손패로 시작').click()
    choices=page.locator('.hand-slot').evaluate_all('''els=>els.map((e,i)=>({
      i,cost:Number(e.querySelector('.cost-bubble')?.textContent||99),
      unit:/type-(몬스터|시설|영웅유닛)/.test(e.querySelector('.card-ui')?.className||'')
    }))''')
    affordable=[v for v in choices if v['unit'] and v['cost']<=2]
    assert affordable,'No affordable unit in seeded hand'
    page.locator('.hand-slot').nth(affordable[0]['i']).evaluate('(e)=>e.click()')
    key=page.locator('#arena .slot.legal').first.get_attribute('data-slot')
    page.locator('#arena [data-slot="'+key+'"]').evaluate('(e)=>e.click()')
    assert page.locator('#arena [data-slot="'+key+'"] .hpbar > div').count()==1
    snapshot=page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}''')
    page.locator('#mrr-battlefield-open').click()
    page.wait_for_function('MRRBattlefield.state.open && MRRBattlefield.state.scene.frames>3',timeout=20000)
    state=page.evaluate('MRRBattlefield.state.scene')
    assert state['healthHudRevision']==52,state
    assert state['healthIndicatorCount']==page.locator('#arena .board-card .hpbar').count(),state
    assert state['cardHealth'][key]['ratio']>0,state
    assert state['cardHealth'][key]['ratio']==1 or state['cardHealth'][key]['ratio']<1
    assert state['cardHealth'][key]['color'] in ['healthy','warning','danger']
    page.locator('#mrr-view-selected').is_visible()
    page.screenshot(path=str(ROOT/'tests/phase52_public_hp_3d_fhd.png'))
    for w,h in [(1366,768),(390,844)]:
      page.set_viewport_size({'width':w,'height':h})
      page.wait_for_timeout(550)
      assert page.evaluate('MRRBattlefield.state.scene.healthIndicatorCount')==page.locator('#arena .board-card .hpbar').count()
      assert page.evaluate('MRRBattlefield.state.scene.cardHealth')[key]['ratio']>0
      page.screenshot(path=str(ROOT/f'tests/phase52_public_hp_3d_{w}x{h}.png'))
    assert snapshot==page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}'''),'3D health HUD mutated game state'
    page.locator('#mrr-battlefield-close').click()
    assert not page.evaluate('MRRBattlefield.state.open')
    assert page.locator('#mrr-battlefield-stage canvas').count()==0
    assert not errors,errors
    print('PHASE52 PASS - real public HP overlay, native health count parity, 3 viewport renders, original snapshot unchanged')
    browser.close()
finally:
  server.shutdown();server.server_close()
