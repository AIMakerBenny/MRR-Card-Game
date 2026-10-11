"""Phase69: real PC Chromium/WebGL zone contrast, native clicks and unchanged engine."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import threading
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
server=ThreadingHTTPServer(('127.0.0.1',0),
    partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
    with sync_playwright() as pw:
        options={'headless':True,'args':['--no-sandbox','--enable-webgl',
            '--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']}
        if Path('/usr/bin/chromium').exists():
            options['executable_path']='/usr/bin/chromium'
        browser=pw.chromium.launch(**options)
        page=browser.new_page(viewport={'width':1920,'height':1080})
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.add_init_script("""(() => {
          let n=Number(new URLSearchParams(location.search).get('qa_seed'))||198704;
          Math.random=()=>{n=(Math.imul(n,1664525)+1013904223)>>>0;
            return n/4294967296;};
        })();""")
        url=f'http://127.0.0.1:{server.server_port}/Marorong_Card_War_Phase69_3D_Prototype.html'
        affordable=None
        for seed in range(198704,198750):
            page.goto(url+f'?qa_seed={seed}',wait_until='domcontentloaded')
            page.locator('#newGame').click()
            page.locator('#launchGame').click()
            page.get_by_role('button',name='이 손패로 시작').click()
            hand=page.locator('#hand .hand-slot').evaluate_all("""els=>els.map((e,i)=>({
               i,cost:Number(e.querySelector('.cost-bubble')?.textContent||99),
               board:/type-(몬스터|시설|영웅유닛)/.test(e.querySelector('.card-ui')?.className||'')
            }))""")
            affordable=next((c for c in hand if c['board'] and c['cost']<=2),None)
            if affordable:break
        assert affordable,'No real affordable original field card found'
        def snap():
            return page.evaluate("""() => {
              const s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);
            }""")
        baseline=snap()
        page.locator('#mrr-integrated-open').click()
        page.wait_for_function('MRRIntegrated.state.open && MRRIntegrated.state.scene.frames>4',
            timeout=25000)
        stage=page.evaluate('MRRIntegrated.state.scene')
        assert stage['rendererAlive'] and stage['slotCount']==30
        assert stage['pcZoneContrastRevision']==69
        assert stage['pcLegibilityRevision']==67
        assert stage['artworkEmbeddedCount']==0,'Never import placeholder artwork'
        assert stage['cameraPreset']=='tabletop'
        assert snap()==baseline,'Visual scene mutated native gameplay'
        for w,h in ((1366,768),(1920,1080),(2560,1440)):
            page.set_viewport_size({'width':w,'height':h})
            page.mouse.move(5,h//2)
            page.wait_for_timeout(350)
            assert page.locator('#enemyHand .mcw-back').count()>0
            assert page.locator('#endTurn').is_visible()
            tab=page.locator('#mrr-integrated-hand-tab')
            assert tab.is_visible()
            tab.click()
            assert tab.get_attribute('aria-expanded')=='true'
            assert snap()==baseline
            page.screenshot(path=str(ROOT/f'tests/phase69_zone_hand_{w}x{h}.png'),
                            animations='disabled')
            tab.click()
            assert tab.get_attribute('aria-expanded')=='false'
            page.screenshot(path=str(ROOT/f'tests/phase69_zone_board_{w}x{h}.png'),
                            animations='disabled')
            assert snap()==baseline,(w,h,'Viewport changed original game state')
            print('PHASE69 ZONE',w,h,'WebGL scene/hand/engine unchanged',flush=True)
        page.set_viewport_size({'width':1920,'height':1080})
        page.locator('#hand .hand-slot').nth(affordable['i']).evaluate('e=>e.click()')
        target=page.locator('#arena .slot.legal').first.get_attribute('data-slot')
        assert target
        pt=page.evaluate('(key)=>MRRIntegrated.scene.projectSlot(key)',target)
        assert pt and 0<pt['x']<1920 and 0<pt['y']<1080
        assert page.evaluate("""p=>!!document.elementFromPoint(p.x,p.y)
            ?.closest('#mrr-integrated-stage')""",pt),'Legal target click intercepted'
        page.mouse.click(pt['x'],pt['y'])
        page.wait_for_function("""key=>document.querySelector(
            '#arena [data-slot="'+key+'"] .board-card')!==null""",
            arg=target,timeout=9000)
        placed=snap()
        assert placed!=baseline,'Native placement did not change game state'
        for w,h in ((1366,768),(1920,1080),(2560,1440)):
            page.set_viewport_size({'width':w,'height':h})
            page.mouse.move(5,h//2)
            page.wait_for_timeout(350)
            card=page.evaluate('(key)=>MRRIntegrated.scene.projectCard(key)',target)
            assert card and 0<card['x']<w and 0<card['y']<h,(w,h,card)
            assert page.evaluate("""p=>!!document.elementFromPoint(p.x,p.y)
                ?.closest('#mrr-integrated-stage')""",card),(w,h,'Public card covered')
            assert snap()==placed
            page.screenshot(path=str(ROOT/f'tests/phase69_zone_card_{w}x{h}.png'),
                            animations='disabled')
        page.locator('#mrr-integrated-exit').evaluate('e=>e.click()')
        assert page.evaluate('MRRIntegrated.scene===null')
        assert page.locator('#arena').is_visible()
        assert snap()==placed,'2D exit changed legacy game'
        assert not errors,errors
        browser.close()
        print('PHASE69 PASS: 3 PC WebGL resolutions, visible territories, hand, native placement, 2D parity')
finally:
    server.shutdown()
    server.server_close()
