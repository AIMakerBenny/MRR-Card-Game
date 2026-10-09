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
url=f'http://127.0.0.1:{server.server_port}/Marorong_Card_War_Phase22_3D_Prototype.html'
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1920,'height':1080})
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
        page.screenshot(path=str(ROOT/'tests/webgl_1920x1080.png'))
        print('WEBGL RUNTIME PASS - local pinned Three.js, 30 mirrored slots, canvas and engine parity.')
        browser.close()
finally:
    server.shutdown();server.server_close()
