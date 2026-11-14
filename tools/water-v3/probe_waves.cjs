// probe_waves.cjs <url> : wave-behaviour checks (patch_water5). Exit 1 on any FAIL.
//  W1 no "BIG WAVE" text is drawn while a big wave comes in and lands
//  W2 the big wave enters from one side and crosses to the other (left->right or right->left), over the castle
//  W3 a lone swash wave's bulge travels away from its entry side and widens (fans out) as it goes
//  W4 wave speeds vary: some lazy, some fast
//  W5 backwash: a wave running up into retreating water advances slower than the same wave on calm water
const { chromium } = require('playwright');
const url = process.argv[2];
let fail = 0;
const check = (ok, name, info) => { if (!ok) fail++; console.log('  ' + (ok ? 'PASS' : 'FAIL') + '  ' + name + '   ' + JSON.stringify(info)); };
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
  const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto(url); await p.waitForTimeout(1200);
  const raf = 'const raf = () => new Promise(r => requestAnimationFrame(r));';

  // W1 + W2
  const big = await p.evaluate(async (rafSrc) => { const raf = () => new Promise(r => requestAnimationFrame(r));
    const texts = []; const ft = CanvasRenderingContext2D.prototype.fillText;
    CanvasRenderingContext2D.prototype.fillText = function (t, ...a) { texts.push(String(t)); return ft.call(this, t, ...a); };
    startWave(); bigWaveTimer = 1;
    const t0 = performance.now(); while (!bigWave && performance.now() - t0 < 5000) await raf();
    if (!bigWave) return { noWave: true };
    const w = bigWave, xs = []; let hitX = null;
    while (bigWave === w && performance.now() - t0 < 30000) {
      if (typeof w.x === 'number') xs.push(w.x);
      if (w.hit && hitX === null) hitX = w.x;
      await raf();
    }
    for (let i = 0; i < 60; i++) await raf();
    CanvasRenderingContext2D.prototype.fillText = ft;
    return { banner: texts.filter(t => /BIG WAVE/i.test(t)).length, dir: w.dir, cx: w.cx, tw: TW(), first: xs[0], last: xs[xs.length - 1], hitX, n: xs.length };
  }, raf);
  check(!big.noWave && big.banner === 0, 'W1 no "BIG WAVE!" banner', { banner: big.banner });
  const crossOk = big.dir === 1 || big.dir === -1 ? ((big.first - big.cx) * big.dir < -big.tw && (big.last - big.cx) * big.dir > big.tw && Math.abs(big.hitX - big.cx) < big.tw * 0.75) : false;
  check(crossOk, 'W2 big wave enters on one side, crosses the castle as it hits, ends on the other side', big);

  // W3 lone swash wave: bulge travels from its entry side and fans out
  const lone = await p.evaluate(async (rafSrc) => { const raf = () => new Promise(r => requestAnimationFrame(r));
    if (typeof spawnSwashWave !== 'function') return { missing: true };
    const res = [];
    for (let trial = 0; trial < 6; trial++) {
      swashWaves.length = 0; swashNext = 1e12;
      spawnSwashWave(); const w = swashWaves[0];
      w.amp = TH() * 3; w.dir = trial % 2 ? -1 : 1; w.x0 = w.dir > 0 ? SW * 0.1 : SW * 0.9; w.spd = 1; w.rise = 40; w.fall = 160; w.base = 0; w.sig = SW * 0.09; w.v = 3; w.reach = SW * 0.6; w.up = SW * 0.04; if (typeof flowPh !== 'undefined') flowPh.fill(0);
      // Driven by hand, no frames in between: at each step compute the waterline once WITHOUT the wave and once
      // WITH it at the same tick, so pitch and chop cancel and only the wave's own run-up is left.
      const cents = [], widths = [], late = [], land = { max: 0, at100: 0 };
      const t0k = tick + 5; if (!('p' in w)) w.born = t0k;         // builds before patch 5 time a wave by tick - born
      for (let f = 0; f < 150; f++) {
        swashWaves.length = 0; updateSwash(t0k + f);
        const calm = []; for (let i = 0; i < SWASH_N; i++) calm.push(baseY[i] - rawY[i]);
        swashWaves.push(w); updateSwash(t0k + f);
        let sw = 0, sx = 0, peak = 0; const run = [];
        for (let i = 0; i < SWASH_N; i++) { const v = Math.max(0, (baseY[i] - rawY[i]) - calm[i]); run.push(v); if (v > peak) peak = v; sw += v; sx += v * i * SWASH_STEP; }
        if (peak < TH() * 0.5) continue;
        const c = sx / sw; let m2 = 0; for (let i = 0; i < SWASH_N; i++) m2 += run[i] * (i * SWASH_STEP - c) * (i * SWASH_STEP - c);
        const spread = Math.sqrt(m2 / sw);                          // how spread out the wave is (weighted std-dev, px)
        if (f % 10 === 0) cents.push(Math.round(c));
        if (f >= 45 && f < 55) widths.push(spread); if (f >= 135 && f < 145) late.push(spread);
        // does the water stay up where it landed while the front slides away? (a travelling bump drops behind itself)
        const i0 = Math.max(1, Math.min(SWASH_N - 2, Math.round(w.x0 / SWASH_STEP))), at0 = (run[i0 - 1] + run[i0] + run[i0 + 1]) / 3;
        if (at0 > land.max) land.max = at0;
        if (f === 100) land.at100 = at0;
      }
      const avg = a => Math.round(a.reduce((x, y) => x + y, 0) / (a.length || 1));
      res.push({ dir: w.dir, c0: cents[1], c1: cents[cents.length - 1], w0: avg(widths), w1: avg(late), skew: land.max > 0 ? Math.round(100 * land.at100 / land.max) : 0, flow: typeof flowPh === 'undefined' ? null : Math.round(Array.from(flowPh).reduce((x, y) => x + y, 0) / SWASH_N * w.dir) });
    }
    return { res };
  }, raf);
  const travelOk = !lone.missing && lone.res.every(r => (r.c1 - r.c0) * r.dir > 40);
  const fanOk = !lone.missing && lone.res.filter(r => r.w0 > 0 && r.w1 > r.w0 * 1.3).length >= 5;
  check(travelOk, 'W3a a lone wave travels away from its entry side (left->right / right->left)', lone.res || lone);
  const pourOk = !lone.missing && lone.res.every(r => r.skew >= 75);
  const flowOk = !lone.missing && lone.res.every(r => r.flow !== null && r.flow > 20);
  check(pourOk, 'W9 poured, not a travelling bump: with the front 300 px away, the water where it landed is still at 75%+ of its height (percent)', (lone.res || []).map(r => r.skew));
  check(flowOk, 'W10 foam/streaks in the thin sheet are carried sideways in the direction the wave slides (avg px per column)', (lone.res || []).map(r => r.flow));
  check(fanOk, 'W3b ...and fans out wider as it goes (spread of the run-up, late vs early; 5 of 6 trials)', (lone.res || []).map(r => [r.w0, r.w1]));

  // W4 speed variety, measured as how fast each wave's run-up actually happens (driven by hand, pitch/chop subtracted)
  const spd = await p.evaluate(() => {
    const ticks = [];
    for (let k = 0; k < 40; k++) {
      swashWaves.length = 0; swashNext = 1e12; spawnSwashWave(); const w = swashWaves[0];
      w.rise = 50; w.amp = TH() * 3; w.v = 0; w.sig = SW * 4; w.fan = 0; w.base = 1; w.x0 = SW / 2;   // no sideways travel: time-to-peak is run-up speed only
      const ref = Math.round(SW / 2 / SWASH_STEP), t0k = tick + 5; if (!('p' in w)) w.born = t0k;
      let best = -1e9, at = 0;
      for (let f = 0; f < 260; f++) {
        swashWaves.length = 0; updateSwash(t0k + f); const calm = baseY[ref] - rawY[ref];
        swashWaves.push(w); updateSwash(t0k + f); const v = (baseY[ref] - rawY[ref]) - calm;
        if (v > best + 0.01) { best = v; at = f; }
      }
      ticks.push(at);
    }
    swashWaves.length = 0; swashNext = 0;
    ticks.sort((a, b) => a - b);
    return { fastest: ticks[2], slowest: ticks[ticks.length - 3], all: ticks };
  });
  check(spd.slowest >= spd.fastest * 3, 'W4 wave speeds vary: slowest run-ups take at least 3x as long as the fastest', { fastest: spd.fastest, slowest: spd.slowest });

  // W5 backwash slows an incoming wave
  const bw = await p.evaluate(async (rafSrc) => { const raf = () => new Promise(r => requestAnimationFrame(r));
    const runUp = async (withBackwash) => {
      swashWaves.length = 0; swashNext = 1e12;
      if (withBackwash) { spawnSwashWave(); const o = swashWaves[0]; o.x0 = SW / 2; o.v = 0; o.dir = 1; o.amp = TH() * 2.5; o.rise = 10; o.fall = 400; o.spd = 1; o.sig = SW * 0.3; o.fan = 0; if ('p' in o) o.p = 12; else o.born = tick - 12; }
      spawnSwashWave(); const w = swashWaves[swashWaves.length - 1];
      w.x0 = SW / 2; w.v = 0; w.dir = 1; w.amp = TH() * 1.5; w.rise = 60; w.fall = 200; w.spd = 1; if ('p' in w) w.p = 0; else w.born = tick;
      for (let f = 0; f < 30; f++) await new Promise(r => requestAnimationFrame(r));
      const out = 'p' in w ? w.p : (tick - w.born);
      swashWaves.length = 0; swashNext = 0; return out;
    };
    const calm = await runUp(false), into = await runUp(true);
    return { calm: +calm.toFixed(1), intoBackwash: +into.toFixed(1) };
  }, raf);
  check(bw.intoBackwash < bw.calm * 0.8, 'W5 backwash slows a wave running up into it', bw);
  // W7 pitch: with no waves at all, how far does the see-saw tip the waterline (one end up, the other down)?
  // W8 fan-out: how many times wider than where it landed does a wave get, on average?
  const ext = await p.evaluate(() => {
    if (typeof swashCentre !== 'function') return { missing: true };
    swashWaves.length = 0; swashNext = 1e12; const sn = swashNext;
    let tip = 0; const L = 2, R = SWASH_N - 3;
    for (let tk = 0; tk < 30000; tk += 7) { updateSwash(tk); const d = Math.abs((baseY[L] - rawY[L]) - (baseY[R] - rawY[R])) / 2 / TH(); if (d > tip) tip = d; }
    let fan = 0; const N = 300;
    for (let k = 0; k < N; k++) { swashWaves.length = 0; spawnSwashWave(); const w = swashWaves[0]; fan += (w.reach || 0) / SW; }
    swashWaves.length = 0; swashNext = 0;
    return { tipTiles: +tip.toFixed(2), fanAvg: +(fan / N).toFixed(2) };
  });
  check(!ext.missing && ext.tipTiles >= 1.8, 'W7 strong pitch: the see-saw tips each end of the waterline by at least 1.8 tile-heights at its peak', ext);
  check(!ext.missing && ext.fanAvg >= 0.5, 'W8 long slide: waves run at least half the screen width along the beach, on average', ext);
  check(errs.length === 0, 'W6 no page errors', errs.slice(0, 3));
  await b.close();
  console.log(fail ? 'FAILED (' + fail + ')' : 'ALL PASS');
  process.exit(fail ? 1 : 0);
})();
