#!/usr/bin/env python3
# Sand Castle Crashers - water v3 wave behaviour, applied ON TOP of patch_water4.py's output.
#   1 no "BIG WAVE!" banner - big waves arrive unannounced
#   2 waves fan out: each enters from one side and sloshes across to the other, spreading as it goes
#     (enters from the left -> travels right; enters from the right -> travels left). Big waves too.
#   3 each wave gets a random speed: some lazy, some fast (run-up, retreat and sideways travel together)
#   4 backwash: water still retreating from an earlier wave slows a wave that is running up into it
# Each wave now runs on its own clock (w.p) instead of tick - born, so it can be slowed.
# usage: patch_water5.py <v4.html> <out.html>
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

# ── 1. no big-wave banner ───────────────────────────────────────────────────────────────────────
rep("let bigWaveWarn = 0;              // frames left on the on-screen warning\n", "")
rep("  bigWaveWarn = 150;\n", "")
rep("  if (bigWaveWarn > 0) bigWaveWarn--;\n", "")
rep_block("function drawBigWaveWarning() {", "// ── Sand texture offscreen", "")
rep("  drawBigWaveWarning();   // ← 'BIG WAVE!' banner while one is coming\n", "")
rep("  bigWave = null; bigWaveTimer = BIGWAVE_FIRST; bigWaveWarn = 0;\n",
    "  bigWave = null; bigWaveTimer = BIGWAVE_FIRST;\n", count=2)

# ── tuning knobs ────────────────────────────────────────────────────────────────────────────────
rep("let bigWave = null;               // the one active big wave, or null\n",
    "let bigWave = null;               // the one active big wave, or null\n"
    "// ← TUNE: wave feel\n"
    "const SWASH_SPEED_MIN = 0.45;     // slowest wave (1 = the old fixed pace)\n"
    "const SWASH_SPEED_MAX = 2.1;      // fastest wave\n"
    "const BACKWASH_DRAG   = 0.55;     // how hard retreating water slows a wave running up into it\n"
    "const BACKWASH_MIN    = 0.3;      // an incoming wave never drops below this fraction of its speed\n")

# ── 2+3. swash waves: random speed, enter from one side, fan out while crossing ─────────────────
rep_block("function spawnSwashWave() {", "function spawnBigWave() {", r'''function spawnSwashWave() {
  const th = TH();
  const big = Math.random() < 0.25;
  const dir = Math.random() < 0.5 ? -1 : 1;        // +1 = comes in from the left and sloshes right; -1 = the reverse
  const r = Math.random();
  const spd = SWASH_SPEED_MIN + (SWASH_SPEED_MAX - SWASH_SPEED_MIN) * r * r;   // most waves lazy-to-medium, a few fast
  swashWaves.push({
    born: tick | 0, p: 0, spd, slow: 1,
    amp: th * (0.35 + Math.random() * 0.85) * (big ? 1.6 : 1),          // up to ~2 tiles of run-up
    rise: 30 + Math.random() * 40, fall: 80 + Math.random() * 150,
    seed: Math.random() * 100,
    dir, v: 2.5 + Math.random() * 5,                                    // sideways travel, px per (speed-1) tick
    x0: dir > 0 ? SW * (-0.12 + Math.random() * 0.4) : SW * (1.12 - Math.random() * 0.4),   // starts on its entry side
    sig: SW * (0.07 + Math.random() * 0.12),                           // narrow where it lands...
    fan: 1.2 + Math.random() * 2.3,                                     // ...and this many times wider by the time it is gone
    base: Math.random() * 0.15,
  });
  swashNext = (tick | 0) + (Math.random() < 0.3 ? 12 + Math.random() * 30 : 50 + Math.random() * 170); // sometimes a quick double
}

// where a swash wave's bulge is centred, and how wide it has fanned, at clock value p
function swashCentre(w, p) { return w.x0 + w.dir * w.v * p; }
function swashWidth(w, p)  { return w.sig * (1 + w.fan * Math.min(1, Math.max(0, p) / (w.rise + w.fall))); }

// How much water is draining back down the beach at screen x right now (px of run-up, weighted by speed).
function backwashAt(x, except) {
  let back = 0;
  for (const o of swashWaves) {
    if (o === except || o.p <= o.rise) continue;
    const u = (o.p - o.rise) / o.fall;
    if (u >= 1) continue;
    const dx = (x - swashCentre(o, o.p)) / swashWidth(o, o.p);
    back += o.amp * (1 - u) * Math.exp(-dx * dx) * o.spd;
  }
  return back;
}
function backwashSlow(x, except) {
  return Math.max(BACKWASH_MIN, 1 - BACKWASH_DRAG * backwashAt(x, except) / TH());
}

''')

# ── 2+3. big wave: enters from a random side, crosses the castle at the moment it hits ──────────
rep("""  bigWave = { born: tick | 0, amp, cx: c.x, sig: TW() * (4.5 + Math.random() * 2),
    back: th * (0.8 + Math.random() * 0.7), draw: 55, rise: 55, hold: 90, fall: 200,
    sl: Math.random() * 6.28, slAmp: TW() * (2.4 + Math.random() * 1.8), hit: false };""",
"""  const dir = Math.random() < 0.5 ? -1 : 1;   // +1 = comes in from the left and sloshes right
  const slAmp = TW() * (2.4 + Math.random() * 1.8);   // how far to each side of the castle it travels
  bigWave = { born: tick | 0, p: 0, spd: 0.7 + Math.random() * 0.7, slow: 1, dir, x: c.x - dir * slAmp,
    amp, cx: c.x, sig: TW() * (4.5 + Math.random() * 2),
    back: th * (0.8 + Math.random() * 0.7), draw: 55, rise: 55, hold: 90, fall: 200,
    slAmp, hit: false };""")

# ── per-frame clocks (with backwash) + big-wave phases on its own clock ─────────────────────────
rep("""  for (let i = swashWaves.length - 1; i >= 0; i--) {
    const w = swashWaves[i];
    if (tk - w.born > w.rise + w.fall + 60) swashWaves.splice(i, 1);
  }
  let bAge = -1, bA = 0, bC = 0;
  if (bigWave) {
    bAge = tk - bigWave.born;
    const w = bigWave;""",
"""  // each wave runs on its own clock: its random speed, slowed while it runs up into backwash
  for (const w of swashWaves) {
    w.slow = w.p < w.rise ? backwashSlow(swashCentre(w, w.p), w) : 1;
    w.p += w.spd * w.slow;
  }
  for (let i = swashWaves.length - 1; i >= 0; i--) {
    const w = swashWaves[i];
    if (w.p > w.rise + w.fall + 60) swashWaves.splice(i, 1);
  }
  let bAge = -1, bA = 0, bC = 0;
  if (bigWave) {
    const w = bigWave;
    w.slow = (w.p >= w.draw && w.p < w.draw + w.rise) ? Math.max(0.5, backwashSlow(w.x, null)) : 1;
    w.p += w.spd * w.slow;
    bAge = w.p;""")
rep("""    bC = w.cx + (bAge > w.draw ? Math.sin((bAge - w.draw) * 0.05 + w.sl) * w.slAmp : 0);    // sloshes left and right""",
"""    // crosses from its entry side to the far side, right over the castle at the moment it hits
    const pr = bAge <= w.draw ? 0 : bAge < w.draw + w.rise ? 0.5 * (bAge - w.draw) / w.rise
             : Math.min(1, 0.5 + 0.5 * (bAge - w.draw - w.rise) / (w.hold + w.fall * 0.5));
    bC = w.cx + w.dir * w.slAmp * (2 * pr - 1);
    if (bigWave) bigWave.x = bC;""")

# per-column shape uses the wave's own clock and its fanned-out width
rep("""      const age = (tk - w.born) - (noise2(sx * 0.0035 + w.seed, w.seed * 0.7) + 0.5) * 30;""",
"""      const age = w.p - (noise2(sx * 0.0035 + w.seed, w.seed * 0.7) + 0.5) * 30;""")
rep("""      const dx = (sx - (w.x0 + w.dir * w.v * age)) / w.sig;               // the bulge travels along the beach""",
"""      const dx = (sx - swashCentre(w, age)) / swashWidth(w, age);         // the bulge travels along the beach, fanning out""")

# the hit lands on the big wave's own clock
rep("  if (bigWave && !bigWave.hit && tick - bigWave.born >= bigWave.draw + bigWave.rise) { bigWave.hit = true; applyBigWaveHit(); }",
    "  if (bigWave && !bigWave.hit && bigWave.p >= bigWave.draw + bigWave.rise) { bigWave.hit = true; applyBigWaveHit(); }")

assert "bigWaveWarn" not in src and "drawBigWaveWarning" not in src
assert "tk - w.born" not in src and "tick - bigWave.born" not in src
open(sys.argv[2], 'w', encoding='utf-8').write(src)
print('patched ->', sys.argv[2])
