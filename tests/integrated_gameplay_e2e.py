"""Phase54 real Chromium native gameplay embedded inside the main 3D play surface.
The authoritative engine, hand and end-turn DOM must remain playable and unchanged.
"""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import threading
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
assert (ROOT/'vendor/three.module.js').exists()
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
  with sync_playwright() as pw:
    options={'headless':True,'args':['--no-sandbox','--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']}
    if Path('/usr/bin/chromium').exists():options['executable_path']='/usr/bin/chromium'
    browser=pw.chromium.launch(**options)
    page=browser.new_page(viewport={'width':1920,'height':1080})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.add_init_script("""(() => {
      let seed=Number(new URLSearchParams(location.search).get('qa_seed'))||198704;
      Math.random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};
    })();""")
    url=f'http://127.0.0.1:{server.server_port}/Marorong_Card_War_Phase55_3D_Prototype.html'
    affordable=[]
    for seed in range(198704,198730):
      page.goto(url+f'?qa_seed={seed}')
      page.locator('#newGame').click();page.locator('#launchGame').click()
      page.get_by_role('button',name='이 손패로 시작').click()
      options_in_hand=page.locator('.hand-slot').evaluate_all("""els=>els.map((e,i)=>({
        i,cost:Number(e.querySelector('.cost-bubble')?.textContent||99),
        board:/type-(몬스터|시설|영웅유닛)/.test(e.querySelector('.card-ui')?.className||'')
      }))""")
      affordable=[a for a in options_in_hand if a['board'] and a['cost']<=2]
      if affordable:break
    assert affordable,'No real native affordable field card available'
    native_hand=page.locator('#hand .hand-slot').count()
    baseline=page.evaluate("""() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}""")
    page.locator('#mrr-integrated-open').click()
    page.wait_for_function('MRRIntegrated.state.open && MRRIntegrated.state.scene.frames>3',timeout=22000)
    assert page.locator('#mrr-battlefield-modal').count()==0,'Integrated view must not be a modal'
    assert page.locator('#mrr-integrated-stage canvas').count()==1
    assert page.locator('#hand .hand-slot').count()==native_hand
    assert page.locator('#endTurn').count()==1 and page.locator('#enemyPortrait').count()==1
    assert page.evaluate("getComputedStyle(document.querySelector('#arena')).opacity")=='0'
    sizes=page.evaluate("""() => {
      const a=document.querySelector('#gameScreen').getBoundingClientRect();
      const b=document.querySelector('#mrr-integrated-stage').getBoundingClientRect();
      return [a.width,a.height,b.width,b.height];
    }""")
    assert abs(sizes[0]-sizes[2])<3 and abs(sizes[1]-sizes[3])<3,sizes
    assert page.evaluate('MRRIntegrated.state.scene.slotCount')==30
    assert page.evaluate('MRRIntegrated.state.scene.desktopArtRevision')==55
    assert page.evaluate('MRRIntegrated.state.scene.tabletopSurface')=='parchment-and-wood'
    assert page.evaluate('MRRIntegrated.state.scene.proceduralTextureCount')==2
    assert page.evaluate('MRRIntegrated.state.scene.cameraPreset')=='tabletop'
    assert page.locator('#mrr-integrated-stage canvas').evaluate('e=>e.width>600 && e.height>500')
    assert page.evaluate('MRRIntegrated.state.nativeEndTurn')
    assert baseline==page.evaluate("""() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}"""),'Just opening 3D altered the game'
    page.screenshot(path=str(ROOT/'tests/phase54_integrated_main_screen_fhd.png'))
    # Native HTML hand remains the sole authoritative hand interaction.
    page.locator('#hand .hand-slot').nth(affordable[0]['i']).evaluate('(e)=>e.click()')
    legal=page.locator('#arena .slot.legal')
    assert legal.count()>0
    key=legal.first.get_attribute('data-slot')
    pt=page.evaluate('(key)=>MRRIntegrated.scene.projectSlot(key)',key)
    assert pt and 0<pt['x']<1920 and 0<pt['y']<1080,pt
    page.mouse.click(pt['x'],pt['y'])
    page.wait_for_function('(key)=>document.querySelector(\'#arena [data-slot="'+key+'"] .board-card\')!==null',arg=key,timeout=8000)
    assert page.locator('#hand .hand-slot').count()==native_hand-1
    assert page.locator('#arena .board-card').count()==1
    assert page.evaluate('MRRIntegrated.state.scene.publicCardCount')==1
    after=page.evaluate("""() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}""")
    assert after!=baseline,'Real native placement did not change game state'
    assert page.locator('#mrr-battlefield-modal').count()==0
    page.screenshot(path=str(ROOT/'tests/phase54_integrated_native_placement_fhd.png'))
    # Native inspector and native resource actions only show on demand.
    page.locator('#mrr-integrated-inspector').click()
    assert page.locator('#inspector').is_visible()
    page.locator('#mrr-integrated-inspector').click()
    assert not page.locator('#inspector').is_visible()
    page.locator('#mrr-integrated-rail').click()
    assert page.locator('#areaRail').is_visible()
    page.locator('#mrr-integrated-rail').click()
    assert not page.locator('#areaRail').is_visible()
    # Verify the native end-turn control remains above the WebGL canvas.
    assert page.locator('#endTurn').is_visible()
    # Resize while still using the in-game surface; no lost engine state.
    for w,h in [(1366,768),(2560,1440)]:
      page.set_viewport_size({'width':w,'height':h})
      page.wait_for_timeout(350)
      assert page.locator('#mrr-integrated-stage canvas').evaluate('e=>e.width>200 && e.height>200')
      assert page.locator('#hand .hand-slot').count()==native_hand-1
      assert page.locator('#endTurn').is_visible()
      page.screenshot(path=str(ROOT/f'tests/phase54_integrated_main_screen_{w}x{h}.png'))
    page.locator('#mrr-integrated-exit').evaluate('(e)=>e.click()')
    assert not page.evaluate('MRRIntegrated.state.open')
    assert page.locator('#mrr-integrated-stage canvas').count()==0
    assert not page.evaluate("document.body.classList.contains('mrr-integrated-active')")
    assert after==page.evaluate("""() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}"""),'Closing integrated graphics mutated game'
    assert page.locator('#arena').is_visible(),'Native board did not return'
    assert not errors,errors
    browser.close()
    print('PHASE54 PASS: in-game WebGL, same native hand/end-turn and engine, legal real 3D placement, no modal, native optional drawers, FHD/compact/2K desktop screenshots, teardown parity')
finally:
  server.shutdown()
