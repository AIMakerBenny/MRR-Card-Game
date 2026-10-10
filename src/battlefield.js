/* Phase 46: read-only full-board perspective 3D presentation.
 * Source of truth is the visible HTML board. No game state, hidden hand, AI,
 * combat rules, localStorage, or original click targets are read or modified.
 */
window.MRRBattlefieldFactory=function(THREE,mount){
  'use strict';
  const scene=new THREE.Scene();
  scene.background=new THREE.Color(0x080f1a);
  scene.fog=new THREE.FogExp2(0x080f1a,0.018);
  const camera=new THREE.PerspectiveCamera(44,1,.1,130);
  const renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:'high-performance'});
  renderer.outputColorSpace=THREE.SRGBColorSpace;
  renderer.toneMapping=THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure=1.47;
  renderer.shadowMap.enabled=true;
  renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  renderer.domElement.setAttribute('aria-label','실시간 공개 카드 3D 전장');
  renderer.domElement.style.cssText='width:100%;height:100%;display:block';
  mount.appendChild(renderer.domElement);
  scene.add(new THREE.HemisphereLight(0xbad8e8,0x423440,2.0));
  const sun=new THREE.DirectionalLight(0xffe2b1,4.2);
  sun.position.set(-8,18,13);sun.castShadow=true;
  sun.shadow.mapSize.set(2048,2048);
  sun.shadow.camera.left=-22;sun.shadow.camera.right=22;
  sun.shadow.camera.top=22;sun.shadow.camera.bottom=-22;
  scene.add(sun);
  const enemyLamp=new THREE.PointLight(0xf06b65,80,29);
  enemyLamp.position.set(0,3,-9.5);scene.add(enemyLamp);
  const friendlyLamp=new THREE.PointLight(0x51cdea,95,29);
  friendlyLamp.position.set(0,3,9.5);scene.add(friendlyLamp);

  const madeGeometry=[],madeMaterials=[],madeTextures=[];
  const material=(options,physical=false)=>{
    const m=physical?new THREE.MeshPhysicalMaterial(options):new THREE.MeshStandardMaterial(options);
    madeMaterials.push(m);return m;
  };
  const geometry=g=>{madeGeometry.push(g);return g;};
  const black=material({color:0x223746,metalness:.18,roughness:.72});
  const stone=material({color:0x354957,metalness:.18,roughness:.71});
  const bronze=material({color:0xc6a777,metalness:.68,roughness:.29,clearcoat:.4},true);
  const gold=material({color:0xebc789,metalness:.58,roughness:.3});
  const red=material({color:0xcf6c6a,metalness:.32,roughness:.39,emissive:0x7a2529,emissiveIntensity:.48});
  const blue=material({color:0x64b9cc,metalness:.32,roughness:.36,emissive:0x0a647b,emissiveIntensity:.5});
  const tileGeo=geometry(new THREE.BoxGeometry(2.25,.15,2.45));
  const edgeGeo=geometry(new THREE.BoxGeometry(2.38,.08,2.58));
  const platformGeo=geometry(new THREE.BoxGeometry(22,.65,22.1));
  const floor=new THREE.Mesh(geometry(new THREE.PlaneGeometry(180,180)),black);
  floor.rotation.x=-Math.PI/2;floor.position.y=-.52;floor.receiveShadow=true;scene.add(floor);
  const platform=new THREE.Mesh(platformGeo,stone);
  platform.position.y=-.22;platform.receiveShadow=true;scene.add(platform);
  const border=new THREE.Mesh(geometry(new THREE.BoxGeometry(22.45,.17,22.55)),bronze);
  border.position.y=-.58;scene.add(border);
  for(const sx of [-1,1]){
    const rail=new THREE.Mesh(geometry(new THREE.BoxGeometry(.17,.24,22.2)),gold);
    rail.position.set(sx*11.01,.18,0);scene.add(rail);
    for(const sz of [-1,1]){
      const tower=new THREE.Group();tower.position.set(sx*11.6,0,sz*11.5);
      const post=new THREE.Mesh(geometry(new THREE.CylinderGeometry(.43,.56,4.1,10)),stone);
      post.position.y=1.9;post.castShadow=true;tower.add(post);
      const crown=new THREE.Mesh(geometry(new THREE.CylinderGeometry(.7,.47,.5,10)),bronze);
      crown.position.y=4.13;tower.add(crown);
      const flame=new THREE.Mesh(geometry(new THREE.ConeGeometry(.24,.67,9)),
        material({color:sz>0?0x72dff4:0xf08f70,emissive:sz>0?0x26a8de:0xea5548,emissiveIntensity:1.65,roughness:.2}));
      flame.position.y=4.56;tower.add(flame);
      scene.add(tower);
    }
  }
  const lanes=[
    {owner:1,row:'terrace',z:-8.38,label:'적 시설'},
    {owner:1,row:'rear',z:-5.5,label:'적 후열'},
    {owner:1,row:'front',z:-2.65,label:'적 전열'},
    {owner:0,row:'front',z:2.65,label:'아군 전열'},
    {owner:0,row:'rear',z:5.5,label:'아군 후열'},
    {owner:0,row:'terrace',z:8.38,label:'아군 시설'}
  ];
  const boardSlots=new Map();
  const cardGeometry=geometry(new THREE.BoxGeometry(2.08,2.84,.22));
  const cardFaceGeometry=geometry(new THREE.PlaneGeometry(1.96,2.71));
  const stripGeo=geometry(new THREE.BoxGeometry(19.5,.025,.045));
  for(const lane of lanes){
    const laneMaterial=lane.owner===0?blue:red;
    const laneBorder=new THREE.Mesh(stripGeo,laneMaterial);
    laneBorder.position.set(0,.17,lane.z-1.36);scene.add(laneBorder);
    for(let col=0;col<5;col++){
      const x=(col-2)*3.37;
      const inset=new THREE.Mesh(edgeGeo,bronze);inset.position.set(x,.15,lane.z);
      inset.receiveShadow=true;scene.add(inset);
      const base=new THREE.Mesh(tileGeo,black);base.position.set(x,.23,lane.z);
      base.receiveShadow=true;scene.add(base);
      const crest=new THREE.Mesh(geometry(new THREE.TorusGeometry(.5,.035,7,32)),laneMaterial);
      crest.rotation.x=-Math.PI/2;crest.position.set(x,.32,lane.z);scene.add(crest);
      boardSlots.set(lane.owner+':'+lane.row+':'+col,{x,z:lane.z,owner:lane.owner,row:lane.row,col});
    }
  }
  const center=new THREE.Mesh(geometry(new THREE.BoxGeometry(21,.035,.1)),gold);
  center.position.y=.19;scene.add(center);
  const seal=new THREE.Mesh(geometry(new THREE.TorusGeometry(1.06,.055,8,80)),bronze);
  seal.rotation.x=-Math.PI/2;seal.position.y=.23;scene.add(seal);
  const sealCore=new THREE.Mesh(geometry(new THREE.OctahedronGeometry(.45)),gold);
  sealCore.position.y=.95;scene.add(sealCore);
  const emberPositions=new Float32Array(210*3);
  for(let i=0;i<210;i++){
    const k=i*3;
    emberPositions[k]=(Math.sin(i*91.7)*.5)*40;
    emberPositions[k+1]=1+((i*127)%130)/12;
    emberPositions[k+2]=(Math.cos(i*29.4)*.5)*42;
  }
  const embersGeo=geometry(new THREE.BufferGeometry());
  embersGeo.setAttribute('position',new THREE.BufferAttribute(emberPositions,3));
  const embers=new THREE.Points(embersGeo,new THREE.PointsMaterial({
    color:0xc7ae8b,size:.055,transparent:true,opacity:.42,depthWrite:false
  }));
  madeMaterials.push(embers.material);scene.add(embers);

  function publicSnapshot(){
    return [...document.querySelectorAll('#arena [data-slot]')].map(el=>{
      const key=el.getAttribute('data-slot');
      if(!boardSlots.has(key))return null;
      const card=el.querySelector('.board-card .card-ui');
      return {key,selected:el.classList.contains('selected-slot'),
        name:card?.querySelector('.card-name')?.textContent?.trim()||'',
        kind:card?.querySelector('.card-kind')?.textContent?.trim()||'',
        cost:card?.querySelector('.cost-bubble')?.textContent?.trim()||'',
        stats:card?.querySelector('.card-stats')?.textContent?.trim()||'',
        sigil:card?.querySelector('.sigil-text')?.textContent?.trim()||''};
    }).filter(Boolean);
  }
  function cardTexture(profile,ally){
    const canvas=document.createElement('canvas');
    canvas.width=512;canvas.height=704;
    const c=canvas.getContext('2d');
    const gradient=c.createLinearGradient(0,0,512,704);
    gradient.addColorStop(0,ally?'#1b4e63':'#63333d');
    gradient.addColorStop(.5,'#152a35');
    gradient.addColorStop(1,'#07131e');
    c.fillStyle=gradient;c.fillRect(0,0,512,704);
    c.strokeStyle='#c9aa70';c.lineWidth=17;c.strokeRect(13,13,486,678);
    c.strokeStyle='#fff0b8';c.lineWidth=3;c.strokeRect(31,31,450,642);
    c.fillStyle='#071923';c.fillRect(47,49,420,97);
    c.textAlign='center';c.textBaseline='middle';
    c.fillStyle='#f6e3b6';c.font='bold 37px sans-serif';
    c.fillText(profile.name.slice(0,24),262,96,365);
    c.fillStyle='#aacdcd';c.font='22px sans-serif';
    c.fillText(profile.kind.slice(0,30),260,163,425);
    const panel=c.createRadialGradient(255,350,18,255,350,240);
    panel.addColorStop(0,ally?'#43788a':'#875559');
    panel.addColorStop(1,'#0b1b2a');
    c.fillStyle=panel;c.fillRect(50,194,412,329);
    c.strokeStyle='#cfb07d';c.lineWidth=5;c.strokeRect(52,196,408,325);
    c.save();c.translate(256,348);
    c.strokeStyle='#e5c790';c.lineWidth=7;
    c.beginPath();c.arc(0,0,114,0,Math.PI*2);c.stroke();
    c.strokeStyle=ally?'#9ae3ec':'#ebae9f';c.lineWidth=5;
    for(let i=0;i<8;i++){
      c.save();c.rotate(i*Math.PI/4);
      c.beginPath();c.moveTo(0,-130);c.lineTo(0,-152);c.stroke();c.restore();
    }
    c.beginPath();c.moveTo(0,-79);c.lineTo(79,0);c.lineTo(0,79);c.lineTo(-79,0);
    c.closePath();c.stroke();
    c.fillStyle='#f5d6a2';c.font='bold 92px sans-serif';
    c.fillText(profile.sigil.slice(0,2)||'◇',0,5,135);c.restore();
    c.fillStyle='#0a1927';c.fillRect(52,542,408,112);
    c.strokeStyle='#c9aa70';c.lineWidth=3;c.strokeRect(52,542,408,112);
    c.fillStyle='#dce9e6';c.font='bold 23px sans-serif';
    c.fillText(profile.stats.slice(0,42)||'공개 전장 카드',256,597,380);
    c.fillStyle='#ead7ac';c.font='bold 24px sans-serif';
    c.fillText(ally?'ALLY':'OPPONENT',256,630);
    c.fillStyle='#102637';c.beginPath();c.arc(58,92,31,0,Math.PI*2);c.fill();
    c.strokeStyle='#efcd89';c.lineWidth=5;c.stroke();
    c.fillStyle='#ffffff';c.font='bold 33px sans-serif';
    c.fillText(profile.cost.slice(0,3),58,96);
    const texture=new THREE.CanvasTexture(canvas);
    texture.colorSpace=THREE.SRGBColorSpace;texture.anisotropy=4;
    madeTextures.push(texture);return texture;
  }
  let cards=[],signature='',publicCardCount=0,lastSync=0;
  function sync(){
    const list=publicSnapshot(),s=JSON.stringify(list);
    if(s===signature)return;
    signature=s;
    for(const o of cards){scene.remove(o.group);o.face.material.map.dispose();o.face.material.dispose();}
    cards=[];madeTextures.length=0;publicCardCount=0;
    for(const p of list){
      if(!p.name)continue;
      const slot=boardSlots.get(p.key);
      const group=new THREE.Group();
      group.position.set(slot.x,1.76,slot.z);
      group.rotation.x=-.74;
      const frame=new THREE.Mesh(cardGeometry,p.selected?gold:(slot.owner===0?blue:red));
      frame.castShadow=true;group.add(frame);
      const face=new THREE.Mesh(cardFaceGeometry,new THREE.MeshStandardMaterial({
        map:cardTexture(p,slot.owner===0),metalness:.05,roughness:.48
      }));
      face.position.z=.116;group.add(face);
      const stand=new THREE.Mesh(cardGeometry,bronze);
      stand.position.z=-.065;stand.scale.set(1.055,1.05,.18);group.add(stand);
      scene.add(group);cards.push({group,face,slot});
      publicCardCount++;
    }
  }
  let yaw=0,pitch=.77,distance=29,drag=false,lastX=0,lastY=0;
  function updateCamera(){
    const aspect=mount.clientWidth/Math.max(1,mount.clientHeight);
    const d=distance*(aspect<.75?1.6:aspect<1.1?1.22:1);
    camera.position.set(Math.sin(yaw)*Math.cos(pitch)*d,
      1.3+Math.sin(pitch)*d,Math.cos(yaw)*Math.cos(pitch)*d);
    camera.lookAt(0,.8,0);
  }
  function down(e){if(e.button!==0)return;drag=true;lastX=e.clientX;lastY=e.clientY;mount.setPointerCapture?.(e.pointerId);}
  function move(e){if(!drag)return;yaw=Math.max(-.8,Math.min(.8,yaw+(e.clientX-lastX)*.004));
    pitch=Math.max(.42,Math.min(1.28,pitch+(e.clientY-lastY)*.003));
    lastX=e.clientX;lastY=e.clientY;updateCamera();}
  function up(){drag=false;}
  function wheel(e){e.preventDefault();distance=Math.max(24,Math.min(47,distance+e.deltaY*.018));updateCamera();}
  mount.addEventListener('pointerdown',down);
  mount.addEventListener('pointermove',move);
  mount.addEventListener('pointerup',up);
  mount.addEventListener('pointercancel',up);
  mount.addEventListener('wheel',wheel,{passive:false});
  let frames=0,raf=0,running=false,disposed=false,lastDraw=0;
  function resize(){
    if(disposed)return;
    const w=Math.max(250,mount.clientWidth||900),h=Math.max(240,mount.clientHeight||560);
    camera.aspect=w/h;camera.updateProjectionMatrix();
    renderer.setPixelRatio(Math.min(devicePixelRatio||1,w<650?1:1.5));
    renderer.setSize(w,h,false);updateCamera();
  }
  function tick(time){
    if(!running||disposed)return;
    raf=requestAnimationFrame(tick);
    const interval=mount.clientWidth<650?48:32;
    if(time-lastDraw<interval)return;
    lastDraw=time;
    if(time-lastSync>220){lastSync=time;sync();}
    const frozen=matchMedia('(prefers-reduced-motion: reduce)').matches;
    if(!frozen){
      sealCore.rotation.y=time*.00035;
      for(const [i,c] of cards.entries())c.group.position.y=1.76+Math.sin(time*.0015+i*.67)*.045;
    }
    renderer.render(scene,camera);frames++;
  }
  function start(){if(disposed)return;resize();sync();if(running)return;running=true;lastDraw=0;raf=requestAnimationFrame(tick);}
  function stop(){running=false;cancelAnimationFrame(raf);}
  function resetCamera(){yaw=0;pitch=.77;distance=29;updateCamera();}
  function dispose(){
    if(disposed)return;stop();disposed=true;
    for(const c of cards){c.face.material.map.dispose();c.face.material.dispose();}
    cards=[];for(const g of madeGeometry)g.dispose();
    for(const m of madeMaterials)m.dispose();
    for(const t of madeTextures)t.dispose();
    mount.removeEventListener('pointerdown',down);
    mount.removeEventListener('pointermove',move);
    mount.removeEventListener('pointerup',up);
    mount.removeEventListener('pointercancel',up);
    mount.removeEventListener('wheel',wheel);
    renderer.dispose();renderer.domElement.remove();
  }
  return {start,stop,dispose,resize,resetCamera,sync,
    get state(){return {revision:46,projection:camera.type,frames,slotCount:boardSlots.size,
      publicCardCount,cardMeshCount:cards.length,shadows:renderer.shadowMap.enabled,
      rendererAlive:renderer.domElement.isConnected,yaw,pitch,distance};}};
};
window.MRRBattlefieldUIInit=function(loadThree){
  'use strict';
  const bar=document.querySelector('.mcw-top-controls'),root=document.querySelector('#gameScreen');
  if(!bar||!root||document.getElementById('mrr-battlefield-open'))return;
  const button=document.createElement('button');
  button.id='mrr-battlefield-open';button.type='button';button.textContent='입체 전장';
  button.title='전체 공개 전장을 원근 3D로 둘러보기';
  bar.appendChild(button);
  let overlay=null,view=null,busy=false;
  function close(){
    const oldOverlay=overlay,oldView=view;
    overlay=null;view=null;button.disabled=false;
    try{oldView?.dispose();}catch(e){console.warn('3D battlefield dispose:',e);}
    finally{oldOverlay?.remove();if(button.isConnected)button.focus({preventScroll:true});}
  }
  button.addEventListener('click',async()=>{
    if(busy||overlay)return;busy=true;button.disabled=true;
    try{
      const THREE=await loadThree();
      const layer=document.createElement('div');layer.id='mrr-battlefield-modal';
      const dialog=document.createElement('section');dialog.id='mrr-battlefield-dialog';
      dialog.setAttribute('role','dialog');dialog.setAttribute('aria-modal','true');
      dialog.setAttribute('aria-label','입체 전장 전체보기');
      const header=document.createElement('header');header.id='mrr-battlefield-header';
      const name=document.createElement('span');name.textContent='MARORONG CARD WAR  /  3D BATTLEFIELD';
      const status=document.createElement('span');status.id='mrr-battlefield-status';status.textContent='공개 전장 전체 30슬롯';
      const reset=document.createElement('button');reset.id='mrr-battlefield-reset';reset.textContent='시점 초기화';
      const exit=document.createElement('button');exit.id='mrr-battlefield-close';exit.textContent='게임으로 돌아가기';
      exit.addEventListener('click',close);
      header.append(name,status,reset,exit);
      const stage=document.createElement('div');stage.id='mrr-battlefield-stage';
      const overlayHelp=document.createElement('div');overlayHelp.id='mrr-battlefield-help';
      overlayHelp.textContent='마우스 드래그 - 카메라 회전  |  휠 - 확대·축소  |  실제 카드 조작은 게임 화면에서';
      const enemy=document.createElement('div');enemy.className='mrr-side-label enemy';enemy.textContent='OPPONENT TERRITORY';
      const friendly=document.createElement('div');friendly.className='mrr-side-label friendly';friendly.textContent='ALLIED TERRITORY';
      stage.append(enemy,friendly,overlayHelp);
      dialog.append(header,stage);layer.appendChild(dialog);document.body.appendChild(layer);
      layer.addEventListener('click',event=>{if(event.target===layer)close();});
      overlay=layer;view=window.MRRBattlefieldFactory(THREE,stage);
      reset.addEventListener('click',()=>view?.resetCamera());
      view.start();
      status.textContent='30 전장 슬롯  /  공개 카드 '+view.state.publicCardCount+'장';
      exit.focus();
    }catch(err){console.warn('Phase46 WebGL battlefield unavailable:',err);close();}
    finally{busy=false;}
  });
  window.addEventListener('keyup',e=>{if(e.key==='Escape'&&overlay){
    e.preventDefault();e.stopImmediatePropagation();close();
  }},true);
  window.addEventListener('resize',()=>view?.resize());
  document.addEventListener('visibilitychange',()=>{if(view){if(document.hidden)view.stop();else view.start();}});
  window.addEventListener('beforeunload',()=>view?.dispose());
  window.MRRBattlefield={get state(){return {open:!!overlay,scene:view?.state||null};},get scene(){return view;},close};
};
