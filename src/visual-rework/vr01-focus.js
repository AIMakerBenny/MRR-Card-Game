/* VR01 in-game card focus. Reads only the existing PUBLIC 3D card texture. */
(() => {
  'use strict';
  let frame=null, picture=null, caption=null, currentKey=null, pointerOnCanvas=false;
  const q=(selector,parent=document)=>parent.querySelector(selector);
  function dispose(){frame?.remove();frame=picture=caption=null;currentKey=null;pointerOnCanvas=false;}
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
    if(!key||!scene?.hasCard(key)){frame.hidden=true;currentKey=null;return;}
    const where=scene.projectCard(key),box=q('#mrr-integrated-stage')?.getBoundingClientRect();
    if(!where||!box||!Number.isFinite(where.x)||!Number.isFinite(where.y)){
      frame.hidden=true;currentKey=null;return;
    }
    if(currentKey!==key){
      const data=scene.getCardPreview(key);
      if(!data?.artData){frame.hidden=true;return;}
      currentKey=key;picture.src=data.artData;
      caption.textContent=[data.name,data.stats].filter(Boolean).join('  |  ');
    }
    const width=frame.offsetWidth||260,height=frame.offsetHeight||375;
    const cx=where.x-box.left,cy=where.y-box.top;
    // VR01F: choose a side inspection dock with the least overlap against
    // actual PUBLIC face projections. No game/hidden data or hand reads.
    const cardRects=[...document.querySelectorAll('#arena [data-slot] .board-card .card-ui')]
      .map(card=>card.closest('[data-slot]')?.getAttribute('data-slot'))
      .filter(Boolean).map(slot=>({key:slot,bounds:scene.projectCardBounds?.(slot)}))
      .filter(p=>p.bounds);
    const yMin=box.height<830?85:100,yMax=Math.max(yMin,box.height-height-88);
    const targetY=Math.max(yMin,Math.min(yMax,cy-height/2));
    const xs=[12,box.width-width-12],ys=[targetY,yMin,yMax];
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
    frame.dataset.dock=chosen.x===xs[0]?'left':'right';
    frame.dataset.publicOcclusion=Math.round(chosen.occlusion).toString();
    frame.hidden=false;
  }
  document.addEventListener('pointermove',event=>{
    pointerOnCanvas=!!event.target.matches?.('#mrr-integrated-stage canvas');
    if(frame)render();
  },{passive:true});
  window.addEventListener('resize',render);
  // Low frequency reconciliation covers camera movement without reading private state.
  window.setInterval(render,400);
})();