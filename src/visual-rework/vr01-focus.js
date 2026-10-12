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
    const x=where.x-box.left,y=where.y-box.top;
    const target=x+width+170<box.width?x+155:x-width-155;
    frame.style.left=Math.min(box.width-width-14,Math.max(12,target))+'px';
    frame.style.top=Math.min(box.height-height-25,Math.max(94,y-height*.51))+'px';
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