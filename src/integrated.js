/* Phase 54 - first integrated gameplay stage.  This is a *view* over
   the original Phase21 engine, not another card game or an HTML modal. */
window.MRRIntegratedUIInit=function(loadThree){
  'use strict';
  const root=document.getElementById('gameScreen');
  const bar=root?.querySelector('.mcw-top-controls');
  if(!bar||document.getElementById('mrr-integrated-open'))return;
  const toggle=document.createElement('button');
  toggle.id='mrr-integrated-open';toggle.type='button';
  toggle.textContent='통합 전장';toggle.title='손패와 턴 조작이 함께 있는 3D 플레이 화면';
  bar.appendChild(toggle);
  let view=null,stage=null,updating=false,busy=false,lastRefresh=null;
  let setHandReveal=null,removeHandCapture=null,handTabElement=null;
  function nativeButton(selector){
    const el=document.querySelector(selector);
    if(!el||el.disabled)return false;
    el.click();view?.sync();return true;
  }
  function close(){
    const old=view,oldStage=stage;view=null;stage=null;lastRefresh=null;
    setHandReveal?.(false);
    removeHandCapture?.();removeHandCapture=null;setHandReveal=null;
    handTabElement?.remove();handTabElement=null;
    root.classList.remove('mrr-integrated-playing','mrr-integrated-inspector-open','mrr-integrated-rail-open','mrr-integrated-hand-open');
    document.body.classList.remove('mrr-integrated-active');
    toggle.textContent='통합 전장';toggle.setAttribute('aria-pressed','false');
    try{old?.dispose();}catch(e){console.warn('Integrated battlefield dispose:',e);}
    finally{oldStage?.remove();toggle.disabled=false;}
  }
  async function open(){
    if(busy||view||root.classList.contains('hidden'))return;
    if(window.MRRBattlefield?.state.open){window.MRRBattlefield.close();}
    busy=true;toggle.disabled=true;
    try{
      const THREE=await loadThree();
      stage=document.createElement('section');
      stage.id='mrr-integrated-stage';
      stage.setAttribute('aria-label','게임 내 통합 Three.js 전장');
      const vignette=document.createElement('div');vignette.className='mrr-integrated-vignette';
      vignette.setAttribute('aria-hidden','true');
      const heading=document.createElement('div');heading.className='mrr-integrated-heading';
      heading.textContent='MARORONG  ·  THE BATTLEFIELD';
      const badge=document.createElement('div');badge.id='mrr-integrated-status';
      badge.setAttribute('role','status');badge.textContent='공개 전장을 불러오는 중';
      const help=document.createElement('div');help.id='mrr-integrated-hint';
      help.textContent='손패 선택 → 전장 배치  ·  카드 선택 → 공격 / 이동';
      const command=document.createElement('nav');command.id='mrr-integrated-actions';
      command.setAttribute('aria-label','전장 행동');
      const control=(id,label,title)=>{const b=document.createElement('button');
        b.type='button';b.id=id;b.textContent=label;b.title=title||label;return b;};
      const attack=control('mrr-integrated-attack','⚔ 공격');
      const move=control('mrr-integrated-move','↗ 이동');
      const cancel=control('mrr-integrated-cancel','× 취소');
      const inspect=control('mrr-integrated-inspector','◇ 카드 / 능력');
      const rail=control('mrr-integrated-rail','▣ 보급 / 영역');
      const exit=control('mrr-integrated-exit','2D 보기','기존 게임 화면으로 돌아가기');
      for(const b of [attack,move,cancel,inspect,rail,exit])command.appendChild(b);
      // Phase68: an on-demand PC hand fan. Only changes CSS presentation of
      // the already existing native hand; it neither clones nor reads cards.
      const handTab=control('mrr-integrated-hand-tab','손패 펼치기','손패를 펼쳐서 읽거나 전장을 다시 볼 수 있습니다.');
      handTab.setAttribute('aria-controls','hand');
      handTab.setAttribute('aria-expanded','false');
      const nativeHandWrap=root.querySelector('.hand-wrap');
      // CSS handles the visual transition and material, while these two
      // display-only coordinates avoid legacy stylesheet-cascade conflicts.
      // Neither card markup nor the Phase21 game engine is ever changed.
      setHandReveal=(requestOpen)=>{
        const open=!!requestOpen&&innerWidth>=1024&&innerHeight>=700
          &&!!root.querySelector('#hand .hand-slot')
          &&!root.querySelector('#arena .slot.legal');
        root.classList.toggle('mrr-integrated-hand-open',open);
        handTab.setAttribute('aria-expanded',String(open));
        if(open){
          const exposed=Math.min(270,Math.max(194,innerHeight*.24));
          const nativeHeight=nativeHandWrap?.offsetHeight||336;
          nativeHandWrap?.style.setProperty('bottom',(exposed-nativeHeight).toFixed(2)+'px','important');
          handTab.style.setProperty('bottom',(exposed+12).toFixed(2)+'px');
        }else{
          nativeHandWrap?.style.removeProperty('bottom');
          handTab.style.removeProperty('bottom');
        }
      };
      handTab.addEventListener('click',()=>setHandReveal(!root.classList.contains('mrr-integrated-hand-open')));
      // A real native hand-card click immediately returns the hand below the
      // battlefield *before* original HTML delegates placement. No animation
      // or extra click is allowed to intercept a projected legal slot.
      const onNativeHandClick=e=>{
        if(e.target.closest?.('#hand .hand-slot')&&root.classList.contains('mrr-integrated-hand-open'))
          setHandReveal(false);
      };
      root.addEventListener('click',onNativeHandClick,true);
      removeHandCapture=()=>root.removeEventListener('click',onNativeHandClick,true);
      // Phase62: commands follow the selected *public* 3D card. All buttons
      // delegate to the existing original-game action buttons.
      const context=document.createElement('div');context.id='mrr-integrated-context';
      context.hidden=true;context.setAttribute('aria-label','선택 카드 명령');
      const commandFor=(id,label,selector)=>{
        const b=control(id,label);
        b.addEventListener('click',()=>nativeButton(selector));
        context.appendChild(b);return b;
      };
      const quickAttack=commandFor('mrr-quick-attack','⚔ 공격','#inspectBody button[data-actor="attack"]');
      const quickMove=commandFor('mrr-quick-move','↗ 이동','#inspectBody button[data-actor="move"]');
      const quickCancel=commandFor('mrr-quick-cancel','× 취소','#inspectBody button[data-cancel-action]');
      // Two real, native control panels are available on demand. No rule actions
      // or state mutations are reimplemented in this graphics adapter.
      inspect.addEventListener('click',()=>root.classList.toggle('mrr-integrated-inspector-open'));
      rail.addEventListener('click',()=>root.classList.toggle('mrr-integrated-rail-open'));
      exit.addEventListener('click',close);
      attack.addEventListener('click',()=>nativeButton('#inspectBody button[data-actor="attack"]'));
      move.addEventListener('click',()=>nativeButton('#inspectBody button[data-actor="move"]'));
      cancel.addEventListener('click',()=>nativeButton('#inspectBody button[data-cancel-action]'));
      stage.append(vignette,heading,badge,help,command,context);
      // Keep hand control outside stage's z-index stacking context: the
      // preserved native #handPreview is z97 and must not block fold/unfold.
      root.append(stage,handTab);
      handTabElement=handTab;
      root.classList.add('mrr-integrated-playing');
      document.body.classList.add('mrr-integrated-active');
      function refresh(info){
        if(updating)return;
        updating=true;
        try{
          // The native HTML board is read-only and remains the source of truth.
          const selection=!!info.selectedKey;
          // Legal placements retain first priority over the readable hand:
          // do not cover a target when the original engine awaits a slot.
          if(info.legalCount&&root.classList.contains('mrr-integrated-hand-open'))
            setHandReveal?.(false);
          const count=document.querySelectorAll('#hand .hand-slot').length;
          handTab.hidden=!count;
          handTab.disabled=!!info.legalCount;
          handTab.textContent=(root.classList.contains('mrr-integrated-hand-open')?'손패 접기':'손패 펼치기')+(count?' · '+count+'장':'');
          const nativeAttack=document.querySelector('#inspectBody button[data-actor="attack"]');
          const nativeMove=document.querySelector('#inspectBody button[data-actor="move"]');
          attack.disabled=!selection||!nativeAttack||nativeAttack.disabled;
          move.disabled=!selection||!nativeMove||nativeMove.disabled;
          cancel.disabled=!document.querySelector('#inspectBody button[data-cancel-action]');
          inspect.setAttribute('aria-pressed',String(root.classList.contains('mrr-integrated-inspector-open')));
          rail.setAttribute('aria-pressed',String(root.classList.contains('mrr-integrated-rail-open')));
          const suffix=info.attackTargetCount?'  ·  공격 대상 '+info.attackTargetCount:
            info.legalCount?'  ·  배치 가능 '+info.legalCount:'';
          badge.textContent='전장 '+info.publicCardCount+'장'+suffix;
          // Only show actions already supplied by the original inspector.
          const valid=!!info.selectedKey && !!view?.hasCard(info.selectedKey);
          quickAttack.hidden=!valid||attack.disabled;
          quickMove.hidden=!valid||move.disabled;
          quickCancel.hidden=!valid||cancel.disabled;
          const show=valid&&(!quickAttack.hidden||!quickMove.hidden||!quickCancel.hidden);
          context.hidden=!show;
          if(show){
            // Phase70: use the fixed native slot, not the animated card mesh.
            // Card hover/selection lifts the mesh every frame, which made the
            // nearby real attack button drift and become unclickable on slow WebGL.
            // Slot projection follows camera/resizes without following hover scale.
            const pos=view.projectSlot(info.selectedKey);
            const rect=stage.getBoundingClientRect();
            if(pos&&rect.width>0&&rect.height>0){
              // Measure the real contextual command group, not a guessed 230px.
              // Selection near an edge, smaller laptop windows and translated
              // canvas positions must never push a clickable action off-screen.
              const width=context.offsetWidth;
              const height=context.offsetHeight;
              const maxX=Math.max(12,rect.width-width-12);
              const topBound=82+height/2;
              const bottomBound=Math.max(topBound,rect.height-118-height/2);
              // VR01AC: choose a measured, card-face-aware placement for
              // the actual native action buttons. The old fixed +48 offset
              // could cover the selected card on edge seats / laptops.
              // The original integrated view retains its historic position.
              const face=document.body.classList.contains('mrr-vr-active')?
                view.projectCardBounds?.(info.selectedKey):null;
              if(face&&Number.isFinite(face.left)&&Number.isFinite(face.right)&&
                Number.isFinite(face.top)&&Number.isFinite(face.bottom)){
                const local={left:face.left-rect.left,right:face.right-rect.left,
                  top:face.top-rect.top,bottom:face.bottom-rect.top};
                const clamp=(value,min,max)=>Math.max(min,Math.min(max,value));
                const area=(a,b)=>Math.max(0,Math.min(a.right,b.right)-
                  Math.max(a.left,b.left))*Math.max(0,Math.min(a.bottom,b.bottom)-
                  Math.max(a.top,b.top));
                const pad=8,shield={left:local.left-pad,right:local.right+pad,
                  top:local.top-pad,bottom:local.bottom+pad};
                const center=(local.top+local.bottom)/2;
                const mx=(local.left+local.right-width)/2;
                const candidates=[
                  {x:local.right+12,y:center,priority:0},
                  {x:local.left-width-12,y:center,priority:4},
                  {x:mx,y:local.top-height/2-12,priority:8},
                  {x:mx,y:local.bottom+height/2+12,priority:12}
                ];
                const sideActions=document.querySelector('#mrr-integrated-actions');
                const rightHUD=sideActions?.getBoundingClientRect();
                const hud=rightHUD?{left:rightHUD.left-rect.left-5,
                  right:rightHUD.right-rect.left+5,
                  top:rightHUD.top-rect.top-5,
                  bottom:rightHUD.bottom-rect.top+5}:null;
                const scored=candidates.map(c=>{
                  const x=clamp(c.x,12,maxX),y=clamp(c.y,topBound,bottomBound);
                  const box={left:x,top:y-height/2,right:x+width,bottom:y+height/2};
                  return {x,y,score:area(box,shield)*120+
                    (hud?area(box,hud)*24:0)+
                    Math.abs(c.x-x)*2+Math.abs(c.y-y)*2+c.priority};
                }).sort((a,b)=>a.score-b.score);
                context.style.left=scored[0].x.toFixed(1)+'px';
                context.style.top=scored[0].y.toFixed(1)+'px';
              }else{
                context.style.left=Math.max(12,Math.min(maxX,pos.x-rect.left+48))+'px';
                context.style.top=Math.max(topBound,Math.min(bottomBound,pos.y-rect.top-48))+'px';
              }
            }else context.hidden=true;
          }
        }finally{updating=false;}
      }
      function pick(key){
        const node=document.querySelector('#arena [data-slot="'+key+'"]');
        if(!node||!view||!document.querySelector('#overlay.hidden'))return;
        if(!node.querySelector('.board-card')&&!node.classList.contains('legal')&&!node.classList.contains('attack-target'))return;
        if(node.classList.contains('attack-target')&&view.state.selectedKey)
          view.stageAttack(view.state.selectedKey,key);
        node.click(); // Exactly one real engine click. No fake battle resolution.
        view.sync();view.refreshHover(key);
      }
      lastRefresh=refresh;
      view=window.MRRBattlefieldFactory(THREE,stage,{
        onPick:pick,onState:refresh,onHover:(key,profile)=>{
          if(key&&profile?.name)help.textContent=[profile.name,profile.kind,profile.stats].filter(Boolean).join('  ·  ');
          else help.textContent='손패 선택 → 전장 배치  ·  카드 선택 → 공격 / 이동';
        }
      });
      view.setCameraPreset('tabletop'); // Higher desktop angle, room for hand and hero HUD.
      view.start();refresh(view.state);
      toggle.setAttribute('aria-pressed','true');toggle.textContent='3D 플레이 중';
      toggle.disabled=false;
    }catch(e){console.warn('Integrated battlefield unavailable:',e);close();}
    finally{busy=false;}
  }
  toggle.addEventListener('click',()=>view?close():open());
  window.addEventListener('resize',()=>{
    view?.resize();
    if(view&&root.classList.contains('mrr-integrated-hand-open'))
      setHandReveal?.(true);
    if(view&&lastRefresh)lastRefresh(view.state);
  });
  document.addEventListener('visibilitychange',()=>{
    if(!view)return;
    if(document.hidden)view.stop();else view.start();
  });
  window.addEventListener('beforeunload',()=>view?.dispose());
  // Keyboard Escape continues to belong to the original engine and its action cancellation.
  window.MRRIntegrated={get state(){return {open:!!view,scene:view?.state||null,
    nativeHandCount:document.querySelectorAll('#hand .hand-slot').length,
    nativeEndTurn:!!document.querySelector('#endTurn')};},get scene(){return view;},close};
};
