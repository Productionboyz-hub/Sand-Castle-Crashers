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
  // (once a wall is a flat mound this column reads the mound's back edge, so 5 health is only required not to read taller than 30)
  check(kinds.every(k => m[k][0] > m[k][1] && m[k][1] > m[k][2] && m[k][2] >= m[k][3] && m[k][3] > 0),
    'W3 every wall stands lower at 60 and at 30 health, no taller at 5, and is still there at 5', m);
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
  // toolbox icons come from the sheet (no code blocks drawn), and the buttons in the page were redrawn with them
  const icon = await p.evaluate(() => {
    const same = (a, b) => { const x = a.getContext('2d').getImageData(0, 0, 64, 38).data, y = b.getContext('2d').getImageData(0, 0, 64, 38).data; for (let i = 0; i < x.length; i++) if (x[i] !== y[i]) return false; return true; };
    const out = { blocks: 0, sameAsPage: [], opaque: [] };
    const o = miniBlock; miniBlock = function () { out.blocks++; return o.apply(null, arguments); };
    for (const id of ['wall-small', 'wall-medium', 'wall-tall']) {
      const c = document.createElement('canvas'); c.width = 64; c.height = 38;
      PIECES.find(q => q.id === id).draw(c.getContext('2d'), 32, 22);
      const d = c.getContext('2d').getImageData(0, 0, 64, 38).data; let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 128) n++;
      out.opaque.push(n);
      out.sameAsPage.push(same(c, document.querySelector('#toolbox .tool-btn[data-id="' + id + '"] canvas')));
    }
    miniBlock = o;
    return out;
  });
  check(icon.blocks === 0 && icon.sameAsPage.every(v => v) && icon.opaque[0] > 150 && icon.opaque[2] > icon.opaque[1] && icon.opaque[1] > icon.opaque[0],
    'W9 toolbox wall icons are drawn from the sheet, and the buttons on the page show them', icon);
  // a badly damaged sprite wall is drawn solid (no fade); the code-drawn fallback still fades
  const fade = await p.evaluate(async () => {
    const raf = n => new Promise(res => { const step = () => (n-- > 0 ? requestAnimationFrame(step) : res()); step(); });
    const g = canvas.getContext('2d'); let a = -1, tint = 0;
    placedPieces.length = 0; placedPieces.push({ id: 'wall-tall', col: 10, row: 4, health: 30, decayTimer: 0 });
    const o = drawPlacedPiece; drawPlacedPiece = function () { a = g.globalAlpha; return o.apply(null, arguments); };
    await raf(2); const sprite = a;
    wallsReady = false; await raf(2); const fallback = a; wallsReady = true;
    drawPlacedPiece = o; placedPieces.length = 0;
    return { sprite, fallback };
  });
  check(fade.sprite === 1 && fade.fallback < 1, 'W10 a damaged sprite wall is drawn solid; the code-drawn fallback still fades', fade);
  check(errs.length === 0, 'W6 no page errors (with sprites)', errs);
  await ctx.close();
  ({ p, errs, ctx } = await open(withoutUrl));
  const f = await p.evaluate(() => wallsReady);
  const m2 = await p.evaluate('(' + measure.toString() + ')(["wall-tall"],[100,30])');
  check(f === false && m2['wall-tall'][0] > 2.0 && m2['wall-tall'][1] < m2['wall-tall'][0] && m2['wall-tall'][1] > 0, 'W7 no sprite file: the code-drawn walls are used and still melt', { ready: f, tall: m2['wall-tall'] });
  const ic2 = await p.evaluate(() => { let n = 0; const o = miniBlock; miniBlock = function () { n++; return o.apply(null, arguments); }; const c = document.createElement('canvas'); c.width = 64; c.height = 38; PIECES.find(q => q.id === 'wall-tall').draw(c.getContext('2d'), 32, 22); miniBlock = o; return n; });
  check(ic2 > 0, 'W11 no sprite file: the code-drawn wall icon is used', { blocks: ic2 });
  check(errs.length === 0, 'W8 no page errors (without sprites)', errs);
  await b.close();
  process.exit(fail ? 1 : 0);
})();
