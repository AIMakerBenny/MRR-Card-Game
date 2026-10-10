/* Three.js presentation adapter for MARORONG CARD WAR Phase 21.
 * World units are CSS pixels and snapshots come only from the visible DOM.
 * No rules/state changes; no hidden-hand reads; pointer-events never captured.
 */
window.MCW3DSceneFactory = function createMCW3DScene(THREE, mount) {
  'use strict';
  const scene=new THREE.Scene();
  let width=innerWidth,height=innerHeight,last=0,raf=0,running=false,paused=false;
  const camera=new THREE.OrthographicCamera(0,width,height,0,-1500,1500);
  camera.position.set(width/2,height/2,1100);camera.lookAt(width/2,height/2,0);
  const renderer=new THREE.WebGLRenderer({alpha:true,antialias:true,powerPreference:'high-performance'});
  renderer.setClearColor(0x000000,0);
  renderer.setPixelRatio(Math.min(devicePixelRatio||1,1.5));
  renderer.setSize(width,height,false);
  renderer.outputColorSpace=THREE.SRGBColorSpace;
  renderer.toneMapping=THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure=1.12;
  renderer.domElement.setAttribute('aria-hidden','true');
  renderer.domElement.style.pointerEvents='none';
  mount.appendChild(renderer.domElement);
  const ambient=new THREE.AmbientLight(0xbed5d7,2.4);scene.add(ambient);
  const key=new THREE.DirectionalLight(0xffdaaa,2.3);
  key.position.set(width*.19,height*.96,650);scene.add(key);
  const fill=new THREE.PointLight(0x6cbcd1,34000,1900);
  fill.position.set(width*.82,height*.42,200);scene.add(fill);
  const cardGeometry=new THREE.BoxGeometry(1,1,1);
  const plateGeometry=new THREE.BoxGeometry(1,1,1);
  const entries=new Map();
  const effects=[];
  let effectsTriggered=0,lastClip=null;
  // Phase 25 - sparse, transparent battlefield dressing that mirrors the DOM
  // arena rectangle. It has no input or state authority.
  const arenaTrim=new THREE.Group();scene.add(arenaTrim);
  const rimGeo=new THREE.BoxGeometry(1,1,1);
  const rimMat=new THREE.MeshStandardMaterial({color:0x987b51,metalness:.75,roughness:.38,
    transparent:true,opacity:.065,depthWrite:false});
  const rimParts=Array.from({length:4},()=>{
    const m=new THREE.Mesh(rimGeo,rimMat);arenaTrim.add(m);return m;
  });
  const lightPools=[];
  for(const tone of ['cyan','amber']){
    // Each color requires its own backing canvas. Reusing a mutable canvas
    // makes both textures display the last painted gradient on first upload.
    const glowCanvas=document.createElement('canvas');
    glowCanvas.width=glowCanvas.height=128;
    const glowCtx=glowCanvas.getContext('2d');
    const g=glowCtx.createRadialGradient(64,64,4,64,64,64);
    g.addColorStop(0,tone==='cyan'?'rgba(55,170,180,.50)':'rgba(189,127,55,.37)');
    g.addColorStop(.6,tone==='cyan'?'rgba(35,95,117,.18)':'rgba(108,71,44,.15)');
    g.addColorStop(1,'rgba(0,0,0,0)');
    glowCtx.clearRect(0,0,128,128);glowCtx.fillStyle=g;glowCtx.fillRect(0,0,128,128);
    const tex=new THREE.CanvasTexture(glowCanvas);tex.colorSpace=THREE.SRGBColorSpace;
    const m=new THREE.Mesh(new THREE.PlaneGeometry(1,1),
      new THREE.MeshBasicMaterial({map:tex,transparent:true,depthWrite:false,opacity:.58,side:THREE.DoubleSide}));
    m.position.z=-72;arenaTrim.add(m);lightPools.push(m);
  }
  const reduced=matchMedia('(prefers-reduced-motion: reduce)');
  let observer=null,dirty=true,failed=false;
  function rectOf(node){const r=node.getBoundingClientRect();return {x:r.left+r.width/2,y:height-r.top-r.height/2,w:r.width,h:r.height};}
  function colorOf(kind){
    if(/영웅/.test(kind))return '#d2ad61';
    if(/마법|의식|전술/.test(kind))return '#9b80ca';
    if(/시설|함선|포탈/.test(kind))return '#88ac9d';
    if(/장비/.test(kind))return '#bfb0a1';
    if(/자원|보급/.test(kind))return '#6ec1c8';
    return '#c69a62';
  }
  function cardInfo(slot){
    const card=slot.querySelector('.board-card .card-ui');
    if(!card)return null;
    const get=(selector)=>card.querySelector(selector)?.textContent?.trim()||'';
    const status=slot.querySelector('.status-chip')?.textContent?.trim()||'';
    // Read only the public HP bar already visible on the field.
    const publicHp=slot.querySelector('.hpbar > div');
    const hpRaw=publicHp?Number.parseFloat(publicHp.style.width):NaN;
    const hpRatio=Number.isFinite(hpRaw)?Math.max(0,Math.min(1,hpRaw/100)):null;
    const name=get('.card-name'),kind=get('.card-kind')||card.className,
      cost=get('.cost-bubble'),stats=get('.card-stats'),sigil=get('.sigil-text');
    return {name,kind,cost,stats,sigil,status,hpRatio,signature:[name,kind,cost,stats,sigil,status].join('|')};
  }
  function rounded(ctx,x,y,w,h,r){
    const rr=Math.min(r,w/2,h/2);ctx.beginPath();ctx.moveTo(x+rr,y);ctx.lineTo(x+w-rr,y);
    ctx.quadraticCurveTo(x+w,y,x+w,y+rr);ctx.lineTo(x+w,y+h-rr);
    ctx.quadraticCurveTo(x+w,y+h,x+w-rr,y+h);ctx.lineTo(x+rr,y+h);
    ctx.quadraticCurveTo(x,y+h,x,y+h-rr);ctx.lineTo(x,y+rr);
    ctx.quadraticCurveTo(x,y,x+rr,y);ctx.closePath();
  }
  function fitText(ctx,value,maxWidth,baseSize,minSize){
    let size=baseSize;
    while(size>minSize){ctx.font=`bold ${size}px 'Malgun Gothic',sans-serif`;if(ctx.measureText(value).width<=maxWidth)break;size-=2;}
    ctx.font=`bold ${size}px 'Malgun Gothic',sans-serif`;
    if(ctx.measureText(value).width>maxWidth){while(value.length>2&&ctx.measureText(value+'…').width>maxWidth)value=value.slice(0,-1);value+='…';}
    return value;
  }
  // Phase 24 - visual-only heraldry. Never creates card types or game abilities.
  function sealFor(info){
    if(/영웅/.test(info.kind))return '♛';
    if(/함선/.test(info.kind))return '⚓';
    if(/시설|포탈/.test(info.kind))return '⌂';
    if(/마법|의식/.test(info.kind))return '✧';
    if(/장비/.test(info.kind))return '⚒';
    if(/자원|보급/.test(info.kind))return '◇';
    return '⚔';
  }

  // Phase29 procedural artwork. Uses a public card name/type as a stable seed;
  // does not fetch images, inspect hidden information or change card definitions.
  function illustrationKind(info){
    const s=info.kind+' '+info.name;
    if(/함선|배|해군|항해|선박|해적/.test(s))return 'ship';
    if(/시설|요새|성벽|탑|관문|포탈|성채/.test(s))return 'citadel';
    if(/마법|의식|마도|주술|정령|사제|치유/.test(s))return 'arcane';
    if(/자원|보급|광산|수정|보물|교역/.test(s))return 'crystal';
    return 'warrior';
  }
  function paintIllustration(c,info,accent){
    const category=illustrationKind(info);
    let seed=2166136261;
    for(const v of info.name+'|'+info.kind){seed=Math.imul(seed^v.charCodeAt(0),16777619)>>>0;}
    const random=()=>{seed^=seed<<13;seed^=seed>>>17;seed^=seed<<5;return (seed>>>0)/4294967296;};
    c.save();rounded(c,38,116,308,245,8);c.clip();
    const tones=category==='ship'?['#0d253d','#286078','#172d36']:
      category==='citadel'?['#292935','#585b61','#1b2c30']:
      category==='arcane'?['#211b40','#574985','#141d39']:
      category==='crystal'?['#153343','#34746b','#172b31']:['#3e2b34','#83634f','#1a2931'];
    const sky=c.createLinearGradient(35,116,300,361);
    sky.addColorStop(0,tones[0]);sky.addColorStop(.56,tones[1]);sky.addColorStop(1,tones[2]);
    c.fillStyle=sky;c.fillRect(38,116,308,245);
    c.save();c.globalAlpha=.55;c.fillStyle=category==='arcane'?'#bdc4f1':'#f6dca7';
    c.beginPath();c.arc(262+random()*26,164+random()*18,31+random()*15,0,Math.PI*2);c.fill();c.restore();
    for(let j=0;j<18;j++){
      c.globalAlpha=.15+random()*.42;c.fillStyle='#f9ebcc';
      c.fillRect(46+random()*285,125+random()*115,1.2+random()*1.7,1.2+random()*1.6);
    }
    c.globalAlpha=1;
    const mountains=(base,shade,top)=>{c.fillStyle=shade;c.beginPath();c.moveTo(38,363);
      for(let x=38;x<360;x+=27)c.lineTo(x,base-random()*top);
      c.lineTo(346,363);c.closePath();c.fill();};
    mountains(308,'#14242c',45);mountains(342,'#0d1b25',35);
    c.save();c.translate(187+random()*14,255+random()*14);
    c.fillStyle='#101925';c.strokeStyle=accent;c.lineWidth=3;
    if(category==='citadel'){
      c.fillRect(-70,-45,140,105);c.fillRect(-95,-68,42,128);c.fillRect(53,-68,42,128);
      c.fillRect(-34,-104,68,164);
      for(const x of [-86,-67,-28,-8,13,62,82])c.fillRect(x,-118+(Math.abs(x)>40?45:0),13,15);
      c.fillStyle='#d6ac6c';c.fillRect(-8,-62,17,24);c.fillRect(-71,-43,9,20);c.fillRect(61,-43,9,20);
      c.fillStyle='#080f17';c.beginPath();c.arc(0,60,22,Math.PI,0);c.fill();
    }else if(category==='ship'){
      c.fillStyle='#182a34';c.beginPath();c.moveTo(-126,12);c.lineTo(115,12);c.lineTo(78,59);c.lineTo(-83,59);c.closePath();c.fill();
      c.fillStyle='#ded1b2';c.beginPath();c.moveTo(-6,-116);c.lineTo(-4,4);c.lineTo(74,4);c.closePath();c.fill();
      c.fillStyle='#d4b28d';c.beginPath();c.moveTo(-13,-108);c.lineTo(-16,6);c.lineTo(-99,6);c.closePath();c.fill();
      c.strokeStyle='#c7ab79';c.beginPath();c.moveTo(-8,-126);c.lineTo(-8,20);c.stroke();
      c.strokeStyle='#a9d9dd';for(let w=0;w<3;w++){c.beginPath();c.moveTo(-110,69+w*8);c.quadraticCurveTo(0,58+w*8,106,70+w*8);c.stroke();}
    }else if(category==='arcane'){
      c.strokeStyle='#d8c1ff';c.lineWidth=6;c.beginPath();c.moveTo(0,-100);c.lineTo(0,62);c.stroke();
      c.strokeStyle='#a4e9ed';c.lineWidth=4;
      for(let i=0;i<3;i++){c.beginPath();c.ellipse(0,-77,44+i*15,17+i*8,i*.5,0,Math.PI*2);c.stroke();}
      c.fillStyle='#c9c0ff';c.beginPath();c.moveTo(0,-139);c.lineTo(35,-101);c.lineTo(0,-58);c.lineTo(-35,-101);c.closePath();c.fill();
      c.fillStyle='#17192b';c.beginPath();c.moveTo(-67,55);c.lineTo(-39,-47);c.lineTo(0,-83);c.lineTo(40,-47);c.lineTo(68,55);c.closePath();c.fill();
    }else if(category==='crystal'){
      for(let i=-2;i<=2;i++){const dx=i*37,h=67+random()*58;
        c.fillStyle=i%2?'#4eaa9e':'#a2ded1';c.beginPath();c.moveTo(dx,-h);c.lineTo(dx+23,-h*.62);c.lineTo(dx+28,48);c.lineTo(dx-26,48);c.lineTo(dx-20,-h*.62);c.closePath();c.fill();
        c.fillStyle='#173b50';c.beginPath();c.moveTo(dx,-h);c.lineTo(dx+23,-h*.62);c.lineTo(dx+28,48);c.closePath();c.fill();
      }
    }else{
      // Helmet, shield and sword silhouettes that remain legible at thumbnail size.
      c.fillStyle='#1c2730';c.beginPath();c.moveTo(-70,65);c.lineTo(-64,-10);c.lineTo(-33,-45);c.lineTo(39,-45);c.lineTo(68,-5);c.lineTo(72,65);c.closePath();c.fill();
      c.fillStyle='#e4d0a0';c.beginPath();c.arc(0,-56,37,Math.PI,0);c.lineTo(35,-40);c.lineTo(-35,-40);c.closePath();c.fill();
      c.fillStyle='#172027';c.fillRect(-39,-45,78,23);
      c.strokeStyle='#d9c99d';c.lineWidth=5;c.beginPath();c.moveTo(65,-113);c.lineTo(65,75);c.stroke();
      c.fillStyle='#ad8e67';c.beginPath();c.moveTo(-85,-15);c.lineTo(-20,3);c.lineTo(-30,74);c.lineTo(-88,42);c.closePath();c.fill();
      c.strokeStyle='#eee0b0';c.stroke();
    }
    c.restore();
    c.globalAlpha=.75;c.strokeStyle=accent;c.lineWidth=2;
    c.beginPath();c.moveTo(45,351);c.lineTo(338,351);c.stroke();
    c.restore();
    return category;
  }
  function textureFor(info){
    const cvs=document.createElement('canvas');cvs.width=384;cvs.height=538;
    const c=cvs.getContext('2d');const accent=colorOf(info.kind);
    const bg=c.createLinearGradient(0,0,384,538);bg.addColorStop(0,'#49534e');bg.addColorStop(.14,'#1a2b30');bg.addColorStop(.75,'#1c252b');bg.addColorStop(1,'#4b4639');
    c.fillStyle=bg;rounded(c,4,4,376,530,20);c.fill();
    c.strokeStyle=accent;c.lineWidth=10;rounded(c,9,9,366,520,18);c.stroke();
    c.strokeStyle='#efd69a';c.lineWidth=3;rounded(c,19,19,346,500,12);c.stroke();
    c.fillStyle='#0b1820';rounded(c,26,25,332,71,9);c.fill();
    c.fillStyle='#eee0c2';c.textAlign='center';c.textBaseline='middle';
    const title=fitText(c,info.name,280,35,20);c.fillText(title,207,58);
    c.fillStyle='#28648a';c.beginPath();c.arc(46,54,29,0,Math.PI*2);c.fill();
    c.strokeStyle='#e8d4aa';c.lineWidth=3;c.stroke();c.fillStyle='#fff4db';c.font='bold 30px sans-serif';c.fillText(info.cost||'0',46,54);
    const art=c.createLinearGradient(0,117,0,370);art.addColorStop(0,'#293e43');art.addColorStop(.56,'#304c4a');art.addColorStop(1,'#0c1c25');
    c.fillStyle=art;rounded(c,35,113,314,251,10);c.fill();c.strokeStyle=accent;c.lineWidth=2;c.stroke();
    // Unique source-free battlefield illustrations. No third-party media/license dependencies.
    paintIllustration(c,info,accent);
    // Small stamped heraldry remains visible without hiding the scene painting.
    c.save();c.globalAlpha=.88;
    c.fillStyle='#14232a';c.beginPath();c.arc(302,328,21,0,Math.PI*2);c.fill();
    c.strokeStyle=accent;c.lineWidth=3;c.stroke();
    c.fillStyle='#f3dfae';c.font='bold 21px Georgia,serif';c.textAlign='center';
    c.fillText(sealFor(info),302,329);c.restore();
    // Four inset filigree corners keep the card visually distinct at small sizes.
    c.save();c.strokeStyle='#d4b984af';c.lineWidth=3;
    for(const [x,y,dx,dy] of [[48,125,1,1],[336,125,-1,1],[48,351,1,-1],[336,351,-1,-1]]){
      c.beginPath();c.moveTo(x,y+dy*21);c.lineTo(x,y);c.lineTo(x+dx*21,y);c.stroke();
    }c.restore();
    c.fillStyle='#bdc9c8';c.font="19px 'Malgun Gothic',sans-serif";c.fillText(info.kind.replace(/·.*/,'' ).slice(0,12),192,390);
    c.fillStyle='#c0a874';c.fillRect(38,417,308,2);
    c.fillStyle='#f8edd8';c.font="bold 28px 'Malgun Gothic',sans-serif";c.fillText(info.stats||'전장 카드',192,460);
    // Raised cost/status trim and engraved bottom bands stay presentation-only.
    c.strokeStyle=accent;c.lineWidth=3;c.beginPath();c.moveTo(52,486);c.lineTo(332,486);c.stroke();
    c.fillStyle='#edd5a8';c.font='bold 14px sans-serif';c.fillText('MARORONG',192,507);
    if(info.status){c.fillStyle='#283a4b';rounded(c,231,105,120,28,7);c.fill();c.fillStyle='#fff2bd';c.font='bold 15px sans-serif';c.fillText(info.status.slice(0,12),291,119);}
    const texture=new THREE.CanvasTexture(cvs);texture.colorSpace=THREE.SRGBColorSpace;texture.anisotropy=Math.min(4,renderer.capabilities.getMaxAnisotropy());

    // Crop only the illustrated panel, never overlay name, cost or stat text.
    const artCrop=document.createElement('canvas');artCrop.width=308;artCrop.height=245;
    artCrop.getContext('2d').drawImage(cvs,35,113,314,251,0,0,308,245);
    texture.userData.artUrl=artCrop.toDataURL('image/png');
    return texture;
  }
  function restoreArt(e){
    if(!e.artWell)return;
    e.artWell.style.backgroundImage=e.artOriginal.backgroundImage;
    e.artWell.style.backgroundSize=e.artOriginal.backgroundSize;
    e.artWell.style.backgroundPosition=e.artOriginal.backgroundPosition;
    e.artWell=null;e.artOriginal=null;e.artURL=null;
  }
  function exposeArt(e,card){
    const well=card?.querySelector('.art-well');
    // Existing real illustrations are never replaced.
    if(!well||well.querySelector('img,video,picture,canvas')){restoreArt(e);return;}
    if(e.artWell!==well){
      restoreArt(e);
      e.artWell=well;
      e.artOriginal={backgroundImage:well.style.backgroundImage,
        backgroundSize:well.style.backgroundSize,backgroundPosition:well.style.backgroundPosition};
    }
    const art=e.front.material.map?.userData?.artUrl;
    if(art&&e.artURL!==art){well.style.backgroundImage='url("'+art+'")';
      well.style.backgroundSize='cover';well.style.backgroundPosition='center';e.artURL=art;}
  }
  function makeEntry(id){
    const group=new THREE.Group();scene.add(group);
    const plate=new THREE.Mesh(plateGeometry,new THREE.MeshStandardMaterial({color:0x627474,metalness:.47,roughness:.54,transparent:true,opacity:.24,depthWrite:false}));
    plate.position.z=2;group.add(plate);
    const edge=new THREE.Mesh(cardGeometry,[
      new THREE.MeshStandardMaterial({color:0xb79964,metalness:.76,roughness:.32}),
      new THREE.MeshStandardMaterial({color:0xb79964,metalness:.76,roughness:.32}),
      new THREE.MeshStandardMaterial({color:0xe3c58b,metalness:.74,roughness:.3}),
      new THREE.MeshStandardMaterial({color:0x67492d,metalness:.68,roughness:.45}),
      new THREE.MeshStandardMaterial({color:0x2b3437,metalness:.43,roughness:.55}),
      new THREE.MeshStandardMaterial({color:0x2b3437,metalness:.43,roughness:.55})
    ]);
    edge.position.z=10;group.add(edge);
    const front=new THREE.Mesh(new THREE.PlaneGeometry(1,1),new THREE.MeshBasicMaterial({color:0xffffff,side:THREE.FrontSide}));
    front.position.z=13.2;group.add(front);
    const shadow=new THREE.Mesh(new THREE.PlaneGeometry(1,1),new THREE.MeshBasicMaterial({color:0x000000,transparent:true,opacity:.28,depthWrite:false}));
    shadow.position.set(5,-8,4);group.add(shadow);
    // Phase27: visual-only health trim derives from the existing public DOM HP bar.
    // It never mutates HP and never reads hand/deck/hidden opponent information.
    const meterBg=new THREE.Mesh(new THREE.PlaneGeometry(1,1),
      new THREE.MeshBasicMaterial({color:0x18252a,transparent:true,opacity:.86,depthWrite:false}));
    const meterFill=new THREE.Mesh(new THREE.PlaneGeometry(1,1),
      new THREE.MeshBasicMaterial({color:0x7fe0a3,transparent:true,opacity:.95,depthWrite:false}));
    meterBg.position.z=18;meterFill.position.z=19;
    group.add(meterBg,meterFill);
    meterBg.visible=meterFill.visible=false;
    // The focus glow belongs to the visual card only, never to the original hit target.
    const halo=new THREE.Mesh(new THREE.RingGeometry(.68,.77,48),
      new THREE.MeshBasicMaterial({color:0xffe3a0,transparent:true,opacity:.68,side:THREE.DoubleSide,depthWrite:false}));
    halo.position.z=12.6;halo.visible=false;group.add(halo);
    const entry={id,group,plate,edge,front,shadow,halo,meterBg,meterFill,hpRatio:null,
      artWell:null,artOriginal:null,artURL:null,signature:null,hasCard:false,prevEffect:'',
      position:new THREE.Vector3(),lift:0,targetLift:0,hovered:false,selected:false};
    entries.set(id,entry);return entry;
  }
  function removeEntry(id){const e=entries.get(id);if(!e)return;
    restoreArt(e);
    e.front.material.map?.dispose();e.front.material.dispose();e.front.geometry.dispose();
    e.plate.material.dispose();e.edge.material.forEach(m=>m.dispose());
    e.shadow.material.dispose();e.shadow.geometry.dispose();
    e.halo.material.dispose();e.halo.geometry.dispose();
    for(const m of [e.meterBg,e.meterFill]){m.material.dispose();m.geometry.dispose();}
    scene.remove(e.group);entries.delete(id);}
  // Phase 26: predictable VFX only. No damage/healing/target calculations here.
  // A single game visual class starts a distinct material effect. Entries expire
  // promptly and each allocated geometry/material is disposed at completion.
  function effectAt(e,type){
    if(reduced.matches)return;
    const color=type==='fx-heal'?0x79eeb9:type==='fx-hit'?0xffa66b:0xe8c57b;
    const now=performance.now(),origin=e.position.clone();
    const ring=new THREE.Mesh(new THREE.RingGeometry(23,28,48),
      new THREE.MeshBasicMaterial({color,transparent:true,opacity:.74,side:THREE.DoubleSide,depthWrite:false}));
    ring.position.copy(origin);ring.position.z=36;
    scene.add(ring);effects.push({mesh:ring,born:now,duration:630,particle:false});
    const n=type==='fx-hit'?11:type==='fx-heal'?10:14;
    for(let i=0;i<n;i++){
      const theta=2*Math.PI*i/n+(type==='fx-summon'?.2:0);
      const mesh=new THREE.Mesh(new THREE.PlaneGeometry(4.5,10),
        new THREE.MeshBasicMaterial({color,transparent:true,opacity:.88,depthWrite:false,side:THREE.DoubleSide}));
      mesh.position.set(origin.x+Math.cos(theta)*8,origin.y+Math.sin(theta)*8,40);
      scene.add(mesh);
      const vx=type==='fx-hit'?Math.cos(theta)*74:type==='fx-heal'?Math.cos(theta)*19:Math.cos(theta)*42;
      const vy=type==='fx-hit'?Math.sin(theta)*65:type==='fx-heal'?65+i*3:Math.sin(theta)*40+18;
      effects.push({mesh,born:now,duration:type==='fx-heal'?840:620,particle:true,
        origin:mesh.position.clone(),vx,vy,spin:(i%2?1:-1)*2});
    }
    effectsTriggered++;
    while(effects.length>112){
      const old=effects.shift();scene.remove(old.mesh);
      old.mesh.geometry.dispose();old.mesh.material.dispose();
    }
  }
  function syncArena(){
    const node=document.querySelector('#arena');
    const r=node?.getBoundingClientRect();
    if(!r||r.width<160||r.height<100){arenaTrim.visible=false;return;}
    arenaTrim.visible=true;
    const cx=r.left+r.width/2,cy=height-r.top-r.height/2;
    const w=Math.max(0,r.width-24),h=Math.max(0,r.height-24);
    arenaTrim.position.set(cx,cy,-60);
    rimParts[0].position.set(0,h/2,0);rimParts[0].scale.set(w,2,2);
    rimParts[1].position.set(0,-h/2,0);rimParts[1].scale.set(w,2,2);
    rimParts[2].position.set(-w/2,0,0);rimParts[2].scale.set(2,h,2);
    rimParts[3].position.set(w/2,0,0);rimParts[3].scale.set(2,h,2);
    lightPools[0].position.set(0,-h*.23,0);
    lightPools[1].position.set(0,h*.23,0);
    for(const p of lightPools)p.scale.set(w*.85,h*.58,1);
  }
  function sync(){
    if(!running)return;
    const seen=new Set();
    const gameVisible=!document.querySelector('#gameScreen')?.classList.contains('hidden');
    renderer.domElement.style.display=gameVisible?'block':'none';
    if(!gameVisible){arenaTrim.visible=false;return;}
    syncArena();
    for(const slot of document.querySelectorAll('#enemyTerrace [data-slot],#fieldTable [data-slot],#myTerrace [data-slot]')){
      const id=slot.getAttribute('data-slot');if(!id)continue;seen.add(id);
      const r=rectOf(slot);if(r.w<10||r.h<10)continue;
      const e=entries.get(id)||makeEntry(id);
      e.position.set(r.x,r.y,6);e.group.position.copy(e.position);
      e.plate.scale.set(Math.min(r.w*.8,r.h*.74),Math.min(r.h*.83,r.w*.85),4);
      e.plate.material.color.set(slot.classList.contains('legal')?0x368e83:slot.classList.contains('attack-target')?0x9c723c:0x627474);
      const info=cardInfo(slot);
      const card=slot.querySelector('.board-card');
      // Empty slots are already painted by the accessible DOM arena.
      // Do not overlay translucent empty WebGL plates over row names or UI.
      e.plate.visible=!!info&&!!card;
      if(info&&card){
        const cr=rectOf(card);const cw=Math.max(26,cr.w),ch=Math.max(38,cr.h);
        e.hasCard=true;e.edge.visible=e.front.visible=e.shadow.visible=true;
        e.edge.scale.set(cw,ch,6);e.front.scale.set(cw-6,ch-7,1);e.shadow.scale.set(cw,ch,1);
        e.hpRatio=info.hpRatio;
        const showMeter=info.hpRatio!==null;
        e.meterBg.visible=e.meterFill.visible=showMeter;
        if(showMeter){
          const barWidth=Math.min(cw*.82,90),barHeight=3.5;
          const valueWidth=Math.max(.001,barWidth*info.hpRatio);
          const y=-ch*.5-5;
          e.meterBg.scale.set(barWidth,barHeight,1);e.meterBg.position.set(0,y,18);
          e.meterFill.scale.set(valueWidth,barHeight,1);
          e.meterFill.position.set(-barWidth*.5+valueWidth*.5,y,19);
          e.meterFill.material.color.set(info.hpRatio<=.25?0xf19b79:info.hpRatio<=.5?0xe8c17d:0x7fe0a3);
        }
        e.group.position.set(cr.x,cr.y,9);
        e.plate.position.set(r.x-cr.x,r.y-cr.y,-4);
        if(e.signature!==info.signature){
          e.front.material.map?.dispose();e.front.material.map=textureFor(info);
          e.front.material.needsUpdate=true;e.signature=info.signature;
          const accent=new THREE.Color(colorOf(info.kind));
          for(const idx of [0,1,2])e.edge.material[idx].color.copy(accent);
          e.halo.material.color.copy(accent);
        }
        exposeArt(e,card);
        const active=slot.classList.contains('selected-slot')||slot.classList.contains('attack-target');
        const hovered=slot.matches(':hover');
        e.hovered=hovered;e.selected=active;e.targetLift=hovered?18:active?10:0;
        e.halo.visible=hovered||active;
        e.halo.scale.set(cw*.75,ch*.75,1);
        e.halo.material.color.set(slot.classList.contains('attack-target')?0xffb66e:hovered?0xffdfa7:0x93e9d6);
      }else{
        restoreArt(e);
        e.signature=null;e.hasCard=false;e.edge.visible=e.front.visible=e.shadow.visible=false;
        e.lift=e.targetLift=0;e.hovered=e.selected=false;e.halo.visible=false;
        e.meterBg.visible=e.meterFill.visible=false;e.hpRatio=null;
        e.plate.position.set(0,0,0);e.group.position.set(r.x,r.y,3);
      }
      const fx=['fx-hit','fx-heal','fx-summon'].find(x=>slot.classList.contains(x))||'';
      if(fx&&fx!==e.prevEffect)effectAt(e,fx);
      e.prevEffect=fx;
    }
    for(const id of Array.from(entries.keys()))if(!seen.has(id))removeEntry(id);
    dirty=false;
  }
  function frame(t){
    if(!running||paused)return;
    raf=requestAnimationFrame(frame);
    if(t-last<32)return;last=t;
    if(innerWidth!==width||innerHeight!==height)resize();
    // Client rects can change on hover/scroll without mutating the slot subtree.
    sync();
    // Ease only the selected / hovered card out of the tabletop.
    // The DOM cards and every other 3D card keep their original slots.
    for(const e of entries.values()){
      if(!e.hasCard)continue;
      e.lift+=(e.targetLift-e.lift)*.28;
      if(Math.abs(e.targetLift-e.lift)<.1)e.lift=e.targetLift;
      e.group.position.z=9+e.lift;
      e.plate.position.z=-4-e.lift; // Keep the slot plate on the table.
      e.shadow.position.set(5+e.lift*.18,-8-e.lift*.25,4-e.lift);
      const yaw=e.hovered?.075:e.selected?-.075:0;
      e.edge.rotation.y=yaw;e.front.rotation.y=yaw;
      e.halo.material.opacity=e.hovered?.74:.5;
    }
    for(let i=effects.length-1;i>=0;i--){const fx=effects[i],pct=(t-fx.born)/fx.duration;
      if(pct>=1){scene.remove(fx.mesh);fx.mesh.geometry.dispose();fx.mesh.material.dispose();effects.splice(i,1);continue;}
      if(fx.particle){
        fx.mesh.position.x=fx.origin.x+fx.vx*pct;
        fx.mesh.position.y=fx.origin.y+fx.vy*pct;
        fx.mesh.rotation.z=pct*fx.spin;
        fx.mesh.scale.setScalar(Math.max(.2,1-pct*.7));
        fx.mesh.material.opacity=(1-pct)*.88;
      }else{
        fx.mesh.scale.setScalar(1+pct*2.4);
        fx.mesh.material.opacity=(1-pct)*.74;
      }
    }
    // Avoid rendering 3D embellishments over HUD, hand, menus and detail panel.
    // Clearing the whole transparent canvas first also prevents stale scenery
    // pixels after browser zoom or layout changes.
    renderer.setScissorTest(false);renderer.clear(true,true,true);
    const rect=document.querySelector('#arena')?.getBoundingClientRect();
    if(rect&&rect.width>100&&rect.height>80){
      const x=Math.max(0,Math.floor(rect.left)),y=Math.max(0,Math.floor(height-rect.bottom));
      const right=Math.min(width,Math.ceil(rect.right)),top=Math.min(height,Math.ceil(height-rect.top));
      const cw=Math.max(0,right-x),ch=Math.max(0,top-y);
      lastClip={x,y,w:cw,h:ch};
      if(cw>0&&ch>0){
        renderer.setScissor(x,y,cw,ch);renderer.setScissorTest(true);
        renderer.render(scene,camera);renderer.setScissorTest(false);
      }
    }else lastClip=null;
  }
  function resize(){width=innerWidth;height=innerHeight;
    camera.left=0;camera.right=width;camera.top=height;camera.bottom=0;
    camera.position.set(width/2,height/2,1100);camera.lookAt(width/2,height/2,0);camera.updateProjectionMatrix();
    key.position.set(width*.19,height*.96,650);fill.position.set(width*.82,height*.42,200);
    renderer.setPixelRatio(Math.min(devicePixelRatio||1,1.5));renderer.setSize(width,height,false);dirty=true;
  }
  function start(){
    if(running){paused=false;return;}
    running=true;paused=false;resize();
    observer=new MutationObserver(()=>{dirty=true;});
    for(const node of [document.querySelector('#arenaInner'),document.querySelector('#gameScreen')]){
      if(!node)continue;
      if(node.id==='gameScreen')observer.observe(node,{attributes:true,attributeFilter:['class']});
      else observer.observe(node,{childList:true,subtree:true,attributes:true,attributeFilter:['class']});
    }
    raf=requestAnimationFrame(frame);
  }
  function stop(){running=false;paused=false;cancelAnimationFrame(raf);observer?.disconnect();observer=null;
    for(const id of Array.from(entries.keys()))removeEntry(id);
    for(const fx of effects){scene.remove(fx.mesh);fx.mesh.geometry.dispose();fx.mesh.material.dispose();}effects.length=0;
    renderer.clear();
  }
  function pause(){paused=true;cancelAnimationFrame(raf);}
  function resume(){if(running&&paused){paused=false;raf=requestAnimationFrame(frame);}}
  function dispose(){
    stop();
    for(const p of lightPools){p.geometry.dispose();p.material.map.dispose();p.material.dispose();}
    rimGeo.dispose();rimMat.dispose();renderer.dispose();renderer.domElement.remove();
  }
  renderer.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();stop();
    document.body.classList.remove('mcw-three-ready');document.body.classList.add('mcw-depth-fallback');
    const button=document.querySelector('#mcw3d-toggle');if(button)button.textContent='입체 모드';
    const status=document.querySelector('#mcw3d-status');if(status){status.textContent='WebGL 연결이 끊겨 CSS 입체 모드로 전환했습니다.';status.classList.add('active');}
  });
  return {start,stop,pause,resume,resize,dispose,get state(){
    const active=Array.from(entries.values()).filter(e=>e.hasCard);
    return {running,paused,cardCount:active.length,slotCount:entries.size,
      illustrationRevision:29,
      proceduralArtCards:active.filter(e=>e.front.material.map?.image&&e.signature).length,
      visibleDomArtCards:active.filter(e=>e.artWell&&e.artWell.isConnected).length,
      proceduralArtProfiles:active.filter(e=>e.hasCard).map(e=>({slot:e.id,profile:illustrationKind(cardInfo(document.querySelector('[data-slot="'+e.id+'"]'))||{kind:'',name:''})})),
      hoveredCardCount:active.filter(e=>e.hovered).length,
      liftedCardCount:active.filter(e=>e.lift>3).length,
      maxLift:active.reduce((max,e)=>Math.max(max,e.lift),0),
      maxTargetLift:active.reduce((max,e)=>Math.max(max,e.targetLift),0),
      focusedSlot:active.find(e=>e.hovered)?.id||null,
      decoratedCards:active.filter(e=>e.front.material.map&&e.signature).length,
      publicHealthMeterCount:active.filter(e=>e.meterFill.visible).length,
      visibleHealthRatios:active.filter(e=>e.meterFill.visible).map(e=>({slot:e.id,ratio:e.hpRatio})),
      healthMeterRevision:27,
      frameRevision:24,battlefieldRevision:25,
      battlefieldTrimCount:arenaTrim.visible?rimParts.length:0,
      battlefieldLightPoolCount:arenaTrim.visible?lightPools.length:0,
      visualFxRevision:26,visualFxTriggered:effectsTriggered,
      activeVisualMeshes:effects.length,renderClip:lastClip};
  }};
};
