"""Phase70: static native-slot command anchor, real Chromium WebGL and attack."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import threading
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
http=ThreadingHTTPServer(('127.0.0.1',0),
    partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=http.serve_forever,daemon=True).start()
try:
  with sync_playwright() as pw:
    args=['--no-sandbox','--enable-webgl','--use-gl=angle',
          '--use-angle=swiftshader','--enable-unsafe-swiftshader']
    opts={'headless':True,'args':args}
    if Path('/usr/bin/chromium').exists():opts['executable_path']='/usr/bin/chromium'
    browser=pw.chromium.launch(**opts)
    page=browser.new_page(viewport={'width':1920,'height':1080})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.add_init_script("""(() => {
      let seed=Number(new URLSearchParams(location.search).get('qa_seed'))||198704;
      Math.random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;
        return seed/4294967296;};
    })();""")
    url=f'http://127.0.0.1:{http.server_port}/Marorong_Card_War_Phase70_3D_Prototype.html'
    def set_unit(side):
      cards=page.locator('.hand-slot').evaluate_all("""els=>els.map((e,i)=>{
        const c=e.querySelector('.card-ui');
        const kind=c?.querySelector('.card-kind')?.textContent||'';
        const stats=c?.querySelector('.card-stats')?.textContent||'';
        return {i,atk:Number(stats.match(/[검공]\s*(\d+)/)?.[1]||0),
          cost:Number(c?.querySelector('.cost-bubble')?.textContent||99),
          unit:/몬스터/.test(kind)};
      }).filter(x=>x.unit&&x.atk>0&&x.cost<=2)""")
      for c in cards:
        page.locator('.hand-slot').nth(c['i']).evaluate('e=>e.click()')
        front=page.locator(f'#arena [data-slot^="{side}:front:"].legal')
        if not front.count():continue
        key=front.first.get_attribute('data-slot')
        front.first.evaluate('e=>e.click()')
        return key
      return None
    my_key=their_key=None
    for seed in range(198704,198780):
      page.goto(url+f'?qa_seed={seed}',wait_until='domcontentloaded')
      page.locator('#newGame').click()
      page.locator('#modeSelect').select_option('local')
      page.locator('#launchGame').click()
      page.get_by_role('button',name='이 손패로 시작').click()
      my_key=set_unit(0)
      if not my_key:continue
      page.locator('#endTurn').evaluate('e=>e.click()')
      page.wait_for_selector('#passContinue')
      page.locator('#passContinue').click()
      their_key=set_unit(1)
      if not their_key:continue
      page.locator('#endTurn').evaluate('e=>e.click()')
      page.wait_for_selector('#passContinue')
      page.locator('#passContinue').click()
      break
    assert my_key and their_key,'Cannot prepare two real native units'
    def snap():
      return page.evaluate("""() => {
        const s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);
      }""")
    native=snap()
    page.locator('#mrr-integrated-open').click()
    page.wait_for_function('MRRIntegrated.state.open && MRRIntegrated.state.scene.frames>7',
                           timeout=25000)
    assert snap()==native and page.evaluate('MRRIntegrated.state.scene.pcZoneContrastRevision')==69
    me=page.evaluate('(key)=>MRRIntegrated.scene.projectCard(key)',my_key)
    page.mouse.click(me['x'],me['y'])
    page.wait_for_function("""()=>MRRIntegrated.state.scene.selectedKey!==null
      && !document.querySelector('#mrr-integrated-context').hidden""",timeout=10000)
    assert snap()==native
    for w,h in ((1920,1080),(1366,768),(2560,1440)):
      page.set_viewport_size({'width':w,'height':h})
      page.mouse.move(5,h//2)
      page.wait_for_timeout(600)
      me=page.evaluate('(key)=>MRRIntegrated.scene.projectCard(key)',my_key)
      assert me and 0<me['x']<w and 0<me['y']<h
      page.mouse.move(me['x'],me['y'])
      page.wait_for_function("""k=>MRRIntegrated.state.scene.hoveredKey===k""",
                             arg=my_key,timeout=12000)
      sampled=page.evaluate("""() => new Promise(resolve=>{
        const el=document.querySelector('#mrr-integrated-context');
        const data=[];
        function read(){
          const r=el.getBoundingClientRect();
          data.push({x:r.left,y:r.top,width:r.width,height:r.height,
            hidden:el.hidden});
          if(data.length<12)requestAnimationFrame(read);
          else resolve(data);
        }
        requestAnimationFrame(read);
      })""")
      assert all(not p['hidden'] and p['width']>50 and p['height']>20 for p in sampled)
      drift_x=max(p['x'] for p in sampled)-min(p['x'] for p in sampled)
      drift_y=max(p['y'] for p in sampled)-min(p['y'] for p in sampled)
      assert drift_x<=2.5 and drift_y<=2.5,(w,h,sampled)
      r=sampled[-1]
      assert 0<=r['x'] and r['x']+r['width']<=w and r['y']>=0 and r['y']+r['height']<=h
      assert snap()==native,'Card hover/command should not mutate gameplay'
      page.screenshot(path=str(ROOT/f'tests/phase70_stable_context_{w}x{h}.png'),
        animations='disabled')
      print('PHASE70',w,h,'context drift',round(drift_x,2),round(drift_y,2),
            flush=True)
    page.set_viewport_size({'width':1920,'height':1080})
    page.mouse.move(5,550)
    page.wait_for_timeout(450)
    hp=page.evaluate("""key=>{
      const [owner,row,col]=key.split(':');
      return G.players[+owner][row][+col]?.hp;
    }""",their_key)
    assert hp and hp>0
    # Actual mouse click, never direct native dispatch or a fake health edit.
    page.locator('#mrr-quick-attack').click(timeout=12000)
    page.wait_for_function('MRRIntegrated.state.scene.attackTargetCount>0',
                           timeout=9000)
    assert page.locator('#arena [data-slot="'+their_key+'"].attack-target').count()==1
    enemy=page.evaluate('(key)=>MRRIntegrated.scene.projectCard(key)',their_key)
    page.mouse.click(enemy['x'],enemy['y'])
    page.wait_for_function("""o=>{
      const [owner,row,col]=o.key.split(':');
      return (G.players[+owner][row][+col]?.hp||0)<o.hp;
    }""",arg={'key':their_key,'hp':hp},timeout=9000)
    before_exit=snap()
    page.locator('#mrr-integrated-exit').evaluate('e=>e.click()')
    assert page.evaluate('MRRIntegrated.scene===null')
    assert page.locator('#arena').is_visible() and snap()==before_exit
    assert not errors,errors
    browser.close()
    print('PHASE70 PASS: anchored real native command stable at three PC sizes,'
          ' attack damages original HP; no game-state mutation from hover',flush=True)
finally:
  http.shutdown()
  http.server_close()
