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
      move_seed=seed
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
      # VR01AA: no invented legal rings when no genuine original slot
      # has been declared by the Phase21 game engine.
      assert page.locator('#vr-guide-targets .vr-legal-guide').count()==0
      # VR01X command strip remains in the desktop viewport, reflects
      # native legal/attack candidates, and never steals battlefield clicks.
      page.wait_for_function("""() =>
        document.querySelector('#vr-hint')?.dataset.mode==='hand' &&
        document.querySelector('#vr-hint-mode')?.textContent==='손패'""",timeout=12000)
      info=page.evaluate("""() => {
        const h=document.querySelector('#vr-hint'),r=h.getBoundingClientRect();
        return {rect:r.toJSON(),text:document.querySelector('#vr-hint-text').textContent,
          pointer:getComputedStyle(h).pointerEvents,
          mode:h.dataset.mode};
      }""")
      assert info['pointer']=='none' and info['mode']=='hand',info
      assert info['rect']['left']>=0 and info['rect']['right']<=w and (
        0<=info['rect']['top']<info['rect']['bottom']<=h),info
      assert '손패' in info['text'],info
      assert page.locator('#vr-enemy-fan .vr-back').count()==page.locator('#enemyHand .mcw-back').count()
      assert page.locator('#vr-hand .vr-card').count()==page.locator('#hand .hand-slot').count()
      visible_public=page.locator('#arena [data-slot] .board-card .card-ui').count()
      plaques=page.locator('#vr-public-plaques .vr-unit-plaque')
      assert plaques.count()==visible_public,(w,h,plaques.count(),visible_public)
      # VR01H uses only the same publicly rendered CURRENT Phase21 values.
      public_badges=page.evaluate("""() => {
        const host=document.querySelector('#vr-public-plaques');
        const source=[...document.querySelectorAll('#arena [data-slot]')]
          .filter(e=>e.querySelector('.board-card .card-ui'));
        const examples=[];
        for(const el of source){
          const stats=[...el.querySelectorAll('.card-stats > span')]
            .map(e=>e.textContent.replace(/\\s+/g,' ').trim());
          const atk=stats.map(s=>s.match(/^(검|공)(?:격력)?\\s*(\\d+)/)).find(Boolean);
          const hp=stats.map(s=>s.match(/^체(?:력)?\\s*(\\d+)/)).find(Boolean);
          const badge=host.querySelector('.vr-public-combat[data-slot="'+el.dataset.slot+'"]');
          if(!atk||!hp)continue;
          const actual=badge?{attack:badge.dataset.publicAttack,health:badge.dataset.publicHealth,
            visible:!badge.hidden,pointer:getComputedStyle(badge).pointerEvents}:null;
          examples.push({key:el.dataset.slot,expected:[atk[2],hp[1]],actual});
        }
        return {examples,allBadges:host.querySelectorAll('.vr-public-combat').length};
      }""")
      assert public_badges['allBadges']==len(public_badges['examples']),public_badges
      assert all(e['actual'] and e['actual']['visible'] and
        [e['actual']['attack'],e['actual']['health']]==e['expected'] and
        e['actual']['pointer']=='none' for e in public_badges['examples']),public_badges
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
    # VR01L: mouse drag cannot orbit/pan the new fixed PC board, but
    # drag release must still not cause an accidental original slot click.
    page.wait_for_timeout(450)
    camera_before=page.evaluate("""() => {
      const s=MRRIntegrated.state.scene;
      return {yaw:s.yaw,pitch:s.pitch,manual:s.vrCameraAuto};
    }""")
    canvas=page.locator('#mrr-integrated-stage canvas').first.bounding_box()
    assert canvas and canvas['width']>400,canvas
    x=canvas['x']+canvas['width']*.48
    y=canvas['y']+canvas['height']*.49
    page.mouse.move(x,y)
    page.mouse.down()
    page.mouse.move(x+125,y+64,steps=8)
    page.mouse.up()
    page.wait_for_timeout(220)
    camera_after=page.evaluate("""() => {
      const s=MRRIntegrated.state.scene;
      return {yaw:s.yaw,pitch:s.pitch,manual:s.vrCameraAuto};
    }""")
    assert abs(camera_after['yaw']-camera_before['yaw'])<.001,(
      'VR tabletop should not rotate under drag',camera_before,camera_after)
    assert camera_after['manual'] is True,(
      'A VR board drag must not disable automatic tabletop framing',camera_after)
    assert snap()==baseline,'Dragging the fixed tabletop changed actual Phase21 game'
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
    # VR01P: OS/browser cancellation must never synthesize a card click.
    page.locator('#mrr-integrated-stage canvas').evaluate("""(canvas,p)=>{
      for(const type of ['pointerdown','pointercancel','pointerup'])
        canvas.dispatchEvent(new PointerEvent(type,{bubbles:true,button:0,
          pointerId:1,clientX:p.x,clientY:p.y}));
    }""",xy)
    assert page.locator('#arena .selected-slot').count()==0
    assert snap()==baseline,'Cancelled pointer gesture selected or played a card'
    page.mouse.click(xy['x'],xy['y'])
    page.wait_for_function("""()=>MRRIntegrated.state.scene.selectedKey!==null &&
      !document.querySelector('#mrr-integrated-context').hidden""",timeout=18000)
    # VR01M: only a genuine Phase21 selection triggers a 3D focus accent.
    # It must return to baseline without leaving enlarged click geometry.
    page.wait_for_function("""key=>{
      const state=MRRIntegrated.state.scene;
      return state.selectedKey===key&&state.vrSelectionBursts===1;
    }""",arg=mine,timeout=12000)
    assert page.evaluate('MRRIntegrated.state.scene.pickableCount')>=30
    page.wait_for_function("""() => {
      const s=MRRIntegrated.state.scene;
      return s.vrSelectionBurstKey===null &&
        Math.abs(s.vrSelectionRingScale-1)<.001;
    }""",timeout=12000)
    assert snap()==baseline
    # VR01AC: native contextual actions must remain within all supported
    # PC viewports without covering their selected real 3D card face.
    # This checks the EXISTING native buttons, not a simulated toolbar.
    for ww,hh in ((1920,1080),(1366,768),(2560,1440)):
      page.set_viewport_size({'width':ww,'height':hh})
      page.wait_for_function("""key=>{
        const ctx=document.querySelector('#mrr-integrated-context');
        const stage=document.querySelector('#mrr-integrated-stage');
        if(!ctx||ctx.hidden||!stage)return false;
        const face=MRRIntegrated.scene.projectCardBounds(key);
        if(!face)return false;
        const a=ctx.getBoundingClientRect(),b=stage.getBoundingClientRect();
        const overlap=Math.max(0,Math.min(a.right,face.right)-Math.max(a.left,face.left))*
          Math.max(0,Math.min(a.bottom,face.bottom)-Math.max(a.top,face.top));
        return a.left>=b.left+10&&a.right<=b.right-10 &&
          a.top>=b.top+79&&a.bottom<=b.bottom-110 && overlap<4;
      }""",arg=mine,timeout=16000)
      assert snap()==baseline,('VR01AC layout changed original game',ww,hh)
      if ww==1920:
        # The quick native buttons must not chase the pointer when
        # selected 3D artwork animates or hover focus changes.
        before=page.locator('#mrr-integrated-context').bounding_box()
        action_box=page.locator('#mrr-quick-attack').bounding_box()
        assert before and action_box
        page.mouse.move(action_box['x']+action_box['width']/2,
          action_box['y']+action_box['height']/2)
        page.wait_for_timeout(850)
        after_hover=page.locator('#mrr-integrated-context').bounding_box()
        assert after_hover and abs(after_hover['x']-before['x'])<3 and (
          abs(after_hover['y']-before['y'])<3),('VR01AC jumpy quick command',before,after_hover)
        page.screenshot(path=str(ROOT/'tests/vr01ac_native_context_nonoverlap_1920x1080.png'),
          animations='disabled')
    # VR01AD: stress the actual native toolbar using 22 additional
    # public-DOM-only clones. Do not alter G, effects, original cards or
    # any native legal/attack class. Compare the toolbar against every
    # other projected card face and public status badge at PC widths.
    qa_clones=page.evaluate("""() => {
      const slots=[...document.querySelectorAll('#arena .slot[data-slot]')];
      const template=slots.find(s=>s.querySelector('.board-card'))?.querySelector('.board-card');
      if(!template)return -1;
      let added=0;
      for(const slot of slots){
        if(added>=22)break;
        if(slot.querySelector('.board-card'))continue;
        const clone=template.cloneNode(true);
        clone.dataset.vrAcDenseClone='true';
        slot.append(clone);added++;
      }
      MRRIntegrated.scene.sync();
      return added;
    }""")
    assert qa_clones==22,qa_clones
    # VR01AD: Phase21 may re-render the entire public slot grid whenever
    # the 3D viewport is resized. Hold ONLY synthetic cloned public DOM
    # cards while the dense layout QA is active, never native game state.
    page.evaluate("""() => {
      const arena=document.querySelector('#arena');
      window.__vrAdDenseActive=true;
      window.__vrAdDenseQueued=false;
      window.__vrAdDenseObserver=new MutationObserver(()=>{
        if(!window.__vrAdDenseActive||window.__vrAdDenseQueued)return;
        window.__vrAdDenseQueued=true;
        requestAnimationFrame(()=>{
          window.__vrAdDenseQueued=false;
          if(!window.__vrAdDenseActive)return;
          const slots=[...document.querySelectorAll('#arena .slot[data-slot]')];
          const template=slots.find(s=>s.querySelector(
            '.board-card:not([data-vr-ac-dense-clone])'))?.querySelector('.board-card');
          if(!template)return;
          let count=slots.filter(s=>s.querySelector('.board-card')).length;
          let changed=false;
          for(const slot of slots){
            if(count>=24)break;
            if(slot.querySelector('.board-card'))continue;
            const clone=template.cloneNode(true);
            clone.dataset.vrAcDenseClone='true';slot.append(clone);
            changed=true;count++;
          }
          if(changed)MRRIntegrated.scene.sync();
        });
      });
      window.__vrAdDenseObserver.observe(arena,{childList:true,subtree:true});
    }""")
    # Renderer and native DOM can repaint at different animation frames.
    # Keep the display-only fixture honest: it must contain exactly 24
    # public cards BEFORE accepting a 24-mesh projection snapshot.
    reconcile_dense="""() => {
      const slots=[...document.querySelectorAll('#arena .slot[data-slot]')];
      const template=slots.find(s=>s.querySelector('.board-card:not([data-vr-ac-dense-clone])'))?.querySelector('.board-card');
      if(!template)return false;
      let occupied=slots.filter(s=>s.querySelector('.board-card')).length;
      for(const slot of slots){
        if(occupied>=24)break;
        if(slot.querySelector('.board-card'))continue;
        const copy=template.cloneNode(true);
        copy.dataset.vrAcDenseClone='true';slot.append(copy);occupied++;
      }
      if(occupied!==24)return false;
      if(MRRIntegrated.state.scene.cardMeshCount!==24)MRRIntegrated.scene.sync();
      return MRRIntegrated.state.scene.cardMeshCount===24 &&
        document.querySelectorAll('#arena .slot .board-card').length===24;
    }"""
    page.wait_for_function(reconcile_dense,timeout=40000)
    for ww,hh in ((1920,1080),(1366,768)):
      page.set_viewport_size({'width':ww,'height':hh})
      page.wait_for_timeout(800)
      # Phase21 is permitted to repaint its DOM during resize; restore
      # only synthetic public DISPLAY clones, never engine game state.
      restored=page.evaluate("""() => {
        const slots=[...document.querySelectorAll('#arena .slot[data-slot]')];
        const template=slots.find(s=>s.querySelector('.board-card'))?.querySelector('.board-card');
        if(!template)return -1;
        let total=slots.filter(s=>s.querySelector('.board-card')).length;
        for(const slot of slots){
          if(total>=24)break;
          if(slot.querySelector('.board-card'))continue;
          const copy=template.cloneNode(true);
          copy.dataset.vrAcDenseClone='true';slot.append(copy);total++;
        }
        MRRIntegrated.scene.sync();
        return total;
      }""")
      assert restored==24,('VR01AD viewport fixture repaint',ww,hh,restored)
      page.wait_for_function(reconcile_dense,timeout=30000)
      try:
        page.wait_for_function("""key=>{
        const ctx=document.querySelector('#mrr-integrated-context');
        const stage=document.querySelector('#mrr-integrated-stage');
        const state=MRRIntegrated.state.scene;
        if(!ctx||ctx.hidden||!stage||state.cardMeshCount!==24||
          document.querySelectorAll('#arena .slot .board-card').length!==24)return false;
        const screen=stage.getBoundingClientRect();
        const a=ctx.getBoundingClientRect();
        if(a.left<screen.left+10||a.right>screen.right-10||
          a.top<screen.top+79||a.bottom>screen.bottom-110)return false;
        const intersection=b=>Math.max(0,Math.min(a.right,b.right)-Math.max(a.left,b.left))*
          Math.max(0,Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top));
        const native=[...document.querySelectorAll('#arena .slot[data-slot]')]
          .filter(s=>s.dataset.slot!==key&&s.querySelector('.board-card .card-ui'));
        if(native.length!==23)return false;
        const blocked=native.some(s=>{
          const b=MRRIntegrated.scene.projectCardBounds(s.dataset.slot);
          return !b||intersection(b)>4;
        });
        const marks=[...document.querySelectorAll(
          '#vr-public-plaques .vr-public-action:not([hidden]),'+
          '#vr-public-plaques .vr-public-combat:not([hidden])')];
        return !blocked&&marks.every(e=>intersection(e.getBoundingClientRect())<4);
      }""",arg=mine,timeout=28000)
      except Exception:
        debug=page.evaluate("""key=>{
          const scene=MRRIntegrated.scene,ctx=document.querySelector('#mrr-integrated-context');
          const b=ctx?.getBoundingClientRect(),stage=document.querySelector('#mrr-integrated-stage')?.getBoundingClientRect();
          const overlap=q=>!b||!q?null:Math.max(0,Math.min(b.right,q.right)-Math.max(b.left,q.left))*
            Math.max(0,Math.min(b.bottom,q.bottom)-Math.max(b.top,q.top));
          return {selected:scene.state.selectedKey,meshes:scene.state.cardMeshCount,
            dom:document.querySelectorAll('#arena .slot .board-card').length,
            contextHidden:ctx?.hidden,context:b?.toJSON(),stage:stage?.toJSON(),
            publicCards:[...document.querySelectorAll('#arena .slot[data-slot]')]
              .filter(s=>s.dataset.slot!==key&&s.querySelector('.board-card .card-ui'))
              .map(s=>({key:s.dataset.slot,area:overlap(scene.projectCardBounds(s.dataset.slot))}))
              .filter(s=>s.area===null||s.area>4),
            marks:[...document.querySelectorAll('#vr-public-plaques .vr-public-combat:not([hidden]),#vr-public-plaques .vr-public-action:not([hidden])')]
              .map(s=>({key:s.dataset.slot,area:overlap(s.getBoundingClientRect())}))
              .filter(s=>s.area===null||s.area>4)};
        }""",mine)
        print('VR01AD DENSE QA DIAGNOSTIC',ww,hh,debug,flush=True)
        raise
      assert snap()==baseline,('VR01AD dense display changed native game',ww,hh)
      page.screenshot(path=str(ROOT/f'tests/vr01ad_dense_native_context_{ww}x{hh}.png'),
        animations='disabled')
    page.evaluate("""() => {
      window.__vrAdDenseActive=false;
      window.__vrAdDenseObserver?.disconnect();
      window.__vrAdDenseObserver=null;
      document.querySelectorAll('[data-vr-ac-dense-clone]').forEach(n=>n.remove());
      MRRIntegrated.scene.sync();
    }""")
    page.wait_for_function('MRRIntegrated.state.scene.cardMeshCount===2',timeout=26000)
    page.set_viewport_size({'width':1920,'height':1080})
    page.wait_for_function("""key=>{
      const ctx=document.querySelector('#mrr-integrated-context');
      return !ctx.hidden&&MRRIntegrated.state.scene.selectedKey===key;
    }""",arg=mine,timeout=14000)
    assert page.locator('#mrr-quick-attack').is_visible()
    assert snap()==baseline
    # VR01AD: removing display-only stress cards deliberately produces
    # cosmetic 3D exit effects. Let them finish and use this counter as a
    # strict baseline for the NEXT genuinely native Phase21 attack.
    page.wait_for_function('MRRIntegrated.state.scene.vrDepartActive===0',timeout=15000)
    departures_before_native_attack=page.evaluate(
      'MRRIntegrated.state.scene.vrDepartStarted')
    before_hp=page.evaluate("""key=>{const [owner,row,col]=key.split(':');
      return G.players[+owner][row][+col]?.hp}""",opponent)
    assert before_hp and before_hp>0
    # VR01Y: the handoff-safe A shortcut must invoke the one existing,
    # genuinely enabled Phase21 attack command, not simulate an attack.
    page.wait_for_function("""() => {
      const b=document.querySelector('#mrr-quick-attack');
      const original=document.querySelector('#inspectBody button[data-actor="attack"]');
      return !!MRRIntegrated.state.scene.selectedKey && b&&!b.hidden &&
        !document.querySelector('#mrr-integrated-context').hidden &&
        original&&!original.disabled &&
        document.querySelector('#vr-hint').dataset.mode==='selected' &&
        document.querySelector('#vr-hint-text').textContent.includes('A 공격');
    }""",timeout=12000)
    assert snap()==baseline
    page.keyboard.press('a')
    page.wait_for_function('MRRIntegrated.state.scene.attackTargetCount>0',timeout=13000)
    assert snap()==baseline,'VR01Y attack initiation spent native resources'
    page.wait_for_selector('#vr-cancel:not([hidden])')
    page.wait_for_function("""() => {
      const count=document.querySelectorAll('#arena .slot.attack-target').length;
      const hint=document.querySelector('#vr-hint');
      return count>0 && hint?.dataset.mode==='attack' &&
        document.querySelector('#vr-hint-mode')?.textContent==='공격' &&
        document.querySelector('#vr-hint-text')?.textContent.includes(count+'곳');
    }""",timeout=14000)
    assert snap()==baseline,'VR01X attack command strip changed Phase21 state'
    page.screenshot(path=str(ROOT/'tests/vr01x_native_attack_command_1920x1080.png'),
      animations='disabled')
    # VR01W: the new C shortcut must perform exactly the same native
    # cancellation as the previous on-screen click; no HP/mana spending.
    assert page.locator('#vr-cancel').get_attribute('aria-keyshortcuts')=='C'
    assert page.locator('#vr-cancel .vr-cancel-key').inner_text()=='C'
    assert page.locator('#vr-cancel .vr-cancel-key').evaluate(
      'e=>getComputedStyle(e).pointerEvents')=='none'
    page.screenshot(path=str(ROOT/'tests/vr01w_native_cancel_command_1920x1080.png'),
      animations='disabled')
    page.keyboard.press('c')
    page.wait_for_function("""() => MRRIntegrated.state.scene.attackTargetCount===0 &&
      MRRIntegrated.state.scene.vrTargetLockKey===null &&
      !document.querySelector('#vr-aim-line').getAttribute('d') &&
      !document.querySelector('#vr-guide-targets').children.length""",timeout=14000)
    assert page.evaluate('MRRVR.status.open')
    assert snap()==baseline,'Native attack cancellation changed game resources'
    # The attack declaration cannot be overwritten by M/A; C is the
    # only VR shortcut allowed to cancel this Phase21-native state.
    page.locator('#mrr-quick-attack').click(timeout=12000)
    page.wait_for_function('MRRIntegrated.state.scene.attackTargetCount>0',timeout=13000)
    attack_targets_before=page.evaluate('MRRIntegrated.state.scene.attackTargetCount')
    page.keyboard.press('m')
    page.keyboard.press('a')
    assert page.evaluate('MRRIntegrated.state.scene.attackTargetCount')==attack_targets_before
    assert snap()==baseline,'VR01Y repeated A/M altered active native attack'
    # VR01I: the target icon only appears on a genuinely native-marked
    # attack target; aiming itself must not produce a fabricated attack.
    page.wait_for_function("""() => {
      const card=[...document.querySelectorAll('#arena .slot.attack-target')]
        .find(s=>s.querySelector('.board-card .card-ui'));
      if(!card)return false;
      const mark=document.querySelector('#vr-public-plaques .vr-public-action[data-slot="'+card.dataset.slot+'"]');
      return mark?.dataset.state==='target'&&!mark.hidden&&
        getComputedStyle(mark).pointerEvents==='none';
    }""",timeout=14000)
    assert snap()==baseline,'Aiming cannot alter the engine'
    assert page.evaluate('MRRVR.status.nativeOutcomes')==0,(
      'Starting a speculative attack must not produce a damage result')
    # VR01J: all candidate reticles come from truly native legal attack
    # targets; no arbitrary mouse-location path can imply an attack.
    guide=page.evaluate("""() => ({
      expected:[...document.querySelectorAll('#arena .slot.attack-target')]
        .filter(x=>x.querySelector('.board-card .card-ui')).map(x=>x.dataset.slot).sort(),
      actual:[...document.querySelectorAll('#vr-guide-targets .vr-target-guide')]
        .map(x=>x.dataset.slot).sort(),
      path:document.querySelector('#vr-aim-line')?.getAttribute('d')
    })""")
    assert guide['expected'] and guide['expected']==guide['actual'],guide
    # VR01R: the target guide follows the REAL projected card face rather
    # than a fixed 20px circle; never attach click geometry to an SVG guide.
    outlines=page.evaluate("""() => {
      const stage=document.querySelector('#mrr-integrated-stage').getBoundingClientRect();
      return [...document.querySelectorAll('#vr-guide-targets .vr-target-guide')].map(node=>{
        const b=MRRIntegrated.scene.projectCardBounds(node.dataset.slot);
        if(!b)return {tag:node.localName,error:999};
        const w=b.right-b.left,h=b.bottom-b.top;
        const i=Math.min(9,Math.min(w,h)*.065);
        const expected=[b.left-stage.left+i,b.top-stage.top+i,
          Math.max(2,w-i*2),Math.max(2,h-i*2)];
        const actual=['x','y','width','height'].map(v=>Number(node.getAttribute(v)));
        return {tag:node.localName,width:actual[2],height:actual[3],
          error:Math.max(...actual.map((value,index)=>Math.abs(value-expected[index]))),
          pointer:getComputedStyle(node).pointerEvents};
      });
    }""")
    assert outlines and all(o['tag']=='rect' and o['width']>20 and
      o['height']>30 and o['error']<1 and o['pointer']=='none'
      for o in outlines),outlines
    page.screenshot(path=str(ROOT/'tests/vr01_attack_target_1920x1080.png'),animations='disabled')
    target=page.evaluate('(key)=>MRRIntegrated.scene.projectCard(key)',opponent)
    assert target and 0<target['x']<1920 and 0<target['y']<1080
    page.mouse.move(target['x'],target['y'])
    page.wait_for_function("""key=>MRRIntegrated.state.scene.hoveredKey===key &&
      document.querySelector('#vr-aim-line')?.dataset.target===key &&
      !!document.querySelector('#vr-aim-line')?.getAttribute('d')""",
      arg=opponent,timeout=15000)
    # VR01N: only a genuinely native target hover creates one bounded,
    # temporary lock-on accent; moving off clears it without touching
    # damage or inventing legal actions.
    page.wait_for_function("""key=>{
      const s=MRRIntegrated.state.scene;
      return s.vrTargetLockKey===key&&s.vrTargetLocks===1&&
        s.vrTargetLockScale>1.07&&s.vrTargetLockScale<1.5;
    }""",arg=opponent,timeout=14000)
    page.mouse.move(3,550)
    page.wait_for_function("""()=>MRRIntegrated.state.scene.vrTargetLockKey===null&&
      !document.querySelector('#vr-aim-line').getAttribute('d')""",timeout=12000)
    assert page.evaluate('MRRIntegrated.state.scene.vrTargetLocks')==1
    assert snap()==baseline,'Changing the cursor changed Phase21 gameplay'
    page.mouse.move(target['x'],target['y'])
    page.wait_for_function("""key=>{
      const s=MRRIntegrated.state.scene;
      return s.vrTargetLockKey===key&&s.vrTargetLocks===2&&
        document.querySelector('#vr-aim-line')?.dataset.target===key;
    }""",arg=opponent,timeout=15000)
    assert snap()==baseline,'Hovering native aim cue changed game state'
    page.screenshot(path=str(ROOT/'tests/vr01_attack_lockon_1920x1080.png'),animations='disabled')
    # Capture VR01S feedback at the actual native FX DOM insertion, not
    # seconds afterward when its short-lived badge may have expired.
    page.evaluate("""key=>{
      window.__vr01sAnchorResult=null;
      const host=document.querySelector('#vr-combat-outcomes');
      const observer=new MutationObserver(()=>{
        const badge=[...host.querySelectorAll('.vr-combat-outcome')]
          .find(e=>e.dataset.slot===key&&e.dataset.kind==='hit');
        if(!badge)return;
        observer.disconnect();
        try{
          const stage=document.querySelector('#mrr-integrated-stage');
          const button=document.querySelector('#vr-camera');
          button.click();
          const scene=MRRIntegrated.scene;
          const preset=scene.state.cameraPreset;
          window.dispatchEvent(new Event('resize'));
          const point=scene.projectCard(key)||scene.projectSlot(key);
          const rect=stage.getBoundingClientRect();
          const expected=[Math.max(42,Math.min(rect.width-42,point.x-rect.left)),
            Math.max(92,Math.min(rect.height-88,point.y-rect.top-30))];
          const actual=[parseFloat(badge.style.left),parseFloat(badge.style.top)];
          button.click();button.click();
          window.__vr01sAnchorResult={present:true,preset,expected,actual,
            delta:Math.max(...expected.map((v,i)=>Math.abs(v-actual[i])))};
        }catch(error){window.__vr01sAnchorResult={error:String(error)};}
      });
      observer.observe(host,{childList:true});
    }""",opponent)
    page.mouse.click(target['x'],target['y'])
    page.wait_for_function("""v=>{const [owner,row,col]=v.key.split(':');
      return (G.players[+owner][row][+col]?.hp||0)<v.hp}""",
      arg={'key':opponent,'hp':before_hp},timeout=13000)
    after=snap()
    assert after!=baseline
    # VR01K: ONLY original Phase21 confirmed native FX may render an impact
    # badge. Merely selecting, aiming or hovering must not create one.
    page.wait_for_function("""key=>{
      const state=MRRVR.status;
      return state.nativeOutcomes>=1&&state.outcomeHistory.some(
        event=>event.key===key&&event.type==='hit');
    }""",arg=opponent,timeout=14000)
    outcome=page.evaluate("""key=>{
      const vr=MRRVR.status,scene=MRRIntegrated.state.scene;
      return {events:vr.outcomeHistory.filter(e=>e.key===key&&e.type==='hit'),
        rawEvents:scene.nativeCombatEvents};
    }""",opponent)
    assert outcome['events'] and all(e['label'] and
      (e['amount'] is None or e['amount']>0) for e in outcome['events']),outcome
    # VR01S: genuine hit feedback must follow the projected card when
    # the camera changes and never affect native Phase21 gameplay.
    page.wait_for_function('window.__vr01sAnchorResult!==null',timeout=14000)
    anchor=page.evaluate('window.__vr01sAnchorResult')
    assert anchor.get('present') and anchor.get('preset')=='ally' and anchor.get('delta',999)<2,anchor
    assert snap()==after,'Camera-tracked visual feedback modified Phase21 state'
    page.screenshot(path=str(ROOT/'tests/vr01_native_confirmed_impact_1920x1080.png'),animations='disabled')
    # Native confirmed damage must refresh the badge to the CURRENT public
    # health value. If the native card is destroyed, its badge must disappear.
    page.wait_for_function("""key => {
      const el=document.querySelector('#arena [data-slot="'+key+'"]');
      const card=el?.querySelector('.board-card .card-ui');
      const badge=document.querySelector('#vr-public-plaques .vr-public-combat[data-slot="'+key+'"]');
      if(!card)return !badge;
      const span=[...card.querySelectorAll('.card-stats > span')]
        .find(e=>/^체(?:력)?\\s*\\d+/.test(e.textContent.trim()));
      const hp=span?.textContent.trim().match(/^체(?:력)?\\s*(\\d+)/);
      return !!(hp&&badge&&!badge.hidden&&badge.dataset.publicHealth===hp[1]);
    }""",arg=opponent,timeout=12000)
    if page.locator(f'#arena [data-slot="{opponent}"] .board-card').count():
      page.wait_for_function('MRRIntegrated.state.scene.vrHitReactions>=1',timeout=13000)
    assert page.evaluate('MRRIntegrated.state.scene.vrHitReactions')>=0
    # VR01O: only the original native targeting state can retain a
    # lock-on after resolution; there must never be an orphaned VR target.
    page.wait_for_function("""() => {
      const s=MRRIntegrated.state.scene;
      if(s.attackTargetCount)return true;
      return s.vrTargetLockKey===null &&
        document.querySelectorAll('#vr-guide-targets .vr-target-guide').length===0 &&
        !document.querySelector('#vr-aim-line')?.getAttribute('d');
    }""",timeout=14000)
    if page.locator(f'#arena [data-slot="{opponent}"] .board-card').count()==0:
      page.wait_for_function(
        'base=>MRRIntegrated.state.scene.vrDepartStarted>base',
        arg=departures_before_native_attack,timeout=14000)
    else:
      assert page.evaluate('MRRIntegrated.state.scene.vrDepartStarted')==(
        departures_before_native_attack),(
        'An ordinary surviving hit must not cause a NEW card destruction')
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
      # VR01Z QA stabilization: the perspective camera eases after resize,
      # whereas display-only public stat badges refresh periodically. A
      # single immediate sample can compare different camera frames.
      # REQUIRE actual native projection and every badge to agree within
      # the original 3px tolerance; never relax the geometry assertion.
      page.wait_for_function("""expected => {
        const cards=[...document.querySelectorAll('#arena [data-slot]')]
          .filter(e=>e.querySelector('.board-card .card-ui'));
        if(cards.length!==expected)return false;
        for(const slot of cards){
          const key=slot.dataset.slot;
          const badge=document.querySelector(
            '#vr-public-plaques .vr-public-combat[data-slot="'+key+'"]');
          const face=MRRIntegrated.scene.projectCardBounds(key);
          if(!face||!badge||badge.hidden)return false;
          const box=badge.getBoundingClientRect();
          if(box.left<face.left-3||box.right>face.right+3||
            box.top<face.top-3||box.bottom>face.bottom+3)return false;
        }
        return true;
      }""",arg=count,timeout=24000)
      # Every synthetic dense unit is a CLONE of an already-public original.
      # Verify all 24 corner badges reflect their matching public DOM and
      # lie within their original projected 3D faces, with no hidden reads.
      combat=page.evaluate("""() => {
        const cards=[...document.querySelectorAll('#arena [data-slot]')]
          .filter(e=>e.querySelector('.board-card .card-ui'));
        const errors=[],rects=[],scene=MRRIntegrated.scene;
        for(const slot of cards){
          const values=[...slot.querySelectorAll('.card-stats > span')]
            .map(s=>s.textContent.replace(/\\s+/g,' ').trim());
          const a=values.map(s=>s.match(/^(검|공)(?:격력)?\\s*(\\d+)/)).find(Boolean);
          const h=values.map(s=>s.match(/^체(?:력)?\\s*(\\d+)/)).find(Boolean);
          if(!a||!h)continue;
          const key=slot.dataset.slot,overlay=document.querySelector(
            '#vr-public-plaques .vr-public-combat[data-slot="'+key+'"]');
          if(!overlay||overlay.hidden){errors.push([key,'missing']);continue;}
          if(overlay.dataset.publicAttack!==a[2]||overlay.dataset.publicHealth!==h[1])
            errors.push([key,'not-live-public',overlay.dataset.publicAttack,overlay.dataset.publicHealth]);
          const face=scene.projectCardBounds(key),box=overlay.getBoundingClientRect();
          if(!face||box.left<face.left-3||box.right>face.right+3||
              box.top<face.top-3||box.bottom>face.bottom+3)
            errors.push([key,'outside-own-card',face,box.toJSON()]);
          if(getComputedStyle(overlay).pointerEvents!=='none')
            errors.push([key,'blocks-native-hit']);
          rects.push({key,rect:box});
        }
        const overlap=[];
        for(let i=0;i<rects.length;i++)for(let j=i+1;j<rects.length;j++){
          const a=rects[i].rect,b=rects[j].rect;
          if(a.left<b.right-1&&a.right>b.left+1&&a.top<b.bottom-1&&a.bottom>b.top+1)
            overlap.push([rects[i].key,rects[j].key]);
        }
        return {verified:rects.length,errors,overlap};
      }""")
      assert combat['verified']==count and not combat['errors'] and not combat['overlap'],(w,h,combat)
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
    # VR01I: controlled PUBLIC DOM-only status transitions. Clone an
    # already-public card in a synthetic occupied field slot, alter only
    # its original status-chip or original slot marker, and verify the
    # dedicated icon follows EXACT native DOM labels without changing G.
    qa_states=page.evaluate("""() => {
      const sources=[...document.querySelectorAll('#arena [data-slot]')]
        .filter(s=>s.querySelector('.board-card[data-vr-stress-clone]'));
      const cases=[
        ['acted','행동 완료',null],
        ['waiting','대기',null],
        ['ward','보호 2',null],
        ['selected','', 'selected-slot'],
        ['target','', 'attack-target'],
        ['legal','', 'legal'],
        ['other','완성',null],
        ['none','',null]
      ];
      if(sources.length<cases.length)return {error:'Insufficient public synthetic units'};
      return cases.map(([kind,txt,cls],i)=>{
        const slot=sources[i];
        slot.dataset.vrQaAction=kind;
        slot.classList.remove('attack-target','selected-slot','legal');
        slot.querySelector('.board-card .status-chip')?.remove();
        if(txt){
          const chip=document.createElement('span');
          chip.className='status-chip';chip.textContent=txt;
          slot.querySelector('.board-card').append(chip);
        }
        if(cls)slot.classList.add(cls);
        return {key:slot.dataset.slot,kind,label:txt};
      });
    }""")
    assert isinstance(qa_states,list) and len(qa_states)==8,qa_states
    page.wait_for_function("""cases => cases.every(({key,kind})=>{
      const mark=document.querySelector('#vr-public-plaques .vr-public-action[data-slot="'+key+'"]');
      return kind==='none'?(!mark||mark.hidden):
        !!(mark&&!mark.hidden&&mark.dataset.state===kind);
    })""",arg=qa_states,timeout=18000)
    checked=page.evaluate("""cases=>{
      const stage=MRRIntegrated.scene,bad=[],boxes=[];
      for(const c of cases){
        const mark=document.querySelector('#vr-public-plaques .vr-public-action[data-slot="'+c.key+'"]');
        if(c.kind==='none'){
          if(mark&&!mark.hidden)bad.push([c.key,'invented-ready-state']);
          continue;
        }
        const face=stage.projectCardBounds(c.key),box=mark?.getBoundingClientRect();
        if(!box||!face||box.left<face.left-3||box.right>face.right+3||
            box.top<face.top-3||box.bottom>face.bottom+3)
          bad.push([c.key,'outside-face',face,box?.toJSON()]);
        if(getComputedStyle(mark).pointerEvents!=='none')
          bad.push([c.key,'blocks-native-raycast']);
        if(c.label&&mark.title!==c.label)
          bad.push([c.key,'wrong-public-state',mark.title,c.label]);
        const combat=document.querySelector(
          '#vr-public-plaques .vr-public-combat[data-slot="'+c.key+'"]');
        if(combat&&!combat.hidden){
          const a=combat.getBoundingClientRect();
          if(box.left<a.right-1&&box.right>a.left+1&&
             box.top<a.bottom-1&&box.bottom>a.top+1)
            bad.push([c.key,'overlaps-attack-health']);
        }
        boxes.push([c.key,box]);
      }
      for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++){
        const a=boxes[i][1],b=boxes[j][1];
        if(a.left<b.right-1&&a.right>b.left+1&&
           a.top<b.bottom-1&&a.bottom>b.top+1)
          bad.push([boxes[i][0],boxes[j][0],'state-icons-overlap']);
      }
      return {checked:cases.length,errors:bad};
    }""",qa_states)
    assert checked['checked']==8 and not checked['errors'],checked
    assert snap()==dense_native,'Status fixtures must never touch Phase21 engine'
    page.screenshot(path=str(ROOT/'tests/vr01_dense_action_states_1366x768.png'),animations='disabled')
    page.evaluate("""() => {
      for(const slot of document.querySelectorAll('[data-vr-qa-action]')){
        slot.classList.remove('selected-slot','attack-target','legal');
        slot.removeAttribute('data-vr-qa-action');
      }
    }""")
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
    # VR01O synthetic DISPLAY fixture verifies departure effects cannot
    # leave ghost cards, inject click surfaces, or leak GPU resources.
    effects=page.evaluate("""() => ({
      departing:MRRIntegrated.state.scene.vrDepartStarted,
      active:MRRIntegrated.state.scene.vrDepartActive,
      pickable:MRRIntegrated.state.scene.pickableCount
    })""")
    # The cumulative count can exceed seven across successive syncs;
    # GPU load is bounded by at most seven simultaneously live bursts.
    assert effects['departing']>=1 and 0<=effects['active']<=7,effects
    assert effects['pickable']==30+stress['originals']*2,effects
    page.wait_for_function('MRRIntegrated.state.scene.vrDepartActive===0',timeout=8000)
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
        page.wait_for_selector('#vr-cancel:not([hidden])')
        page.wait_for_function("""() => {
          const count=document.querySelectorAll('#arena .slot.legal').length;
          const hint=document.querySelector('#vr-hint');
          return count>0 && hint?.dataset.mode==='place' &&
            document.querySelector('#vr-hint-mode')?.textContent==='배치' &&
            document.querySelector('#vr-hint-text')?.textContent.includes(count+'곳');
        }""",timeout=14000)
        # VR01AA: every projected ring must match one genuine empty native
        # placement candidate. It cannot catch a click or fake a target.
        page.wait_for_function("""() => {
          const source=[...document.querySelectorAll('#arena .slot.legal')]
            .filter(s=>!s.querySelector('.board-card .card-ui'));
          const rings=[...document.querySelectorAll('#vr-guide-targets .vr-legal-guide')];
          if(!source.length||source.length!==rings.length)return false;
          return source.every(slot=>{
            const key=slot.dataset.slot;
            const ring=rings.find(e=>e.dataset.slot===key);
            const point=MRRIntegrated.scene.projectSlot(key);
            const frame=document.querySelector('#mrr-integrated-stage').getBoundingClientRect();
            return ring?.dataset.mode==='place'&&point &&
              Math.abs(Number(ring.getAttribute('cx'))+frame.left-point.x)<2.5 &&
              Math.abs(Number(ring.getAttribute('cy'))+frame.top-point.y)<2.5 &&
              getComputedStyle(ring).pointerEvents==='none';
          });
        }""",timeout=15000)
        assert snap()==prior,'VR01AA marker changed native placement state'
        page.screenshot(path=str(ROOT/'tests/vr01aa_native_place_guides_1920x1080.png'),
          animations='disabled')
        page.screenshot(path=str(ROOT/'tests/vr01x_native_place_command_1920x1080.png'),
          animations='disabled')
        page.locator('#vr-cancel').click()
        page.wait_for_function("""() => !document.querySelector('#arena .slot.legal') &&
          !document.querySelector('#mrr-vr-shell').classList.contains('vr-placing')""",timeout=14000)
        assert snap()==prior,'Cancelling hand placement spent native resources'
        page.wait_for_function("""() =>
          !document.querySelector('#hand .hand-slot.active') &&
          !document.querySelector('#vr-hand .vr-card.vr-native-selected') &&
          [...document.querySelectorAll('#vr-hand .vr-card')]
            .every(card=>card.getAttribute('aria-pressed')==='false')
        """,timeout=14000)
        # VR01U: select the very same genuine Phase21 card with its PC
        # number hotkey. This must only enter native placement selection,
        # without paying mana or changing the original game snapshot.
        assert candidate['i']<10,'VR01U supports the first ten hand positions'
        shortcut='0' if candidate['i']==9 else str(candidate['i']+1)
        assert page.locator('#vr-hand .vr-card').nth(candidate['i']).get_attribute(
          'aria-keyshortcuts')==shortcut
        page.evaluate('document.activeElement?.blur()')
        page.keyboard.press(shortcut)
        page.wait_for_function("!!document.querySelector('#arena .slot.legal')")
        assert snap()==prior,'VR01U numeric hand selection spent native resources'
        # VR01V: the mirrored keycap is legible and the SINGLE highlighted
        # card must match the original native selection, including after the
        # fan updates through the normal render path.
        page.wait_for_function("""index => {
          const native=[...document.querySelectorAll('#hand .hand-slot')];
          const mirror=[...document.querySelectorAll('#vr-hand .vr-card')];
          if(!native[index]?.classList.contains('active'))return false;
          return mirror.length===native.length&&mirror.every((card,i)=>{
            const selected=native[i].classList.contains('active');
            const keycap=card.querySelector('.vr-shortcut-key');
            return card.classList.contains('vr-native-selected')===selected &&
              card.getAttribute('aria-pressed')===(selected?'true':'false') &&
              (i<10?keycap?.textContent===(i===9?'0':String(i+1)):!keycap);
          });
        }""",arg=candidate['i'],timeout=14000)
        highlighted=page.locator('#vr-hand .vr-card.vr-native-selected')
        assert highlighted.count()==1
        assert highlighted.first.get_attribute('data-index')==str(candidate['i'])
        assert highlighted.first.locator('.vr-shortcut-key').evaluate(
          "e=>getComputedStyle(e).pointerEvents")=='none'
        visible_key=highlighted.first.evaluate("""card=>{
          const badge=card.querySelector('.vr-shortcut-key');
          const a=badge.getBoundingClientRect(),b=card.getBoundingClientRect();
          return {key:badge.textContent.trim(),badgeTop:a.top,
            badgeBottom:a.bottom,cardTop:b.top,
            computed:getComputedStyle(badge).visibility,
            viewportHeight:innerHeight};
        }""")
        assert visible_key['key']==shortcut and visible_key['computed']=='visible',visible_key
        assert 0<visible_key['badgeTop']<visible_key['cardTop'] and (
          visible_key['badgeBottom']<visible_key['viewportHeight']),visible_key
        page.screenshot(path=str(ROOT/'tests/vr01v_numeric_native_selection_1920x1080.png'),
          animations='disabled')
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
        page.wait_for_function("""key=>{
          const slot=document.querySelector('#arena [data-slot="'+key+'"]');
          const chip=slot?.querySelector('.board-card .status-chip')?.textContent.trim()||'';
          const expected=slot?.classList.contains('attack-target')?'target':
            slot?.classList.contains('selected-slot')?'selected':
            slot?.classList.contains('legal')?'legal':
            /행동 완료/.test(chip)?'acted':
            /^대기/.test(chip)?'waiting':
            /^보호/.test(chip)?'ward':chip?'other':null;
          const mark=document.querySelector('#vr-public-plaques .vr-public-action[data-slot="'+key+'"]');
          return expected?!!(mark&&!mark.hidden&&mark.dataset.state===expected):
            !mark||mark.hidden;
        }""",arg=dest,timeout=13000)
        assert snap()!=prior,'The status marker must not change native game state'
        page.screenshot(path=str(ROOT/'tests/vr01_native_deploy_landed_1920x1080.png'),animations='disabled')
        page.locator('#vr-end-turn').click()
        page.wait_for_selector('#passContinue',timeout=12000)
        # VR01T: a real local turn handoff must hide the next player's
        # mirrored THREE/DOM hand BEFORE the Phase21 reveal confirmation.
        shield=page.evaluate("""() => {
          const overlay=document.querySelector('#overlay');
          const hand=document.querySelector('#vr-hand');
          const hint=document.querySelector('#vr-hint');
          const original=document.querySelector('#hand');
          return {nativePass:!!overlay&&!overlay.classList.contains('hidden')&&
              !!document.querySelector('#passContinue'),
            handVisibility:getComputedStyle(hand).visibility,
            hintVisibility:getComputedStyle(hint).visibility,
            nativeHandCount:original.querySelectorAll('.hand-slot').length,
            mirrorCount:hand.querySelectorAll('.vr-card').length,
            vrOpen:MRRVR.status.open};
        }""")
        assert shield['nativePass'] and shield['vrOpen'],shield
        assert shield['handVisibility']=='hidden' and shield['hintVisibility']=='hidden',shield
        assert page.locator('#vr-hand .vr-card:visible').count()==0,(
          'VR01T handoff must not expose either player hand in the 3D shell')
        # VR01U hotkeys must not bypass the private turn handoff, even if
        # the next player's genuine native hand already exists underneath.
        shield_snapshot=snap()
        page.keyboard.press(shortcut)
        page.keyboard.press('a')
        page.keyboard.press('m')
        page.keyboard.press('c')
        assert snap()==shield_snapshot,'PC shortcut bypassed Phase21 privacy overlay'
        assert page.locator('#passContinue').count()==1
        assert page.locator('#vr-hand .vr-card:visible').count()==0
        page.screenshot(path=str(ROOT/'tests/vr01t_turn_pass_private_1920x1080.png'),
          animations='disabled')
        # ONLY the real Phase21 continuation can expose the next hand.
        page.locator('#passContinue').click(timeout=12000)
        page.wait_for_function("""() => !document.querySelector('#passContinue') &&
          document.querySelector('#overlay').classList.contains('hidden') &&
          getComputedStyle(document.querySelector('#vr-hand')).visibility==='visible' &&
          document.querySelectorAll('#vr-hand .vr-card').length===
          document.querySelectorAll('#hand .hand-slot').length""",timeout=18000)
        assert page.evaluate('MRRVR.status.open'),(
          'Native turn handoff must preserve the 3D PC session')
        page.screenshot(path=str(ROOT/'tests/vr01t_turn_pass_revealed_1920x1080.png'),
          animations='disabled')
        placed=True
        print('VR01T native protected pass, next hand reveal and uninterrupted VR PASS',flush=True)
        break
      if placed:break
      page.locator('#vr-return').evaluate('e=>e.click()')
    assert placed,'No genuine VR mouse hand placement + turn cycle was verified'

    # VR01Z: a separate REAL local two-player turn cycle tests M from
    # selection through Phase21 movement, including cancellation and
    # an occupied action after moving. No synthetic game state fixtures.
    page.goto(url+f'?qa_seed={move_seed}',wait_until='domcontentloaded')
    page.locator('#newGame').click()
    page.locator('#modeSelect').select_option('local')
    page.locator('#launchGame').click()
    page.get_by_role('button',name='이 손패로 시작').click()
    moving_source=set_unit(0)
    assert moving_source,'VR01Z could not summon genuine player unit'
    page.locator('#endTurn').evaluate('e=>e.click()')
    page.wait_for_selector('#passContinue')
    page.locator('#passContinue').click()
    assert set_unit(1),'VR01Z could not prepare real opposing turn'
    page.locator('#endTurn').evaluate('e=>e.click()')
    page.wait_for_selector('#passContinue')
    page.locator('#passContinue').click()
    assert page.locator(f'#arena [data-slot="{moving_source}"] .board-card').count()==1
    prior_move=snap()
    page.locator('#mrr-vr-open').click()
    page.wait_for_function('MRRVR.status.open && MRRIntegrated.state.scene.frames>5',
      timeout=45000)
    origin=page.evaluate('k=>MRRIntegrated.scene.projectSlot(k)',moving_source)
    assert origin and 0<origin['x']<1920 and 0<origin['y']<1080,origin
    page.mouse.click(origin['x'],origin['y'])
    page.wait_for_function("""key=>{
      const quick=document.querySelector('#mrr-quick-move');
      const native=document.querySelector('#inspectBody button[data-actor="move"]');
      const hint=document.querySelector('#vr-hint-text');
      return MRRIntegrated.state.scene.selectedKey===key && quick&&!quick.hidden &&
        native&&!native.disabled && hint?.textContent.includes('M 이동');
    }""",arg=moving_source,timeout=14000)
    assert snap()==prior_move,'Selecting move source changed native state'

    page.keyboard.press('m')
    page.wait_for_function("""() => {
      const legal=document.querySelectorAll('#arena .slot.legal').length;
      return legal>0 &&
        document.querySelector('#vr-hint')?.dataset.mode==='move' &&
        document.querySelector('#vr-hint-mode')?.textContent==='이동' &&
        document.querySelector('#vr-hint-text')?.textContent.includes(legal+'곳');
    }""",timeout=16000)
    candidates=page.locator('#arena .slot.legal').evaluate_all(
      'els=>els.map(e=>e.dataset.slot)')
    assert candidates and all(
      key.split(':')[0]==moving_source.split(':')[0] and
      key.split(':')[1]==moving_source.split(':')[1] and
      abs(int(key.split(':')[2])-int(moving_source.split(':')[2]))==1
      for key in candidates),candidates
    assert snap()==prior_move,'M selection changed native gameplay state'
    page.wait_for_function("""() => {
      const native=[...document.querySelectorAll('#arena .slot.legal')]
        .filter(s=>!s.querySelector('.board-card .card-ui'));
      const guides=[...document.querySelectorAll('#vr-guide-targets .vr-legal-guide')];
      if(!native.length||native.length!==guides.length)return false;
      const stage=document.querySelector('#mrr-integrated-stage').getBoundingClientRect();
      return native.every(slot=>{
        const ring=guides.find(e=>e.dataset.slot===slot.dataset.slot);
        const p=MRRIntegrated.scene.projectSlot(slot.dataset.slot);
        return !!ring&&ring.dataset.mode==='move'&&!!p &&
          Math.abs(Number(ring.getAttribute('cx'))+stage.left-p.x)<2.5 &&
          Math.abs(Number(ring.getAttribute('cy'))+stage.top-p.y)<2.5 &&
          getComputedStyle(ring).pointerEvents==='none';
      });
    }""",timeout=16000)
    page.screenshot(path=str(ROOT/'tests/vr01aa_native_move_guides_1920x1080.png'),
      animations='disabled')
    # VR01AB: hover a true adjacent legal slot through the real canvas.
    # This must highlight exactly that slot and display only a visual
    # source-to-destination path; Phase21 snapshot stays unchanged.
    hovered_target=candidates[0]
    hovered_point=page.evaluate('k=>MRRIntegrated.scene.projectSlot(k)',hovered_target)
    assert hovered_point and 0<hovered_point['x']<1920 and (
      0<hovered_point['y']<1080),hovered_point
    page.mouse.move(hovered_point['x'],hovered_point['y'])
    page.wait_for_function("""key=>{
      const line=document.querySelector('#vr-aim-line');
      const guides=[...document.querySelectorAll('#vr-guide-targets .vr-legal-guide')];
      const hover=guides.filter(g=>g.classList.contains('vr-legal-hover'));
      return MRRIntegrated.state.scene.hoveredKey===key &&
        line?.dataset.target===key&&line.dataset.mode==='move' &&
        !!line.getAttribute('d') &&
        line.getAttribute('marker-end')==='url(#vr-move-arrow)' &&
        hover.length===1&&hover[0].dataset.slot===key &&
        getComputedStyle(line).pointerEvents==='none';
    }""",arg=hovered_target,timeout=16000)
    assert snap()==prior_move,'VR01AB hover preview changed native game'
    page.screenshot(path=str(ROOT/'tests/vr01ab_native_move_hover_1920x1080.png'),
      animations='disabled')
    page.mouse.move(4,540)
    page.wait_for_function("""() => {
      const line=document.querySelector('#vr-aim-line');
      return !line?.getAttribute('d')&&!line?.dataset.target &&
        !document.querySelector('#vr-guide-targets .vr-legal-guide.vr-legal-hover');
    }""",timeout=16000)
    assert snap()==prior_move,'VR01AB hover exit changed native game'
    page.screenshot(path=str(ROOT/'tests/vr01z_native_move_aim_1920x1080.png'),
      animations='disabled')
    # Cancel the genuinely pending native move. Action still available.
    page.keyboard.press('c')
    page.wait_for_function("""() => !document.querySelector('#arena .slot.legal') &&
      document.querySelector('#vr-hint')?.dataset.mode==='selected' &&
      !document.querySelector('#vr-guide-targets .vr-legal-guide')""",timeout=16000)
    assert snap()==prior_move,'Cancelled M spent or moved Phase21 unit'

    page.keyboard.press('m')
    page.wait_for_function("""() =>
      document.querySelector('#vr-hint')?.dataset.mode==='move' &&
      document.querySelectorAll('#arena .slot.legal').length>0""",timeout=16000)
    target=page.locator('#arena .slot.legal').first.get_attribute('data-slot')
    target_projection=page.evaluate('k=>MRRIntegrated.scene.projectSlot(k)',target)
    assert target_projection and 0<target_projection['x']<1920 and (
      0<target_projection['y']<1080),target_projection
    page.mouse.click(target_projection['x'],target_projection['y'])
    page.wait_for_function("""pairs=>{
      const source=document.querySelector('#arena [data-slot="'+pairs[0]+'"]');
      const dest=document.querySelector('#arena [data-slot="'+pairs[1]+'"]');
      return !source?.querySelector('.board-card') &&
        !!dest?.querySelector('.board-card') &&
        !document.querySelector('#arena .slot.legal');
    }""",arg=[moving_source,target],timeout=18000)
    assert snap()!=prior_move,'Real M click did not move Phase21 unit'
    assert page.locator(f'#arena [data-slot="{target}"] .status-chip.exhausted').count()==1,(
      'Phase21 move must consume the unit action')
    assert page.evaluate('MRRIntegrated.state.scene.vrOccupiedSeats')==2
    after_move=snap()
    page.keyboard.press('m')
    assert not page.locator('#arena .slot.legal').count(),(
      'Exhausted native actor must not start another move')
    assert snap()==after_move,'Exhausted actor shortcut changed Phase21 game'
    page.screenshot(path=str(ROOT/'tests/vr01z_native_move_confirmed_1920x1080.png'),
      animations='disabled')
    page.locator('#vr-return').click()
    assert snap()==after_move,'2D return after move changed Phase21 game'
    assert not errors,errors
    print('VR01Z genuine M select, C cancel, adjacent move, exhausted action PASS',flush=True)
    browser.close()
    print('VR01 PASS: real Phase21 HP damage, 3 desktop viewports, native move and fallback',flush=True)
finally:
  http.shutdown()
  http.server_close()
