/* Phase37: optional independent cinematic 3D viewport. This scene only renders
 * display data; the existing JavaScript engine remains authoritative. */
window.MRRCinemaFactory=function(THREE,mount){
  'use strict';
  const scene=new THREE.Scene();
  scene.background=new THREE.Color(0x09121d);
  scene.fog=new THREE.FogExp2(0x09121d,0.032);
  const camera=new THREE.PerspectiveCamera(36,1,.1,100);
  camera.position.set(0,2.7,9.6);camera.lookAt(0,1.9,0);
  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,powerPreference:'high-performance'});
  renderer.outputColorSpace=THREE.SRGBColorSpace;
  renderer.toneMapping=THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure=1.35;
  renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  renderer.domElement.style.cssText='width:100%;height:100%;display:block;pointer-events:none';
  renderer.domElement.setAttribute('aria-hidden','true');mount.appendChild(renderer.domElement);
  const ambient=new THREE.HemisphereLight(0x9ecbe6,0x17131f,1.5);scene.add(ambient);
  const key=new THREE.SpotLight(0xffd49d,180,30,Math.PI/5,.52,1.3);
  key.position.set(-4,9,7);key.castShadow=true;key.shadow.mapSize.set(1024,1024);scene.add(key);
  const rim=new THREE.PointLight(0x4daddb,65,14);rim.position.set(3,3,-2);scene.add(rim);
  const card=new THREE.Group();card.position.set(0,2.15,0);scene.add(card);
  const gold=new THREE.MeshPhysicalMaterial({color:0xc39a58,metalness:.82,roughness:.22,clearcoat:.85,clearcoatRoughness:.16});
  const bevel=new THREE.Mesh(new THREE.BoxGeometry(3.12,4.42,.27),gold);
  bevel.castShadow=true;card.add(bevel);
  const core=new THREE.Mesh(new THREE.BoxGeometry(2.94,4.24,.295),
    new THREE.MeshStandardMaterial({color:0x17242d,metalness:.3,roughness:.5}));
  core.position.z=.016;card.add(core);
  const frontMaterial=new THREE.MeshStandardMaterial({color:0xffffff,metalness:.05,roughness:.49,side:THREE.FrontSide});
  const front=new THREE.Mesh(new THREE.PlaneGeometry(2.84,4.15),frontMaterial);
  front.position.z=.174;card.add(front);
  const back=new THREE.Mesh(new THREE.PlaneGeometry(2.84,4.15),
    new THREE.MeshStandardMaterial({color:0x1d3142,metalness:.22,roughness:.47,side:THREE.DoubleSide}));
  back.position.z=-.166;back.rotation.y=Math.PI;card.add(back);

  // Phase41: locally authored full-bleed card-back art, no external assets.
  function paintCardBack(){
    const canvas=document.createElement('canvas');canvas.width=512;canvas.height=720;
    const c=canvas.getContext('2d');
    const bg=c.createLinearGradient(20,10,490,710);
    bg.addColorStop(0,'#30485b');bg.addColorStop(.32,'#0f2631');
    bg.addColorStop(.7,'#162b34');bg.addColorStop(1,'#533d31');
    c.fillStyle=bg;c.fillRect(0,0,512,720);
    c.strokeStyle='#cba569';c.lineWidth=20;c.strokeRect(15,15,482,690);
    c.strokeStyle='#f3d49b';c.lineWidth=2.5;c.strokeRect(34,34,444,652);
    c.strokeStyle='#786b55';c.lineWidth=4;c.strokeRect(46,46,420,628);
    const g=c.createRadialGradient(256,342,16,256,342,214);
    g.addColorStop(0,'#a4d8c258');g.addColorStop(.52,'#497d8348');g.addColorStop(1,'#0b1b2600');
    c.fillStyle=g;c.fillRect(48,70,416,570);
    c.save();c.translate(256,345);
    for(let k=0;k<16;k++){c.save();c.rotate(k*Math.PI/8);
      c.strokeStyle=k%2?'#deb77899':'#a7daca77';c.lineWidth=k%2?3:2;
      c.beginPath();c.moveTo(0,-193);c.lineTo(0,-221);c.stroke();
      c.beginPath();c.moveTo(-7,-178);c.lineTo(0,-165);c.lineTo(7,-178);c.stroke();
      c.restore();}
    c.strokeStyle='#e0c391';c.lineWidth=9;
    c.beginPath();c.arc(0,0,158,0,Math.PI*2);c.stroke();
    c.lineWidth=2.5;c.strokeStyle='#9fd6d1';
    c.beginPath();c.arc(0,0,133,0,Math.PI*2);c.stroke();
    c.save();c.rotate(Math.PI/4);
    c.strokeStyle='#d7b985';c.strokeRect(-81,-81,162,162);
    c.restore();
    c.fillStyle='#0e2630';c.beginPath();c.arc(0,0,110,0,Math.PI*2);c.fill();
    c.strokeStyle='#e5c98b';c.lineWidth=5;
    c.beginPath();c.moveTo(-61,64);c.lineTo(-61,-64);c.lineTo(0,16);
    c.lineTo(61,-64);c.lineTo(61,64);c.stroke();
    c.fillStyle='#d7c291';c.beginPath();c.moveTo(0,-108);
    c.lineTo(13,-91);c.lineTo(0,-75);c.lineTo(-13,-91);c.closePath();c.fill();
    c.restore();
    c.textAlign='center';c.textBaseline='middle';
    c.fillStyle='#f1dbad';c.font='bold 28px Georgia,serif';
    c.fillText('MARORONG',256,92);
    c.font='bold 24px Georgia,serif';c.fillText('CARD WAR',256,636);
    for(const [x,y,sx,sy] of [[70,89,1,1],[442,89,-1,1],[70,634,1,-1],[442,634,-1,-1]]){
      c.save();c.translate(x,y);c.scale(sx,sy);
      c.strokeStyle='#d1ae76';c.lineWidth=4;c.beginPath();
      c.moveTo(0,38);c.lineTo(0,0);c.lineTo(38,0);c.stroke();
      c.restore();
    }
    const map=new THREE.CanvasTexture(canvas);
    map.colorSpace=THREE.SRGBColorSpace;map.anisotropy=4;
    return map;
  }
  const backTexture=paintCardBack();
  back.material.color.set(0xffffff);
  back.material.map=backTexture;
  back.material.needsUpdate=true;
  const railGeometry=new THREE.BoxGeometry(.04,4.08,.06);
  const rails=[];
  for(const side of [-1,1]){const x=new THREE.Mesh(railGeometry,gold);x.position.set(side*1.39,0,.19);card.add(x);rails.push(x);}
  const gem=new THREE.Mesh(new THREE.OctahedronGeometry(.105),
    new THREE.MeshPhysicalMaterial({color:0x63e7e3,emissive:0x0b555a,emissiveIntensity:.75,metalness:.38,roughness:.14}));
  gem.position.set(0,2.1,.24);card.add(gem);

  // Phase38 - a world-space diorama with shadows, material depth and a
  // physically illuminated platform, not another HTML gradient.
  const stage=new THREE.Group();scene.add(stage);
  const stageObjects=[],stageMats=[],stageGeometries=[];
  function add(mesh){stage.add(mesh);stageObjects.push(mesh);return mesh;}
  const obsidian=new THREE.MeshStandardMaterial({color:0x101e2b,metalness:.5,roughness:.58});
  const bronze=new THREE.MeshPhysicalMaterial({color:0x896b48,metalness:.84,roughness:.31,clearcoat:.46});
  const stone=new THREE.MeshStandardMaterial({color:0x1c303c,metalness:.22,roughness:.81});
  stageMats.push(obsidian,bronze,stone);
  const floor=add(new THREE.Mesh(new THREE.PlaneGeometry(60,60),stone));
  stageGeometries.push(floor.geometry);floor.rotation.x=-Math.PI/2;floor.position.y=-.73;floor.receiveShadow=true;
  const base=add(new THREE.Mesh(new THREE.CylinderGeometry(2.9,3.17,.42,80,1),obsidian));
  stageGeometries.push(base.geometry);base.position.y=-.49;base.receiveShadow=true;
  const lip=add(new THREE.Mesh(new THREE.TorusGeometry(2.85,.055,8,96),bronze));
  stageGeometries.push(lip.geometry);lip.rotation.x=Math.PI/2;lip.position.y=-.268;
  const center=add(new THREE.Mesh(new THREE.CylinderGeometry(2.5,2.5,.05,80),bronze));
  stageGeometries.push(center.geometry);center.position.y=-.24;center.receiveShadow=true;
  const plaque=add(new THREE.Mesh(new THREE.CylinderGeometry(2.37,2.37,.06,80),obsidian));
  stageGeometries.push(plaque.geometry);plaque.position.y=-.197;plaque.receiveShadow=true;
  // Eight architectural columns remain behind and below the interactive card.
  for(let i=0;i<8;i++){
    // Keep architecture to either side of the main card. No columns are
    // allowed in the center corridor, even after perspective projection.
    const xs=[-7.3,-5.5,5.5,7.3,-8,-6.5,6.5,8];
    const col=add(new THREE.Mesh(new THREE.CylinderGeometry(.19,.3,4.1,8),stone));
    stageGeometries.push(col.geometry);
    col.position.set(xs[i],1.18,i<4?-2.7:-6.1);
    col.castShadow=true;
    const cap=add(new THREE.Mesh(new THREE.CylinderGeometry(.37,.24,.23,8),bronze));
    stageGeometries.push(cap.geometry);cap.position.set(col.position.x,3.3,col.position.z);
  }
  // Reflective arcane rings and warm/cool accent lights produce depth cues.
  const rings=[];
  const runeMat=new THREE.MeshBasicMaterial({color:0xb4dfd8,transparent:true,opacity:.55,side:THREE.DoubleSide});
  stageMats.push(runeMat);
  for(const rad of [1.28,1.72,2.18]){
    const mesh=add(new THREE.Mesh(new THREE.TorusGeometry(rad,.013,4,96),runeMat));
    stageGeometries.push(mesh.geometry);mesh.rotation.x=Math.PI/2;mesh.position.y=-.151;rings.push(mesh);
  }
  const torch1=new THREE.PointLight(0xe9a760,45,11,2);torch1.position.set(-3.7,2.2,2.1);stage.add(torch1);
  const torch2=new THREE.PointLight(0x54c5e1,42,11,2);torch2.position.set(3.7,1.9,-.8);stage.add(torch2);
  const portraitGlow=new THREE.Mesh(new THREE.SphereGeometry(.09,10,10),
    new THREE.MeshBasicMaterial({color:0xf2d293}));
  stageGeometries.push(portraitGlow.geometry);stageMats.push(portraitGlow.material);
  portraitGlow.position.set(0,4.7,-1.1);stage.add(portraitGlow);
  // Phase43: real perspective orbit/zoom with clamped angles. Input is
  // handled exclusively by the optional modal stage, not the game board.
  let orbitYaw=0,orbitPitch=.13,orbitDistance=9.6;
  let drag=null;
  function updateCamera(){
    const target=new THREE.Vector3(0,1.9,0);
    const vertical=orbitDistance*Math.sin(orbitPitch);
    const radius=orbitDistance*Math.cos(orbitPitch);
    camera.position.set(radius*Math.sin(orbitYaw),1.9+vertical,radius*Math.cos(orbitYaw));
    camera.lookAt(target);
  }
  function orbit(dx,dy){
    orbitYaw=THREE.MathUtils.clamp(orbitYaw+dx,-1.1,1.1);
    orbitPitch=THREE.MathUtils.clamp(orbitPitch+dy,-.24,.6);
    updateCamera();
  }
  function zoom(amount){
    orbitDistance=THREE.MathUtils.clamp(orbitDistance+amount,7.1,13.5);
    updateCamera();
  }
  function resetCamera(){orbitYaw=0;orbitPitch=.13;orbitDistance=9.6;updateCamera();}
  function onDown(e){
    if(e.button!==0||disposed)return;
    drag={id:e.pointerId,x:e.clientX,y:e.clientY};
    mount.setPointerCapture?.(e.pointerId);
  }
  function onMove(e){
    if(!drag||e.pointerId!==drag.id)return;
    orbit((e.clientX-drag.x)*.007,(e.clientY-drag.y)*.005);
    drag.x=e.clientX;drag.y=e.clientY;
  }
  function onUp(e){
    if(!drag||drag.id!==e.pointerId)return;
    drag=null;
    try{if(mount.hasPointerCapture?.(e.pointerId))mount.releasePointerCapture(e.pointerId);}catch(_){}
  }
  function onWheel(e){e.preventDefault();zoom(e.deltaY*.004);}
  mount.addEventListener('pointerdown',onDown);
  mount.addEventListener('pointermove',onMove);
  mount.addEventListener('pointerup',onUp);
  mount.addEventListener('pointercancel',onUp);
  mount.addEventListener('wheel',onWheel,{passive:false});
  resetCamera();
  let cardToken=0,viewMode='front';
  function setView(value){
    if(disposed)return;
    if(value!=='front'&&value!=='back')return;
    viewMode=value;
  }
  let lastDraw=0;
  let frame=0,raf=0,running=false,disposed=false,startAt=0,profile={name:'MARORONG',kind:'CARD WAR',cost:'',stats:''};
  function artwork(p){
    const cvs=document.createElement('canvas');cvs.width=640;cvs.height=900;
    const c=cvs.getContext('2d');const name=(p.name||'MARORONG').slice(0,42);
    const kind=(p.kind||'CARD WAR').slice(0,44);
    let seed=2166136261;for(const ch of name+'|'+kind)seed=Math.imul(seed^ch.charCodeAt(0),16777619)>>>0;
    const rnd=()=>{seed^=seed<<13;seed^=seed>>>17;seed^=seed<<5;return (seed>>>0)/4294967296;};
    const bg=c.createLinearGradient(0,0,640,900);
    bg.addColorStop(0,'#152f40');bg.addColorStop(.55,'#243549');bg.addColorStop(1,'#080e1a');
    c.fillStyle=bg;c.fillRect(0,0,640,900);
    const grd=c.createRadialGradient(330,300,35,330,300,310);
    grd.addColorStop(0,'#e2a96a55');grd.addColorStop(1,'#11182700');
    c.fillStyle=grd;c.fillRect(0,0,640,850);
    c.strokeStyle='#dfbb7a';c.lineWidth=15;c.strokeRect(20,20,600,860);
    c.strokeStyle='#e7cea0';c.lineWidth=3;c.strokeRect(37,37,566,826);
    c.fillStyle='#081c29';c.fillRect(52,54,536,118);
    c.textAlign='center';c.textBaseline='middle';c.fillStyle='#f9deb0';
    c.font='bold 40px sans-serif';c.fillText(name,320,105,505);
    c.font='26px sans-serif';c.fillStyle='#aad6d5';c.fillText(kind,320,149,505);
    // Stylized illustrative landscape, not an externally sourced asset.
    c.fillStyle='#162c38';c.beginPath();c.moveTo(53,610);
    for(let i=0;i<12;i++)c.lineTo(53+i*48,490-rnd()*120);
    c.lineTo(587,620);c.closePath();c.fill();
    c.fillStyle='#0c1b2a';c.beginPath();c.moveTo(53,660);
    for(let i=0;i<13;i++)c.lineTo(53+i*44,560-rnd()*85);
    c.lineTo(587,670);c.closePath();c.fill();
    c.save();c.translate(320,402);
    c.strokeStyle='#e7bd7f';c.lineWidth=10;c.beginPath();c.arc(0,0,151,0,Math.PI*2);c.stroke();
    for(let i=0;i<12;i++){c.save();c.rotate(i*Math.PI/6);c.strokeStyle='#79c0c777';c.lineWidth=3;
      c.beginPath();c.moveTo(0,-172);c.lineTo(0,-192);c.stroke();c.restore();}
    c.fillStyle='#142c3d';c.beginPath();c.arc(0,0,120,0,Math.PI*2);c.fill();
    c.strokeStyle='#9bdfd8';c.lineWidth=6;c.beginPath();
    c.moveTo(0,-93);c.lineTo(83,0);c.lineTo(0,93);c.lineTo(-83,0);c.closePath();c.stroke();
    c.fillStyle='#e9bd82';c.beginPath();c.moveTo(0,-65);c.lineTo(45,0);c.lineTo(0,65);c.lineTo(-45,0);c.closePath();c.fill();
    c.restore();
    for(let i=0;i<30;i++){c.globalAlpha=.15+rnd()*.55;c.fillStyle='#cae7dd';
      c.fillRect(70+rnd()*500,215+rnd()*370,2+rnd()*3,2+rnd()*3);}
    c.globalAlpha=1;c.fillStyle='#0e1c2a';c.fillRect(52,692,536,140);
    c.strokeStyle='#9e8455';c.lineWidth=2;c.strokeRect(54,693,532,138);
    c.fillStyle='#eddaa8';c.font='bold 27px sans-serif';c.fillText(String(p.stats||'3D CINEMATIC CARD').replace(/([가-힣]+)(\d+)/g,'$1 $2 ').slice(0,45),320,748,495);
    c.font='18px sans-serif';c.fillStyle='#b7d8d7';c.fillText('MARORONG CARD WAR',320,797);
    if(p.cost){
      c.fillStyle='#193b52';c.beginPath();c.arc(555,205,36,0,Math.PI*2);c.fill();
      c.lineWidth=4;c.strokeStyle='#e0bd7e';c.stroke();
      c.fillStyle='#f9e4b7';c.font='bold 36px sans-serif';c.fillText(String(p.cost).slice(0,4),555,209);
    }
    const texture=new THREE.CanvasTexture(cvs);texture.colorSpace=THREE.SRGBColorSpace;texture.anisotropy=4;
    return texture;
  }
  function setCard(p){
    if(disposed)return;
    const token=++cardToken;
    profile={name:String(p?.name||'MARORONG'),kind:String(p?.kind||'CARD WAR'),
      cost:String(p?.cost||''),stats:String(p?.stats||'')};
    frontMaterial.map?.dispose();frontMaterial.map=artwork(profile);frontMaterial.needsUpdate=true;
    // Reuse only locally generated public card art from the live DOM.
    // On-load guards prevent old images from replacing later card selections.
    if(typeof p?.artData==='string'&&p.artData.startsWith('data:image/png;base64,')){
      const pic=new Image();
      pic.onload=()=>{
        if(disposed||token!==cardToken)return;
        const ctx=frontMaterial.map?.image?.getContext('2d');
        if(!ctx)return;
        ctx.save();ctx.beginPath();ctx.rect(65,188,510,475);ctx.clip();
        ctx.drawImage(pic,65,188,510,475);ctx.restore();
        frontMaterial.map.needsUpdate=true;
      };
      pic.src=p.artData;
    }
  }
  function resize(){
    if(disposed)return;
    const w=Math.max(200,mount.clientWidth||800),h=Math.max(200,mount.clientHeight||520);
    camera.aspect=w/h;camera.updateProjectionMatrix();
    const cap=w<620?1:1.5;
    renderer.setPixelRatio(Math.min(Math.max(.75,devicePixelRatio||1),cap));
    renderer.setSize(w,h,false);
  }
  function tick(t){
    if(!running||disposed)return;
    raf=requestAnimationFrame(tick);
    const frameInterval=mount.clientWidth<620?48:32;
    if(t-lastDraw<frameInterval)return;
    lastDraw=t;
    const sec=(t-startAt)/1000;
    const slow=matchMedia('(prefers-reduced-motion: reduce)').matches;
    card.rotation.y=(viewMode==='back'?Math.PI:0)+(slow?-.19:Math.sin(sec*.63)*.18-.13);
    card.rotation.x=slow?-.06:-.075+Math.sin(sec*.53)*.055;
    card.position.y=2.15+(slow?0:Math.sin(sec*1.45)*.105);
    gem.rotation.y=sec*.9;
    for(let i=0;i<rings.length;i++)rings[i].rotation.z=slow?0:Math.sin(sec*.18+i*.8)*.038;
    renderer.render(scene,camera);frame++;
  }
  function start(){if(disposed)return;resize();if(running)return;running=true;lastDraw=0;startAt=performance.now();raf=requestAnimationFrame(tick);}
  function stop(){running=false;cancelAnimationFrame(raf);}
  function dispose(){
    if(disposed)return;stop();disposed=true;
    frontMaterial.map?.dispose();frontMaterial.dispose();
    back.material.map?.dispose();back.material.dispose();
    for(const m of [bevel,core,front,back,gem,...rails])m.geometry.dispose();
    gold.dispose();core.material.dispose();gem.material.dispose();
    for(const g of stageGeometries)g.dispose();
    for(const m of stageMats)m.dispose();
    mount.removeEventListener('pointerdown',onDown);
    mount.removeEventListener('pointermove',onMove);
    mount.removeEventListener('pointerup',onUp);
    mount.removeEventListener('pointercancel',onUp);
    mount.removeEventListener('wheel',onWheel);
    renderer.dispose();renderer.domElement.remove();
  }
  setCard(profile);
  return {start,stop,dispose,resize,setCard,setView,resetCamera,
    get state(){return {running,projection:camera.type,frameCount:frame,profile:{...profile},
      orbitRevision:43,orbitYaw,orbitPitch,orbitDistance,
      cardFlipRevision:40,viewMode,
      cardBackRevision:41,cardBackTextureReady:!!back.material.map?.image,
      cinematicLifecycleRevision:42,
      renderPixelRatio:renderer.getPixelRatio(),
      frameIntervalMs:mount.clientWidth<620?48:32,
      stageRevision:38,cardBindingRevision:39,stageMeshCount:stageObjects.length,
      castShadows:renderer.shadowMap.enabled,lightCount:5,
      meshes:6+rails.length+stageObjects.length,hasCanvas:renderer.domElement.isConnected};}};
};
