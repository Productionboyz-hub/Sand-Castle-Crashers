#!/usr/bin/env python3
# Sand Castle Crashers - water v3: waves POURED along the beach, applied ON TOP of patch_water6.py's output.
# Before: each wave was a symmetric bump travelling sideways, so every column only went up then down
#         ("piano keys pressed one after another").
# Now:    a wave lands at one spot (x0) and its front SLIDES along the beach in its direction, thinning as it
#         goes and leaving a long sheet behind it that drains slowly. The foam, streaks and flecks in the thin
#         sheet are carried sideways with the flow (flowPh), so the water is seen to move left / right.
# usage: patch_water7.py <v6.html> <out.html>
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

# ── knobs: fan-out width knobs become slide speed + reach ───────────────────────────────────────
rep("const SWASH_FAN_MIN   = 3;        // a wave ends at least this many times wider than it landed (plus 1)\n"
    "const SWASH_FAN_MAX   = 7;        // ...and at most this many\n",
    "const SWASH_SLIDE_MIN = 4;        // how fast a wave's front slides along the beach, px per tick (slowest)\n"
    "const SWASH_SLIDE_MAX = 13;       // ...fastest\n"
    "const SWASH_REACH_MIN = 0.35;     // how far along the beach a wave slides before it has thinned to nothing (x screen width)\n"
    "const SWASH_REACH_MAX = 0.95;\n"
    "const SWASH_FLOW_VIS  = 0.6;      // how strongly foam/streaks in the thin sheet are carried sideways (0 = not at all)\n")
rep("const pressed = new Float32Array(SWASH_N);   // px of surge held back by the barrier (drives the foam pile-up)",
    "const pressed = new Float32Array(SWASH_N);   // px of surge held back by the barrier (drives the foam pile-up)\n"
    "const flowPh = new Float32Array(SWASH_N);    // px the thin sheet has been carried sideways, per column (drawing only)")

# ── wave spawn + shape ──────────────────────────────────────────────────────────────────────────
rep_block("function spawnSwashWave() {", "function spawnBigWave() {", r'''function spawnSwashWave() {
  const th = TH();
  const big = Math.random() < 0.25;
  const dir = Math.random() < 0.5 ? -1 : 1;        // +1 = lands and slides to the right; -1 = slides to the left
  const r = Math.random();
  const spd = SWASH_SPEED_MIN + (SWASH_SPEED_MAX - SWASH_SPEED_MIN) * r * r;   // most waves lazy-to-medium, a few fast
  swashWaves.push({
    born: tick | 0, p: 0, spd, slow: 1,
    amp: th * (0.35 + Math.random() * 0.85) * (big ? 1.6 : 1),          // up to ~2 tiles of run-up
    rise: 30 + Math.random() * 40, fall: 80 + Math.random() * 150,
    seed: Math.random() * 100,
    dir, v: SWASH_SLIDE_MIN + Math.random() * (SWASH_SLIDE_MAX - SWASH_SLIDE_MIN),           // front speed along the beach
    x0: dir > 0 ? SW * (-0.05 + Math.random() * 0.55) : SW * (1.05 - Math.random() * 0.55), // where it lands
    up: SW * (0.03 + Math.random() * 0.05),                                                  // it spreads only a little the other way
    reach: SW * (SWASH_REACH_MIN + Math.random() * (SWASH_REACH_MAX - SWASH_REACH_MIN)),
  });
  swashNext = (tick | 0) + (Math.random() < 0.3 ? 12 + Math.random() * 30 : 50 + Math.random() * 170); // sometimes a quick double
}

// One swash wave at screen x. The wave lands at x0 and is poured along the beach: the further downstream,
// the later it arrives (d / v) and the thinner it is. Returns its run-up factor 0..1 at x (0 = not there yet,
// or gone) and sets swashFalling (is that water draining back?) and swashMove (0..1, is it still sliding?).
let swashFalling = false, swashMove = 0;
function swashShape(w, sx) {
  const d = (sx - w.x0) * w.dir;                  // + = downstream (the way it slides), - = upstream
  let lat, tau;
  if (d >= 0) { const q = d / w.reach; lat = Math.exp(-2.2 * q * Math.sqrt(q)); tau = d / Math.max(0.01, w.v); }
  else { const q = d / w.up; lat = Math.exp(-q * q); tau = -d / Math.max(0.01, w.v * 0.5); }
  const age = w.p - tau - (noise2(sx * 0.0035 + w.seed, w.seed * 0.7) + 0.5) * 14;   // ragged front
  swashFalling = false; swashMove = 0;
  if (age <= 0) return 0;
  const rise = w.rise * 0.55;                     // each stretch of beach fills fast as the front passes...
  const pour = rise + (w.v > 0.5 ? 0.6 * w.reach / w.v : 0);   // how long the pour keeps feeding the sheet
  let a;
  if (age < rise) { const u = age / rise; a = 1 - (1 - u) * (1 - u); swashMove = 1; }
  else {                                          // ...stays up while the pour lasts, then drains slowly
    const u = (age - rise - Math.max(0, pour - tau - rise)) / w.fall;
    if (u >= 1) return 0;
    if (u <= 0) { a = 1; swashMove = 1; }
    else { const q = 1 - u; a = q * q * (3 - 2 * q); swashFalling = true; swashMove = u < 0.5 ? 1 - u * 2 : 0; }
  }
  return a * lat;
}
// where a wave's sliding front is at clock value p (it stops once it has run its reach)
function swashCentre(w, p) { return w.x0 + w.dir * Math.min(w.reach, w.v * Math.max(0, p)); }

// How much water is draining back down the beach at screen x right now (px of run-up, weighted by speed).
function backwashAt(x, except) {
  let back = 0;
  for (const o of swashWaves) {
    if (o === except) continue;
    const s = swashShape(o, x);
    if (s > 0 && swashFalling) back += o.amp * s * o.spd;
  }
  return back;
}
function backwashSlow(x, except) {
  return Math.max(BACKWASH_MIN, 1 - BACKWASH_DRAG * backwashAt(x, except) / TH());
}

''')

# a wave is "incoming" (and can be slowed by backwash at its front) until its front has run its reach
rep("    w.slow = w.p < w.rise ? backwashSlow(swashCentre(w, w.p), w) : 1;",
    "    w.slow = w.p < w.rise * 0.55 + w.reach / Math.max(0.01, w.v) ? backwashSlow(swashCentre(w, w.p), w) : 1;")
rep("    if (w.p > w.rise + w.fall + 60) swashWaves.splice(i, 1);",
    "    if (w.p > w.rise + w.fall + w.reach / Math.max(0.01, w.v) + 60) swashWaves.splice(i, 1);")

# per-column: poured shape + sideways flow of the sheet
rep("""    let run = 0;
    for (let j = 0; j < swashWaves.length; j++) {
      const w = swashWaves[j];
      const age = w.p - (noise2(sx * 0.0035 + w.seed, w.seed * 0.7) + 0.5) * 30;
      if (age <= 0) continue;
      let a;
      if (age < w.rise) { const u = age / w.rise; a = 1 - (1 - u) * (1 - u); }
      else { const u = (age - w.rise) / w.fall; if (u >= 1) continue; a = 1 - u; a = a * a * (3 - 2 * a); }
      const dx = (sx - swashCentre(w, age)) / swashWidth(w, age);         // the bulge travels along the beach, fanning out
      const lat = w.base + (1 - w.base) * Math.exp(-dx * dx);
      const rr = a * w.amp * lat * (0.75 + 0.25 * (noise2(sx * 0.006 + w.seed * 3.1, 5.5) + 0.5));
      if (rr > run) run = rr;
    }
    if (bigWave) {
      const dx = (sx - bC) / bigWave.sig;
      const lat = Math.exp(-dx * dx);
      if (bA < 0) run += bA * (0.45 + 0.55 * lat);
      else { const rr = bA * lat; if (rr > run) run = rr; }
    }""",
"""    let run = 0, flow = 0;
    for (let j = 0; j < swashWaves.length; j++) {
      const w = swashWaves[j];
      const s = swashShape(w, sx);                                         // poured along the beach from where it landed
      if (s <= 0) continue;
      const rr = s * w.amp * (0.75 + 0.25 * (noise2(sx * 0.006 + w.seed * 3.1, 5.5) + 0.5));
      if (rr > run) run = rr;
      flow += w.dir * w.v * w.spd * w.slow * swashMove * Math.min(1, rr / (th * 0.6));   // the sheet is carried with the front
    }
    if (bigWave) {
      const dx = (sx - bC) / bigWave.sig;
      const lat = Math.exp(-dx * dx);
      if (bA < 0) run += bA * (0.45 + 0.55 * lat);
      else { const rr = bA * lat; if (rr > run) run = rr; flow += bDX * lat; }
    }
    flowPh[i] += flow * SWASH_FLOW_VIS;""")
rep("""    bC = w.cx + w.dir * w.slAmp * (2 * pr - 1);
    if (bigWave) bigWave.x = bC;""",
"""    bC = w.cx + w.dir * w.slAmp * (2 * pr - 1);
    bDX = bC - w.x;                                  // how far the big wave slid sideways this tick
    if (bigWave) bigWave.x = bC;""")
rep("  let bAge = -1, bA = 0, bC = 0;", "  let bAge = -1, bA = 0, bC = 0, bDX = 0;")

# ── texture: streaks, lace and flecks in the thin water are carried sideways with the flow ──────
rep("""    const edgeY = visShoreYAt(sx);            // where the water actually is right now (with surge)""",
"""    const edgeY = visShoreYAt(sx);            // where the water actually is right now (with surge)
    const wxf = (sx - swashLerp(flowPh, sx)) / th;   // x for anything floating on the thin sheet (carried sideways)""")
rep("""        const streak = noise2(wx * 0.7 + t * 0.3, wy * 3.4 + t * 1.1);
        a = 0.36 + streak * 0.14;
        if (streak > 0.18) { const f = (streak - 0.18) * 1.5; r += (255 - r) * f; g += (255 - g) * f; b += (255 - b) * f; a += f * 0.4; }""",
"""        const streak = noise2(wxf * 0.7 + t * 0.3, wy * 3.4 + t * 1.1);
        a = 0.36 + streak * 0.14;
        if (streak > 0.18) { const f = (streak - 0.18) * 1.5; r += (255 - r) * f; g += (255 - g) * f; b += (255 - b) * f; a += f * 0.4; }
        const fleck = noise2(wxf * 2.6 + 17.3, wy * 2.6 + t * 0.35);      // foam flecks riding the sheet: these show the sideways slide
        if (fleck > 0.26) { const f = Math.min(0.85, (fleck - 0.26) * 3); r += (255 - r) * f; g += (255 - g) * f; b += (255 - b) * f; a += f * 0.45; }""")
rep("""        const lace = noise2(wx * 2.3 + t * 0.5, wy * 4.2 + t * 0.9);""",
    """        const lace = noise2(wxf * 2.3 + t * 0.5, wy * 4.2 + t * 0.9);""")

# bubbles behind the edge drift with the flow too
rep("""    const n = noise2(i * 0.5, t * 0.012);
    if (n < 0.08) continue;""",
"""    const n = noise2((i * SWASH_STEP - flowPh[i]) * 0.0625, t * 0.012);
    if (n < 0.08) continue;""")

assert "swashWidth" not in src and "SWASH_FAN" not in src
open(sys.argv[2], 'w', encoding='utf-8').write(src)
print('patched ->', sys.argv[2])
