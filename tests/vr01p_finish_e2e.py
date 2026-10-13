"""VR01P real native lethal combat and cleanup, no engine mutations."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import threading
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
  with sync_playwright() as pw:
    opts={'headless':True,'args':['--no-sandbox','--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']}
    if Path('/usr/bin/chromium').exists():opts['executable_path']='/usr/bin/chromium'
    browser=pw.chromium.launch(**opts)
    page=browser.new_page(viewport={'width':1920,'height':1080})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.add_init_script('''(() => {let seed=198713;Math.random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};})();''')
    def snap():return page.evaluate('() => {const s=gameSnapshot();delete s.storedAt;return JSON.stringify(s)}')
    def turn():
      page.locator('#endTurn').evaluate('e=>e.click()')
      page.wait_for_selector('#passContinue');page.locator('#passContinue').click()
    def place(side):
      cards=page.locator('#hand .hand-slot').evaluate_all('''els=>els.map((e,i)=>{
        const c=e.querySelector('.card-ui');return {i,
          cost:Number(c?.querySelector('.cost-bubble')?.textContent||99),
          unit:/몬스터/.test(c?.querySelector('.card-kind')?.textContent||''),
          attack:Number(c?.querySelector('.card-stats')?.textContent.match(/[검공]\\s*(\\d+)/)?.[1]||0)};
      }).filter(c=>c.unit&&c.attack>0&&c.cost<=2)''')
      for card in cards:
        page.locator('#hand .hand-slot').nth(card['i']).evaluate('e=>e.click()')
        slot=page.locator(f'#arena [data-slot^="{side}:front:"].legal').first
        if not slot.count():continue
        key=slot.get_attribute('data-slot');slot.evaluate('e=>e.click()');return key
      raise AssertionError('Known native opening has no affordable front unit')
    for reduced in [False,True]:
      page.emulate_media(reduced_motion='reduce' if reduced else 'no-preference')
      page.goto(f'http://127.0.0.1:{server.server_port}/Marorong_Card_War_Phase76_3D_Prototype.html')
      page.locator('#newGame').click();page.locator('#modeSelect').select_option('local')
      page.locator('#launchGame').click();page.get_by_role('button',name='이 손패로 시작').click()
      source=place(0);turn();target=place(1);turn()
      page.locator('#mrr-vr-open').click()
      page.wait_for_function('MRRVR.status.open && MRRIntegrated.state.scene.frames>5',timeout=45000)
      target_slot=page.locator(f'#arena [data-slot="{target}"]');hits=0
      while target_slot.locator('.board-card').count() and hits<12:
        if hits:turn();turn()
        xy=page.evaluate('k=>MRRIntegrated.scene.projectCard(k)',source);assert xy
        page.mouse.click(xy['x'],xy['y'])
        page.wait_for_function('k=>MRRIntegrated.state.scene.selectedKey===k',arg=source)
        page.wait_for_selector('#mrr-quick-attack:not([hidden])');page.locator('#mrr-quick-attack').click()
        page.wait_for_function('MRRIntegrated.state.scene.attackTargetCount>0')
        assert 'attack-target' in target_slot.get_attribute('class')
        xy=page.evaluate('k=>MRRIntegrated.scene.projectCard(k)',target)
        page.mouse.move(xy['x'],xy['y'])
        page.wait_for_function('k=>MRRIntegrated.state.scene.hoveredKey===k',arg=target,timeout=15000)
        xy=page.evaluate('k=>MRRIntegrated.scene.projectCard(k)',target)
        old=page.evaluate('MRRVR.status.nativeOutcomes')
        hp=target_slot.locator('.card-stats').text_content()
        print('Native aim',source,target,xy,'reduced',reduced,flush=True)
        page.mouse.click(xy['x'],xy['y'])
        # Phase21 emits fx-hit only on surviving hits, and suppresses all
        # native FX under reduced motion. Verify its actual public result.
        page.wait_for_function('''v=>{const c=document.querySelector(
          '#arena [data-slot="'+v.key+'"] .board-card .card-stats');
          return !c||c.textContent!==v.hp;}''',arg={'key':target,'hp':hp},timeout=15000)
        if not reduced and target_slot.locator('.board-card').count():
          page.wait_for_function('n=>MRRVR.status.nativeOutcomes>n',arg=old,timeout=15000)
        page.wait_for_function('!document.querySelector("#arena .slot.attack-target")');hits+=1
        print('Native hit',hits,'reduced',reduced,flush=True)
      assert not target_slot.locator('.board-card').count(),'No native lethal combat occurred'
      page.wait_for_function('k=>!MRRIntegrated.scene.hasCard(k)',arg=target,timeout=15000)
      departing=page.evaluate('MRRIntegrated.state.scene.vrDepartStarted')
      halos=page.evaluate('MRRIntegrated.state.scene.vrDepartHaloStarted')
      assert departing==0 if reduced else departing>=1
      assert halos==departing,('Every genuine VR departure must start exactly one halo',halos,departing)
      page.wait_for_function('''() => {const s=MRRIntegrated.state.scene;return
        !s.vrTargetLockKey&&!s.hoveredKey&&s.vrDepartActive===0&&
        s.vrDepartHaloActive===0&&
        !document.querySelector('#vr-guide-targets').children.length&&
        !document.querySelector('#vr-aim-line').getAttribute('d');}'''.replace('return\n','return '),timeout=15000)
      live=page.locator('#arena .board-card .card-ui').count();state=page.evaluate('MRRIntegrated.state.scene')
      assert state['cardMeshCount']==live and state['vrLiveCardTextures']==live
      assert state['pickableCount']==30+live*2
      assert page.locator(f'#vr-public-plaques [data-slot="{target}"]').count()==0
      before=snap()
      page.screenshot(path=str(ROOT/f'tests/vr01p_native_lethal_{"reduced" if reduced else "normal"}_1920x1080.png'))
      page.locator('#vr-return').click();assert snap()==before
      print('VR01P REAL LETHAL PASS',{'hits':hits,'reduced':reduced,'live':live},flush=True)
    assert not errors,errors
    browser.close()
finally:
  server.shutdown();server.server_close()
