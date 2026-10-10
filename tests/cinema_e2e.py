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
    page.add_init_script('''() => {
      let seed=Number(new URLSearchParams(location.search).get('qa_seed'))||198704;
      Math.random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};
    }''')
    url=f'http://127.0.0.1:{server.server_port}/Marorong_Card_War_Phase39_3D_Prototype.html'
    legal=[]
    for seed in range(198704,198728):
      page.goto(url+f'?qa_seed={seed}')
      page.locator('#newGame').click();page.locator('#launchGame').click()
      page.get_by_role('button',name='이 손패로 시작').click()
      choices=page.locator('.hand-slot').evaluate_all('''els=>els.map((e,i)=>({index:i,cost:Number(e.querySelector('.cost-bubble')?.textContent||99),
        board:/type-(몬스터|시설|영웅유닛)/.test(e.querySelector('.card-ui')?.className||'')}))''')
      legal=[c for c in choices if c['board'] and c['cost']<=2]
      if legal:break
    assert legal,'Could not find legal public card placement in 24 seeded openings'
    page.locator('.hand-slot').nth(legal[0]['index']).evaluate('(el)=>el.click()')
    slots=page.locator('.slot.legal')
    assert slots.count()>0
    slots.first.evaluate('(el)=>el.click()')
    assert page.locator('#arena .board-card').count()>0
    expected=page.locator('#arena .board-card .card-name').first.inner_text().strip()
    before=page.evaluate('''()=>{let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}''')
    page.locator('#mcw-cinema-open').click()
    page.wait_for_function('MRRCinema.status.open && MRRCinema.scene.state.frameCount>4',timeout=15000)
    state=page.evaluate('MRRCinema.scene.state')
    assert state['projection']=='PerspectiveCamera' and state['hasCanvas'] and state['meshes']>=8,state
    assert state['stageRevision']==38 and state['stageMeshCount']>=20 and state['castShadows'] and state['lightCount']>=5,state
    assert state['cardBindingRevision']==39 and state['profile']['name']==expected,(state,expected)
    assert page.evaluate('MRRCinema.status.publicCardCount')>=1
    assert expected in page.locator('#mcw-cinema-current').inner_text()
    assert page.locator('#mcw-cinema-next').count()==1
    assert page.locator('#mcw-cinema-prev').count()==1
    assert page.locator('#mcw-cinema-stage canvas').count()==1
    assert page.locator('[data-slot]').count()==30
    assert not errors,errors
    page.screenshot(path=str(ROOT/'tests/phase39_live_card.png'))
    page.set_viewport_size({'width':390,'height':844})
    page.wait_for_timeout(500)
    assert page.locator('#mcw-cinema-stage canvas').evaluate('e=>e.width>100 && e.height>100')
    page.screenshot(path=str(ROOT/'tests/phase39_live_card_mobile.png'))
    page.set_viewport_size({'width':1600,'height':900})
    page.locator('#mcw-cinema-close').click()
    page.wait_for_function("!MRRCinema.status.open",timeout=6000)
    assert page.locator('#mcw-cinema-view').count()==0
    assert before==page.evaluate('''()=>{let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}''')
    assert not errors,errors
    print('PHASE39 CINEMATIC PASS - live public field card, actual perspective WebGL, resize and state parity.')
    browser.close()
finally:
  server.shutdown();server.server_close()
