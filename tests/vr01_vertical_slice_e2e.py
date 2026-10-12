"""VR01: compare Phase76 baseline to new desktop shell in real Chromium.
Keep all existing Phase76 and older tests untouched.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
http=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=http.serve_forever,daemon=True).start()
try:
  with sync_playwright() as pw:
    opts={'headless':True,'args':['--no-sandbox','--enable-webgl','--use-gl=angle',
      '--use-angle=swiftshader','--enable-unsafe-swiftshader']}
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
    url=f'http://127.0.0.1:{http.server_port}/Marorong_Card_War_Phase76_3D_Prototype.html'
    def snap():
      return page.evaluate("""() => {
        const s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);
      }""")
    def set_unit(side):
      cards=page.locator('.hand-slot').evaluate_all("""els=>els.map((e,i)=>{
        const c=e.querySelector('.card-ui'),kind=c?.querySelector('.card-kind')?.textContent||'',
          stats=c?.querySelector('.card-stats')?.textContent||'';
        return {i,attack:Number(stats.match(/[검공]\s*(\d+)/)?.[1]||0),
          cost:Number(c?.querySelector('.cost-bubble')?.textContent||99),
          unit:/몬스터/.test(kind)};
      }).filter(x=>x.unit&&x.attack>0&&x.cost<=2)""")
      for card in cards:
        page.locator('#hand .hand-slot').nth(card['i']).evaluate('e=>e.click()')
        legal=page.locator(f'#arena [data-slot^="{side}:front:"].legal')
        if not legal.count():continue
        key=legal.first.get_attribute('data-slot')
        legal.first.evaluate('e=>e.click()')
        return key
      return None
    mine=opponent=None
    for seed in range(198704,198780):
      page.goto(url+f'?qa_seed={seed}',wait_until='domcontentloaded')
      page.locator('#newGame').click()
      page.locator('#modeSelect').select_option('local')
      page.locator('#launchGame').click()
      page.get_by_role('button',name='이 손패로 시작').click()
      mine=set_unit(0)
      if not mine:continue
      page.locator('#endTurn').evaluate('e=>e.click()')
      page.wait_for_selector('#passContinue')
      page.locator('#passContinue').click()
      opponent=set_unit(1)
      if not opponent:continue
      page.locator('#endTurn').evaluate('e=>e.click()')
      page.wait_for_selector('#passContinue')
      page.locator('#passContinue').click()
      break
    assert mine and opponent,'Could not prepare two genuine Phase21 units'
    baseline=snap()
    page.locator('#mrr-integrated-open').click()
    page.wait_for_function('MRRIntegrated.state.open && MRRIntegrated.state.scene.frames>5',timeout=35000)
    page.screenshot(path=str(ROOT/'tests/vr00_phase76_before_1920x1080.png'),animations='disabled')
    page.locator('#mrr-integrated-exit').evaluate('e=>e.click()')
    assert snap()==baseline
    page.locator('#mrr-vr-open').click()
    page.wait_for_function('MRRVR.status.open && MRRIntegrated.state.scene.frames>5',timeout=45000)
    assert snap()==baseline,'Opening VR changed actual gameplay'
    assert page.locator('#mrr-vr-shell').is_visible()
    for w,h in ((1920,1080),(1366,768),(2560,1440)):
      page.set_viewport_size({'width':w,'height':h})
      page.mouse.move(5,h//2)
      page.wait_for_timeout(750)
      assert page.locator('#vr-end-turn').is_visible()
      assert page.locator('#vr-return').is_visible()
      assert page.locator('#vr-enemy-fan .vr-back').count()==page.locator('#enemyHand .mcw-back').count()
      assert page.locator('#vr-hand .vr-card').count()==page.locator('#hand .hand-slot').count()
      visible_public=page.locator('#arena [data-slot] .board-card .card-ui').count()
      plaques=page.locator('#vr-public-plaques .vr-unit-plaque')
      assert plaques.count()==visible_public,(w,h,plaques.count(),visible_public)
      assert page.locator('#vr-public-plaques').evaluate("e=>getComputedStyle(e).pointerEvents")=='none'
      assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1 || document.documentElement.scrollHeight>innerHeight+1')
      for selector in ('#vr-end-turn','#vr-return'):
        box=page.locator(selector).bounding_box()
        assert box and box['x']>=0 and box['y']>=0,(selector,box)
        assert box['x']+box['width']<=w and box['y']+box['height']<=h
      assert snap()==baseline,(w,h,'VR rendering changed gameplay')
      page.screenshot(path=str(ROOT/f'tests/vr01_after_{w}x{h}.png'),animations='disabled')
      print('VR01',w,h,'hand',page.locator('#vr-hand .vr-card').count(),
        'enemy backs',page.locator('#vr-enemy-fan .vr-back').count(),flush=True)
    page.set_viewport_size({'width':1920,'height':1080})
    # VR camera buttons change only the Three.js view, not game state.
    for label,preset in [('시점: 아군','ally'),('시점: 상대','enemy'),('시점: 전체','tabletop')]:
      page.locator('#vr-camera').click()
      assert page.locator('#vr-camera').inner_text()==label
      assert page.evaluate('MRRIntegrated.state.scene.cameraPreset')==preset
      assert snap()==baseline,('camera changed engine',preset)
    xy=page.evaluate('(key)=>MRRIntegrated.scene.projectCard(key)',mine)
    assert xy and 0<xy['x']<1920 and 0<xy['y']<1080,xy
    # VR01 public-card enlargement uses the existing Three.js card texture,
    # and must not change Phase21 state or substitute a fabricated illustration.
    page.mouse.move(xy['x'],xy['y'])
    page.wait_for_function("""key=>{
      const target=document.querySelector('#mrr-vr-card-focus');
      return MRRIntegrated.state.scene.hoveredKey===key &&
        !!target && !target.hidden &&
        target.querySelector('img')?.src.startsWith('data:image/png;base64,');
    }""",arg=mine,timeout=18000)
    assert snap()==baseline,'Card magnification must not change original gameplay'
    focus_box=page.locator('#mrr-vr-card-focus').bounding_box()
    assert focus_box and focus_box['width']>=200 and focus_box['height']>=270,focus_box
    page.screenshot(path=str(ROOT/'tests/vr01_card_focus_1920x1080.png'),animations='disabled')
    page.mouse.click(xy['x'],xy['y'])
    page.wait_for_function("""()=>MRRIntegrated.state.scene.selectedKey!==null &&
      !document.querySelector('#mrr-integrated-context').hidden""",timeout=18000)
    assert snap()==baseline
    before_hp=page.evaluate("""key=>{const [owner,row,col]=key.split(':');
      return G.players[+owner][row][+col]?.hp}""",opponent)
    assert before_hp and before_hp>0
    page.locator('#mrr-quick-attack').click(timeout=12000)
    page.wait_for_function('MRRIntegrated.state.scene.attackTargetCount>0',timeout=13000)
    assert snap()==baseline,'Aiming cannot alter the engine'
    page.screenshot(path=str(ROOT/'tests/vr01_attack_target_1920x1080.png'),animations='disabled')
    target=page.evaluate('(key)=>MRRIntegrated.scene.projectCard(key)',opponent)
    assert target and 0<target['x']<1920 and 0<target['y']<1080
    page.mouse.click(target['x'],target['y'])
    page.wait_for_function("""v=>{const [owner,row,col]=v.key.split(':');
      return (G.players[+owner][row][+col]?.hp||0)<v.hp}""",
      arg={'key':opponent,'hp':before_hp},timeout=13000)
    after=snap()
    assert after!=baseline
    page.screenshot(path=str(ROOT/'tests/vr01_attack_confirmed_1920x1080.png'),animations='disabled')
    page.locator('#vr-return').click()
    assert not page.evaluate('MRRVR.status.open')
    assert page.locator('#arena').is_visible()
    assert snap()==after,'2D return changed original engine snapshot'
    assert not errors,errors

    # A separate round tests a physical VR hand click, true 3D placement,
    # then the on-screen VR turn action. All results come from Phase21.
    placed=False
    for seed in range(198704,198755):
      page.goto(url+f'?qa_seed={seed}',wait_until='domcontentloaded')
      page.locator('#newGame').click()
      page.locator('#modeSelect').select_option('local')
      page.locator('#launchGame').click()
      page.get_by_role('button',name='이 손패로 시작').click()
      affordable=page.locator('#hand .hand-slot').evaluate_all("""els=>els.map((e,i)=>({
        i,cost:Number(e.querySelector('.cost-bubble')?.textContent||99),
        board:/type-(몬스터|시설|영웅유닛)/.test(e.querySelector('.card-ui')?.className||'')
      })).filter(x=>x.board&&x.cost<=2)""")
      if not affordable:continue
      prior=snap()
      page.locator('#mrr-vr-open').click()
      page.wait_for_function('MRRVR.status.open && MRRIntegrated.state.scene.frames>3',timeout=45000)
      assert snap()==prior
      for candidate in affordable:
        card=page.locator('#vr-hand .vr-card').nth(candidate['i'])
        box=card.bounding_box()
        if not box:continue
        px=box['x']+box['width']/2
        py=min(box['y']+box['height']-8,1072)
        page.mouse.move(px,py)
        page.wait_for_timeout(280)
        # All other hand cards must remain present and the hovered card must
        # physically rise into the viewport without modifying game state.
        assert page.locator('#vr-hand .vr-card').count()==page.locator('#hand .hand-slot').count()
        debug=page.locator('#vr-hand .vr-card').nth(candidate['i']).evaluate("""e=>{
          const r=e.getBoundingClientRect(),style=getComputedStyle(e),
            face=e.querySelector('.vr-card-face'),
            at=document.elementFromPoint(r.x+r.width/2,Math.min(innerHeight-8,r.bottom-8));
          return {rect:r.toJSON(),hover:e.matches(':hover'),height:style.height,
            pointerEvents:style.pointerEvents,face:face?.getBoundingClientRect().toJSON(),
            underPointer:at?.outerHTML?.slice(0,250),rootClasses:document.querySelector('#mrr-vr-shell')?.className};
        }""")
        print('VR01 HAND DEBUG',debug,flush=True)
        page.screenshot(path=str(ROOT/'tests/vr01_hand_hover_1920x1080.png'),animations='disabled')
        assert debug['rect']['height']>250,debug
        assert snap()==prior
        page.mouse.click(px,py)
        legal=page.locator('#arena .slot.legal')
        if not legal.count():continue
        dest=legal.first.get_attribute('data-slot')
        projected=page.evaluate('k=>MRRIntegrated.scene.projectSlot(k)',dest)
        assert projected and 0<projected['x']<1920 and 0<projected['y']<1080
        page.mouse.click(projected['x'],projected['y'])
        page.wait_for_function("""key=>!!document.querySelector('#arena [data-slot="'+key+'"] .board-card')""",
          arg=dest,timeout=15000)
        assert snap()!=prior,'Real VR hand play did not change the Phase21 engine'
        page.locator('#vr-end-turn').click()
        page.wait_for_selector('#passContinue',timeout=12000)
        placed=True
        print('VR01 native hand, native 3D slot and on-screen turn end PASS',flush=True)
        break
      if placed:break
      page.locator('#vr-return').evaluate('e=>e.click()')
    assert placed,'No genuine VR mouse hand placement + turn cycle was verified'
    browser.close()
    print('VR01 PASS: real Phase21 HP damage, 3 desktop viewports, unchanged display-only state and fallback',flush=True)
finally:
  http.shutdown()
  http.server_close()
