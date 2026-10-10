"""Phase55 actual desktop-only Chromium visual QA for the in-game parchment table.
Only checks public board data; all native game rules and state remain unchanged.
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
  with sync_playwright() as pw:
    opts={'headless':True,'args':['--no-sandbox','--enable-webgl','--use-gl=angle',
      '--use-angle=swiftshader','--enable-unsafe-swiftshader']}
    if Path('/usr/bin/chromium').exists():opts['executable_path']='/usr/bin/chromium'
    browser=pw.chromium.launch(**opts)
    page=browser.new_page(viewport={'width':1920,'height':1080},device_scale_factor=1)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.add_init_script("""(() => {
      let seed=Number(new URLSearchParams(location.search).get('qa_seed'))||198704;
      Math.random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
    })();""")
    base=f'http://127.0.0.1:{server.server_port}/Marorong_Card_War_Phase55_3D_Prototype.html'
    affordable=[]
    for seed in range(198704,198745):
      page.goto(base+f'?qa_seed={seed}')
      page.locator('#newGame').click();page.locator('#launchGame').click()
      page.get_by_role('button',name='이 손패로 시작').click()
      hand=page.locator('.hand-slot').evaluate_all("""els=>els.map((e,i)=>({
        i,cost:Number(e.querySelector('.cost-bubble')?.textContent||99),
        board:/type-(몬스터|시설|영웅유닛)/.test(e.querySelector('.card-ui')?.className||'')
      }))""")
      affordable=[a for a in hand if a['board'] and a['cost']<=2]
      if affordable:break
    assert affordable
    before=page.evaluate("""() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}""")
    page.locator('#mrr-integrated-open').click()
    page.wait_for_function('MRRIntegrated.state.open && MRRIntegrated.state.scene.frames>4',timeout=25000)
    state=page.evaluate('MRRIntegrated.state.scene')
    assert state['desktopArtRevision']==55,state
    assert state['tabletopSurface']=='parchment-and-wood',state
    assert state['proceduralTextureCount']==2,state
    assert state['cameraPreset']=='tabletop' and state['pitch']>1.1,state
    assert state['slotCount']==30 and state['shadows'] and state['rendererAlive'],state
    assert page.evaluate("getComputedStyle(document.querySelector('#arena')).opacity")=='0'
    assert page.locator('#mrr-integrated-stage canvas').count()==1
    assert page.locator('#mrr-battlefield-modal').count()==0
    assert before==page.evaluate("""() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}""")
    page.wait_for_timeout(500)
    page.screenshot(path=str(ROOT/'tests/phase55_desktop_parchment_fhd_empty.png'))
    page.locator('#hand .hand-slot').nth(affordable[0]['i']).evaluate('(e)=>e.click()')
    key=page.locator('#arena .slot.legal').first.get_attribute('data-slot')
    assert key
    pt=page.evaluate('(key)=>MRRIntegrated.scene.projectSlot(key)',key)
    assert pt and 0<pt['x']<1920 and 0<pt['y']<1080,pt
    page.mouse.click(pt['x'],pt['y'])
    page.wait_for_function('(key)=>document.querySelector(\'#arena [data-slot="'+key+'"] .board-card\')!==null',arg=key,timeout=9000)
    assert page.evaluate('MRRIntegrated.state.scene.publicCardCount')>=1
    page.wait_for_timeout(400)
    page.screenshot(path=str(ROOT/'tests/phase55_desktop_parchment_fhd_card.png'))
    after=page.evaluate("""() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}""")
    assert before!=after,'Legal native placement did not advance the game'
    # PC-only targets. No new phone layouts, handset capture or phone QA.
    for w,h in [(1366,768),(2560,1440)]:
      page.set_viewport_size({'width':w,'height':h})
      page.wait_for_timeout(450)
      assert page.evaluate('MRRIntegrated.state.scene.desktopArtRevision')==55
      assert page.locator('#mrr-integrated-stage canvas').evaluate('e=>e.width>500 && e.height>400')
      assert page.locator('#endTurn').is_visible()
      assert page.locator('#hand .hand-slot').count()>0
      page.screenshot(path=str(ROOT/f'tests/phase55_desktop_parchment_{w}x{h}.png'))
    assert after==page.evaluate("""() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}"""),'Visual layout changed native engine'
    page.locator('#mrr-integrated-exit').evaluate('(e)=>e.click()')
    assert page.evaluate('MRRIntegrated.scene===null')
    assert page.locator('#mrr-integrated-stage canvas').count()==0
    assert page.locator('#arena').is_visible()
    assert not errors,errors
    browser.close()
    print('PHASE55 DESKTOP TABLETOP PASS: 2 GPU-managed parchment/wood textures, natural lighting, tabletop PC camera, real card placement, FHD/1366/2K Chromium images, legacy state parity')
finally:
  server.shutdown();server.server_close()
