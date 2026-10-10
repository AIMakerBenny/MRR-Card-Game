from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
import threading
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
assert (ROOT/'vendor/three.module.js').exists(),'Need local pinned Three module'
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
  with sync_playwright() as p:
    options={'headless':True,'args':['--no-sandbox','--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']}
    if Path('/usr/bin/chromium').exists():options['executable_path']='/usr/bin/chromium'
    browser=p.chromium.launch(**options)
    page=browser.new_page(viewport={'width':1600,'height':900})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{server.server_port}/Marorong_Card_War_Phase38_3D_Prototype.html')
    page.locator('#newGame').click();page.locator('#launchGame').click()
    page.get_by_role('button',name='이 손패로 시작').click()
    before=page.evaluate('''()=>{let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}''')
    page.locator('#mcw-cinema-open').click()
    page.wait_for_function('MRRCinema.status.open && MRRCinema.scene.state.frameCount>4',timeout=15000)
    state=page.evaluate('MRRCinema.scene.state')
    assert state['projection']=='PerspectiveCamera' and state['hasCanvas'] and state['meshes']>=8,state
    assert state['stageRevision']==38 and state['stageMeshCount']>=20 and state['castShadows'] and state['lightCount']>=5,state
    assert page.locator('#mcw-cinema-stage canvas').count()==1
    assert page.locator('[data-slot]').count()==30
    assert not errors,errors
    page.screenshot(path=str(ROOT/'tests/phase37_cinematic.png'))
    page.locator('#mcw-cinema-close').click()
    page.wait_for_function("!MRRCinema.status.open",timeout=6000)
    assert page.locator('#mcw-cinema-view').count()==0
    assert before==page.evaluate('''()=>{let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}''')
    assert not errors,errors
    print('PHASE37 CINEMATIC PASS - real perspective WebGL scene, modal return, game snapshot unchanged.')
    browser.close()
finally:
  server.shutdown();server.server_close()
