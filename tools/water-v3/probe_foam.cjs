// probe_foam.cjs <url> : lacy foam + see-through shallows (patch_water11). Exit 1 on any FAIL.
// Foam is measured on screen behind the water's leading edge: a wide band, and LACE (white strands with water in
// the holes), not a solid ribbon and not nothing. Shallows are measured in the water texture's alpha.
const { chromium, devices } = require('playwright');
const url = process.argv[2];
let fail = 0;
const check = (ok, name, info) => { if (!ok) fail++; console.log('  ' + (ok ? 'PASS' : 'FAIL') + '  ' + name + '   ' + JSON.stringify(info)); };
(async () => {
  const b = await chromium.launch();
  for (const [n, o] of [['desk', { viewport: { width: 1280, height: 720 } }], ['iphone', devices['iPhone 13']]]) {
    const c = await b.newContext(o); const p = await c.newPage();
    const errs = []; p.on('pageerror', e => errs.push(e.message));
    await p.goto(url); await p.waitForTimeout(800);
    await p.evaluate(() => { getTideT = () => 0.6; });
    await p.waitForTimeout(2500);
    const r = await p.evaluate(async () => {
      const raf = () => new Promise(res => requestAnimationFrame(res));
      const th = Math.max(TH(), WATER_PATTERN_MIN_PX);
      // white share in bands behind the edge (in tile-heights), over 6 frames
      const bands = [[0, 0.3], [0.5, 1.5], [1.5, 2.5], [5, 7]], white = bands.map(() => [0, 0]);
      let alphaNear = 0, alphaFar = 0, na = 0, nf = 0;
      for (let f = 0; f < 6; f++) {
        await raf(); await raf();
        const img = ctx.getImageData(0, 0, SW, SH).data;
        for (let x = 4; x < SW - 4; x += 2) {
          const e = visShoreYAt(x);
          bands.forEach((bd, k) => {
            for (let y = Math.ceil(e + bd[0] * th); y < Math.min(SH - 60, e + bd[1] * th); y += 2) {
              const i = (y * SW + x) * 4, r = img[i], g = img[i + 1], bl = img[i + 2];
              white[k][1]++;
              if (Math.min(r, g, bl) > 165) white[k][0]++;   // foam-white (part-see-through strands included); sand and teal water have a low red or blue
            }
          });
          // water texture alpha: 0.6 tile and 7 tiles behind the TIDE line (outside any run-up)
          const tide = baseShoreYAt(x), d = wImg.data, tx = Math.floor(x / W_SCALE);
          const yn = Math.floor((tide + 0.6 * th) / W_SCALE), yf = Math.floor((tide + 7 * th) / W_SCALE);
          if (tide > e && yn < WH) { alphaNear += d[(yn * WW + tx) * 4 + 3]; na++; }
          if (yf < WH) { alphaFar += d[(yf * WW + tx) * 4 + 3]; nf++; }
        }
      }
      return { white: white.map(w => +(w[0] / Math.max(1, w[1])).toFixed(3)), alphaNear: +(alphaNear / Math.max(1, na) / 255).toFixed(2), alphaFar: +(alphaFar / Math.max(1, nf) / 255).toFixed(2), th: +th.toFixed(1) };
    });
    check(r.white[0] > 0.6, n + ' F1 a bright foam lip right at the edge', { lip: r.white[0] });
    check(r.white[1] > 0.25 && r.white[1] < 0.9 && r.white[2] > 0.05 && r.white[2] < r.white[1], n + ' F2 lace behind the lip: strands with holes, thinning with distance (0.5-1.5 and 1.5-2.5 tiles back)', { near: r.white[1], further: r.white[2] });
    check(r.white[3] < 0.08, n + ' F3 open water further out is not covered in foam (5-7 tiles back)', { far: r.white[3] });
    check(r.alphaNear < 0.6 && r.alphaFar > 0.95, n + ' F4 shallows are see-through near the tide line and the water turns opaque further out', { near: r.alphaNear, far: r.alphaFar });
    check(errs.length === 0, n + ' F5 no page errors', errs.slice(0, 3));
    await c.close();
  }
  await b.close();
  process.exit(fail ? 1 : 0);
})();
