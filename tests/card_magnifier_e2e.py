"""Phase53 Chromium WebGL real public-card face magnifier, pinned detail and UI regression."""
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
    page.add_init_script('''() => {let seed=Number(new URLSearchParams(location.search).get('qa_seed'))||198704;Math.random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};}''')
    url=f'http://127.0.0.1:{server.server_port}/Marorong_Card_War_Phase54_3D_Prototype.html'
    affordable=[]
    for seed in range(198704,198728):
      page.goto(url+f'?qa_seed={seed}')
      page.locator('#newGame').click();page.locator('#launchGame').click()
      page.get_by_role('button',name='이 손패로 시작').click()
      choices=page.locator('.hand-slot').evaluate_all('''els=>els.map((e,i)=>({
        i,cost:Number(e.querySelector('.cost-bubble')?.textContent||99),
        unit:/type-(몬스터|시설|영웅유닛)/.test(e.querySelector('.card-ui')?.className||'')
      }))''')
      affordable=[x for x in choices if x['unit'] and x['cost']<=2]
      if affordable:break
    assert affordable,'No lawful card to place across deterministic openings'
    page.locator('.hand-slot').nth(affordable[0]['i']).evaluate('(e)=>e.click()')
    key=page.locator('#arena .slot.legal').first.get_attribute('data-slot')
    page.locator('#arena [data-slot="'+key+'"]').evaluate('(e)=>e.click()')
    snapshot=page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}''')
    page.locator('#mrr-battlefield-open').click()
    page.wait_for_function('MRRBattlefield.state.open && MRRBattlefield.state.scene.frames>3',timeout=19000)
    s=page.evaluate('MRRBattlefield.state.scene')
    assert s['previewRevision']==53 and s['previewReadyCards']>=1,s
    assert page.locator('#mrr-battlefield-stage canvas').count()==1
    assert page.locator('#arena .board-card').count()==1
    pt=page.evaluate('(key)=>MRRBattlefield.scene.projectCard(key)',key)
    visible=False
    for dx,dy in [(0,0),(0,-12),(-12,0),(12,0),(0,12),(-8,-8),(8,-8)]:
      page.mouse.move(pt['x']+dx,pt['y']+dy)
      page.wait_for_timeout(120)
      if page.locator('#mrr-battlefield-zoom-pane.visible img[src^="data:image/png;base64,"]').count()==1:
        visible=True
        break
    assert visible,'Hovering over public WebGL card must display the actual enlarged face'
    natural=page.locator('#mrr-battlefield-zoom-image').evaluate('(e)=>({w:e.naturalWidth,h:e.naturalHeight})')
    assert natural=={'w':512,'h':704},natural
    name=page.locator('#arena [data-slot="'+key+'"] .card-name').inner_text().strip()
    assert name in page.locator('#mrr-battlefield-zoom-caption').inner_text()
    assert page.evaluate('(key)=>MRRBattlefield.scene.getCardPreview(key).artData===document.querySelector("#mrr-battlefield-zoom-image").src',key)
    page.screenshot(path=str(ROOT/'tests/phase53_live_hover_card_zoom_fhd.png'))
    page.locator('#mrr-battlefield-preview-pin').click()
    assert page.locator('#mrr-battlefield-preview-pin').get_attribute('aria-pressed')=='true'
    assert page.locator('#mrr-battlefield-zoom-pane.visible').count()==1
    page.mouse.move(20,100)
    assert page.locator('#mrr-battlefield-zoom-pane.visible').count()==1,'Pin did not retain public card preview'
    assert page.evaluate('MRRBattlefield.state.scene.cardMeshCount')==1
    assert page.locator('#arena .board-card').count()==1
    assert snapshot==page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}'''),'Magnifier mutated original game'
    page.screenshot(path=str(ROOT/'tests/phase53_pinned_full_card_fhd.png'))
    for w,h in [(1366,768),(390,844)]:
      page.set_viewport_size({'width':w,'height':h})
      page.wait_for_timeout(650)
      assert page.locator('#mrr-battlefield-stage canvas').count()==1
      assert page.locator('#mrr-battlefield-zoom-pane.visible img').count()==1
      assert page.locator('#mrr-battlefield-zoom-image').evaluate('e=>e.naturalWidth===512&&e.naturalHeight===704')
      assert page.evaluate('MRRBattlefield.state.scene.cardMeshCount')==1
      page.screenshot(path=str(ROOT/f'tests/phase53_pinned_card_{w}x{h}.png'))
    page.locator('#mrr-battlefield-preview-pin').click()
    assert page.locator('#mrr-battlefield-preview-pin').get_attribute('aria-pressed')=='false'
    assert snapshot==page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}''')
    page.locator('#mrr-battlefield-close').click()
    assert page.evaluate('MRRBattlefield.scene===null')
    assert page.locator('#mrr-battlefield-zoom-pane').count()==0
    assert not errors,errors
    print('PHASE53 PASS: actual 512x704 public Three.js texture in zoom pane, hovered/pinned, preserved original field cards and native state, 3 viewport screenshots, modal teardown')
    browser.close()
finally:
  server.shutdown();server.server_close()
