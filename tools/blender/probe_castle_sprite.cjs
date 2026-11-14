// probe_castle_sprite.cjs <url-with-sprite> <url-without-sprite> : the melt-run castle in the game. Exit 1 on any FAIL.
const { chromium } = require('playwright');
const [withUrl, withoutUrl] = process.argv.slice(2);
let fail = 0;
const check = (ok, name, info) => { if (!ok) fail++; console.log('  ' + (ok ? 'PASS' : 'FAIL') + '  ' + name + '   ' + JSON.stringify(info)); };
(async () => {
  const b = await chromium.launch();
  const open = async (url) => {
    const ctx = await b.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
    const p = await ctx.newPage();
    const errs = []; p.on('pageerror', e => errs.push(e.message));
    await p.goto(url, { waitUntil: 'load' }); await p.waitForTimeout(1500);
    return { p, errs, ctx };
  };
  // how much castle stands tall: opaque pixels in the mixed sprite more than 6 game px above its anchor row
  const topAbove = () => { const d = meltBlendCtx.getImageData(0, 0, MELT_FW, MELT_AY - 12).data; let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 128) n++; return n; };
  let { p, errs, ctx } = await open(withUrl);
  const r = await p.evaluate(async (topSrc) => {
    const topAbove = new Function('return (' + topSrc + ')()');
    const raf = n => new Promise(res => { const step = () => (n-- > 0 ? requestAnimationFrame(step) : res()); step(); });
    const out = { ready: meltReady, pos0: castleMeltPos };
    let flags = [];                                          // every flag drawn in a frame: [col, row, z]
    const realFlag = drawIsoFlag; drawIsoFlag = function (c, r2, z, col, t) { flags.push([c, r2, +z.toFixed(2)]); return realFlag(c, r2, z, col, t); };
    const flagsNow = async () => { await raf(1); flags = []; await raf(1); return flags.slice(); };
    await raf(3); out.top100 = topAbove(); out.flags100 = await flagsNow();
    castleHP = 50; await raf(8); out.posSoonAfterHit = castleMeltPos;
    await raf(400); out.pos50 = castleMeltPos; out.top50 = topAbove(); out.flags50 = await flagsNow();
    castleHP = 0; await raf(500); out.pos0hp = castleMeltPos; out.top0 = topAbove(); out.flags0 = await flagsNow();
    return out;
  }, topAbove.toString());
  check(r.ready === true, 'C1 the sprite sheet loaded', { ready: r.ready });
  check(r.posSoonAfterHit > 0 && r.posSoonAfterHit < 2 && r.pos50 === 5, 'C2 after a hit the castle eases to its new stage (not a jump) and rests on a whole one: half health -> stage 5', { soon: r.posSoonAfterHit, settled: r.pos50 });
  check(Math.abs(r.pos0hp - 9) < 0.05, 'C3 zero health -> the last stage (mound)', { pos: r.pos0hp });
  check(r.top100 > r.top50 * 1.1 && r.top50 > r.top0 * 1.1, 'C4 less of the castle stands tall as health drops (opaque px above the base)', { top100: r.top100, top50: r.top50, top0: r.top0 });
  check(r.flags100.length === 5 && r.flags50.length === 2 && r.flags0.length === 0 && r.flags50.every(f => f[2] >= 1.8),
    'C9 flags: 5 on the whole castle, only the 2 on towers still standing at half health, none on the mound', { full: r.flags100.length, half: r.flags50, zero: r.flags0.length });
  // restart resets the melt
  const rs = await p.evaluate(async () => {
    gameOver = true;
    canvas.dispatchEvent(new MouseEvent('click', { bubbles: true, clientX: 640, clientY: 360 }));
    await new Promise(res => requestAnimationFrame(() => requestAnimationFrame(res)));
    return { hp: castleHP, pos: castleMeltPos, over: gameOver };
  });
  check(rs.over === false && rs.hp === 100 && rs.pos < 0.01, 'C5 restart puts the castle back whole', rs);
  check(errs.length === 0, 'C6 no page errors (with sprite)', errs);
  await ctx.close();
  ({ p, errs, ctx } = await open(withoutUrl));
  const f = await p.evaluate(() => ({ ready: meltReady, hasFallback: typeof isoBlock === 'function' }));
  const px = await p.evaluate(() => { const q = iso(7, 7, 0.2), d = canvas.getContext('2d').getImageData(Math.round(q.x), Math.round(q.y), 1, 1).data; return [d[0], d[1], d[2]]; });
  check(f.ready === false && px[0] > 120 && px[0] - px[2] > 90, 'C7 no sprite file: the old drawn castle is used (yellow block at the front corner)', { ready: f.ready, px });
  check(errs.length === 0, 'C8 no page errors (without sprite)', errs);
  await b.close();
  process.exit(fail ? 1 : 0);
})();
