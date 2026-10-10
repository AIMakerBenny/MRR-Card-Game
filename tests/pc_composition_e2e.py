"""Phase 56 PC-only Chromium WebGL and native control composition gate."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
server = ThreadingHTTPServer(('127.0.0.1', 0),
    partial(SimpleHTTPRequestHandler, directory=str(ROOT)))
threading.Thread(target=server.serve_forever, daemon=True).start()

try:
  with sync_playwright() as pw:
    options = {'headless': True, 'args': [
      '--no-sandbox', '--enable-webgl', '--use-gl=angle',
      '--use-angle=swiftshader', '--enable-unsafe-swiftshader']}
    if Path('/usr/bin/chromium').exists():
      options['executable_path'] = '/usr/bin/chromium'
    browser = pw.chromium.launch(**options)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080},
                            device_scale_factor=1)
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.add_init_script("""(() => {
      let seed = Number(new URLSearchParams(location.search).get('qa_seed')) || 198704;
      Math.random = () => {
        seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
        return seed / 4294967296;
      };
    })();""")
    url = f'http://127.0.0.1:{server.server_port}/Marorong_Card_War_Phase56_3D_Prototype.html'
    affordable = []
    for seed in range(198704, 198745):
      page.goto(url + f'?qa_seed={seed}')
      page.locator('#newGame').click()
      page.locator('#launchGame').click()
      page.get_by_role('button', name='이 손패로 시작').click()
      hand = page.locator('#hand .hand-slot').evaluate_all("""els => els.map((e,i) => ({
        i, cost:Number(e.querySelector('.cost-bubble')?.textContent || 99),
        board:/type-(몬스터|시설|영웅유닛)/.test(e.querySelector('.card-ui')?.className || '')
      }))""")
      affordable = [a for a in hand if a['board'] and a['cost'] <= 2]
      if affordable: break
    assert affordable, 'No affordable real native card was found'
    def snap():
      return page.evaluate("""() => {
        let s = gameSnapshot(); delete s.storedAt; return JSON.stringify(s);
      }""")
    before = snap()
    page.locator('#mrr-integrated-open').click()
    page.wait_for_function('MRRIntegrated.state.open && MRRIntegrated.state.scene.frames > 4',
                           timeout=25000)
    assert snap() == before, 'Entering 3D changed legacy engine state'
    assert page.locator('#mrr-battlefield-modal').count() == 0
    state = page.evaluate('MRRIntegrated.state.scene')
    assert state['slotCount'] == 30 and state['rendererAlive'] and state['cameraPreset'] == 'tabletop'
    assert state['desktopArtRevision'] == 55 and state['proceduralTextureCount'] == 2

    for w,h in [(1920,1080),(1366,768),(2560,1440)]:
      page.set_viewport_size({'width':w,'height':h})
      page.wait_for_timeout(450)
      assert page.locator('#endTurn').is_visible()
      assert page.locator('#hand .hand-slot').count() > 0
      assert page.locator('#enemyHand .mcw-back').count() > 0
      metrics = page.evaluate("""() => {
        const box = sel => {
          const el = document.querySelector(sel);
          if (!el) return null;
          const r = el.getBoundingClientRect();
          return {x:r.left,y:r.top,right:r.right,bottom:r.bottom,
                  width:r.width,height:r.height};
        };
        return {
          enemyHero:box('#enemyPortrait'),
          ownHero:box('#myPortrait'),
          enemyBacks:[...document.querySelectorAll('#enemyHand .mcw-back')].map(e => {
            const r=e.getBoundingClientRect();
            return {x:r.left,y:r.top,right:r.right,bottom:r.bottom};
          }),
          hand:[...document.querySelectorAll('#hand .hand-slot .card-ui')].map(e => {
            const r=e.getBoundingClientRect();
            return {y:r.top,bottom:r.bottom,height:r.height};
          }),
          canvas:box('#mrr-integrated-stage canvas'),
          stage:MRRIntegrated.state.scene
        };
      }""")
      for name in ['enemyHero','ownHero']:
        b = metrics[name]
        assert b and b['x'] >= 0 and b['right'] <= w and b['y'] >= 0 and b['bottom'] <= h, (name,w,h,b)
      for b in metrics['enemyBacks']:
        assert b['x'] >= -1 and b['right'] <= w+1 and b['y'] >= -1 and b['bottom'] < h*.25, (w,h,b)
      assert metrics['hand']
      visible = [max(0,min(h,c['bottom'])-max(0,c['y'])) / c['height']
                 for c in metrics['hand']]
      assert min(visible) >= .36,(w,h,visible)
      assert metrics['canvas']['width'] > 600 and metrics['canvas']['height'] > 600
      assert metrics['stage']['slotCount'] == 30
      assert snap() == before,'PC viewport resize changed native match state'
      print(f'PHASE56 MEASURE {w}x{h}: enemy-backs={len(metrics["enemyBacks"])} '
            f'hand-visible-min={min(visible):.3f} native-state=unchanged',flush=True)
      page.screenshot(path=str(ROOT/f'tests/phase56_pc_{w}x{h}_empty.png'),
                      animations='disabled')
    page.set_viewport_size({'width':1920,'height':1080})
    page.wait_for_timeout(250)
    page.locator('#hand .hand-slot').nth(affordable[0]['i']).evaluate('(e)=>e.click()')
    target = page.locator('#arena .slot.legal').first.get_attribute('data-slot')
    assert target
    projected = page.evaluate('(key)=>MRRIntegrated.scene.projectSlot(key)',target)
    assert projected and 0 < projected['x'] < 1920 and 0 < projected['y'] < 1080, projected
    page.mouse.click(projected['x'],projected['y'])
    page.wait_for_function("""key =>
      document.querySelector('#arena [data-slot="' + key + '"] .board-card') !== null""",
      arg=target,timeout=9000)
    assert page.evaluate('MRRIntegrated.state.scene.publicCardCount') >= 1
    assert before != snap(),'Native legal placement not reflected in engine'
    page.screenshot(path=str(ROOT/'tests/phase56_pc_1920x1080_card.png'),
                    animations='disabled')
    page.locator('#mrr-integrated-exit').evaluate('(e)=>e.click()')
    assert page.evaluate('MRRIntegrated.scene === null')
    assert page.locator('#mrr-integrated-stage').count() == 0
    assert page.locator('#arena').is_visible()
    assert not errors,errors
    browser.close()
    print('PHASE56 PC CHROMIUM PASS: FHD, 1366, 2K, native placement, no hero/back clipping, 30 slots, state parity')
finally:
  server.shutdown()
  server.server_close()
