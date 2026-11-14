// probe_wall_sprites.cjs <url-with-sprites> <url-without-sprites> [screenshot.png] : the Blender walls in the game. Exit 1 on any FAIL.
const { chromium } = require('playwright');
const [withUrl, withoutUrl, shot] = process.argv.slice(2);
let fail = 0;
const check = (ok, name, info) => { if (!ok) fail++; console.log('  ' + (ok ? 'PASS' : 'FAIL') + '  ' + name + '   ' + JSON.stringify(info)); };
// how tall a wall of this kind and health stands on screen, in game z units: the highest pixel it changes above its tile centre.
// On that screen column the highest point of a whole wall is its back top corner, which draws 0.5 z above its real height.
const measure = async (kinds, healths) => {
  const raf = n => new Promise(res => { const step = () => (n-- > 0 ? requestAnimationFrame(step) : res()); step(); });
  const g = canvas.getContext('2d'), C = 10, R = 4;
  const q = iso(C + 0.5, R + 0.5, 0), x = Math.round(q.x), y0 = Math.round(q.y), span = Math.round(80 * camZoom);
  const column = () => g.getImageData(x, y0 - span, 1, span).data;
  placedPieces.length = 0; await raf(2);
  const base = column(), out = {};
  for (const id of kinds) {
    out[id] = [];
    for (const h of healths) {
      placedPieces.length = 0;
      placedPieces.push({ id: id, col: C, row: R, health: h, decayTimer: 0 });
      await raf(2);
      const d = column(); let top = span;
      for (let i = 0; i < span; i++) if (Math.abs(d[i * 4] - base[i * 4]) + Math.abs(d[i * 4 + 1] - base[i * 4 + 1]) + Math.abs(d[i * 4 + 2] - base[i * 4 + 2]) > 24) { top = i; break; }
      out[id].push(+((span - top) / (28 * camZoom)).toFixed(2));
    }
  }
  placedPieces.length = 0;
  return out;
};
(async () => {
  const b = await chromium.launch();
  const open = async (url) => {
    const ctx = await b.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
    const p = await ctx.newPage();
    const errs = []; p.on('pageerror', e => errs.push(e.message));
    await p.goto(url, { waitUntil: 'load' }); await p.waitForTimeout(1500);
    return { p, errs, ctx };
  };
  const kinds = ['wall-small', 'wall-medium', 'wall-tall'], healths = [100, 60, 30, 5];
  let { p, errs, ctx } = await open(withUrl);
  const ready = await p.evaluate(() => wallsReady);
  check(ready === true, 'W1 the wall sheet loaded', { ready });
  const m = await p.evaluate('(' + measure.toString() + ')(' + JSON.stringify(kinds) + ',' + JSON.stringify(healths) + ')');
  const full = kinds.map(k => m[k][0]);
  check(Math.abs(full[0] - 0.5 - 0.6) < 0.2 && Math.abs(full[1] - 0.5 - 1.38) < 0.2 && Math.abs(full[2] - 0.5 - 1.9) < 0.2,
    'W2 at full health each wall stands at its game height (small 0.6, medium 1.38, tall 1.9; measured + 0.5)', full);
  check(kinds.every(k => m[k][0] > m[k][1] && m[k][1] > m[k][2] && m[k][2] > m[k][3] && m[k][3] > 0),
    'W3 every wall stands lower at 60, 30 and 5 health, and is still there at 5', m);
  // colour: pale castle sand on the sun-lit face, lighter than the shadowed face
  const col = await p.evaluate(async () => {
    placedPieces.length = 0; placedPieces.push({ id: 'wall-tall', col: 10, row: 4, health: 100, decayTimer: 0 });
    await new Promise(res => requestAnimationFrame(() => requestAnimationFrame(res)));
    const g = canvas.getContext('2d'), at = (c, r2, z) => { const q = iso(c, r2, z), d = g.getImageData(Math.round(q.x), Math.round(q.y), 1, 1).data; return [d[0], d[1], d[2]]; };
    const out = { lit: at(10.5, 5, 0.8), shadow: at(11, 4.5, 0.8) };
    placedPieces.length = 0;
    return out;
  });
  check(col.lit[2] > 150 && col.lit[0] - col.lit[2] < 80 && col.lit[0] > col.shadow[0] + 15, 'W4 castle sand colours: pale, lit face lighter than the shadowed face', col);
  // cross-fade: a health between two stages draws a mixed frame; a long run of healths never keeps more than the cap
  const mix = await p.evaluate(async () => {
    const raf = n => new Promise(res => { const step = () => (n-- > 0 ? requestAnimationFrame(step) : res()); step(); });
    wallsMix.clear(); placedPieces.length = 0;
    placedPieces.push({ id: 'wall-medium', col: 10, row: 4, health: 100, decayTimer: 0 }); await raf(2);
    const whole = wallsMix.size;
    placedPieces[0].health = 93; await raf(2);
    const between = wallsMix.size; let most = 0;
    for (let h = 100; h > 0; h -= 1) { for (const id of ['wall-small', 'wall-medium', 'wall-tall']) { placedPieces[0].id = id; placedPieces[0].health = h; await raf(1); } most = Math.max(most, wallsMix.size); }
    placedPieces.length = 0;
    return { whole, between, most, cap: WALLS_MIX_MAX };
  });
  check(mix.whole === 0 && mix.between === 1 && mix.most <= mix.cap, 'W5 whole stages come straight from the sheet, in-between health is cross-faded, mixed frames stay under the cap', mix);
  if (shot) {
    await p.evaluate(async () => {
      placedPieces.length = 0;
      ['wall-small', 'wall-medium', 'wall-tall'].forEach((id, k) => [100, 80, 60, 40, 20, 5].forEach((h, j) => placedPieces.push({ id: id, col: 8 + j, row: 1 + k * 2, health: h, decayTimer: 0 })));
      for (let c = 8; c < 12; c++) placedPieces.push({ id: 'wall-medium', col: c, row: 8, health: 100, decayTimer: 0 });
      await new Promise(res => requestAnimationFrame(() => requestAnimationFrame(res)));
    });
    await p.screenshot({ path: shot });
    await p.evaluate(() => { placedPieces.length = 0; });
  }
  check(errs.length === 0, 'W6 no page errors (with sprites)', errs);
  await ctx.close();
  ({ p, errs, ctx } = await open(withoutUrl));
  const f = await p.evaluate(() => wallsReady);
  const m2 = await p.evaluate('(' + measure.toString() + ')(["wall-tall"],[100,30])');
  check(f === false && m2['wall-tall'][0] > 2.0 && m2['wall-tall'][1] < m2['wall-tall'][0] && m2['wall-tall'][1] > 0, 'W7 no sprite file: the code-drawn walls are used and still melt', { ready: f, tall: m2['wall-tall'] });
  check(errs.length === 0, 'W8 no page errors (without sprites)', errs);
  await b.close();
  process.exit(fail ? 1 : 0);
})();
