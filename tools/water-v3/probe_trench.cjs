// probe_trench.cjs <url> [shotDir] : rising water in the moat (patch_water9). Exit 1 on any FAIL.
// Measures, straight down from each moat's back corner, how far below the rim the water starts.
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
  // three moats well apart behind/beside the castle, away from the sea; ordinary waves off; build phase
  const measure = (level) => p.evaluate(async (level) => {
    swashWaves.length = 0; swashNext = 1e12;
    const spots = { 'moat-shallow': [0, 9], 'moat-standard': [0, 5], 'moat-deep': [0, 1] };
    placedPieces.length = 0;
    for (const id in spots) placedPieces.push({ id, col: spots[id][0], row: spots[id][1], health: 100, decayTimer: 0, depth: level, cover: level > 0 ? 1 : 0, feedK: 1, damp: level > 0 ? 1 : 0 });
    ringDepth = level; ringCover = level > 0 ? 1 : 0; ringK = 1;
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
    const g = canvas.getContext('2d');
    const th = TH();
    const drop = (c, r) => {             // px from the back corner down to the first water-blue pixel (-1 = none)
      const q = iso(c, r, 0), x = Math.round(q.x), y0 = Math.round(q.y) + 2, n = Math.round(th) - 4;
      const d = g.getImageData(x, y0, 1, n).data;
      for (let i = 0; i < n; i++) if (d[i * 4 + 2] > d[i * 4] + 20) return +((i + 2) / th).toFixed(3);
      return -1;
    };
    const out = { ring: drop(7, 3), fn: typeof drawTrenchOnTile };
    for (const id in spots) out[id] = drop(spots[id][0], spots[id][1]);
    return out;
  }, level);
  const dry = await measure(0), half = await measure(0.5);
  const full = await measure(1);
  check(dry['moat-shallow'] === -1 && dry['moat-standard'] === -1 && dry['moat-deep'] === -1 && dry.ring === -1, 'T1 dry moats and ring show no water', dry);
  check(half['moat-shallow'] > 0.06 && half['moat-standard'] > half['moat-shallow'] + 0.04 && half['moat-deep'] > half['moat-standard'] + 0.04,
    'T2 half full: the surface sits below the rim, lower in deeper moats (shallow < standard < deep)', half);
  check(['moat-shallow', 'moat-standard', 'moat-deep'].every(id => full[id] > 0 && full[id] < half[id] - 0.03 && full[id] <= 0.2),
    'T3 full: the surface has climbed to just below the rim', full);
  check(half.ring > 0.1 && full.ring > 0 && full.ring < half.ring - 0.03, 'T4 castle ring: same rising level', { half: half.ring, full: full.ring });
  check(errs.length === 0, 'T5 no page errors', errs);
  await b.close();
  process.exit(fail ? 1 : 0);
})();
