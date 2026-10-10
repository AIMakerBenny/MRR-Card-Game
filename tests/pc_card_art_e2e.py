"""Phase57 PC-only illustrated tabletop, native state and screenshot QA."""
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
    opts={'headless':True,'args':['--no-sandbox','--enable-webgl',
      '--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']}
    if Path('/usr/bin/chromium').exists():opts['executable_path']='/usr/bin/chromium'
    browser=pw.chromium.launch(**opts)
    page=browser.new_page(viewport={'width':1920,'height':1080},device_scale_factor=1)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.add_init_script("""(() => {
      let seed=Number(new URLSearchParams(location.search).get('qa_seed'))||198704;
      Math.random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
    })();""")
    url=f'http://127.0.0.1:{server.server_port}/Marorong_Card_War_Phase57_3D_Prototype.html'
    affordable=[]
    for seed in range(198704,198745):
      page.goto(url+f'?qa_seed={seed}')
      page.locator('#newGame').click();page.locator('#launchGame').click()
      page.get_by_role('button',name='이 손패로 시작').click()
      hand=page.locator('.hand-slot').evaluate_all("""els=>els.map((e,i)=>({
        i,cost:Number(e.querySelector('.cost-bubble')?.textContent||99),
        board:/type-(몬스터|시설|영웅유닛)/.test(e.querySelector('.card-ui')?.className||'')
      }))""")
      affordable=[a for a in hand if a['board'] and a['cost']<=2]
      if affordable:break
    assert affordable,'Expected affordable public-card placement fixture'
    def snap():
      return page.evaluate("""() => {
        let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);
      }""")
    before=snap()
    page.locator('#mrr-integrated-open').click()
    page.wait_for_function("MRRIntegrated.state.open && MRRIntegrated.state.scene.frames>4",timeout=25000)
    state=page.evaluate('MRRIntegrated.state.scene')
    assert state['pcArtRevision']==57,state
    assert state['desktopArtRevision']==55 and state['slotCount']==30
    assert state['rendererAlive'] and state['cameraPreset']=='tabletop'
    assert snap()==before,'Opening decorative scene mutated native gameplay'
    page.locator('#hand .hand-slot').nth(affordable[0]['i']).evaluate('(e)=>e.click()')
    key=page.locator('#arena .slot.legal').first.get_attribute('data-slot')
    assert key
    xy=page.evaluate('(key)=>MRRIntegrated.scene.projectSlot(key)',key)
    assert xy and 0<xy['x']<1920 and 0<xy['y']<1080,xy
    page.mouse.click(xy['x'],xy['y'])
    page.wait_for_function("""key=>
      document.querySelector('#arena [data-slot="'+key+'"] .board-card')!==null""",
      arg=key,timeout=9000)
    assert snap()!=before,'Public 3D placement did not delegate to native engine'
    details=page.evaluate("""key=>{
      const item=MRRIntegrated.scene.getCardPreview(key);
      const layer=document.querySelector('#mrr-integrated-stage canvas');
      const data=item&&item.artData;
      if(!data)return null;
      return {dataLength:data.length,valid:data.startsWith('data:image/png;base64,'),
        name:item.name,kind:item.kind,stat:item.stats,
        inWorld:MRRIntegrated.scene.projectCard(key),
        canvasVisible:layer.getBoundingClientRect().width>600,
        pcArtRevision:MRRIntegrated.state.scene.pcArtRevision};
    }""",key)
    assert details and details['valid'] and details['dataLength']>11000,details
    assert details['inWorld'] and details['pcArtRevision']==57,details
    assert details['canvasVisible']
    after=snap()
    for w,h in [(1920,1080),(1366,768),(2560,1440)]:
      page.set_viewport_size({'width':w,'height':h})
      page.wait_for_timeout(420)
      assert page.locator('#endTurn').is_visible()
      assert page.evaluate('MRRIntegrated.state.scene.pcArtRevision')==57
      assert page.evaluate('MRRIntegrated.state.scene.publicCardCount')>=1
      assert page.locator('#hand .hand-slot').count()>0
      pt=page.evaluate('(key)=>MRRIntegrated.scene.projectSlot(key)',key)
      assert pt and 0<pt['x']<w and 0<pt['y']<h,pt
      actual=page.evaluate("""p=>{
        return !!document.elementFromPoint(p.x,p.y)?.closest('#mrr-integrated-stage')
      }""",pt)
      assert actual,('3D public card is occluded at resolution',w,h,pt)
      assert snap()==after,'Visual-only resize changed native game state'
      page.screenshot(path=str(ROOT/f'tests/phase57_pc_art_{w}x{h}.png'),animations='disabled')
    # Inspect source of truth, not a second card database, while preserving modal.
    page.locator('#mrr-integrated-exit').evaluate('(e)=>e.click()')
    assert page.evaluate('MRRIntegrated.scene===null')
    assert page.locator('#arena').is_visible()
    assert snap()==after
    assert not errors,errors
    browser.close()
    print('PHASE57 PC ART PASS: unique public canvas, dimensional frame, 30 original slots, real legal placement, FHD/1366/2K screenshots and legacy parity')
finally:
  server.shutdown();server.server_close()
