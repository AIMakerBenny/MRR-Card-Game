/* VR01 in-game card focus. Reads only the existing PUBLIC 3D card texture. */
(() => {
  'use strict';
  let frame=null, picture=null, caption=null, currentKey=null,
      currentIdentity=null,currentArtData=null,currentCaption='',pointerOnCanvas=false;
  const q=(selector,parent=document)=>parent.querySelector(selector);
  function dispose(){frame?.remove();frame=picture=caption=null;currentKey=currentIdentity=currentArtData=null;currentCaption='';pointerOnCanvas=false;}
  // VR01JS: canvas pointer-exit, window deactivation and tab hiding
  // withdraw the visual inspector immediately without touching Phase21.
  // A pointermove event is not guaranteed when the mouse leaves a canvas.
  function clearFocus(){
    pointerOnCanvas=false;
    if(frame)frame.hidden=true;
    currentKey=currentIdentity=currentArtData=null;
    currentCaption='';
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
      picture.alt=data.name+' 공개 카드 확대';
      currentCaption=captionText;
    }
    currentKey=key;currentIdentity=identity;
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
    let chosen=null;
    for(const x of xs)for(const y of ys){
      let occlusion=0;
      for(const card of cardRects){
        const a=card.bounds,ix=Math.max(0,Math.min(x+width,a.right-box.left)-Math.max(x,a.left-box.left)),
          iy=Math.max(0,Math.min(y+height,a.bottom-box.top)-Math.max(y,a.top-box.top));
        occlusion+=ix*iy*(card.key===key?50:1);
      }
      // Avoid jumping the inspection dock far from the mouse when scores tie.
      const score=occlusion+Math.abs(y-targetY)*.03+
        (cx<box.width/2&&x===xs[0]?35:0)+(cx>=box.width/2&&x===xs[1]?35:0);
      if(!chosen||score<chosen.score)chosen={x,y,score,occlusion};
    }
    frame.style.left=chosen.x+'px';
    frame.style.top=chosen.y+'px';
    frame.dataset.dock=chosen.x===leftDock?'left':'right';
    frame.dataset.publicOcclusion=Math.round(chosen.occlusion).toString();
    frame.hidden=false;
  }
  document.addEventListener('pointermove',event=>{
    pointerOnCanvas=!!event.target.matches?.('#mrr-integrated-stage canvas');
    if(frame)render();
  },{passive:true});
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
  window.addEventListener('resize',render);
  // Low frequency reconciliation covers camera movement without reading private state.
  window.setInterval(render,400);
})();