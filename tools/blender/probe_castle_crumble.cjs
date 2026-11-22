// probe_castle_crumble.cjs <url-with-sheets> <url-melt-only> : the castle that crumbles in four sections. Exit 1 on any FAIL.
// <url-melt-only> serves the game without castle_sections.webp (castle_melt.png still there): the melt run must take over.
const { chromium } = require('playwright');
const [withUrl, meltUrl] = process.argv.slice(2);
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
  let { p, errs, ctx } = await open(withUrl);
  const r = await p.evaluate(async () => {
    const raf = n => new Promise(res => { const step = () => (n-- > 0 ? requestAnimationFrame(step) : res()); step(); });
    let flags = [];
    const realFlag = drawIsoFlag; drawIsoFlag = function (c, r2, z, col, t) { flags.push([c, r2]); return realFlag(c, r2, z, col, t); };
    const flagsNow = async () => { await raf(1); flags = []; await raf(1); return flags.slice(); };
    // the resting frames of the sheet: how many px change from one to the next, and how high the castle stands
    // (topmost opaque row) in the screen columns through the right section, the left section and the middle
    // (the middle column runs through the front and the back sections; the back tower is the tallest thing there)
    const cv = document.createElement('canvas'); cv.width = CRUMBLE_FW; cv.height = CRUMBLE_FH; const g = cv.getContext('2d');
    const frameData = f => { g.clearRect(0, 0, CRUMBLE_FW, CRUMBLE_FH); g.drawImage(crumbleImg, (f % CRUMBLE_COLS) * CRUMBLE_FW, Math.floor(f / CRUMBLE_COLS) * CRUMBLE_FH, CRUMBLE_FW, CRUMBLE_FH, 0, 0, CRUMBLE_FW, CRUMBLE_FH); return g.getImageData(0, 0, CRUMBLE_FW, CRUMBLE_FH).data; };
    const rests = [0, 1, 2, 3, 4].map(k => frameData(k * CRUMBLE_FRAMES));
    // each corner tower's body (tile centre, 1.6 game z up): solid while its section stands, empty sky once it has fallen
    // (sand heaps are far lower than that). Towers: front (3,3), right (3,0), left (0,3), back (0,0) - one per section.
    // The front tower is the exception: once it is gone the standing castle behind it shows through that spot, so
    // for it count how much of its box changes when it falls (frontChange).
    const S = CRUMBLE_SCALE, towerAt = [[3.5, 3.5], [3.5, 0.5], [0.5, 3.5], [0.5, 0.5]];
    const alphaAt = (d, c, r2, z) => { const x = Math.round(CRUMBLE_AX + (c - r2) * 28 * S), y = Math.round(CRUMBLE_AY + ((c + r2) * 14 - z * 28) * S); let t = 0;
      for (let j = -2; j <= 2; j++) for (let i = -2; i <= 2; i++) t += d[((y + j) * CRUMBLE_FW + x + i) * 4 + 3]; return Math.round(t / 25); };
    const towers = rests.map(d => towerAt.map(([c, r2]) => alphaAt(d, c, r2, 1.6)));
    const fx = Math.round(CRUMBLE_AX), fy0 = Math.round(CRUMBLE_AY + (7 * 14 - 2.2 * 28) * S), fy1 = Math.round(CRUMBLE_AY + (7 * 14 - 0.5 * 28) * S);
    let fc = 0, fn = 0;
    for (let y = fy0; y < fy1; y++) for (let x = fx - Math.round(20 * S); x <= fx + Math.round(20 * S); x++) {
      const j = (y * CRUMBLE_FW + x) * 4; fn++;
      if (Math.abs(rests[0][j] - rests[1][j]) + Math.abs(rests[0][j + 1] - rests[1][j + 1]) + Math.abs(rests[0][j + 2] - rests[1][j + 2]) + Math.abs(rests[0][j + 3] - rests[1][j + 3]) > 60) fc++; }
    const frontChange = +(fc / fn).toFixed(2);
    const changed = rests.slice(1).map((d, i) => { const p0 = rests[i]; let n = 0; for (let j = 3; j < d.length; j += 4) if (Math.abs(d[j] - p0[j]) > 64 || Math.abs(d[j - 3] - p0[j - 3]) > 40) n++; return +(n / (CRUMBLE_FW * CRUMBLE_FH)).toFixed(3); });
    const out = { ready: crumbleReady, meltRequested: !!meltImg.getAttribute('src'), changed, towers, frontChange };
    await raf(3); out.full = { fallen: castleFallen, tick: castleFallTick, flags: (await flagsNow()).length };
    castleHP = 74; await raf(3); out.soon = { fallen: castleFallen, tick: castleFallTick };
    await raf(CRUMBLE_FRAMES * CRUMBLE_TICKS + 5); out.after75 = { fallen: castleFallen, tick: castleFallTick, flags: await flagsNow() };
    // one big drop past two marks: the sections must fall one after the other
    castleHP = 20; const seen = []; let both = false;
    for (let i = 0; i < 2 * CRUMBLE_FRAMES * CRUMBLE_TICKS + 20; i++) { await raf(1); if (seen[seen.length - 1] !== castleFallen) seen.push(castleFallen); }
    out.after20 = { fallen: castleFallen, seen, flags: (await flagsNow()).length };
    castleHP = 0; await raf(CRUMBLE_FRAMES * CRUMBLE_TICKS + 10); out.after0 = { fallen: castleFallen, flags: (await flagsNow()).length };
    return out;
  });
  check(r.ready === true && r.meltRequested === false, 'K1 the crumble sheet loaded, and the melt sheet was not downloaded', { ready: r.ready, melt: r.meltRequested });
  // rest k: sections 0..k-1 have fallen -> their towers are gone (alpha < 40), the others still stand (alpha > 215)
  const towersOk = r.towers.every((row, k) => row.every((al, sec) => sec === 0 ? (k === 0 ? al > 215 : true) : sec < k ? al < 40 : al > 215)) && r.frontChange > 0.4;
  check(r.changed.every(v => v > 0.03) && towersOk,
    'K2 each resting stage of the sheet differs from the one before; a corner tower is solid until its section falls and gone after', { changed: r.changed, towers: r.towers, frontChange: r.frontChange });
  check(r.full.fallen === 0 && r.full.tick === -1 && r.full.flags === 5, 'K3 full health: whole castle, nothing falling, 5 flags', r.full);
  check(r.soon.fallen === 0 && r.soon.tick > 0 && r.after75.fallen === 1 && r.after75.tick === -1, 'K4 below 75%: the front section falls (animated), then the castle rests with 1 section gone', { soon: r.soon, after: r.after75.fallen });
  check(r.after75.flags.length === 4 && !r.after75.flags.some(f => f[0] === 6 && f[1] === 6), 'K5 the flag on the fallen front tower is gone, the other 4 still stand', r.after75.flags);
  check(r.after20.fallen === 3 && JSON.stringify(r.after20.seen) === '[1,2,3]' && r.after20.flags === 2, 'K6 one drop from 74 to 20 health: the right then the left section fall, one after the other; the 2 flags on the back section stay', r.after20);
  check(r.after0.fallen === 4 && r.after0.flags === 0, 'K7 zero health: all four sections down, no flags', r.after0);
  const rs = await p.evaluate(async () => {
    gameOver = true;
    canvas.dispatchEvent(new MouseEvent('click', { bubbles: true, clientX: 640, clientY: 360 }));
    await new Promise(res => requestAnimationFrame(() => requestAnimationFrame(res)));
    return { hp: castleHP, fallen: castleFallen, tick: castleFallTick, over: gameOver };
  });
  check(rs.over === false && rs.hp === 100 && rs.fallen === 0 && rs.tick === -1, 'K8 restart puts the castle back whole', rs);
  check(errs.length === 0, 'K9 no page errors (with sheets)', errs);
  await ctx.close();
  ({ p, errs, ctx } = await open(meltUrl));
  const m = await p.evaluate(() => ({ crumble: crumbleReady, melt: meltReady }));
  check(m.crumble === false && m.melt === true, 'K10 no crumble sheet: the melt run is loaded instead', m);
  check(errs.length === 0, 'K11 no page errors (melt only)', errs);
  await b.close();
  process.exit(fail ? 1 : 0);
})();
