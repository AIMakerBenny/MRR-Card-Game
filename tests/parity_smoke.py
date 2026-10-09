from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
texts=[(ROOT/'legacy/Phase21_Original.html').read_text('utf-8'),(ROOT/'Marorong_Card_War_Phase26_3D_Prototype.html').read_text('utf-8')]

def open_game(browser,text):
    page=browser.new_page(viewport={'width':1366,'height':768})
    page.route('**/*',lambda route:route.abort())
    page.evaluate('''() => { let seed=198704; Math.random=()=>{seed=(1664525*seed+1013904223)>>>0; return seed/4294967296;}; }''')
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content(text)
    page.locator('#newGame').click();page.locator('#launchGame').click()
    page.get_by_role('button',name='이 손패로 시작').click()
    snapshot=page.evaluate('''() => {let snap=gameSnapshot();delete snap.storedAt;return JSON.stringify(snap);}''')
    assert not errors,errors
    return page,snapshot

with sync_playwright() as pw:
    chrome=Path('/usr/bin/chromium')
    args={'headless':True,'args':['--no-sandbox','--no-proxy-server']}
    if chrome.exists():args['executable_path']=str(chrome)
    browser=pw.chromium.launch(**args)
    a,snapshot_old=open_game(browser,texts[0]);b,snapshot_new=open_game(browser,texts[1]);
    assert json.loads(snapshot_old)==json.loads(snapshot_new),'3D extension changed game state at battle start'
    assert b.locator('#mcw3d-toggle').count()==1
    b.locator('#mcw3d-toggle').click();b.wait_for_timeout(1200)
    snapshot_after=b.evaluate('''() => {let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);}''')
    assert json.loads(snapshot_new)==json.loads(snapshot_after),'Presentation mode changed game state'
    print('PARITY PASS - original and enhanced battle snapshots match; toggling fallback does not change gameplay state.')
    a.close();b.close();browser.close()
