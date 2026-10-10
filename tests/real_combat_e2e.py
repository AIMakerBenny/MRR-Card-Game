"""Phase 50: actual UI-only local multiplayer attack transaction in Chromium WebGL.

Unlike the Phase48/49 visual-signal fixtures, this runs both players' real turns,
selects two actual cards from real opening hands, and executes an attack through
the 3D raycast controls without calling visual(), changing G, or mocking combat.
"""
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
  with sync_playwright() as p:
    config={'headless':True,'args':['--no-sandbox','--enable-webgl','--use-gl=angle',
      '--use-angle=swiftshader','--enable-unsafe-swiftshader']}
    if Path('/usr/bin/chromium').exists():config['executable_path']='/usr/bin/chromium'
    browser=p.chromium.launch(**config)
    page=browser.new_page(viewport={'width':1920,'height':1080})
    errors=[];page.on('pageerror',lambda exc:errors.append(str(exc)))
    page.add_init_script('''() => {
      let seed=Number(new URLSearchParams(location.search).get('qa_seed'))||198704;
      Math.random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};
    }''')
    url=f'http://127.0.0.1:{server.server_port}/Marorong_Card_War_Phase50_3D_Prototype.html'
    success=False
    for seed in range(198704,198760):
      page.goto(url+f'?qa_seed={seed}',wait_until='domcontentloaded')
      page.locator('#newGame').click()
      page.locator('#modeSelect').select_option('local')
      page.locator('#launchGame').click()
      page.get_by_role('button',name='이 손패로 시작').click()
      def affordable():
        return page.locator('.hand-slot').evaluate_all('''els=>els.map((e,i)=>{
          const node=e.querySelector('.card-ui'),kind=node?.querySelector('.card-kind')?.textContent||'';
          const cost=Number(node?.querySelector('.cost-bubble')?.textContent||99);
          const stats=node?.querySelector('.card-stats')?.textContent||'';
          const attack=Number(stats.match(/[검공]\s*(\d+)/)?.[1]||0);
          return {i,cost,attack,kind,front:/몬스터/.test(kind)};
        }).filter(x=>x.front&&x.cost<=2&&x.attack>0)''')
      mine=affordable()
      if not mine:continue
      page.locator('.hand-slot').nth(mine[0]['i']).evaluate('(el)=>el.click()')
      front=page.locator('#arena [data-slot^="0:front:"].legal')
      if front.count()==0:continue
      my_key=front.first.get_attribute('data-slot')
      front.first.evaluate('(el)=>el.click()')
      assert page.locator('#arena [data-slot="'+my_key+'"] .board-card').count()==1
      page.locator('#turnDock #endTurn').evaluate('(el)=>el.click()')
      page.wait_for_selector('#passContinue',timeout=5000)
      page.locator('#passContinue').click()
      theirs=affordable()
      if not theirs:continue
      page.locator('.hand-slot').nth(theirs[0]['i']).evaluate('(el)=>el.click()')
      enemy_front=page.locator('#arena [data-slot^="1:front:"].legal')
      if enemy_front.count()==0:continue
      enemy_key=enemy_front.first.get_attribute('data-slot')
      enemy_front.first.evaluate('(el)=>el.click()')
      assert page.locator('#arena [data-slot="'+enemy_key+'"] .board-card').count()==1
      page.locator('#turnDock #endTurn').evaluate('(el)=>el.click()')
      page.wait_for_selector('#passContinue',timeout=5000)
      page.locator('#passContinue').click()
      assert page.evaluate('G.current===0 && G.players[0].turns>1')
      # P0 unit is ready and its attack button is actually enabled.
      page.locator('#arena [data-slot="'+my_key+'"]').evaluate('(el)=>el.click()')
      if page.locator('#inspectBody button[data-actor="attack"]').count()==0 or page.locator('#inspectBody button[data-actor="attack"]').is_disabled():continue
      page.locator('#mrr-battlefield-open').click()
      page.wait_for_function('MRRBattlefield.state.open && MRRBattlefield.state.scene.frames>2',timeout=20000)
      assert page.evaluate('MRRBattlefield.state.scene.fxReceived.hit===0')
      if page.locator('#mrr-battlefield-attack').is_disabled():continue
      initial=page.evaluate('''(key)=>{
        const [o,row,col]=key.split(':');
        const c=G.players[+o][row][+col];
        return {hp:c?.hp,turn:G.turn,attacker:G.players[0].front.some(x=>x&&x.acted)};
      }''',enemy_key)
      assert initial['hp']>0
      page.locator('#mrr-battlefield-attack').click()
      page.wait_for_function('MRRBattlefield.state.scene.attackTargetCount>0',timeout=5000)
      assert page.locator('#arena [data-slot="'+enemy_key+'"].attack-target').count()==1
      pt=page.evaluate('(key)=>MRRBattlefield.scene.projectCard(key)',enemy_key)
      assert pt,enemy_key
      page.mouse.move(pt['x'],pt['y'])
      page.mouse.click(pt['x'],pt['y'])
      page.wait_for_function('MRRBattlefield.state.scene.fxReceived.hit>=1',timeout=10000)
      after=page.evaluate('''(key)=>{
        const [o,row,col]=key.split(':');
        const c=G.players[+o][row][+col];
        return {hp:c?.hp||0,acted:G.players[0].front.some(x=>x&&x.acted)};
      }''',enemy_key)
      assert after['hp']<initial['hp'],'A real attack animation without game damage is not verified'
      assert after['acted'],'Native attacker did not consume its actual action'
      assert page.evaluate('MRRBattlefield.state.scene.confirmedStrikes')==1
      assert page.locator('#mrr-battlefield-combat-feed[data-kind="hit"]').count()==1
      page.screenshot(path=str(ROOT/'tests/phase50_verified_real_3d_combat_fhd.png'))
      page.set_viewport_size({'width':390,'height':844})
      page.wait_for_timeout(450)
      page.screenshot(path=str(ROOT/'tests/phase50_verified_real_3d_combat_mobile.png'))
      assert page.evaluate('MRRBattlefield.state.scene.slotCount')==30
      page.locator('#mrr-battlefield-close').click()
      assert page.evaluate('MRRBattlefield.scene===null')
      assert not errors,errors
      print('PHASE50 ACTUAL COMBAT PASS',{'seed':seed,'source':my_key,'target':enemy_key,'old_hp':initial['hp'],'new_hp':after['hp'],'native_hit':True,'consumed_turn_action':True})
      success=True
      break
    assert success,'Could not complete one real two-player Chromium attack. Never report a visual fixture as real combat.'
    browser.close()
finally:
  server.shutdown()
  server.server_close()
