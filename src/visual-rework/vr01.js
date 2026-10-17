/* VR01 - presentation-only PC game shell. Phase21 engine owns all gameplay. */
(() => {
'use strict';
const root=document.getElementById('gameScreen');
const bar=root?.querySelector('.mcw-top-controls');
if(!root||!bar||document.getElementById('mrr-vr-open'))return;
const q=(s,p=document)=>p.querySelector(s), qa=(s,p=document)=>[...p.querySelectorAll(s)];
const el=(tag,cls,txt)=>{
  const e=document.createElement(tag);if(cls)e.className=cls;
  if(txt!==undefined)e.textContent=String(txt);return e;
};
const clean=v=>String(v||'').replace(/\s+/g,' ').trim();
const native=selector=>{const n=q(selector);if(!n||n.disabled)return false;n.click();return true;};
const entry=el('button','','VR01 새 게임 화면');entry.id='mrr-vr-open';entry.type='button';bar.append(entry);
let open=false,busy=false,ui=null,stage=null,observer=null,interval=null,scheduled=0,handSignature='',handArtSources=[],backCount=-1;
let tacticalCamera='tabletop';
const nativeCardLabels=new Map(),nativeStatBadges=new Map(),nativeActionMarks=new Map();
let nativeHpSnapshot=new Map(),recentHpChanges=new Map(),lastCombatTime=null,vrOutcomeCount=0,lastOutcome=null;
const outcomeNodes=[],outcomeHistory=[];
const button=(id,txt,fn)=>{const e=el('button','vr-btn',txt);e.id=id;e.type='button';e.onclick=fn;return e;};
function buildUI(){
  ui=el('section','vr-shell');ui.id='mrr-vr-shell';ui.setAttribute('aria-label','3D 카드게임 통합 화면');
  const border=el('div','vr-outline');ui.append(border);
  const header=el('div','vr-header');
  const logo=el('div','vr-logo');logo.append(el('small','','MARORONG'),el('strong','','CARD WAR'),el('small','','VISUAL REWORK'));
  const heroEnemy=el('div','vr-hero vr-enemy');heroEnemy.id='vr-enemy';
  heroEnemy.append(el('div','vr-portrait','E'),el('div','vr-profile'),el('div','vr-hp'));
  const tools=el('div','vr-tools');tools.append(
    button('vr-piles','덱 · 묘지',()=>native('#mrr-integrated-rail')),
    button('vr-inspector','카드 상세',()=>native('#mrr-integrated-inspector')),
    button('vr-camera','시점: 전체',()=>{
      const views=['tabletop','ally','enemy'];
      const labels=['시점: 전체','시점: 아군','시점: 상대'];
      const next=(views.indexOf(tacticalCamera)+1)%views.length;
      const scene=window.MRRIntegrated?.scene;
      if(scene?.setCameraPreset(views[next])){
        tacticalCamera=views[next];q('#vr-camera',ui).textContent=labels[next];
        positionActiveOutcomes();schedule();
      }
    }),
    button('vr-return','2D 보기',closeUI));
  header.append(logo,heroEnemy,tools);ui.append(header);
  const enemyFan=el('div','vr-enemy-fan');enemyFan.id='vr-enemy-fan';enemyFan.setAttribute('aria-label','상대 손패 뒷면');ui.append(enemyFan);
  // Territorial markings belong to the real Three.js arena, not a floating
  // flat HTML centerline that drifts away when the user changes camera.
  // Public, world-anchored card identity plaques, not a second card face.
  // The authoritative slot still owns pointer picking and original actions.
  const plaques=el('div','vr-public-plaques');plaques.id='vr-public-plaques';
  plaques.setAttribute('aria-label','공개 전장 카드 이름과 능력치');
  ui.append(plaques);
  const outcomes=el('div','vr-combat-outcomes');outcomes.id='vr-combat-outcomes';
  outcomes.setAttribute('aria-label','실제 전투 결과 연출');ui.append(outcomes);
  const piles=el('div','vr-pile-display');
  for(const word of ['DECK','GRAVE','EXILE']){const token=button('vr-token-'+word.toLowerCase(),word,()=>native('#mrr-integrated-rail'));token.className='vr-pile';piles.append(token);}
  ui.append(piles);
  const footer=el('div','vr-footer');
  const heroAlly=el('div','vr-hero vr-ally');heroAlly.id='vr-ally';
  heroAlly.append(el('div','vr-portrait','M'),el('div','vr-profile'),el('div','vr-hp'));
  footer.append(heroAlly,button('vr-end-turn','턴 종료',()=>native('#endTurn')));ui.append(footer);
  const hand=el('div','vr-hand');hand.id='vr-hand';hand.setAttribute('aria-label','내 실제 손패');ui.append(hand);
  const hint=el('div','vr-hint');hint.id='vr-hint';
  const hintMode=el('span','vr-hint-mode','손패');
  hintMode.id='vr-hint-mode';hintMode.setAttribute('aria-hidden','true');
  const hintText=el('span','','손패 클릭 또는 숫자 키로 선택');hintText.id='vr-hint-text';
  // Delegate cancellation to Phase21, including hand placement where the
  // selected-card context menu intentionally has no battlefield source.
  const cancel=button('vr-cancel','선택 취소',()=>{
    native('#inspectBody button[data-cancel-action]');
    window.MRRIntegrated?.scene?.sync();schedule();
  });
  // VR01W: keep Phase21 cancellation authoritative, with one visible PC
  // shortcut cue on the same existing VR control.
  cancel.setAttribute('aria-keyshortcuts','C');
  cancel.title='C · 현재 선택 취소';
  const cancelKey=el('kbd','vr-cancel-key','C');
  cancelKey.setAttribute('aria-hidden','true');
  cancel.append(cancelKey);
  cancel.hidden=true;hint.append(hintMode,hintText,cancel);ui.append(hint);
  q('#vr-camera',ui).title='시점 전환 · 휠로 확대·축소 · 전장 드래그 회전 없음';
  const aim=document.createElementNS('http://www.w3.org/2000/svg','svg');
  aim.id='vr-aim';aim.setAttribute('preserveAspectRatio','none');
  aim.innerHTML='<defs><marker id="vr-arrow" markerWidth="7" markerHeight="7" refX="8" refY="5" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10Z" fill="#f0b982"/></marker><marker id="vr-move-arrow" markerWidth="7" markerHeight="7" refX="8" refY="5" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10Z" fill="#b5ccff"/></marker></defs><g id="vr-guide-targets"></g><path id="vr-aim-line" fill="none" stroke="#f0b982" stroke-width="3" marker-end="url(#vr-arrow)" />';
  ui.append(aim);
  stage.append(ui);
  stage.addEventListener('pointermove',updateAim);
}
function updateAim(){
  if(!open||!ui)return;
  const path=q('#vr-aim-line',ui),guides=q('#vr-guide-targets',ui);
  const scene=window.MRRIntegrated?.scene,state=scene?.state;
  const targets=state?.selectedKey&&state.attackTargetCount?
    qa('#arena .slot.attack-target').filter(slot=>slot.querySelector('.board-card .card-ui')):[];
  const box=stage.getBoundingClientRect();
  q('#vr-aim',ui).setAttribute('viewBox','0 0 '+box.width+' '+box.height);
  const ns='http://www.w3.org/2000/svg';
  const old=new Map([...guides.children].map(node=>[node.dataset.slot,node]));
  for(const slot of targets){
    const key=slot.getAttribute('data-slot');
    const bounds=scene.projectCardBounds?.(key);
    if(!bounds)continue;
    const width=bounds.right-bounds.left,height=bounds.bottom-bounds.top;
    if(!Number.isFinite(width)||!Number.isFinite(height)||width<=0||height<=0)continue;
    // VR01R: trace the actual projected public card, not a fixed-size
    // reticle. The authoritative native .attack-target remains the only
    // source of legal targets; the SVG has no pointer or gameplay handlers.
    const inset=Math.min(9,Math.min(width,height)*.065);
    let outline=old.get(key);
    if(!outline||outline.localName!=='rect'){
      outline?.remove();
      outline=document.createElementNS(ns,'rect');
      outline.dataset.slot=key;
      outline.setAttribute('class','vr-target-guide');
      outline.setAttribute('rx','8');
      outline.setAttribute('ry','8');
      guides.append(outline);
    }
    outline.setAttribute('x',(bounds.left-box.left+inset).toFixed(1));
    outline.setAttribute('y',(bounds.top-box.top+inset).toFixed(1));
    outline.setAttribute('width',Math.max(2,width-inset*2).toFixed(1));
    outline.setAttribute('height',Math.max(2,height-inset*2).toFixed(1));
    outline.classList.toggle('vr-target-hover',state.hoveredKey===key);
    old.delete(key);
  }
  // VR01AA: project ONLY genuine vacant native legal slots. Phase21 still
  // provides every allowed destination and owns all clicks; SVG circles
  // have no hit areas and do not affect summons, movement, or abilities.
  const legalMode=q('#vr-hint',ui)?.dataset.mode;
  if((legalMode==='place'||legalMode==='move')&&scene?.projectSlot){
    const legal=qa('#arena .slot.legal').filter(slot=>
      !slot.querySelector('.board-card .card-ui'));
    for(const slot of legal){
      const key=slot.getAttribute('data-slot'),point=scene.projectSlot(key);
      if(!key||!point||!Number.isFinite(point.x)||!Number.isFinite(point.y)||
        point.x<box.left||point.x>box.right||
        point.y<box.top||point.y>box.bottom)continue;
      let marker=old.get(key);
      if(!marker||marker.localName!=='circle'){
        marker?.remove();marker=document.createElementNS(ns,'circle');
        marker.dataset.slot=key;marker.setAttribute('class','vr-legal-guide');
        guides.append(marker);
      }
      marker.dataset.mode=legalMode;
      marker.classList.toggle('vr-legal-hover',state?.hoveredKey===key);
      marker.setAttribute('cx',(point.x-box.left).toFixed(1));
      marker.setAttribute('cy',(point.y-box.top).toFixed(1));
      marker.setAttribute('r',String(Math.max(11,Math.min(19,box.width*.014))));
      old.delete(key);
    }
  }
  for(const stale of old.values())stale.remove();
  // VR01AB: preview movement ONLY when hovering an actual native legal,
  // vacant destination. The existing selected public card is the source.
  // No preview is ever treated as a command or a confirmed engine action.
  const target=targets.find(slot=>slot.getAttribute('data-slot')===state?.hoveredKey);
  const moveTarget=!target&&legalMode==='move'&&state?.selectedKey?
    qa('#arena .slot.legal').find(slot=>slot.dataset.slot===state.hoveredKey&&
      !slot.querySelector('.board-card .card-ui')):null;
  const src=target||moveTarget?scene.projectCard(state.selectedKey):null;
  const dst=target?scene.projectCard(state.hoveredKey):
    moveTarget?scene.projectSlot(state.hoveredKey):null;
  if(!src||!dst){path.setAttribute('d','');path.dataset.target='';path.dataset.mode='';return;}
  const sx=src.x-box.left,sy=src.y-box.top,ex=dst.x-box.left,ey=dst.y-box.top;
  const bend=Math.max(20,Math.min(65,Math.abs(ex-sx)*.15));
  path.setAttribute('d','M'+sx.toFixed(1)+' '+sy.toFixed(1)+' Q'+
    ((sx+ex)/2).toFixed(1)+' '+(Math.min(sy,ey)-bend).toFixed(1)+' '+
    ex.toFixed(1)+' '+ey.toFixed(1));
  path.dataset.target=state.hoveredKey;
  path.dataset.mode=moveTarget?'move':'attack';
  path.setAttribute('marker-end',moveTarget?'url(#vr-move-arrow)':'url(#vr-arrow)');
}
function updateBacks(){
  // Read only publicly displayed opponent backs. Never read the opponent hand array.
  const n=qa('#enemyHand .mcw-back').length;if(n===backCount)return;
  backCount=n;const fan=q('#vr-enemy-fan',ui);fan.replaceChildren();
  const step=Math.min(innerWidth<1500?41:52,(innerWidth-360)/Math.max(1,n));
  for(let i=0;i<n;i++){
    const back=el('div','vr-back');back.setAttribute('aria-label','상대 카드 뒷면 '+(i+1));
    back.style.setProperty('--x',((i-(n-1)/2)*step)+'px');
    back.style.setProperty('--angle',((i-(n-1)/2)*Math.min(5,22/Math.max(n-1,1)))+'deg');
    fan.append(back);
  }
}
function updateHand(){
  const src=qa('#hand .hand-slot');
  const hand=src.map((slot,i)=>{
    const c=q('.card-ui',slot),t=s=>clean(q(s,c||slot)?.textContent);
    return {i,name:t('.card-name')||'카드',cost:t('.cost-bubble'),kind:t('.card-kind'),summary:t('.card-summary'),stats:t('.card-stats')};
  });
  // VR01AG: existing current-player hand art may change independently
  // of card text. Track only artwork already present in the visible native
  // hand DOM, never game-engine or opponent private card data.
  const artSources=src.map(slot=>{
    const img=q('.art-well > .mrr-owner-art',slot);
    return [img?.getAttribute('src')||'',img?.getAttribute('srcset')||''];
  });
  const signature=JSON.stringify(hand);
  const artChanged=artSources.length!==handArtSources.length||
    artSources.some((pair,i)=>pair[0]!==handArtSources[i]?.[0]||
      pair[1]!==handArtSources[i]?.[1]);
  if(handSignature===signature&&!artChanged)return;
  const fan=q('#vr-hand',ui);
  // VR01AJ: the same visible Phase21 cards can have cosmetic changes
  // to cost, rules or stats. Keep each existing 3D button/focus/hover and
  // update its displayed text in place instead of replacing the whole fan.
  // Genuine hand identity/order changes still use the full rebuild below.
  const previousHand=handSignature?JSON.parse(handSignature):[];
  const sameVisibleCards=previousHand.length===hand.length&&
    fan.children.length===hand.length&&hand.every((d,i)=>
      d.name===previousHand[i].name&&d.kind===previousHand[i].kind);
  if(sameVisibleCards){
    src.forEach((slot,i)=>{
      const card=fan.children[i],d=hand[i];
      for(const [selector,value] of [
        ['.vr-mana',d.cost||'0'],
        ['.vr-rules',d.summary||''],
        ['.vr-stats',d.stats||'']]){
        const node=q(selector,card);
        if(node&&node.textContent!==value)node.textContent=value;
      }
      // Preserve VR01AG/AH dynamic Phase59 artwork behavior as well.
      const face=q('.vr-art-blank',card);
      if(!face)return;
      const nativeArt=q('.art-well > .mrr-owner-art',slot);
      const mirrored=q('.vr-provided-art',face);
      if(nativeArt){
        if(mirrored){
          for(const attr of ['src','srcset','alt']){
            if(nativeArt.hasAttribute(attr))mirrored.setAttribute(attr,nativeArt.getAttribute(attr));
            else mirrored.removeAttribute(attr);
          }
        }else{
          const img=nativeArt.cloneNode(false);
          img.className='vr-provided-art';face.append(img);
        }
      }else mirrored?.remove();
    });
    handSignature=signature;handArtSources=artSources;
    return;
  }
  handSignature=signature;handArtSources=artSources;
  fan.replaceChildren();
  const n=hand.length,step=Math.min(innerWidth<1500?72:innerWidth<2200?91:108,
    Math.max(43,(innerWidth-420)/Math.max(1,n)));
  for(const d of hand){
    const card=el('button','vr-card');card.type='button';
    card.setAttribute('aria-label',d.name+' 손패 선택');card.dataset.index=String(d.i);
    if(d.i<10){
      const shortcut=d.i===9?'0':String(d.i+1);
      card.setAttribute('aria-keyshortcuts',shortcut);
      card.title=d.name+' · 단축키 '+shortcut;
      card.dataset.vrKeyTitle=card.title;
    }
    card.style.setProperty('--x',((d.i-(n-1)/2)*step)+'px');
    card.style.setProperty('--hit',step+'px');
    card.style.setProperty('--angle',((d.i-(n-1)/2)*Math.min(5,22/Math.max(n-1,1)))+'deg');
    card.style.zIndex=String(d.i+2);
    const surface=el('div','vr-card-face');
    const artwork=el('div','vr-art-blank');
    const ownerArt=q('.art-well > .mrr-owner-art',src[d.i]);
    if(ownerArt) {const img=ownerArt.cloneNode(false);img.className='vr-provided-art';artwork.append(img);}
    surface.append(el('span','vr-mana',d.cost||'0'),el('div','vr-name',d.name),
      artwork,el('div','vr-kind',d.kind||'카드'),el('div','vr-rules',d.summary||''),el('div','vr-stats',d.stats||''));
    card.append(surface);
    // VR01V visual QA: keep the keycap on the pointer anchor, NOT inside
    // the overlapped card face. The top edge stays visible while the hand
    // is folded down during native placement / targeting.
    if(d.i<10){
      const keycap=el('span','vr-shortcut-key',d.i===9?'0':String(d.i+1));
      keycap.setAttribute('aria-hidden','true');
      card.append(keycap);
    }
    card.addEventListener('click',()=>{
      const original=qa('#hand .hand-slot')[d.i];
      if(original){
        // Arm a visual launch at the hand card's actual onscreen position.
        // The 3D scene waits until original Phase21 rules really create a
        // public allied card before animating; no imaginary summon is made.
        const origin=surface.getBoundingClientRect();
        window.MRRIntegrated?.scene?.armDeployment?.({
          name:d.name,x:origin.left+origin.width/2,
          y:Math.min(origin.bottom-20,window.innerHeight-20)});
        original.click(); // Exactly one original hand click.
      }
      schedule();
    });
    card.addEventListener('mouseenter',()=>card.classList.add('raised'));
    card.addEventListener('mouseleave',()=>card.classList.remove('raised'));
    fan.append(card);
  }
  fan.dataset.count=String(n);
}
// Native Phase21 .hand-slot.active is authoritative. Keep this in refresh,
// outside the hand content signature, so selecting/cancelling never leaves
// a stale highlighted 3D hand card or regenerates every card mesh.
function syncNativeHandSelection(){
  const source=qa('#hand .hand-slot'),mirror=qa('#vr-hand .vr-card',ui);
  for(let i=0;i<mirror.length;i++){
    const active=!!source[i]?.classList.contains('active');
    mirror[i].classList.toggle('vr-native-selected',active);
    mirror[i].setAttribute('aria-pressed',active?'true':'false');
  }
}
function updatePublicPlaques(){
  const host=q('#vr-public-plaques',ui),scene=window.MRRIntegrated?.scene;
  if(!host||!scene?.projectCardBounds||!stage)return;
  const bounds=stage.getBoundingClientRect(),seen=new Set();
  const selected=scene.state?.selectedKey,hovered=scene.state?.hoveredKey;
  const projected=qa('#arena [data-slot]').map(slot=>{
    const card=q('.board-card .card-ui',slot);
    if(!card)return null;
    const key=slot.getAttribute('data-slot'),rect=scene.projectCardBounds(key);
    if(!rect)return null;
    return {slot,card,key,rect,lane:key.slice(0,key.lastIndexOf(':')),
      cx:(rect.left+rect.right)/2-bounds.left,
      top:rect.top-bounds.top,bottom:rect.bottom-bounds.top,
      priority:key===selected?0:slot.classList.contains('attack-target')?1:
        key===hovered?2:3};
  }).filter(Boolean);
  // VR01G: a dense card game table must remain a card table, not a
  // scoreboard made of two dozen giant floating rectangular HUD panels.
  // Preserve full public name/stats in the native 3D face and inspection.
  const dense=projected.length>=16;
  ui.classList.toggle('vr-dense-public',dense);
  // Put native-targeted cards first, then work back-to-front. These labels
  // are display-only and never change source slot order or hit locations.
  projected.sort((a,b)=>a.priority-b.priority||a.top-b.top||a.cx-b.cx);
  const reserved=[];
  const overlaps=(a,b)=>a.x<b.x+b.w+4&&a.x+a.w+4>b.x&&
    a.y<b.y+b.h+3&&a.y+a.h+3>b.y;
  for(const p of projected){
    const {slot,card,key,lane,cx,top,bottom}=p;
    seen.add(key);
    let plaque=nativeCardLabels.get(key);
    if(!plaque){
      plaque=el('div','vr-unit-plaque');
      plaque.setAttribute('data-slot',key);
      plaque.append(el('strong','vr-unit-name'),el('small','vr-unit-stats'));
      host.append(plaque);nativeCardLabels.set(key,plaque);
    }
    const name=clean(q('.card-name',card)?.textContent)||'공개 카드';
    const stats=clean(q('.card-stats',card)?.textContent);
    const nameEl=q('.vr-unit-name',plaque),statsEl=q('.vr-unit-stats',plaque);
    if(nameEl.textContent!==name)nameEl.textContent=name;
    if(statsEl.textContent!==stats)statsEl.textContent=stats;
    plaque.title=[name,stats].filter(Boolean).join(' · ');
    // VR01H: current combat values from PUBLIC Phase21 rendered elements.
    // Never infer stats from deck registry, card ID or private G objects.
    const publicSpans=qa('.card-stats > span',card);
    const atkText=clean(publicSpans.find(node=>/^(검|공)(?:격력)?\s*\d+/.test(clean(node.textContent)))?.textContent);
    const hpText=clean(publicSpans.find(node=>/^체(?:력)?\s*\d+/.test(clean(node.textContent)))?.textContent);
    const atkMatch=atkText.match(/^(검|공)(?:격력)?\s*(\d+)/);
    const hpMatch=hpText.match(/^체(?:력)?\s*(\d+)/);
    let badge=nativeStatBadges.get(key);
    if(!badge&&atkMatch&&hpMatch){
      badge=el('div','vr-public-combat');
      badge.setAttribute('data-slot',key);
      badge.append(el('span','vr-combat-atk'),el('span','vr-combat-hp'));
      host.append(badge);nativeStatBadges.set(key,badge);
    }
    if(badge){
      const faceWidth=Math.max(0,p.rect.right-p.rect.left);
      const size=Math.min(23,Math.max(14,faceWidth*.26));
      // Badge pair sits entirely WITHIN its projected public card face.
      const canShow=!!(atkMatch&&hpMatch&&faceWidth>=2*size+4&&
        p.rect.bottom-p.rect.top>=size+12);
      badge.hidden=!canShow;
      if(canShow){
        const attack=q('.vr-combat-atk',badge),health=q('.vr-combat-hp',badge);
        const attackValue=atkMatch[2],hpValue=hpMatch[1];
        if(attack.textContent!==attackValue)attack.textContent=attackValue;
        if(health.textContent!==hpValue)health.textContent=hpValue;
        attack.setAttribute('aria-label',atkMatch[1]+' '+attackValue);
        health.setAttribute('aria-label','체력 '+hpValue);
        badge.setAttribute('aria-label',atkMatch[1]+' '+attackValue+' · 체력 '+hpValue);
        badge.title=[name,atkMatch[1]+' '+attackValue,'체력 '+hpValue].join(' · ');
        badge.dataset.publicAttack=attackValue;
        badge.dataset.publicHealth=hpValue;
        badge.style.left=(p.rect.left-bounds.left+2).toFixed(1)+'px';
        badge.style.top=(p.rect.bottom-bounds.top-size-4).toFixed(1)+'px';
        badge.style.width=(faceWidth-4).toFixed(1)+'px';
        badge.style.setProperty('--vr-combat-size',size.toFixed(1)+'px');
      }
    }
    // VR01I: use only explicit, publicly rendered Phase21 status and native
    // selected/attack-target slot classes. An absent status-chip does NOT
    // imply ready-to-act: legal actions depend on native turn/rule conditions.
    const chipText=clean(q('.board-card .status-chip',slot)?.textContent);
    const action=slot.classList.contains('attack-target')?
      {kind:'target',glyph:'⚔',label:'공격 대상'}:
      slot.classList.contains('selected-slot')?
      {kind:'selected',glyph:'◆',label:'선택됨'}:
      slot.classList.contains('legal')?
      {kind:'legal',glyph:'↗',label:'행동 가능한 위치'}:
      /행동 완료/.test(chipText)?
      {kind:'acted',glyph:'✓',label:'행동 완료'}:
      /^대기/.test(chipText)?
      {kind:'waiting',glyph:'⌛',label:chipText}:
      /^보호/.test(chipText)?
      {kind:'ward',glyph:'◇',label:chipText}:
      chipText?{kind:'other',glyph:'•',label:chipText}:null;
    let mark=nativeActionMarks.get(key);
    if(action&&!mark){
      mark=el('span','vr-public-action');
      mark.setAttribute('data-slot',key);host.append(mark);
      nativeActionMarks.set(key,mark);
    }
    if(mark){
      const faceWidth=p.rect.right-p.rect.left,faceHeight=p.rect.bottom-p.rect.top;
      const size=Math.min(19,Math.max(12,faceWidth*.26));
      const available=!!action&&faceWidth>=size+7&&faceHeight>=size+12;
      mark.hidden=!available;
      mark.dataset.state=action?.kind||'none';
      if(available){
        if(mark.textContent!==action.glyph)mark.textContent=action.glyph;
        mark.title=action.label;
        mark.setAttribute('aria-label',action.label);
        mark.style.left=(p.rect.right-bounds.left-size-3).toFixed(1)+'px';
        mark.style.top=(p.rect.top-bounds.top+3).toFixed(1)+'px';
        mark.style.width=mark.style.height=size.toFixed(1)+'px';
        mark.style.fontSize=Math.max(9,size*.72).toFixed(1)+'px';
      }
    }
    plaque.classList.toggle('vr-enemy-unit',key.startsWith('1:'));
    plaque.classList.toggle('vr-selected-unit',key===selected);
    plaque.classList.toggle('vr-target-unit',slot.classList.contains('attack-target'));
    const gap=Math.min(Infinity,...projected.filter(other=>other.key!==key&&other.lane===lane)
      .map(other=>Math.abs(other.cx-cx)));
    const wide=bounds.width<1500?117:166;
    // The visible label cannot be wider than the actual gap in its 3D row.
    const desired=Number.isFinite(gap)?Math.min(wide,gap-10):wide;
    const sizes=dense?[Math.min(92,Math.max(66,desired)),58]:
      [Math.max(76,desired),72,58];
    const marginX=bounds.width<1500?61:72;
    const yMin=100,yMax=bounds.height-94;
    let solution=null,compact=false;
    for(const width of sizes){
      const isCompact=dense||width<98,height=isCompact?25:41;
      const offsets=[
        [0,bottom+8],[0,top-height-8],
        [0,bottom+height+15],[0,top-height*2-16],
        [0,bottom+height*2+22],
        [-width*.65,bottom+8],[width*.65,bottom+8],
        [-width*.65,top-height-8],[width*.65,top-height-8]
      ];
      for(const [shift,cy] of offsets){
        const x=cx+shift-width/2,y=cy;
        const r={x,y,w:width,h:height};
        if(x<marginX||x+width>bounds.width-marginX||y<yMin||y+height>yMax)continue;
        if(reserved.some(old=>overlaps(r,old)))continue;
        solution=r;compact=isCompact;break;
      }
      if(solution)break;
    }
    plaque.hidden=!solution;
    if(!solution)continue;
    plaque.classList.toggle('vr-unit-compact',compact);
    plaque.style.width=solution.w.toFixed(1)+'px';
    plaque.style.left=(solution.x+solution.w/2).toFixed(1)+'px';
    plaque.style.top=solution.y.toFixed(1)+'px';
    reserved.push(solution);
  }
  for(const [key,plaque] of nativeCardLabels){
    if(seen.has(key))continue;
    plaque.remove();nativeCardLabels.delete(key);
  }
  for(const [key,badge] of nativeStatBadges){
    if(seen.has(key))continue;
    badge.remove();nativeStatBadges.delete(key);
  }
  for(const [key,mark] of nativeActionMarks){
    if(seen.has(key))continue;
    mark.remove();nativeActionMarks.delete(key);
  }
}
// VR01S: confirmed impact badges follow public card coordinates as camera or viewport changes.
function positionConfirmedOutcome(node,key,scene){
  const point=scene.projectCard(key)||scene.projectSlot(key);
  if(!point||!stage)return false;
  const rect=stage.getBoundingClientRect();
  node.style.left=Math.max(42,Math.min(rect.width-42,point.x-rect.left)).toFixed(1)+'px';
  node.style.top=Math.max(92,Math.min(rect.height-88,point.y-rect.top-30)).toFixed(1)+'px';
  return true;
}
function positionActiveOutcomes(){
  if(!open||!stage)return;
  const scene=window.MRRIntegrated?.scene;
  if(!scene)return;
  for(const item of outcomeNodes)positionConfirmedOutcome(item.node,item.key,scene);
}
function reconcileConfirmedOutcomes(){
  if(!open||!ui)return;
  const scene=window.MRRIntegrated?.scene,st=scene?.state;
  if(!st)return;
  const now=performance.now(),current=new Map();
  for(const slot of qa('#arena [data-slot]')){
    const card=q('.board-card .card-ui',slot);
    if(!card)continue;
    const value=qa('.card-stats > span',card).map(n=>clean(n.textContent))
      .map(t=>t.match(/^체(?:력)?\s*(\d+)/)).find(Boolean);
    if(value)current.set(slot.dataset.slot,Number(value[1]));
  }
  // Retain a public HP change briefly until the matching native FX arrives,
  // regardless of which mutation observer runs first.
  for(const [key,oldHp] of nativeHpSnapshot){
    const hp=current.get(key);
    if(hp!==oldHp)recentHpChanges.set(key,{before:oldHp,after:hp,at:now});
  }
  nativeHpSnapshot=current;
  for(const [key,item] of recentHpChanges)if(now-item.at>1800)recentHpChanges.delete(key);
  const events=st.nativeCombatEvents||[];
  if(lastCombatTime===null){
    lastCombatTime=Math.max(0,...events.map(x=>x.at||0));
    return;
  }
  const host=q('#vr-combat-outcomes',ui);
  for(const event of events){
    if(!event||event.at<=lastCombatTime)continue;
    if(event.type!=='hit'&&event.type!=='heal')continue;
    const changed=recentHpChanges.get(event.key),heal=event.type==='heal';
    const diff=changed&&Number.isFinite(changed.before)&&Number.isFinite(changed.after)?
      changed.after-changed.before:null;
    const exact=(heal&&diff>0)||(!heal&&diff<0);
    // A confirmed FX with no verified public change is only an impact,
    // never a fabricated numerical damage/heal amount.
    const msg=exact?(heal?'+':'−')+Math.abs(diff):heal?'회복':'명중';
    const node=el('span','vr-combat-outcome',msg);
    node.dataset.slot=event.key;node.dataset.kind=event.type;
    node.dataset.amount=exact?String(Math.abs(diff)):'';
    node.setAttribute('aria-label',heal?'회복 결과 '+msg:'피격 결과 '+msg);
    if(!positionConfirmedOutcome(node,event.key,scene))continue;
    if(matchMedia('(prefers-reduced-motion: reduce)').matches)node.classList.add('vr-no-motion');
    host.append(node);outcomeNodes.push({node,key:event.key,at:now});
    lastOutcome={key:event.key,type:event.type,amount:exact?Math.abs(diff):null,label:msg};
    outcomeHistory.push(lastOutcome);if(outcomeHistory.length>16)outcomeHistory.shift();
    vrOutcomeCount++;
  }
  lastCombatTime=Math.max(lastCombatTime,...events.map(x=>x.at||0));
  for(let i=outcomeNodes.length-1;i>=0;i--){
    const item=outcomeNodes[i];
    if(now-item.at>=1500){
      item.node.remove();outcomeNodes.splice(i,1);
      continue;
    }
    positionConfirmedOutcome(item.node,item.key,scene);
  }
}
function refresh(){
 if(!open||!ui)return;
 reconcileConfirmedOutcomes();
 updateHand();syncNativeHandSelection();updateBacks();updatePublicPlaques();
 for(const [sel,portrait,mana,fallback] of [
   ['#vr-ally','#myPortrait','#myMana','아군'],
   ['#vr-enemy','#enemyPortrait','#enemyMana','상대']]){
   const dest=q(sel,ui),name=clean(q(portrait+' .hq-name')?.textContent)||fallback;
   const hp=clean(q(portrait+' .hp-badge')?.textContent);
   const resource=clean(q(mana)?.textContent).slice(0,50);
   const copy=q('.vr-profile',dest);
   // Update only when changed to avoid recreating visible elements every frame.
   const str=name+'|'+resource;
   if(copy.dataset.value!==str){copy.dataset.value=str;copy.replaceChildren(el('strong','',name),el('small','',resource));}
   q('.vr-hp',dest).textContent=hp?'HP '+hp:'HP';
 }
 // VR01X: a compact command strip derived entirely from Phase21 legal
 // DOM slot classes and the original scene's public selected key.
 // This does NOT create a command, legal target or gameplay selection.
 const legalCount=qa('#arena .slot.legal').length;
 const attackCount=qa('#arena .slot.attack-target').length;
 const selectedKey=window.MRRIntegrated?.state.scene?.selectedKey;
 // VR01Z: movement is NOT hand deployment. Derive the distinction from
 // the original Phase21 inspector's public result-preview instructions.
 // Neither this label nor the adjacent-slot count changes move rules.
 const preview=clean(q('#inspectBody .result-preview')?.textContent);
 const moving=legalCount>0&&preview.includes('인접한 빈칸 선택');
 const mode=attackCount?'attack':moving?'move':legalCount?'place':
   selectedKey?'selected':'hand';
 const modeName={attack:'공격',move:'이동',place:'배치',selected:'선택',hand:'손패'};
 // VR01Y: the original Phase21 inspector is authoritative about which
 // commands can execute. These hints and hotkeys only mirror enabled
 // context commands and never supply new movement/attack rules.
 const attackControl=q('#inspectBody button[data-actor="attack"]');
 const moveControl=q('#inspectBody button[data-actor="move"]');
 const attackQuick=q('#mrr-quick-attack');
 const moveQuick=q('#mrr-quick-move');
 // VR01AF: advertise A/M only while the SAME native action can run.
 // A targeting state, private handoff or hidden/disabled native command
 // must never display a shortcut that the real keyboard handler rejects.
 const canNativeCommand=(native,quick)=>!!(mode==='selected'&&selectedKey&&
   native&&!native.disabled&&quick&&!quick.hidden&&!quick.disabled&&
   !q('#mrr-integrated-context')?.hidden&&
   q('#overlay')?.classList.contains('hidden'));
 const canAttack=canNativeCommand(attackControl,attackQuick);
 const canMove=canNativeCommand(moveControl,moveQuick);
 // VR01AE: cosmetic key labels remain on the ORIGINAL Phase21 buttons.
 for(const [control,key,enabled] of [
   [attackQuick,'A',canAttack],
   [moveQuick,'M',canMove]
 ]){
   if(!control)continue;
   if(enabled&&!control.hidden){
     control.setAttribute('aria-keyshortcuts',key);
     control.dataset.vrShortcut=key;
     control.title=control.textContent.trim()+' · '+key+' 단축키';
   }else{
     control.removeAttribute('aria-keyshortcuts');
     delete control.dataset.vrShortcut;
     control.removeAttribute('title');
   }
 }

 const commands=[canAttack?'A 공격':'',canMove?'M 이동':''].filter(Boolean);
 const instruction=mode==='attack'?'공격 대상 '+attackCount+'곳 · 카드 선택':
   mode==='move'?'이동 가능 '+legalCount+'곳 · 인접 빈칸 선택':
   mode==='place'?'배치 가능 '+legalCount+'곳 · 전장 위치 선택':
   mode==='selected'?(commands.length?'카드 명령 · '+commands.join(' · '):
     '선택 카드의 명령을 실행하세요'):
   '손패 클릭 또는 숫자 1–0으로 선택';
 ui.classList.toggle('vr-placing',!!(legalCount||attackCount));
 // VR01AI: number keys are blocked by the existing Phase21-aware handler
 // during targeting or private handoff. Match the cues on the same genuine
 // current-player hand buttons without disabling mouse clicks or game rules.
 const handButtons=qa('#vr-hand .vr-card',ui);
 const handHotkeysActive=legalCount===0&&attackCount===0&&
   q('#overlay')?.classList.contains('hidden')&&
   handButtons.length===qa('#hand .hand-slot').length;
 ui.classList.toggle('vr-hand-hotkeys-paused',!handHotkeysActive);
 handButtons.forEach((card,i)=>{
   if(i>=10)return;
   const key=i===9?'0':String(i+1);
   if(handHotkeysActive&&!card.disabled){
     if(card.getAttribute('aria-keyshortcuts')!==key)card.setAttribute('aria-keyshortcuts',key);
     if(card.title!==card.dataset.vrKeyTitle)card.title=card.dataset.vrKeyTitle||'';
   }else{
     card.removeAttribute('aria-keyshortcuts');
     card.removeAttribute('title');
   }
 });
 const hint=q('#vr-hint',ui);
 hint.dataset.mode=mode;
 const tag=q('#vr-hint-mode',hint),label=q('#vr-hint-text',hint);
 if(tag.textContent!==modeName[mode])tag.textContent=modeName[mode];
 if(label.textContent!==instruction)label.textContent=instruction;
 const cancel=q('#vr-cancel',ui),nativeCancel=q('#inspectBody button[data-cancel-action]');
 cancel.hidden=!nativeCancel;cancel.disabled=!nativeCancel||nativeCancel.disabled;
 q('#vr-end-turn',ui).disabled=!!q('#endTurn')?.disabled;
 updateAim();
}
// VR01U: PC numeric hotkeys delegate to the exact same one-click
// Phase21 hand path. Do not bypass legal placement, payment, targeting or
// the original local two-player privacy overlay.
function handleHandShortcut(ev){
 if(!open||busy||!ui||ev.defaultPrevented||ev.repeat||ev.ctrlKey||ev.altKey||ev.metaKey)return;
 if(ev.target?.closest?.('input,textarea,select,[contenteditable],[role="textbox"]'))return;
 if(!q('#overlay')?.classList.contains('hidden'))return;
 const key=ev.key.toLowerCase();
 if(key==='a'||key==='m'){
   // VR01Y: never reinterpret an active placement/target declaration, a
   // private handoff or a native-disabled command as a fresh action.
   if(q('#arena .slot.legal')||q('#arena .slot.attack-target'))return;
   const selected=window.MRRIntegrated?.state.scene?.selectedKey;
   const context=q('#mrr-integrated-context');
   const quick=q(key==='a'?'#mrr-quick-attack':'#mrr-quick-move');
   const original=q(key==='a'?'#inspectBody button[data-actor="attack"]':
     '#inspectBody button[data-actor="move"]');
   if(!selected||!context||context.hidden||!quick||quick.hidden||
      quick.disabled||!original||original.disabled)return;
   ev.preventDefault();ev.stopImmediatePropagation();
   quick.click(); // Exactly one existing native Phase21 command dispatch.
   schedule();return;
 }
 if(key==='c'){
   // Existing visible Phase21 cancel state is the only authorization.
   // Never invent a cancel action or intercept when native has none.
   const cancel=q('#vr-cancel',ui),original=q('#inspectBody button[data-cancel-action]');
   if(!cancel||cancel.hidden||cancel.disabled||!original||original.disabled)return;
   ev.preventDefault();ev.stopImmediatePropagation();cancel.click();
   return;
 }
 if(!/^[0-9]$/.test(ev.key))return;
 if(q('#arena .slot.legal')||q('#arena .slot.attack-target'))return;
 const index=ev.key==='0'?9:Number(ev.key)-1;
 const handCards=qa('#vr-hand .vr-card',ui),nativeCards=qa('#hand .hand-slot');
 const card=handCards[index];
 if(!card||!nativeCards[index]||handCards.length!==nativeCards.length||
    card.disabled||getComputedStyle(card).visibility==='hidden')return;
 ev.preventDefault();
 ev.stopImmediatePropagation();
 card.click();
}
function schedule(){if(!open||scheduled)return;scheduled=requestAnimationFrame(()=>{scheduled=0;refresh();});}
function cleanup(){
 observer?.disconnect();observer=null;clearInterval(interval);interval=null;
 if(scheduled)cancelAnimationFrame(scheduled);scheduled=0;
 stage?.removeEventListener('pointermove',updateAim);ui?.remove();ui=stage=null;
 handSignature='';handArtSources=[];backCount=-1;tacticalCamera='tabletop';nativeCardLabels.clear();nativeStatBadges.clear();nativeActionMarks.clear();
  nativeHpSnapshot.clear();recentHpChanges.clear();lastCombatTime=null;vrOutcomeCount=0;lastOutcome=null;outcomeNodes.length=0;outcomeHistory.length=0;
}
function closeUI(){
 // VR01AK: when a keyboard/mouse user leaves the 3D shell, keep the
 // currently visible original PC entry reachable. A programmatic close
 // while focus is outside this shell must not steal somebody else's focus.
 const returnFocus=!!(ui&&ui.contains(document.activeElement));
 for(const id of ['#mrr-quick-attack','#mrr-quick-move']){
   const control=q(id);if(!control)continue;
   control.removeAttribute('aria-keyshortcuts');
   delete control.dataset.vrShortcut;
   control.removeAttribute('title');
 }
 open=false;busy=false;cleanup();
 if(window.MRRIntegrated?.state.open)window.MRRIntegrated.close();
 document.body.classList.remove('mrr-vr-active');
 root.classList.remove('mrr-vr-playing');
 entry.disabled=false;
 if(returnFocus&&entry.isConnected&&!root.classList.contains('hidden'))
   entry.focus({preventScroll:true});
}
async function openUI(){
 if(open||busy||root.classList.contains('hidden'))return;
 busy=true;entry.disabled=true;document.body.classList.add('mrr-vr-active');
 root.classList.add('mrr-vr-playing');
 try{
  if(window.MRRIntegrated?.state.open)window.MRRIntegrated.close();
  if(!native('#mrr-integrated-open'))throw Error('Phase76 integrated entry absent');
  const start=performance.now();
  while(!window.MRRIntegrated?.state.open||window.MRRIntegrated.state.scene?.frames<4){
    if(performance.now()-start>35000)throw Error('WebGL initialization unavailable');
    await new Promise(done=>setTimeout(done,160));
  }
  stage=q('#mrr-integrated-stage');
  if(!stage)throw Error('Native battlefield stage absent');
  open=true;buildUI();refresh();
  observer=new MutationObserver(schedule);
  for(const s of ['#hand','#enemyHand','#arena','#myPortrait','#enemyPortrait','#myMana','#enemyMana','#endTurn','#overlay']){
    const target=q(s);if(target)observer.observe(target,{childList:true,characterData:true,attributes:true,subtree:true});
  }
  interval=setInterval(schedule,500);
 }catch(err){console.warn('VR01 unavailable:',err);closeUI();}
 finally{busy=false;entry.disabled=false;}
}
entry.addEventListener('click',()=>open?closeUI():openUI());
window.addEventListener('keydown',handleHandShortcut,true);
window.addEventListener('resize',()=>{if(open){
 handSignature='';backCount=-1;
 positionActiveOutcomes();schedule();
}});
window.addEventListener('beforeunload',cleanup);
window.MRRVR={open:openUI,close:closeUI,get status(){
 return {open,hand:q('#vr-hand',ui||document)?.childElementCount||0,
  enemyBacks:q('#vr-enemy-fan',ui||document)?.childElementCount||0,
  integrated:!!window.MRRIntegrated?.state.open,nativeOutcomes:vrOutcomeCount,lastOutcome,outcomeHistory:outcomeHistory.slice()};}};
})();
