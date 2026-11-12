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
      w.amp = TH() * 3; w.dir = trial % 2 ? -1 : 1; w.x0 = w.dir > 0 ? SW * 0.1 : SW * 0.9; w.spd = 1; w.rise = 40; w.fall = 160; w.base = 0; w.sig = SW * 0.09; w.v = 3;
      const cents = [], widths = [], late = [];
      for (let f = 0; f < 150 && swashWaves.includes(w); f++) {
        await new Promise(r => requestAnimationFrame(r));
        const run = []; for (let i = 0; i < SWASH_N; i++) run.push(baseY[i] - rawY[i]);
        const peak = Math.max(...run); if (peak < TH() * 0.8) continue;
        let sw = 0, sx = 0, n = 0; for (let i = 0; i < SWASH_N; i++) if (run[i] > peak * 0.6) { sw += run[i]; sx += run[i] * i * SWASH_STEP; n++; }
        if (f % 10 === 0) cents.push(Math.round(sx / sw));
        if (f >= 55 && f < 65) widths.push(n * SWASH_STEP); if (f >= 135 && f < 145) late.push(n * SWASH_STEP);
      }
      const avg = a => Math.round(a.reduce((x, y) => x + y, 0) / (a.length || 1));
      res.push({ dir: w.dir, c0: cents[1], c1: cents[cents.length - 1], w0: avg(widths), w1: avg(late) });
    }
    return { res };
  }, raf);
  const travelOk = !lone.missing && lone.res.every(r => (r.c1 - r.c0) * r.dir > 40);
  const fanOk = !lone.missing && lone.res.filter(r => r.w0 > 0 && r.w1 > r.w0 * 1.35).length >= 5;
  check(travelOk, 'W3a a lone wave travels away from its entry side (left->right / right->left)', lone.res || lone);
  check(fanOk, 'W3b ...and fans out wider as it goes (width at 60% of peak, late vs early; 5 of 6 trials)', (lone.res || []).map(r => [r.w0, r.w1]));

  // W4 speed variety, measured as how fast each wave's run-up actually happens
  const spd = await p.evaluate(async (rafSrc) => { const raf = () => new Promise(r => requestAnimationFrame(r));
    const ticks = [];
    for (let k = 0; k < 40; k++) {
      swashWaves.length = 0; swashNext = 1e12; spawnSwashWave(); const w = swashWaves[0];
      w.rise = 50; w.amp = TH() * 3; w.v = 0; w.sig = SW * 4; w.fan = 0; w.base = 1;   // no sideways travel: time-to-peak is run-up speed only
      const ref = Math.max(0, Math.min(SWASH_N - 1, Math.round((typeof swashCentre === 'function' ? swashCentre(w, 0) : w.x0) / SWASH_STEP)));
      let best = -1e9, at = 0;
      for (let f = 0; f < 230; f++) { await new Promise(r => requestAnimationFrame(r)); const v = baseY[ref] - rawY[ref]; if (v > best) { best = v; at = f; } }
      ticks.push(at);
    }
    swashWaves.length = 0; swashNext = 0;
    ticks.sort((a, b) => a - b);
    return { fastest: ticks[2], slowest: ticks[ticks.length - 3], all: ticks };
  }, raf);
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
  check(errs.length === 0, 'W6 no page errors', errs.slice(0, 3));
  await b.close();
  console.log(fail ? 'FAILED (' + fail + ')' : 'ALL PASS');
  process.exit(fail ? 1 : 0);
})();
