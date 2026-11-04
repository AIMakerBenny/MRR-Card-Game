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
            candidates=[c for c in hand if c['board'] and c['cost']<=2]
            affordable=None
            # Phase69 QA: the displayed mana cost and card type alone do
            # not prove that the original engine allows a destination.
            # Qualify each seed against genuine .slot.legal, then cancel
            # without playing/spending the card before the visual review.
            for candidate in candidates:
                page.locator('#hand .hand-slot').nth(candidate['i']).evaluate('e=>e.click()')
                if page.locator('#arena .slot.legal').count():
                    affordable=candidate
                    page.locator('#inspectBody button[data-cancel-action]').evaluate('e=>e.click()')
                    assert not page.locator('#arena .slot.legal').count()
                    break
                cancel=page.locator('#inspectBody button[data-cancel-action]')
                if cancel.count():cancel.evaluate('e=>e.click()')
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
        # VR01FC: repeat the REAL visible hand gesture after the three
        # viewport checks. Clicking a folded native hand by script is not
        # representative of the integrated PC controls and gave an
        # unexplained intermittent timeout on Actions run 41461816172.
        tab=page.locator('#mrr-integrated-hand-tab')
        assert tab.is_visible() and tab.is_enabled(),(
            'Native Phase69 hand reveal is unavailable before placement')
        tab.click()
        assert tab.get_attribute('aria-expanded')=='true'
        card=page.locator('#hand .hand-slot').nth(affordable['i'])
        assert card.is_visible(),'Qualified native hand card is not visible'
        # VR01GO: the original Phase21 hand is a genuine overlapping fan.
        # Playwright's default CENTER click can hit the neighboring card's
        # SVG even though the desired card is visible and enabled. Find a
        # physically exposed pixel belonging to this exact native card,
        # then issue a real mouse click there, not a synthetic DOM click.
        def exposed_point():
            return page.evaluate("""idx => {
              const card=document.querySelectorAll('#hand .hand-slot')[idx];
              if(!card)return null;
              const r=card.getBoundingClientRect();
              for(const yy of [.5,.28,.72,.12,.88])
                for(const xx of [.02,.07,.15,.25,.4,.6,.75,.88,.98]){
                  const x=r.left+r.width*xx,y=r.top+r.height*yy;
                  if(x<0||y<0||x>=innerWidth||y>=innerHeight)continue;
                  if(document.elementFromPoint(x,y)?.closest('.hand-slot')===card)
                    return {x,y,probeX:xx,probeY:yy};
                }
              return null;
            }""",affordable['i'])
        point=exposed_point()
        assert point,('Native hand fan fully obscures intended card',
                      affordable,page.locator('#hand .hand-slot').count())
        page.mouse.move(point['x'],point['y'])
        point=exposed_point()
        assert point,('Hover animation obscured native card',affordable)
        page.mouse.click(point['x'],point['y'])
        assert tab.get_attribute('aria-expanded')=='false',(
            'Native hand fan did not fold after clicking the genuine card')
        try:
            page.wait_for_function("""() => document.querySelectorAll(
                '#arena .slot.legal').length>0""",timeout=13000)
        except Exception:
            diagnostic=page.evaluate("""() => ({
                handCards:document.querySelectorAll('#hand .hand-slot').length,
                legal:document.querySelectorAll('#arena .slot.legal').length,
                attackTargets:document.querySelectorAll('#arena .slot.attack-target').length,
                selected:document.querySelectorAll('#arena .slot.selected-slot').length,
                handOpen:document.getElementById('gameScreen')
                    ?.classList.contains('mrr-integrated-hand-open'),
                overlayHidden:!!document.querySelector('#overlay.hidden'),
                handTabDisabled:document.querySelector('#mrr-integrated-hand-tab')?.disabled,
                inspector:document.querySelector('#inspectBody')?.textContent?.trim().slice(0,180)
            })""")
            print('VR01FC Phase69 genuine native card click diagnostic',
                diagnostic,flush=True)
            raise
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
