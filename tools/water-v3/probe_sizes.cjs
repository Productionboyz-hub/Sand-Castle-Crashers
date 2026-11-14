// probe_sizes.cjs <url> : wave SIZE checks (patch_water8). Exit 1 on any FAIL.
// Everything is driven by hand (updateSwash + tickSurge in a loop, no frames in between) with the tide parked
// a quarter tile-height short of the target tile, so one crafted ordinary wave reaches it and nothing else does.
const { chromium } = require('playwright');
const url = process.argv[2];
let fail = 0;
const check = (ok, name, info) => { if (!ok) fail++; console.log('  ' + (ok ? 'PASS' : 'FAIL') + '  ' + name + '   ' + JSON.stringify(info)); };
async function scenario(b, opts) {
  const ctx = await b.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
  const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto(url); await p.waitForTimeout(900);
  const r = await p.evaluate((o) => {
    if (typeof spawnSwashWave !== 'function') return { missing: true };
    placedPieces.length = 0;
    if (o.piece) placedPieces.push({ id: o.piece, col: 8, row: 8, health: 100, decayTimer: 0 });
    startWave(); if (o.build) wavePhase = 'build';
    bigWaveTimer = 1e9; swashWaves.length = 0; swashNext = 1e12;
    const tgt = o.piece ? [8, 8] : [7, 7];                       // the placed piece, or the castle ring's sea corner
    const f = iso(tgt[0] + 1, tgt[1] + 1, 0), T = tick + 10;
    const gap = sd => { shoreD = sd; updateSwash(T); return (baseShoreYAt(f.x) - f.y) / TH(); };
    let lo = SHORE_HIGH_CAP - 4, hi = SHORE_LOW + 4;             // park the tide 0.25 tile-heights below the corner
    for (let k = 0; k < 40; k++) { const mid = (lo + hi) / 2; if (gap(mid) > 0.25) hi = mid; else lo = mid; }
    const parked = +gap((lo + hi) / 2).toFixed(2);
    const hp0 = castleHP, out = { parked, waves: [] };
    let t = T;
    for (const ampTiles of o.amps) {
      spawnSwashWave(); const w = swashWaves[swashWaves.length - 1];
      Object.assign(w, { amp: ampTiles * TH(), dir: 1, x0: f.x - 150, v: 8, reach: SW * 0.8, up: SW * 0.04, spd: 1, rise: 40, fall: 100, p: 0 });
      swashNext = 1e12;
      const piece = placedPieces[0], h0 = piece ? piece.health : null, c0 = castleHP;
      let peak = 0, dryAt = -1, fedSeen = false, lastFed = 0;
      for (let k = 0; k < 1400; k++) {
        updateSwash(++t); tickSurge();
        const d = piece ? (piece.depth || 0) : ringDepth;
        if (d > peak) peak = d; if (d > 0) fedSeen = true;
        if (surgeReaches(tgt[0], tgt[1])) lastFed = k;                 // drying is timed from when the water stops reaching it
        if (fedSeen && d === 0 && dryAt < 0) dryAt = k - lastFed;      // first tick it is empty again
        if (dryAt >= 0 && swashWaves.length === 0) break;
        if (!fedSeen && swashWaves.length === 0) break;
      }
      out.waves.push({ amp: ampTiles, k: typeof waveSizeK === 'function' ? +Math.min(1, ampTiles / SWASH_SIZE_REF).toFixed(2) : null,
        dmg: piece ? +(h0 - piece.health).toFixed(2) : null, castleLost: c0 - castleHP, peakDepth: +peak.toFixed(2), ticksToDry: dryAt });
    }
    out.castleLostTotal = hp0 - castleHP; out.hitHP = CASTLE_DAMAGE_PER_HIT;
    return out;
  }, opts);
  r.errs = errs.length; await ctx.close(); return r;
}
(async () => {
  const b = await chromium.launch();
  const m = await scenario(b, { piece: 'moat-standard', amps: [0.7, 1.9] });
  if (m.missing) { console.log('  FAIL  no swash system in this build'); process.exit(1); }
  const [s, l] = m.waves;
  check(s.dmg > 0.5 && s.dmg < 4 && l.dmg > s.dmg * 1.8 && l.dmg < 10, 'Z1 moat: a small wave does a little damage, a larger one more, both far below a big wave (34)', { small: s.dmg, large: l.dmg });
  check(s.peakDepth > 0.2 && s.peakDepth < 0.75 && l.peakDepth > 0.85, 'Z2 moat: a small wave only part-fills it, a large one nearly fills it', { small: s.peakDepth, large: l.peakDepth });
  check(s.ticksToDry > 0 && l.ticksToDry > s.ticksToDry * 2.5, 'Z3 moat: dries quickly after a small wave, slowly after a large one (ticks until empty)', { small: s.ticksToDry, large: l.ticksToDry });
  const w = await scenario(b, { piece: 'wall-tall', amps: [0.7, 1.9] });
  check(w.waves[0].dmg > 0.5 && w.waves[0].dmg < 4.5 && w.waves[1].dmg > w.waves[0].dmg * 1.8 && w.waves[1].dmg < 10, 'Z4 wall (no moat): small wave little damage, larger wave more, far below a big wave (40)', w.waves.map(x => x.dmg));
  const bp = await scenario(b, { piece: 'moat-standard', amps: [1.9], build: true });
  check(bp.waves[0].dmg === 0 && bp.waves[0].peakDepth > 0.5, 'Z5 build phase: waves still fill the moat but do no damage', bp.waves[0]);
  const c = await scenario(b, { piece: null, amps: [1.9, 1.9, 1.9, 1.9] });
  const lost = c.waves.map(x => x.castleLost);
  check(lost[0] === 0 && c.castleLostTotal === c.hitHP, 'Z6 castle (nothing in the way): it takes several ordinary waves to cost one castle hit (a big wave costs 3)', { perWave: lost, total: c.castleLostTotal, oneHit: c.hitHP });
  check(m.errs + w.errs + bp.errs + c.errs === 0, 'Z7 no page errors', {});
  await b.close();
  console.log(fail ? 'FAILED (' + fail + ')' : 'ALL PASS');
  process.exit(fail ? 1 : 0);
})();
