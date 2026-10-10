from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
original=(ROOT/'legacy/Phase21_Original.html').read_text(encoding='utf-8')
modded=(ROOT/'Marorong_Card_War_Phase31_3D_Prototype.html').read_text(encoding='utf-8')

def launch_game(page):
    page.locator('#newGame').click()
    page.locator('#launchGame').click()
    page.get_by_role('button',name='이 손패로 시작').click()

with sync_playwright() as playwright:
    opts={'headless':True,'args':['--no-sandbox','--disable-dev-shm-usage','--disable-gpu-sandbox','--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--no-proxy-server']}
    if Path('/usr/bin/chromium').exists(): opts['executable_path']='/usr/bin/chromium'
    browser=playwright.chromium.launch(**opts)
    for W,H in [(1920,1080),(1366,768),(390,844)]:
        page=browser.new_page(viewport={'width':W,'height':H})
        errors=[]
        page.on('pageerror',lambda exc:errors.append(str(exc)))
        page.route('**/*',lambda route:route.abort())
        page.set_content(modded,wait_until='domcontentloaded')
        page.wait_for_timeout(250)
        assert page.locator('#newGame').is_visible(),f'New game not visible at {W}x{H}'
        assert page.locator('#mcw3d-toggle').count()==1,('No 3d switch',errors)
        assert page.locator('#mcw3d-canvas-host').count()==1
        assert not errors,('Script errors during boot:',errors)
        launch_game(page)
        page.wait_for_timeout(200)
        assert page.locator('[data-slot]').count()==30
        assert page.locator('.hand-slot').count()>0
        hand_before=page.locator('.hand-slot').count()
        d={
            'viewport':f'{W}x{H}',
            'slots':page.locator('[data-slot]').count(),
            'hand':hand_before,
            'engine':page.evaluate('typeof G !== "undefined" && !!G'),
            'original_title':page.title(),
        }
        assert d['engine']
        page.locator('#mcw3d-toggle').click()
        page.wait_for_timeout(1400)
        d['3d_mode']=page.evaluate('window.MCW3D.status.renderer')
        assert d['3d_mode']=='css',d
        assert page.locator('.hand-slot').count()==hand_before
        assert page.locator('[data-slot]').count()==30
        assert not errors,('Script errors:',errors)
        page.locator('#mcw3d-toggle').click()
        assert page.evaluate('window.MCW3D.status.renderer')=='legacy'
        assert page.locator('[data-slot]').count()==30
        page.screenshot(path=str(ROOT/f'tests/phase22_{W}x{H}.png'))
        print('BROWSER PASS',json.dumps(d,ensure_ascii=False))
        page.close()
    browser.close()
