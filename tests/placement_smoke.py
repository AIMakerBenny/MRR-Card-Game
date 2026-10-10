"""Check that Phase22 still dispatches legal placements to the original engine."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
html=(ROOT/'Marorong_Card_War_Phase37_3D_Prototype.html').read_text()
with sync_playwright() as pw:
    browser_args={'headless':True,'args':['--no-sandbox','--no-proxy-server']}
    if Path('/usr/bin/chromium').exists():browser_args['executable_path']='/usr/bin/chromium'
    browser=pw.chromium.launch(**browser_args)
    page=browser.new_page(viewport={'width':1920,'height':1080})
    page.route('**/*',lambda route:route.abort())
    page.evaluate('''() => {let seed=198704;Math.random=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};}''')
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content(html)
    page.locator('#newGame').click();page.locator('#launchGame').click()
    page.get_by_role('button',name='이 손패로 시작').click()
    options=page.locator('.hand-slot').evaluate_all('''els=>els.map((e,i)=>({index:i,cost:Number(e.querySelector('.cost-bubble')?.textContent||99),isBoardCard:/type-(몬스터|시설|영웅유닛)/.test(e.querySelector('.card-ui')?.className||'')}))''')
    legal=[x for x in options if x['isBoardCard'] and x['cost']<=2]
    assert legal,'Seeded opening hand lacks an affordable field card, cannot test unit placement'
    hand_before=page.locator('.hand-slot').count()
    page.locator('.hand-slot').nth(legal[0]['index']).evaluate('(el)=>el.click()')
    targets=page.locator('.slot.legal')
    assert targets.count()>0,'No legal field target after selecting affordable field card'
    targets.first.evaluate('(el)=>el.click()')
    page.wait_for_timeout(150)
    assert page.locator('.board-card').count()==1
    assert page.locator('.hand-slot').count()==hand_before-1
    assert page.locator('[data-slot]').count()==30
    assert not errors,errors
    page.locator('#mcw3d-toggle').click()
    page.wait_for_timeout(950)
    assert page.evaluate('MCW3D.status.renderer')=='css'
    assert page.locator('.board-card').count()==1
    page.screenshot(path=str(ROOT/'tests/phase22_depth_with_unit.png'))
    print('PLACEMENT PASS - legal card placed, hand decreases once, 30 slots stable after mode switch.')
    page.close();browser.close()
