/* Phase 47: full-board perspective 3D with delegated native input and visual interaction.
 * Source of truth is the visible HTML board. No game state, hidden hand, AI,
 * combat rules, localStorage, or original click targets are read or modified.
 */
window.MRRBattlefieldFactory=function(THREE,mount,events){
  'use strict';
  events=events||{};
  // Phase55: use a dedicated art direction only in the main PC gameplay view.
  // The older 3D modal and authoritative HTML engine remain unchanged.
  const tabletop=mount.id==='mrr-integrated-stage';
  const vrMode=tabletop&&document.body.classList.contains('mrr-vr-active');
  const scene=new THREE.Scene();
  scene.background=new THREE.Color(vrMode?0x0b2024:tabletop?0x261a15:0x080f1a);
  scene.fog=new THREE.FogExp2(vrMode?0x0b2024:tabletop?0x261a15:0x080f1a,tabletop?.008:.018);
  const camera=new THREE.PerspectiveCamera(vrMode?40:44,1,.1,130);
  const renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:'high-performance'});
  renderer.outputColorSpace=THREE.SRGBColorSpace;
  renderer.toneMapping=THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure=vrMode?1.06:tabletop?1.22:1.47;
  renderer.shadowMap.enabled=true;
  renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  renderer.domElement.setAttribute('aria-label','실시간 공개 카드 3D 전장');
  renderer.domElement.style.cssText='width:100%;height:100%;display:block';
  mount.appendChild(renderer.domElement);
  scene.add(new THREE.HemisphereLight(vrMode?0xb6d8d2:tabletop?0xffe5c3:0xbad8e8,vrMode?0x1b3539:tabletop?0x49301f:0x423440,tabletop?2.4:2.0));
  const sun=new THREE.DirectionalLight(vrMode?0xc4dacc:tabletop?0xffe1b1:0xffe2b1,tabletop?3.3:4.2);
  sun.position.set(-8,18,13);sun.castShadow=true;
  sun.shadow.mapSize.set(2048,2048);
  sun.shadow.camera.left=-22;sun.shadow.camera.right=22;
  sun.shadow.camera.top=22;sun.shadow.camera.bottom=-22;
  scene.add(sun);
  const enemyLamp=new THREE.PointLight(tabletop?0xecb67b:0xf06b65,tabletop?52:80,29);
  enemyLamp.position.set(0,3,-9.5);scene.add(enemyLamp);
  const friendlyLamp=new THREE.PointLight(tabletop?0xc5d0b0:0x51cdea,tabletop?50:95,29);
  friendlyLamp.position.set(0,3,9.5);scene.add(friendlyLamp);

  const madeGeometry=[],madeMaterials=[],madeTextures=[];
  const material=(options,physical=false)=>{
    const m=physical?new THREE.MeshPhysicalMaterial(options):new THREE.MeshStandardMaterial(options);
    madeMaterials.push(m);return m;
  };
  const geometry=g=>{madeGeometry.push(g);return g;};

  // Phase55: deterministic offline textures; no downloaded artwork, network,
  // hidden-card access or extra render pass. Each texture is shared for the
  // entire main tabletop and is disposed when the scene closes.
  const tabletopTextures=[];
  function tabletopTexture(kind){
    const c=document.createElement('canvas'),n=1024;
    c.width=c.height=n;
    const ctx=c.getContext('2d',{alpha:false});
    const pix=ctx.createImageData(n,n);
    let seed=kind==='wood'?991827:555137;
    const rand=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
    for(let y=0;y<n;y++){
      const plank=kind==='wood'?Math.floor(y/145):0;
      const seam=kind==='wood'?Math.min(y%145,145-y%145):100;
      for(let x=0;x<n;x++){
        const k=(y*n+x)*4,noise=(rand()-.5)*23;
        if(kind==='parchment'&&vrMode){
          const grain=Math.sin(x*.051+y*.011)*2.8+Math.cos(y*.037)*2.6;
          pix.data[k]=Math.max(0,26+noise*.22+grain);
          pix.data[k+1]=Math.max(0,53+noise*.22+grain);
          pix.data[k+2]=Math.max(0,57+noise*.22+grain);
        }else if(kind==='wood'){
          const grain=Math.sin(x*.083+Math.sin(y*.028)*3.4)*6+
            Math.sin(x*.012+y*.035)*4;
          const knot=((plank*17)%7)*2;
          const dark=seam<3?22:seam<6?12:0;
          pix.data[k]=Math.max(0,83+grain+noise-dark-knot);
          pix.data[k+1]=Math.max(0,51+grain*.7+noise*.65-dark);
          pix.data[k+2]=Math.max(0,31+grain*.45+noise*.4-dark);
        }else{
          const e=Math.min(x,y,n-1-x,n-1-y)/(n*.18);
          const burn=38*Math.pow(1-Math.min(1,e),2);
          const paper=3*Math.sin(y*.012+x*.004)+2*Math.sin(x*.021-y*.009);
          pix.data[k]=Math.max(0,232+noise*.55+paper-burn*.8);
          pix.data[k+1]=Math.max(0,211+noise*.67+paper-burn);
          pix.data[k+2]=Math.max(0,173+noise*.8+paper-burn*1.3);
        }
        pix.data[k+3]=255;
      }
    }
    ctx.putImageData(pix,0,0);
    if(kind==='parchment'&&!vrMode){
      // Hand-drawn, low-contrast atlas: cartographic circles, compass rays,
      // border filigree and opposing zones. Slot hit targets live above it.
      ctx.save();ctx.strokeStyle='rgba(86,58,40,.24)';ctx.lineWidth=3;
      ctx.strokeRect(28,28,968,968);ctx.strokeRect(42,42,940,940);
      for(let i=0;i<4;i++){
        const offset=63+i*8;
        ctx.strokeRect(offset,offset,n-offset*2,n-offset*2);
      }
      ctx.strokeStyle='rgba(97,69,43,.12)';ctx.lineWidth=2;
      for(let i=1;i<6;i++){
        const y=95+i*138;
        ctx.beginPath();ctx.moveTo(100,y);ctx.lineTo(924,y);ctx.stroke();
      }
      const cx=n/2,cy=n/2;
      for(const rad of [104,146,204,252]){
        ctx.beginPath();ctx.arc(cx,cy,rad,0,Math.PI*2);ctx.stroke();
      }
      ctx.lineWidth=2.5;ctx.strokeStyle='rgba(113,79,47,.24)';
      for(let i=0;i<24;i++){
        const a=i*Math.PI/12;
        ctx.beginPath();
        ctx.moveTo(cx+Math.cos(a)*106,cy+Math.sin(a)*106);
        ctx.lineTo(cx+Math.cos(a)*(i%2?154:198),cy+Math.sin(a)*(i%2?154:198));
        ctx.stroke();
      }
      ctx.strokeStyle='rgba(108,76,43,.25)';
      for(const [x,y] of [[100,100],[924,100],[100,924],[924,924]]){
        for(const r of [10,19,28]){
          ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.stroke();
        }
      }
      ctx.lineWidth=3;ctx.strokeStyle='rgba(129,81,60,.20)';
      ctx.beginPath();ctx.moveTo(55,514);ctx.lineTo(968,514);ctx.stroke();
      ctx.restore();
    }
    const tex=new THREE.CanvasTexture(c);
    tex.colorSpace=THREE.SRGBColorSpace;tex.anisotropy=8;
    if(kind==='wood'){
      tex.wrapS=tex.wrapT=THREE.RepeatWrapping;
      tex.repeat.set(6,6);
    }
    tabletopTextures.push(tex);return tex;
  }
  const woodSurface=tabletop?material({map:tabletopTexture('wood'),color:0xffffff,roughness:.83}):null;
  const parchmentSurface=tabletop?material({map:tabletopTexture('parchment'),color:0xffffff,roughness:.98}):null;
  // VR01 has no constant, loudly outlined empty cells. Slot pick meshes are
  // retained and raycastable; only their passive appearance changes.
  const vrGround=vrMode?material({color:0x12282d,roughness:.94,metalness:.06}):null;
  const woodEdge=tabletop?material({color:0x51301d,roughness:.82}):null;
  // Phase69: quiet but readable physical placement beds. Distinguish the
  // two publicly visible territories without adding GUI panels or cards.
  // These are non-textured, non-interactive materials; no hidden data.
  const allySlot=tabletop?material({color:0x497b79,roughness:.94,transparent:true,opacity:vrMode?.008:.16}):null;
  const enemySlot=tabletop?material({color:0x946451,roughness:.94,transparent:true,opacity:vrMode?.008:.16}):null;
  const parchmentInk=tabletop?material({color:vrMode?0x6d9992:0x80603b,roughness:.9,transparent:true,opacity:vrMode?.005:.20}):null;
  // Pick meshes are invisible to the GPU but remain fully raycastable in VR.
  // Transparent depth-writing tiles otherwise cut 30 black holes in terrain.
  const vrSlotHitMaterial=vrMode?material({color:0xffffff,transparent:true,
    opacity:0,depthWrite:false,colorWrite:false}):null;
  const softZone=tabletop?material({color:0x9a7150,metalness:.25,roughness:.77}):null;

  const black=material({color:0x223746,metalness:.18,roughness:.72});
  const stone=material({color:0x354957,metalness:.18,roughness:.71});
  const bronze=material({color:0xc6a777,metalness:.68,roughness:.29,clearcoat:.4},true);
  const gold=material({color:0xebc789,metalness:.58,roughness:.3});
  const red=material({color:0xcf6c6a,metalness:.32,roughness:.39,emissive:0x7a2529,emissiveIntensity:.48});
  const blue=material({color:0x64b9cc,metalness:.32,roughness:.36,emissive:0x0a647b,emissiveIntensity:.5});
  const tileGeo=geometry(new THREE.BoxGeometry(2.25,tabletop?.025:.15,2.45));
  const edgeGeo=geometry(new THREE.BoxGeometry(2.38,tabletop?.023:.08,2.58));
  const platformGeo=geometry(new THREE.BoxGeometry(22,.65,22.1));
  const floor=new THREE.Mesh(geometry(new THREE.PlaneGeometry(180,180)),tabletop?woodSurface:black);
  if(vrMode)floor.material=vrGround;
  floor.rotation.x=-Math.PI/2;floor.position.y=-.52;floor.receiveShadow=true;scene.add(floor);
  const platform=new THREE.Mesh(platformGeo,vrMode?vrGround:tabletop?woodEdge:stone);
  platform.position.y=-.22;platform.receiveShadow=true;scene.add(platform);
  if(tabletop){
    const sheet=new THREE.Mesh(geometry(new THREE.PlaneGeometry(21.95,21.94)),parchmentSurface);
    sheet.rotation.x=-Math.PI/2;sheet.position.y=.113;
    sheet.receiveShadow=true;scene.add(sheet);
  }
  const border=new THREE.Mesh(geometry(new THREE.BoxGeometry(22.45,.17,22.55)),vrMode?stone:bronze);
  border.position.y=-.58;scene.add(border);
  for(const sx of [-1,1]){
    const rail=new THREE.Mesh(geometry(new THREE.BoxGeometry(.17,.24,22.2)),gold);
    rail.position.set(sx*11.01,.18,0);scene.add(rail);
    for(const sz of [-1,1]){
      if(tabletop){
        const candle=new THREE.Group();candle.position.set(sx*11.8,0,sz*11.8);
        const foot=new THREE.Mesh(geometry(new THREE.CylinderGeometry(.68,.75,.22,18)),bronze);
        foot.position.y=.24;candle.add(foot);
        const wax=new THREE.Mesh(geometry(new THREE.CylinderGeometry(.35,.38,.94,16)),
          material({color:0xefdfb5,roughness:.88}));
        wax.position.y=.79;wax.castShadow=true;candle.add(wax);
        const flame=new THREE.Mesh(geometry(new THREE.ConeGeometry(.15,.43,11)),
          material({color:0xffe6a1,emissive:0xffb84e,emissiveIntensity:2.2,roughness:.4}));
        flame.position.y=1.50;candle.add(flame);scene.add(candle);continue;
      }
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
  // Small dimensional tabletop props fill the unused PC desktop margins.
  // Purely decorative; they never enter the board raycaster or game state.
  if(tabletop&&!vrMode){
    const leather=material({color:0x533022,roughness:.75,metalness:.08});
    const paper=material({color:0xe3c9a0,roughness:.95});
    const ink=material({color:0x242622,roughness:.26,metalness:.35});
    for(let i=0;i<3;i++){
      const book=new THREE.Group();
      book.position.set(-15+i*.12,-.12+i*.28,-1.8-i*.12);
      book.rotation.y=-.17+i*.085;
      const cover=new THREE.Mesh(geometry(new THREE.BoxGeometry(4.3,.22,5.5)),leather);
      cover.castShadow=true;book.add(cover);
      const pages=new THREE.Mesh(geometry(new THREE.BoxGeometry(4,.14,5.14)),paper);
      pages.position.y=.16;pages.castShadow=true;book.add(pages);
      const spine=new THREE.Mesh(geometry(new THREE.BoxGeometry(.25,.27,5.6)),bronze);
      spine.position.set(-2.04,.09,0);book.add(spine);
      scene.add(book);
    }
    const inkwell=new THREE.Group();
    inkwell.position.set(15.5,.1,2.35);
    const cup=new THREE.Mesh(geometry(new THREE.CylinderGeometry(.64,.73,1.12,22)),ink);
    cup.position.y=.46;cup.castShadow=true;inkwell.add(cup);
    const rim=new THREE.Mesh(geometry(new THREE.TorusGeometry(.62,.1,10,30)),bronze);
    rim.rotation.x=-Math.PI/2;rim.position.y=1.04;inkwell.add(rim);
    const quill=new THREE.Mesh(geometry(new THREE.CylinderGeometry(.017,.065,3.0,8)),
      material({color:0xd3b78b,roughness:.62}));
    quill.position.set(.39,1.88,-.06);quill.rotation.z=-.36;
    inkwell.add(quill);scene.add(inkwell);
    const compass=new THREE.Group();compass.position.set(16.0,.2,-4.2);
    const compassBase=new THREE.Mesh(geometry(new THREE.CylinderGeometry(.96,.96,.13,36)),bronze);
    compass.add(compassBase);
    const dial=new THREE.Mesh(geometry(new THREE.CylinderGeometry(.81,.81,.14,36)),paper);
    dial.position.y=.13;compass.add(dial);
    const needle=new THREE.Mesh(geometry(new THREE.BoxGeometry(.13,.08,1.27)),leather);
    needle.position.y=.24;needle.rotation.y=.55;compass.add(needle);
    scene.add(compass);
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
  const raycaster=new THREE.Raycaster();
  const pointer=new THREE.Vector2();
  const slotPickMeshes=[];
  const selectGlow=material({color:0xffdb83,emissive:0xb87518,emissiveIntensity:1.6,metalness:.22,roughness:.25});
  const legalGlow=material({color:0x8dffe8,emissive:0x29bb9b,emissiveIntensity:1.4,metalness:.15,roughness:.35});
  const attackGlow=material({color:0xffaf66,emissive:0xe65d20,emissiveIntensity:1.85,metalness:.15,roughness:.35});
  const hoverGlow=material({color:0xffffff,emissive:0xc9a66b,emissiveIntensity:.9,metalness:.18,roughness:.33});
  const glowGeo=geometry(new THREE.TorusGeometry(1.04,.07,8,48));
  // Phase73: secondary, physically separate golden focus ring on PC only.
  // Render-only mesh: it is deliberately absent from slotPickMeshes.
  const pcFocusGeo=tabletop?geometry(new THREE.TorusGeometry(1.32,.055,8,48)):null;
  // Occupied-card staging is tied to PUBLIC mesh lifetimes. Empty legal
  // positions remain an unobstructed physical arena, never thirty boxes.
  const vrSeatSurface=vrMode?geometry(new THREE.BoxGeometry(2.54,.12,2.64)):null;
  const vrSeatEdge=vrMode?geometry(new THREE.BoxGeometry(2.66,.035,2.76)):null;
  const vrSeatBase=vrMode?material({color:0x132c30,metalness:.43,roughness:.59}):null;
  const vrSeatFriendly=vrMode?material({color:0x7ebbb1,metalness:.48,roughness:.37,
    emissive:0x174947,emissiveIntensity:.33}):null;
  const vrSeatEnemy=vrMode?material({color:0xc49a79,metalness:.48,roughness:.39,
    emissive:0x56342d,emissiveIntensity:.32}):null;
  const cardGeometry=geometry(new THREE.BoxGeometry(tabletop?2.22:2.08,2.84,.22));
  const cardFaceGeometry=geometry(new THREE.PlaneGeometry(tabletop?2.10:1.96,2.71));
  // Phase57: dimensional gilt trims are scenery, not selectable meshes.
  const pcGilt=tabletop?material({color:0xc49c62,metalness:.73,roughness:.26,emissive:0x251406}):null;
  const pcSide=tabletop?geometry(new THREE.BoxGeometry(.046,2.89,.075)):null;
  const pcEnd=tabletop?geometry(new THREE.BoxGeometry(2.23,.046,.075)):null;
  // Phase52: public-health display floats above each card, never reads G.
  const healthBackGeo=geometry(new THREE.BoxGeometry(2.18,.22,.075));
  const healthFillGeo=geometry(new THREE.BoxGeometry(2.04,.15,.084));
  const statusGeo=geometry(new THREE.SphereGeometry(.135,12,8));
  const healthBackMat=material({color:0x061820,emissive:0x0d2a31,emissiveIntensity:.4});
  const healthHealthyMat=material({color:0x76f0c6,emissive:0x17bd8c,emissiveIntensity:.78});
  const healthWarnMat=material({color:0xf7c46b,emissive:0xdb8a24,emissiveIntensity:.9});
  const healthDangerMat=material({color:0xff7771,emissive:0xe54444,emissiveIntensity:1});
  const readyMat=material({color:0x96e9ff,emissive:0x1875c2,emissiveIntensity:.7});
  const actedMat=material({color:0x708090,emissive:0x1f2c32,emissiveIntensity:.25});
  const wardMat=material({color:0xffe39e,emissive:0xf2ba53,emissiveIntensity:.75});
  const stripGeo=geometry(new THREE.BoxGeometry(19.5,.025,.045));
  for(const lane of lanes){
    const laneMaterial=tabletop?softZone:(lane.owner===0?blue:red);
    const laneBorder=new THREE.Mesh(stripGeo,laneMaterial);
    laneBorder.position.set(0,tabletop?.15:.17,lane.z-1.36);
    if(!vrMode)scene.add(laneBorder);
    for(let col=0;col<5;col++){
      const x=(col-2)*3.37;
      const inset=new THREE.Mesh(edgeGeo,tabletop?parchmentInk:bronze);inset.position.set(x,tabletop?.134:.15,lane.z);
      inset.receiveShadow=!vrMode;if(vrMode)inset.visible=false;scene.add(inset);
      const base=new THREE.Mesh(tileGeo,vrMode?vrSlotHitMaterial:tabletop?(lane.owner===0?allySlot:enemySlot):black);base.position.set(x,tabletop?.156:.23,lane.z);
      base.receiveShadow=!vrMode;scene.add(base);
      const key=lane.owner+':'+lane.row+':'+col;
      base.userData.mrrSlotKey=key;slotPickMeshes.push(base);
      const halo=new THREE.Mesh(glowGeo,legalGlow);
      halo.rotation.x=-Math.PI/2;halo.position.set(x,tabletop?.24:.38,lane.z);
      halo.visible=false;scene.add(halo);
      const focusRing=tabletop?new THREE.Mesh(pcFocusGeo,selectGlow):null;
      if(focusRing){
        focusRing.rotation.x=-Math.PI/2;
        focusRing.position.set(x,.29,lane.z);
        focusRing.visible=false;scene.add(focusRing);
      }
      const crest=new THREE.Mesh(geometry(new THREE.TorusGeometry(.5,.035,7,32)),tabletop?parchmentInk:laneMaterial);
      crest.rotation.x=-Math.PI/2;crest.position.set(x,tabletop?.175:.32,lane.z);
      if(vrMode)crest.visible=false;scene.add(crest);
      boardSlots.set(key,{x,z:lane.z,owner:lane.owner,row:lane.row,col,base,halo,focusRing});
    }
  }
  // VR01-B: the game world is an arena, not a 30-box grid. These physical
  // surfaces are never added to pickMeshes, and all 30 original coordinates
  // remain exactly where the Phase21 renderer expects them.
  if(vrMode){
    const enemyInk=material({color:0x976b5b,roughness:.76,metalness:.11,transparent:true,opacity:.23});
    const allyInk=material({color:0x73b4a6,roughness:.72,metalness:.13,transparent:true,opacity:.25});
    const brassInlay=material({color:0xb9a57b,metalness:.61,roughness:.35,transparent:true,opacity:.65});
    const emboss=material({color:0x19373e,roughness:.66,metalness:.4});
    // Two distinct territorial fabrics and three subtly carved paths per
    // side. The background is generated geometrically, not supplied card art.
    for(const [owner,tint] of [[1,[94,52,55]],[0,[25,95,92]]]){
      const surface=document.createElement('canvas');
      surface.width=1024;surface.height=512;
      const c=surface.getContext('2d');
      const wash=c.createLinearGradient(0,0,0,512);
      const rgba=(alpha)=>'rgba('+tint.join(',')+','+alpha+')';
      wash.addColorStop(0,rgba('.03'));
      wash.addColorStop(.26,rgba('.44'));
      wash.addColorStop(.75,rgba('.39'));
      wash.addColorStop(1,rgba('.03'));
      c.fillStyle=wash;c.fillRect(0,0,1024,512);
      // Wide woven strips imply physical ranks, without outlining empty cells.
      for(let i=0;i<3;i++){
        const cy=84+i*169;
        const lane=c.createLinearGradient(0,cy-56,0,cy+56);
        lane.addColorStop(0,'rgba(230,221,188,0)');
        lane.addColorStop(.5,'rgba(216,224,195,.055)');
        lane.addColorStop(1,'rgba(230,221,188,0)');
        c.fillStyle=lane;c.fillRect(25,cy-57,974,114);
        c.lineWidth=1;c.strokeStyle='rgba(207,199,172,.11)';
        c.beginPath();c.moveTo(45,cy-74);c.lineTo(979,cy-74);c.stroke();
        // Stone direction markers, symmetric but unobtrusive.
        for(const side of [-1,1]){
          const x=side<0?47:977;
          c.fillStyle='rgba(209,192,154,.30)';
          c.beginPath();c.moveTo(x,cy-10);
          c.lineTo(x-side*11,cy);c.lineTo(x,cy+10);c.closePath();c.fill();
        }
      }
      // Fine diagonal fabric fibers are batched into one texture.
      c.strokeStyle='rgba(242,231,207,.045)';c.lineWidth=1;
      for(let x=-512;x<1500;x+=26){
        c.beginPath();c.moveTo(x,0);c.lineTo(x+512,512);c.stroke();
      }
      const tex=new THREE.CanvasTexture(surface);
      tex.colorSpace=THREE.SRGBColorSpace;tex.anisotropy=4;
      // Long-lived terrain belongs to scene resources, not per-card textures.
      tabletopTextures.push(tex);
      const mat=material({map:tex,transparent:true,depthWrite:false,roughness:.84,
        metalness:.08,side:THREE.DoubleSide});
      const carpet=new THREE.Mesh(geometry(new THREE.PlaneGeometry(20.72,10.05)),mat);
      carpet.rotation.x=-Math.PI/2;
      carpet.position.set(0,.129,owner===1?-5.54:5.54);
      scene.add(carpet);
    }
    // The center emblem visually divides territories. All it does is reflect
    // existing world ownership; combat simulation and pathing never read it.
    const medallion=new THREE.Group();
    medallion.position.set(0,.155,0);
    const disc=new THREE.Mesh(geometry(new THREE.CylinderGeometry(1.11,1.16,.048,64)),emboss);
    disc.position.y=.04;medallion.add(disc);
    for(const radius of [1.23,.93]){
      const ring=new THREE.Mesh(geometry(new THREE.TorusGeometry(radius,.045,8,80)),brassInlay);
      ring.rotation.x=-Math.PI/2;ring.position.y=.087;medallion.add(ring);
    }
    for(let i=0;i<8;i++){
      const a=i*Math.PI/4;
      const stud=new THREE.Mesh(geometry(new THREE.BoxGeometry(.075,.028,.23)),brassInlay);
      stud.rotation.y=-a;stud.position.set(Math.sin(a)*1.05,.094,Math.cos(a)*1.05);
      medallion.add(stud);
    }
    scene.add(medallion);
    // Lanes are engraved on the physical side edge, not empty slot frames.
    for(const lane of lanes){
      const ally=lane.owner===0;
      const m=ally?allyInk:enemyInk;
      for(const side of [-1,1]){
        const block=new THREE.Mesh(geometry(new THREE.BoxGeometry(.64,.035,1.62)),m);
        block.position.set(side*9.92,.145,lane.z);scene.add(block);
        const dot=new THREE.Mesh(geometry(new THREE.CylinderGeometry(.075,.075,.023,18)),brassInlay);
        dot.position.set(side*9.92,.188,lane.z);scene.add(dot);
      }
    }
    // A thin metallic fracture between two territories, below every card.
    const borderline=new THREE.Mesh(geometry(new THREE.BoxGeometry(20.5,.014,.07)),brassInlay);
    borderline.position.set(0,.155,0);scene.add(borderline);
  }
  const attackArrowGeo=geometry(new THREE.BufferGeometry());
  attackArrowGeo.setAttribute('position',new THREE.BufferAttribute(new Float32Array(6),3));
  const attackArrowMat=new THREE.LineBasicMaterial({color:0xffc074,transparent:true,opacity:.95});
  madeMaterials.push(attackArrowMat);
  const attackArrow=new THREE.Line(attackArrowGeo,attackArrowMat);
  attackArrow.visible=false;scene.add(attackArrow);
  const attackTip=new THREE.Mesh(geometry(new THREE.ConeGeometry(.28,.69,10)),attackGlow);
  attackTip.visible=false;scene.add(attackTip);
  const center=new THREE.Mesh(geometry(new THREE.BoxGeometry(21,.035,.1)),tabletop?parchmentInk:gold);
  center.position.y=.19;scene.add(center);
  const seal=new THREE.Mesh(geometry(new THREE.TorusGeometry(1.06,.055,8,80)),tabletop?parchmentInk:bronze);
  seal.rotation.x=-Math.PI/2;seal.position.y=.23;scene.add(seal);
  const sealCore=new THREE.Mesh(geometry(new THREE.OctahedronGeometry(.45)),tabletop?softZone:gold);
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
      const fill=el.querySelector('.board-card .hpbar > div');
      const pct=fill?Number.parseFloat(fill.style.width):NaN;
      const chip=el.querySelector('.board-card .status-chip')?.textContent?.trim()||'';
      return {key,cardId:card?.getAttribute('data-mrr-public-card-id')||null,
        selected:el.classList.contains('selected-slot'),
        legal:el.classList.contains('legal'),attackTarget:el.classList.contains('attack-target'),
        name:card?.querySelector('.card-name')?.textContent?.trim()||'',
        kind:card?.querySelector('.card-kind')?.textContent?.trim()||'',
        cost:card?.querySelector('.cost-bubble')?.textContent?.trim()||'',
        stats:card?.querySelector('.card-stats')?.textContent?.trim()||'',
        sigil:card?.querySelector('.sigil-text')?.textContent?.trim()||'',
        hasHealth:!!fill,hpRatio:fill&&Number.isFinite(pct)?Math.max(0,Math.min(1,pct/100)):null,
        stateChip:chip};
    }).filter(Boolean);
  }

  // Phase51: deterministic original illustrated art, no external images or
  // hidden game data. Each public card's name and kind select a coherent
  // illustration silhouette, with a stable per-card palette and atmosphere.

  // Phase57: render-only engravings from publicly visible card text.
  function pc57Engrave(c,p,ally,pass){
    let seed=2166136261;
    for(const ch of String(p.name||''))seed=Math.imul(seed^ch.charCodeAt(0),16777619)>>>0;
    const rng=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
    const info=String(p.kind||'')+' '+String(p.name||'');
    const fort=/시설|성소|병영|성채|전초|기지|탑|제단|대성당|연구소/.test(info);
    const ship=/함선|해적선|범선|전함|항구|수병/.test(info);
    const mage=/마법|마도|술사|성녀|사제|치유|엘리온|의식/.test(info);
    const archer=/궁병|석궁|사수|저격|총|활/.test(info);
    const beast=/야수|늑대|곰|용|도마뱀|뱀파이어|흡혈|괴물|쥐인/.test(info);
    const hue=[38,185,212,275,145,10][seed%6],a='hsla('+hue+',83%,75%,';
    const ink=ally?'#edd7ab':'#eac4ac';
    const line=(pts,color,width)=>{c.beginPath();c.moveTo(pts[0][0],pts[0][1]);
      for(let i=1;i<pts.length;i++)c.lineTo(pts[i][0],pts[i][1]);
      c.strokeStyle=color;c.lineWidth=width;c.stroke();};
    c.save();
    if(pass==='landscape'){
      const sun=c.createRadialGradient(260,315,6,260,315,225);
      sun.addColorStop(0,a+'.38)');sun.addColorStop(1,a+'0)');
      c.fillStyle=sun;c.fillRect(56,200,399,318);
      for(let i=0;i<34;i++){
        c.fillStyle=a+(rng()*.24+.09).toFixed(2)+')';
        c.beginPath();c.ellipse(60+rng()*392,216+rng()*270,.7+rng()*2,1+rng()*3,0,0,7);c.fill();
      }
      if(fort){
        for(let i=0;i<7;i++){
          const x=63+i*56,ht=38+rng()*57;
          c.fillStyle='#101c21a5';c.fillRect(x,458-ht,18,ht);
          c.beginPath();c.moveTo(x-5,458-ht);c.lineTo(x+9,439-ht);
          c.lineTo(x+23,458-ht);c.closePath();c.fill();
          line([[x+5,455-ht],[x+5,448-ht]],'#e3bb78b0',2);
        }
      }else if(ship){
        for(let i=0;i<12;i++){
          const y=400+i*10;c.beginPath();c.moveTo(56,y);
          c.bezierCurveTo(147,y-19,297,y+18,458,y-7);
          c.strokeStyle=i%2?'#8aebf545':'#e7daa737';c.lineWidth=1.4;c.stroke();
        }
      }else if(mage){
        for(let i=0;i<4;i++){
          c.beginPath();c.arc(260,379,90+i*26,Math.PI*.06,Math.PI*1.86);
          c.strokeStyle=a+(.52-i*.09).toFixed(2)+')';c.lineWidth=1.5;c.stroke();
        }
        for(let i=0;i<13;i++){
          const t=i*Math.PI*2/13,r=136+(i%3)*14;
          const x=260+Math.cos(t)*r,y=379+Math.sin(t)*r*.78;
          line([[x-5,y],[x+5,y],[x,y-10]],a+'.52)',1.5);
        }
      }else if(archer){
        for(let i=0;i<8;i++)line([[58,315+i*24],[443,202+i*24]],'#d9f9e430',2);
      }else if(beast){
        for(let i=0;i<7;i++){
          const x=65+i*55,y=275+(i%2)*28;
          for(let j=0;j<3;j++)line([[x+j*10,y],[x+j*10+17,y+54]],'#e4b39e51',2);
        }
      }else{
        for(let i=0;i<5;i++){
          const x=83+i*81,y=283+rng()*40;
          c.fillStyle='#091926a9';c.fillRect(x,y,10,156);
          c.beginPath();c.moveTo(x+9,y);c.lineTo(x+50,y+11);
          c.lineTo(x+9,y+42);c.closePath();c.fillStyle='#edd7ab67';c.fill();
        }
      }
    }else if(pass==='frame'){
      c.lineWidth=7;c.strokeStyle='#1d120b';c.strokeRect(25,25,462,655);
      c.lineWidth=2;c.strokeStyle=ink+'a9';c.strokeRect(32,31,448,642);
      for(const [x,y] of [[37,36],[475,36],[37,668],[475,668]]){
        c.fillStyle='#5e3824';c.beginPath();c.arc(x,y,5,0,7);c.fill();
        c.fillStyle='#ffe2a4';c.beginPath();c.arc(x-1,y-1,2.1,0,7);c.fill();
      }
      for(let i=0;i<7;i++){
        const yy=69+i*12;
        line([[43,yy],[46,yy+4],[43,yy+8]],ink+'70',1.4);
        line([[469,yy],[466,yy+4],[469,yy+8]],ink+'70',1.4);
      }
      // Original archetype insignia in a small lower-right bronze medallion.
      const x=430,y=626,disk=c.createRadialGradient(x-5,y-7,2,x,y,27);
      disk.addColorStop(0,'#f3dda1');disk.addColorStop(.48,'#a67843');disk.addColorStop(1,'#322921');
      c.beginPath();c.arc(x,y,23,0,7);c.fillStyle=disk;c.fill();
      c.strokeStyle='#f8e3b7';c.lineWidth=2;c.beginPath();c.arc(x,y,17,0,7);c.stroke();
      c.translate(x,y);
      if(fort){c.strokeRect(-7,-7,14,15);line([[-12,-8],[0,-15],[12,-8]],'#f7eaca',2);}
      else if(ship){line([[-13,3],[11,3],[7,11],[-7,11]],'#f7eaca',2);line([[0,2],[0,-13],[9,2]],'#f7eaca',2);}
      else if(mage){for(let i=0;i<3;i++){c.rotate(Math.PI*2/3);line([[0,-12],[4,-3],[0,3]],'#f7eaca',2);}}
      else if(archer)line([[-8,10],[8,-10],[-1,-7],[8,-10],[9,0]],'#f7eaca',2);
      else if(beast){for(let i=-1;i<=1;i++)line([[i*7-4,-11],[i*7+4,12]],'#f7eaca',2);}
      else line([[0,-13],[4,-3],[2,13],[-2,13],[-4,-3],[0,-13]],'#f7eaca',2);
    }
    c.restore();
  }

  // Phase58: reserve an exact 5:4 400x320 pixel window for user-supplied artwork.
  // The master artwork size is 1200x960 px. This surface stays genuinely blank
  // until the owner supplies images. The standalone 3D modal is unchanged.
  const pcArtSlot={x:56,y:199,width:400,height:320,sourceWidth:1200,sourceHeight:960};
  function drawPcBlankArtwork(c){
    c.save();
    c.fillStyle='#2b3335';
    c.fillRect(pcArtSlot.x,pcArtSlot.y,pcArtSlot.width,pcArtSlot.height);
    c.strokeStyle='#857455';c.lineWidth=2;
    c.strokeRect(pcArtSlot.x-1,pcArtSlot.y-1,pcArtSlot.width+2,pcArtSlot.height+2);
    c.restore();
  }
  function drawCardIllustration(c,profile,ally){
    if(tabletop){drawPcBlankArtwork(c);return 'blank-art-slot';}
    let hash=2166136261;
    for(const ch of profile.name){hash=Math.imul(hash^ch.charCodeAt(0),16777619)>>>0;}
    const types=profile.kind+' '+profile.name;
    const building=/시설|성소|병영|성채|전초|기지|탑|제단|대성당|연구소/.test(types);
    const ranged=/궁병|석궁|사수|저격|총|활/.test(types);
    const magic=/마법|마도|술사|성녀|사제|치유|엘리온|의식/.test(types);
    const nautical=/함선|해적선|범선|전함|항구|수병/.test(types);
    const beast=/야수|늑대|곰|용|도마뱀|뱀파이어|흡혈|괴물|쥐인/.test(types);
    const palettes=[
      ['#163f59','#3a6573','#d9a979','#e8ddd2'],
      ['#442d50','#945d7c','#ebac77','#e9d0b9'],
      ['#263e36','#68856e','#ddbc7d','#cedfcd'],
      ['#293f55','#61749c','#f1c489','#b6ddec'],
      ['#533b32','#a16b43','#f5c57d','#e3d9c6'],
      ['#323b61','#7b70b0','#dfb9a0','#dee4fa']
    ];
    const colors=palettes[hash%palettes.length],sky=colors[0],haze=colors[1],golden=colors[2],steel=colors[3];
    c.save();
    c.beginPath();c.rect(55,199,402,319);c.clip();
    const skyGrad=c.createLinearGradient(0,200,0,520);
    skyGrad.addColorStop(0,sky);skyGrad.addColorStop(.59,haze);skyGrad.addColorStop(1,'#081924');
    c.fillStyle=skyGrad;c.fillRect(55,198,402,321);
    // Luminous moon and atmospheric radiance are created procedurally.
    const moonX=315+(hash%61)-28,moonY=271+((hash>>>7)%24);
    const aura=c.createRadialGradient(moonX,moonY,7,moonX,moonY,127);
    aura.addColorStop(0,golden+'bb');aura.addColorStop(.32,golden+'43');aura.addColorStop(1,golden+'00');
    c.fillStyle=aura;c.fillRect(110,199,350,280);
    c.fillStyle=golden+'e1';c.beginPath();c.arc(moonX,moonY,26,0,Math.PI*2);c.fill();
    for(let i=0;i<24;i++){
      const x=65+((hash+i*133)%375),y=205+((hash+i*79)%188),r=i%4===0?2.1:1;
      c.fillStyle=steel+'a5';c.beginPath();c.arc(x,y,r,0,Math.PI*2);c.fill();
    }
    // Mountains, towers, and arches establish scale around the subject.
    for(let layer=0;layer<3;layer++){
      const bottom=465+layer*21;
      c.fillStyle=[sky+'b7','#152e3fc4','#0a1d30ee'][layer];
      c.beginPath();c.moveTo(52,540);
      for(let k=0;k<8;k++)c.lineTo(48+k*61,bottom-((hash+k*67+layer*17)%52));
      c.lineTo(480,540);c.closePath();c.fill();
    }
    c.strokeStyle=golden+'80';c.lineWidth=2;
    for(let i=0;i<3;i++){
      c.beginPath();c.arc(256,391,119+i*21,Math.PI*1.02,Math.PI*1.97);c.stroke();
    }
    if(tabletop)pc57Engrave(c,profile,ally,'landscape');
    c.save();c.translate(256,410);
    // Keep large recognisable silhouettes rather than tiny undecipherable symbols.
    if(building){
      c.fillStyle='#091b2b';c.fillRect(-80,-51,160,130);
      c.fillStyle=steel;c.beginPath();c.moveTo(-96,-52);c.lineTo(0,-139);c.lineTo(96,-52);c.closePath();c.fill();
      for(const x of [-66,66]){
        c.fillStyle='#152637';c.fillRect(x-19,-100,38,179);
        c.fillStyle=golden;c.fillRect(x-23,-105,46,10);
        for(let y=-76;y<57;y+=35){c.fillStyle=golden+'a8';c.fillRect(x-8,y,16,22);}
      }
      c.fillStyle=golden;c.beginPath();c.arc(0,-31,24,0,7);c.fill();
      c.fillStyle='#081925';c.fillRect(-21,5,42,80);
      c.strokeStyle=golden;c.lineWidth=5;c.strokeRect(-78,-48,156,131);
    }else if(nautical){
      c.fillStyle='#071725';c.beginPath();c.moveTo(-145,24);c.lineTo(143,24);c.lineTo(90,88);c.lineTo(-94,88);c.closePath();c.fill();
      c.strokeStyle=golden;c.lineWidth=7;c.beginPath();c.moveTo(-5,32);c.lineTo(-5,-147);c.stroke();
      c.fillStyle=steel;c.beginPath();c.moveTo(0,-136);c.lineTo(122,12);c.lineTo(0,12);c.closePath();c.fill();
      c.fillStyle=golden+'dc';c.beginPath();c.moveTo(-12,-101);c.lineTo(-112,20);c.lineTo(-12,20);c.closePath();c.fill();
      c.strokeStyle='#a9eced';c.lineWidth=2;
      for(let y=70;y<104;y+=12){c.beginPath();c.moveTo(-185,y);c.quadraticCurveTo(-70,y-10,12,y);c.quadraticCurveTo(90,y+10,184,y);c.stroke();}
    }else{
      // Caped figure, layered shoulders and plated cuirass.
      c.fillStyle='#09141f';c.beginPath();c.moveTo(0,-76);c.lineTo(-120,84);c.lineTo(117,84);c.closePath();c.fill();
      c.fillStyle=beast?'#5a3a41':'#4e6171';
      c.beginPath();c.moveTo(-74,-37);c.quadraticCurveTo(0,-92,70,-38);
      c.lineTo(99,73);c.lineTo(-92,73);c.closePath();c.fill();
      c.fillStyle=steel;c.beginPath();c.ellipse(-65,-29,35,25,-.4,0,7);c.fill();
      c.beginPath();c.ellipse(65,-29,35,25,.4,0,7);c.fill();
      c.fillStyle='#101f29';c.beginPath();c.roundRect(-45,-56,90,123,20);c.fill();
      c.strokeStyle=golden;c.lineWidth=5;c.strokeRect(-31,-45,62,102);
      c.fillStyle=golden;c.beginPath();c.arc(0,5,19,0,7);c.fill();
      c.fillStyle='#101923';c.beginPath();c.arc(0,5,11,0,7);c.fill();
      c.fillStyle=steel;c.beginPath();c.ellipse(0,-88,35,43,0,0,7);c.fill();
      c.fillStyle='#0c1e30';c.beginPath();c.moveTo(-33,-95);c.lineTo(0,-135);
      c.lineTo(33,-95);c.lineTo(24,-74);c.lineTo(-24,-74);c.closePath();c.fill();
      if(beast){
        c.fillStyle=golden;c.beginPath();c.moveTo(-34,-107);c.lineTo(-64,-147);c.lineTo(-17,-126);c.closePath();c.fill();
        c.beginPath();c.moveTo(34,-107);c.lineTo(64,-147);c.lineTo(17,-126);c.closePath();c.fill();
      }
      c.fillStyle=golden;c.fillRect(-21,-92,13,5);c.fillRect(9,-92,13,5);
      if(magic){
        c.strokeStyle=golden;c.lineWidth=8;c.beginPath();c.moveTo(104,72);c.lineTo(103,-137);c.stroke();
        c.fillStyle='#92eaf0';c.beginPath();c.arc(103,-140,18,0,7);c.fill();
        for(let k=0;k<7;k++){c.strokeStyle='#b4f4ff88';c.lineWidth=2;c.beginPath();c.arc(103,-139,24+k*7,0,7);c.stroke();}
      }else if(ranged){
        c.strokeStyle=golden;c.lineWidth=9;c.beginPath();c.arc(98,-27,63,-1.42,1.42);c.stroke();
        c.strokeStyle='#e7edf2';c.lineWidth=2;c.beginPath();c.moveTo(108,-89);c.lineTo(108,35);c.stroke();
        c.strokeStyle=steel;c.lineWidth=5;c.beginPath();c.moveTo(18,-22);c.lineTo(135,-29);c.stroke();
      }else{
        c.strokeStyle=golden;c.lineWidth=8;c.beginPath();c.moveTo(91,68);c.lineTo(98,-155);c.stroke();
        c.fillStyle=steel;c.beginPath();c.moveTo(98,-163);c.lineTo(86,-127);c.lineTo(111,-128);c.closePath();c.fill();
        c.strokeStyle='#e9eff4';c.lineWidth=3;c.beginPath();c.moveTo(100,-135);c.lineTo(96,-70);c.stroke();
      }
    }
    c.restore();
    const under=c.createLinearGradient(0,450,0,523);
    under.addColorStop(0,'#07152300');under.addColorStop(1,'#071523ed');
    c.fillStyle=under;c.fillRect(55,448,402,75);
    // Thin technical corner ornament, preserving an open illustration center.
    c.strokeStyle=golden+'cd';c.lineWidth=3;
    for(const [x,y,sx,sy] of [[63,208,1,1],[448,208,-1,1],[63,510,1,-1],[448,510,-1,-1]]){
      c.beginPath();c.moveTo(x,y+sy*28);c.lineTo(x,y);c.lineTo(x+sx*28,y);c.stroke();
    }
    c.restore();
    return building?'fortress':nautical?'ship':magic?'mage':ranged?'archer':beast?'beast':'warrior';
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
    c.fillStyle='#f6e3b6';c.font=tabletop?'bold 43px sans-serif':'bold 37px sans-serif';
    c.fillText(profile.name.slice(0,24),262,96,365);
    c.fillStyle='#aacdcd';c.font=tabletop?'bold 27px sans-serif':'22px sans-serif';
    c.fillText(profile.kind.slice(0,30),260,163,425);
    const archetype=drawCardIllustration(c,profile,ally);
    c.fillStyle='#0a1927';c.fillRect(52,542,408,112);
    c.strokeStyle='#c9aa70';c.lineWidth=3;c.strokeRect(52,542,408,112);
    c.fillStyle='#dce9e6';c.font=tabletop?'bold 29px sans-serif':'bold 23px sans-serif';
    c.fillText(profile.stats.slice(0,42)||'공개 전장 카드',256,597,380);
    c.fillStyle='#ead7ac';c.font=tabletop?'bold 27px sans-serif':'bold 24px sans-serif';
    c.fillText(ally?'ALLY':'OPPONENT',256,630);
    c.fillStyle='#102637';c.beginPath();c.arc(58,92,31,0,Math.PI*2);c.fill();
    c.strokeStyle='#efcd89';c.lineWidth=5;c.stroke();
    c.fillStyle='#ffffff';c.font=tabletop?'bold 37px sans-serif':'bold 33px sans-serif';
    c.fillText(profile.cost.slice(0,3),58,96);
    if(tabletop)pc57Engrave(c,profile,ally,'frame');
    const texture=new THREE.CanvasTexture(canvas);
    texture.userData.artArchetype=archetype;
    texture.userData.artPhase=tabletop?57:51;
    texture.userData.artLoaded=false;
    if(tabletop){
      // Match the exact public name/type/faction shown on the already-rendered
      // card. Do not inspect the hidden decks, opponent hand, or native G.
      const lookup=window.MRRCardArtRegistry;
      const id=profile.cardId;
      const known=typeof id==='string'&&lookup?.knownIds?.includes(id);
      const src=known?lookup?.assets?.[id]:null;
      texture.userData.artId=known?id:null;
      if(typeof src==='string'&&/^data:image\/(png|jpeg);base64,/.test(src)){
        const img=new Image();
        img.onload=()=>{
          if(disposed||texture.userData.artDisposed)return;
          if(img.naturalWidth!==pcArtSlot.sourceWidth||img.naturalHeight!==pcArtSlot.sourceHeight)return;
          c.drawImage(img,pcArtSlot.x,pcArtSlot.y,pcArtSlot.width,pcArtSlot.height);
          texture.userData.artLoaded=true;
          texture.needsUpdate=true;
          const item=cardIndex.get(profile.key);
          if(item?.face.material.map===texture)item.previewUrl=null;
        };
        img.onerror=()=>{texture.userData.artLoadFailed=true;};
        img.src=src;
      }
    }
    texture.colorSpace=THREE.SRGBColorSpace;texture.anisotropy=4;
    madeTextures.push(texture);return texture;
  }
  // Phase49: camera/lighting react only after a native FX transition.
  // A target click can stage a trajectory but cannot itself trigger an impact.
  const impactLamp=new THREE.PointLight(0xffffff,0,17,2);
  impactLamp.position.set(0,2,0);scene.add(impactLamp);
  let pendingStrike=null,cinemaImpact=null,confirmedStrikes=0,cinematicFrameCount=0;
  let vrHitReactions=0,vrLandingDustStarted=0;
  const vrLandingDust=[];
  let latestCombat=null;
  const nativeCombatEvents=[];
  function stageAttack(sourceKey,targetKey){
    if(!boardSlots.has(sourceKey)||!boardSlots.has(targetKey)||sourceKey===targetKey)return false;
    pendingStrike={sourceKey,targetKey,at:performance.now()};
    return true;
  }
  function cinematicLight(type,key,at){
    const spot=boardSlots.get(key);
    impactLamp.position.set(spot.x,2.5,spot.z);
    impactLamp.color.set(type==='hit'?0xffa775:type==='heal'?0x90ffca:0x7de4ff);
    cinemaImpact={type,key,at};
    latestCombat={type,key,at};
  }
  function advanceCinematics(now){
    if(pendingStrike&&now-pendingStrike.at>2800)pendingStrike=null;
    if(!cinemaImpact){impactLamp.intensity=0;return;}
    const p=(now-cinemaImpact.at)/(cinemaImpact.type==='hit'?540:880);
    if(p>=1){
      cinemaImpact=null;impactLamp.intensity=0;updateCamera();return;
    }
    const envelope=Math.max(0,1-p);
    impactLamp.intensity=(cinemaImpact.type==='hit'?110:75)*Math.pow(envelope,2);
    if(!matchMedia('(prefers-reduced-motion: reduce)').matches){
      // This transient offset is never written into the camera orbit state.
      updateCamera();
      const shake=(cinemaImpact.type==='hit'?.21:.045)*envelope;
      camera.position.x+=Math.sin(now*.119)*shake;
      camera.position.y+=Math.cos(now*.151)*shake*.7;
      camera.lookAt(focusX,.8,focusZ);
      cinematicFrameCount++;
    }
  }
  // Phase48: CSS effects are emitted by the unmodified original game.
  // Observe only real native fx-* class transitions, never compute damage or healing.
  const liveEffects=[],effectsReceived={hit:0,heal:0,summon:0};
  let peakLiveFxCount=0;
  const recentFx=new Map();
  const effectColors={hit:0xffa96e,heal:0x7affbd,summon:0x69d8ef};
  const fxObserver=new MutationObserver(records=>{
    if(disposed)return;
    for(const record of records){
      if(record.type!=='attributes'||record.attributeName!=='class')continue;
      const node=record.target;
      if(!(node instanceof Element)||!node.matches('#arena [data-slot]'))continue;
      const key=node.getAttribute('data-slot');
      if(!boardSlots.has(key))continue;
      for(const type of ['hit','heal','summon']){
        if(!node.classList.contains('fx-'+type))continue;
        // Even multiple DOM writes in a single native frame are one visible effect.
        const stamp=key+'|'+type,now=performance.now();
        if(now-(recentFx.get(stamp)||-9999)<95)continue;
        recentFx.set(stamp,now);
        triggerNativeFx(type,key,now);
      }
    }
  });
  function triggerNativeFx(type,key,now){
    const spot=boardSlots.get(key);
    if(!spot||!Object.prototype.hasOwnProperty.call(effectColors,type))return;
    const radius=type==='summon'?1.12:type==='heal'?.92:.78;
    const colour=effectColors[type];
    const group=new THREE.Group();
    group.position.set(spot.x,.48,spot.z);
    const ringGeo=new THREE.TorusGeometry(radius,.055,8,64);
    const ringMat=new THREE.MeshBasicMaterial({color:colour,transparent:true,opacity:.88,depthWrite:false});
    const ring=new THREE.Mesh(ringGeo,ringMat);
    ring.rotation.x=-Math.PI/2;group.add(ring);
    const sparkCount=type==='hit'?36:28;
    const coords=new Float32Array(sparkCount*3),velocity=new Float32Array(sparkCount*3);
    for(let i=0;i<sparkCount;i++){
      const theta=i*2.39996323;
      const spread=.5+.5*((i*29)%17)/16;
      velocity[i*3]=Math.cos(theta)*spread*(type==='hit'?4.2:2.6);
      velocity[i*3+1]=(type==='heal'?2.4:3.1)+((i*7)%11)*.24;
      velocity[i*3+2]=Math.sin(theta)*spread*(type==='hit'?4.2:2.6);
    }
    const sparkGeo=new THREE.BufferGeometry();
    sparkGeo.setAttribute('position',new THREE.BufferAttribute(coords,3));
    const sparkMat=new THREE.PointsMaterial({color:colour,size:type==='hit'?.15:.13,
      transparent:true,opacity:1,depthWrite:false});
    group.add(new THREE.Points(sparkGeo,sparkMat));
    const beaconGeo=new THREE.IcosahedronGeometry(type==='hit'?.40:.26,1);
    const beaconMat=new THREE.MeshBasicMaterial({color:colour,transparent:true,opacity:.64,depthWrite:false});
    const beacon=new THREE.Mesh(beaconGeo,beaconMat);
    beacon.position.y=1.2;group.add(beacon);
    scene.add(group);
    cinematicLight(type,key,now);
    // VR01F: a card visibly recoils ONLY after the original game actually
    // emits fx-hit, never on mouse hover, speculative click or targeting.
    // The original Phase76 3D presentation is untouched.
    if(vrMode&&type==='hit'){
      const victim=cardIndex.get(key);
      if(victim&&!victim.deploy){
        const from=pendingStrike?.targetKey===key?boardSlots.get(pendingStrike.sourceKey):null;
        const dx=spot.x-(from?.x??spot.x+.4),dz=spot.z-(from?.z??spot.z+1);
        const length=Math.hypot(dx,dz)||1;
        victim.hitReaction={born:now,dx:dx/length,dz:dz/length};
        vrHitReactions++;
      }
    }
    // Attack vectors originate from the player's actual delegated selection.
    // The beam is committed only when the original engine emits fx-hit.
    const strike=type==='hit'&&pendingStrike?.targetKey===key &&
      now-pendingStrike.at<2800?pendingStrike:null;
    if(strike){
      const source=boardSlots.get(strike.sourceKey),delta=new THREE.Vector3(source.x-spot.x,0,source.z-spot.z);
      const origin=new THREE.Vector3(delta.x,1.3,delta.z),end=new THREE.Vector3(0,1.3,0);
      const vec=new THREE.Vector3().subVectors(end,origin),length=vec.length();
      for(const [width,alpha] of [[.19,.32],[.055,.9]]){
        const beamGeo=new THREE.CylinderGeometry(width,width,length,10);
        const beamMat=new THREE.MeshBasicMaterial({color:0xffddac,transparent:true,opacity:alpha,
          blending:THREE.AdditiveBlending,depthWrite:false});
        const beam=new THREE.Mesh(beamGeo,beamMat);
        beam.position.copy(origin).add(end).multiplyScalar(.5);
        beam.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),vec.normalize());
        group.add(beam);
        group.userData.beams||=[];group.userData.beams.push(beam);
        group.userData.beamResources||=[];group.userData.beamResources.push(beamGeo,beamMat);
      }
      confirmedStrikes++;pendingStrike=null;
    }
    // Soft additive volumetric core creates readable summon/heal silhouettes.
    const columnGeo=new THREE.CylinderGeometry(type==='hit'?.45:.16,
      type==='hit'?.65:.34,type==='hit'?1.6:3.8,16,1,true);
    const columnMat=new THREE.MeshBasicMaterial({color:colour,transparent:true,
      opacity:type==='hit'?.42:.32,depthWrite:false,side:THREE.DoubleSide,
      blending:THREE.AdditiveBlending});
    const column=new THREE.Mesh(columnGeo,columnMat);
    column.position.y=type==='hit'?.7:1.9;
    group.add(column);group.userData.column=column;
    group.userData.columnResources=[columnGeo,columnMat];
    const life=type==='summon'?1150:type==='heal'?1040:820;
    liveEffects.push({type,key,group,ring,sparkGeo,sparkMat,beacon,
      velocity,born:now,life,resources:[ringGeo,ringMat,sparkGeo,sparkMat,beaconGeo,beaconMat,...(group.userData.beamResources||[]),...(group.userData.columnResources||[])]});
    peakLiveFxCount=Math.max(peakLiveFxCount,liveEffects.length);
    effectsReceived[type]++;
    const combatEntry={type,key,name:document.querySelector('#arena [data-slot="'+key+'"] .card-name')?.textContent?.trim()||'',at:now,confirmedStrike:!!strike};
    nativeCombatEvents.push(combatEntry);
    if(nativeCombatEvents.length>12)nativeCombatEvents.shift();
    events.onCombat?.(combatEntry);
    while(liveEffects.length>24)removeFx(liveEffects.shift());
  }
  function removeFx(fx){
    scene.remove(fx.group);
    for(const res of fx.resources)res.dispose();
  }
  // Ground-contact dust is triggered only after a confirmed Phase21 hand
  // placement actually FINISHES its 3D arrival. Not a second summon event.
  // No rings, click surfaces or extra canvas textures.
  function spawnVrLandingDust(slot,at){
    if(!vrMode||matchMedia('(prefers-reduced-motion: reduce)').matches)return;
    const count=18,coords=new Float32Array(count*3),velocity=new Float32Array(count*3);
    for(let i=0;i<count;i++){
      const angle=i*2.399963229728653,spread=.45+(i%5)*.085;
      velocity[i*3]=Math.cos(angle)*spread*2.6;
      velocity[i*3+1]=.45+(i%4)*.16;
      velocity[i*3+2]=Math.sin(angle)*spread*2.6;
    }
    const geo=new THREE.BufferGeometry();
    geo.setAttribute('position',new THREE.BufferAttribute(coords,3));
    const mat=new THREE.PointsMaterial({color:slot.owner===0?0x9fc4b9:0xc0a18b,
      size:.14,transparent:true,opacity:.68,depthWrite:false,sizeAttenuation:true});
    const points=new THREE.Points(geo,mat);
    points.position.set(slot.x,.35,slot.z);scene.add(points);
    vrLandingDust.push({points,geo,mat,velocity,born:at,life:520});
    vrLandingDustStarted++;
  }
  function advanceVrLandingDust(now){
    for(let i=vrLandingDust.length-1;i>=0;i--){
      const f=vrLandingDust[i],p=Math.max(0,(now-f.born)/f.life);
      if(p>=1){
        scene.remove(f.points);f.geo.dispose();f.mat.dispose();vrLandingDust.splice(i,1);continue;
      }
      const pos=f.geo.attributes.position;
      for(let j=0;j<f.velocity.length/3;j++){
        const k=j*3;
        pos.setXYZ(j,f.velocity[k]*p,
          f.velocity[k+1]*p-.35*p*p,
          f.velocity[k+2]*p);
      }
      pos.needsUpdate=true;f.mat.opacity=Math.pow(1-p,1.6)*.68;
    }
  }
  function advanceEffects(now){
    for(let i=liveEffects.length-1;i>=0;i--){
      const f=liveEffects[i],p=Math.max(0,(now-f.born)/f.life);
      if(p>=1){removeFx(f);liveEffects.splice(i,1);continue;}
      const ease=Math.sin(Math.PI*p);
      f.ring.scale.setScalar(.7+p*1.55);
      if(f.group.userData.column){
        const column=f.group.userData.column;
        column.material.opacity=(1-p)*(f.type==='hit'?.44:.36);
        column.scale.x=column.scale.z=.65+Math.sin(Math.PI*p)*.58;
        column.scale.y=.8+Math.sin(Math.PI*p)*.4;
      }
      f.ring.material.opacity=(1-p)*.9;
      f.beacon.scale.setScalar(.7+ease*1.9);
      f.beacon.material.opacity=(1-p)*.72;
      const pos=f.sparkGeo.attributes.position;
      for(let j=0;j<f.velocity.length/3;j++){
        const ix=j*3;
        pos.setXYZ(j,f.velocity[ix]*p,
          f.velocity[ix+1]*p-3.3*p*p+1.2,f.velocity[ix+2]*p);
      }
      pos.needsUpdate=true;
      f.sparkMat.opacity=(1-p)*.9;
      if(f.group.userData.beams)for(const beam of f.group.userData.beams){
        beam.material.opacity=Math.max(0,1-p)*(beam.geometry.parameters.radiusTop>.1?.30:.92);
        beam.scale.set(1+p*.22,1,1+p*.22);
      }
    }
  }
  let cards=[],signature='',publicCardCount=0,lastSync=0;
  let vrPendingDeploy=null,vrDeployTransitions=0,vrReusedCards=0;
  // A hand click only arms a presentation. Neither it nor this animation
  // creates a unit: the public Phase21 board must confirm placement first.
  function armDeployment(request){
    if(!vrMode||!request||typeof request.name!=='string'||!request.name.trim())return false;
    const r=renderer.domElement.getBoundingClientRect();
    const screenX=Number(request.x),screenY=Number(request.y);
    if(!Number.isFinite(screenX)||!Number.isFinite(screenY))return false;
    const nx=(screenX-r.left)/r.width*2-1,ny=1-(screenY-r.top)/r.height*2;
    const rayPoint=new THREE.Vector3(nx,ny,.5).unproject(camera);
    const direction=rayPoint.sub(camera.position).normalize();
    const distanceToStage=(1.76-camera.position.y)/direction.y;
    const start=distanceToStage>0?camera.position.clone().addScaledVector(direction,distanceToStage):
      new THREE.Vector3(0,1.76,15);
    vrPendingDeploy={name:request.name.trim(),born:performance.now(),
      origin:new THREE.Vector3(Math.max(-11,Math.min(11,start.x)),4.7,
        Math.max(9.7,Math.min(17,start.z)))};
    return true;
  }
  const vrCardFingerprint=p=>JSON.stringify([p.cardId,p.name,p.kind,p.cost,p.stats,p.sigil]);
  let hoveredKey=null,selectedKey=null,legalCount=0,attackTargetCount=0,statusSignature='';
  let cardHealth=new Map(),healthIndicatorCount=0;
  let pickMeshes=slotPickMeshes.slice(),cardIndex=new Map();
  function publicHit(e){
    const rect=renderer.domElement.getBoundingClientRect();
    if(rect.width<10||rect.height<10||e.clientX<rect.left||e.clientX>rect.right||e.clientY<rect.top||e.clientY>rect.bottom)return null;
    pointer.set((e.clientX-rect.left)/rect.width*2-1,-((e.clientY-rect.top)/rect.height*2-1));
    raycaster.setFromCamera(pointer,camera);
    const hits=raycaster.intersectObjects(pickMeshes,false);
    // While the new model is arriving from the hand it cannot steal a click
    // from the actual legal native slot beneath it.
    return hits.find(hit=>!hit.object.userData.mrrDeploying)?.object.userData.mrrSlotKey||null;
  }
  function projectCard(key){
    const c=cardIndex.get(key);
    if(!c)return null;
    c.group.updateMatrixWorld(true);
    const point=c.group.localToWorld(new THREE.Vector3(0,.12,.15)).project(camera);
    const r=renderer.domElement.getBoundingClientRect();
    return {x:r.left+(point.x+1)*r.width/2,y:r.top+(1-point.y)*r.height/2};
  }
  // VR01-D: the public card's four REAL projected face corners. Dynamic
  // nameplates use these bounds instead of an arbitrary offset from the slot
  // center, so zoom, card count and camera pitch do not desync the labels.
  function projectCardBounds(key){
    if(!vrMode)return null;
    const item=cardIndex.get(key);
    if(!item)return null;
    item.group.updateMatrixWorld(true);
    const rect=renderer.domElement.getBoundingClientRect();
    const halfW=1.05,halfH=1.355;
    const vertices=[[-halfW,-halfH],[halfW,-halfH],
      [halfW,halfH],[-halfW,halfH]];
    const pixels=vertices.map(([x,y])=>{
      const p=item.face.localToWorld(new THREE.Vector3(x,y,.002)).project(camera);
      return {x:rect.left+(1+p.x)*rect.width/2,
        y:rect.top+(1-p.y)*rect.height/2};
    });
    if(!pixels.every(p=>Number.isFinite(p.x)&&Number.isFinite(p.y)))return null;
    const xs=pixels.map(p=>p.x),ys=pixels.map(p=>p.y);
    return {left:Math.min(...xs),right:Math.max(...xs),
      top:Math.min(...ys),bottom:Math.max(...ys)};
  }
  // Phase53: render the exact card-face canvas already shown on the public
  // WebGL mesh. No second artwork catalogue or hidden-game data.
  function getCardPreview(key){
    const item=cardIndex.get(key);
    if(!item)return null;
    if(!item.previewUrl){
      const canvas=item.face.material.map?.image;
      if(!(canvas instanceof HTMLCanvasElement))return null;
      item.previewUrl=canvas.toDataURL('image/png');
    }
    const node=document.querySelector('#arena [data-slot="'+key+'"] .card-ui');
    return {key,artData:item.previewUrl,
      name:node?.querySelector('.card-name')?.textContent?.trim()||'',
      kind:node?.querySelector('.card-kind')?.textContent?.trim()||'',
      stats:node?.querySelector('.card-stats')?.textContent?.trim()||'',
      cost:node?.querySelector('.cost-bubble')?.textContent?.trim()||''};
  }
  function hasCard(key){return cardIndex.has(key);}
  function projectSlot(key){
    const c=boardSlots.get(key);
    if(!c)return null;
    const point=new THREE.Vector3(c.x,.4,c.z).project(camera);
    const r=renderer.domElement.getBoundingClientRect();
    return {x:r.left+(point.x+1)*r.width/2,y:r.top+(1-point.y)*r.height/2};
  }
  function sync(){
    const list=publicSnapshot();
    const nextStatusSignature=JSON.stringify(list.map(p=>[p.key,p.selected,p.legal,p.attackTarget,p.hasHealth,p.hpRatio,p.stateChip]));
    const statusChanged=nextStatusSignature!==statusSignature;
    statusSignature=nextStatusSignature;
    const cardsSignature=JSON.stringify(list.map(p=>[p.key,p.cardId,p.name,p.kind,p.cost,p.stats,p.sigil]));
    const cardChanged=cardsSignature!==signature;
    if(cardChanged){
      signature=cardsSignature;
      // Preserve unchanged public 3D cards. Previously any new card replaced
      // every mesh and texture, making a crowded board visibly flicker.
      const reuse=new Map();
      if(vrMode)for(const p of list){
        const old=cardIndex.get(p.key);
        if(p.name&&old?.fingerprint===vrCardFingerprint(p))reuse.set(p.key,old);
      }
      for(const c of cards){
        if(reuse.get(c.key)===c)continue;
        scene.remove(c.group);if(c.seat)scene.remove(c.seat);
        if(c.face.material.map){
          const tex=c.face.material.map;tex.userData.artDisposed=true;tex.dispose();
          if(vrMode){
            const pos=madeTextures.indexOf(tex);
            if(pos!==-1)madeTextures.splice(pos,1);
          }
        }
        c.face.material.dispose();
      }
      cards=[];if(!vrMode)madeTextures.length=0;
      cardIndex=new Map();pickMeshes=slotPickMeshes.slice();publicCardCount=0;
      vrReusedCards=reuse.size;
      for(const p of list){
        if(!p.name)continue;
        const retained=reuse.get(p.key);
        if(retained){
          cards.push(retained);cardIndex.set(p.key,retained);
          pickMeshes.push(retained.frame,retained.face);publicCardCount++;
          continue;
        }
        const slot=boardSlots.get(p.key);
        const group=new THREE.Group();
        group.position.set(slot.x,1.76,slot.z);group.rotation.x=-.74;
        const frame=new THREE.Mesh(cardGeometry,slot.owner===0?blue:red);
        frame.castShadow=true;frame.userData.mrrSlotKey=p.key;group.add(frame);
        const face=new THREE.Mesh(cardFaceGeometry,new THREE.MeshStandardMaterial({
          map:cardTexture(p,slot.owner===0),metalness:.05,roughness:.48
        }));
        face.position.z=.116;face.userData.mrrSlotKey=p.key;group.add(face);
        if(tabletop){
          for(const x of [-1.112,1.112]){
            const trim=new THREE.Mesh(pcSide,pcGilt);trim.position.set(x,0,.161);group.add(trim);
          }
          for(const y of [-1.427,1.427]){
            const trim=new THREE.Mesh(pcEnd,pcGilt);trim.position.set(0,y,.161);group.add(trim);
          }
        }
        const stand=new THREE.Mesh(cardGeometry,bronze);
        stand.position.z=-.065;stand.scale.set(1.055,1.05,.18);group.add(stand);
        // Parent the indicators to the 3D card so tilt, hover and focus
        // transform the art and health/status as a single visible object.
        const hpBg=new THREE.Mesh(healthBackGeo,healthBackMat);
        hpBg.position.set(0,1.66,.2);group.add(hpBg);
        const hpFill=new THREE.Mesh(healthFillGeo,healthHealthyMat);
        hpFill.position.set(0,1.66,.265);group.add(hpFill);
        const statusDot=new THREE.Mesh(statusGeo,readyMat);
        statusDot.position.set(1.22,1.67,.26);group.add(statusDot);
        scene.add(group);
        let seat=null;
        if(vrMode){
          seat=new THREE.Group();
          seat.position.set(slot.x,.25,slot.z);
          const rim=new THREE.Mesh(vrSeatEdge,slot.owner===0?vrSeatFriendly:vrSeatEnemy);
          rim.position.y=-.035;seat.add(rim);
          const bed=new THREE.Mesh(vrSeatSurface,vrSeatBase);
          bed.position.y=.017;bed.receiveShadow=true;seat.add(bed);
          // Position is decorative: card clicks still hit the pre-existing
          // raycast list and no seat surface is ever part of pickMeshes.
          scene.add(seat);
        }
        const item={key:p.key,group,face,frame,seat,slot,hpBg,hpFill,statusDot,
          fingerprint:vrCardFingerprint(p)};
        // Only newly confirmed, friendly, matching real cards can launch
        // from the last player hand click. Old cards never animate again.
        if(vrMode&&slot.owner===0&&vrPendingDeploy&&
          vrPendingDeploy.name===p.name&&
          performance.now()-vrPendingDeploy.born<18000){
          if(!matchMedia('(prefers-reduced-motion: reduce)').matches){
            item.deploy={started:performance.now(),from:vrPendingDeploy.origin.clone()};
            frame.userData.mrrDeploying=face.userData.mrrDeploying=true;
            vrDeployTransitions++;
          }
          vrPendingDeploy=null;
        }
        cards.push(item);cardIndex.set(p.key,item);
        pickMeshes.push(frame,face);publicCardCount++;
      }
    }
    selectedKey=list.find(p=>p.selected)?.key||null;
    legalCount=list.filter(p=>p.legal).length;
    cardHealth=new Map();healthIndicatorCount=0;
    attackTargetCount=list.filter(p=>p.attackTarget).length;
    for(const p of list){
      const slot=boardSlots.get(p.key);
      // Phase72: follow the original native .legal class; never change rules.
      slot.legalPulse=tabletop&&!!p.legal&&!p.selected&&!p.attackTarget;
      // Phase74: warm target animation uses only the native attack-target class.
      slot.attackPulse=tabletop&&!!p.attackTarget&&!p.selected;
      // Phase73: the source marker follows native selection, never inferred AI.
      if(slot.focusRing)slot.focusRing.visible=!!p.selected;
      slot.halo.visible=!!(p.selected||p.attackTarget||p.legal||hoveredKey===p.key);
      slot.halo.material=p.attackTarget?attackGlow:p.selected?selectGlow:p.legal?legalGlow:hoverGlow;
      const item=cardIndex.get(p.key);
      if(item){
        item.frame.material=p.selected?gold:(slot.owner===0?blue:red);
        item.hpBg.visible=item.hpFill.visible=p.hasHealth;
        item.hpFill.material=p.hpRatio<=.33?healthDangerMat:p.hpRatio<=.66?healthWarnMat:healthHealthyMat;
        item.hpFill.scale.x=Math.max(.001,p.hpRatio??0);
        item.hpFill.position.x=-1.02*(1-(p.hpRatio??0));
        item.statusDot.material=/보호|방호/.test(p.stateChip)?wardMat:
          /행동 완료|대기/.test(p.stateChip)?actedMat:readyMat;
        item.statusDot.visible=!!p.stateChip;
        if(p.hasHealth){
          healthIndicatorCount++;
          cardHealth.set(p.key,{ratio:p.hpRatio,state:p.stateChip,color:p.hpRatio<=.33?'danger':p.hpRatio<=.66?'warning':'healthy'});
        }
      }
    }
    if(hoveredKey&&!list.some(p=>p.key===hoveredKey))hoveredKey=null;
    const hovered=list.find(p=>p.key===hoveredKey);
    const source=boardSlots.get(selectedKey),target=boardSlots.get(hoveredKey);
    const arrowVisible=!!(source&&target&&hovered?.attackTarget);
    attackArrow.visible=attackTip.visible=arrowVisible;
    if(arrowVisible){
      const pos=attackArrowGeo.attributes.position;
      pos.setXYZ(0,source.x,1.65,source.z);
      pos.setXYZ(1,target.x,1.65,target.z);
      pos.needsUpdate=true;
      const direction=new THREE.Vector3(target.x-source.x,0,target.z-source.z);
      attackTip.position.set(target.x,1.66,target.z);
      attackTip.rotation.set(0,0,0);
      attackTip.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),direction.normalize());
    }
    events.onState?.({selectedKey,hoveredKey,legalCount,attackTargetCount,publicCardCount});
    if((cardChanged||statusChanged)&&hoveredKey)setHover(hoveredKey,true);
  }
  function setHover(key,force=false){
    if(hoveredKey===key&&!force)return;
    hoveredKey=key;
    const slot=document.querySelector('#arena [data-slot="'+(key||'')+'"]');
    const card=slot?.querySelector('.board-card .card-ui');
    mount.style.cursor=key&&(card||slot?.classList.contains('legal')||slot?.classList.contains('attack-target'))?'pointer':vrMode?'default':'grab';
    events.onHover?.(key,card?{
      name:card.querySelector('.card-name')?.textContent?.trim()||'',
      kind:card.querySelector('.card-kind')?.textContent?.trim()||'',
      stats:card.querySelector('.card-stats')?.textContent?.trim()||'',
      selected:slot.classList.contains('selected-slot'),
      target:slot.classList.contains('attack-target'),
      legal:slot.classList.contains('legal')
    }:slot?{name:slot.classList.contains('legal')?'배치 또는 이동 가능한 슬롯':'빈 슬롯',kind:'',stats:'',target:slot.classList.contains('attack-target'),legal:slot.classList.contains('legal')}:null);
    if(!force)sync();
  }
  let yaw=0,pitch=.77,distance=29,focusX=0,focusZ=0,cameraPreset='all',focusKey=null;
  // The player always wins control: density-aware camera framing runs only
  // while using the untouched automatic tabletop preset.
  let manualCamera=false;
  let drag=false,moved=false,lastX=0,lastY=0,startX=0,startY=0;
  function updateCamera(){
    const aspect=mount.clientWidth/Math.max(1,mount.clientHeight);
    const d=distance*(aspect<.75?1.6:aspect<1.1?1.22:1);
    camera.position.set(focusX+Math.sin(yaw)*Math.cos(pitch)*d,
      1.3+Math.sin(pitch)*d,focusZ+Math.cos(yaw)*Math.cos(pitch)*d);
    camera.lookAt(focusX,.8,focusZ);
    // Raycaster, projectCard and projectSlot can be called before the next
    // WebGL frame after a camera button click. Never use a stale view matrix.
    camera.updateMatrixWorld(true);
  }
  function down(e){
    if(e.button!==0||e.target!==renderer.domElement)return;
    drag=true;moved=false;
    startX=lastX=e.clientX;startY=lastY=e.clientY;
    mount.setPointerCapture?.(e.pointerId);
  }
  function move(e){
    if(!drag){setHover(e.target===renderer.domElement?publicHit(e):null);return;}
    if(Math.hypot(e.clientX-startX,e.clientY-startY)>6)moved=true;
    // VR mode is a fixed tabletop: dragging must never turn, tilt or pan
    // the entire board. Keep movement threshold to avoid accidental
    // card selection when the player releases after a gesture.
    if(moved&&!vrMode){
      yaw=Math.max(-.8,Math.min(.8,yaw+(e.clientX-lastX)*.004));
      pitch=Math.max(.42,Math.min(1.28,pitch+(e.clientY-lastY)*.003));
      manualCamera=true;
      updateCamera();setHover(null);
    }
    lastX=e.clientX;lastY=e.clientY;
  }
  function up(e){
    if(!drag)return;
    drag=false;
    const picked=publicHit(e);
    if(!moved&&picked){events.onPick?.(picked);sync();}
    setHover(picked);
  }
  function leave(){if(!drag)setHover(null);}
  function wheel(e){e.preventDefault();manualCamera=true;distance=Math.max(24,Math.min(47,distance+e.deltaY*.018));updateCamera();setHover(null);}
  mount.addEventListener('pointerdown',down);
  mount.addEventListener('pointermove',move);
  mount.addEventListener('pointerup',up);
  mount.addEventListener('pointercancel',up);
  mount.addEventListener('pointerleave',leave);
  mount.addEventListener('wheel',wheel,{passive:false});
  let frames=0,raf=0,running=false,disposed=false,lastDraw=0,lastVisualTime=0;
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
    const visualDelta=lastVisualTime?Math.max(1,Math.min(220,time-lastVisualTime)):32;
    lastVisualTime=time;
    if(time-lastSync>220){lastSync=time;sync();}
    const frozen=matchMedia('(prefers-reduced-motion: reduce)').matches;
    if(vrMode&&cameraPreset==='tabletop'&&!manualCamera){
      // VR01G: a crowded 6-row table needs more vertical screen real
      // estate. Move the camera back a little while preserving true slot
      // coordinates and the player's absolute priority over auto views.
      const dense=cards.length>=16;
      const desiredPitch=dense?1.31:cards.length>=9?1.245:1.17;
      const desiredDistance=dense?32.2:cards.length>=9?30.2:28.8;
      const alpha=frozen?1:1-Math.exp(-visualDelta/330);
      const np=pitch+(desiredPitch-pitch)*alpha;
      const nd=distance+(desiredDistance-distance)*alpha;
      if(Math.abs(np-pitch)>.0002||Math.abs(nd-distance)>.001){
        pitch=np;distance=nd;updateCamera();
      }
    }
    if(!frozen)sealCore.rotation.y=time*.00035;
    // Phase72: decorative slot halos never enter raycast target meshes.
    if(tabletop)for(const [key,slot] of boardSlots){
      // Phases74-76: semantic targets share existing halos/materials;
      // there are no added click surfaces and no per-frame GPU allocations.
      const pulse=frozen?0:.5+.5*Math.sin(time*.0046);
      const size=frozen?1:slot.attackPulse?1.07+.16*pulse:
        slot.legalPulse?1.035+.075*pulse:hoveredKey===key?1.055:1;
      slot.halo.scale.setScalar(size);
    }
    for(const [i,c] of cards.entries()){
      const hover=c.key===hoveredKey;
      if(tabletop){
        // VR01-C: an occupied card gets larger when it has actual physical
        // room. Dense battles retain a non-overlapping normal scale; lone
        // cards must not look like thumbnails in a nearly empty arena.
        // Only publicly rendered slot coordinates are considered.
        // VR01G: measure actual occupied row direction, not just nearest
        // radial neighbor. Card HEIGHT is the limiting dimension when
        // adjacent native rows share a column; a 1.42 face can cover most
        // of the face behind it even though native slot clicks still work.
        const sameColumnRow=vrMode&&cards.some(other=>other!==c&&
          Math.abs(other.slot.x-c.slot.x)<.65&&
          Math.abs(other.slot.z-c.slot.z)<3.05);
        const sameRowNeighbor=vrMode&&cards.some(other=>other!==c&&
          Math.abs(other.slot.x-c.slot.x)<3.43&&
          Math.abs(other.slot.z-c.slot.z)<.65);
        const dense=vrMode&&cards.length>=16;
        const adaptive=vrMode&&cameraPreset==='tabletop'?
          sameColumnRow?(dense?.96:1.04):
          sameRowNeighbor?(dense?1.19:1.31):dense?1.13:1.61:1.30;
        // A focused card may rise for inspection, but never expand enough
        // to hide an unrelated occupied row in a dense battlefield.
        const emphasis=hover?(sameColumnRow?.10:.23):
          c.key===selectedKey?(sameColumnRow?.045:.12):0;
        const targetScale=vrMode?adaptive+emphasis:
          hover?1.52:c.key===selectedKey?1.35:1.30;
        const targetLift=hover?.86:c.key===selectedKey?.18:0;
        // Time-based smoothing stays stable on low-FPS software WebGL.
        const blend=frozen?1:1-Math.exp(-visualDelta/115);
        c.visualScale=(c.visualScale??1.30)+(targetScale-(c.visualScale??1.30))*blend;
        c.visualLift=(c.visualLift??0)+(targetLift-(c.visualLift??0))*blend;
        if(vrMode&&c.deploy){
          const raw=Math.max(0,Math.min(1,(performance.now()-c.deploy.started)/720));
          const ease=1-Math.pow(1-raw,3);
          const arc=Math.sin(Math.PI*raw)*1.65;
          const start=c.deploy.from;
          c.group.position.set(
            start.x+(c.slot.x-start.x)*ease,
            start.y+(1.76+c.visualLift-start.y)*ease+arc,
            start.z+(c.slot.z-start.z)*ease);
          c.group.rotation.x=.16+(-.74-.16)*ease;
          c.group.rotation.z=(1-ease)*.13;
          c.group.scale.setScalar(c.visualScale*(.66+.34*ease));
          if(c.seat)c.seat.scale.setScalar(.72+.28*ease);
          if(raw>=1){
            c.deploy=null;
            c.frame.userData.mrrDeploying=c.face.userData.mrrDeploying=false;
            c.group.rotation.set(-.74,0,0);
            if(c.seat)c.seat.scale.setScalar(1);
            spawnVrLandingDust(c.slot,time);
          }
        }else{
          c.group.scale.setScalar(c.visualScale);
          c.group.position.y=1.76+c.visualLift+(frozen?0:Math.sin(time*.0015+i*.67)*.025);
          if(vrMode){
            const impact=c.hitReaction;
            const age=impact?(time-impact.born)/390:1;
            if(impact&&age>=1)c.hitReaction=null;
            const recoil=impact&&age<1?Math.sin(Math.PI*Math.max(0,age))*(1-Math.max(0,age)*.35):0;
            c.group.position.x=c.slot.x+(impact?.dx||0)*recoil*.34;
            c.group.position.z=c.slot.z+(impact?.dz||0)*recoil*.34;
            c.group.rotation.z=(impact?.dx||0)*recoil*.10;
          }
        }
      }else{
        // Keep the existing standalone battlefield presentation unchanged.
        c.group.scale.setScalar(hover?1.26:1);
        c.group.position.y=1.76+(hover?.78:0)+(frozen?0:Math.sin(time*.0015+i*.67)*.045);
      }
    }
    advanceEffects(time);
    if(vrMode)advanceVrLandingDust(time);
    advanceCinematics(time);
    renderer.render(scene,camera);frames++;
  }
  function start(){if(disposed)return;resize();sync();if(running)return;
    const arena=document.querySelector('#arena');
    if(arena)fxObserver.observe(arena,{subtree:true,attributes:true,attributeFilter:['class']});
    running=true;lastDraw=0;raf=requestAnimationFrame(tick);
  }
  function stop(){running=false;cancelAnimationFrame(raf);fxObserver.disconnect();}
  function setCameraPreset(preset){
    const target=preset==='selected'?(selectedKey||hoveredKey):null;
    if(preset==='selected'&&!target)return false;
    if(!['all','ally','enemy','selected','tabletop'].includes(preset))return false;
    if(preset==='tabletop'&&!tabletop)return false;
    yaw=0;manualCamera=false;
    pitch=vrMode&&['ally','enemy'].includes(preset)?1.12:
      preset==='tabletop'?1.17:preset==='selected'?.64:preset==='all'?.77:.67;
    focusKey=target;cameraPreset=preset;
    const slot=target?boardSlots.get(target):null;
    focusX=slot?.x||0;
    // Dedicated PC tactical views are high enough to preserve all five
    // columns. The generic Phase76 camera and modal keep their exact values.
    focusZ=slot?.z||(preset==='ally'?(vrMode?5.0:5.6):
      preset==='enemy'?(vrMode?-5.0:-5.6):0);
    distance=preset==='tabletop'?28.8:preset==='all'?29:
      preset==='selected'?11.5:vrMode?22.8:18.5;
    updateCamera();return true;
  }
  function resetCamera(){setCameraPreset('all');}
  function dispose(){
    if(disposed)return;stop();disposed=true;
    for(const fx of liveEffects.splice(0))removeFx(fx);
    for(const f of vrLandingDust.splice(0)){scene.remove(f.points);f.geo.dispose();f.mat.dispose();}
    recentFx.clear();pendingStrike=null;cinemaImpact=null;impactLamp.intensity=0;
    for(const c of cards){
      if(c.seat)scene.remove(c.seat);
      c.face.material.map.userData.artDisposed=true;c.face.material.map.dispose();c.face.material.dispose();
    }
    cards=[];for(const g of madeGeometry)g.dispose();
    for(const m of madeMaterials)m.dispose();
    for(const t of madeTextures)t.dispose();
    for(const t of tabletopTextures)t.dispose();
    mount.removeEventListener('pointerdown',down);
    mount.removeEventListener('pointermove',move);
    mount.removeEventListener('pointerup',up);
    mount.removeEventListener('pointercancel',up);
    mount.removeEventListener('pointerleave',leave);
    mount.removeEventListener('wheel',wheel);
    renderer.dispose();renderer.domElement.remove();
  }
  return {start,stop,dispose,resize,resetCamera,setCameraPreset,sync,projectCard,projectCardBounds,projectSlot,stageAttack,getCardPreview,hasCard,armDeployment,
    refreshHover:(key)=>setHover(key,true),
    get state(){return {revision:49,projection:camera.type,frames,slotCount:boardSlots.size,
      publicCardCount,cardMeshCount:cards.length,shadows:renderer.shadowMap.enabled,
      rendererAlive:renderer.domElement.isConnected,yaw,pitch,distance,
      vrCameraAuto:vrMode?!manualCamera:null,
      vrCrowdedComposition:vrMode&&cameraPreset==='tabletop'&&cards.length>=16,
      hoveredKey,selectedKey,legalCount,attackTargetCount,pickableCount:pickMeshes.length,
      nativeFxRevision:48,fxReceived:{...effectsReceived},liveFxCount:liveEffects.length,peakLiveFxCount,
      fxSources:'native-slot-classes',cinematicRevision:49,
      confirmedStrikes,cinematicFrameCount,impactLightIntensity:impactLamp.intensity,
      realCombatQaRevision:50,nativeCombatEvents:nativeCombatEvents.slice(),
      visualArtRevision:51,pcArtRevision:tabletop?57:0,illustratedCards:cards.length,illustrationArchetypes:cards.map(c=>c.face.material.map?.userData?.artArchetype||''),cameraPreset,focusKey,focusX,focusZ,
      vrAdaptiveCardScales:vrMode?Object.fromEntries(cards.map(c=>[c.key,Math.round((c.visualScale||1.30)*1000)/1000])):null,
      vrOccupiedSeats:vrMode?cards.filter(c=>!!c.seat).length:null,
      vrReusedCards:vrMode?vrReusedCards:null,vrDeployTransitions:vrMode?vrDeployTransitions:null,
      vrDeployActive:vrMode?cards.filter(c=>!!c.deploy).length:null,
      vrLiveCardTextures:vrMode?madeTextures.length:null,
      vrLandingDustStarted:vrMode?vrLandingDustStarted:null,
      vrLandingDustActive:vrMode?vrLandingDust.length:null,
      vrHitReactions:vrMode?vrHitReactions:null,
      vrActiveHitReactions:vrMode?cards.filter(c=>!!c.hitReaction).length:null,
      healthHudRevision:52,healthIndicatorCount,cardHealth:Object.fromEntries(cardHealth),
      previewRevision:53,previewReadyCards:cardIndex.size,
      artworkSlotRevision:tabletop?58:0,
      artworkImportRevision:tabletop?59:0,
      pcLegibilityRevision:tabletop?67:0,pcCardScale:tabletop?1.30:1,
      pcCardHoverScale:tabletop?1.52:1.26,pcCardSelectedScale:tabletop?1.35:1,
      pcRenderedCardScales:tabletop?Object.fromEntries(cards.map(c=>[c.key,Number(c.group.scale.x.toFixed(3))])):null,
      artworkEmbeddedCount:tabletop?Object.keys(window.MRRCardArtRegistry?.assets||{}).length:0,
      artworkLoadedCount:tabletop?cards.filter(c=>c.face.material.map?.userData.artLoaded).length:0,artworkSlotResolution:tabletop?'1200x960':null,
      artworkSlotBounds:tabletop?{...pcArtSlot}:null,
      pcFieldGuideRevision:tabletop?76:0,
      pcSelectedFocusKeys:tabletop?[...boardSlots].filter(([,s])=>s.focusRing?.visible).map(([k])=>k):[],
      pcAttackTargetScales:tabletop?Object.fromEntries([...boardSlots].filter(([,s])=>s.attackPulse).map(([k,s])=>[k,Number(s.halo.scale.x.toFixed(3))])):{},
      pcLegalPulseRevision:tabletop?72:0,
      pcLegalPulseScales:tabletop?Object.fromEntries([...boardSlots].filter(([,s])=>s.legalPulse).map(([k,s])=>[k,Number(s.halo.scale.x.toFixed(3))])):{},
      pcZoneContrastRevision:tabletop?69:0,desktopArtRevision:tabletop?55:0,tabletopSurface:tabletop?'parchment-and-wood':'legacy-stone',
      proceduralTextureCount:tabletopTextures.length,
      combatEvent:latestCombat,stagedStrike:!!pendingStrike,
      liveStrikeCount:liveEffects.filter(x=>(x.group.userData.beams||[]).length).length};}};
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
      const commands=document.createElement('nav');commands.id='mrr-battlefield-commands';
      commands.setAttribute('aria-label','3D 전장 카드 행동');
      const attack=document.createElement('button');attack.id='mrr-battlefield-attack';
      attack.type='button';attack.textContent='공격 대상 지정';attack.disabled=true;
      const moveCard=document.createElement('button');moveCard.id='mrr-battlefield-move';
      moveCard.type='button';moveCard.textContent='인접 이동';moveCard.disabled=true;
      const cancelAction=document.createElement('button');cancelAction.id='mrr-battlefield-cancel';
      cancelAction.type='button';cancelAction.textContent='선택 취소';cancelAction.disabled=true;
      const pinPreview=document.createElement('button');
      pinPreview.id='mrr-battlefield-preview-pin';pinPreview.type='button';
      pinPreview.textContent='확대 고정';pinPreview.disabled=true;
      pinPreview.setAttribute('aria-pressed','false');
      commands.append(attack,moveCard,cancelAction,pinPreview);
      const combatFeed=document.createElement('div');combatFeed.id='mrr-battlefield-combat-feed';
      combatFeed.setAttribute('role','status');combatFeed.setAttribute('aria-live','polite');
      function onNativeCombat(event){
        const label=event.type==='hit'?'피격':event.type==='heal'?'치유':'소환';
        combatFeed.textContent=label+' 신호  |  '+(event.name||'전장 슬롯')+(event.confirmedStrike?'  ·  공격 궤적 확정':'');
        combatFeed.dataset.kind=event.type;combatFeed.classList.add('active');
        combatFeed.dataset.since=String(event.at);
      }
      const zoomPane=document.createElement('aside');zoomPane.id='mrr-battlefield-zoom-pane';
      zoomPane.setAttribute('role','region');zoomPane.setAttribute('aria-label','공개 카드 확대 미리보기');
      const zoomImage=document.createElement('img');zoomImage.id='mrr-battlefield-zoom-image';
      zoomImage.alt='공개 카드 일러스트 확대';
      const zoomCaption=document.createElement('div');zoomCaption.id='mrr-battlefield-zoom-caption';
      zoomPane.append(zoomImage,zoomCaption);
      let pinnedKey=null,previewKey=null,shownImage='';
      function renderZoom(key){
        if(pinnedKey)key=pinnedKey;
        const info=key?view?.getCardPreview(key):null;
        if(!info||!info.name){
          previewKey=null;shownImage='';zoomPane.classList.remove('visible');
          zoomImage.removeAttribute('src');zoomCaption.textContent='';
          return;
        }
        previewKey=info.key;
        if(shownImage!==info.artData){shownImage=info.artData;zoomImage.src=info.artData;}
        zoomImage.alt=info.name+' 카드 확대';
        zoomCaption.textContent=[info.name,info.kind,info.stats].filter(Boolean).join(' · ');
        zoomPane.classList.add('visible');
      }
      pinPreview.addEventListener('click',()=>{
        if(pinnedKey){
          pinnedKey=null;pinPreview.setAttribute('aria-pressed','false');
          pinPreview.textContent='확대 고정';
          renderZoom(view?.state.hoveredKey||view?.state.selectedKey||previewKey);
        }else{
          const key=view?.state.hoveredKey||view?.state.selectedKey||previewKey;
          if(!key||!view?.hasCard(key))return;
          pinnedKey=key;pinPreview.setAttribute('aria-pressed','true');
          pinPreview.textContent='고정 해제';renderZoom(key);
        }
      });
      const cardTip=document.createElement('div');cardTip.id='mrr-battlefield-cardtip';
      cardTip.setAttribute('role','status');cardTip.setAttribute('aria-live','off');
      function runNativeAction(selector){
        const native=document.querySelector('#inspectBody '+selector);
        if(!native||native.disabled||!view)return;
        native.click();view.sync();
      }
      attack.addEventListener('click',()=>runNativeAction('button[data-actor="attack"]'));
      moveCard.addEventListener('click',()=>runNativeAction('button[data-actor="move"]'));
      cancelAction.addEventListener('click',()=>runNativeAction('button[data-cancel-action]'));
      function updateCommands(info){
        if(previewKey&&!view?.hasCard(previewKey))renderZoom(null);
        if(pinnedKey&&!view?.hasCard(pinnedKey)){
          pinnedKey=null;pinPreview.setAttribute('aria-pressed','false');
          pinPreview.textContent='확대 고정';
        }
        pinPreview.disabled=!(pinnedKey||view?.hasCard(info.hoveredKey)||view?.hasCard(info.selectedKey)||view?.hasCard(previewKey));
        if(!pinnedKey&&(info.hoveredKey||info.selectedKey)&&(info.hoveredKey||info.selectedKey)!==previewKey){
          renderZoom(info.hoveredKey||info.selectedKey);
        }
        if(combatFeed.classList.contains('active')&&performance.now()-Number(combatFeed.dataset.since)>1650){combatFeed.classList.remove('active');}
        const inspect=Boolean(info.selectedKey);
        const nativeAttack=document.querySelector('#inspectBody button[data-actor="attack"]');
        const nativeMove=document.querySelector('#inspectBody button[data-actor="move"]');
        attack.disabled=!inspect||!nativeAttack||nativeAttack.disabled;
        moveCard.disabled=!inspect||!nativeMove||nativeMove.disabled;
        cancelAction.disabled=!document.querySelector('#inspectBody button[data-cancel-action]');
        const phase=info.attackTargetCount?'  /  공격 대상 '+info.attackTargetCount+'곳':
          info.legalCount?'  /  유효 위치 '+info.legalCount+'곳':'';
        status.textContent='전장 30슬롯  /  공개 카드 '+info.publicCardCount+'장'+phase;
        if(view)refreshPresetButtons();
      }
      function pickNativeSlot(key){
        const node=document.querySelector('#arena [data-slot="'+key+'"]');
        if(!node||!view||!document.querySelector('#overlay.hidden'))return;
        const actionable=node.querySelector('.board-card')||
          node.classList.contains('legal')||node.classList.contains('attack-target');
        if(!actionable)return;
        if(node.classList.contains('attack-target')&&view.state.selectedKey){
          view.stageAttack(view.state.selectedKey,key);
        }
        // One delegated DOM click is the sole authority for all selection,
        // movement, summons and attacks. Never simulate a damage event.
        node.click();
        view.sync();
        // Rendering can recreate slot DOM nodes; read the new card immediately
        // instead of relying on a second pointer movement after the native click.
        view.refreshHover(key);
      }
      function describeHover(key,profile){
        if(!pinnedKey&&(view?.hasCard(key)||view?.hasCard(view?.state.selectedKey)))renderZoom(view?.hasCard(key)?key:view?.state.selectedKey);
        if(!key||!profile){cardTip.classList.remove('visible');cardTip.textContent='';return;}
        const legal=profile.target?'공격 가능 대상':profile.legal?'합법적 대상 또는 위치':'';
        cardTip.replaceChildren();
        const headline=document.createElement('strong');headline.textContent=profile.name;
        const summary=document.createElement('span');summary.textContent=
          [profile.kind,profile.stats,legal].filter(Boolean).join('  |  ');
        cardTip.append(headline,summary);cardTip.classList.add('visible');
      }
      const overlayHelp=document.createElement('div');overlayHelp.id='mrr-battlefield-help';
      overlayHelp.textContent=vrMode?'카드 클릭 - 선택  |  공격 버튼 - 대상 지정  |  휠 - 확대·축소  |  시점 버튼 - 카메라 전환':
  '카드 클릭 - 선택  |  공격 버튼 - 대상 지정  |  드래그 - 시점 회전  |  휠 - 확대·축소';
      const enemy=document.createElement('div');enemy.className='mrr-side-label enemy';enemy.textContent='OPPONENT TERRITORY';
      const friendly=document.createElement('div');friendly.className='mrr-side-label friendly';friendly.textContent='ALLIED TERRITORY';
      stage.append(enemy,friendly,overlayHelp,commands,cardTip,combatFeed,zoomPane);
      dialog.append(header,stage);layer.appendChild(dialog);document.body.appendChild(layer);
      layer.addEventListener('click',event=>{if(event.target===layer)close();});
      overlay=layer;view=window.MRRBattlefieldFactory(THREE,stage,{
        onPick:pickNativeSlot,onHover:describeHover,onState:updateCommands,onCombat:onNativeCombat
      });
      const viewpoints=document.createElement('nav');viewpoints.id='mrr-battlefield-viewpoints';
      viewpoints.setAttribute('aria-label','3D 전장 카메라 프리셋');
      const presetSpecs=[
        ['all','전장 전체'],['ally','아군 전선'],['enemy','적군 전선'],['selected','선택 카드 확대']
      ];
      const presetButtons=new Map();
      function refreshPresetButtons(){
        const state=view?.state;
        for(const [id,button] of presetButtons){
          button.setAttribute('aria-pressed',String(state?.cameraPreset===id));
          button.disabled=id==='selected'&&!state?.selectedKey&&!state?.hoveredKey;
        }
      }
      for(const [id,label] of presetSpecs){
        const b=document.createElement('button');b.type='button';b.textContent=label;
        b.id='mrr-view-'+id;b.setAttribute('aria-pressed',String(id==='all'));
        b.addEventListener('click',()=>{
          if(view?.setCameraPreset(id))refreshPresetButtons();
        });
        presetButtons.set(id,b);viewpoints.appendChild(b);
      }
      stage.appendChild(viewpoints);
      reset.addEventListener('click',()=>{view?.resetCamera();refreshPresetButtons();});
      refreshPresetButtons();
      view.start();
      updateCommands(view.state);
      exit.focus();
    }catch(err){console.warn('Phase47 WebGL battlefield unavailable:',err);close();}
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
