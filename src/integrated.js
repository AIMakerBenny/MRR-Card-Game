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
  let view=null,stage=null,updating=false,busy=false;
  function nativeButton(selector){
    const el=document.querySelector(selector);
    if(!el||el.disabled)return false;
    el.click();view?.sync();return true;
  }
  function close(){
    const old=view,oldStage=stage;view=null;stage=null;
    root.classList.remove('mrr-integrated-playing','mrr-integrated-inspector-open','mrr-integrated-rail-open');
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
      // Two real, native control panels are available on demand. No rule actions
      // or state mutations are reimplemented in this graphics adapter.
      inspect.addEventListener('click',()=>root.classList.toggle('mrr-integrated-inspector-open'));
      rail.addEventListener('click',()=>root.classList.toggle('mrr-integrated-rail-open'));
      exit.addEventListener('click',close);
      attack.addEventListener('click',()=>nativeButton('#inspectBody button[data-actor="attack"]'));
      move.addEventListener('click',()=>nativeButton('#inspectBody button[data-actor="move"]'));
      cancel.addEventListener('click',()=>nativeButton('#inspectBody button[data-cancel-action]'));
      stage.append(vignette,heading,badge,help,command);
      root.appendChild(stage);
      root.classList.add('mrr-integrated-playing');
      document.body.classList.add('mrr-integrated-active');
      function refresh(info){
        if(updating)return;
        updating=true;
        try{
          // The native HTML board is read-only and remains the source of truth.
          const selection=!!info.selectedKey;
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
      view=window.MRRBattlefieldFactory(THREE,stage,{
        onPick:pick,onState:refresh,onHover:(key,profile)=>{
          if(key&&profile?.name)help.textContent=[profile.name,profile.kind,profile.stats].filter(Boolean).join('  ·  ');
          else help.textContent='손패 선택 → 전장 배치  ·  카드 선택 → 공격 / 이동';
        }
      });
      view.start();refresh(view.state);
      toggle.setAttribute('aria-pressed','true');toggle.textContent='3D 플레이 중';
      toggle.disabled=false;
    }catch(e){console.warn('Integrated battlefield unavailable:',e);close();}
    finally{busy=false;}
  }
  toggle.addEventListener('click',()=>view?close():open());
  window.addEventListener('resize',()=>view?.resize());
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
