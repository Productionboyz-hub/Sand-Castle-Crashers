export default {
  async fetch(request) {
    const html = `<!-- Sand Castle Crashers v0.6.1 — Castle restored with health & deterioration -->
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sand Castle Crashers v0.6.1</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#0a0e14; display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:100vh; }
canvas { display:block; cursor:crosshair; }
#hud { color:#7ab8cc; font:10px/1 monospace; letter-spacing:2px; text-transform:uppercase; margin-top:8px; opacity:0.6; }
#toolbar { display:flex; gap:8px; margin-top:10px; }
.pbtn {
  background:#111e2a; border:1px solid #2a4a60; color:#6a9ab0;
  font:10px/1 monospace; letter-spacing:1px; text-transform:uppercase;
  padding:6px 12px; cursor:pointer; border-radius:3px;
}
.pbtn.active { background:#1e3a52; border-color:#7ab8cc; color:#c8eeff; }
.pbtn:hover  { background:#182838; }
</style>
</head>
<body>
<canvas id="c"></canvas>
<div id="hud">tide: rising · 0%</div>
<div id="toolbar">
  <button class="pbtn" data-type="moat">Moat</button>
  <button class="pbtn active" data-type="smallWall">Small Wall</button>
  <button class="pbtn" data-type="mediumWall">Medium Wall</button>
  <button class="pbtn" data-type="tallWall">Tall Wall</button>
</div>
<script>
const canvas = document.getElementById('c');
const ctx    = canvas.getContext('2d');
const hud    = document.getElementById('hud');

const SW = Math.min(window.innerWidth,  740);
const SH = Math.min(window.innerHeight, 520);
canvas.width = SW; canvas.height = SH;

function fade(t){return t*t*t*(t*(t*6-15)+10);}
function lerp(a,b,t){return a+(b-a)*t;}
const PERM=new Uint8Array(512);
(()=>{const p=new Uint8Array(256);for(let i=0;i<256;i++)p[i]=i;
  for(let i=255;i>0;i--){const j=Math.random()*i|0;[p[i],p[j]]=[p[j],p[i]];}
  for(let i=0;i<512;i++)PERM[i]=p[i&255];})();
function grad2(h,x,y){const u=h<4?x:y,v=h<4?y:x;return((h&1)?-u:u)+((h&2)?-v:v);}
function noise2(x,y){
  const X=Math.floor(x)&255,Y=Math.floor(y)&255;
  x-=Math.floor(x);y-=Math.floor(y);
  const u=fade(x),v=fade(y),a=PERM[X]+Y,b=PERM[X+1]+Y;
  return lerp(lerp(grad2(PERM[a]&7,x,y),grad2(PERM[b]&7,x-1,y),u),
              lerp(grad2(PERM[a+1]&7,x,y-1),grad2(PERM[b+1]&7,x-1,y-1),u),v);
}
function fbm(x,y,oct){
  let v=0,amp=0.5,freq=1,mx=0;
  for(let i=0;i<oct;i++){v+=noise2(x*freq,y*freq)*amp;mx+=amp;amp*=0.5;freq*=2;}
  return v/mx;
}

const GCOLS=16,GROWS=16,TW=56,TH=28;
const OX=SW*0.5, OY=SH*0.06;

function iso(col,row,z){
  return{x:OX+(col-row)*(TW/2),y:OY+(col+row)*(TH/2)-(z||0)*TH};
}
function screenToIso(sx,sy){
  const a=(sx-OX)/(TW/2),b=(sy-OY)/(TH/2);
  return{col:Math.floor((a+b)/2),row:Math.floor((b-a)/2)};
}

const SHORE_LOW=22;
let tidePhase=0,shoreD=22,lastTideSign=1;
let tideSpeed=0.0035,tidePeak=10,tideShape=1.0,tideSurge=0.08,surgeFreq=3.1,surgeShift=0,shoreSnap=0.004;

function getTideT(){
  const raw=(Math.sin(tidePhase)+1)/2;
  const shaped=Math.pow(raw,tideShape);
  const surge=Math.sin(tidePhase*surgeFreq+surgeShift)*tideSurge;
  return Math.max(0,Math.min(1,shaped+surge));
}
function randomizeTideCycle(){
  tideSpeed =0.0012+Math.random()*0.007;
  tidePeak  =2+Math.random()*14;
  tideShape =0.4+Math.random()*1.8;
  tideSurge =Math.random()*0.28;
  surgeFreq =2.3+Math.random()*3.4;
  surgeShift=Math.random()*Math.PI*2;
  shoreSnap =0.002+Math.random()*0.009;
}

let edgeTime=0;
function getShoreOffset(col,row,t){return fbm(col*0.6+t*0.35,row*0.6+t*0.25,3)*2.2;}
function isTileWater(col,row){return col+row+getShoreOffset(col,row,edgeTime)>shoreD;}
function isShore(col,row){const d=col+row+getShoreOffset(col,row,edgeTime);return d>=shoreD-1.5&&d<=shoreD+1.5;}

const wCanvas=document.createElement('canvas');
wCanvas.width=SW;wCanvas.height=SH;
const wCtx=wCanvas.getContext('2d');
function buildWaterTex(t){
  const imgd=wCtx.createImageData(SW,SH);
  for(let sy=0;sy<SH;sy++)for(let sx=0;sx<SW;sx++){
    const wx=sx/SW,wy=sy/SH;
    const n1=fbm(wx*6+t*0.11,wy*6-t*0.08,3),n2=fbm(wx*11-t*0.07,wy*11+t*0.10,2);
    const n=n1*0.6+n2*0.4,dx=wx-0.5,dy=wy-0.08;
    const bloom=Math.max(0,1-Math.sqrt(dx*dx*1.8+dy*dy*4)*2.0);
    const base=0.3+n*0.45+bloom*0.4;
    const idx=(sy*SW+sx)*4;
    imgd.data[idx]  =Math.min(255,(15 +base*35 +bloom*55)|0);
    imgd.data[idx+1]=Math.min(255,(50 +base*65 +bloom*45)|0);
    imgd.data[idx+2]=Math.min(255,(130+base*90 +bloom*70)|0);
    imgd.data[idx+3]=255;
  }
  wCtx.putImageData(imgd,0,0);
}

const sCanvas=document.createElement('canvas');
sCanvas.width=SW;sCanvas.height=SH;
const sCtx2=sCanvas.getContext('2d');
(()=>{
  const imgd=sCtx2.createImageData(SW,SH);
  for(let sy=0;sy<SH;sy++)for(let sx=0;sx<SW;sx++){
    const n=fbm(sx/90,sy/90,3)*0.5+0.5,base=210+n*22|0,idx=(sy*SW+sx)*4;
    imgd.data[idx]  =Math.min(255,base+8);
    imgd.data[idx+1]=Math.min(255,(base*0.83)|0);
    imgd.data[idx+2]=Math.min(255,(base*0.52)|0);
    imgd.data[idx+3]=255;
  }
  sCtx2.putImageData(imgd,0,0);
})();

function clipTilePath(col,row){
  const p=iso(col,row,0),pr=iso(col+1,row,0),pb=iso(col+1,row+1,0),pf=iso(col,row+1,0);
  ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(pr.x,pr.y);ctx.lineTo(pb.x,pb.y);ctx.lineTo(pf.x,pf.y);ctx.closePath();
}
function isoBlock(col,row,z,h,topC,leftC,rightC,alpha){
  const p=iso(col,row,z+h),pr=iso(col+1,row,z+h),pf=iso(col,row+1,z+h),pb=iso(col+1,row+1,z+h);
  const p0=iso(col,row,z),pr0=iso(col+1,row,z),pf0=iso(col,row+1,z),pb0=iso(col+1,row+1,z);
  ctx.save();if(alpha!==undefined)ctx.globalAlpha=alpha;
  ctx.fillStyle=topC;ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(pr.x,pr.y);ctx.lineTo(pb.x,pb.y);ctx.lineTo(pf.x,pf.y);ctx.closePath();ctx.fill();
  ctx.fillStyle=leftC;ctx.beginPath();ctx.moveTo(pf.x,pf.y);ctx.lineTo(pb.x,pb.y);ctx.lineTo(pb0.x,pb0.y);ctx.lineTo(pf0.x,pf0.y);ctx.closePath();ctx.fill();
  ctx.fillStyle=rightC;ctx.beginPath();ctx.moveTo(pr.x,pr.y);ctx.lineTo(pb.x,pb.y);ctx.lineTo(pb0.x,pb0.y);ctx.lineTo(pr0.x,pr0.y);ctx.closePath();ctx.fill();
  ctx.restore();
}
function drawFoamOnTile(col,row,t){
  ctx.save();clipTilePath(col,row);ctx.clip();
  for(let i=0;i<18;i++){
    const tc=i/18,sp=iso(col+tc,row+(1-tc)*0.3,0.05);
    const pulse=Math.sin(t*0.07+col*1.1+i*0.8)*0.5+0.5;
    ctx.globalAlpha=0.5+pulse*0.45;ctx.fillStyle='#d8f2ff';
    ctx.beginPath();ctx.arc(sp.x,sp.y,3+pulse*4,0,Math.PI*2);ctx.fill();
  }
  ctx.globalAlpha=1;ctx.restore();
}

const waveRings=[];let waveTimer=0,nextWaveIn=60+Math.random()*80;
const SPAWN_ZONES=[[0.5,2.5],[2,4.5],[4,7],[6,9.5],[9,11.5],[0.5,11.5]];
function spawnWave(){
  const zone=SPAWN_ZONES[Math.floor(Math.random()*SPAWN_ZONES.length)];
  waveRings.push({col:zone[0]+Math.random()*(zone[1]-zone[0]),row:shoreD-(zone[0]+Math.random()*(zone[1]-zone[0]))+0.5+Math.random()*2.5,
    r:0,alpha:0.5+Math.random()*0.45,speed:0.008+Math.random()*0.022,decay:0.003+Math.random()*0.012});
  nextWaveIn=30+Math.random()*120;
}

function drawSky(){
  const g=ctx.createLinearGradient(0,0,0,SH*0.38);
  g.addColorStop(0,'#2e6898');g.addColorStop(1,'#70b0d0');
  ctx.fillStyle=g;ctx.fillRect(0,0,SW,SH);
  [[SW*.14,SH*.06,1],[SW*.50,SH*.03,.75],[SW*.80,SH*.09,.6]].forEach(([x,y,s])=>{
    ctx.save();ctx.translate(x,y);ctx.scale(s,s);ctx.fillStyle='#daeef8';
    [[0,7,42,13],[10,-4,30,13],[22,-13,22,13],[38,4,18,12]].forEach(([rx,ry,rw,rh])=>ctx.fillRect(rx,ry,rw,rh));
    ctx.restore();
  });
}

const CASTLE_BC=3,CASTLE_BR=3,CASTLE_MAX_HEALTH=800;
let castleHealth=CASTLE_MAX_HEALTH;
function isCastleTile(col,row){return col>=CASTLE_BC&&col<=CASTLE_BC+3&&row>=CASTLE_BR&&row<=CASTLE_BR+3;}

function drawIsoFlag(col,row,z,color,t){
  const base=iso(col+0.5,row+0.5,z),top={x:base.x,y:base.y-28};
  ctx.strokeStyle='#7a6030';ctx.lineWidth=2;
  ctx.beginPath();ctx.moveTo(base.x,base.y);ctx.lineTo(top.x,top.y);ctx.stroke();
  const wave=Math.sin(t*0.09)*5;
  ctx.fillStyle=color;ctx.beginPath();ctx.moveTo(top.x,top.y);
  ctx.lineTo(top.x+14+wave,top.y+5);ctx.lineTo(top.x+12+wave*.5,top.y+11);ctx.lineTo(top.x,top.y+8);
  ctx.closePath();ctx.fill();
}
function drawCastle(t){
  const BC=CASTLE_BC,BR=CASTLE_BR;
  for(let dc=0;dc<4;dc++)for(let dr=0;dr<4;dr++)isoBlock(BC+dc,BR+dr,0,0.4,'#dab84a','#b89030','#906810');
  for(let i=0;i<4;i++){
    isoBlock(BC+i,BR,  0.4,0.5,'#d0a840','#a88228','#806010');
    isoBlock(BC+i,BR+3,0.4,0.5,'#d0a840','#a88228','#806010');
    isoBlock(BC,  BR+i,0.4,0.5,'#d0a840','#a88228','#806010');
    isoBlock(BC+3,BR+i,0.4,0.5,'#d0a840','#a88228','#806010');
  }
  [[BC,BR],[BC+3,BR],[BC,BR+3],[BC+3,BR+3]].forEach(([c,r])=>{
    isoBlock(c,r,0.4,0.5,'#dab848','#b89030','#906810');
    isoBlock(c,r,0.9,0.5,'#dab848','#b89030','#906810');
    isoBlock(c,r,1.4,0.5,'#dab848','#b89030','#906810');
    isoBlock(c+0.1,r+0.1,1.9,0.35,'#e0c050','#c0a030','#907010');
    isoBlock(c+0.55,r+0.1,1.9,0.35,'#e0c050','#c0a030','#907010');
    isoBlock(c+0.1,r+0.55,1.9,0.35,'#e0c050','#c0a030','#907010');
  });
  for(let i=1;i<3;i++){
    isoBlock(BC+i,BR,  0.9,0.35,'#dabb48','#b89030','#906810');
    isoBlock(BC+i,BR+3,0.9,0.35,'#dabb48','#b89030','#906810');
    isoBlock(BC,  BR+i,0.9,0.35,'#dabb48','#b89030','#906810');
    isoBlock(BC+3,BR+i,0.9,0.35,'#dabb48','#b89030','#906810');
  }
  isoBlock(BC+1,BR+1,0.4,0.5,'#e0c050','#c0a030','#907010');
  isoBlock(BC+2,BR+1,0.4,0.5,'#e0c050','#c0a030','#907010');
  isoBlock(BC+1,BR+2,0.4,0.5,'#e0c050','#c0a030','#907010');
  isoBlock(BC+2,BR+2,0.4,0.5,'#e0c050','#c0a030','#907010');
  isoBlock(BC+1,BR+1,0.9,0.5,'#e8c855','#c8a835','#987515');
  isoBlock(BC+2,BR+1,0.9,0.5,'#e8c855','#c8a835','#987515');
  isoBlock(BC+1,BR+2,0.9,0.5,'#e8c855','#c8a835','#987515');
  isoBlock(BC+2,BR+2,0.9,0.5,'#e8c855','#c8a835','#987515');
  isoBlock(BC+1,BR+1,1.4,0.6,'#f0d060','#d0b040','#a08020');
  isoBlock(BC+2,BR+2,1.4,0.6,'#f0d060','#d0b040','#a08020');
  const gp=iso(BC+1.5,BR,0.4);
  ctx.fillStyle='#1a1000';ctx.beginPath();ctx.ellipse(gp.x-2,gp.y+2,8,13,0,Math.PI,0);ctx.fill();
  ctx.fillRect(gp.x-10,gp.y+2,16,10);
  drawIsoFlag(BC,    BR,    1.95,'#cc2020',t);
  drawIsoFlag(BC+3,  BR,    1.95,'#d4a010',t);
  drawIsoFlag(BC,    BR+3,  1.95,'#cc2020',t);
  drawIsoFlag(BC+3,  BR+3,  1.95,'#d4a010',t);
  drawIsoFlag(BC+1.5,BR+1.5,2.15,'#cc2020',t);
}

const BASE_WATER_DAMAGE_PER_SEC=8,BASE_SHORE_DAMAGE_PER_SEC=2,MAX_DEFENSE_REDUCTION=0.85;
const PIECE_DEFS={
  moat:      {health:60, defenseReduction:0.18,label:'Moat',       h:0.0},
  smallWall: {health:80, defenseReduction:0.28,label:'Small Wall', h:0.3,top:'#d4c060',left:'#b09a40',right:'#887020'},
  mediumWall:{health:120,defenseReduction:0.48,label:'Medium Wall',h:0.6,top:'#c8b050',left:'#a89030',right:'#806010'},
  tallWall:  {health:180,defenseReduction:0.68,label:'Tall Wall',  h:1.0,top:'#c0a848',left:'#a08828',right:'#786808'},
};
let placedPieces=[],selectedType='smallWall',hoverCol=-1,hoverRow=-1;

function getDefenseReduction(col,row){
  let rem=1.0;
  for(const p of placedPieces){
    if(Math.abs(p.col-col)>1||Math.abs(p.row-row)>1)continue;
    const def=PIECE_DEFS[p.type];
    rem*=(1-def.defenseReduction*(p.health/def.health));
  }
  return Math.min(1-rem,MAX_DEFENSE_REDUCTION);
}
function drawPiece(piece,isGhost){
  const def=PIECE_DEFS[piece.type],hp=isGhost?1:(piece.health/def.health),alpha=isGhost?0.4:(0.25+hp*0.75);
  if(piece.type==='moat'){
    ctx.save();ctx.globalAlpha=alpha;clipTilePath(piece.col,piece.row);ctx.clip();
    ctx.drawImage(wCanvas,0,0);
    if(!isGhost&&hp<0.6){ctx.fillStyle='rgba(160,100,30,'+(0.6-hp)*1.1+')';ctx.fill();}
    ctx.restore();
  } else {
    isoBlock(piece.col,piece.row,0,def.h*(0.5+hp*0.5),def.top,def.left,def.right,alpha);
  }
}

canvas.addEventListener('mousemove',e=>{
  const rect=canvas.getBoundingClientRect(),t=screenToIso(e.clientX-rect.left,e.clientY-rect.top);
  hoverCol=t.col;hoverRow=t.row;
});
canvas.addEventListener('mouseleave',()=>{hoverCol=-1;hoverRow=-1;});
canvas.addEventListener('click',e=>{
  const rect=canvas.getBoundingClientRect(),{col,row}=screenToIso(e.clientX-rect.left,e.clientY-rect.top);
  if(col<0||col>=GCOLS||row<0||row>=GROWS)return;
  if(isTileWater(col,row)||isCastleTile(col,row))return;
  const idx=placedPieces.findIndex(p=>p.col===col&&p.row===row);
  if(idx!==-1)placedPieces.splice(idx,1);
  placedPieces.push({col,row,type:selectedType,health:PIECE_DEFS[selectedType].health});
});
document.querySelectorAll('.pbtn').forEach(btn=>{
  btn.addEventListener('click',()=>{
    selectedType=btn.dataset.type;
    document.querySelectorAll('.pbtn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
  });
});

let tick=0;const DT=1/60;
function render(){
  tick++;
  tidePhase+=tideSpeed;edgeTime+=0.0007;
  const curSign=Math.cos(tidePhase)>0?1:-1;
  if(curSign===1&&lastTideSign===-1)randomizeTideCycle();
  lastTideSign=curSign;
  const targetD=tidePeak+getTideT()*(SHORE_LOW-tidePeak);
  shoreD+=(targetD-shoreD)*shoreSnap;
  waveTimer++;if(waveTimer>=nextWaveIn){spawnWave();waveTimer=0;}
  for(let i=waveRings.length-1;i>=0;i--){
    waveRings[i].r+=waveRings[i].speed;waveRings[i].alpha-=waveRings[i].decay;
    if(waveRings[i].alpha<=0)waveRings.splice(i,1);
  }
  if(castleHealth>0){
    for(let dc=0;dc<4;dc++)for(let dr=0;dr<4;dr++){
      const tc=CASTLE_BC+dc,tr=CASTLE_BR+dr;
      const inW=isTileWater(tc,tr),onS=!inW&&isShore(tc,tr);
      if(!inW&&!onS)continue;
      castleHealth-=(inW?BASE_WATER_DAMAGE_PER_SEC:BASE_SHORE_DAMAGE_PER_SEC)*DT*(1-getDefenseReduction(tc,tr));
    }
    castleHealth=Math.max(0,castleHealth);
  }
  for(let i=placedPieces.length-1;i>=0;i--){
    const piece=placedPieces[i],inWater=isTileWater(piece.col,piece.row),onShore=!inWater&&isShore(piece.col,piece.row);
    if(!inWater&&!onShore)continue;
    piece.health-=(inWater?BASE_WATER_DAMAGE_PER_SEC:BASE_SHORE_DAMAGE_PER_SEC)*DT*(1-getDefenseReduction(piece.col,piece.row));
    if(piece.health<=0)placedPieces.splice(i,1);
  }
  if(tick%3===0)buildWaterTex(tick*0.011);
  ctx.clearRect(0,0,SW,SH);drawSky();
  for(let d=0;d<GCOLS+GROWS;d++){
    for(let col=0;col<GCOLS;col++){
      const row=d-col;if(row<0||row>=GROWS)continue;
      if(isTileWater(col,row)){
        ctx.save();clipTilePath(col,row);ctx.clip();ctx.drawImage(wCanvas,0,0);ctx.restore();
        ctx.save();clipTilePath(col,row);ctx.strokeStyle='rgba(10,30,60,0.18)';ctx.lineWidth=0.8;ctx.stroke();ctx.restore();
      } else {
        const wet=isShore(col,row);
        ctx.save();clipTilePath(col,row);ctx.clip();ctx.drawImage(sCanvas,0,0);
        if(wet){ctx.fillStyle='rgba(40,80,120,0.22)';ctx.fill();}
        ctx.restore();
        waveRings.forEach(ring=>{
          const dp=iso(ring.col+ring.r*1.4,ring.row+ring.r,0.02);
          const rsx=ring.r*TW*0.9,rsy=ring.r*TH*0.9;
          if(rsx<2)return;
          ctx.save();clipTilePath(col,row);ctx.clip();
          ctx.globalAlpha=ring.alpha*0.38;ctx.strokeStyle='#a8d8f8';ctx.lineWidth=2;
          ctx.beginPath();ctx.ellipse(dp.x,dp.y,rsx,rsy*0.5,-0.5,0,Math.PI*2);ctx.stroke();
          ctx.globalAlpha=1;ctx.restore();
        });
      }
      if(isShore(col,row))drawFoamOnTile(col,row,tick);
      if(!isCastleTile(col,row)){
        const piece=placedPieces.find(p=>p.col===col&&p.row===row);
        if(piece)drawPiece(piece,false);
      }
      if(col===hoverCol&&row===hoverRow&&!isTileWater(col,row)&&!isCastleTile(col,row)&&!placedPieces.some(p=>p.col===col&&p.row===row))
        drawPiece({col,row,type:selectedType,health:PIECE_DEFS[selectedType].health},true);
    }
  }
  if(castleHealth>0){
    ctx.save();ctx.globalAlpha=0.2+(castleHealth/CASTLE_MAX_HEALTH)*0.8;drawCastle(tick);ctx.restore();
  }
  const tl=getTideT(),dir=Math.cos(tidePhase)>0?'rising':'falling';
  hud.textContent='tide: '+dir+' \xB7 '+Math.round(tl*100)+'%  \xB7  castle: '+Math.round(castleHealth/CASTLE_MAX_HEALTH*100)+'%  \xB7  pieces: '+placedPieces.length+'  \xB7  ['+PIECE_DEFS[selectedType].label+']';
  requestAnimationFrame(render);
}
buildWaterTex(0);randomizeTideCycle();spawnWave();spawnWave();spawnWave();render();
<\/script>
</body>
</html>`;

    return new Response(html, {
      headers: {
        'Content-Type': 'text/html; charset=utf-8'
      }
    });
  }
}
