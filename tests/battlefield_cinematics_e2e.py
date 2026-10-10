"""Phase49 real Chromium WebGL cinematic feedback and strictly gated attack visuals.

Lawful native summon is real gameplay. The staged strike hit is explicitly a
visual-signal fixture: staging alone must not produce a successful attack,
damage, hit animation or game-state change.
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
    page=browser.new_page(viewport={'width':1920,'height':1080})
    errors=[];page.on('pageerror',lambda exc:errors.append(str(exc)))
    page.add_init_script('''() => {
      let seed=Number(new URLSearchParams(location.search).get('qa_seed'))||198704;
      Math.random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};
    }''')
    url=f'http://127.0.0.1:{server.server_port}/Marorong_Card_War_Phase51_3D_Prototype.html'
    affordable=[]
    for seed in range(198704,198728):
      page.goto(url+f'?qa_seed={seed}')
      page.locator('#newGame').click();page.locator('#launchGame').click()
      page.get_by_role('button',name='이 손패로 시작').click()
      opts=page.locator('.hand-slot').evaluate_all('''els=>els.map((e,i)=>({
        i,cost:Number(e.querySelector('.cost-bubble')?.textContent||99),
        board:/type-(몬스터|시설|영웅유닛)/.test(e.querySelector('.card-ui')?.className||'')
      }))''')
      affordable=[x for x in opts if x['board'] and x['cost']<=2]
      if affordable:break
    assert affordable
    page.locator('.hand-slot').nth(affordable[0]['i']).evaluate('(e)=>e.click()')
    target=page.locator('#arena .slot.legal').first.get_attribute('data-slot')
    assert target
    page.locator('#mrr-battlefield-open').click()
    page.wait_for_function('MRRBattlefield.state.open && MRRBattlefield.state.scene.frames>3',timeout=20000)
    state=page.evaluate('MRRBattlefield.state.scene')
    assert state['revision']==49 and state['cinematicRevision']==49,state
    assert state['confirmedStrikes']==0 and not state['stagedStrike'],state
    pt=page.evaluate('(key)=>MRRBattlefield.scene.projectSlot(key)',target)
    page.mouse.click(pt['x'],pt['y'])
    page.wait_for_function('MRRBattlefield.state.scene.fxReceived.summon>=1',timeout=8000)
    assert page.locator('#arena [data-slot="'+target+'"] .board-card').count()==1
    page.wait_for_function("document.querySelector('#mrr-battlefield-combat-feed')?.textContent.includes('소환')")
    assert page.evaluate('MRRBattlefield.state.scene.confirmedStrikes')==0
    page.wait_for_timeout(130)
    page.screenshot(path=str(ROOT/'tests/phase49_real_native_summon_cinematic.png'))
    page.wait_for_function('MRRBattlefield.state.scene.liveFxCount===0',timeout=7000)
    before=page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}''')
    # Test the combat path exclusively as a native visual-signal fixture.
    source='0:front:4' if target!='0:front:4' else '0:front:3'
    assert page.evaluate('([src,dst])=>MRRBattlefield.scene.stageAttack(src,dst)',[source,target])
    assert page.evaluate('MRRBattlefield.state.scene.stagedStrike')
    assert page.evaluate('MRRBattlefield.state.scene.confirmedStrikes')==0
    assert page.evaluate('MRRBattlefield.state.scene.liveStrikeCount')==0
    assert before==page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}''')
    # visual() is the unchanged original engine's event-emitting helper, not
    # an attack resolution. The resulting FX must be clearly gated.
    page.evaluate('''key => {const [o,row,c]=key.split(':'); visual('hit',Number(o),row,Number(c));}''',target)
    # The banner is intentionally transient: observe its activation immediately
    # after the native signal, before later GPU-frame assertions can outlive it.
    page.wait_for_function("document.querySelector('#mrr-battlefield-combat-feed.active')?.dataset.kind==='hit'",timeout=7000)
    page.wait_for_function('MRRBattlefield.state.scene.confirmedStrikes===1',timeout=7000)
    page.wait_for_function('MRRBattlefield.state.scene.liveStrikeCount>=1',timeout=7000)
    page.wait_for_function('MRRBattlefield.state.scene.cinematicFrameCount>=1',timeout=7000)
    assert page.evaluate('MRRBattlefield.state.scene.fxReceived.hit')>=1
    assert page.locator('#mrr-battlefield-combat-feed[data-kind="hit"]').count()==1
    assert '피격' in page.locator('#mrr-battlefield-combat-feed').inner_text()
    page.screenshot(path=str(ROOT/'tests/phase49_confirmed_native_hit_signal_beam.png'))
    page.wait_for_function('MRRBattlefield.state.scene.liveStrikeCount===0',timeout=7000)
    page.wait_for_function('MRRBattlefield.state.scene.impactLightIntensity===0',timeout=7000)
    assert before==page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}''')
    page.set_viewport_size({'width':390,'height':844})
    page.wait_for_timeout(300)
    assert page.locator('#mrr-battlefield-stage canvas').evaluate('e=>e.width>100 && e.height>100')
    page.screenshot(path=str(ROOT/'tests/phase49_mobile_game_cinematic.png'))
    page.locator('#mrr-battlefield-close').click()
    assert not page.evaluate('MRRBattlefield.state.open')
    assert page.evaluate('MRRBattlefield.scene===null')
    assert page.locator('#mrr-battlefield-combat-feed').count()==0
    assert not errors,errors
    print('PHASE49 PASS - real summon HUD, gated visual-signal-only strike, GPU beam and camera/light pulse, full teardown and state parity across desktop/mobile')
    browser.close()
finally:
  server.shutdown();server.server_close()
