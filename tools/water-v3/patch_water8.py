#!/usr/bin/env python3
# Sand Castle Crashers - water v3: wave SIZE matters, applied ON TOP of patch_water7.py's output.
#   - every wave has a size factor k (0..1): ordinary waves ~0.2-0.95 from their run-up, a big wave = 1
#   - moats: a small wave only part-fills a moat and it dries quickly; a big wave fills it and it dries slowly
#   - damage: ordinary waves now do a LITTLE damage (scaled by k) when they reach the defences, in the defend
#     phase only, through the same locked chain as big waves: moat pieces -> else nearest sea-side wall ->
#     else the castle (castle damage accrues in fractions of a hit; damageCastle() stays the sole mutator)
#   - big-wave damage is unchanged (34 / 40 / 3 hits)
# usage: patch_water8.py <v7.html> <out.html>
import sys
src = open(sys.argv[1], encoding='utf-8').read()

def rep(old, new, count=1):
    global src
    assert src.count(old) == count, (src.count(old), old[:80])
    src = src.replace(old, new)

# ── knobs + state ───────────────────────────────────────────────────────────────────────────────
rep("let bigWave = null;               // the one active big wave, or null\n",
    "// ← TUNE: ordinary (small) waves. Each is scaled by the wave's size factor k (0..1).\n"
    "const SWASH_MOAT_DMG    = 4;      // health a moat piece loses to the largest ordinary wave (a small one: ~1)\n"
    "const SWASH_WALL_DMG    = 4;      // same for the nearest sea-side wall when no moat is in the way\n"
    "const SWASH_CASTLE_HITS = 0.34;   // fraction of one castle hit from the largest ordinary wave when nothing is in the way\n"
    "const SWASH_SIZE_REF    = 2;      // run-up (in tile-heights) that counts as size 1\n"
    "const MOAT_FILL_MIN     = 0.3;    // how full the smallest wave leaves a moat (a big wave fills it to 1)\n"
    "const MOAT_DRY_SMALL    = 0.012;  // depth lost per tick after the smallest wave (~1.5 s to dry)\n"
    "const MOAT_DRY_BIG      = 0.002;  // depth lost per tick after a big wave (~8 s to dry; big waves come every 12-25 s)\n"
    "const runSrc = new Array(SWASH_N).fill(null);   // which wave is giving each screen column its run-up right now\n"
    "let swashCastleDebt = 0;          // fractions of a castle hit owed by ordinary waves\n"
    "let bigWave = null;               // the one active big wave, or null\n")

# restart reset list (both handlers)
rep("  bigWave = null; bigWaveTimer = BIGWAVE_FIRST;\n",
    "  bigWave = null; bigWaveTimer = BIGWAVE_FIRST; swashCastleDebt = 0;\n", count=2)

# ── record the source wave per column ───────────────────────────────────────────────────────────
rep("""    let run = 0, flow = 0;
    for (let j = 0; j < swashWaves.length; j++) {
      const w = swashWaves[j];
      const s = swashShape(w, sx);                                         // poured along the beach from where it landed
      if (s <= 0) continue;
      const rr = s * w.amp * (0.75 + 0.25 * (noise2(sx * 0.006 + w.seed * 3.1, 5.5) + 0.5));
      if (rr > run) run = rr;""",
"""    let run = 0, flow = 0, srcW = null;
    for (let j = 0; j < swashWaves.length; j++) {
      const w = swashWaves[j];
      const s = swashShape(w, sx);                                         // poured along the beach from where it landed
      if (s <= 0) continue;
      const rr = s * w.amp * (0.75 + 0.25 * (noise2(sx * 0.006 + w.seed * 3.1, 5.5) + 0.5));
      if (rr > run) { run = rr; srcW = w; }""")
rep("      else { const rr = bA * lat; if (rr > run) run = rr; flow += bDX * lat; }\n    }\n    flowPh[i] += flow * SWASH_FLOW_VIS;",
    "      else { const rr = bA * lat; if (rr > run) { run = rr; srcW = bigWave; } flow += bDX * lat; }\n    }\n    runSrc[i] = srcW;\n    flowPh[i] += flow * SWASH_FLOW_VIS;")

# ── size helpers + the ordinary-wave hit (same chain as applyBigWaveHit) ────────────────────────
rep("function applyBigWaveHit() {",
r'''// Size factor 0..1 of a wave: a big wave is 1, an ordinary wave is its run-up against SWASH_SIZE_REF tile-heights.
function waveSizeK(w) { return !w ? 0 : w.draw !== undefined ? 1 : Math.min(1, w.amp / (TH() * SWASH_SIZE_REF)); }
// Which wave's water is at this tile's sea-side corner right now (null = none / only the tide).
function surgeSourceAt(col, row) {
  const f = iso(col + 1, row + 1, 0);
  const i = Math.max(0, Math.min(SWASH_N - 1, Math.round(f.x / SWASH_STEP)));
  return runSrc[i];
}
// Is the TIDE itself (no wave) already at this tile's sea-side corner?
function tideReaches(col, row) {
  const f = iso(col + 1, row + 1, 0);
  return baseShoreYAt(f.x) <= f.y + 2;
}
// How strongly is this tile being fed right now: 1 if it sits in the tide or a big wave, else the wave's size.
function feedSizeAt(col, row) {
  if (tideReaches(col, row)) return 1;
  const s = surgeSourceAt(col, row);
  return s ? waveSizeK(s) : 0.15;
}
// The moment an ordinary wave's pour is at its fullest: that is when it lands its (small) hit.
function swashHitAt(w) { return w.rise * 0.55 + (w.v > 0.5 ? 0.6 * w.reach / w.v : 0) + 14; }

// An ordinary wave reaches the defences: the same locked chain as a big wave, scaled down by its size.
function applySwashHit(w) {
  if (gameOver || wavePhase !== 'defend') return;
  const k = waveSizeK(w);
  const hit = p => guardsCastle(p) && surgeReaches(p.col, p.row) && surgeSourceAt(p.col, p.row) === w;
  // 1. moat pieces it reaches absorb it
  const moats = placedPieces.filter(p => p.id.indexOf('moat-') === 0 && hit(p));
  if (moats.length) { moats.forEach(p => { p.health = Math.max(0, p.health - SWASH_MOAT_DMG * k); }); return; }
  // 2. the nearest wall / drawbridge on the castle's sea side
  let best = null, bestD = 1e9;
  for (const p of placedPieces) {
    if (p.id.indexOf('moat-') === 0 || !hit(p)) continue;
    const d = Math.hypot(p.col - 7, p.row - 7);
    if (d < bestD) { bestD = d; best = p; }
  }
  if (best) { best.health = Math.max(0, best.health - SWASH_WALL_DMG * k); return; }
  // 3. nothing in the way and it reaches the castle ring: fractions of a hit, paid through damageCastle()
  if (surgeReaches(7, 7) && surgeSourceAt(7, 7) === w) {
    swashCastleDebt += SWASH_CASTLE_HITS * k;
    while (swashCastleDebt >= 1) { swashCastleDebt -= 1; damageCastle(); }
  }
}

function applyBigWaveHit() {''')

# ── tickSurge: moats fill to a level set by wave size and dry at a rate set by wave size ────────
rep("""    if (fed) { p.cover = Math.min(1, (p.cover || 0) + 0.013); p.depth = Math.min(1, (p.depth || 0) + 0.05); p.damp = 1; }
    else {
      if (p.depth > 0) { p.depth = Math.max(0, p.depth - 0.0035); if (p.depth === 0) p.cover = 0; }
      if (p.damp > 0) p.damp = Math.max(0, p.damp - 0.0012);
    }""",
"""    if (fed) {
      p.feedK = Math.max(p.feedK || 0, feedSizeAt(p.col, p.row));        // remember the biggest wave that filled it
      const level = MOAT_FILL_MIN + (1 - MOAT_FILL_MIN) * p.feedK;       // a small wave only part-fills it
      p.cover = Math.min(1, (p.cover || 0) + 0.013);
      if ((p.depth || 0) < level) p.depth = Math.min(level, (p.depth || 0) + 0.05);
      p.damp = 1;
    } else {
      if (p.depth > 0) {                                                 // small wave: dries fast. big wave: dries slowly.
        p.depth = Math.max(0, p.depth - (MOAT_DRY_SMALL + (MOAT_DRY_BIG - MOAT_DRY_SMALL) * (p.feedK || 0)));
        if (p.depth === 0) { p.cover = 0; p.feedK = 0; }
      }
      if (p.damp > 0) p.damp = Math.max(0, p.damp - 0.0012);
    }""")
rep("""  if (ringFed) { ringCover = Math.min(1, ringCover + 0.008); ringDepth = Math.min(1, ringDepth + 0.05); ringDamp = 1; }
  else {
    if (ringDepth > 0) { ringDepth = Math.max(0, ringDepth - 0.003); if (ringDepth === 0) ringCover = 0; }
    if (ringDamp > 0) ringDamp = Math.max(0, ringDamp - 0.001);
  }""",
"""  if (ringFed) {
    ringK = Math.max(ringK, ringFeed > 0 ? 1 : feedSizeAt(7, 7));
    const level = MOAT_FILL_MIN + (1 - MOAT_FILL_MIN) * ringK;
    ringCover = Math.min(1, ringCover + 0.008);
    if (ringDepth < level) ringDepth = Math.min(level, ringDepth + 0.05);
    ringDamp = 1;
  } else {
    if (ringDepth > 0) {
      ringDepth = Math.max(0, ringDepth - (MOAT_DRY_SMALL + (MOAT_DRY_BIG - MOAT_DRY_SMALL) * ringK));
      if (ringDepth === 0) { ringCover = 0; ringK = 0; }
    }
    if (ringDamp > 0) ringDamp = Math.max(0, ringDamp - 0.001);
  }
  // ordinary waves land their small hit when their pour is at its fullest
  for (const w of swashWaves) if (!w.hit && w.p >= swashHitAt(w)) { w.hit = true; applySwashHit(w); }""")
rep("let ringCover = 0, ringDepth = 0, ringDamp = 0, ringFeed = 0;",
    "let ringK = 0;                    // size of the biggest wave that filled the castle ring (sets how slowly it dries)\nlet ringCover = 0, ringDepth = 0, ringDamp = 0, ringFeed = 0;")
rep("  ringCover = 0; ringDepth = 0; ringDamp = 0; ringFeed = 0; castleShown = CASTLE_MAX_HP;",
    "  ringCover = 0; ringDepth = 0; ringDamp = 0; ringFeed = 0; ringK = 0; castleShown = CASTLE_MAX_HP;", count=2)

open(sys.argv[2], 'w', encoding='utf-8').write(src)
print('patched ->', sys.argv[2])
