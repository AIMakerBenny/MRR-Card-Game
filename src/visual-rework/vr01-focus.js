/* VR01 in-game card focus. Reads only the existing PUBLIC 3D card texture. */
(() => {
  'use strict';
  let frame=null, picture=null, caption=null, currentKey=null,
      currentIdentity=null,currentArtData=null,currentCaption='',pointerOnCanvas=false;
  let arenaObserver=null,observedArena=null,focusFrame=0;
  let passObserver=null,observedPass=null;
  let panelObserver=null,observedGameScreen=null;
  const q=(selector,parent=document)=>parent.querySelector(selector);
  function dispose(){
    arenaObserver?.disconnect();arenaObserver=observedArena=null;
    passObserver?.disconnect();passObserver=observedPass=null;
    panelObserver?.disconnect();panelObserver=observedGameScreen=null;
    if(focusFrame)cancelAnimationFrame(focusFrame);
    focusFrame=0;
    frame?.remove();frame=picture=caption=null;
    currentKey=currentIdentity=currentArtData=null;
    currentCaption='';pointerOnCanvas=false;
  }
  // VR01JS: canvas pointer-exit, window deactivation and tab hiding
  // withdraw the visual inspector immediately without touching Phase21.
  // A pointermove event is not guaranteed when the mouse leaves a canvas.
  function clearFocus(){
    pointerOnCanvas=false;
    if(focusFrame)cancelAnimationFrame(focusFrame);
    focusFrame=0;
    if(frame)frame.hidden=true;
    currentKey=currentIdentity=currentArtData=null;
    currentCaption='';
  }
  // VR01KB: coalesce high-frequency pointer moves, native mutations and
  // camera wheel events into at most one expensive 3D projection per frame.
  function scheduleFocus(){
    if(!pointerOnCanvas||focusFrame)return;
    focusFrame=requestAnimationFrame(()=>{
      focusFrame=0;
      if(pointerOnCanvas)render();
    });
  }
  // VR01JW: the original Phase21 PUBLIC arena is the only observed DOM.
  // Coalesce its HP, status and card replacements to one inspector refresh
  // per browser frame; the 400ms camera reconciliation remains a fallback.
  function watchPublicArena(){
    const arena=q('#arena');
    if(arena===observedArena)return;
    arenaObserver?.disconnect();arenaObserver=observedArena=null;
    if(!arena)return;
    observedArena=arena;
    arenaObserver=new MutationObserver(scheduleFocus);
    arenaObserver.observe(arena,{
      subtree:true,childList:true,characterData:true,
      attributes:true,
      attributeFilter:['class','style','data-mrr-public-card-id']
    });
  }
  // VR01JX: a real Phase21 handoff overlay instantly hides public
  // inspection, even when the cursor never moves. The observer watches
  // only the native overlay visibility, never any private hand contents.
  function watchNativeOverlay(){
    const overlay=q('#overlay');
    if(overlay===observedPass)return;
    passObserver?.disconnect();passObserver=observedPass=null;
    if(!overlay)return;
    observedPass=overlay;
    passObserver=new MutationObserver(()=>{
      if(!overlay.classList.contains('hidden'))clearFocus();
    });
    passObserver.observe(overlay,{attributes:true,attributeFilter:['class']});
  }
  // VR01KA: a real Phase21 inspector/deck panel has priority over
  // this decorative hover magnifier. It may open by keyboard without a
  // canvas pointerout event, so track the ORIGINAL panel classes.
  function nativePanelOpen(){
    const game=q('#gameScreen');
    return !!game&&(game.classList.contains('mrr-integrated-inspector-open')||
      game.classList.contains('mrr-integrated-rail-open'));
  }
  function watchNativePanels(){
    const game=q('#gameScreen');
    if(game===observedGameScreen)return;
    panelObserver?.disconnect();panelObserver=observedGameScreen=null;
    if(!game)return;
    observedGameScreen=game;
    panelObserver=new MutationObserver(()=>{
      if(nativePanelOpen())clearFocus();
    });
    panelObserver.observe(game,{attributes:true,attributeFilter:['class']});
  }
  function create(){
    const shell=q('#mrr-vr-shell');if(!shell)return;
    frame=document.createElement('aside');frame.id='mrr-vr-card-focus';
    frame.setAttribute('aria-label','공개 전장 카드 확대');
    picture=document.createElement('img');picture.alt='';picture.draggable=false;
    caption=document.createElement('div');caption.className='vr-card-focus-caption';
    frame.append(picture,caption);shell.append(frame);
  }
  function render(){
    if(!window.MRRVR?.status.open){if(frame)dispose();return;}
    if(!frame)create();
    if(!frame)return;
    watchPublicArena();
    watchNativeOverlay();
    watchNativePanels();
    const nativeCover=q('#overlay');
    if(document.hidden||nativePanelOpen()||
       (nativeCover&&!nativeCover.classList.contains('hidden'))){
      clearFocus();return;
    }
    const scene=window.MRRIntegrated?.scene;
    const key=pointerOnCanvas?scene?.state.hoveredKey:null;
    if(!key||!scene?.hasCard(key)){frame.hidden=true;currentKey=currentIdentity=currentArtData=null;currentCaption='';return;}
    const where=scene.projectCard(key),box=q('#mrr-integrated-stage')?.getBoundingClientRect();
    if(!where||!box||!Number.isFinite(where.x)||!Number.isFinite(where.y)){
      frame.hidden=true;currentKey=currentIdentity=currentArtData=null;currentCaption='';return;
    }
    // VR01JP: a Phase21 native slot can be reused by a different PUBLIC
    // card while the mouse stays still. The old magnifier must never
    // preserve the departed occupant's card art at the reused key.
    const data=scene.getCardPreview(key);
    if(!data?.artData){frame.hidden=true;currentKey=currentIdentity=currentArtData=null;currentCaption='';return;}
    const identity=data.publicId?
      'id:'+data.publicId:'name:'+data.name;
    // VR01JQ: a card with the SAME native ID can receive visible HP/stat
    // updates and a fresh Three.js face texture without changing slots.
    // Refresh only the changed artwork or text, avoiding repeat uploads.
    const identityChanged=currentKey!==key||currentIdentity!==identity;
    // VR01JR: the small in-game inspector now reads the same
    // already PUBLIC card details as the Phase55 inspector.
    // VR01JV: mirror only the HP bar percentage and status CHIP
    // already rendered on this native PUBLIC card. Neither one is
    // a computed game HP value or a new action entitlement.
    const captionText=JSON.stringify([
      data.name,data.kind,data.cost,data.stats,data.sigil,
      data.hpBarPercent,data.statusChip
    ]);
    if(identityChanged||currentArtData!==data.artData){
      picture.src=data.artData;
      currentArtData=data.artData;
    }
    if(identityChanged||currentCaption!==captionText){
      const title=document.createElement('strong');
      title.textContent=data.name;
      const detail=document.createElement('span');
      detail.textContent=[
        data.kind,data.cost?'비용 '+data.cost:'',data.stats
      ].filter(Boolean).join(' · ');
      caption.replaceChildren(title,detail);
      if(data.sigil){
        const sigil=document.createElement('span');
        sigil.className='vr-focus-sigil';
        sigil.textContent=data.sigil;
        caption.append(sigil);
      }
      const publicState=[
        Number.isFinite(data.hpBarPercent)?
          '공개 HP 게이지 '+Math.round(data.hpBarPercent)+'%':'',
        data.statusChip||''
      ].filter(Boolean).join(' · ');
      if(publicState){
        const state=document.createElement('span');
        state.className='vr-focus-public-state';
        state.textContent=publicState;
        caption.append(state);
      }
      // VR01KD: an exact copy of the visible Phase21 public HP-bar
      // fill percentage. No guessed max HP, damage or gameplay state.
      if(Number.isFinite(data.hpBarPercent)){
        const percent=Math.max(0,Math.min(100,data.hpBarPercent));
        const meter=document.createElement('span');
        meter.className='vr-focus-hp-meter';
        meter.setAttribute('aria-hidden','true');
        meter.dataset.level=percent<=33?'low':percent<=66?'medium':'high';
        const fill=document.createElement('span');
        fill.className='vr-focus-hp-meter-fill';
        fill.style.width=percent+'%';
        meter.append(fill);caption.append(meter);
      }
      picture.alt=data.name+' 공개 카드 확대';
      currentCaption=captionText;
    }
    currentKey=key;currentIdentity=identity;
    // VR01JY: present the TRUE Phase21 native selected/attack class
    // on the inspected public card, never inferred legality.
    // The outline itself is decorative and never intercepts clicks.
    const nativeSlot=q('#arena [data-slot="'+key+'"]');
    frame.dataset.nativeRole=nativeSlot?.classList.contains('attack-target')?
      'target':nativeSlot?.classList.contains('selected-slot')?
      'selected':'public';
    // VR01JT: a hidden display:none frame always measures zero.
    // Show it for DOM measurement within this same frame, then
    // choose the dock from its REAL current artwork/caption height.
    frame.hidden=false;
    const width=frame.offsetWidth||260,height=frame.offsetHeight||375;
    const cx=where.x-box.left,cy=where.y-box.top;
    // VR01F: choose a side inspection dock with the least overlap against
    // actual PUBLIC face projections. No game/hidden data or hand reads.
    const cardRects=[...document.querySelectorAll('#arena [data-slot] .board-card .card-ui')]
      .map(card=>card.closest('[data-slot]')?.getAttribute('data-slot'))
      .filter(Boolean).map(slot=>({key:slot,bounds:scene.projectCardBounds?.(slot)}))
      .filter(p=>p.bounds);
    // VR01JT: short PC viewports and long public sigils may leave
    // less usable height than the old fixed 375px estimate.
    const margin=12;
    const yEnd=Math.max(margin,box.height-height-88);
    const yMin=Math.min(box.height<830?85:100,yEnd);
    const yMax=Math.max(yMin,yEnd);
    const targetY=Math.max(yMin,Math.min(yMax,cy-height/2));
    const leftDock=margin,rightDock=Math.max(margin,box.width-width-margin);
    const xs=[leftDock,rightDock],ys=[targetY,yMin,yMax];
    // VR01JZ: real PC controls and raised hand cards must remain
    // readable when a public card is magnified. Sample only current
    // DOM rectangles, with no extra pointer surface or game commands.
    // VR01KC: the transparent full-width header/footer wrappers do
    // not block the 3D table. Score ONLY their actual visible controls,
    // so a safe dock can stay near the hovered public unit.
    const hudRects=[
      ...document.querySelectorAll(
        '#mrr-vr-shell .vr-header .vr-logo,'+
        '#mrr-vr-shell .vr-header .vr-hero,'+
        '#mrr-vr-shell .vr-header .vr-tools,'+
        '#mrr-vr-shell .vr-footer .vr-hero,'+
        '#mrr-vr-shell .vr-footer #vr-end-turn,'+
        '#mrr-vr-shell .vr-pile-display,'+
        '#mrr-vr-shell #vr-hint,'+
        '#mrr-vr-shell .vr-card:is(:hover,:focus-visible,.raised),'+
        '#mrr-integrated-context')
    ].filter(node=>node.getClientRects().length&&
      !node.closest('[hidden]')&&
      getComputedStyle(node).visibility!=='hidden').map(node=>{
      const r=node.getBoundingClientRect();
      return {x:r.left-box.left,y:r.top-box.top,w:r.width,h:r.height};
    }).filter(r=>r.w>0&&r.h>0);
    let chosen=null;
    for(const x of xs)for(const y of ys){
      let occlusion=0;
      for(const card of cardRects){
        const a=card.bounds,ix=Math.max(0,Math.min(x+width,a.right-box.left)-Math.max(x,a.left-box.left)),
          iy=Math.max(0,Math.min(y+height,a.bottom-box.top)-Math.max(y,a.top-box.top));
        occlusion+=ix*iy*(card.key===key?50:1);
      }
      // VR01JZ: penalize overlap with actual hero controls, action
      // buttons and raised hand cards. Existing 50x source-card
      // protection remains the primary visibility requirement.
      let hudOcclusion=0;
      for(const r of hudRects){
        const iw=Math.max(0,Math.min(x+width,r.x+r.w)-Math.max(x,r.x));
        const ih=Math.max(0,Math.min(y+height,r.y+r.h)-Math.max(y,r.y));
        hudOcclusion+=iw*ih;
      }
      const score=occlusion+hudOcclusion*2.2+Math.abs(y-targetY)*.03+
        (cx<box.width/2&&x===xs[0]?35:0)+(cx>=box.width/2&&x===xs[1]?35:0);
      if(!chosen||score<chosen.score)
        chosen={x,y,score,occlusion,hudOcclusion};
    }
    frame.style.left=chosen.x+'px';
    frame.style.top=chosen.y+'px';
    frame.dataset.dock=chosen.x===leftDock?'left':'right';
    frame.dataset.publicOcclusion=Math.round(chosen.occlusion).toString();
    frame.dataset.hudOcclusion=Math.round(chosen.hudOcclusion).toString();
    frame.hidden=false;
  }
  document.addEventListener('pointermove',event=>{
    const onCanvas=!!event.target.matches?.('#mrr-integrated-stage canvas');
    if(!onCanvas){if(pointerOnCanvas)clearFocus();return;}
    pointerOnCanvas=true;
    scheduleFocus();
  },{passive:true});
  // The authoritative Phase76 camera controls run first. Follow their
  // wheel/preset changes with a pure visual inspection projection.
  document.addEventListener('wheel',event=>{
    if(event.target.matches?.('#mrr-integrated-stage canvas'))scheduleFocus();
  },{passive:true});
  document.addEventListener('click',event=>{
    if(event.target.closest?.('#vr-camera'))scheduleFocus();
  });
  document.addEventListener('pointerout',event=>{
    if(event.target.matches?.('#mrr-integrated-stage canvas')){
      // Other canvases or overlays must never retain a stale card hover.
      clearFocus();
    }
  },{passive:true});
  window.addEventListener('blur',clearFocus);
  document.addEventListener('visibilitychange',()=>{
    if(document.hidden)clearFocus();
  });
  window.addEventListener('resize',scheduleFocus);
  // Low frequency reconciliation covers camera movement without reading private state.
  window.setInterval(render,400);
})();