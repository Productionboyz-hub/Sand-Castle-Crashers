// test_surge3.cjs <url> : water v3 gameplay checks in a real page. Exit 1 on any FAIL.
const { chromium } = require('playwright');
const url = process.argv[2];
let fail = 0;
const check = (ok, name, info) => { if (!ok) fail++; console.log('  ' + (ok ? 'PASS' : 'FAIL') + '  ' + name + '   ' + JSON.stringify(info)); };
async function fresh(b) {
  const ctx = await b.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
  const p = await ctx.newPage();
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto(url, { waitUntil: 'load' }); await p.waitForTimeout(1200);
  return { ctx, p, errs };
}
// Runs one big wave. Samples every frame from the hit to the end of the hold.
async function oneBigWave(p, setup) {
  return p.evaluate(async (setupSrc) => {
    if (typeof spawnBigWave !== 'function' || typeof buildBarrier !== 'function') return { missing: true };
    (new Function(setupSrc))();
    startWave();
    const before = { hp: castleHP, cut: castleCutZ(), ring: [ringCover, ringDepth], pieces: placedPieces.map(q => ({ id: q.id, h: q.health, cover: q.cover || 0 })) };
    bigWaveTimer = 1;
    const raf = () => new Promise(r => requestAnimationFrame(r));
    const t0 = performance.now();
    const pour = [], ringPour = []; let pn = 0;
    while (!(bigWave && bigWave.hit) && performance.now() - t0 < 20000) {
      if (pn++ % 6 === 0) { const mm = placedPieces.find(q => q.id.indexOf('moat-') === 0); pour.push(mm ? +(mm.cover || 0).toFixed(2) : -1); ringPour.push(+ringCover.toFixed(2)); }
      await raf();
    }
    const hitSeen = !!(bigWave && bigWave.hit);
    const atHit = { hp: castleHP, pieces: placedPieces.map(q => ({ id: q.id, h: q.health, cover: q.cover || 0 })), ringCover };
    // through the hold: the water must never be past the barrier, and must never reach behind the castle
    let worstPast = 0, behind = false, minCover = 9, maxCover = 0, ringSteps = [], pressedMax = 0, n = 0;
    const back = iso(2, 2, 0), ctr = iso(5, 5, 0);
    while (bigWave && tick - bigWave.born < bigWave.draw + bigWave.rise + bigWave.hold && performance.now() - t0 < 40000) {
      for (let i = 0; i < SWASH_N; i++) {
        if (barrierY[i] > -1e8 && baseY[i] > barrierY[i]) { const past = barrierY[i] - visY[i]; if (past > worstPast) worstPast = past; }
        if (pressed[i] > pressedMax) pressedMax = pressed[i];
      }
      if (visShoreYAt(ctr.x) < ctr.y || visShoreYAt(back.x) < back.y) behind = true;
      const mc = placedPieces.filter(q => q.id.indexOf('moat-') === 0).map(q => q.cover || 0);
      if (mc.length) { minCover = Math.min(minCover, ...mc); maxCover = Math.max(maxCover, ...mc); }
      if (n % 6 === 0) { ringSteps.push(+ringCover.toFixed(2)); const mm = placedPieces.find(q => q.id.indexOf('moat-') === 0); pour.push(mm ? +(mm.cover || 0).toFixed(2) : -1); }
      n++; await raf();
    }
    const afterHold = { hp: castleHP, cut: castleCutZ(), ring: [ringCover, ringDepth], pieces: placedPieces.map(q => ({ id: q.id, h: q.health, cover: +(q.cover || 0).toFixed(2), depth: +(q.depth || 0).toFixed(2) })) };
    return { pour, ringPour, before, atHit, afterHold, hitSeen, worstPast, behind, minCover, maxCover, ringSteps, pressedMax, dmgPerHit: CASTLE_DAMAGE_PER_HIT };
  }, setup);
}
(async () => {
  const b = await chromium.launch();
  // S1 moat absorbs, pours, wave stops
  let { ctx, p, errs } = await fresh(b);
  let r = await oneBigWave(p, "placedPieces.push({id:'moat-standard',col:8,row:8,health:100,decayTimer:0},{id:'wall-tall',col:8,row:7,health:100,decayTimer:0});");
  if (r.missing) { console.log('  FAIL  no v3 wave system in this build'); console.log('FAILED'); process.exit(1); }
  check(r.hitSeen, 'S1a the big wave lands its hit', r.hitSeen);
  const m = r.atHit.pieces.find(q => q.id === 'moat-standard'), w = r.atHit.pieces.find(q => q.id === 'wall-tall');
  check(m.h <= 66 && m.h >= 64 && w.h >= 99 && r.atHit.hp === r.before.hp, 'S1b moat absorbs: moat -34, wall and castle untouched', { moat: m.h, wall: w.h, hp: r.atHit.hp });
  check(r.worstPast <= 0.01 && !r.behind && r.pressedMax > 10, 'S1c #1 the surge never passes the barrier and never gets behind the castle (and is held back against it)', { worstPast: r.worstPast, behind: r.behind, pressedMax: Math.round(r.pressedMax) });
  const mid = r.pour.filter(v => v > 0.02 && v < 0.98);
  check(r.pour[0] === 0 && mid.length >= 4 && new Set(mid).size >= 4 && r.pour.every((v, i) => i === 0 || v >= r.pour[i - 1] - 0.001) && r.afterHold.pieces[0].cover === 1, 'S1d #2 the moat POURS: starts empty, passes through partial levels, ends full', { samples: r.pour.filter((v, i) => i % 2 === 0).slice(0, 14), end: r.afterHold.pieces[0].cover });
  check(r.afterHold.ring[0] === 0, 'S1e a moat that held the wave keeps the castle ring dry', r.afterHold.ring);
  const dry = await p.evaluate(async () => { const raf = () => new Promise(r => requestAnimationFrame(r)); const t0 = performance.now(); const depths = []; let n = 0; while (placedPieces.some(q => q.depth > 0) && performance.now() - t0 < 60000) { if (n++ % 40 === 0) depths.push(+placedPieces[0].depth.toFixed(2)); await raf(); } return { depths: depths.slice(-8), n: depths.length, end: placedPieces.map(q => [q.cover || 0, q.depth || 0]) }; });
  check(dry.depths.length >= 4 && dry.depths.every((v, i) => i === 0 || v < dry.depths[i - 1]) && dry.depths[dry.depths.length - 1] < 0.3 && dry.end.every(e => e[0] === 0 && e[1] === 0), 'S1f #2 the moat DRIES UP gradually (last samples fall step by step), back to empty', dry);
  check(errs.length === 0, 'S1g no page errors', errs.slice(0, 3));
  await ctx.close();
  // S2 wall takes it; wall melts; ring pours round
  ({ ctx, p, errs } = await fresh(b));
  r = await oneBigWave(p, "placedPieces.push({id:'wall-tall',col:8,row:8,health:100,decayTimer:0},{id:'wall-tall',col:1,row:1,health:100,decayTimer:0});");
  const ws = r.atHit.pieces.map(q => q.h);
  check(ws[0] <= 60 && ws[0] >= 58 && ws[1] >= 99 && r.atHit.hp === r.before.hp, 'S2a no moat: only the nearest sea-side wall loses 40, castle untouched', { walls: ws, hp: r.atHit.hp });
  const rs = r.ringPour.concat(r.ringSteps);
  const rmid = rs.filter(v => v > 0.02 && v < 0.98);
  check(rs[0] === 0 && new Set(rmid).size >= 6 && rs.every((v, i) => i === 0 || v >= rs[i - 1] - 0.001) && rs[rs.length - 1] > 0.6, 'S2b #2 the castle ring POURS round: starts dry and rises through partial levels (never a snap)', rs.filter((v, i) => i % 3 === 0).slice(0, 16));
  const melt = await p.evaluate(() => { const cuts = h => { pieceDrawHealth = h; let top = 0; const o = isoBlock; isoBlock = (c, r2, z, hh) => { top = Math.max(top, z + hh); }; drawPlacedPiece('wall-tall', 12, 12, 'full'); isoBlock = o; pieceDrawHealth = 100; return +top.toFixed(2); }; return { full: cuts(100), at60: cuts(60), at10: cuts(10) }; });
  check(melt.full === 1.9 && melt.at60 < melt.full && melt.at10 < melt.at60 && melt.at10 > 0.3, 'S2c #3 walls MELT: drawn height drops with health', melt);
  await ctx.close();
  // S3 castle takes it; castle melts
  ({ ctx, p, errs } = await fresh(b));
  r = await oneBigWave(p, "");
  check(r.atHit.hp === r.before.hp - 3 * r.dmgPerHit, 'S3a nothing in the way: castle loses 3 hits', { before: r.before.hp, after: r.atHit.hp });
  check(r.worstPast <= 0.01 && !r.behind, 'S3b #1 even with no defences the surge stops at the castle ring', { worstPast: r.worstPast, behind: r.behind });
  const cm = await p.evaluate(async () => { const raf = () => new Promise(r => requestAnimationFrame(r)); const full = 0.5 + 1.95; castleHP = 40; const t0 = performance.now(); const seen = []; let n = 0; while (Math.abs(castleShown - 40) > 0.5 && performance.now() - t0 < 20000) { if (n++ % 15 === 0) seen.push(+castleCutZ().toFixed(2)); await raf(); } return { full, seen: seen.slice(0, 6), end: +castleCutZ().toFixed(2) }; });
  check(cm.seen.length >= 3 && cm.seen[0] > cm.end && cm.end < cm.full - 0.9, 'S3c #3 the castle MELTS: its cut height eases down as health drops', cm);
  check(errs.length === 0, 'S3d no page errors', errs.slice(0, 3));
  await ctx.close();
  // S4 build phase is safe
  ({ ctx, p, errs } = await fresh(b));
  const s4 = await p.evaluate(async () => { const hp0 = castleHP; bigWaveTimer = 1; let seen = false; const t0 = performance.now(); while (performance.now() - t0 < 6000) { if (bigWave) seen = true; await new Promise(r => requestAnimationFrame(r)); } return { phase: wavePhase, seen, hp0, hp: castleHP }; });
  check(s4.phase === 'build' && !s4.seen && s4.hp === s4.hp0, 'S4 build phase: no big wave comes even with the timer at 1', s4);
  await ctx.close();
  await b.close();
  console.log(fail ? 'FAILED (' + fail + ')' : 'ALL PASS');
  process.exit(fail ? 1 : 0);
})();
