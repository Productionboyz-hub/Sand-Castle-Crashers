#!/usr/bin/env python3
# Sand Castle Crashers - water v2 prototype. Applies exact-string replacements to a COPY of sandcastle_iso2.html.
#   visual:   low-res water texture (see-through shallows, swell, caustics, glints), swash that sloshes sideways,
#             wet sand + stranded foam, broken foam edge
#   gameplay: BIG WAVES in the defend phase surge to the castle; moats start empty, fill, drain; damage follows the
#             locked enemy chain (moat piece -> nearest wall -> castle)
# usage: patch_water2.py <in.html> <out.html>
import sys
src = open(sys.argv[1], encoding='utf-8').read()

def rep(old, new, count=1):
    global src
    assert src.count(old) == count, (src.count(old), old[:80])
    src = src.replace(old, new)

def rep_block(start, end, new):
    global src
    a = src.index(start); b = src.index(end, a)
    src = src[:a] + new + src[b:]

# ── 1. water texture + swash model ──────────────────────────────────────────────────────────────
rep_block("const wCanvas = document.createElement('canvas');", "// ── Sand texture offscreen", r'''// v0.9 water: built at 1/W_SCALE resolution and upscaled with smoothing (far fewer pixels than the old
// full-res build, so there is budget for swell, caustics and glints). Alpha is real: the first stretch of
// water is see-through so the sand shows under the shallows.
const W_SCALE = 3;
const WW = Math.ceil(SW / W_SCALE), WH = Math.ceil(SH / W_SCALE);
const wCanvas = document.createElement('canvas');
wCanvas.width = WW; wCanvas.height = WH;
const wCtx = wCanvas.getContext('2d');
const wImg = wCtx.createImageData(WW, WH);

// Depth-gradient stops, measured from the tide line (baseY), not from the surging edge.
const WATER_SHALLOW = [118, 212, 206];
const WATER_MID     = [36, 148, 186];
const WATER_DEEP    = [14, 60, 120];

function buildWaterTex(t) {
  const data = wImg.data;
  const th = TH();
  const rampSpan = SH * 0.42;
  const k1 = 6.2832 / (th * 2.6), k2 = 6.2832 / (th * 1.65); // two swell trains (wavelength in px)
  const drift = Math.sin(t * 0.13) * 0.35;                   // swell direction wanders over time
  const band = th * 0.6;                                     // lacy foam just behind the leading edge
  for (let x = 0; x < WW; x++) {
    const sx = x * W_SCALE;
    const edgeY = visShoreYAt(sx);            // where the water actually is right now (with surge)
    const tideY = baseShoreYAt(sx);           // the tide line the surge runs up from
    const y0 = Math.max(0, Math.floor(edgeY / W_SCALE) - 1);
    for (let y = 0; y < y0; y++) data[(y * WW + x) * 4 + 3] = 0;
    for (let y = y0; y < WH; y++) {
      const sy = y * W_SCALE;
      const dv = sy - edgeY;                  // px behind the leading edge
      const idx = (y * WW + x) * 4;
      if (dv < 0) { data[idx + 3] = 0; continue; }
      const dp = sy > tideY ? sy - tideY : 0; // depth for colour; 0 inside the thin run-up sheet
      const dT = Math.min(1, dp / rampSpan);
      const e = dT * dT * (3 - 2 * dT);
      let r, g, b;
      if (e < 0.4) { const u = e / 0.4;
        r = WATER_SHALLOW[0] + (WATER_MID[0] - WATER_SHALLOW[0]) * u;
        g = WATER_SHALLOW[1] + (WATER_MID[1] - WATER_SHALLOW[1]) * u;
        b = WATER_SHALLOW[2] + (WATER_MID[2] - WATER_SHALLOW[2]) * u;
      } else { const u = (e - 0.4) / 0.6;
        r = WATER_MID[0] + (WATER_DEEP[0] - WATER_MID[0]) * u;
        g = WATER_MID[1] + (WATER_DEEP[1] - WATER_MID[1]) * u;
        b = WATER_MID[2] + (WATER_DEEP[2] - WATER_MID[2]) * u;
      }
      const wx = sx / th, wy = sy / th;       // tile-relative, so the look is the same at any zoom
      const warp = fbm(wx * 0.22 + t * 0.05, wy * 0.22 - t * 0.04, 2);
      // swell crests rolling toward shore, bent by the warp so they never run as straight stripes
      const s = Math.sin(dp * k1 + t * 1.9 + warp * 5.5 + sx * k1 * drift) * 0.6
              + Math.sin(dp * k2 + t * 2.7 - warp * 4.0 - sx * k2 * (0.25 - drift)) * 0.4;
      const crest = s > 0 ? s * s * s : 0;
      const swellFade = (0.25 + 0.75 * (1 - e)) * Math.min(1, dp / (th * 0.4));
      // caustics: the shifting net of light in the shallows (and over the run-up sheet)
      const c1 = 1 - Math.abs(noise2(wx * 0.9 + t * 0.22, wy * 1.6 - t * 0.15));
      const c2 = 1 - Math.abs(noise2(wx * 1.1 - t * 0.17 + 31.7, wy * 1.9 + t * 0.2 + 11.3));
      const cc = c1 * c2;
      const caus = cc * cc * cc * cc * cc * (1 - e) * (1 - e);
      // sun glints riding the crests
      const gl = noise2(wx * 3.1 + t * 0.9, wy * 5.3 - t * 1.3);
      const glint = (crest > 0.3 && gl > 0.36) ? (gl - 0.36) * 3.2 : 0;
      const shade = warp * 26 + (s < 0 ? s : 0) * 22 * swellFade;
      const light = crest * 78 * swellFade + caus * 92 + glint * 150;
      r += shade * 0.5 + light * 0.85; g += shade * 0.8 + light * 0.95; b += shade + light;
      let a = 0.40 + 0.60 * Math.min(1, dp / (th * 1.5));
      if (dp === 0) {                         // run-up sheet: thin, streaky water sliding over the sand
        const streak = noise2(wx * 0.7 + t * 0.3, wy * 3.4 + t * 1.1);
        a = 0.36 + streak * 0.14;
        if (streak > 0.18) { const f = (streak - 0.18) * 1.5; r += (255 - r) * f; g += (255 - g) * f; b += (255 - b) * f; a += f * 0.4; }
      }
      if (dv < band) {
        const lace = noise2(wx * 2.3 + t * 0.5, wy * 4.2 + t * 0.9);
        const f = (1 - dv / band) * (lace > -0.05 ? 0.78 : 0.16);
        r += (255 - r) * f; g += (255 - g) * f; b += (255 - b) * f;
        if (f > a) a = f;
      }
      data[idx]     = r < 0 ? 0 : r > 255 ? 255 : r;
      data[idx + 1] = g < 0 ? 0 : g > 255 ? 255 : g;
      data[idx + 2] = b < 0 ? 0 : b > 255 ? 255 : b;
      data[idx + 3] = a > 1 ? 255 : a * 255;
    }
  }
  wCtx.putImageData(wImg, 0, 0);
}

// ── SWASH + BIG WAVES (v0.9) ──────────────────────────────────────
// The visible water edge = tide line (shoreYAtScreenX) minus a run-up that comes in uneven sets and
// sloshes sideways along the beach. Ordinary swash is DRAWING ONLY: isTileWater() is untouched and stays
// the single source of truth for building, crabs and tourists.
// BIG WAVES are the one gameplay hook: in the defend phase a big wave draws back, surges to the castle,
// and applyBigWaveHit() damages defences with the locked chain (moat piece -> nearest wall -> castle).
const SWASH_STEP = 8;
const SWASH_N = Math.ceil(SW / SWASH_STEP) + 2;
const visY = new Float32Array(SWASH_N), prevVisY = new Float32Array(SWASH_N), baseY = new Float32Array(SWASH_N);
const wetY = new Float32Array(SWASH_N), wetAge = new Float32Array(SWASH_N);
const swashWaves = [];
let swashNext = 30, swashReady = false;

// ← TUNE: big-wave gameplay
const BIGWAVE_FIRST      = 480;   // ticks into a defend phase before the first big wave can come
const BIGWAVE_GAP_MIN    = 700;   // ticks between big waves (min) — 60 ticks = 1 second
const BIGWAVE_GAP_MAX    = 1500;  // ticks between big waves (max)
const BIGWAVE_MOAT_DMG   = 34;    // health a moat piece loses when it absorbs a big wave
const BIGWAVE_WALL_DMG   = 40;    // health the nearest wall loses when no moat is in the way
const BIGWAVE_CASTLE_HITS = 3;    // damageCastle() calls when nothing is in the way
const BIGWAVE_GUARD_RADIUS = 6.5; // a piece must be within this many tiles of the castle centre to count
let bigWave = null;               // the one active big wave, or null
let bigWaveTimer = BIGWAVE_FIRST;
let bigWaveWarn = 0;              // frames left on the on-screen warning
let ringFill = 0;                 // 0 = castle ring dry, 1 = full (drawing only)

function spawnSwashWave() {
  const th = TH();
  const big = Math.random() < 0.25;
  const dir = Math.random() < 0.5 ? -1 : 1;
  swashWaves.push({
    born: tick | 0,
    amp: th * (0.35 + Math.random() * 0.85) * (big ? 1.6 : 1),          // up to ~2 tiles of run-up
    rise: 30 + Math.random() * 40, fall: 80 + Math.random() * 150,
    seed: Math.random() * 100,
    dir, v: 1.5 + Math.random() * 5.5,                                  // sideways travel, px per tick
    x0: dir > 0 ? -SW * 0.15 + Math.random() * SW * 0.5 : SW * 1.15 - Math.random() * SW * 0.5,
    sig: SW * (0.12 + Math.random() * 0.3), base: Math.random() * 0.45,
  });
  swashNext = (tick | 0) + (Math.random() < 0.3 ? 12 + Math.random() * 30 : 50 + Math.random() * 170); // sometimes a quick double
}

function spawnBigWave() {
  const th = TH();
  const c = iso(5, 5, 0);                    // castle centre
  const far = iso(2, 2, 0);                  // far corner of the castle ring
  const amp = Math.max(th * 2.2, baseShoreYAt(c.x) - far.y + th * 0.6);
  bigWave = { born: tick | 0, amp, cx: c.x, sig: TW() * (4.5 + Math.random() * 2.5),
    back: th * (0.7 + Math.random() * 0.6), draw: 55, rise: 60, hold: 35, fall: 190,
    sl: Math.random() * 6.28, slAmp: TW() * (1.2 + Math.random() * 1.6), hit: false };
  bigWaveWarn = 150;
}

function updateSwash(tk) {
  const th = TH();
  if (tk >= swashNext) spawnSwashWave();
  for (let i = swashWaves.length - 1; i >= 0; i--) {
    const w = swashWaves[i];
    if (tk - w.born > w.rise + w.fall + 60) swashWaves.splice(i, 1);
  }
  let bAge = -1, bA = 0, bC = 0;
  if (bigWave) {
    bAge = tk - bigWave.born;
    const w = bigWave;
    if (bAge < w.draw) bA = -w.back * Math.sin(Math.PI * bAge / w.draw);                       // draws back first
    else if (bAge < w.draw + w.rise) { const u = (bAge - w.draw) / w.rise; bA = w.amp * (1 - (1 - u) * (1 - u) * (1 - u)); }
    else if (bAge < w.draw + w.rise + w.hold) bA = w.amp * (1 - 0.05 * Math.sin((bAge - w.draw - w.rise) * 0.2));
    else { const u = (bAge - w.draw - w.rise - w.hold) / w.fall; if (u >= 1) { bigWave = null; bA = 0; } else { const q = 1 - u; bA = w.amp * q * q * (3 - 2 * q); } }
    bC = w.cx + (bAge > w.draw ? Math.sin((bAge - w.draw) * 0.028 + w.sl) * w.slAmp : 0);   // sloshes left and right
  }
  for (let i = 0; i < SWASH_N; i++) {
    const sx = i * SWASH_STEP;
    let run = 0;
    for (let j = 0; j < swashWaves.length; j++) {
      const w = swashWaves[j];
      const age = (tk - w.born) - (noise2(sx * 0.0035 + w.seed, w.seed * 0.7) + 0.5) * 30;
      if (age <= 0) continue;
      let a;
      if (age < w.rise) { const u = age / w.rise; a = 1 - (1 - u) * (1 - u); }
      else { const u = (age - w.rise) / w.fall; if (u >= 1) continue; a = 1 - u; a = a * a * (3 - 2 * a); }
      const dx = (sx - (w.x0 + w.dir * w.v * age)) / w.sig;               // the bulge travels along the beach
      const lat = w.base + (1 - w.base) * Math.exp(-dx * dx);
      const rr = a * w.amp * lat * (0.75 + 0.25 * (noise2(sx * 0.006 + w.seed * 3.1, 5.5) + 0.5));
      if (rr > run) run = rr;
    }
    if (bigWave) {
      const dx = (sx - bC) / bigWave.sig;
      const lat = Math.exp(-dx * dx);
      if (bA < 0) run += bA * (0.45 + 0.55 * lat);
      else { const rr = bA * lat; if (rr > run) run = rr; }
    }
    const chop = Math.sin(sx * 0.045 + tk * 0.05) * 1.2 + Math.sin(sx * 0.013 - tk * 0.031) * 1.6;
    const b0 = shoreYAtScreenX(sx) + chop;
    const y = b0 - run;
    baseY[i] = b0;
    prevVisY[i] = swashReady ? visY[i] : y;
    visY[i] = y;
    if (!swashReady || y <= wetY[i]) { wetY[i] = y; wetAge[i] = 0; }
    else { wetY[i] = Math.min(y, wetY[i] + Math.max(th * 0.004, (y - wetY[i]) * 0.007)); wetAge[i]++; }
  }
  swashReady = true;
}

function swashLerp(arr, sx) {
  if (!swashReady) updateSwash(0);
  const f = sx / SWASH_STEP;
  const i = f < 0 ? 0 : f > SWASH_N - 2 ? SWASH_N - 2 : f | 0;
  return arr[i] + (arr[i + 1] - arr[i]) * (f - i);
}
function visShoreYAt(sx)  { return swashLerp(visY, sx); }
function baseShoreYAt(sx) { return swashLerp(baseY, sx); }

// Is this grid point under the SURGE right now? Used only by the big-wave hazard and the moat fill
// drawing. Building, crabs, tourists and the truck keep using isTileWater() (the tide).
function isSurgeWet(col, row) {
  const q = iso(col + 0.5, row + 0.5, 0);
  return q.y > visShoreYAt(q.x);
}

function applyBigWaveHit() {
  if (gameOver) return;
  ringFill = 1;
  const near = p => Math.hypot(p.col - 5, p.row - 5) <= BIGWAVE_GUARD_RADIUS && isSurgeWet(p.col, p.row);
  // 1. moat pieces in the water absorb the wave
  const moats = placedPieces.filter(p => p.id.indexOf('moat-') === 0 && near(p));
  if (moats.length) {
    moats.forEach(p => { p.health = Math.max(0, p.health - BIGWAVE_MOAT_DMG); p.fill = 1; });
    return;
  }
  // 2. otherwise the nearest wall / drawbridge on the castle's sea side takes it
  let best = null, bestD = 1e9;
  for (const p of placedPieces) {
    if (p.id.indexOf('moat-') === 0 || !near(p)) continue;
    const d = Math.hypot(p.col - 7, p.row - 7);
    if (d < bestD) { bestD = d; best = p; }
  }
  if (best) { best.health = Math.max(0, best.health - BIGWAVE_WALL_DMG); return; }
  // 3. nothing in the way: the castle itself
  for (let i = 0; i < BIGWAVE_CASTLE_HITS; i++) damageCastle();
}

// Called once per frame from render(), right after tickDeterioration().
function tickSurge() {
  if (ringFill > 0) ringFill = Math.max(0, ringFill - 0.0035);
  if (isSurgeWet(7, 7) || isSurgeWet(7, 4) || isSurgeWet(4, 7)) ringFill = 1;
  for (const p of placedPieces) {
    if (p.id.indexOf('moat-') !== 0) continue;
    if (isSurgeWet(p.col, p.row)) p.fill = 1;
    else if (p.fill > 0) p.fill = Math.max(0, p.fill - 0.004);
  }
  if (bigWaveWarn > 0) bigWaveWarn--;
  if (bigWave && !bigWave.hit && tick - bigWave.born >= bigWave.draw + bigWave.rise) { bigWave.hit = true; applyBigWaveHit(); }
  if (gameOver || wavePhase !== 'defend') { bigWaveTimer = BIGWAVE_FIRST; return; }
  if (!bigWave && --bigWaveTimer <= 0) {
    spawnBigWave();
    bigWaveTimer = BIGWAVE_GAP_MIN + Math.random() * (BIGWAVE_GAP_MAX - BIGWAVE_GAP_MIN);
  }
}

function drawBigWaveWarning() {
  if (bigWaveWarn <= 0) return;
  const a = Math.min(1, bigWaveWarn / 30) * (0.65 + 0.35 * Math.sin(tick * 0.3));
  ctx.save();
  ctx.textAlign = 'center';
  ctx.font = 'bold ' + Math.round(Math.min(34, SW * 0.05)) + 'px monospace';
  ctx.fillStyle = 'rgba(8,16,26,' + (0.55 * a).toFixed(2) + ')';
  const tw = ctx.measureText('BIG WAVE!').width + 36;
  ctx.beginPath(); ctx.roundRect(SW / 2 - tw / 2, SH * 0.16 - 32, tw, 46, 10); ctx.fill();
  ctx.fillStyle = 'rgba(140,225,255,' + a.toFixed(2) + ')';
  ctx.fillText('BIG WAVE!', SW / 2, SH * 0.16);
  ctx.restore();
}

''')

# ── 2. shoreline path follows the surging edge; wet sand; texture drawn scaled ──────────────────
rep_block("function buildShorelinePath() {", "// Drawing-only: for a given screen x", r'''function buildShorelinePath() {
  ctx.beginPath();
  ctx.moveTo(0, visY[0]);
  for (let i = 1; i < SWASH_N; i++) ctx.lineTo(i * SWASH_STEP, visY[i]);
  ctx.lineTo(SW, SH);
  ctx.lineTo(0, SH);
  ctx.closePath();
}

// Dark, glossy sand where a wave has just been, plus the thin foam line it strands as it retreats.
function drawWetSand() {
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(0, wetY[0]);
  for (let i = 1; i < SWASH_N; i++) ctx.lineTo(i * SWASH_STEP, wetY[i]);
  for (let i = SWASH_N - 1; i >= 0; i--) ctx.lineTo(i * SWASH_STEP, visY[i] + 3);
  ctx.closePath();
  ctx.fillStyle = 'rgba(72,52,28,0.36)'; ctx.fill();
  ctx.fillStyle = 'rgba(170,215,235,0.11)'; ctx.fill();   // sky sheen on the wet surface
  ctx.lineCap = 'round';
  for (let i = 0; i < SWASH_N - 1; i++) {
    if (visY[i] - wetY[i] < 3) continue;
    const a = 0.55 - wetAge[i] / 150;
    if (a <= 0.02) continue;
    const n = noise2(i * 0.37, 3.3);
    if (n < -0.2) continue;
    ctx.strokeStyle = 'rgba(240,250,255,' + a.toFixed(2) + ')';
    ctx.lineWidth = 1 + (n + 0.3) * 2;
    ctx.beginPath();
    ctx.moveTo(i * SWASH_STEP, wetY[i] + 1);
    ctx.lineTo((i + 1) * SWASH_STEP, wetY[i + 1] + 1);
    ctx.stroke();
  }
  ctx.restore();
}

function drawOceanOverlay() {
  drawWetSand();
  buildShorelinePath();
  ctx.save();
  ctx.clip();
  ctx.imageSmoothingEnabled = true;
  ctx.drawImage(wCanvas, 0, 0, SW, SH);
  ctx.restore();
}

''')

# ── 3. foam edge ────────────────────────────────────────────────────────────────────────────────
rep_block("const FOAM_LINES = [", "function drawCastle(t) {", r'''function drawShoreFoamBand(t) {
  const z = TH() / 28;
  ctx.save();
  ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  // soft underlay
  ctx.beginPath();
  ctx.moveTo(0, visY[0] + 3 * z);
  for (let i = 1; i < SWASH_N; i++) ctx.lineTo(i * SWASH_STEP, visY[i] + 3 * z);
  ctx.strokeStyle = 'rgba(235,250,255,0.34)';
  ctx.lineWidth = 9 * z;
  ctx.stroke();
  // crisp leading edge: thicker where the water is advancing, with gaps so it is never one even ribbon
  for (let i = 0; i < SWASH_N - 1; i++) {
    const n = noise2(i * 0.21 + t * 0.004, 7.7);
    if (n < -0.38) continue;
    const adv = Math.min(4, Math.max(0, prevVisY[i] - visY[i]));
    ctx.strokeStyle = 'rgba(248,253,255,' + Math.min(0.97, 0.7 + adv * 0.3 + n * 0.2).toFixed(2) + ')';
    ctx.lineWidth = (2.0 + adv * 2.4 + (n + 0.5) * 2.4) * z;
    ctx.beginPath();
    ctx.moveTo(i * SWASH_STEP, visY[i]);
    ctx.lineTo((i + 1) * SWASH_STEP, visY[i + 1]);
    ctx.stroke();
  }
  // bubbles trailing just behind the edge
  ctx.fillStyle = '#e6f6ff';
  for (let i = 0; i < SWASH_N; i += 2) {
    const n = noise2(i * 0.5, t * 0.012);
    if (n < 0.08) continue;
    ctx.globalAlpha = 0.35 + n * 0.9;
    ctx.beginPath();
    ctx.ellipse(i * SWASH_STEP + n * 11, visY[i] + (5 + n * 16) * z, (1.4 + n * 4.5) * z, (0.8 + n * 2.2) * z, 0, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.globalAlpha = 1;
  ctx.restore();
}

''')

# ── 4. castle ring: a dry trench that fills when the surge reaches it, then drains (drawing only) ──
rep("""    clipTilePath(c,r); ctx.clip();
    ctx.drawImage(wCanvas,0,0);
    ctx.restore();
    const pulse = Math.sin(t*0.06+c*0.7+r*0.5)*0.5+0.5;
    drawTileTop(c,r,`rgba(200,240,255,${0.15+pulse*0.15})`);""",
"""    clipTilePath(c,r); ctx.clip();
    ctx.fillStyle='#a8823f'; ctx.fill();                       // dry trench floor
    ctx.fillStyle='rgba(60,40,15,0.28)'; ctx.fill();
    if (ringFill > 0) { ctx.globalAlpha = Math.min(1, ringFill * 1.6); ctx.fillStyle='#58c2da'; ctx.fill(); ctx.globalAlpha = 1; }
    ctx.restore();
    const pulse = Math.sin(t*0.06+c*0.7+r*0.5)*0.5+0.5;
    if (ringFill > 0) drawTileTop(c,r,`rgba(200,240,255,${(0.15+pulse*0.15)*Math.min(1, ringFill*1.6)})`);""")

# ── 5. placed moat pieces: empty trench, water drawn at the piece's fill level ──────────────────
rep("""      const [c1,c2] = colors[id];
      const g = ctx.createLinearGradient(p.x,p.y,pb.x,pb.y);
      g.addColorStop(0,c1); g.addColorStop(1,c2);
      ctx.fillStyle=g; ctx.beginPath();
      ctx.moveTo(p.x,p.y);ctx.lineTo(pr.x,pr.y);ctx.lineTo(pb.x,pb.y);ctx.lineTo(pf.x,pf.y);
      ctx.closePath();ctx.fill();
      // Shimmer line
      ctx.strokeStyle='rgba(140,210,255,0.35)'; ctx.lineWidth=1;""",
"""      const [c1,c2] = colors[id];
      // v0.9: a moat is a dry trench until the surge fills it (p.fill 0..1), then it drains
      const mp = placedPieces.find(q => q.col === col && q.row === row);
      const mFill = mp && mp.fill ? Math.min(1, mp.fill * 1.6) : 0;
      const dry = { 'moat-shallow': ['#b08a48','#96743a'], 'moat-standard': ['#9c7838','#7c5c28'], 'moat-deep': ['#84622c','#5c421a'] }[id];
      const gd = ctx.createLinearGradient(p.x,p.y,pb.x,pb.y);
      gd.addColorStop(0,dry[0]); gd.addColorStop(1,dry[1]);
      ctx.fillStyle=gd; ctx.beginPath();
      ctx.moveTo(p.x,p.y);ctx.lineTo(pr.x,pr.y);ctx.lineTo(pb.x,pb.y);ctx.lineTo(pf.x,pf.y);
      ctx.closePath();ctx.fill();
      const g = ctx.createLinearGradient(p.x,p.y,pb.x,pb.y);
      g.addColorStop(0,c1); g.addColorStop(1,c2);
      const ga0 = ctx.globalAlpha;
      ctx.globalAlpha = ga0 * mFill;
      ctx.fillStyle=g; ctx.beginPath();
      ctx.moveTo(p.x,p.y);ctx.lineTo(pr.x,pr.y);ctx.lineTo(pb.x,pb.y);ctx.lineTo(pf.x,pf.y);
      ctx.closePath();ctx.fill();
      ctx.globalAlpha = ga0;
      // Shimmer line (trench rim when dry)
      ctx.strokeStyle = mFill > 0.05 ? 'rgba(140,210,255,0.35)' : 'rgba(60,40,15,0.45)'; ctx.lineWidth=1;""")

# ── 6. render loop hooks ────────────────────────────────────────────────────────────────────────
rep("  if(tick%3===0) buildWaterTex(tick*0.011);",
    "  updateSwash(tick);\n  if(tick%2===0) buildWaterTex(tick*0.011);")
rep("  tickDeterioration();  // ← decay placed pieces each frame\n",
    "  tickDeterioration();  // ← decay placed pieces each frame\n  tickSurge();          // ← big-wave schedule + damage, moat fill/drain\n")
rep("  drawCastleHUD();        // ← castle HP bar upper-left\n",
    "  drawCastleHUD();        // ← castle HP bar upper-left\n  drawBigWaveWarning();   // ← 'BIG WAVE!' banner while one is coming\n")

# ── 7. restart reset list (both handlers) + wave start ─────────────────────────────────────────
rep("  healthPeekCol = -1; healthPeekRow = -1; healthPeekTimer = 0;\n  selectedCounter = null;",
    "  healthPeekCol = -1; healthPeekRow = -1; healthPeekTimer = 0;\n  bigWave = null; bigWaveTimer = BIGWAVE_FIRST; bigWaveWarn = 0; ringFill = 0;\n  selectedCounter = null;", count=2)
rep("  wavePhase = 'defend';\n  waveSpawnsRemaining = waveBudget();",
    "  wavePhase = 'defend';\n  bigWaveTimer = BIGWAVE_FIRST;\n  waveSpawnsRemaining = waveBudget();")

open(sys.argv[2], 'w', encoding='utf-8').write(src)
print('patched ->', sys.argv[2])
