"""Phase53: real Chromium screenshots of unique drawn card archetypes and four 3D camera presets."""
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
    cfg={'headless':True,'args':['--no-sandbox','--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']}
    if Path('/usr/bin/chromium').exists():cfg['executable_path']='/usr/bin/chromium'
    browser=p.chromium.launch(**cfg)
    page=browser.new_page(viewport={'width':1920,'height':1080})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.add_init_script('''() => {
      let seed=Number(new URLSearchParams(location.search).get('qa_seed'))||198704;
      Math.random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};
    }''')
    base=f'http://127.0.0.1:{server.server_port}/Marorong_Card_War_Phase53_3D_Prototype.html'
    options=[]
    for seed in range(198704,198730):
      page.goto(base+f'?qa_seed={seed}')
      page.locator('#newGame').click();page.locator('#launchGame').click()
      page.get_by_role('button',name='이 손패로 시작').click()
      options=page.locator('.hand-slot').evaluate_all('''els=>els.map((e,i)=>({
        i,cost:Number(e.querySelector('.cost-bubble')?.textContent||99),
        board:/type-(몬스터|시설|영웅유닛)/.test(e.querySelector('.card-ui')?.className||'')
      })).filter(x=>x.board&&x.cost<=2)''')
      if options:break
    assert options
    page.locator('.hand-slot').nth(options[0]['i']).evaluate('(e)=>e.click()')
    loc=page.locator('#arena .slot.legal').first.get_attribute('data-slot')
    assert loc
    page.locator('#arena .slot.legal').first.evaluate('(e)=>e.click()')
    name=page.locator('#arena [data-slot="'+loc+'"] .card-name').inner_text().strip()
    original=page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}''')
    page.locator('#mrr-battlefield-open').click()
    page.wait_for_function('MRRBattlefield.state.open && MRRBattlefield.state.scene.frames>3',timeout=19000)
    s=page.evaluate('MRRBattlefield.state.scene')
    assert s['visualArtRevision']==51 and s['illustratedCards']>=1,s
    assert len(s['illustrationArchetypes'])==s['illustratedCards'],s
    assert s['illustrationArchetypes'][0] in ['fortress','ship','mage','archer','beast','warrior'],s
    assert s['cameraPreset']=='all'
    assert s['slotCount']==30 and s['pickableCount']>=30
    page.screenshot(path=str(ROOT/'tests/phase53_illustrated_3d_cards_fhd.png'))
    # Change real 3D camera presets using accessible DOM buttons.
    for preset,expectedZ in [('ally',5.6),('enemy',-5.6)]:
      page.locator('#mrr-view-'+preset).click()
      page.wait_for_function('(preset)=>MRRBattlefield.state.scene.cameraPreset===preset',arg=preset)
      state=page.evaluate('MRRBattlefield.state.scene')
      assert abs(state['focusZ']-expectedZ)<.01,state
      assert page.locator('#mrr-view-'+preset).get_attribute('aria-pressed')=='true'
      page.screenshot(path=str(ROOT/f'tests/phase53_camera_{preset}.png'))
    page.locator('#mrr-view-all').click()
    assert page.evaluate('MRRBattlefield.state.scene.distance')==29
    # Select a public card using its true WebGL projected coordinates.
    pt=page.evaluate('(key)=>MRRBattlefield.scene.projectCard(key)',loc)
    page.mouse.click(pt['x'],pt['y'])
    page.wait_for_function('(key)=>MRRBattlefield.state.scene.selectedKey===key',arg=loc,timeout=7000)
    page.locator('#mrr-view-selected').click()
    page.wait_for_function('MRRBattlefield.state.scene.cameraPreset==="selected"')
    focused=page.evaluate('MRRBattlefield.state.scene')
    assert focused['focusKey']==loc and focused['distance']==11.5
    assert page.locator('#mrr-view-selected').get_attribute('aria-pressed')=='true'
    assert page.evaluate('MRRBattlefield.state.scene.cardMeshCount')>=1
    page.screenshot(path=str(ROOT/'tests/phase53_selected_card_3d_closeup.png'))
    page.locator('#mrr-battlefield-reset').click()
    assert page.evaluate('MRRBattlefield.state.scene.cameraPreset')=='all'
    assert page.evaluate('MRRBattlefield.state.scene.focusX')==0
    assert original==page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}'''), 'Camera/art mutated engine'
    page.set_viewport_size({'width':390,'height':844})
    page.wait_for_timeout(450)
    assert page.locator('#mrr-battlefield-viewpoints button').count()==4
    assert page.evaluate('MRRBattlefield.state.scene.cardMeshCount')>=1
    assert page.locator('#mrr-battlefield-stage canvas').evaluate('e=>e.width>100 && e.height>100')
    page.screenshot(path=str(ROOT/'tests/phase53_mobile_illustrated_3d_battlefield.png'))
    page.locator('#mrr-battlefield-close').click()
    assert not page.evaluate('MRRBattlefield.state.open')
    assert page.evaluate('MRRBattlefield.scene===null')
    assert page.locator('#mrr-battlefield-stage canvas').count()==0
    assert not errors,errors
    print('PHASE51 PASS illustrated public-card archetypes, four camera presets, selected closeup, desktop/mobile WebGL, unchanged legacy state and renderer teardown',name)
    browser.close()
finally:
  server.shutdown();server.server_close()
