"""Real pointer and DOM interaction checks for Phase 28 hand visual treatment."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'Marorong_Card_War_Phase51_3D_Prototype.html').read_text('utf-8')

with sync_playwright() as pw:
    options={'headless':True,'args':['--no-sandbox','--no-proxy-server']}
    if Path('/usr/bin/chromium').exists():options['executable_path']='/usr/bin/chromium'
    browser=pw.chromium.launch(**options)
    for W,H in [(1920,1080),(390,844)]:
        page=browser.new_page(viewport={'width':W,'height':H})
        page.route('**/*',lambda route:route.abort())
        page.evaluate('''() => {let seed=198704;Math.random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};}''')
        errors=[];page.on('pageerror',lambda exc:errors.append(str(exc)))
        page.set_content(HTML)
        page.locator('#newGame').click();page.locator('#launchGame').click()
        page.get_by_role('button',name='이 손패로 시작').click()
        hand=page.locator('#hand .hand-slot')
        num=hand.count()
        assert num>1
        backs=page.locator('#enemyHand .mcw-back')
        assert backs.count()==page.evaluate('G.players[1].hand.length')
        assert page.locator('#enemyHand .mcw-hand-count').count()==1
        before=page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);}''')
        page.locator('#mcw3d-toggle').click()
        page.wait_for_function("MCW3D.status.renderer === 'css'",timeout=16000)
        assert hand.count()==num
        assert backs.count()==page.evaluate('G.players[1].hand.length')
        assert backs.first.evaluate("e => getComputedStyle(e,'::after').content !== 'none'")
        target=hand.nth(1)
        target.hover(force=True)
        page.wait_for_timeout(250)
        assert hand.count()==num
        # Non-focused cards must remain present and unhidden even when a preview is shown.
        cards=page.locator('#hand .hand-slot .card-ui')
        visible=cards.evaluate_all('''els=>els.map(e=>{let s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&Number(s.opacity)>.2&&r.width>0&&r.height>0})''')
        assert len(visible)==num and all(visible),('hand card vanished',visible)
        assert target.locator('.card-ui').evaluate("e => getComputedStyle(e,'::after').content !== 'none'")
        after=page.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);}''')
        assert before==after,'decorative hand hover mutated gameplay state'
        assert page.locator('[data-slot]').count()==30
        assert not errors,errors
        page.screenshot(path=str(ROOT/f'tests/phase28_hand_{W}x{H}.png'))
        print('PHASE28 HAND PASS',W,H,num,backs.count())
        page.close()
    browser.close()
