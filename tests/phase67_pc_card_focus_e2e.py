"""Phase67 PC card-first legibility and eased in-world hover, real Chromium/WebGL."""
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
        opts = {'headless': True, 'args': [
            '--no-sandbox', '--enable-webgl', '--use-gl=angle',
            '--use-angle=swiftshader', '--enable-unsafe-swiftshader']}
        if Path('/usr/bin/chromium').exists():
            opts['executable_path'] = '/usr/bin/chromium'
        browser = pw.chromium.launch(**opts)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.add_init_script("""(() => {
            let seed=Number(new URLSearchParams(location.search).get('qa_seed'))||198704;
            Math.random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;
              return seed/4294967296;};
        })();""")
        url = f'http://127.0.0.1:{server.server_port}/Marorong_Card_War_Phase67_3D_Prototype.html'
        affordable = None
        for seed in range(198704, 198750):
            page.goto(url + f'?qa_seed={seed}')
            page.locator('#newGame').click()
            page.locator('#launchGame').click()
            page.get_by_role('button', name='이 손패로 시작').click()
            hand = page.locator('#hand .hand-slot').evaluate_all("""els => els.map((e,i) => ({
                i,cost:Number(e.querySelector('.cost-bubble')?.textContent||99),
                board:/type-(몬스터|시설|영웅유닛)/.test(e.querySelector('.card-ui')?.className||'')
            }))""")
            affordable = next((x for x in hand if x['board'] and x['cost']<=2), None)
            if affordable:
                break
        assert affordable, 'No affordable native card for WebGL test'

        def snapshot():
            return page.evaluate("""() => {
                const s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);
            }""")

        original=snapshot()
        page.locator('#mrr-integrated-open').click()
        page.wait_for_function('MRRIntegrated.state.open && MRRIntegrated.state.scene.frames>4',
                               timeout=25000)
        assert snapshot()==original, 'Opening view changed gameplay'
        assert page.evaluate('MRRIntegrated.state.scene.pcLegibilityRevision') == 67
        assert page.evaluate('MRRIntegrated.state.scene.pcCardScale') == 1.30
        assert page.evaluate('MRRIntegrated.state.scene.pcCardHoverScale') == 1.52
        page.locator('#hand .hand-slot').nth(affordable['i']).evaluate('e=>e.click()')
        key = page.locator('#arena .slot.legal').first.get_attribute('data-slot')
        assert key
        xy = page.evaluate('(key)=>MRRIntegrated.scene.projectSlot(key)',key)
        page.mouse.click(xy['x'],xy['y'])
        page.wait_for_function("""key => document.querySelector(
          '#arena [data-slot="'+key+'"] .board-card')!==null""",arg=key)
        after_placement=snapshot()

        for w,h in ((1920,1080),(1366,768),(2560,1440)):
            page.set_viewport_size({'width':w,'height':h})
            page.wait_for_timeout(250)
            assert page.locator('#endTurn').is_visible()
            page.mouse.move(5,h//2)
            page.wait_for_timeout(450)
            idle=page.evaluate('(key)=>MRRIntegrated.state.scene.pcRenderedCardScales[key]',key)
            assert 1.29<=idle<=1.31,('idle scale',w,h,idle)
            center=page.evaluate('(key)=>MRRIntegrated.scene.projectCard(key)',key)
            assert center and 0<center['x']<w and 0<center['y']<h,(w,h,center)
            actual=page.evaluate("""p=>!!document.elementFromPoint(p.x,p.y)
              ?.closest('#mrr-integrated-stage')""",center)
            assert actual,('3D card obscured by HTML hand',w,h,center)
            page.mouse.move(center['x'],center['y'])
            page.wait_for_function('(key)=>MRRIntegrated.state.scene.hoveredKey===key',
                                   arg=key,timeout=9000)
            page.wait_for_timeout(510)
            hovered=page.evaluate('(key)=>MRRIntegrated.state.scene.pcRenderedCardScales[key]',key)
            assert 1.46<=hovered<=1.53,('hovered focus scale',w,h,hovered)
            assert snapshot()==after_placement,('Hover mutated original game',w,h)
            page.screenshot(path=str(ROOT/f'tests/phase67_card_focus_{w}x{h}.png'),
                            animations='disabled')
            page.mouse.move(5,h//2)
            page.wait_for_timeout(420)
            returned=page.evaluate('(key)=>MRRIntegrated.state.scene.pcRenderedCardScales[key]',key)
            assert 1.29<=returned<=1.32,('hover focus failed to settle',w,h,returned)
            assert snapshot()==after_placement
            print(f'PHASE67 {w}x{h}: idle={idle:.3f}, focused={hovered:.3f}, returned={returned:.3f}',flush=True)

        page.locator('#mrr-integrated-exit').evaluate('e=>e.click()')
        assert page.evaluate('MRRIntegrated.scene===null')
        assert snapshot()==after_placement
        assert not errors,errors
        browser.close()
        print('PHASE67 CARD-FIRST PASS: FHD/laptop/2K real WebGL focus, original native state unchanged')
finally:
    server.shutdown()
    server.server_close()
