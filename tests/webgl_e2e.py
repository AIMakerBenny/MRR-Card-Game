"""CI-only strict WebGL test. Requires npm vendor and a normal localhost browser.

This test is NOT claimed as passed in the initial environment, which blocks
Chromium navigation and fetching of the pinned Three.js dependency.
"""
from pathlib import Path
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
assert (ROOT/'vendor/three.module.js').exists(), 'Three.js is not vendored: run npm install and npm run vendor'
handler=partial(SimpleHTTPRequestHandler,directory=str(ROOT))
server=ThreadingHTTPServer(('127.0.0.1',0),handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}/Marorong_Card_War_Phase34_3D_Prototype.html'
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1920,'height':1080})
        # Reproducible opening hand, same seed as the existing placement smoke test.
        page.add_init_script('''() => {let seed=Number(new URLSearchParams(location.search).get('qa_seed'))||198704;Math.random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};}''')
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(url,wait_until='domcontentloaded')
        page.locator('#newGame').click();page.locator('#launchGame').click()
        page.get_by_role('button',name='이 손패로 시작').click()
        before=page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);}''')
        page.locator('#mcw3d-toggle').click()
        page.wait_for_function('window.MCW3D?.status.renderer === "three"',timeout=18000)
        page.wait_for_function('window.MCW3D.scene?.state.slotCount === 30',timeout=9000)
        assert page.locator('#mcw3d-canvas-host canvas').count()==1
        assert page.locator('#mcw3d-canvas-host canvas').evaluate('e=>e.width>300 && e.height>200')
        after=page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);}''')
        assert before==after, 'Three scene mutated game state'
        assert not errors,errors
        # Use normal game commands to place a card, then check the actual
        # WebGL focus state. No test mutates the game's rules or hand directly.
        options=page.locator('.hand-slot').evaluate_all('''els=>els.map((e,i)=>({index:i,cost:Number(e.querySelector('.cost-bubble')?.textContent||99),isBoardCard:/type-(몬스터|시설|영웅유닛)/.test(e.querySelector('.card-ui')?.className||'')}))''')
        legal=[x for x in options if x['isBoardCard'] and x['cost']<=2]
        # A randomized opening hand is not guaranteed to contain a cheap unit.
        # Retry whole normal matches with explicit deterministic seeds; never
        # insert a card into the engine or mutate card costs for test convenience.
        for seed in range(198705,198725):
            if legal:break
            page.goto(url+f'?qa_seed={seed}',wait_until='domcontentloaded')
            page.locator('#newGame').click();page.locator('#launchGame').click()
            page.get_by_role('button',name='이 손패로 시작').click()
            page.locator('#mcw3d-toggle').click()
            page.wait_for_function('window.MCW3D?.status.renderer === "three" && MCW3D.scene.state.slotCount === 30',timeout=18000)
            options=page.locator('.hand-slot').evaluate_all('''els=>els.map((e,i)=>({index:i,cost:Number(e.querySelector('.cost-bubble')?.textContent||99),isBoardCard:/type-(몬스터|시설|영웅유닛)/.test(e.querySelector('.card-ui')?.className||'')}))''')
            legal=[x for x in options if x['isBoardCard'] and x['cost']<=2]
        assert legal,'No affordable field card in 21 deterministic test openings'
        page.locator('.hand-slot').nth(legal[0]['index']).evaluate('(el)=>el.click()')
        targets=page.locator('.slot.legal')
        assert targets.count()>0,'No legal target for normal placement'
        # Exercise eligible DOM targets via the same native click the legacy
        # engine receives; don't directly mutate G or insert a unit.
        slot_options=targets.evaluate_all("els=>els.map(e=>e.getAttribute('data-slot'))")
        before_count=page.locator('.board-card').count()
        targets.first.evaluate('(el)=>el.click()')
        page.wait_for_timeout(200)
        if page.locator('.board-card').count()==before_count:
            # A normal invalid placement can leave no unit; report enough
            # information to distinguish game legality from renderer failure.
            raise AssertionError(f'Normal placement did not create a board card: slots={slot_options}, candidate={legal[0]}, before={before_count}, hand={page.locator(".hand-slot").count()}')
        page.wait_for_function('MCW3D.scene.state.cardCount >= 1',timeout=8000)
        # Phase27: only visible HP is mirrored; the meter is not a second game state.
        actual=page.locator('.slot:has(.board-card) .hpbar > div').first
        assert actual.count()==1, 'No public health bar on placed unit'
        dom_ratio=actual.evaluate("e => parseFloat(e.style.width)/100")
        shown=page.evaluate("MCW3D.scene.state.visibleHealthRatios")
        assert page.evaluate("MCW3D.scene.state.healthMeterRevision === 27")
        assert len(shown)==1 and abs(shown[0]['ratio']-dom_ratio)<.001,(shown,dom_ratio)
        assert page.evaluate("MCW3D.scene.state.illustrationRevision === 29 && MCW3D.scene.state.proceduralArtCards === 1 && MCW3D.scene.state.visibleDomArtCards === 1"), 'Procedural card art is not visible on the original card'
        assert page.evaluate("MCW3D.scene.state.artIdentityRevision===31 && MCW3D.scene.state.proceduralArtProfiles.length===1 && MCW3D.scene.state.proceduralArtProfiles[0].identity.motif>=0 && MCW3D.scene.state.proceduralArtProfiles[0].identity.motif<8"),'Phase31 unique heraldic art identity missing'
        assert page.locator('.slot:has(.board-card) .art-well').first.evaluate(
            "el => getComputedStyle(el).backgroundImage.includes('data:image/png')"
        ),'Original visible art well does not contain the new generated painting'
        assert page.evaluate("['warrior','ship','citadel','arcane','crystal'].includes(MCW3D.scene.state.proceduralArtProfiles[0].profile)"), 'Unexpected illustration profile'
        # The selected card must remain actually visible in WebGL mode.
        assert page.locator('.slot:has(.board-card) .card-ui').first.evaluate(
            "el => Number(getComputedStyle(el).opacity) > 0.9"
        ), 'Phase 23 visual regression: WebGL mode hides DOM card art'
        assert page.evaluate('MCW3D.scene.state.frameRevision === 24 && MCW3D.scene.state.decoratedCards === 1'), 'Card face texture and metal trim missing'
        assert page.evaluate('MCW3D.scene.state.battlefieldRevision === 25 && MCW3D.scene.state.battlefieldTrimCount === 4 && MCW3D.scene.state.battlefieldLightPoolCount === 2'), 'Arena rim/light pools missing'
        assert page.locator('#mcw3d-canvas-host').evaluate("e => getComputedStyle(e).pointerEvents === 'none'"), 'WebGL scene steals mouse input'
        assert page.evaluate("MCW3D.scene.state.arenaRevision===30 && MCW3D.scene.state.cornerArtworkSources===4 && MCW3D.scene.state.visibleArenaMedallions===4 && MCW3D.scene.state.decorativeDomCount===4"),'Phase30 arena corner decorations missing'
        assert page.locator('#mcw30-arena-ornaments .mcw30-corner').count()==4
        assert page.locator('#mcw30-arena-ornaments').evaluate("e=>getComputedStyle(e).pointerEvents==='none'"),'Arena accents intercept clicks'
        assert page.evaluate("MCW3D.scene.state.laneRevision===32 && MCW3D.scene.state.visibleLaneCount>0 && MCW3D.scene.state.visibleLaneCount===MCW3D.scene.state.visibleLaneMeshes"),'Phase32 battlefield lane inlays missing'
        assert page.locator('#mcw32-lane-inlays').evaluate("e=>getComputedStyle(e).pointerEvents==='none'"),'Lane inlays intercept input'
        before_focus=page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);}''')
        # Newly placed cards may remain selected. Their idle height is 10,
        # whereas a true hover must raise only that card to height 18.
        idle_target=page.evaluate('MCW3D.scene.state.maxTargetLift')
        assert idle_target in (0,10),f'Unexpected idle focus lift: {idle_target}'
        node=page.locator('.slot:has(.board-card)').first
        # Phase33: test only a visual marker, not an actual attack dispatch.
        assert page.evaluate('MCW3D.scene.state.targetingRevision===33')
        before_target=page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);}''')
        possible=page.locator('#fieldTable .slot').first
        assert possible.count()==1
        was_selected=node.evaluate("el=>el.classList.contains('selected-slot')")
        node.evaluate("el=>el.classList.add('selected-slot')")
        possible.evaluate("el=>el.classList.add('attack-target')")
        possible.hover()
        page.wait_for_function("MCW3D.scene.state.targetGuideActive && !!MCW3D.scene.state.targetGuidePath",timeout=9000)
        assert page.locator('#mcw33-target-guide path[stroke]').count()==1
        assert page.evaluate("MCW3D.scene.state.targetReticleRevision === 34")
        assert page.locator('#mcw33-target-guide .mcw34-reticle').count()==1
        assert page.locator('#mcw33-target-guide .mcw34-reticle').evaluate(
            "e=>Number(e.getAttribute('r'))===16 && Number.isFinite(Number(e.getAttribute('cx')))"
        )
        assert page.locator('#mcw33-target-guide').evaluate("e=>getComputedStyle(e).pointerEvents==='none'")
        page.screenshot(path=str(ROOT/'tests/phase33_target_arrow.png'))
        page.mouse.move(0,0)
        page.wait_for_function("MCW3D.scene.state.targetGuideActive===false",timeout=9000)
        assert page.locator('#mcw33-target-guide').count()==0
        possible.evaluate("el=>el.classList.remove('attack-target')")
        if not was_selected:
            node.evaluate("el=>el.classList.remove('selected-slot')")
        after_target=page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);}''')
        assert before_target==after_target,'Decorative targeting guide changed game state'
        node.hover()
        page.wait_for_function('MCW3D.scene.state.hoveredCardCount === 1 && MCW3D.scene.state.maxTargetLift === 18 && MCW3D.scene.state.maxLift > 15',timeout=8000)
        assert page.locator('[data-slot]').count()==30
        assert page.locator('.board-card').count()==1
        page.screenshot(path=str(ROOT/'tests/webgl_phase23_hover.png'))
        page.mouse.move(0,0)
        page.wait_for_function('''idle => MCW3D.scene.state.hoveredCardCount === 0 && MCW3D.scene.state.maxTargetLift === idle && MCW3D.scene.state.maxLift <= idle+1''',arg=idle_target,timeout=8000)
        after_focus=page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);}''')
        assert before_focus==after_focus,'Hover changed the game state'
        # 3D drawing must be constrained to #arena (no decorations on HUD).
        clip=page.evaluate('MCW3D.scene.state.renderClip')
        arena=page.locator('#arena').bounding_box()
        assert clip is not None and arena is not None
        assert abs(clip['x']-max(0,arena['x']))<=2, (clip,arena)
        assert abs(clip['w']-min(1920-arena['x'],arena['width']))<=3,(clip,arena)
        assert page.locator('#mcw3d-canvas-host canvas').evaluate("e => getComputedStyle(e).pointerEvents === 'none'")
        assert page.evaluate('MCW3D.scene.state.visualFxRevision === 26')
        # Trigger an established visual marker. This touches only presentation;
        # it is not a simulated gameplay attack or a balance change.
        node.evaluate("el => el.classList.remove('fx-hit','fx-heal','fx-summon')")
        page.wait_for_timeout(110)
        old_fx=page.evaluate('MCW3D.scene.state.visualFxTriggered')
        node.evaluate("el => el.classList.add('fx-hit')")
        page.wait_for_function('prior => MCW3D.scene.state.visualFxTriggered > prior && MCW3D.scene.state.activeVisualMeshes > 1',arg=old_fx,timeout=8000)
        page.wait_for_timeout(175)
        assert node.locator('.board-card').evaluate("el => getComputedStyle(el,'::after').content !== 'none'"), 'Hit ring CSS overlay was not painted on card'
        page.screenshot(path=str(ROOT/'tests/webgl_phase26_hit.png'))
        node.evaluate("el => el.classList.remove('fx-hit')")
        page.wait_for_timeout(120)
        old_fx=page.evaluate('MCW3D.scene.state.visualFxTriggered')
        node.evaluate("el => el.classList.add('fx-heal')")
        page.wait_for_function('prior => MCW3D.scene.state.visualFxTriggered > prior',arg=old_fx,timeout=8000)
        node.evaluate("el => el.classList.remove('fx-heal')")
        page.wait_for_timeout(120)
        old_fx=page.evaluate('MCW3D.scene.state.visualFxTriggered')
        node.evaluate("el => el.classList.add('fx-summon')")
        page.wait_for_function('prior => MCW3D.scene.state.visualFxTriggered > prior',arg=old_fx,timeout=8000)
        node.evaluate("el => el.classList.remove('fx-summon')")
        page.wait_for_timeout(1000)
        assert page.evaluate('MCW3D.scene.state.activeVisualMeshes === 0'), 'VFX meshes failed to release'
        after_fx=page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);}''')
        assert before_focus==after_fx,'Decorative combat effects changed gameplay data'
        page.screenshot(path=str(ROOT/'tests/phase30_arena.png'))
        page.screenshot(path=str(ROOT/'tests/webgl_1920x1080.png'))
        page.locator('#mcw3d-toggle').click()
        page.wait_for_function("MCW3D.status.renderer === 'legacy'")
        assert page.locator('#mcw30-arena-ornaments').count()==0,'Arena ornaments not removed with WebGL'
        assert page.locator('#mcw32-lane-inlays').count()==0,'Lane inlays not removed with WebGL'
        assert page.locator('#mcw33-target-guide').count()==0,'Target guide not removed with WebGL'
        assert not page.locator('.slot:has(.board-card) .art-well').first.evaluate(
            "el => getComputedStyle(el).backgroundImage.includes('data:image/png')"
        ),'Turning off Three.js left behind generated art'
        print('WEBGL PHASE23 PASS - local Three.js, 30 slots, hover lift, return, game state unchanged.')
        browser.close()
finally:
    server.shutdown();server.server_close()
