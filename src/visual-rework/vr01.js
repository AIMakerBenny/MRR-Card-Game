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
let open=false,busy=false,ui=null,stage=null,observer=null,interval=null,scheduled=0,handSignature='',backCount=-1;
let tacticalCamera='tabletop';
const nativeCardLabels=new Map();
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
        tacticalCamera=views[next];q('#vr-camera',ui).textContent=labels[next];schedule();
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
  const piles=el('div','vr-pile-display');
  for(const word of ['DECK','GRAVE','EXILE']){const token=button('vr-token-'+word.toLowerCase(),word,()=>native('#mrr-integrated-rail'));token.className='vr-pile';piles.append(token);}
  ui.append(piles);
  const footer=el('div','vr-footer');
  const heroAlly=el('div','vr-hero vr-ally');heroAlly.id='vr-ally';
  heroAlly.append(el('div','vr-portrait','M'),el('div','vr-profile'),el('div','vr-hp'));
  footer.append(heroAlly,button('vr-end-turn','턴 종료',()=>native('#endTurn')));ui.append(footer);
  const hand=el('div','vr-hand');hand.id='vr-hand';hand.setAttribute('aria-label','내 실제 손패');ui.append(hand);
  const hint=el('div','vr-hint','손패를 선택하여 전장에 배치하세요');hint.id='vr-hint';ui.append(hint);
  const aim=document.createElementNS('http://www.w3.org/2000/svg','svg');
  aim.id='vr-aim';aim.setAttribute('preserveAspectRatio','none');
  aim.innerHTML='<defs><marker id="vr-arrow" markerWidth="7" markerHeight="7" refX="8" refY="5" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10Z" fill="#f0b982"/></marker></defs><path id="vr-aim-line" fill="none" stroke="#f0b982" stroke-width="3" marker-end="url(#vr-arrow)" />';
  ui.append(aim);
  stage.append(ui);
  stage.addEventListener('pointermove',updateAim);
}
function updateAim(event){
  if(!open||!ui)return;
  const path=q('#vr-aim-line',ui),state=window.MRRIntegrated?.state.scene;
  if(!state?.selectedKey||!state.attackTargetCount){path.setAttribute('d','');return;}
  const start=window.MRRIntegrated.scene?.projectCard(state.selectedKey),box=stage.getBoundingClientRect();
  if(!start)return;
  const sx=start.x-box.left,sy=start.y-box.top,ex=event.clientX-box.left,ey=event.clientY-box.top;
  const cy=Math.min(sy,ey)-65;
  path.setAttribute('d','M'+sx+' '+sy+' Q'+((sx+ex)/2)+' '+cy+' '+ex+' '+ey);
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
  const signature=JSON.stringify(hand);if(handSignature===signature)return;
  handSignature=signature;const fan=q('#vr-hand',ui);fan.replaceChildren();
  const n=hand.length,step=Math.min(innerWidth<1500?72:innerWidth<2200?91:108,
    Math.max(43,(innerWidth-420)/Math.max(1,n)));
  for(const d of hand){
    const card=el('button','vr-card');card.type='button';
    card.setAttribute('aria-label',d.name+' 손패 선택');card.dataset.index=String(d.i);
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
    plaque.classList.toggle('vr-enemy-unit',key.startsWith('1:'));
    plaque.classList.toggle('vr-selected-unit',key===selected);
    plaque.classList.toggle('vr-target-unit',slot.classList.contains('attack-target'));
    const gap=Math.min(Infinity,...projected.filter(other=>other.key!==key&&other.lane===lane)
      .map(other=>Math.abs(other.cx-cx)));
    const wide=bounds.width<1500?117:166;
    // The visible label cannot be wider than the actual gap in its 3D row.
    const desired=Number.isFinite(gap)?Math.min(wide,gap-10):wide;
    const sizes=[Math.max(76,desired),72,58];
    const marginX=bounds.width<1500?61:72;
    const yMin=100,yMax=bounds.height-94;
    let solution=null,compact=false;
    for(const width of sizes){
      const isCompact=width<98,height=isCompact?25:41;
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
}
function refresh(){
 if(!open||!ui)return;
 updateHand();updateBacks();updatePublicPlaques();
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
 const placing=qa('#arena .slot.legal').length>0;
 const target=qa('#arena .slot.attack-target').length>0;
 ui.classList.toggle('vr-placing',placing||target);
 q('#vr-hint',ui).textContent=target?'공격할 대상을 선택하세요':
   placing?'전장의 합법 위치를 선택하세요':
   window.MRRIntegrated?.state.scene?.selectedKey?'선택 카드의 명령을 실행하세요':'손패를 선택하여 배치하세요';
 q('#vr-end-turn',ui).disabled=!!q('#endTurn')?.disabled;
 if(!target)q('#vr-aim-line',ui)?.setAttribute('d','');
}
function schedule(){if(!open||scheduled)return;scheduled=requestAnimationFrame(()=>{scheduled=0;refresh();});}
function cleanup(){
 observer?.disconnect();observer=null;clearInterval(interval);interval=null;
 if(scheduled)cancelAnimationFrame(scheduled);scheduled=0;
 stage?.removeEventListener('pointermove',updateAim);ui?.remove();ui=stage=null;
 handSignature='';backCount=-1;tacticalCamera='tabletop';nativeCardLabels.clear();
}
function closeUI(){
 open=false;busy=false;cleanup();
 if(window.MRRIntegrated?.state.open)window.MRRIntegrated.close();
 document.body.classList.remove('mrr-vr-active');
 root.classList.remove('mrr-vr-playing');
 entry.disabled=false;
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
  for(const s of ['#hand','#enemyHand','#arena','#myPortrait','#enemyPortrait','#myMana','#enemyMana','#endTurn']){
    const target=q(s);if(target)observer.observe(target,{childList:true,characterData:true,attributes:true,subtree:true});
  }
  interval=setInterval(schedule,500);
 }catch(err){console.warn('VR01 unavailable:',err);closeUI();}
 finally{busy=false;entry.disabled=false;}
}
entry.addEventListener('click',()=>open?closeUI():openUI());
window.addEventListener('resize',()=>{if(open){handSignature='';backCount=-1;schedule();}});
window.addEventListener('beforeunload',cleanup);
window.MRRVR={open:openUI,close:closeUI,get status(){
 return {open,hand:q('#vr-hand',ui||document)?.childElementCount||0,
  enemyBacks:q('#vr-enemy-fan',ui||document)?.childElementCount||0,
  integrated:!!window.MRRIntegrated?.state.open};}};
})();