"""CI-only strict WebGL test. Requires npm vendor and a normal localhost browser.

This test is NOT claimed as passed in the initial environment, which blocks
Chromium navigation and fetching of the pinned Three.js dependency.
"""
from pathlib import Path
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
assert (ROOT/'vendor/three.module.js').exists(), 'Three.js is not vendored: run npm install and npm run vendor'
handler=partial(SimpleHTTPRequestHandler,directory=str(ROOT))
server=ThreadingHTTPServer(('127.0.0.1',0),handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}/Marorong_Card_War_Phase23_3D_Prototype.html'
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1920,'height':1080})
        # Reproducible opening hand, same seed as the existing placement smoke test.
        page.add_init_script('''() => {let seed=198704;Math.random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};}''')
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(url,wait_until='domcontentloaded')
        page.locator('#newGame').click();page.locator('#launchGame').click()
        page.get_by_role('button',name='이 손패로 시작').click()
        before=page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);}''')
        page.locator('#mcw3d-toggle').click()
        page.wait_for_function('window.MCW3D?.status.renderer === "three"',timeout=18000)
        page.wait_for_function('window.MCW3D.scene?.state.slotCount === 30',timeout=9000)
        assert page.locator('#mcw3d-canvas-host canvas').count()==1
        assert page.locator('#mcw3d-canvas-host canvas').evaluate('e=>e.width>300 && e.height>200')
        after=page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);}''')
        assert before==after, 'Three scene mutated game state'
        assert not errors,errors
        # Use normal game commands to place a card, then check the actual
        # WebGL focus state. No test mutates the game's rules or hand directly.
        options=page.locator('.hand-slot').evaluate_all('''els=>els.map((e,i)=>({index:i,cost:Number(e.querySelector('.cost-bubble')?.textContent||99),isBoardCard:/type-(몬스터|시설|영웅유닛)/.test(e.querySelector('.card-ui')?.className||'')}))''')
        legal=[x for x in options if x['isBoardCard'] and x['cost']<=2]
        assert legal,'Cannot test focus: no affordable field card'
        page.locator('.hand-slot').nth(legal[0]['index']).evaluate('(el)=>el.click()')
        targets=page.locator('.slot.legal')
        assert targets.count()>0,'No legal target for normal placement'
        targets.first.evaluate('(el)=>el.click()')
        page.wait_for_function('MCW3D.scene.state.cardCount === 1',timeout=8000)
        before_focus=page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);}''')
        # Newly placed cards may remain selected. Their idle height is 10,
        # whereas a true hover must raise only that card to height 18.
        idle_target=page.evaluate('MCW3D.scene.state.maxTargetLift')
        assert idle_target in (0,10),f'Unexpected idle focus lift: {idle_target}'
        node=page.locator('.slot:has(.board-card)').first
        node.hover()
        page.wait_for_function('MCW3D.scene.state.hoveredCardCount === 1 && MCW3D.scene.state.maxTargetLift === 18 && MCW3D.scene.state.maxLift > 15',timeout=8000)
        assert page.locator('[data-slot]').count()==30
        assert page.locator('.board-card').count()==1
        page.screenshot(path=str(ROOT/'tests/webgl_phase23_hover.png'))
        page.mouse.move(0,0)
        page.wait_for_function('''idle => MCW3D.scene.state.hoveredCardCount === 0 && MCW3D.scene.state.maxTargetLift === idle && MCW3D.scene.state.maxLift <= idle+1''',arg=idle_target,timeout=8000)
        after_focus=page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);}''')
        assert before_focus==after_focus,'Hover changed the game state'
        page.screenshot(path=str(ROOT/'tests/webgl_1920x1080.png'))
        print('WEBGL PHASE23 PASS - local Three.js, 30 slots, hover lift, return, game state unchanged.')
        browser.close()
finally:
    server.shutdown();server.server_close()
