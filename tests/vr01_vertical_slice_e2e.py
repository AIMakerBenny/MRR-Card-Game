"""VR01: compare Phase76 baseline to new desktop shell in real Chromium.
Keep all existing Phase76 and older tests untouched.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
http=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=http.serve_forever,daemon=True).start()
try:
  with sync_playwright() as pw:
    opts={'headless':True,'args':['--no-sandbox','--enable-webgl','--use-gl=angle',
      '--use-angle=swiftshader','--enable-unsafe-swiftshader']}
    if Path('/usr/bin/chromium').exists():opts['executable_path']='/usr/bin/chromium'
    browser=pw.chromium.launch(**opts)
    page=browser.new_page(viewport={'width':1920,'height':1080})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.add_init_script("""(() => {
      let seed=Number(new URLSearchParams(location.search).get('qa_seed'))||198704;
      Math.random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;
      return seed/4294967296;};
    })();""")
    url=f'http://127.0.0.1:{http.server_port}/Marorong_Card_War_Phase76_3D_Prototype.html'
    def snap():
      return page.evaluate("""() => {
        const s=gameSnapshot();delete s.storedAt;return JSON.stringify(s);
      }""")
    def set_unit(side):
      cards=page.locator('.hand-slot').evaluate_all("""els=>els.map((e,i)=>{
        const c=e.querySelector('.card-ui'),kind=c?.querySelector('.card-kind')?.textContent||'',
          stats=c?.querySelector('.card-stats')?.textContent||'';
        return {i,attack:Number(stats.match(/[검공]\s*(\d+)/)?.[1]||0),
          cost:Number(c?.querySelector('.cost-bubble')?.textContent||99),
          unit:/몬스터/.test(kind)};
      }).filter(x=>x.unit&&x.attack>0&&x.cost<=2)""")
      for card in cards:
        page.locator('#hand .hand-slot').nth(card['i']).evaluate('e=>e.click()')
        legal=page.locator(f'#arena [data-slot^="{side}:front:"].legal')
        if not legal.count():continue
        key=legal.first.get_attribute('data-slot')
        legal.first.evaluate('e=>e.click()')
        return key
      return None
    mine=opponent=None
    for seed in range(198704,198780):
      page.goto(url+f'?qa_seed={seed}',wait_until='domcontentloaded')
      page.locator('#newGame').click()
      page.locator('#modeSelect').select_option('local')
      page.locator('#launchGame').click()
      page.get_by_role('button',name='이 손패로 시작').click()
      mine=set_unit(0)
      if not mine:continue
      page.locator('#endTurn').evaluate('e=>e.click()')
      page.wait_for_selector('#passContinue')
      page.locator('#passContinue').click()
      opponent=set_unit(1)
      if not opponent:continue
      page.locator('#endTurn').evaluate('e=>e.click()')
      page.wait_for_selector('#passContinue')
      page.locator('#passContinue').click()
      break
    assert mine and opponent,'Could not prepare two genuine Phase21 units'
    baseline=snap()
    page.locator('#mrr-integrated-open').click()
    page.wait_for_function('MRRIntegrated.state.open && MRRIntegrated.state.scene.frames>5',timeout=35000)
    page.screenshot(path=str(ROOT/'tests/vr00_phase76_before_1920x1080.png'),animations='disabled')
    page.locator('#mrr-integrated-exit').evaluate('e=>e.click()')
    assert snap()==baseline
    page.locator('#mrr-vr-open').click()
    page.wait_for_function('MRRVR.status.open && MRRIntegrated.state.scene.frames>5',timeout=45000)
    assert snap()==baseline,'Opening VR changed actual gameplay'
    assert page.locator('#mrr-vr-shell').is_visible()
    for w,h in ((1920,1080),(1366,768),(2560,1440)):
      page.set_viewport_size({'width':w,'height':h})
      page.mouse.move(5,h//2)
      page.wait_for_timeout(750)
      assert page.locator('#vr-end-turn').is_visible()
      assert page.locator('#vr-return').is_visible()
      assert page.locator('#vr-enemy-fan .vr-back').count()==page.locator('#enemyHand .mcw-back').count()
      assert page.locator('#vr-hand .vr-card').count()==page.locator('#hand .hand-slot').count()
      visible_public=page.locator('#arena [data-slot] .board-card .card-ui').count()
      plaques=page.locator('#vr-public-plaques .vr-unit-plaque')
      assert plaques.count()==visible_public,(w,h,plaques.count(),visible_public)
      assert page.evaluate('MRRIntegrated.state.scene.vrOccupiedSeats')==visible_public,(
        w,h,'Decorative seats must follow public native cards only')
      assert page.locator('#vr-public-plaques').evaluate("e=>getComputedStyle(e).pointerEvents")=='none'
      assert page.locator('#vr-enemy-fan').evaluate("e=>getComputedStyle(e).pointerEvents")=='none'
      if page.locator('#vr-enemy-fan .vr-back').count():
        back=page.locator('#vr-enemy-fan .vr-back').first.bounding_box()
        assert back and back['y']+back['height']>78,(w,h,'Opponent backs are tiny',back)
      assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1 || document.documentElement.scrollHeight>innerHeight+1')
      for selector in ('#vr-end-turn','#vr-return'):
        box=page.locator(selector).bounding_box()
        assert box and box['x']>=0 and box['y']>=0,(selector,box)
        assert box['x']+box['width']<=w and box['y']+box['height']<=h
      assert snap()==baseline,(w,h,'VR rendering changed gameplay')
      page.screenshot(path=str(ROOT/f'tests/vr01_after_{w}x{h}.png'),animations='disabled')
      print('VR01',w,h,'hand',page.locator('#vr-hand .vr-card').count(),
        'enemy backs',page.locator('#vr-enemy-fan .vr-back').count(),flush=True)
    page.set_viewport_size({'width':1920,'height':1080})
    # Both authentic public units were placed far apart. Each must grow from
    # original Phase76 idle 1.30 to >1.48 without changing engine state.
    page.wait_for_function("""() => {
      const scales=MRRIntegrated.state.scene.vrAdaptiveCardScales||{};
      return Object.values(scales).length===2 &&
        Object.values(scales).every(v=>v>1.48);
    }""",timeout=26000)
    assert snap()==baseline,'VR-only physical scaling modified game'
    # VR camera buttons change only the Three.js view, not game state.
    for label,preset in [('시점: 아군','ally'),('시점: 상대','enemy'),('시점: 전체','tabletop')]:
      previous_frames=page.evaluate('MRRIntegrated.state.scene.frames')
      page.locator('#vr-camera').click()
      assert page.locator('#vr-camera').inner_text()==label
      assert page.evaluate('MRRIntegrated.state.scene.cameraPreset')==preset
      # Wait for the actual rendered frame, not only the camera setter.
      page.wait_for_function('old=>MRRIntegrated.state.scene.frames>old',arg=previous_frames,timeout=25000)
      assert snap()==baseline,('camera changed engine',preset)
      if preset in ('ally','enemy'):
        owner='0' if preset=='ally' else '1'
        positions=page.evaluate("""owner=>[...document.querySelectorAll('#arena [data-slot^="'+owner+':"]')]
          .map(el=>MRRIntegrated.scene.projectSlot(el.dataset.slot))""",owner)
        assert len(positions)==15,(preset,'all native row addresses retained',len(positions))
        assert all(p and 80<p['x']<1840 and 85<p['y']<970 for p in positions),(
          preset,'some native card slots clipped by camera',positions)
      page.screenshot(path=str(ROOT/f'tests/vr01_camera_{preset}_1920x1080.png'),animations='disabled')
    xy=page.evaluate('(key)=>MRRIntegrated.scene.projectCard(key)',mine)
    assert xy and 0<xy['x']<1920 and 0<xy['y']<1080,xy
    # VR01 public-card enlargement uses the existing Three.js card texture,
    # and must not change Phase21 state or substitute a fabricated illustration.
    page.mouse.move(xy['x'],xy['y'])
    page.wait_for_function("""key=>{
      const target=document.querySelector('#mrr-vr-card-focus');
      return MRRIntegrated.state.scene.hoveredKey===key &&
        !!target && !target.hidden &&
        target.querySelector('img')?.src.startsWith('data:image/png;base64,');
    }""",arg=mine,timeout=18000)
    assert snap()==baseline,'Card magnification must not change original gameplay'
    focus_box=page.locator('#mrr-vr-card-focus').bounding_box()
    assert focus_box and focus_box['width']>=200 and focus_box['height']>=270,focus_box
    dock=page.locator('#mrr-vr-card-focus').get_attribute('data-dock')
    assert dock in ('left','right'),dock
    focus_occlusion=page.evaluate('Number(document.querySelector("#mrr-vr-card-focus").dataset.publicOcclusion)')
    assert focus_occlusion>=0,focus_occlusion
    main_card=page.evaluate('key=>MRRIntegrated.scene.projectCardBounds(key)',mine)
    assert main_card and (focus_box['x']+focus_box['width']<=main_card['left']+8 or
      focus_box['x']>=main_card['right']-8 or
      focus_box['y']+focus_box['height']<=main_card['top']+8 or
      focus_box['y']>=main_card['bottom']-8),('focus occludes hovered public card',focus_box,main_card)
    page.screenshot(path=str(ROOT/'tests/vr01_card_focus_1920x1080.png'),animations='disabled')
    page.mouse.click(xy['x'],xy['y'])
    page.wait_for_function("""()=>MRRIntegrated.state.scene.selectedKey!==null &&
      !document.querySelector('#mrr-integrated-context').hidden""",timeout=18000)
    assert snap()==baseline
    before_hp=page.evaluate("""key=>{const [owner,row,col]=key.split(':');
      return G.players[+owner][row][+col]?.hp}""",opponent)
    assert before_hp and before_hp>0
    page.locator('#mrr-quick-attack').click(timeout=12000)
    page.wait_for_function('MRRIntegrated.state.scene.attackTargetCount>0',timeout=13000)
    assert snap()==baseline,'Aiming cannot alter the engine'
    page.screenshot(path=str(ROOT/'tests/vr01_attack_target_1920x1080.png'),animations='disabled')
    target=page.evaluate('(key)=>MRRIntegrated.scene.projectCard(key)',opponent)
    assert target and 0<target['x']<1920 and 0<target['y']<1080
    page.mouse.click(target['x'],target['y'])
    page.wait_for_function("""v=>{const [owner,row,col]=v.key.split(':');
      return (G.players[+owner][row][+col]?.hp||0)<v.hp}""",
      arg={'key':opponent,'hp':before_hp},timeout=13000)
    after=snap()
    assert after!=baseline
    if page.locator(f'#arena [data-slot="{opponent}"] .board-card').count():
      page.wait_for_function('MRRIntegrated.state.scene.vrHitReactions>=1',timeout=13000)
    assert page.evaluate('MRRIntegrated.state.scene.vrHitReactions')>=0
    page.screenshot(path=str(ROOT/'tests/vr01_attack_confirmed_1920x1080.png'),animations='disabled')

    # VR01-D: deliberately dense DISPLAY-ONLY stress fixture. Clone only
    # native, already-public board-card DOM; never edit G, decks, hands or AI.
    # Real attack / placement / turn tests remain separately authoritative.
    dense_native=snap()
    stress=page.evaluate("""() => {
      const cells=[...document.querySelectorAll('#arena .slot[data-slot]')];
      const original=cells.find(s=>s.querySelector('.board-card'))?.querySelector('.board-card');
      if(!original)return {error:'No real public board-card to clone'};
      const clones=[];
      for(const cell of cells){
        if(clones.length>=22)break;
        if(cell.querySelector('.board-card'))continue;
        const copy=original.cloneNode(true);
        copy.dataset.vrStressClone='true';
        cell.append(copy);clones.push(cell.dataset.slot);
      }
      return {cloned:clones.length,originals:cells.filter(c=>c.querySelector('.board-card:not([data-vr-stress-clone])')).length};
    }""")
    assert stress.get('cloned')==22,stress
    count=stress['originals']+stress['cloned']
    page.evaluate('MRRIntegrated.scene.sync()')
    page.wait_for_function("""n=>MRRIntegrated.state.scene.cardMeshCount===n &&
      MRRIntegrated.state.scene.vrOccupiedSeats===n &&
      document.querySelectorAll('#vr-public-plaques .vr-unit-plaque').length===n""",
      arg=count,timeout=40000)
    for w,h in ((1920,1080),(1366,768)):
      page.set_viewport_size({'width':w,'height':h})
      page.mouse.move(4,h//2)
      # The real Phase21 resize may repaint #arena from G, which correctly
      # discards synthetic DOM clones. Top up the display fixture only AFTER
      # the responsive repaint; this is not a native game bug.
      page.wait_for_timeout(800)
      replenished=page.evaluate("""target => {
        const cells=[...document.querySelectorAll('#arena .slot[data-slot]')];
        const template=cells.find(s=>s.querySelector('.board-card'))?.querySelector('.board-card');
        if(!template)return -1;
        let current=cells.filter(s=>s.querySelector('.board-card')).length;
        for(const cell of cells){
          if(current>=target)break;
          if(cell.querySelector('.board-card'))continue;
          const clone=template.cloneNode(true);
          clone.dataset.vrStressClone='true';
          cell.append(clone);current++;
        }
        MRRIntegrated.scene.sync();
        return current;
      }""",count)
      assert replenished==count,(w,h,'public-only fixture rehydration',replenished,count)
      page.wait_for_function("""n=>MRRIntegrated.state.scene.cardMeshCount===n &&
        MRRIntegrated.state.scene.vrOccupiedSeats===n &&
        document.querySelectorAll('#vr-public-plaques .vr-unit-plaque').length===n""",
        arg=count,timeout=40000)
      page.wait_for_function("""() => {
        const v=MRRIntegrated.state.scene;
        return v.vrCameraAuto && v.pitch>1.265 && v.distance>31.5;
      }""",timeout=35000)
      page.wait_for_timeout(650)
      layout=page.evaluate("""() => {
        const nodes=[...document.querySelectorAll('#vr-public-plaques .vr-unit-plaque')]
          .filter(e=>!e.hidden);
        const rects=nodes.map(e=>e.getBoundingClientRect());
        const overlap=[];
        for(let i=0;i<rects.length;i++)for(let j=i+1;j<rects.length;j++){
          const a=rects[i],b=rects[j];
          if(a.left<b.right-2&&a.right>b.left+2&&
             a.top<b.bottom-2&&a.bottom>b.top+2)overlap.push([i,j]);
        }
        // Actual public card faces must be less occluded in occupied
        // adjacent rows; plaque collision checks alone cannot prove this.
        const scene=MRRIntegrated.scene;
        const field=[...document.querySelectorAll('#arena [data-slot]')]
          .filter(s=>s.querySelector('.board-card .card-ui')).map(s=>{
            const key=s.dataset.slot;
            return {parts:key.split(':'),rect:scene.projectCardBounds(key),key};
          }).filter(s=>s.rect);
        const occlusion=[];let inspectedSameColumnPairs=0;
        for(let i=0;i<field.length;i++)for(let j=i+1;j<field.length;j++){
          const a=field[i],b=field[j];
          if(a.parts[0]!==b.parts[0]||a.parts[2]!==b.parts[2])continue;
          inspectedSameColumnPairs++;
          const ra=a.rect,rb=b.rect;
          const h=Math.min(ra.bottom,rb.bottom)-Math.max(ra.top,rb.top);
          const w=Math.min(ra.right,rb.right)-Math.max(ra.left,rb.left);
          if(h<=0||w<=0)continue;
          occlusion.push({keys:[a.key,b.key],
            fraction:Math.round(h/Math.min(ra.bottom-ra.top,rb.bottom-rb.top)*1000)/1000});
        }
        const backs=[...document.querySelectorAll('#vr-enemy-fan .vr-back')]
          .map(e=>e.getBoundingClientRect());
        let fanCover=0;
        for(const card of field){
          if(card.parts[0]!=='1')continue;
          const c=card.rect;
          for(const b of backs){
            const ox=Math.max(0,Math.min(c.right,b.right)-Math.max(c.left,b.left));
            const oy=Math.max(0,Math.min(c.bottom,b.bottom)-Math.max(c.top,b.top));
            fanCover=Math.max(fanCover,ox*oy/Math.max(1,(c.right-c.left)*(c.bottom-c.top)));
          }
        }
        const scales=MRRIntegrated.state.scene.vrAdaptiveCardScales||{};
        return {visible:nodes.length,overlap,compact:nodes.filter(e=>e.classList.contains('vr-unit-compact')).length,
          opponentFanCover:Math.round(fanCover*1000)/1000,
          cards:MRRIntegrated.state.scene.cardMeshCount,
          seats:MRRIntegrated.state.scene.vrOccupiedSeats,
          textures:MRRIntegrated.state.scene.vrLiveCardTextures,
          rowFaceOcclusion:occlusion,inspectedSameColumnPairs,
          maxRowFaceOcclusion:Math.max(0,...occlusion.map(v=>v.fraction)),
          smallerCards:Object.values(scales).filter(v=>v<=1.09).length,
          autoDistance:MRRIntegrated.state.scene.distance};
      }""")
      print('VR01-D DENSE',w,h,layout,flush=True)
      assert layout['cards']==count and layout['seats']==count and layout['textures']==count,(w,h,layout)
      assert len(layout['overlap'])==0,(w,h,'nameplates collided',layout)
      # V1.0 showed legible nameplates but cards themselves overlapped.
      assert layout['smallerCards']>=8,(w,h,'crowded rows did not shrink',layout)
      assert layout['inspectedSameColumnPairs']>=8,(w,h,'same-column face test was vacuous',layout)
      assert layout['maxRowFaceOcclusion']<=.26,(w,h,'actual public card faces overlap',layout)
      assert layout['autoDistance']>31.4,(w,h,'all-row camera did not expand',layout)
      assert layout['opponentFanCover']<=.08,(w,h,'opponent hand covers publicly occupied enemy cards',layout)
      assert layout['visible']>=(16 if w==1920 else 12),(w,h,'too many nameplates hidden',layout)
      assert snap()==dense_native,'Dense DISPLAY fixture must not mutate native Phase21 state'
      page.screenshot(path=str(ROOT/f'tests/vr01_dense_public_{w}x{h}.png'),animations='disabled')
    # A 25th public-only card must reuse all 24 existing 3D card meshes.
    # Otherwise the entire board flashes on every real summon.
    reuse=page.evaluate("""() => {
      const cell=[...document.querySelectorAll('#arena .slot[data-slot]')]
        .find(s=>!s.querySelector('.board-card'));
      const real=document.querySelector('#arena .board-card:not([data-vr-stress-clone])');
      if(!cell||!real)return {error:'Missing source or target public DOM'};
      const clone=real.cloneNode(true);
      clone.dataset.vrStressClone='true';cell.append(clone);
      MRRIntegrated.scene.sync();
      return {total:MRRIntegrated.state.scene.cardMeshCount,
        reused:MRRIntegrated.state.scene.vrReusedCards,
        textures:MRRIntegrated.state.scene.vrLiveCardTextures,
        animationCount:MRRIntegrated.state.scene.vrDeployTransitions};
    }""")
    assert reuse['total']==count+1 and reuse['reused']==count and reuse['textures']==count+1,reuse
    assert reuse['animationCount']==0,'Synthetic DOM should not animate like a real hand play'
    assert snap()==dense_native,'Public-only card re-use changed Phase21 engine'
    removed=page.evaluate("""() => {
      const clones=[...document.querySelectorAll('[data-vr-stress-clone]')];
      clones.forEach(e=>e.remove());
      MRRIntegrated.scene.sync();
      return clones.length;
    }""")
    assert removed==23,removed
    page.wait_for_function("""n=>MRRIntegrated.state.scene.cardMeshCount===n &&
      MRRIntegrated.state.scene.vrOccupiedSeats===n &&
      MRRIntegrated.state.scene.vrLiveCardTextures===n""",arg=stress['originals'],timeout=30000)
    assert snap()==dense_native,'Removing display-only stress fixture changed engine'
    page.set_viewport_size({'width':1920,'height':1080})
    page.mouse.move(950,400)
    page.mouse.wheel(0,180)
    page.wait_for_function('MRRIntegrated.state.scene.vrCameraAuto===false',timeout=7000)
    assert snap()==dense_native,'Manual camera wheel must never affect game'
    page.locator('#vr-return').click()
    assert not page.evaluate('MRRVR.status.open')
    assert page.locator('#arena').is_visible()
    assert snap()==after,'2D return changed original engine snapshot'
    assert not errors,errors

    # A separate round tests a physical VR hand click, true 3D placement,
    # then the on-screen VR turn action. All results come from Phase21.
    placed=False
    for seed in range(198704,198755):
      page.goto(url+f'?qa_seed={seed}',wait_until='domcontentloaded')
      page.locator('#newGame').click()
      page.locator('#modeSelect').select_option('local')
      page.locator('#launchGame').click()
      page.get_by_role('button',name='이 손패로 시작').click()
      affordable=page.locator('#hand .hand-slot').evaluate_all("""els=>els.map((e,i)=>({
        i,cost:Number(e.querySelector('.cost-bubble')?.textContent||99),
        board:/type-(몬스터|시설|영웅유닛)/.test(e.querySelector('.card-ui')?.className||'')
      })).filter(x=>x.board&&x.cost<=2)""")
      if not affordable:continue
      prior=snap()
      page.locator('#mrr-vr-open').click()
      page.wait_for_function('MRRVR.status.open && MRRIntegrated.state.scene.frames>3',timeout=45000)
      assert snap()==prior
      for candidate in affordable:
        card=page.locator('#vr-hand .vr-card').nth(candidate['i'])
        box=card.bounding_box()
        if not box:continue
        px=box['x']+box['width']/2
        py=min(box['y']+box['height']-8,1072)
        page.mouse.move(px,py)
        page.wait_for_timeout(280)
        # All other hand cards must remain present and the hovered card must
        # physically rise into the viewport without modifying game state.
        assert page.locator('#vr-hand .vr-card').count()==page.locator('#hand .hand-slot').count()
        debug=page.locator('#vr-hand .vr-card').nth(candidate['i']).evaluate("""e=>{
          const r=e.getBoundingClientRect(),style=getComputedStyle(e),
            face=e.querySelector('.vr-card-face'),
            at=document.elementFromPoint(r.x+r.width/2,Math.min(innerHeight-8,r.bottom-8));
          return {rect:r.toJSON(),hover:e.matches(':hover'),height:style.height,
            pointerEvents:style.pointerEvents,face:face?.getBoundingClientRect().toJSON(),
            underPointer:at?.outerHTML?.slice(0,250),rootClasses:document.querySelector('#mrr-vr-shell')?.className};
        }""")
        print('VR01 HAND DEBUG',debug,flush=True)
        page.screenshot(path=str(ROOT/'tests/vr01_hand_hover_1920x1080.png'),animations='disabled')
        assert debug['rect']['height']>250,debug
        assert snap()==prior
        page.mouse.click(px,py)
        legal=page.locator('#arena .slot.legal')
        if not legal.count():continue
        dest=legal.first.get_attribute('data-slot')
        projected=page.evaluate('k=>MRRIntegrated.scene.projectSlot(k)',dest)
        assert projected and 0<projected['x']<1920 and 0<projected['y']<1080
        page.mouse.click(projected['x'],projected['y'])
        page.wait_for_function("""key=>!!document.querySelector('#arena [data-slot="'+key+'"] .board-card')""",
          arg=dest,timeout=15000)
        assert snap()!=prior,'Real VR hand play did not change the Phase21 engine'
        # A true native confirmation, not the hand click itself, must start
        # exactly one Three.js arrival and then land with no stuck ghost.
        page.wait_for_function("""() => MRRIntegrated.state.scene.vrDeployTransitions>=1""",timeout=22000)
        page.wait_for_function("""() => MRRIntegrated.state.scene.vrDeployActive===0""",timeout=27000)
        assert page.evaluate('MRRIntegrated.state.scene.vrDeployTransitions')==1
        assert page.evaluate('MRRIntegrated.state.scene.vrLandingDustStarted')==1,(
          'Real confirmed landing should create exactly one temporary ground-contact puff')
        page.wait_for_function('MRRIntegrated.state.scene.vrLandingDustActive===0',timeout=15000)
        assert page.evaluate('MRRIntegrated.state.scene.vrOccupiedSeats')>=1
        page.screenshot(path=str(ROOT/'tests/vr01_native_deploy_landed_1920x1080.png'),animations='disabled')
        page.locator('#vr-end-turn').click()
        page.wait_for_selector('#passContinue',timeout=12000)
        placed=True
        print('VR01 native hand, native 3D slot and on-screen turn end PASS',flush=True)
        break
      if placed:break
      page.locator('#vr-return').evaluate('e=>e.click()')
    assert placed,'No genuine VR mouse hand placement + turn cycle was verified'
    browser.close()
    print('VR01 PASS: real Phase21 HP damage, 3 desktop viewports, unchanged display-only state and fallback',flush=True)
finally:
  http.shutdown()
  http.server_close()
