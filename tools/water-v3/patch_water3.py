#!/usr/bin/env python3
# Sand Castle Crashers - water v3: applied ON TOP of patch_water2.py's output.
#   1 the surge stops at the moat / castle (barrier clamp)   2 moats pour in and dry up
#   3 walls and the castle melt with health                  4 more side-to-side slosh, scalloped edge
# usage: patch_water3.py <v2.html> <out.html>
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

# ── state ───────────────────────────────────────────────────────────────────────────────────────
rep("const wetY = new Float32Array(SWASH_N), wetAge = new Float32Array(SWASH_N);",
    "const wetY = new Float32Array(SWASH_N), wetAge = new Float32Array(SWASH_N);\n"
    "const rawY = new Float32Array(SWASH_N);      // where the surge WOULD reach with nothing in its way\n"
    "const barrierY = new Float32Array(SWASH_N);  // sea-side edge of the castle ring / placed defences, per screen column\n"
    "const pressed = new Float32Array(SWASH_N);   // px of surge held back by the barrier (drives the foam pile-up)\n"
    "let surgeCapY = -1e9;                        // no surge is drawn above this screen y (set each frame by buildBarrier)")
rep("let ringFill = 0;                 // 0 = castle ring dry, 1 = full (drawing only)",
    "let ringCover = 0, ringDepth = 0, ringDamp = 0, ringFeed = 0; // castle ring: how far the water has poured round, how deep, how damp (drawing only)\n"
    "let castleShown = 100;            // castle health as DRAWN - eases toward castleHP so the castle melts instead of popping\n"
    "let pieceDrawHealth = 100;        // set by drawPlacedPieces() so walls draw melted to their health\n"
    "let meltCutZ = 1e9;\n"
    "let tiltPhase = Math.random() * 6.28;\n"
    "// the 17 ring tiles (same list drawMoat uses) and the castle footprint, as barrier tiles\n"
    "const RING_TILES = [[2,3],[3,2],[4,2],[5,2],[6,2],[7,3],[7,4],[7,5],[7,6],[7,7],[6,7],[5,7],[4,7],[3,7],[2,6],[2,5],[2,4]];")

# ── big wave: aims at the castle FRONT (it can no longer run past), longer hold, wider slosh ─────
rep("""  const far = iso(2, 2, 0);                  // far corner of the castle ring
  const amp = Math.max(th * 2.2, baseShoreYAt(c.x) - far.y + th * 0.6);
  bigWave = { born: tick | 0, amp, cx: c.x, sig: TW() * (4.5 + Math.random() * 2.5),
    back: th * (0.7 + Math.random() * 0.6), draw: 55, rise: 60, hold: 35, fall: 190,
    sl: Math.random() * 6.28, slAmp: TW() * (1.2 + Math.random() * 1.6), hit: false };""",
"""  const far = iso(2, 2, 0);                  // far corner of the castle ring
  // rawY (the surge's own reach) goes right round the castle so every sea-facing moat gets fed;
  // what is DRAWN is held at the barrier / surge cap, so the water never runs past the castle.
  const amp = Math.max(th * 2.2, baseShoreYAt(c.x) - far.y + th * 0.5);
  bigWave = { born: tick | 0, amp, cx: c.x, sig: TW() * (4.5 + Math.random() * 2),
    back: th * (0.8 + Math.random() * 0.7), draw: 55, rise: 55, hold: 90, fall: 200,
    sl: Math.random() * 6.28, slAmp: TW() * (2.4 + Math.random() * 1.8), hit: false };""")
rep("bC = w.cx + (bAge > w.draw ? Math.sin((bAge - w.draw) * 0.028 + w.sl) * w.slAmp : 0);   // sloshes left and right",
    "bC = w.cx + (bAge > w.draw ? Math.sin((bAge - w.draw) * 0.05 + w.sl) * w.slAmp : 0);    // sloshes left and right")

# ordinary swash travels sideways faster
rep("dir, v: 1.5 + Math.random() * 5.5,", "dir, v: 3 + Math.random() * 8,")

# ── barrier + tilt + scallops in the per-column loop ────────────────────────────────────────────
rep("""  for (let i = 0; i < SWASH_N; i++) {
    const sx = i * SWASH_STEP;
    let run = 0;
    for (let j = 0; j < swashWaves.length; j++) {""",
"""  buildBarrier();
  // see-saw: the whole waterline rocks, one end up while the other goes down
  const tilt = Math.sin(tk * 0.021 + tiltPhase) * th * 0.6 * (noise2(tk * 0.003, 9.1) + 0.7);
  for (let i = 0; i < SWASH_N; i++) {
    const sx = i * SWASH_STEP;
    let run = 0;
    for (let j = 0; j < swashWaves.length; j++) {""")
rep("""    const chop = Math.sin(sx * 0.045 + tk * 0.05) * 1.2 + Math.sin(sx * 0.013 - tk * 0.031) * 1.6;
    const b0 = shoreYAtScreenX(sx) + chop;
    const y = b0 - run;
    baseY[i] = b0;""",
"""    if (run > 0) run *= 1 + 0.16 * Math.abs(Math.sin(sx * 0.02 + tk * 0.012));   // scalloped, shell-ribbed edge
    run += tilt * (sx / SW - 0.5) * 2;
    const chop = Math.sin(sx * 0.045 + tk * 0.05) * 1.2 + Math.sin(sx * 0.013 - tk * 0.031) * 1.6;
    const b0 = shoreYAtScreenX(sx) + chop;
    let y = b0 - run;
    rawY[i] = y;
    pressed[i] = 0;
    // the surge stops at the castle ring / placed defences. (If the TIDE itself is already past them, leave it.)
    // Beside the castle it may wrap up to surgeCapY (a little above the castle's sea-side corner) and no further.
    const lim = barrierY[i] > surgeCapY ? barrierY[i] : surgeCapY;
    if (b0 > lim && y < lim) {
      if (barrierY[i] > -1e8) { pressed[i] = lim - y; y = lim; }          // hard stop at the castle / defences
      else {                                                               // beside it: a soft, rounded, moving crest
        const soft = th * 0.9;
        y = lim - soft * (1 - Math.exp(-(lim - y) / soft)) * (0.75 + 0.25 * Math.sin(sx * 0.03 + tk * 0.06));
      }
    }
    baseY[i] = b0;""")

# ── helpers + gameplay: replace isSurgeWet..drawBigWaveWarning ──────────────────────────────────
rep_block("// Is this grid point under the SURGE right now?", "function drawBigWaveWarning() {", r'''function rawShoreYAt(sx) { return swashLerp(rawY, sx); }

// Sea-side edge (screen y) of everything the surge has to stop at, sampled per screen column:
// the castle ring, plus any placed piece close enough to the castle to be defending it.
function addBarrierTile(c, r) {
  const L = iso(c, r + 1, 0), B = iso(c + 1, r + 1, 0), R = iso(c + 1, r, 0);
  const i0 = Math.max(0, Math.ceil(L.x / SWASH_STEP)), i1 = Math.min(SWASH_N - 1, Math.floor(R.x / SWASH_STEP));
  for (let i = i0; i <= i1; i++) {
    const x = i * SWASH_STEP;
    const y = x <= B.x ? L.y + (B.y - L.y) * (x - L.x) / (B.x - L.x || 1) : B.y + (R.y - B.y) * (x - B.x) / (R.x - B.x || 1);
    if (y > barrierY[i]) barrierY[i] = y;
  }
}
function guardsCastle(p) { return Math.hypot(p.col - 5, p.row - 5) <= BIGWAVE_GUARD_RADIUS; }
function buildBarrier() {
  barrierY.fill(-1e9);
  for (let k = 0; k < RING_TILES.length; k++) addBarrierTile(RING_TILES[k][0], RING_TILES[k][1]);
  for (const p of placedPieces) if (guardsCastle(p)) addBarrierTile(p.col, p.row);
  // the furthest-seaward point of the barrier; the surge may wrap ~1.6 tile-heights above it, beside the castle
  let frontY = -1e9;
  for (let i = 0; i < SWASH_N; i++) if (barrierY[i] > frontY) frontY = barrierY[i];
  surgeCapY = frontY - TH() * 1.6;
}

// Has the surge reached this tile's sea-side corner? (rawY = the surge before the barrier stops it.)
// Used only by the big-wave hazard and the moat pour. Building, crabs, tourists and the truck keep
// using isTileWater() (the tide).
function surgeReaches(col, row) {
  const f = iso(col + 1, row + 1, 0);
  return rawShoreYAt(f.x) <= f.y + 2;
}

function applyBigWaveHit() {
  if (gameOver) return;
  const hit = p => guardsCastle(p) && surgeReaches(p.col, p.row);
  // 1. moat pieces the wave reaches absorb it (they pour full in tickSurge)
  const moats = placedPieces.filter(p => p.id.indexOf('moat-') === 0 && hit(p));
  if (moats.length) { moats.forEach(p => { p.health = Math.max(0, p.health - BIGWAVE_MOAT_DMG); }); return; }
  // no moat held it: the water reaches the castle ring and pours in
  ringFeed = bigWave ? bigWave.hold + 90 : 160;
  // 2. the nearest wall / drawbridge on the castle's sea side takes it
  let best = null, bestD = 1e9;
  for (const p of placedPieces) {
    if (p.id.indexOf('moat-') === 0 || !hit(p)) continue;
    const d = Math.hypot(p.col - 7, p.row - 7);
    if (d < bestD) { bestD = d; best = p; }
  }
  if (best) { best.health = Math.max(0, best.health - BIGWAVE_WALL_DMG); return; }
  // 3. nothing in the way: the castle itself
  for (let i = 0; i < BIGWAVE_CASTLE_HITS; i++) damageCastle();
}

// Called once per frame from render(), right after tickDeterioration().
function tickSurge() {
  castleShown += (castleHP - castleShown) * 0.035;
  // placed moats: pour while the surge reaches them, then dry up
  let moatHolding = false;
  for (const p of placedPieces) {
    if (p.id.indexOf('moat-') !== 0) continue;
    const fed = surgeReaches(p.col, p.row);
    if (fed && guardsCastle(p)) moatHolding = true;
    if (fed) { p.cover = Math.min(1, (p.cover || 0) + 0.013); p.depth = Math.min(1, (p.depth || 0) + 0.05); p.damp = 1; }
    else {
      if (p.depth > 0) { p.depth = Math.max(0, p.depth - 0.0035); if (p.depth === 0) p.cover = 0; }
      if (p.damp > 0) p.damp = Math.max(0, p.damp - 0.0012);
    }
  }
  // castle ring: pours round from the sea-side corner while a wave is against it, then dries up
  if (ringFeed > 0) ringFeed--;
  const ringFed = ringFeed > 0 || (!moatHolding && surgeReaches(7, 7));
  if (ringFed) { ringCover = Math.min(1, ringCover + 0.008); ringDepth = Math.min(1, ringDepth + 0.05); ringDamp = 1; }
  else {
    if (ringDepth > 0) { ringDepth = Math.max(0, ringDepth - 0.003); if (ringDepth === 0) ringCover = 0; }
    if (ringDamp > 0) ringDamp = Math.max(0, ringDamp - 0.001);
  }
  if (bigWaveWarn > 0) bigWaveWarn--;
  if (bigWave && !bigWave.hit && tick - bigWave.born >= bigWave.draw + bigWave.rise) { bigWave.hit = true; applyBigWaveHit(); }
  if (gameOver || wavePhase !== 'defend') { bigWaveTimer = BIGWAVE_FIRST; return; }
  if (!bigWave && --bigWaveTimer <= 0) {
    spawnBigWave();
    bigWaveTimer = BIGWAVE_GAP_MIN + Math.random() * (BIGWAVE_GAP_MAX - BIGWAVE_GAP_MIN);
  }
}

// Water pouring across one tile from its sea-side corner: cover 0..1 = how far it has spread,
// depth 0..1 = how much is left (it dries by fading in place). Colours c1 -> c2 down the tile.
function drawPoolOnTile(col, row, cover, depth, c1, c2) {
  if (cover <= 0.001 || depth <= 0.001) return;
  const s = 2 * (1 - cover);                 // wet where u + v >= s  (u,v = 0..1 across the tile)
  const pts = s >= 1 ? [[1, s - 1], [1, 1], [s - 1, 1]] : [[s, 0], [1, 0], [1, 1], [0, 1], [0, s]];
  const a0 = ctx.globalAlpha;
  const top = iso(col, row, 0), bot = iso(col + 1, row + 1, 0);
  const g = ctx.createLinearGradient(top.x, top.y, bot.x, bot.y);
  g.addColorStop(0, c1); g.addColorStop(1, c2);
  ctx.globalAlpha = a0 * Math.min(1, depth * 1.5);
  ctx.fillStyle = g;
  ctx.beginPath();
  pts.forEach((q, k) => { const w = iso(col + q[0], row + q[1], 0.01); if (k) ctx.lineTo(w.x, w.y); else ctx.moveTo(w.x, w.y); });
  ctx.closePath(); ctx.fill();
  if (cover < 0.995) {                       // foamy front while it is still pouring
    const A = iso(col + pts[0][0], row + pts[0][1], 0.01), Z = iso(col + pts[pts.length - 1][0], row + pts[pts.length - 1][1], 0.01);
    ctx.strokeStyle = 'rgba(245,252,255,0.9)'; ctx.lineWidth = 2; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(A.x, A.y); ctx.lineTo(Z.x, Z.y); ctx.stroke();
  }
  ctx.globalAlpha = a0;
}

// Castle + walls melt: blocks are cut off above a height that drops with health.
function castleCutZ() { return 0.5 + 1.95 * Math.max(0, castleShown) / CASTLE_MAX_HP; }
function castleBlock(c, r, z, h, a, b, d) {
  const cut = castleCutZ();
  if (z >= cut) return;
  isoBlock(c, r, z, Math.min(h, cut - z), a, b, d);
}
function meltBlock(c, r, z, h, a, b, d) {
  if (z >= meltCutZ) return;
  isoBlock(c, r, z, Math.min(h, meltCutZ - z), a, b, d);
}

''')

# ── foam piles up where the barrier holds the surge back ────────────────────────────────────────
rep("    ctx.lineWidth = (2.0 + adv * 2.4 + (n + 0.5) * 2.4) * z;",
    "    ctx.lineWidth = (2.0 + adv * 2.4 + (n + 0.5) * 2.4 + Math.min(9, pressed[i] * 0.12)) * z;")
rep("""  // bubbles trailing just behind the edge
  ctx.fillStyle = '#e6f6ff';""",
"""  // spray thrown up where a wave is pressing against the castle / defences
  ctx.fillStyle = '#f4fbff';
  for (let i = 0; i < SWASH_N; i++) {
    if (pressed[i] < 6) continue;
    const k = Math.min(1, pressed[i] / (TH() * 1.2));
    for (let s = 0; s < 2; s++) {
      const n = noise2(i * 1.7 + s * 9.3, t * 0.11 + s);
      if (n < 0) continue;
      ctx.globalAlpha = 0.35 + n * 0.6;
      ctx.beginPath();
      ctx.arc(i * SWASH_STEP + (n - 0.2) * 14, visY[i] - (2 + n * 22 * k) * z, (1 + n * 2.6) * z, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  ctx.globalAlpha = 1;
  // bubbles trailing just behind the edge
  ctx.fillStyle = '#e6f6ff';""")

# ── castle ring: pours round tile by tile, dries in place ───────────────────────────────────────
rep("""    ctx.fillStyle='rgba(60,40,15,0.28)'; ctx.fill();
    if (ringFill > 0) { ctx.globalAlpha = Math.min(1, ringFill * 1.6); ctx.fillStyle='#58c2da'; ctx.fill(); ctx.globalAlpha = 1; }
    ctx.restore();
    const pulse = Math.sin(t*0.06+c*0.7+r*0.5)*0.5+0.5;
    if (ringFill > 0) drawTileTop(c,r,`rgba(200,240,255,${(0.15+pulse*0.15)*Math.min(1, ringFill*1.6)})`);""",
"""    ctx.fillStyle='rgba(60,40,15,' + (0.24 + 0.22 * ringDamp).toFixed(2) + ')'; ctx.fill();   // darker while damp
    ctx.restore();
    // the water reaches the far tiles last: delay each tile by its distance from the sea-side corner
    const tileCover = Math.max(0, Math.min(1, (ringCover - 0.65 * (Math.abs(c - 7) + Math.abs(r - 7)) / 10) / 0.35));
    drawPoolOnTile(c, r, tileCover, ringDepth, '#6fd0e2', '#3fa6c8');""")

# ── placed moat pieces: pour / dry instead of a flat fill level ─────────────────────────────────
rep("""      const mp = placedPieces.find(q => q.col === col && q.row === row);
      const mFill = mp && mp.fill ? Math.min(1, mp.fill * 1.6) : 0;""",
"""      const mp = placedPieces.find(q => q.col === col && q.row === row);
      const mCover = mp && mp.cover ? mp.cover : 0, mDepth = mp && mp.depth ? mp.depth : 0, mDamp = mp && mp.damp ? mp.damp : 0;
      const mFill = Math.min(mCover, mDepth) > 0.05 ? 1 : 0;""")
rep("""      const g = ctx.createLinearGradient(p.x,p.y,pb.x,pb.y);
      g.addColorStop(0,c1); g.addColorStop(1,c2);
      const ga0 = ctx.globalAlpha;
      ctx.globalAlpha = ga0 * mFill;
      ctx.fillStyle=g; ctx.beginPath();
      ctx.moveTo(p.x,p.y);ctx.lineTo(pr.x,pr.y);ctx.lineTo(pb.x,pb.y);ctx.lineTo(pf.x,pf.y);
      ctx.closePath();ctx.fill();
      ctx.globalAlpha = ga0;""",
"""      if (mDamp > 0) { ctx.fillStyle = 'rgba(50,32,10,' + (0.3 * mDamp).toFixed(2) + ')'; ctx.fill(); }   // damp floor after it drains
      drawPoolOnTile(col, row, mCover, mDepth, c1, c2);""")

# ── walls melt with health ──────────────────────────────────────────────────────────────────────
a = src.index("function drawPlacedPiece(id, col, row, state) {"); b = src.index("case 'moat-shallow':", a)
seg = src[a:b]
assert seg.count("isoBlock(") == 14, seg.count("isoBlock(")
seg = seg.replace("isoBlock(", "meltBlock(")
seg = seg.replace("function drawPlacedPiece(id, col, row, state) {\n",
    "function drawPlacedPiece(id, col, row, state) {\n"
    "  // v0.9: walls melt - cut off above a height that drops with the piece's health (ghost previews draw at full height)\n"
    "  const _fullH = { 'wall-small': 0.6, 'wall-medium': 1.38, 'wall-tall': 1.9 }[id];\n"
    "  meltCutZ = _fullH ? _fullH * (0.22 + 0.78 * pieceDrawHealth / 100) : 1e9;\n")
src = src[:a] + seg + src[b:]
rep("    drawPlacedPiece(p.id, p.col, p.row, state);",
    "    pieceDrawHealth = p.health;\n    drawPlacedPiece(p.id, p.col, p.row, state);\n    pieceDrawHealth = 100;")

# ── castle melts with (displayed) health ────────────────────────────────────────────────────────
a = src.index("function drawCastle(t) {"); b = src.index("function drawIsoFlag(", a)
seg = src[a:b]
n_blocks = seg.count("isoBlock(")
assert n_blocks >= 20, n_blocks
seg = seg.replace("isoBlock(", "castleBlock(")
assert seg.count("  drawIsoFlag(") == 5
seg = seg.replace("  drawIsoFlag(BC,   BR,   1.95,'#cc2020',t);", "  if (castleCutZ() < 2.3) return;   // flags are the first thing to go\n  drawIsoFlag(BC,   BR,   1.95,'#cc2020',t);")
src = src[:a] + seg + src[b:]

# ── drop the old per-tile foam dots (they showed through the thin water as stripes) ─────────────
rep("""      if(isShore(col,row)){
        drawFoamOnTile(col,row,tick);
      }""", "      // v0.9: per-tile foam dots removed - drawShoreFoamBand() carries the foam along the real edge")

# ── reset list ──────────────────────────────────────────────────────────────────────────────────
rep("  bigWave = null; bigWaveTimer = BIGWAVE_FIRST; bigWaveWarn = 0; ringFill = 0;",
    "  bigWave = null; bigWaveTimer = BIGWAVE_FIRST; bigWaveWarn = 0;\n  ringCover = 0; ringDepth = 0; ringDamp = 0; ringFeed = 0; castleShown = CASTLE_MAX_HP;", count=2)

assert "ringFill" not in src, "ringFill left behind"
assert "isSurgeWet" not in src, "isSurgeWet left behind"
open(sys.argv[2], 'w', encoding='utf-8').write(src)
print('patched ->', sys.argv[2])
