"""Phase63: actual PC contextual actions and 3-resolution gameplay regression."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
import threading
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
  with sync_playwright() as pw:
    opts={'headless':True,'args':['--no-sandbox','--enable-webgl','--use-gl=angle',
      '--use-angle=swiftshader','--enable-unsafe-swiftshader']}
    if Path('/usr/bin/chromium').exists():opts['executable_path']='/usr/bin/chromium'
    browser=pw.chromium.launch(**opts)
    page=browser.new_page(viewport={'width':1920,'height':1080})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.add_init_script("""(() => {
      let seed=Number(new URLSearchParams(location.search).get('qa_seed'))||198708;
      Math.random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
    })();""")
    url=f'http://127.0.0.1:{server.server_port}/Marorong_Card_War_Phase63_3D_Prototype.html'
    page.goto(url+'?qa_seed=198708')
    page.locator('#newGame').click()
    page.locator('#modeSelect').select_option('local')
    page.locator('#launchGame').click()
    page.get_by_role('button',name='이 손패로 시작').click()
    def affordable():
      return page.locator('.hand-slot').evaluate_all("""els=>els.map((e,i)=>{
        const c=e.querySelector('.card-ui'),kind=c?.querySelector('.card-kind')?.textContent||'';
        const stats=c?.querySelector('.card-stats')?.textContent||'';
        return {i,attack:Number(stats.match(/[검공]\s*(\d+)/)?.[1]||0),
          cost:Number(c?.querySelector('.cost-bubble')?.textContent||99),
          unit:/몬스터/.test(kind)};
      }).filter(x=>x.unit && x.attack>0 && x.cost<=2)""")
    def set_unit(side):
      units=affordable()
      assert units,('No affordable unit',side)
      page.locator('.hand-slot').nth(units[0]['i']).evaluate('e=>e.click()')
      key=page.locator(f'#arena [data-slot^="{side}:front:"].legal').first.get_attribute('data-slot')
      assert key
      page.locator('#arena [data-slot="'+key+'"]').evaluate('e=>e.click()')
      assert page.locator('#arena [data-slot="'+key+'"] .board-card').count()==1
      return key
    my_key=set_unit(0)
    page.locator('#turnDock #endTurn').evaluate('e=>e.click()')
    page.wait_for_selector('#passContinue')
    page.locator('#passContinue').click()
    their_key=set_unit(1)
    page.locator('#turnDock #endTurn').evaluate('e=>e.click()')
    page.wait_for_selector('#passContinue')
    page.locator('#passContinue').click()
    assert page.evaluate('G.current===0 && G.players[0].turns>1')
    page.locator('#mrr-integrated-open').click()
    page.wait_for_function('MRRIntegrated.state.open && MRRIntegrated.state.scene.frames>3',timeout=25000)
    assert page.locator('#mrr-integrated-context').count()==1
    # No new gameplay action until the native deployed card is selected.
    before=page.evaluate("""() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);}""")
    target=page.evaluate('(key)=>MRRIntegrated.scene.projectCard(key)',my_key)
    assert target and 0<target['x']<1920 and 0<target['y']<1080,target
    page.mouse.click(target['x'],target['y'])
    page.wait_for_function('MRRIntegrated.state.scene.selectedKey!==null',timeout=7000)
    assert page.evaluate("""() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);}""")==before
    # Player receives an attack command near the actual selected 3D unit.
    page.wait_for_function("""()=>!document.querySelector('#mrr-integrated-context')?.hidden""",timeout=7000)
    assert page.locator('#mrr-quick-attack').is_visible()
    assert not page.locator('#mrr-integrated-attack').is_disabled()
    for w,h in ((1920,1080),(1366,768),(2560,1440)):
      page.set_viewport_size({'width':w,'height':h})
      page.wait_for_timeout(330)
      context=page.locator('#mrr-integrated-context')
      assert context.is_visible(),(w,h)
      rect=context.bounding_box()
      assert rect and rect['x']>=0 and rect['x']+rect['width']<=w and rect['y']>=0 and rect['y']+rect['height']<=h,(w,h,rect)
      page.screenshot(path=str(ROOT/f'tests/phase63_context_{w}x{h}.png'))
    page.set_viewport_size({'width':1920,'height':1080})
    page.wait_for_timeout(200)
    initial_hp=page.evaluate("""key=>{
      const [owner,row,col]=key.split(':');
      return G.players[+owner][row][+col]?.hp;
    }""",their_key)
    assert initial_hp and initial_hp>0
    page.evaluate('(hp)=>window.__initial_hp=hp',initial_hp)
    page.locator('#mrr-quick-attack').click()
    page.wait_for_function('MRRIntegrated.state.scene.attackTargetCount>0',timeout=7000)
    assert page.locator('#arena [data-slot="'+their_key+'"].attack-target').count()==1
    enemy=page.evaluate('(key)=>MRRIntegrated.scene.projectCard(key)',their_key)
    assert enemy and 0<enemy['x']<1920 and 0<enemy['y']<1080
    page.mouse.click(enemy['x'],enemy['y'])
    page.wait_for_function("""key=>{
      const [owner,row,col]=key.split(':');
      return (G.players[+owner][row][+col]?.hp||0)<window.__initial_hp;
    }""",arg=their_key,timeout=9000)
    assert page.evaluate('G.players[0].front.some(c=>c?.acted)')
    assert not errors,errors
    page.locator('#mrr-integrated-exit').evaluate('e=>e.click()')
    assert page.evaluate('MRRIntegrated.scene===null')
    browser.close()
    print('PHASE63 PC CONTEXT PASS: native delegated 3D commands, actual HP damage, 3 resolutions and game state parity')
finally:
  server.shutdown();server.server_close()
