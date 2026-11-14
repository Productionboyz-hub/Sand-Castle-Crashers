// probe_truck.cjs <url> : cleaner truck size (patch_truck10). Exit 1 on any FAIL.
// Measures the width in pixels of the truck's blue cab at two zoom levels.
const { chromium } = require('playwright');
const url = process.argv[2];
let fail = 0;
const check = (ok, name, info) => { if (!ok) fail++; console.log('  ' + (ok ? 'PASS' : 'FAIL') + '  ' + name + '   ' + JSON.stringify(info)); };
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
  const p = await ctx.newPage();
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto(url, { waitUntil: 'load' }); await p.waitForTimeout(1200);
  const cabWidth = (zoomMul) => p.evaluate(async (zoomMul) => {
    swashWaves.length = 0; swashNext = 1e12;
    if (!window.__z0) window.__z0 = camZoom;
    camZoom = camZoomDest = window.__z0 * zoomMul;
    truck = { col: 9, row: 1, dirC: 1 };
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
    const q = iso(truck.col, truck.row, 0.02), R = 140;
    const d = canvas.getContext('2d').getImageData(Math.round(q.x) - R, Math.round(q.y) - R, 2 * R, 2 * R).data;
    let x0 = 1e9, x1 = -1;
    for (let y = 0; y < 2 * R; y++) for (let x = 0; x < 2 * R; x++) {
      const i = (y * 2 * R + x) * 4;
      if (Math.abs(d[i] - 63) < 6 && Math.abs(d[i + 1] - 169) < 6 && Math.abs(d[i + 2] - 224) < 6) { if (x < x0) x0 = x; if (x > x1) x1 = x; }
    }
    return { cab: x1 - x0 + 1, zoom: +camZoom.toFixed(3), tourist: +(31 * camZoom * 0.9).toFixed(1) };
  }, zoomMul);
  const a = await cabWidth(1), z = await cabWidth(1.5);
  check(z.cab > a.cab * 1.35 && z.cab < a.cab * 1.65, 'K1 the truck scales with zoom (1.5x zoom -> ~1.5x wider cab)', { at1: a, at1_5: z });
  // the solid blue of the cab is ~12.5 of the truck's 40 drawing units, so 0.7 here = a truck about 2.2 tourist-heights long
  check(a.cab > a.tourist * 0.7, 'K2 the cab blue is over 0.7 tourist-heights wide (truck about 2.2+ tourist-heights long)', { cab: a.cab, tourist: a.tourist });
  check(errs.length === 0, 'K3 no page errors', errs);
  await b.close();
  process.exit(fail ? 1 : 0);
})();
