"""Phase59: verify owner art packaging and actual Chromium WebGL card replacement."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
import tempfile,threading,struct,zlib
from playwright.sync_api import sync_playwright
from src.card_art_bundle import bundle,dimensions

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"Marorong_Card_War_Phase59_3D_Prototype.html"
FIXTURE=ROOT/"Phase59_Artwork_QA_Fixture.html"

def png(w,h):
    # Synthetic two-colour pixels for QA only. This image is never delivered.
    left=b"\x23\xd2\x55"
    right=b"\xf0\x28\x5a"
    row=b"\x00"+left*(w//2)+right*(w-w//2)
    scan=row*h
    def chunk(tag,data):
        payload=tag+data
        return struct.pack(">I",len(data))+payload+struct.pack(">I",zlib.crc32(payload)&0xffffffff)
    return (b"\x89PNG\r\n\x1a\n"+
      chunk(b"IHDR",struct.pack(">IIBBBBB",w,h,8,2,0,0,0))+
      chunk(b"IDAT",zlib.compress(scan,9))+chunk(b"IEND",b""))

blank_js,loaded_ids=bundle(ROOT)
assert not loaded_ids,"Production cannot contain fabricated artworks"
plain=OUTPUT.read_text("utf-8")
assert blank_js in plain,"Embedded registry in output differs from actual source catalog"
assert dimensions(png(1200,960),".png")== (1200,960)

server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
  with sync_playwright() as pw:
    launch={'headless':True,'args':['--no-sandbox','--enable-webgl','--use-gl=angle',
      '--use-angle=swiftshader','--enable-unsafe-swiftshader']}
    if Path('/usr/bin/chromium').exists():launch['executable_path']='/usr/bin/chromium'
    browser=pw.chromium.launch(**launch)
    page=browser.new_page(viewport={'width':1920,'height':1080})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.add_init_script("""(() => {
      let seed=Number(new URLSearchParams(location.search).get('qa_seed'))||198704;
      Math.random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
    })();""")
    url=f'http://127.0.0.1:{server.server_port}/Marorong_Card_War_Phase59_3D_Prototype.html'
    chosen=None
    for seed in range(198704,198745):
      page.goto(url+f'?qa_seed={seed}')
      page.locator('#newGame').click()
      page.locator('#launchGame').click()
      page.get_by_role('button',name='이 손패로 시작').click()
      available=page.locator('#hand .hand-slot').evaluate_all("""els=>els.map((e,i)=>({
        i,cost:Number(e.querySelector('.cost-bubble')?.textContent||99),
        board:/type-(몬스터|시설|영웅유닛)/.test(e.querySelector('.card-ui')?.className||''),
        name:e.querySelector('.card-name')?.textContent?.trim()||'',
        kind:e.querySelector('.card-kind')?.textContent?.trim()||''
      }))""")
      candidates=[a for a in available if a['board'] and a['cost']<=2]
      if candidates:
        chosen=candidates[0]
        card_id=page.evaluate("""card=>
          window.MRRCardArtRegistry.byPublicKey[JSON.stringify([card.name,card.kind])]||null""",chosen)
        if card_id:break
        chosen=None
    assert chosen and card_id,"No unique public card ID resolved from visible hand"
    assert page.evaluate("Object.keys(window.MRRCardArtRegistry.assets).length")==0
    with tempfile.TemporaryDirectory() as temp:
      folder=Path(temp)
      art_path=folder/(card_id+".png")
      art_path.write_bytes(png(900,720))
      try:bundle(ROOT,folder)
      except ValueError as e:assert "expected 1200x960" in str(e),str(e)
      else:raise AssertionError("Importer accepted wrong picture dimensions")
      art_path.write_bytes(png(1200,960))
      rogue=folder/"not-a-card.png"
      rogue.write_bytes(png(1200,960))
      try:bundle(ROOT,folder)
      except ValueError as e:assert "unexpected card image" in str(e)
      else:raise AssertionError("Importer accepted invalid card ID")
      rogue.unlink()
      fixture_js,ids=bundle(ROOT,folder)
      assert ids==(card_id,) and "data:image/png;base64," in fixture_js
      assert len(fixture_js)>len(blank_js)
      assert plain.count(blank_js)==1
      FIXTURE.write_text(plain.replace(blank_js,fixture_js,1),encoding="utf-8")
      page.goto(f'http://127.0.0.1:{server.server_port}/{FIXTURE.name}?qa_seed={seed}')
      page.locator('#newGame').click()
      page.locator('#launchGame').click()
      page.get_by_role('button',name='이 손패로 시작').click()
      hand_item=page.locator('#hand .hand-slot').nth(chosen['i'])
      assert hand_item.locator('.card-name').inner_text().strip()==chosen['name']
      before=page.evaluate("""() => {
        let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);
      }""")
      page.locator('#mrr-integrated-open').click()
      page.wait_for_function('MRRIntegrated.state.open && MRRIntegrated.state.scene.frames>4',timeout=25000)
      assert page.evaluate('MRRIntegrated.state.scene.artworkImportRevision')==59
      assert page.evaluate('MRRIntegrated.state.scene.artworkEmbeddedCount')==1
      assert page.evaluate('MRRIntegrated.state.scene.artworkLoadedCount')==0
      assert page.evaluate("""() => {
        let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);
      }""")==before
      hand_item.evaluate('(e)=>e.click()')
      key=page.locator('#arena .slot.legal').first.get_attribute('data-slot')
      pt=page.evaluate('key=>MRRIntegrated.scene.projectSlot(key)',key)
      assert pt and 0<pt['x']<1920 and 0<pt['y']<1080
      page.mouse.click(pt['x'],pt['y'])
      page.wait_for_function("""key =>
        !!document.querySelector('#arena [data-slot="'+key+'"] .board-card')""",
        arg=key,timeout=9000)
      page.wait_for_function('MRRIntegrated.state.scene.artworkLoadedCount>=1',timeout=12000)
      assert page.evaluate('MRRIntegrated.state.scene.publicCardCount')>=1
      assert page.evaluate("""() => {
        let s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);
      }""")!=before
      pixels=page.evaluate("""async key=>{
        const data=MRRIntegrated.scene.getCardPreview(key)?.artData;
        const im=new Image();im.src=data;await im.decode();
        const cv=document.createElement('canvas');
        cv.width=im.width;cv.height=im.height;
        const c=cv.getContext('2d',{willReadFrequently:true});c.drawImage(im,0,0);
        return {
          left:[...c.getImageData(70,250,1,1).data],
          right:[...c.getImageData(430,250,1,1).data],
          header:[...c.getImageData(260,100,1,1).data],
          size:[im.width,im.height]
        };
      }""",key)
      assert pixels["size"]==[512,704],pixels
      assert pixels["left"]==[35,210,85,255],pixels
      assert pixels["right"]==[240,40,90,255],pixels
      # The artwork must not cover the separate title area.
      assert pixels["header"][:3]!=pixels["left"][:3] and pixels["header"][:3]!=pixels["right"][:3]
      for w,h in ((1920,1080),(1366,768),(2560,1440)):
        page.set_viewport_size({'width':w,'height':h})
        page.wait_for_timeout(250)
        assert page.locator('#endTurn').is_visible()
        pt=page.evaluate('key=>MRRIntegrated.scene.projectSlot(key)',key)
        assert 0<pt['x']<w and 0<pt['y']<h,(w,h,pt)
        page.screenshot(path=str(ROOT/f'tests/phase59_test_only_art_{w}x{h}.png'))
      page.locator('#mrr-integrated-exit').evaluate('e=>e.click()')
      assert page.locator('#arena').is_visible()
      assert page.evaluate('MRRIntegrated.scene===null')
      assert not errors,errors
    browser.close()
    print("PHASE59 ART PIPELINE PASS: validated 1200x960 PNG; rejected wrong size and unknown ID; exact on-card pixels, native placement, 3 PC resolutions, no shipped fake art")
finally:
  FIXTURE.unlink(missing_ok=True)
  server.shutdown();server.server_close()
