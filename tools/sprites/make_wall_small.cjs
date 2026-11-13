// make_wall_small.cjs <outDir> : draws the "small wall" piece as a transparent PNG, in code (no image model).
// 2:1 dimetric, one tile long, crenellated, flat cut ends, CONTEXT.md palette + lighting (sun upper LEFT,
// right faces shadowed with a cool tint). No ground, no base, no cast shadow.
// Output: wall-small.png (512x512, tile is 512 wide; the tile's TOP corner is at pixel 256,230)
//         wall-small_preview.png (same sprite on beach sand, three in a row, to check it tiles)
const { chromium } = require('playwright');
const out = process.argv[2] || '.';
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1100, height: 700 }, deviceScaleFactor: 1 });
  const urls = await p.evaluate(() => {
    const W = 512, AX = 256, AY = 230;                       // tile width, anchor = tile's top corner
    const cv = document.createElement('canvas'); cv.width = 512; cv.height = 512;
    const g = cv.getContext('2d');
    const P = (u, v, z) => [AX + (u - v) * W / 2, AY + (u + v) * W / 4 - z * W / 2];
    let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    const path = pts => { g.beginPath(); pts.forEach((q, i) => i ? g.lineTo(q[0], q[1]) : g.moveTo(q[0], q[1])); g.closePath(); };
    // one face: base colour, top-to-bottom shade, sand grain, soft rounded edge
    function face(pts, col, colLow, grain, edge) {
      const ys = pts.map(q => q[1]), y0 = Math.min(...ys), y1 = Math.max(...ys);
      const xs = pts.map(q => q[0]), x0 = Math.min(...xs), x1 = Math.max(...xs);
      const gr = g.createLinearGradient(0, y0, 0, y1); gr.addColorStop(0, col); gr.addColorStop(1, colLow);
      path(pts); g.fillStyle = gr; g.fill();
      g.lineJoin = 'round'; g.lineWidth = 3; g.strokeStyle = gr; g.stroke();          // rounds the corners a little
      g.save(); path(pts); g.clip();
      const n = Math.round((x1 - x0) * (y1 - y0) / 55);
      for (let i = 0; i < n; i++) {
        const x = x0 + rnd() * (x1 - x0), y = y0 + rnd() * (y1 - y0), r = 0.6 + rnd() * 1.3, d = rnd();
        g.fillStyle = d < 0.5 ? 'rgba(120,96,62,' + (grain * (0.25 + rnd() * 0.5)).toFixed(3) + ')' : 'rgba(255,248,230,' + (grain * (0.25 + rnd() * 0.5)).toFixed(3) + ')';
        g.beginPath(); g.arc(x, y, r, 0, 6.3); g.fill();
      }
      g.restore();
      if (edge) { g.strokeStyle = edge; g.lineWidth = 2.5; g.lineCap = 'round'; g.beginPath(); g.moveTo(pts[0][0], pts[0][1]); g.lineTo(pts[1][0], pts[1][1]); g.stroke(); }
    }
    // palette (CONTEXT.md): lit #EFE0C4, top #E2CFAC, shadow #C2A87F with a cool tint, crevice #A98D66
    const LIT = '#EFE0C4', LIT_LOW = '#DEC9A2', TOP = '#E6D4B2', TOP_LOW = '#DCC8A2', SH = '#BFAA8C', SH_LOW = '#A9987F';
    // box u0..u1, v0..v1, z0..z1 : top, long face (v1 side, faces the sun), end face (u1 side, in shadow)
    function box(u0, u1, v0, v1, z0, z1, damp) {
      face([P(u0, v1, z1), P(u1, v1, z1), P(u1, v1, z0), P(u0, v1, z0)], LIT, damp ? '#D2B98F' : LIT_LOW, 0.5, 'rgba(255,250,238,0.55)');
      face([P(u1, v1, z1), P(u1, v0, z1), P(u1, v0, z0), P(u1, v1, z0)], SH, damp ? '#9C8B76' : SH_LOW, 0.4, null);
      face([P(u0, v0, z1), P(u1, v0, z1), P(u1, v1, z1), P(u0, v1, z1)], TOP, TOP_LOW, 0.45, null);
    }
    const V0 = 0.3, V1 = 0.7, H = 0.62, MH = 0.2;
    box(0, 1, V0, V1, 0, H, true);                                       // wall body, damp toward the foot
    // packed-sand layer lines and a few bucket-mould seams on the long face
    g.lineCap = 'round';
    for (const z of [0.2, 0.41]) {
      const a = P(0, V1, z), c = P(1, V1, z);
      g.strokeStyle = 'rgba(169,141,102,0.38)'; g.lineWidth = 2; g.beginPath(); g.moveTo(a[0], a[1]); g.lineTo(c[0], c[1]); g.stroke();
      g.strokeStyle = 'rgba(255,250,238,0.35)'; g.lineWidth = 1.5; g.beginPath(); g.moveTo(a[0], a[1] + 2.5); g.lineTo(c[0], c[1] + 2.5); g.stroke();
    }
    for (const [u, za, zb] of [[0.25, 0, 0.2], [0.75, 0, 0.2], [0.5, 0.2, 0.41], [0.25, 0.41, H], [0.75, 0.41, H]]) {
      const a = P(u, V1, za), c = P(u, V1, zb);
      g.strokeStyle = 'rgba(169,141,102,0.3)'; g.lineWidth = 2; g.beginPath(); g.moveTo(a[0], a[1]); g.lineTo(c[0], c[1]); g.stroke();
    }
    // crenellations: half merlons at both cut ends so identical segments join into whole ones
    const merlons = [[0, 0.125], [0.3125, 0.6875 - 0.125], [0.875, 1]];
    merlons[1] = [0.375, 0.625];
    for (const [a, c] of merlons) box(a, c, V0, V1, H, H + MH, false);
    const sprite = cv.toDataURL('image/png');
    // preview: three in a row on beach sand, with a runtime-style contact shadow
    const pv = document.createElement('canvas'); pv.width = 1100; pv.height = 700;
    const q = pv.getContext('2d'); q.fillStyle = '#EDDFC4'; q.fillRect(0, 0, 1100, 700);
    const s = 0.62;
    for (let k = 0; k < 3; k++) {
      const x = 80 + k * 256 * s, y = 20 + k * 128 * s;
      q.save(); q.filter = 'blur(8px)'; q.fillStyle = 'rgba(138,115,85,0.28)';
      q.beginPath(); q.ellipse(x + 256 * s + 14, y + (230 + 128 + 26) * s, 150 * s, 62 * s, 0.46, 0, 6.3); q.fill(); q.restore();
    }
    for (let k = 0; k < 3; k++) q.drawImage(cv, 80 + k * 256 * s, 20 + k * 128 * s, 512 * s, 512 * s);
    return [sprite, pv.toDataURL('image/png')];
  });
  const fs = require('fs');
  fs.writeFileSync(out + '/wall-small.png', Buffer.from(urls[0].split(',')[1], 'base64'));
  fs.writeFileSync(out + '/wall-small_preview.png', Buffer.from(urls[1].split(',')[1], 'base64'));
  await b.close();
  console.log('wrote', out + '/wall-small.png', out + '/wall-small_preview.png');
})();
