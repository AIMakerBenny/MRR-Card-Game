/* MARORONG CARD WAR - Phase 01 graphics adapter.
   UI-extension only: no writes to G, CARDS, rules, saves or AI. */
(() => {
  'use strict';
  const root = document.querySelector('#gameScreen');
  const bar = document.querySelector('.mcw-top-controls');
  if (!root || !bar || document.getElementById('mcw3d-toggle')) return;
  const host = document.createElement('div');
  host.id='mcw3d-canvas-host';host.setAttribute('aria-hidden','true');
  root.appendChild(host);
  const button = document.createElement('button');
  button.id='mcw3d-toggle';button.type='button';button.textContent='3D 전장';
  button.title='3D 그래픽 켜기 또는 기존 2D로 돌아가기';
  button.setAttribute('aria-pressed','false');
  bar.insertBefore(button, bar.firstChild);
  const status = document.createElement('div');status.id='mcw3d-status';status.setAttribute('role','status');root.appendChild(status);
  let sceneApi = null, busy=false, enabled=false;
  function note(message){status.textContent=message;status.classList.add('active');}
  function clearNote(){status.classList.remove('active');status.textContent='';}
  function setEnabled(flag, mode){
    enabled=flag;document.body.classList.toggle('mcw-three-ready',flag&&mode==='webgl');
    document.body.classList.toggle('mcw-depth-fallback',flag&&mode==='css');
    button.setAttribute('aria-pressed',String(flag));
    button.textContent=!flag?'3D 전장':mode==='webgl'?'3D 켜짐':'입체 모드';
    if(!flag){sceneApi?.stop();clearNote();} 
  }
  async function loadThree(){
    // CDN loading is isolated. If unavailable, legacy DOM game stays usable.
    // A CI build can inject a local vendor module for fully offline distribution.
    const sources = ['./vendor/three.module.js',
      'https://cdn.jsdelivr.net/npm/three@0.160.1/build/three.module.js',
      'https://unpkg.com/three@0.160.1/build/three.module.js'];
    for (const url of sources){
      try {return await import(url);}catch(_){ /* try the next authorized source */ }
    }
    throw new Error('Three.js module unavailable');
  }
  button.addEventListener('click', async () => {
    if (busy)return;
    if(enabled){setEnabled(false);return;}
    busy=true;button.disabled=true;note('Three.js 3D 전장을 준비하고 있습니다.');
    try{
      if(!sceneApi){
        const THREE=await loadThree();
        // Scene module exported from appended inline script to avoid file:// access requirements.
        sceneApi=window.MCW3DSceneFactory(THREE,host);
      }
      sceneApi.start();setEnabled(true,'webgl');clearNote();
    }catch(err){
      setEnabled(true,'css');note('Three.js 로드 불가 - 기존 규칙을 유지하는 CSS 입체 모드입니다. 인터넷 연결과 WebGL 환경을 확인하세요.');
      console.warn('MCW3D graphics fallback:',String(err));
    }finally{busy=false;button.disabled=false;}
  });

  // Phase37: explicit cinematic viewer, isolated from all gameplay controls.
  const cinemaButton=document.createElement('button');
  cinemaButton.id='mcw-cinema-open';cinemaButton.type='button';cinemaButton.textContent='3D 카드 감상';
  cinemaButton.title='원근감이 있는 독립적인 3D 카드 뷰어';
  bar.insertBefore(cinemaButton,button.nextSibling);
  let cinemaModal=null,cinemaScene=null,cinemaBusy=false,cinemaCards=[],cinemaIndex=0;
  // Only public face-up field cards; never read either player's hidden hand,
  // deck, game engine internals or stored state.
  function publicFieldCards(){
    return Array.from(document.querySelectorAll('#arena .slot:has(.board-card)')).map(slot=>{
      const node=slot.querySelector('.board-card .card-ui');
      if(!node||node.getBoundingClientRect().width<10)return null;
      const value=q=>node.querySelector(q)?.textContent?.trim()||'';
      const artWell=node.querySelector('.art-well');
      const artStyle=artWell?.style.getPropertyValue('--mcw-procedural-paint')||'';
      const match=artStyle.match(/data:image\/png;base64,[A-Za-z0-9+/=]+/);
      return {name:value('.card-name')||'이름 없는 카드',kind:value('.card-kind')||node.className,
        cost:value('.cost-bubble'),stats:value('.card-stats'),artData:match?match[0]:null,
        selected:slot.classList.contains('selected-slot')};
    }).filter(Boolean);
  }
  function modalClose(){
    // Clear the modal state before graphics disposal. GPU context errors or
    // late texture callbacks must never strand the user behind an overlay.
    const staleScene=cinemaScene,staleModal=cinemaModal;
    cinemaScene=null;cinemaModal=null;
    cinemaCards=[];cinemaIndex=0;cinemaButton.disabled=false;
    try{staleScene?.dispose();}
    catch(err){console.warn('Cinematic renderer cleanup failed:',err);}
    finally{
      staleModal?.remove();
      if(document.contains(cinemaButton))cinemaButton.focus({preventScroll:true});
    }
  }
  cinemaButton.addEventListener('click',async()=>{
    if(cinemaBusy||cinemaModal)return;
    cinemaBusy=true;cinemaButton.disabled=true;
    try{
      const THREE=await loadThree();
      const overlay=document.createElement('div');overlay.id='mcw-cinema-view';overlay.className='mcw-active';
      const dialog=document.createElement('section');dialog.id='mcw-cinema-dialog';
      dialog.setAttribute('role','dialog');dialog.setAttribute('aria-modal','true');
      dialog.setAttribute('aria-label','3D 카드 시네마틱');
      const header=document.createElement('div');header.id='mcw-cinema-header';
      const title=document.createElement('span');title.textContent='MARORONG CARD WAR - CINEMATIC 3D';
      const controls=document.createElement('nav');controls.id='mcw-cinema-controls';
      const prev=document.createElement('button');prev.id='mcw-cinema-prev';prev.type='button';
      prev.textContent='이전 카드';
      const current=document.createElement('span');current.id='mcw-cinema-current';
      const next=document.createElement('button');next.id='mcw-cinema-next';next.type='button';
      next.textContent='다음 카드';
      const flip=document.createElement('button');flip.id='mcw-cinema-flip';flip.type='button';
      flip.textContent='카드 뒤집기';flip.setAttribute('aria-pressed','false');
      const camReset=document.createElement('button');camReset.id='mcw-cinema-reset-camera';
      camReset.type='button';camReset.textContent='시점 초기화';
      const summon=document.createElement('button');summon.id='mcw-cinema-summon';
      summon.type='button';summon.textContent='소환 연출';
      controls.append(prev,current,next,flip,camReset,summon);
      const close=document.createElement('button');close.id='mcw-cinema-close';close.type='button';close.textContent='닫기';
      close.addEventListener('click',modalClose);header.append(title,controls,close);
      const stage=document.createElement('div');stage.id='mcw-cinema-stage';
      const footer=document.createElement('div');footer.id='mcw-cinema-footer';
      footer.textContent='실제 원근 카메라와 조명을 사용하는 시각 품질 시제품입니다. 게임 규칙은 원본 그대로 유지됩니다.';
      dialog.append(header,stage,footer);overlay.appendChild(dialog);
      document.body.appendChild(overlay);
      overlay.addEventListener('click',event=>{if(event.target===overlay)modalClose();});
      cinemaModal=overlay;
      // Every modal owns and releases exactly one renderer.
      cinemaScene=window.MRRCinemaFactory(THREE,stage);
      cinemaCards=publicFieldCards();
      cinemaIndex=Math.max(0,cinemaCards.findIndex(card=>card.selected));
      function show(){
        cinemaScene.setView('front');flip.setAttribute('aria-pressed','false');flip.textContent='카드 뒤집기';
        const p=cinemaCards[cinemaIndex]||{name:'MARORONG',kind:'CARD WAR',cost:'',stats:''};
        cinemaScene.setCard(p);
        current.textContent=cinemaCards.length?
          (cinemaIndex+1)+' / '+cinemaCards.length+' - '+p.name:'미배치 - 시연 카드';
        prev.disabled=next.disabled=cinemaCards.length<2;
        footer.textContent=cinemaCards.length?
          '현재 공개 카드: '+p.name+' | '+p.kind+' | 비용 '+(p.cost||'0')+' | '+String(p.stats||'공개 카드').replace(/([가-힣]+)(\d+)/g,'$1 $2 '):
          '전장에 카드가 없으므로 시연 카드입니다. 기존 게임 기능은 변경되지 않습니다.';
      }
      prev.addEventListener('click',()=>{cinemaIndex=(cinemaIndex+cinemaCards.length-1)%cinemaCards.length;show();});
      next.addEventListener('click',()=>{cinemaIndex=(cinemaIndex+1)%cinemaCards.length;show();});
      camReset.addEventListener('click',()=>cinemaScene.resetCamera());
      summon.addEventListener('click',()=>cinemaScene.previewSummon());
      flip.addEventListener('click',()=>{
        const nextView=cinemaScene.state.viewMode==='front'?'back':'front';
        cinemaScene.setView(nextView);flip.setAttribute('aria-pressed',String(nextView==='back'));
        flip.textContent=nextView==='back'?'카드 앞면':'카드 뒤집기';
      });
      show();cinemaScene.start();close.focus();
    }catch(err){
      console.warn('Cinematic 3D unavailable',err);modalClose();
    }finally{cinemaBusy=false;}
  });
  // Phase21 captures Escape keydown first at window level and stops its
  // propagation. The modal therefore closes on keyup, without modifying or
  // overriding the original game's shortcut handling.
  window.addEventListener('keyup',event=>{
    if(event.key==='Escape'&&cinemaModal){
      event.preventDefault();event.stopImmediatePropagation();modalClose();
    }
  },true);
  window.addEventListener('resize',()=>{if(cinemaModal)cinemaScene?.resize();});
  document.addEventListener('visibilitychange',()=>{
    if(!cinemaModal||!cinemaScene)return;
    if(document.hidden)cinemaScene.stop();else cinemaScene.start();
  });
  window.addEventListener('beforeunload',()=>cinemaScene?.dispose());
  window.MRRCinema={get status(){return {open:!!cinemaModal,renderer:cinemaModal?'three':'closed',
      publicCardCount:cinemaCards.length,selectedIndex:cinemaIndex};},
    get scene(){return cinemaScene;},close:modalClose};
  document.addEventListener('visibilitychange',()=>{if(sceneApi&&enabled){if(document.hidden)sceneApi.pause();else sceneApi.resume();}});
  window.addEventListener('beforeunload',()=>sceneApi?.dispose());
  window.MCW3D={get status(){return {enabled,renderer:document.body.classList.contains('mcw-three-ready')?'three':enabled?'css':'legacy'};},
    disable:()=>setEnabled(false), get scene(){return sceneApi;}};
})();
