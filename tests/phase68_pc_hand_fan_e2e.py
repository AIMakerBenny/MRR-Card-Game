"""Phase68: actual PC Chromium fan reveal, legal-target auto-fold and native parity."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
server=ThreadingHTTPServer(('127.0.0.1',0),
    partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
    with sync_playwright() as pw:
        opts={'headless':True,'args':['--no-sandbox','--enable-webgl',
          '--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']}
        if Path('/usr/bin/chromium').exists():
            opts['executable_path']='/usr/bin/chromium'
        browser=pw.chromium.launch(**opts)
        page=browser.new_page(viewport={'width':1920,'height':1080})
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.add_init_script("""(() => {
          let seed=Number(new URLSearchParams(location.search).get('qa_seed'))||198704;
          Math.random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;
          return seed/4294967296;};
        })();""")
        url=f'http://127.0.0.1:{server.server_port}/Marorong_Card_War_Phase68_3D_Prototype.html'
        affordable=None
        for seed in range(198704,198750):
            page.goto(url+f'?qa_seed={seed}',wait_until='domcontentloaded')
            page.locator('#newGame').click()
            page.locator('#launchGame').click()
            page.get_by_role('button',name='이 손패로 시작').click()
            cards=page.locator('#hand .hand-slot').evaluate_all("""els=>els.map((e,i)=>({
              i,cost:Number(e.querySelector('.cost-bubble')?.textContent||99),
              board:/type-(몬스터|시설|영웅유닛)/.test(e.querySelector('.card-ui')?.className||'')
            }))""")
            affordable=next((x for x in cards if x['board'] and x['cost']<=2),None)
            if affordable:break
        assert affordable, 'Expected an affordable original card'
        def snap():
            return page.evaluate("""() => {
              const s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);
            }""")

        original=snap()
        page.locator('#mrr-integrated-open').click()
        page.wait_for_function('MRRIntegrated.state.open && MRRIntegrated.state.scene.frames>4',
                               timeout=25000)
        assert snap()==original,'Opening Three.js changed original game'
        hand_tab=page.locator('#mrr-integrated-hand-tab')
        assert hand_tab.is_visible()
        assert hand_tab.get_attribute('aria-controls')=='hand'
        assert hand_tab.get_attribute('aria-expanded')=='false'
        page.locator('#hand .hand-slot').nth(affordable['i']).evaluate('e=>e.click()')
        key=page.locator('#arena .slot.legal').first.get_attribute('data-slot')
        assert key
        assert not hand_tab.is_visible(), 'Legal placement must hide reveal tab'
        xy=page.evaluate('(key)=>MRRIntegrated.scene.projectSlot(key)',key)
        assert xy and 0<xy['x']<1920 and 0<xy['y']<1080,xy
        page.mouse.click(xy['x'],xy['y'])
        page.wait_for_function("""key => document.querySelector(
           '#arena [data-slot="'+key+'"] .board-card')!==null""",
           arg=key,timeout=9000)
        assert page.locator('#arena .board-card').count()>0
        after_placement=snap()
        assert after_placement!=original
        assert hand_tab.is_visible()
        hand=page.locator('#hand .hand-slot .card-ui')
        count=hand.count()
        assert count>0,'Expected original native cards left in the hand'

        for w,h in ((1920,1080),(1366,768),(2560,1440)):
            page.set_viewport_size({'width':w,'height':h})
            page.mouse.move(4,h//2)
            page.wait_for_timeout(450)
            assert hand_tab.is_visible() and not hand_tab.is_disabled()
            assert hand_tab.get_attribute('aria-expanded')=='false'
            assert f'{count}장' in hand_tab.inner_text()
            before=page.locator('.hand-wrap').bounding_box()
            assert before and before['height']>100
            assert hand.count()==count
            assert snap()==after_placement

            # Actual user input, not a synthetic CSS class insertion.
            hand_tab.click()
            page.wait_for_timeout(440)
            assert hand_tab.get_attribute('aria-expanded')=='true'
            assert page.locator('#gameScreen.mrr-integrated-hand-open').count()==1
            lifted=page.locator('.hand-wrap').bounding_box()
            if not lifted or before['y']-lifted['y']<=85:
                debug=page.evaluate("""() => {
                  const root=document.querySelector('#gameScreen');
                  const fan=root.querySelector('.hand-wrap');
                  const tab=document.querySelector('#mrr-integrated-hand-tab');
                  return {
                    classes:root.className,
                    legal:root.querySelectorAll('#arena .slot.legal').length,
                    boardCards:root.querySelectorAll('#arena .board-card').length,
                    previewOpen:root.matches('.mrr-integrated-hand-open:not(:has(#arena .slot.legal))'),
                    selectorMatch:fan.matches(
                      'body.mrr-integrated-active #gameScreen.mrr-integrated-hand-open:not(:has(#arena .slot.legal)) .hand-wrap'),
                    fanBottom:getComputedStyle(fan).bottom,
                    tabShown:getComputedStyle(tab).visibility,
                    tabExpanded:tab.getAttribute('aria-expanded'),
                    handHovered:!!fan.querySelector('.hand-slot:hover'),
                    cssBundled:!!document.querySelector('#mcw3d-extension-css')?.textContent?.includes('Phase68 - PC-only'),
                    cssStyleRules:[...document.querySelector('#mcw3d-extension-css').sheet.cssRules]
                      .filter(r=>r.conditionText?.includes('min-width:1024px'))
                      .map(r=>({media:r.conditionText,rules:[...r.cssRules]
                        .filter(x=>x.selectorText?.includes('hand-open'))
                        .map(x=>({selector:x.selectorText,bottom:x.style.bottom,
                          matches:[...x.selectorText.split(',')].some(a=>{try{return fan.matches(a.trim())}catch(_){return false}})}))})),
                    handInline:fan.getAttribute('style'),
                    tabPosition:getComputedStyle(tab).position,
                    tabBottom:getComputedStyle(tab).bottom,
                    mediaMatched:matchMedia('(min-width:1024px) and (min-height:700px)').matches
                  };
                }""")
                print('PHASE68 OPEN DEBUG',w,h,before,lifted,debug,flush=True)
                page.screenshot(path=str(ROOT/f'tests/phase68_failed_open_{w}x{h}.png'),
                                animations='disabled')
            assert lifted and before['y']-lifted['y']>85,(w,h,before,lifted)
            viewport_cards=hand.evaluate_all("""(els,h)=>els.map(e=>{
              const r=e.getBoundingClientRect(),s=getComputedStyle(e);
              return {display:s.display,visibility:s.visibility,opacity:Number(s.opacity),
                visibleFraction:Math.max(0,Math.min(h,r.bottom)-Math.max(0,r.top))/r.height};
            })""",h)
            assert len(viewport_cards)==count
            assert all(c['display']!='none' and c['visibility']!='hidden'
                       and c['opacity']>.2 and c['visibleFraction']>.28
                       for c in viewport_cards),(w,h,viewport_cards)
            tab_rect=hand_tab.bounding_box()
            assert tab_rect and 0<=tab_rect['x'] and tab_rect['x']+tab_rect['width']<=w
            assert tab_rect['y']>0 and tab_rect['y']+tab_rect['height']<h
            assert page.locator('#endTurn').is_visible()
            assert snap()==after_placement,'Hand reveal mutated original game'
            page.screenshot(path=str(ROOT/f'tests/phase68_hand_open_{w}x{h}.png'),
                            animations='disabled')

            # The same native physical hand cards return below the table.
            hand_tab.click()
            page.wait_for_timeout(450)
            assert hand_tab.get_attribute('aria-expanded')=='false'
            retracted=page.locator('.hand-wrap').bounding_box()
            assert retracted and abs(retracted['y']-before['y'])<7,(w,h,before,retracted)
            assert snap()==after_placement
            page.screenshot(path=str(ROOT/f'tests/phase68_hand_closed_{w}x{h}.png'),
                            animations='disabled')
            print(f'PHASE68 {w}x{h}: fan lifted {before["y"]-lifted["y"]:.1f}px; '
                  f'original cards={count}; native state unchanged',flush=True)

        # Keyboard accessibility and automatically ceding the board to the
        # original native placement target, without ever faking a native click.
        page.set_viewport_size({'width':1920,'height':1080})
        hand_tab.focus()
        page.keyboard.press('Enter')
        assert hand_tab.get_attribute('aria-expanded')=='true'
        choices=page.locator('#hand .hand-slot').evaluate_all("""els=>els.map((e,i)=>({
          i,cost:Number(e.querySelector('.cost-bubble')?.textContent||99),
          board:/type-(몬스터|시설|영웅유닛)/.test(e.querySelector('.card-ui')?.className||'')
        }))""")
        legal=next((x for x in choices if x['board'] and x['cost']<=2),None)
        if legal:
            page.locator('#hand .hand-slot').nth(legal['i']).evaluate('e=>e.click()')
            assert page.locator('#arena .slot.legal').count()>0
            assert page.locator('#gameScreen.mrr-integrated-hand-open').count()==0
            assert not hand_tab.is_visible()
            target=page.locator('#arena .slot.legal').first.get_attribute('data-slot')
            xy=page.evaluate('(key)=>MRRIntegrated.scene.projectSlot(key)',target)
            assert xy and 0<xy['x']<1920 and 0<xy['y']<1080
            assert page.evaluate("""p=>!!document.elementFromPoint(p.x,p.y)
              ?.closest('#mrr-integrated-stage')""",xy)
            page.mouse.click(xy['x'],xy['y'])
            page.wait_for_function("""key=>document.querySelector(
                '#arena [data-slot="'+key+'"] .board-card')!==null""",
                arg=target,timeout=9000)
        else:
            # Even if no cheap card remained after initial placement, the
            # escape/close control must not change the original game state.
            hand_tab.focus()
            page.keyboard.press('Enter')
            assert hand_tab.get_attribute('aria-expanded')=='false'

        before_exit=snap()
        page.locator('#mrr-integrated-exit').evaluate('e=>e.click()')
        assert page.evaluate('MRRIntegrated.scene===null')
        assert page.locator('#mrr-integrated-hand-tab').count()==0
        assert page.locator('#gameScreen.mrr-integrated-hand-open').count()==0
        assert page.locator('#arena').is_visible()
        assert snap()==before_exit,'Leaving 3D hand mode changed original game'
        assert not errors,errors
        browser.close()
        print('PHASE68 PC HAND PASS: on-demand real native cards, reversible fan, '
              '3 viewports, legal auto-collapse and original engine parity')
finally:
    server.shutdown()
    server.server_close()
