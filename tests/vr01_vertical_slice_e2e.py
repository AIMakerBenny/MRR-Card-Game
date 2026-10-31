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
    # VR01AO: save the same public opponent back node across real PC
    # resize events. Only the publicly visible back count is consulted.
    page.evaluate("""() => {
      window.__vr01aoBack=document.querySelector('#vr-enemy-fan .vr-back');
    }""")
    assert page.locator('#vr-enemy-fan .vr-back').count()>0,(
      'VR01AO requires genuine visible Phase21 opponent card backs')
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
      # VR01BO: discoverability must match the actual keyboard behavior.
      # Arrows/Home/End focus cards; numbers select via native Phase21.
      assert '← → 탐색' in info['text'] and 'Home/End' in info['text'],(
        'VR01BO missing PC navigation hint',w,h,info)
      spoken=page.locator('#vr-hand').get_attribute('aria-description') or ''
      assert all(key in spoken for key in ('방향키','Home','End','숫자')),(
        'VR01BO missing accessible navigation guidance',w,h,spoken)
      assert page.locator('#vr-enemy-fan .vr-back').count()==page.locator('#enemyHand .mcw-back').count()
      # VR01AO: after responsive reflow, back identity, order and the
      # old public-only count must be preserved with correct spacing.
      page.wait_for_function("""width => {
        const fan=document.querySelector('#vr-enemy-fan');
        const n=fan?.children.length||0;
        if(!n||!window.__vr01aoBack||fan.firstElementChild!==window.__vr01aoBack)
          return false;
        const step=Math.min(width<1500?41:52,(width-360)/Math.max(1,n));
        return [...fan.children].every((back,i)=>{
          const x=(i-(n-1)/2)*step;
          const angle=(i-(n-1)/2)*Math.min(5,22/Math.max(n-1,1));
          return back.isConnected&&back.getAttribute('aria-label')==='상대 카드 뒷면 '+(i+1)&&
            Math.abs(parseFloat(back.style.getPropertyValue('--x'))-x)<.01&&
            Math.abs(parseFloat(back.style.getPropertyValue('--angle'))-angle)<.01;
        });
      }""",arg=w,timeout=12000)
      assert snap()==baseline,('VR01AO back reflow changed Phase21 game',w,h)
      page.screenshot(path=str(ROOT/f'tests/vr01ao_opponent_reflow_{w}x{h}.png'),
        animations='disabled')
      assert page.locator('#vr-hand .vr-card').count()==page.locator('#hand .hand-slot').count()
      # VR01AW: a visually inspected hand card must not remove or hide
      # neighboring real Phase21 cards at any supported PC resolution.
      hand_review=page.evaluate("""() => {
        const cards=[...document.querySelectorAll('#vr-hand .vr-card')];
        if(cards.length<2)return {count:cards.length,skipped:true};
        const active=cards[Math.floor(cards.length/2)];
        const original=cards.map(c=>({node:c,face:c.querySelector('.vr-card-face')}));
        active.classList.add('raised');
        const result={
          count:cards.length,
          sameNodes:original.every(({node,face})=>node.isConnected&&face.isConnected),
          visible:original.every(({node,face})=>
            getComputedStyle(node).display!=='none' &&
            getComputedStyle(face).visibility==='visible' &&
            getComputedStyle(face).opacity!=='0'),
          raised:getComputedStyle(active).zIndex,
          expanded:active.getBoundingClientRect().height,
          faceTop:active.querySelector('.vr-card-face').getBoundingClientRect().top,
          faceBottom:active.querySelector('.vr-card-face').getBoundingClientRect().bottom,
          neighbors:cards.filter(c=>c!==active).length,
          nameFont:parseFloat(getComputedStyle(active.querySelector('.vr-name')).fontSize),
          nameWhiteSpace:getComputedStyle(active.querySelector('.vr-name')).whiteSpace,
          nameClamp:getComputedStyle(active.querySelector('.vr-name')).webkitLineClamp,
          rulesFont:parseFloat(getComputedStyle(active.querySelector('.vr-rules')).fontSize)
        };
        active.classList.remove('raised');
        return result;
      }""")
      assert hand_review['count']>=2 and hand_review['sameNodes'] and (
        hand_review['visible'] and hand_review['neighbors']==hand_review['count']-1),(
          'VR01AW inspected card hid or replaced neighbors',w,h,hand_review)
      # VR01AX: check the inspected card actually rises into view and
      # has the intended visual stacking priority. Mere DOM visibility is
      # insufficient to detect an off-screen or obscured card face.
      assert hand_review['raised']=='80' and (
        0<=hand_review['faceTop']<hand_review['faceBottom']<=h+1),(
          'VR01AX inspected card layering or viewport position',w,h,hand_review)
      # VR01BA: larger PC text is opt-in for the inspected card only;
      # untouched 1366/1920 layouts and native state remain as before.
      if w>=2200:
        assert hand_review['nameFont']>=16 and hand_review['rulesFont']>=14,(
          'VR01BA large-screen inspected text too small',w,h,hand_review)
      else:
        assert hand_review['nameFont']<=14 and hand_review['rulesFont']<=13,(
          'VR01BA changed standard desktop typography',w,h,hand_review)
      # VR01BB: inspected long names may wrap twice, but never trigger a
      # rebuild or expose additional card content. Confirm at every width.
      assert hand_review['nameWhiteSpace']=='normal' and hand_review['nameClamp']=='2',(
        'VR01BB name inspection wrapping missing',w,h,hand_review)
      # VR01AZ: capture the actual expanded hand at each desktop viewport,
      # then remove only the QA marker. No native game action is invoked.
      page.evaluate("""() => {
        const cards=[...document.querySelectorAll('#vr-hand .vr-card')];
        cards[Math.floor(cards.length/2)]?.classList.add('raised');
      }""")
      page.screenshot(path=str(ROOT/f'tests/vr01az_expanded_hand_{w}x{h}.png'),
        animations='disabled')
      page.evaluate("""() => document.querySelectorAll('#vr-hand .vr-card.raised')
        .forEach(card=>card.classList.remove('raised'))""")
      # VR01BC: shortcut refresh may suppress titles while targeting, but
      # must show the current public inspection when native hand keys work.
      tooltip_audit=page.evaluate("""() => {
        const native=[...document.querySelectorAll('#hand .hand-slot')];
        const cards=[...document.querySelectorAll('#vr-hand .vr-card')];
        if(cards.length!==native.length)return false;
        return cards.every((card,i)=>{
          const name=native[i].querySelector('.card-name')?.textContent.trim()||'카드';
          const cost=native[i].querySelector('.cost-bubble')?.textContent.trim()||'';
          const parts=card.title.split(' · ');
          const spoken=(card.getAttribute('aria-description')||'').split(' · ');
          const shortcut=card.dataset.vrKeyTitle||'';
          const expected=card.dataset.vrInspection+(shortcut?' · '+shortcut:'');
          return card.title===expected && parts.filter(p=>p===name).length===1 &&
            !spoken.includes(name) &&
            (!cost||card.title.includes('비용 '+cost)) &&
            (!shortcut||shortcut.startsWith('단축키 '));
        });
      }""")
      assert tooltip_audit,('VR01BC publicly grounded hand tooltip mismatch',w,h)
      assert snap()==baseline,('VR01AW/AX inspection changed Phase21 state',w,h)
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
      # VR01BL: move keyboard focus left/right between genuine mirrored
      # hand buttons. Boundary arrows must not wrap or click Phase21 cards.
      nav=page.locator('#vr-hand .vr-card')
      assert nav.count()>=2,('VR01BL requires >=2 public player cards',w,h)
      nav.first.focus()
      page.keyboard.press('ArrowRight')
      assert page.evaluate("""() => document.activeElement===
        document.querySelectorAll('#vr-hand .vr-card')[1]"""),(
          'VR01BL right arrow did not focus next hand card',w,h)
      page.keyboard.press('ArrowLeft')
      assert page.evaluate("""() => document.activeElement===
        document.querySelectorAll('#vr-hand .vr-card')[0]"""),(
          'VR01BL left arrow did not focus previous hand card',w,h)
      page.keyboard.press('ArrowLeft')
      assert page.evaluate("""() => document.activeElement===
        document.querySelectorAll('#vr-hand .vr-card')[0]"""),(
          'VR01BL left boundary wrapped unexpectedly',w,h)
      assert snap()==baseline,('VR01BL arrow focus changed Phase21',w,h)
      # VR01BM: Home/End move focus to the hand boundaries without
      # simulating a native card click, including on narrow PC screens.
      page.keyboard.press('End')
      assert page.evaluate("""() => {
        const cards=[...document.querySelectorAll('#vr-hand .vr-card')];
        return document.activeElement===cards[cards.length-1];
      }"""),('VR01BM End did not focus last card',w,h)
      page.keyboard.press('Home')
      assert page.evaluate("""() => document.activeElement===
        document.querySelector('#vr-hand .vr-card')"""),(
          'VR01BM Home did not focus first card',w,h)
      assert snap()==baseline,('VR01BM Home/End changed Phase21',w,h)
      # VR01BR: native legality may flip before the adapter refreshes its
      # cosmetic paused class. Dispatch four keys in that exact same DOM
      # task; no synthetic click, engine command or saved state is touched.
      immediate_guard=page.evaluate("""() => {
        const cards=[...document.querySelectorAll('#vr-hand .vr-card')];
        const slot=[...document.querySelectorAll('#arena .slot')]
          .find(n=>!n.classList.contains('legal')&&
            !n.classList.contains('attack-target'));
        if(cards.length<3||!slot)return null;
        const focus=cards[1],results=[];
        focus.focus();
        if(document.activeElement!==focus)return null;
        for(const nativeMode of ['legal','attack-target']){
          slot.classList.add(nativeMode);
          for(const key of ['ArrowLeft','ArrowRight','Home','End']){
            focus.dispatchEvent(new KeyboardEvent('keydown',
              {key,bubbles:true,cancelable:true}));
            results.push({nativeMode,key,stayed:document.activeElement===focus});
          }
          slot.classList.remove(nativeMode);
        }
        return {results,focusKept:document.activeElement===focus};
      }""")
      assert immediate_guard and immediate_guard['focusKept'] and all(
        case['stayed'] for case in immediate_guard['results']) and (
        len(immediate_guard['results'])==8),(
          'VR01BR native targeting guard missed immediate keydown',
          w,h,immediate_guard)
      assert snap()==baseline,('VR01BR immediate targeting guard altered Phase21',w,h)
      # VR01BS: the original Phase21 hand can redraw before the VR mirror.
      # Probe extra/missing native DOM slots synchronously, before its
      # MutationObserver refresh runs. Do not alter native engine data.
      count_guard=page.evaluate("""() => {
        const mirror=[...document.querySelectorAll('#vr-hand .vr-card')];
        const native=[...document.querySelectorAll('#hand .hand-slot')];
        if(mirror.length<3||native.length<3)return null;
        const focused=mirror[1],results=[];
        focused.focus();
        if(document.activeElement!==focused)return null;
        const check=mode=>{
          for(const key of ['ArrowLeft','ArrowRight','Home','End']){
            focused.dispatchEvent(new KeyboardEvent('keydown',
              {key,bubbles:true,cancelable:true}));
            results.push({mode,key,stayed:document.activeElement===focused});
          }
        };
        const extra=native[0].cloneNode(true);
        native[0].after(extra);
        try{check('extra-native');}
        finally{extra.remove();}
        const tail=native[native.length-1],parent=tail.parentElement,
          next=tail.nextSibling;
        tail.remove();
        try{check('missing-native');}
        finally{parent.insertBefore(tail,next);}
        return {results,focused:document.activeElement===focused,
          countsMatch:document.querySelectorAll('#hand .hand-slot').length===
            mirror.length};
      }""")
      assert count_guard and count_guard['focused'] and (
        count_guard['countsMatch']) and len(count_guard['results'])==8 and all(
          case['stayed'] for case in count_guard['results']),(
          'VR01BS navigation used stale native hand count',w,h,count_guard)
      assert snap()==baseline,('VR01BS temporary native count changed Phase21',w,h)
      # VR01BP: keyboard focus takes priority over a stale mouse-raised
      # card. Exactly one card should occupy expanded hand height.
      page.evaluate("""() => document.querySelector('#vr-hand .vr-card')
        ?.classList.add('raised')""")
      page.keyboard.press('End')
      focused_layout=page.evaluate("""() => {
        const cards=[...document.querySelectorAll('#vr-hand .vr-card')];
        const first=cards[0],last=cards[cards.length-1];
        return {firstHeight:first.getBoundingClientRect().height,
          lastHeight:last.getBoundingClientRect().height,
          firstFaceBottom:first.querySelector('.vr-card-face').getBoundingClientRect().bottom,
          focused:last.matches(':focus-visible')};
      }""")
      assert focused_layout['focused'] and focused_layout['firstHeight']<160 and (
        focused_layout['lastHeight']>240),(
          'VR01BP multiple expanded cards during keyboard hand navigation',
          w,h,focused_layout)
      page.evaluate("""() => document.querySelector('#vr-hand .vr-card')
        ?.classList.remove('raised')""")
      assert snap()==baseline,('VR01BP focus stacking changed Phase21',w,h)
      # VR01BQ: reproduce real mouse hover on the last hand anchor, then
      # keyboard-navigate to the first card without moving the pointer.
      page.evaluate('document.activeElement?.blur()')
      last=page.locator('#vr-hand .vr-card').last
      bounds=last.bounding_box()
      assert bounds,('VR01BQ last hand anchor unavailable',w,h)
      page.mouse.move(bounds['x']+bounds['width']/2,
        min(h-8,bounds['y']+bounds['height']-8))
      page.wait_for_function("""() => {
        const last=document.querySelector('#vr-hand .vr-card:last-child');
        return last?.matches(':hover')&&last.classList.contains('raised');
      }""",timeout=12000)
      last.focus()
      page.keyboard.press('Home')
      mixed_input=page.evaluate("""() => {
        const cards=[...document.querySelectorAll('#vr-hand .vr-card')];
        const first=cards[0],last=cards[cards.length-1];
        return {firstFocused:document.activeElement===first,
          firstFocusVisible:first.matches(':focus-visible'),
          lastHovered:last.matches(':hover'),
          staleRaised:last.classList.contains('raised'),
          firstHeight:first.getBoundingClientRect().height,
          lastHeight:last.getBoundingClientRect().height};
      }""")
      assert mixed_input['firstFocused'] and mixed_input['firstFocusVisible'] and (
        mixed_input['lastHovered'] and not mixed_input['staleRaised'] and
        mixed_input['firstHeight']>240 and mixed_input['lastHeight']<160),(
          'VR01BQ pointer and keyboard inspection conflict',w,h,mixed_input)
      assert snap()==baseline,('VR01BQ pointer/keyboard navigation changed Phase21',w,h)
      page.screenshot(path=str(ROOT/f'tests/vr01bq_mixed_input_{w}x{h}.png'),
        animations='disabled')
      page.mouse.move(5,h//2)
      page.evaluate('document.activeElement?.blur()')
      print('VR01',w,h,'hand',page.locator('#vr-hand .vr-card').count(),
        'enemy backs',page.locator('#vr-enemy-fan .vr-back').count(),flush=True)
    page.set_viewport_size({'width':1920,'height':1080})
    # VR01AG: test owner artwork through the REAL Phase59 public-card
    # artwork registry and native Phase21 renderHand(). Native hand repaints
    # deliberately replace child nodes, so inserting a test image directly
    # into .art-well is not a durable or representative fixture.
    art=page.evaluate("""() => {
      const reg=window.MRRCardArtRegistry;
      const slots=[...document.querySelectorAll('#hand .hand-slot')];
      const index=slots.findIndex(slot=>{
        const id=slot.querySelector('.card-ui')?.getAttribute('data-mrr-public-card-id');
        return !!id&&reg?.knownIds?.includes(id);
      });
      if(index<0||typeof window.renderHand!=='function')return null;
      const id=slots[index].querySelector('.card-ui')
        .getAttribute('data-mrr-public-card-id');
      const hadOriginal=Object.prototype.hasOwnProperty.call(reg.assets,id);
      const original=reg.assets[id];
      const make=colour=>{
        const canvas=document.createElement('canvas');
        canvas.width=1200;canvas.height=960;
        const ctx=canvas.getContext('2d');
        ctx.fillStyle=colour;ctx.fillRect(0,0,1200,960);
        return canvas.toDataURL('image/png');
      };
      reg.assets[id]=make('#146b80');
      window.renderHand();
      window.__vr01agFixture={id,index,original,hadOriginal,make};
      const source=[...document.querySelectorAll('#hand .hand-slot')][index]
        ?.querySelector('.art-well > .mrr-owner-art');
      return {id,index,url:source?.getAttribute('src')||''};
    }""")
    assert art and art['url'].startswith('data:image/png;base64,'),(
      'VR01AG native Phase59 art pipeline fixture unavailable',art)
    page.wait_for_function("""url=>{
      const index=window.__vr01agFixture?.index;
      const mirror=document.querySelector('#vr-hand .vr-card[data-index="'+index+'"] .vr-provided-art');
      return mirror?.getAttribute('src')===url && mirror.complete && mirror.naturalWidth===1200;
    }""",arg=art['url'],timeout=15000)
    for w,h in ((1366,768),(1920,1080),(2560,1440)):
      page.set_viewport_size({'width':w,'height':h})
      page.wait_for_function("""url=>{
        const index=window.__vr01agFixture?.index;
        return document.querySelector('#vr-hand .vr-card[data-index="'+index+'"] .vr-provided-art')
          ?.getAttribute('src')===url;
      }""",arg=art['url'],timeout=15000)
      assert snap()==baseline,('VR01AG artwork changed native game',w,h)
      page.screenshot(path=str(ROOT/f'tests/vr01ag_native_hand_art_{w}x{h}.png'),
        animations='disabled')
    # VR01BK: update only the native art's alt text, not the image data.
    # Keep the same mirrored button and owner image while focus persists.
    art_alt=page.evaluate("""index => {
      const source=[...document.querySelectorAll('#hand .hand-slot')][index]
        ?.querySelector('.art-well > .mrr-owner-art');
      const card=document.querySelector('#vr-hand .vr-card[data-index="'+index+'"]');
      const art=card?.querySelector('.vr-provided-art');
      if(!source||!card||!art)return null;
      window.__vr01bkSource=source;
      window.__vr01bkCard=card;
      window.__vr01bkArt=art;
      window.__vr01bkHadAlt=source.hasAttribute('alt');
      window.__vr01bkOldAlt=source.getAttribute('alt');
      card.focus();card.classList.add('raised');
      source.setAttribute('alt','VR01BK 공개 카드 이미지 설명');
      return {index};
    }""",art['index'])
    assert art_alt,'VR01BK visible native artwork fixture unavailable'
    page.wait_for_function("""() => {
      const card=window.__vr01bkCard,art=window.__vr01bkArt;
      return card?.isConnected&&document.activeElement===card &&
        card.classList.contains('raised') && art?.isConnected &&
        card.querySelector('.vr-provided-art')===art &&
        art.getAttribute('alt')==='VR01BK 공개 카드 이미지 설명';
    }""",timeout=15000)
    assert snap()==baseline,'VR01BK alt-only repaint altered native game'
    page.evaluate("""() => {
      const native=window.__vr01bkSource;
      if(window.__vr01bkHadAlt)native.setAttribute('alt',window.__vr01bkOldAlt);
      else native.removeAttribute('alt');
    }""")
    page.wait_for_function("""() => {
      const art=window.__vr01bkArt,source=window.__vr01bkSource;
      return art?.isConnected &&
        art.getAttribute('alt')===source?.getAttribute('alt') &&
        document.activeElement===window.__vr01bkCard;
    }""",timeout=15000)
    page.evaluate("""() => {
      delete window.__vr01bkSource;
      delete window.__vr01bkCard;
      delete window.__vr01bkArt;
      delete window.__vr01bkHadAlt;
      delete window.__vr01bkOldAlt;
    }""")
    assert snap()==baseline,'VR01BK restored art description changed Phase21'
    # VR01AH: updating only native art must preserve existing hand
    # button identity, focus and hover, avoiding a synthetic mouse reset.
    page.evaluate("""() => {
      const i=window.__vr01agFixture.index;
      const node=document.querySelector('#vr-hand .vr-card[data-index="'+i+'"]');
      window.__vr01ahNode=node;
      node.focus();node.classList.add('raised');
    }""")
    changed=page.evaluate("""() => {
      const fixture=window.__vr01agFixture;
      const url=fixture.make('#b77a38');
      window.MRRCardArtRegistry.assets[fixture.id]=url;
      window.renderHand();
      return url;
    }""")
    page.wait_for_function("""url=>{
      const index=window.__vr01agFixture?.index;
      return document.querySelector('#vr-hand .vr-card[data-index="'+index+'"] .vr-provided-art')
        ?.getAttribute('src')===url;
    }""",arg=changed,timeout=15000)
    assert changed!=art['url'] and snap()==baseline,(
      'VR01AG artwork replacement affected native game')
    assert page.evaluate("""() => {
      const node=window.__vr01ahNode;
      return node?.isConnected && document.activeElement===node &&
        node.classList.contains('raised') &&
        !!node.querySelector('.vr-provided-art');
    }"""),'VR01AH art-only repaint recreated focused hand button'
    page.screenshot(path=str(ROOT/'tests/vr01ah_art_focus_preserved_1920x1080.png'),
      animations='disabled')
    page.evaluate("""() => {
      const fixture=window.__vr01agFixture;
      if(fixture.hadOriginal)
        window.MRRCardArtRegistry.assets[fixture.id]=fixture.original;
      else delete window.MRRCardArtRegistry.assets[fixture.id];
      window.renderHand();
      delete window.__vr01agFixture;
    }""")
    page.wait_for_function("""index => !document.querySelector(
      '#vr-hand .vr-card[data-index="'+index+'"] .vr-provided-art')""",
      arg=art['index'],timeout=15000)
    assert snap()==baseline,'VR01AG artwork removal affected native game'
    # VR01AJ: a cosmetic Phase21 hand cost repaint must NOT destroy an
    # already focused/raised 3D hand button. No engine mana is changed.
    cosmetic=page.evaluate("""index => {
      const slot=[...document.querySelectorAll('#hand .hand-slot')][index];
      const label=slot?.querySelector('.cost-bubble');
      const card=document.querySelector('#vr-hand .vr-card[data-index="'+index+'"]');
      if(!label||!card)return null;
      window.__vr01ajLabel=label;
      window.__vr01ajValue=label.textContent;
      window.__vr01ajCard=card;
      card.focus();
      card.classList.add('raised');
      label.textContent='77';
      return {index,original:window.__vr01ajValue};
    }""",art['index'])
    assert cosmetic is not None,'VR01AJ visible native hand cost fixture unavailable'
    page.wait_for_function("""() => {
      const card=window.__vr01ajCard;
      return card?.isConnected && document.activeElement===card &&
        card.classList.contains('raised') &&
        card.querySelector('.vr-mana')?.textContent==='77';
    }""",timeout=15000)
    # VR01BC: native cosmetic cost updates must refresh the same tooltip
    # and accessible description while preserving the original focused node.
    page.wait_for_function("""() => {
      const card=window.__vr01ajCard;
      return card?.title.includes('비용 77') &&
        card.getAttribute('aria-description')?.includes('비용 77') &&
        card.title===card.dataset.vrInspection+
          (card.dataset.vrKeyTitle?' · '+card.dataset.vrKeyTitle:'');
    }""",timeout=15000)
    assert snap()==baseline,'VR01AJ cosmetic hand refresh changed game state'
    page.screenshot(path=str(ROOT/'tests/vr01aj_text_focus_preserved_1920x1080.png'),
      animations='disabled')
    page.evaluate("""() => {
      window.__vr01ajLabel.textContent=window.__vr01ajValue;
    }""")
    page.wait_for_function("""original => {
      const card=window.__vr01ajCard;
      return card?.isConnected && document.activeElement===card &&
        card.querySelector('.vr-mana')?.textContent===(original||'0');
    }""",arg=cosmetic['original'],timeout=15000)
    page.evaluate("""() => {
      delete window.__vr01ajLabel;
      delete window.__vr01ajValue;
      delete window.__vr01ajCard;
    }""")
    assert snap()==baseline,'VR01AJ restored native text affected game state'
    # VR01BG: a cosmetic native label repaint for an unchanged PUBLIC card
    # identity must update the same mirrored button without losing focus.
    rename=page.evaluate("""index => {
      const source=[...document.querySelectorAll('#hand .hand-slot')][index];
      const name=source?.querySelector('.card-name');
      const nativeId=source?.querySelector('.card-ui')
        ?.getAttribute('data-mrr-public-card-id');
      const mirror=document.querySelector('#vr-hand .vr-card[data-index="'+index+'"]');
      if(!name||!nativeId||!mirror)return null;
      window.__vr01bgName=name;
      window.__vr01bgBefore=name.textContent;
      window.__vr01bgMirror=mirror;
      mirror.focus();mirror.classList.add('raised');
      name.textContent='임시 카드명 확인';
      return {nativeId,index};
    }""",art['index'])
    assert rename,'VR01BG native public-card identity fixture unavailable'
    page.wait_for_function("""() => {
      const card=window.__vr01bgMirror;
      return card?.isConnected && document.activeElement===card &&
        card.classList.contains('raised') &&
        card.querySelector('.vr-name')?.textContent==='임시 카드명 확인' &&
        card.getAttribute('aria-label')==='임시 카드명 확인 손패 선택' &&
        card.dataset.vrInspection.startsWith('임시 카드명 확인');
    }""",timeout=15000)
    assert snap()==baseline,'VR01BG cosmetic native name changed Phase21 state'
    # VR01BJ: click after the in-place cosmetic rename. Spy on visual
    # launch and Phase21 delegation so the test invokes no actual game action.
    click_audit=page.evaluate("""index => {
      const mirror=window.__vr01bgMirror;
      const original=[...document.querySelectorAll('#hand .hand-slot')][index];
      const scene=window.MRRIntegrated?.scene;
      if(!mirror||!original||typeof scene?.armDeployment!=='function')
        return null;
      const oldClick=original.click,oldArm=scene.armDeployment;
      const clickOwn=Object.prototype.hasOwnProperty.call(original,'click');
      const armOwn=Object.prototype.hasOwnProperty.call(scene,'armDeployment');
      const events=[];
      original.click=()=>events.push({type:'native'});
      scene.armDeployment=data=>events.push({
        type:'visual',name:data.name,x:data.x,y:data.y});
      try{mirror.click();}
      finally{
        if(clickOwn)original.click=oldClick;
        else delete original.click;
        if(armOwn)scene.armDeployment=oldArm;
        else delete scene.armDeployment;
      }
      return events;
    }""",art['index'])
    assert click_audit and len(click_audit)==2 and (
      click_audit[0]['type']=='visual' and
      click_audit[0]['name']=='임시 카드명 확인' and
      click_audit[1]['type']=='native'),(
        'VR01BJ launch name/delegation out of sync',click_audit)
    assert snap()==baseline,'VR01BJ visual launch spy changed Phase21 state'
    page.evaluate("""() => {
      window.__vr01bgName.textContent=window.__vr01bgBefore;
    }""")
    page.wait_for_function("""() => {
      const card=window.__vr01bgMirror;
      return card?.isConnected && document.activeElement===card &&
        card.querySelector('.vr-name')?.textContent===
          window.__vr01bgBefore.trim();
    }""",timeout=15000)
    page.evaluate("""() => {
      delete window.__vr01bgName;
      delete window.__vr01bgBefore;
      delete window.__vr01bgMirror;
    }""")
    assert snap()==baseline,'VR01BG restored name affected native game'
    # VR01BH: changing the PUBLIC native identity at the same hand index
    # must rebuild the mirrored button, even if its visible name matches.
    # This simulates a hand-card replacement without touching Phase21 G.
    identity=page.evaluate("""index => {
      const source=[...document.querySelectorAll('#hand .hand-slot')][index]
        ?.querySelector('.card-ui');
      const old=source?.getAttribute('data-mrr-public-card-id');
      const mirror=document.querySelector('#vr-hand .vr-card[data-index="'+index+'"]');
      if(!source||!old||!mirror)return null;
      window.__vr01bhSource=source;
      window.__vr01bhId=old;
      window.__vr01bhOldMirror=mirror;
      mirror.focus();mirror.classList.add('raised');
      source.setAttribute('data-mrr-public-card-id',old+'-qa-replacement');
      return {index,old};
    }""",art['index'])
    assert identity,'VR01BH public hand identity fixture unavailable'
    page.wait_for_function("""index=>{
      const old=window.__vr01bhOldMirror;
      const current=document.querySelector('#vr-hand .vr-card[data-index="'+index+'"]');
      return !!(old&&!old.isConnected&&current&&current!==old &&
        document.activeElement!==old);
    }""",arg=identity['index'],timeout=15000)
    assert snap()==baseline,'VR01BH public identity change touched native game'
    page.evaluate("""index => {
      window.__vr01bhReplacement=document.querySelector(
        '#vr-hand .vr-card[data-index="'+index+'"]');
    }""",identity['index'])
    page.evaluate("""() => {
      window.__vr01bhSource.setAttribute(
        'data-mrr-public-card-id',window.__vr01bhId);
    }""")
    page.wait_for_function("""index => {
      const source=window.__vr01bhSource;
      const mirror=document.querySelector('#vr-hand .vr-card[data-index="'+index+'"]');
      return source?.getAttribute('data-mrr-public-card-id')===window.__vr01bhId &&
        window.__vr01bhReplacement && !window.__vr01bhReplacement.isConnected &&
        !!mirror && mirror!==window.__vr01bhReplacement &&
        mirror.getAttribute('aria-label')?.endsWith(' 손패 선택');
    }""",arg=identity['index'],timeout=15000)
    page.evaluate("""() => {
      delete window.__vr01bhSource;
      delete window.__vr01bhId;
      delete window.__vr01bhOldMirror;
      delete window.__vr01bhReplacement;
    }""")
    assert snap()==baseline,'VR01BH restored native identity affected game'
    # VR01BN: a native DOM hand reorder rebuilds indexed delegates.
    # Preserve focus on the SAME unique public card, not its old position.
    reorder=page.evaluate("""() => {
      const slots=[...document.querySelectorAll('#hand .hand-slot')];
      const id=slot=>slot.querySelector('.card-ui')
        ?.getAttribute('data-mrr-public-card-id')||'';
      const ids=slots.map(id);
      const k=slots.findIndex((slot,i)=>i+1<slots.length&&
        ids[i]&&ids[i+1]&&ids[i]!==ids[i+1]&&
        ids.filter(x=>x===ids[i+1]).length===1);
      if(k<0)return null;
      const first=slots[k],second=slots[k+1],parent=first.parentElement;
      const focus=document.querySelectorAll('#vr-hand .vr-card')[k+1];
      window.__vr01bnFirst=first;window.__vr01bnSecond=second;
      window.__vr01bnFocusId=ids[k+1];
      window.__vr01bnOriginalFocus=focus;
      focus.focus();focus.classList.add('raised');
      parent.insertBefore(second,first);
      return {index:k,focusedId:ids[k+1]};
    }""")
    assert reorder,'VR01BN requires adjacent unique public card identities'
    page.wait_for_function("""index=>{
      const active=document.activeElement;
      const source=[...document.querySelectorAll('#hand .hand-slot')][index]
        ?.querySelector('.card-ui')?.getAttribute('data-mrr-public-card-id');
      return active?.matches('#vr-hand .vr-card')&&
        active.dataset.index===String(index)&&
        active!==window.__vr01bnOriginalFocus &&
        source===window.__vr01bnFocusId;
    }""",arg=reorder['index'],timeout=15000)
    assert snap()==baseline,'VR01BN hand reorder changed native game state'
    page.evaluate("""() => {
      window.__vr01bnFirst.parentElement.insertBefore(
        window.__vr01bnFirst,window.__vr01bnSecond);
    }""")
    page.wait_for_function("""index=>{
      const active=document.activeElement;
      const original=[...document.querySelectorAll('#hand .hand-slot')][index+1]
        ?.querySelector('.card-ui')?.getAttribute('data-mrr-public-card-id');
      return active?.matches('#vr-hand .vr-card')&&
        active.dataset.index===String(index+1)&&
        original===window.__vr01bnFocusId;
    }""",arg=reorder['index'],timeout=15000)
    assert snap()==baseline,'VR01BN hand reorder restore changed native game'
    page.evaluate("""() => {
      delete window.__vr01bnFirst;
      delete window.__vr01bnSecond;
      delete window.__vr01bnFocusId;
      delete window.__vr01bnOriginalFocus;
    }""")
    # VR01AN: a viewport resize is NOT a change to the player's cards.
    # Reflow the original mirrored buttons (not replaceChildren), keeping
    # focused/raised nodes and real Phase21 engine state unchanged.
    page.evaluate("""() => {
      const card=document.querySelector('#vr-hand .vr-card');
      window.__vr01anCard=card;
      card.focus();card.classList.add('raised');
    }""")
    for w,h in ((1366,768),(2560,1440),(1920,1080)):
      page.set_viewport_size({'width':w,'height':h})
      page.wait_for_function("""width => {
        const card=window.__vr01anCard;
        const fan=document.querySelector('#vr-hand');
        const n=fan?.children.length||0;
        const step=Math.min(width<1500?72:width<2200?91:108,
          Math.max(43,(width-420)/Math.max(1,n)));
        return !!card && card.isConnected && fan.children[0]===card &&
          document.activeElement===card && card.classList.contains('raised') &&
          Math.abs(parseFloat(card.style.getPropertyValue('--hit'))-step)<.01 &&
          Math.abs(parseFloat(card.style.getPropertyValue('--x'))-
            ((0-(n-1)/2)*step))<.01;
      }""",arg=w,timeout=15000)
      assert snap()==baseline,('VR01AN resized 3D hand changed Phase21',w,h)
      page.screenshot(path=str(ROOT/f'tests/vr01an_hand_reflow_focus_{w}x{h}.png'),
        animations='disabled')
    page.evaluate("delete window.__vr01anCard")
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
        # VR01BT: the native quick command is genuinely under the pointer;
        # its selected-card placement must not re-seat while safe to click.
        assert page.locator('#mrr-integrated-context').evaluate(
          "node=>node.matches(':hover')"),(
          'VR01BT expected native quick command to receive actual mouse hover')
        page.wait_for_timeout(850)
        after_hover=page.locator('#mrr-integrated-context').bounding_box()
        assert after_hover and abs(after_hover['x']-before['x'])<3 and (
          abs(after_hover['y']-before['y'])<3),('VR01AC jumpy quick command',before,after_hover)
        page.screenshot(path=str(ROOT/'tests/vr01ac_native_context_nonoverlap_1920x1080.png'),
          animations='disabled')
        # VR01BU: keyboard focus must also pin a safe native command
        # despite a synthetic >36px auto-camera slot displacement.
        # Only the visual cache is perturbed, never Phase21 engine state.
        page.mouse.move(5,540)
        page.locator('#mrr-quick-attack').focus()
        focused_command=page.evaluate("""() => {
          const ctx=document.querySelector('#mrr-integrated-context');
          const button=document.querySelector('#mrr-quick-attack');
          const scene=MRRIntegrated.scene;
          const slot=scene.projectSlot(scene.state.selectedKey);
          if(!ctx||ctx.hidden||!slot||!ctx.dataset.vrLayoutKey||
             document.activeElement!==button)return null;
          const before=ctx.getBoundingClientRect(),oldX=ctx.dataset.vrSlotX;
          const oldY=ctx.dataset.vrSlotY;
          ctx.dataset.vrSlotX=String(slot.x-80);
          try{scene.sync();}
          finally{ctx.dataset.vrSlotX=oldX;ctx.dataset.vrSlotY=oldY;}
          const after=ctx.getBoundingClientRect();
          return {focus:document.activeElement===button,
            underPointer:ctx.matches(':hover'),
            deltaX:after.left-before.left,deltaY:after.top-before.top};
        }""")
        assert focused_command and focused_command['focus'] and (
          not focused_command['underPointer'] and
          abs(focused_command['deltaX'])<3 and
          abs(focused_command['deltaY'])<3),(
            'VR01BU focused native quick command unexpectedly jumped',
            focused_command)
        assert snap()==baseline,'VR01BU focused native command altered Phase21'
        # VR01BV: force the SAME cached action into the selected public
        # card's projected face without changing native gameplay state.
        # Even with zero slot displacement, a newly unsafe seat must move.
        unsafe_cache=page.evaluate("""() => {
          const ctx=document.querySelector('#mrr-integrated-context');
          const stage=document.querySelector('#mrr-integrated-stage');
          const scene=MRRIntegrated.scene;
          const face=scene.projectCardBounds(scene.state.selectedKey);
          if(!ctx||!stage||!face||ctx.hidden)return null;
          const stageBox=stage.getBoundingClientRect();
          const old={left:ctx.style.left,top:ctx.style.top};
          const overlap=(a,b)=>Math.max(0,Math.min(a.right,b.right)-Math.max(a.left,b.left))*
            Math.max(0,Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top));
          ctx.style.left=(face.left-stageBox.left+
            (face.right-face.left-ctx.offsetWidth)/2)+'px';
          ctx.style.top=((face.top+face.bottom)/2-stageBox.top)+'px';
          const invalid=overlap(ctx.getBoundingClientRect(),face);
          try{scene.sync();}
          finally{
            // Preserve the real computed safe location if it was fixed;
            // otherwise restore original styles before raising an error.
            if(overlap(ctx.getBoundingClientRect(),face)>=4){
              ctx.style.left=old.left;ctx.style.top=old.top;
            }
          }
          const now=ctx.getBoundingClientRect();
          return {invalid,remaining:overlap(now,face),
            moved:now.left!==face.left||now.top!==face.top};
        }""")
        assert unsafe_cache and unsafe_cache['invalid']>4 and (
          unsafe_cache['remaining']<4),(
          'VR01BV cached command stayed over selected real card',unsafe_cache)
        assert snap()==baseline,'VR01BV cache safety changed native game'
        # VR01BW: a new PUBLIC status badge can overlap a previously safe
        # quick command without any camera-slot displacement. The native
        # view must re-seat the real button away from that visible marker.
        status_collision=page.evaluate("""() => {
          const ctx=document.querySelector('#mrr-integrated-context');
          const host=document.querySelector('#vr-public-plaques');
          const scene=MRRIntegrated.scene;
          if(!ctx||!host||ctx.hidden)return null;
          const r=ctx.getBoundingClientRect(),h=host.getBoundingClientRect();
          const badge=document.createElement('span');
          badge.className='vr-public-action';
          badge.style.left=(r.left-h.left+r.width/2-14)+'px';
          badge.style.top=(r.top-h.top+r.height/2-14)+'px';
          badge.style.width='28px';badge.style.height='28px';
          badge.textContent='◆';
          const area=(a,b)=>Math.max(0,Math.min(a.right,b.right)-Math.max(a.left,b.left))*
            Math.max(0,Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top));
          host.append(badge);
          let before=0,after=0;
          try{
            before=area(r,badge.getBoundingClientRect());
            scene.sync();
            after=area(ctx.getBoundingClientRect(),badge.getBoundingClientRect());
          }finally{badge.remove();}
          return {before,after,focused:document.activeElement?.id==='mrr-quick-attack'};
        }""")
        assert status_collision and status_collision['before']>30 and (
          status_collision['after']<4),(
          'VR01BW command did not clear newly overlapping public status badge',
          status_collision)
        assert snap()==baseline,'VR01BW public-status fixture altered Phase21'
        # VR01BX: temporarily withdraw all original inspector commands
        # without clicking or changing G. The actual integrated adapter
        # must hide its quick group and discard the old cached seat.
        cache_reset=page.evaluate("""() => {
          const scene=MRRIntegrated.scene;
          const ctx=document.querySelector('#mrr-integrated-context');
          const attack=document.querySelector('#inspectBody button[data-actor="attack"]');
          const move=document.querySelector('#inspectBody button[data-actor="move"]');
          const cancel=document.querySelector('#inspectBody button[data-cancel-action]');
          if(!ctx||!attack||!ctx.dataset.vrLayoutKey)return null;
          const oldA=attack.disabled,oldM=move?.disabled;
          const parent=cancel?.parentNode,next=cancel?.nextSibling;
          try{
            attack.disabled=true;
            if(move)move.disabled=true;
            cancel?.remove();
            scene.sync();
            const blocked={hidden:ctx.hidden,
              cacheGone:!ctx.hasAttribute('data-vr-layout-key')&&
                !ctx.hasAttribute('data-vr-slot-x')&&
                !ctx.hasAttribute('data-vr-slot-y')};
            return blocked;
          }finally{
            attack.disabled=oldA;
            if(move)move.disabled=oldM;
            if(cancel&&parent)parent.insertBefore(cancel,next);
            scene.sync();
          }
        }""")
        assert cache_reset and cache_reset['hidden'] and (
          cache_reset['cacheGone']),(
          'VR01BX hidden action group retained a stale command seat',
          cache_reset)
        page.wait_for_function("""() => {
          const ctx=document.querySelector('#mrr-integrated-context');
          return ctx&&!ctx.hidden&&!!ctx.dataset.vrLayoutKey;
        }""",timeout=12000)
        assert snap()==baseline,'VR01BX native command cache reset changed Phase21'
        # VR01BY: the public native target markers or private Phase21 pass
        # must temporarily suppress all selected-card quick commands.
        # These are DOM-only fixtures, not engine actions or fake targets.
        action_gate=page.evaluate("""() => {
          const scene=MRRIntegrated.scene;
          const context=document.querySelector('#mrr-integrated-context');
          const slot=[...document.querySelectorAll('#arena .slot')]
            .find(e=>!e.classList.contains('legal')&&
              !e.classList.contains('attack-target'));
          const overlay=document.querySelector('#overlay');
          if(!context||context.hidden||!context.dataset.vrLayoutKey||
            !slot||!overlay||!overlay.classList.contains('hidden'))return null;
          const checks=[];
          for(const mode of ['legal','attack-target']){
            slot.classList.add(mode);
            try{
              scene.sync();
              checks.push({mode,hidden:context.hidden,
                cacheGone:!context.dataset.vrLayoutKey});
            }finally{slot.classList.remove(mode);scene.sync();}
          }
          overlay.classList.remove('hidden');
          try{
            scene.sync();
            checks.push({mode:'private',hidden:context.hidden,
              cacheGone:!context.dataset.vrLayoutKey});
          }finally{overlay.classList.add('hidden');scene.sync();}
          return {checks,restored:!context.hidden&&!!context.dataset.vrLayoutKey};
        }""")
        assert action_gate and action_gate['restored'] and (
          len(action_gate['checks'])==3) and all(
            item['hidden'] and item['cacheGone']
            for item in action_gate['checks']),(
          'VR01BY native targeting/private quick-action gate failed',action_gate)
        assert snap()==baseline,'VR01BY action gate altered Phase21'
        # VR01BZ: a focused native quick button must relinquish focus,
        # keyboard access and AT exposure when Phase21 target selection
        # temporarily withdraws the action group.
        focus_gate=page.evaluate("""() => {
          const scene=MRRIntegrated.scene;
          const ctx=document.querySelector('#mrr-integrated-context');
          const button=document.querySelector('#mrr-quick-attack');
          const slot=[...document.querySelectorAll('#arena .slot')]
            .find(e=>!e.classList.contains('legal')&&
              !e.classList.contains('attack-target'));
          if(!ctx||ctx.hidden||!button||button.hidden||!slot)return null;
          button.focus();
          if(document.activeElement!==button)return null;
          let blocked;
          slot.classList.add('legal');
          try{
            scene.sync();
            button.focus();
            blocked={hidden:ctx.hidden,inert:ctx.inert,
              ariaHidden:ctx.getAttribute('aria-hidden'),
              focusCleared:document.activeElement!==button};
          }finally{slot.classList.remove('legal');scene.sync();}
          return {blocked,restored:!ctx.hidden&&!ctx.inert&&
            !ctx.hasAttribute('aria-hidden')};
        }""")
        assert focus_gate and focus_gate['restored'] and (
          focus_gate['blocked']['hidden'] and
          focus_gate['blocked']['inert'] and
          focus_gate['blocked']['ariaHidden']=='true' and
          focus_gate['blocked']['focusCleared']),(
          'VR01BZ withdrawn quick action leaked keyboard/AT access',focus_gate)
        assert snap()==baseline,'VR01BZ quick action privacy altered Phase21'
        # VR01CC: a click already queued before the VR adapter's next
        # refresh must not reach original Phase21 during target/pass states.
        # Stub ONLY the native button's click entry point and always restore.
        immediate_click=page.evaluate("""() => {
          const ctx=document.querySelector('#mrr-integrated-context');
          const quick=document.querySelector('#mrr-quick-attack');
          const native=document.querySelector('#inspectBody button[data-actor="attack"]');
          const overlay=document.querySelector('#overlay');
          const slot=[...document.querySelectorAll('#arena .slot')]
            .find(n=>!n.classList.contains('legal')&&!n.classList.contains('attack-target'));
          if(!ctx||ctx.hidden||!quick||quick.hidden||!native||
             native.disabled||!overlay?.classList.contains('hidden')||!slot)return null;
          const own=Object.prototype.hasOwnProperty.call(native,'click');
          const old=native.click,counts=[];
          let delegated=0;
          native.click=()=>{delegated++;};
          const fire=()=>quick.dispatchEvent(new MouseEvent('click',
            {bubbles:true,cancelable:true}));
          try{
            fire();counts.push({mode:'selected',delegated});
            for(const mode of ['legal','attack-target']){
              slot.classList.add(mode);
              try{fire();counts.push({mode,delegated});}
              finally{slot.classList.remove(mode);}
            }
            overlay.classList.remove('hidden');
            try{fire();counts.push({mode:'private',delegated});}
            finally{overlay.classList.add('hidden');}
          }finally{
            if(own)native.click=old;else delete native.click;
          }
          return {counts,restored:!ctx.hidden&&overlay.classList.contains('hidden')};
        }""")
        assert immediate_click and immediate_click['restored'] and (
          immediate_click['counts']==[
            {'mode':'selected','delegated':1},
            {'mode':'legal','delegated':1},
            {'mode':'attack-target','delegated':1},
            {'mode':'private','delegated':1}
          ]),('VR01CC queued quick click crossed native target gate',immediate_click)
        assert snap()==baseline,'VR01CC click gate changed Phase21 state'
        # VR01CD: the native selected-slot can disappear before the VR
        # adapter refreshes. A queued quick click must not delegate to
        # the previously selected real card; restoring selection must.
        deselection_click=page.evaluate("""() => {
          const scene=MRRIntegrated.scene;
          const selected=scene.state.selectedKey;
          const slot=[...document.querySelectorAll('#arena .slot.selected-slot')]
            .find(e=>e.dataset.slot===selected);
          const ctx=document.querySelector('#mrr-integrated-context');
          const quick=document.querySelector('#mrr-quick-attack');
          const native=document.querySelector('#inspectBody button[data-actor="attack"]');
          if(!slot||!ctx||ctx.hidden||!quick||quick.hidden||
             !native||native.disabled)return null;
          const own=Object.prototype.hasOwnProperty.call(native,'click'),
            old=native.click;
          let delegated=0;
          const fire=()=>quick.dispatchEvent(new MouseEvent('click',
            {bubbles:true,cancelable:true}));
          native.click=()=>{delegated++;};
          let result;
          try{
            fire();
            const before=delegated;
            slot.classList.remove('selected-slot');
            try{fire();}
            finally{slot.classList.add('selected-slot');}
            const during=delegated;
            fire();
            result={before,during,after:delegated,
              stillSelected:slot.classList.contains('selected-slot')};
          }finally{
            if(own)native.click=old;else delete native.click;
          }
          return result;
        }""")
        assert deselection_click and deselection_click=={
          'before':1,'during':1,'after':2,'stillSelected':True
        },('VR01CD stale selected-card click was delegated',deselection_click)
        assert snap()==baseline,'VR01CD native selection guard changed Phase21'
        # VR01CE: the public card in the selected slot can change between
        # native DOM repaint and the next integrated VR adapter refresh.
        # A previously rendered quick command may only reach the SAME
        # publicly identified card. Test the race in one synchronous task.
        identity_click=page.evaluate("""() => {
          const selected=MRRIntegrated.state.scene.selectedKey;
          const slot=[...document.querySelectorAll('#arena .slot.selected-slot')]
            .find(e=>e.dataset.slot===selected);
          const card=slot?.querySelector('.board-card .card-ui');
          const ctx=document.querySelector('#mrr-integrated-context');
          const quick=document.querySelector('#mrr-quick-attack');
          const native=document.querySelector('#inspectBody button[data-actor="attack"]');
          if(!card||!ctx||ctx.hidden||!quick||quick.hidden||
             !native||native.disabled)return null;
          const id=card.getAttribute('data-mrr-public-card-id');
          if(!id||ctx.dataset.vrSelectedCardId!==id)return null;
          const own=Object.prototype.hasOwnProperty.call(native,'click');
          const old=native.click;
          let delegated=0;
          const fire=()=>quick.dispatchEvent(new MouseEvent('click',
            {bubbles:true,cancelable:true}));
          native.click=()=>{delegated++;};
          let result;
          try{
            fire();
            const initial=delegated;
            card.setAttribute('data-mrr-public-card-id',id+'-qa-replaced');
            try{fire();}
            finally{card.setAttribute('data-mrr-public-card-id',id);}
            const stale=delegated;
            fire();
            result={initial,stale,restored:delegated,
              cached:ctx.dataset.vrSelectedCardId===id,
              nativeRestored:card.getAttribute('data-mrr-public-card-id')===id};
          }finally{
            if(own)native.click=old;else delete native.click;
          }
          return result;
        }""")
        assert identity_click=={
          'initial':1,'stale':1,'restored':2,
          'cached':True,'nativeRestored':True
        },('VR01CE stale public card identity received a native click',identity_click)
        assert snap()==baseline,'VR01CE public identity gate changed Phase21'
        # VR01CF: during a native DOM selection transition two public
        # slots might both carry selected-slot before the VR refresh.
        # With an otherwise unchanged card, stale quick commands must
        # not delegate while selection is ambiguous.
        ambiguous_selection=page.evaluate("""() => {
          const scene=MRRIntegrated.scene;
          const selected=scene.state.selectedKey;
          const second=[...document.querySelectorAll('#arena .slot')]
            .find(slot=>slot.dataset.slot!==selected&&
              !slot.classList.contains('selected-slot'));
          const quick=document.querySelector('#mrr-quick-attack');
          const native=document.querySelector('#inspectBody button[data-actor="attack"]');
          const ctx=document.querySelector('#mrr-integrated-context');
          if(!second||!quick||quick.hidden||!native||native.disabled||
            !ctx||ctx.hidden)return null;
          const own=Object.prototype.hasOwnProperty.call(native,'click'),
            previous=native.click;
          let delegated=0;
          native.click=()=>{delegated++;};
          const fire=()=>quick.dispatchEvent(new MouseEvent('click',
            {bubbles:true,cancelable:true}));
          let result;
          try{
            fire();
            const before=delegated;
            second.classList.add('selected-slot');
            try{fire();}
            finally{second.classList.remove('selected-slot');}
            const during=delegated;
            fire();
            result={before,during,after:delegated};
          }finally{
            if(own)native.click=previous;
            else delete native.click;
          }
          return result;
        }""")
        assert ambiguous_selection=={'before':1,'during':1,'after':2},(
          'VR01CF ambiguous native selection delegated a quick command',
          ambiguous_selection)
        assert snap()==baseline,'VR01CF ambiguous selection changed Phase21'
        # VR01CH: quick commands must be VISUALLY unavailable while the
        # original public selection is ambiguous, even before any click.
        # A native scene sync is invoked after each display-only fixture.
        display_gate=page.evaluate("""() => {
          const scene=MRRIntegrated.scene,ctx=document.querySelector('#mrr-integrated-context');
          const selectedKey=scene.state.selectedKey;
          const selected=[...document.querySelectorAll('#arena .slot.selected-slot')]
            .find(slot=>slot.dataset.slot===selectedKey);
          const extra=[...document.querySelectorAll('#arena .slot')]
            .find(slot=>slot!==selected&&!slot.classList.contains('selected-slot'));
          if(!selected||!extra||!ctx||ctx.hidden)return null;
          const results=[];
          extra.classList.add('selected-slot');
          try{scene.sync();
            results.push({mode:'double',hidden:ctx.hidden,
              cache:ctx.hasAttribute('data-vr-selected-card-id')});
          }finally{extra.classList.remove('selected-slot');scene.sync();}
          selected.classList.remove('selected-slot');
          try{scene.sync();
            results.push({mode:'none',hidden:ctx.hidden,
              cache:ctx.hasAttribute('data-vr-selected-card-id')});
          }finally{selected.classList.add('selected-slot');scene.sync();}
          return {results,restored:!ctx.hidden&&
            !!ctx.dataset.vrSelectedCardId};
        }""")
        assert display_gate and display_gate['restored'] and (
          display_gate['results']==[
            {'mode':'double','hidden':True,'cache':False},
            {'mode':'none','hidden':True,'cache':False}
          ]),('VR01CH ambiguous selection still displayed native commands',display_gate)
        assert snap()==baseline,'VR01CH visual selection gate changed Phase21'
        # VR01CG: a VR-bound quick command must not turn into an unguarded
        # generic-integrated click during close, even before the original
        # stage is removed. No genuine native action executes in this test.
        closing_click=page.evaluate("""() => {
          const root=document.getElementById('gameScreen');
          const quick=document.getElementById('mrr-quick-attack');
          const native=document.querySelector('#inspectBody button[data-actor="attack"]');
          const ctx=document.getElementById('mrr-integrated-context');
          if(!root||!document.body.classList.contains('mrr-vr-active')||
             !root.classList.contains('mrr-integrated-playing')||
             !quick||quick.hidden||!ctx||ctx.hidden||
             !native||native.disabled)return null;
          const own=Object.prototype.hasOwnProperty.call(native,'click'),
            previous=native.click;
          let delegated=0;
          native.click=()=>{delegated++;};
          const fire=()=>quick.dispatchEvent(new MouseEvent('click',
            {bubbles:true,cancelable:true}));
          const result=[];
          try{
            fire();result.push({phase:'open',delegated});
            document.body.classList.remove('mrr-vr-active');
            try{fire();result.push({phase:'vr-closing',delegated});}
            finally{document.body.classList.add('mrr-vr-active');}
            root.classList.remove('mrr-integrated-playing');
            try{fire();result.push({phase:'stage-closing',delegated});}
            finally{root.classList.add('mrr-integrated-playing');}
            fire();result.push({phase:'reopened',delegated});
          }finally{
            if(own)native.click=previous;
            else delete native.click;
          }
          return result;
        }""")
        assert closing_click==[
          {'phase':'open','delegated':1},
          {'phase':'vr-closing','delegated':1},
          {'phase':'stage-closing','delegated':1},
          {'phase':'reopened','delegated':2}
        ],('VR01CG closing VR quick command delegated to Phase21',closing_click)
        assert snap()==baseline,'VR01CG close-transition guard changed Phase21'
        # VR01BX: viewport reflow must retain the SAME focused native
        # command and keep its actual clickable rectangle inside stage.
        page.locator('#mrr-quick-attack').focus()
        for focus_w,focus_h in ((1366,768),(2560,1440),(1920,1080)):
          page.set_viewport_size({'width':focus_w,'height':focus_h})
          page.wait_for_function("""() => {
            const ctx=document.querySelector('#mrr-integrated-context');
            const stage=document.querySelector('#mrr-integrated-stage');
            if(!ctx||ctx.hidden||!stage)return false;
            const a=ctx.getBoundingClientRect(),b=stage.getBoundingClientRect();
            const face=MRRIntegrated.scene.projectCardBounds(
              MRRIntegrated.state.scene.selectedKey);
            const overlap=face?Math.max(0,Math.min(a.right,face.right)-
              Math.max(a.left,face.left))*
              Math.max(0,Math.min(a.bottom,face.bottom)-Math.max(a.top,face.top)):999;
            return document.activeElement?.id==='mrr-quick-attack' &&
              a.left>=b.left+10&&a.right<=b.right-10&&
              a.top>=b.top+79&&a.bottom<=b.bottom-110&&overlap<4;
          }""",timeout=20000)
          assert snap()==baseline,(
            'VR01BX focused action resize changed Phase21',focus_w,focus_h)
        page.evaluate('document.activeElement?.blur()')
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
    # VR01AE: shortcut badges are the SAME native buttons, and never
    # promise an unavailable command. Browser click hit-test is unchanged.
    keys=page.evaluate("""() => ['attack','move'].map(k=>{
      const button=document.querySelector('#mrr-quick-'+k);
      const original=document.querySelector('#inspectBody button[data-actor="'+k+'"]');
      return {kind:k,enabled:!!original&&!original.disabled&&!button.hidden,
        key:button.dataset.vrShortcut||null,
        aria:button.getAttribute('aria-keyshortcuts'),
        decoration:getComputedStyle(button,'::after').content,
        pointer:getComputedStyle(button,'::after').pointerEvents};
    })""")
    for item in keys:
      expected={'attack':'A','move':'M'}[item['kind']] if item['enabled'] else None
      assert item['key']==expected and item['aria']==expected,item
      if expected:
        assert expected in item['decoration'] and item['pointer']=='none',item
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
    # VR01AF: a real targeting operation disables fresh A/M hotkeys.
    # Cosmetic key labels must agree without mutating the Phase21 game.
    page.wait_for_function("""() => ['attack','move'].every(kind=>{
      const button=document.querySelector('#mrr-quick-'+kind);
      return !!button && !button.dataset.vrShortcut &&
        !button.hasAttribute('aria-keyshortcuts');
    })""",timeout=12000)
    assert snap()==baseline,'VR01AF keycap cleanup changed native game'
    page.screenshot(path=str(ROOT/'tests/vr01af_targeting_keys_suppressed_1920x1080.png'),
      animations='disabled')
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
    # VR01AK: 2D return must restore focus to the existing VR entry so a
    # keyboard-only player can immediately reopen the same game view.
    assert page.evaluate("""() => document.activeElement?.id==='mrr-vr-open'"""),(
      'VR01AK 2D return lost keyboard focus')
    page.screenshot(path=str(ROOT/'tests/vr01ak_2d_return_focus_1920x1080.png'),
      animations='disabled')
    page.keyboard.press('Enter')
    page.wait_for_function('MRRVR.status.open && MRRIntegrated.state.scene.frames>3',
      timeout=45000)
    assert snap()==after,'VR01AK keyboard reopen changed Phase21 engine'
    # VR01AL: a genuine Enter key on the original entry should place focus
    # on the FIRST real 3D toolbar control, without executing a card action.
    assert page.evaluate("""() =>
      document.activeElement?.id==='vr-piles'"""),(
      'VR01AL keyboard 3D entry did not focus first toolbar control')
    page.screenshot(path=str(ROOT/'tests/vr01al_keyboard_entry_focus_1920x1080.png'),
      animations='disabled')
    page.keyboard.press('Tab')
    assert page.evaluate("""() =>
      document.activeElement?.id==='vr-inspector'"""),(
      'VR01AL keyboard toolbar tab order lost')
    assert snap()==after,'VR01AL focus/tab navigation changed Phase21 engine'
    page.locator('#vr-return').click()
    assert page.evaluate("""() => !MRRVR.status.open &&
      document.activeElement?.id==='mrr-vr-open'"""),(
      'VR01AK keyboard reopen did not restore 2D focus')
    assert snap()==after,'VR01AK second 2D return changed Phase21 engine'
    # VR01AM: Space is also a genuine keyboard activation and must reach
    # the first 3D toolbar button without changing the Phase21 snapshot.
    page.keyboard.press('Space')
    page.wait_for_function('MRRVR.status.open && MRRIntegrated.state.scene.frames>3',
      timeout=45000)
    assert page.evaluate("""() =>
      document.activeElement?.id==='vr-piles'"""),(
      'VR01AM Space entry did not focus first 3D control')
    assert snap()==after,'VR01AM Space entry changed native game'
    page.locator('#vr-return').click()
    assert page.evaluate("""() => !MRRVR.status.open &&
      document.activeElement?.id==='mrr-vr-open'""")
    # A cancelled synthetic keydown does not activate the button. A real
    # pointer click afterward must NOT inherit that stale keyboard intent.
    page.evaluate("""() => {
      const entry=document.querySelector('#mrr-vr-open');
      entry.dispatchEvent(new KeyboardEvent('keydown',{
        key:'Enter',bubbles:true,cancelable:true
      }));
    }""")
    page.locator('#mrr-vr-open').click()
    page.wait_for_function('MRRVR.status.open && MRRIntegrated.state.scene.frames>3',
      timeout=45000)
    assert page.evaluate("""() => document.activeElement?.id!=='vr-piles'"""),(
      'VR01AM pointer entry inherited stale keyboard focus')
    assert snap()==after,'VR01AM pointer entry changed native game'
    page.screenshot(path=str(ROOT/'tests/vr01am_pointer_entry_no_focus_1920x1080.png'),
      animations='disabled')
    page.locator('#vr-return').click()
    assert snap()==after,'VR01AM pointer return changed native game'
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
        # VR01BO: navigating hands is not a legal action during placement;
        # the status hint must prioritize the actual native placement.
        assert '← → 탐색' not in (page.locator('#vr-hint-text').text_content() or ''),(
          'VR01BO focus hint shown during real placement')
        # VR01AI: during a genuine Phase21 target declaration 1–0 cannot
        # start another hand selection. Only the cue/ARIA mirror changes.
        page.wait_for_function("""() => {
          const shell=document.querySelector('#mrr-vr-shell');
          return shell?.classList.contains('vr-hand-hotkeys-paused') &&
            [...shell.querySelectorAll('#vr-hand .vr-card')].every((card,i)=>{
              // VR01BD: every card, including positions beyond ten,
              // must lose the hover tooltip while placement is active.
              if(card.hasAttribute('title')||card.hasAttribute('aria-keyshortcuts'))
                return false;
              if(i>=10)return true;
              const keycap=card.querySelector('.vr-shortcut-key');
              return keycap&&Number(getComputedStyle(keycap).opacity)<.5;
            });
        }""",timeout=14000)
        assert snap()==prior,'VR01AI paused hand cues changed Phase21 state'
        # VR01BM: navigation shortcuts must not leave an active
        # Phase21 placement declaration or move focus within the folded fan.
        page.evaluate("""() => document.querySelector('#vr-hand .vr-card')?.focus()""")
        focused_before=page.evaluate("""() => document.activeElement===
          document.querySelector('#vr-hand .vr-card')""")
        assert focused_before,'VR01BM placement focus fixture unavailable'
        page.keyboard.press('End')
        page.keyboard.press('ArrowRight')
        assert page.evaluate("""() => document.activeElement===
          document.querySelector('#vr-hand .vr-card')"""),(
            'VR01BM navigation moved focus during native placement')
        assert snap()==prior,'VR01BM paused arrows changed Phase21 state'
        page.evaluate('document.activeElement?.blur()')
        page.screenshot(path=str(ROOT/'tests/vr01ai_hand_hotkeys_paused_1920x1080.png'),
          animations='disabled')
        page.screenshot(path=str(ROOT/'tests/vr01aa_native_place_guides_1920x1080.png'),
          animations='disabled')
        page.screenshot(path=str(ROOT/'tests/vr01x_native_place_command_1920x1080.png'),
          animations='disabled')
        page.locator('#vr-cancel').click()
        page.wait_for_function("""() => !document.querySelector('#arena .slot.legal') &&
          !document.querySelector('#mrr-vr-shell').classList.contains('vr-placing')""",timeout=14000)
        assert snap()==prior,'Cancelling hand placement spent native resources'
        page.wait_for_function("""() => {
          const shell=document.querySelector('#mrr-vr-shell');
          return shell && !shell.classList.contains('vr-hand-hotkeys-paused') &&
            [...shell.querySelectorAll('#vr-hand .vr-card')].every((card,i)=>{
              const tip=card.dataset.vrInspection+
                (card.dataset.vrKeyTitle?' · '+card.dataset.vrKeyTitle:'');
              return card.title===tip && (i>=10?
                !card.hasAttribute('aria-keyshortcuts'):
                card.getAttribute('aria-keyshortcuts')===(i===9?'0':String(i+1)));
            });
        }""",timeout=14000)
        assert snap()==prior,'VR01AI restored hand cues changed Phase21 state'
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
        # VR01BF: recreate a genuine previous-player inspection state so
        # the privacy assertion cannot pass vacuously on an already-flat hand.
        page.evaluate("""() => {
          const card=document.querySelector('#vr-hand .vr-card');
          if(card){card.classList.add('raised');card.focus();}
        }""")
        assert page.locator('#vr-hand .vr-card.raised').count()>0,(
          'VR01BF previous hand inspection fixture unavailable')
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
        # VR01AP: hidden cards also must be absent from keyboard and AT
        # navigation. The original private Phase21 overlay is authoritative.
        page.wait_for_function("""() => {
          const hand=document.querySelector('#vr-hand');
          const hint=document.querySelector('#vr-hint');
          return hand?.inert && hint?.inert &&
            hand.getAttribute('aria-hidden')==='true' &&
            hint.getAttribute('aria-hidden')==='true';
        }""",timeout=14000)
        # VR01BF: a prior player's expanded hand must lose its transient
        # inspection and tooltip state before the new hand is revealed.
        page.wait_for_function("""() => {
          const cards=[...document.querySelectorAll('#vr-hand .vr-card')];
          return cards.length>0 && cards.every(card=>
            !card.classList.contains('raised') &&
            !card.hasAttribute('title') &&
            !card.hasAttribute('aria-keyshortcuts'));
        }""",timeout=14000)
        guard_snapshot=snap()
        focus_blocked=page.evaluate("""() => {
          const button=document.querySelector('#vr-hand .vr-card');
          button?.focus();
          return document.activeElement!==button;
        }""")
        assert focus_blocked,'VR01AP hidden opponent hand accepted keyboard focus'
        assert snap()==guard_snapshot,'VR01AP private hand guard changed native game'
        page.screenshot(path=str(ROOT/'tests/vr01ap_native_private_handoff_1920x1080.png'),
          animations='disabled')
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
        # VR01AP: only the actual native reveal removes the keyboard/AT
        # privacy barrier; focus returns to current-player hand controls.
        page.wait_for_function("""() => {
          const hand=document.querySelector('#vr-hand');
          const hint=document.querySelector('#vr-hint');
          return hand && hint && !hand.inert && !hint.inert &&
            !hand.hasAttribute('aria-hidden') && !hint.hasAttribute('aria-hidden');
        }""",timeout=14000)
        # VR01BF: only actual passContinue can restore the newly
        # authorized player's public hand inspection and numeric cues.
        page.wait_for_function("""() => {
          const cards=[...document.querySelectorAll('#vr-hand .vr-card')];
          if(!cards.length)return false;
          return cards.every((card,i)=>{
            const hint=card.dataset.vrInspection+
              (card.dataset.vrKeyTitle?' · '+card.dataset.vrKeyTitle:'');
            const key=i<10?(i===9?'0':String(i+1)):null;
            return card.title===hint && (key?
              card.getAttribute('aria-keyshortcuts')===key:
              !card.hasAttribute('aria-keyshortcuts'));
          });
        }""",timeout=14000)
        reveal_snapshot=snap()
        hand_reenabled=page.evaluate("""() => {
          const button=document.querySelector('#vr-hand .vr-card');
          button?.focus();
          return !!button&&document.activeElement===button;
        }""")
        assert hand_reenabled,'VR01AP newly revealed hand cannot receive keyboard focus'
        assert reveal_snapshot==snap(),'VR01AP focus altered native game'
        page.screenshot(path=str(ROOT/'tests/vr01ap_native_private_reveal_1920x1080.png'),
          animations='disabled')
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
