#!/usr/bin/env python3
# Sand Castle Crashers - water v3: RISING WATER in the moat, applied ON TOP of patch_water8.py's output.
#   - a moat is drawn as a sunken trench: two inner side walls going down to a floor below sand level
#     (shallow / standard / deep moats have visibly different depths; the castle ring is a standard trench)
#   - when a wave feeds it, the water SURFACE climbs the inner walls until it sits just below the rim;
#     when it dries the level drops back down and leaves the floor (and walls) damp
#   - DRAWING ONLY: the level is read from the existing fill values (p.depth * p.cover for placed moats,
#     ringDepth * per-tile ringCover for the castle ring). Damage, fill and dry rates are untouched.
#   - all geometry goes through iso()
# usage: patch_water9.py <v8.html> <out.html>
import sys
src = open(sys.argv[1], encoding='utf-8').read()

def rep(old, new, count=1):
    global src
    assert src.count(old) == count, (src.count(old), old[:80])
    src = src.replace(old, new)

# ── the trench drawer replaces the flat pool drawer ─────────────────────────────────────────────
a = src.index("// Water pouring across one tile from its sea-side corner: cover 0..1 = how far it has spread,")
b = src.index("// Castle + walls melt: blocks are cut off above a height that drops with health.")
assert 0 < a < b and src.count("function drawPoolOnTile(") == 1
src = src[:a] + r'''// ← TUNE: how far below the sand each moat's floor sits (in tile-heights) and how close to the rim a full moat gets.
const TRENCH_DEPTH = { 'moat-shallow': 0.2, 'moat-standard': 0.38, 'moat-deep': 0.58 };
const TRENCH_RING_DEPTH = 0.38;   // the castle ring is a standard trench
const TRENCH_RIM_GAP    = 0.05;   // a full moat's surface stops this far below the rim
// Is there a trench on this tile (a placed moat or the castle ring)? Neighbouring trenches join up: no wall between them.
function isRingTile(c, r) {
  return ((r === 2 || r === 7) && c >= 3 && c <= 6) || ((c === 2 || c === 7) && r >= 3 && r <= 6) || (c === 7 && r === 7);
}
function trenchAt(c, r) {
  if (isRingTile(c, r)) return true;
  for (const q of placedPieces) if (q.col === c && q.row === r && q.id.indexOf('moat-') === 0) return true;
  return false;
}
// One tile of sunken trench. D = floor depth below the sand (tile-heights), level 0..1 = how high the water
// stands (0 = empty, 1 = just below the rim), damp 0..1 = how wet the sand still is after it drains.
// wall = [lit, shaded] inner-wall colours, floor = [near, far] floor colours, c1/c2 = water colours.
function drawTrenchOnTile(col, row, D, level, damp, wall, floor, c1, c2) {
  const openW = trenchAt(col - 1, row), openN = trenchAt(col, row - 1);   // joined to the trench behind: no wall there
  const quad = (pts, z) => {
    ctx.beginPath();
    pts.forEach((q, k) => { const w = iso(q[0], q[1], z); if (k) ctx.lineTo(w.x, w.y); else ctx.moveTo(w.x, w.y); });
    ctx.closePath();
  };
  const wallQuad = (c0, r0, c1q, r1q) => {
    const A = iso(c0, r0, 0), B = iso(c1q, r1q, 0), C = iso(c1q, r1q, -D), E = iso(c0, r0, -D);
    ctx.beginPath(); ctx.moveTo(A.x, A.y); ctx.lineTo(B.x, B.y); ctx.lineTo(C.x, C.y); ctx.lineTo(E.x, E.y); ctx.closePath();
  };
  const a0 = ctx.globalAlpha;
  const top = iso(col, row, 0), bot = iso(col + 1, row + 1, 0);
  ctx.save();
  clipTilePath(col, row); ctx.clip();                       // everything stays inside the rim
  // floor (the front walls are hidden by the ground, so the floor runs to the front rim)
  const gf = ctx.createLinearGradient(top.x, top.y, bot.x, bot.y);
  gf.addColorStop(0, floor[1]); gf.addColorStop(1, floor[0]);
  ctx.fillStyle = gf; ctx.fill();
  if (damp > 0) { ctx.fillStyle = 'rgba(50,32,10,' + (0.34 * damp).toFixed(2) + ')'; ctx.fill(); }   // damp floor after it drains
  // the two inner walls we can see: the back-left and back-right sides, from the rim down to the floor
  if (!openW) {
    wallQuad(col, row, col, row + 1); ctx.fillStyle = wall[0]; ctx.fill();
    if (damp > 0) { ctx.fillStyle = 'rgba(50,32,10,' + (0.22 * damp).toFixed(2) + ')'; ctx.fill(); }
  }
  if (!openN) {
    wallQuad(col, row, col + 1, row); ctx.fillStyle = wall[1]; ctx.fill();
    if (damp > 0) { ctx.fillStyle = 'rgba(50,32,10,' + (0.22 * damp).toFixed(2) + ')'; ctx.fill(); }
  }
  // shadow where the walls meet the floor
  ctx.strokeStyle = 'rgba(40,24,6,0.35)'; ctx.lineWidth = 1.5;
  const fl = iso(col, row + 1, -D), fc = iso(col, row, -D), fr = iso(col + 1, row, -D);
  ctx.beginPath();
  if (!openW) { ctx.moveTo(fl.x, fl.y); ctx.lineTo(fc.x, fc.y); } else ctx.moveTo(fc.x, fc.y);
  if (!openN) ctx.lineTo(fr.x, fr.y);
  ctx.stroke();
  // the water: a flat surface that climbs the walls with the level
  if (level > 0.01) {
    const zW = -D + Math.min(1, level) * (D - TRENCH_RIM_GAP);
    const cA = col - (openW ? 1 : 0), rA = row - (openN ? 1 : 0);     // runs on into a joined trench behind
    const gw = ctx.createLinearGradient(top.x, top.y, bot.x, bot.y);
    gw.addColorStop(0, c1); gw.addColorStop(1, c2);
    ctx.globalAlpha = a0 * (0.62 + 0.3 * Math.min(1, level));         // thin water shows the floor through it
    quad([[cA, rA], [col + 1, rA], [col + 1, row + 1], [cA, row + 1]], zW);
    ctx.fillStyle = gw; ctx.fill();
    ctx.globalAlpha = a0;
    // bright line where the surface meets the walls
    const wl = iso(col, row + 1, zW), wc = iso(col, row, zW), wr = iso(col + 1, row, zW);
    ctx.strokeStyle = 'rgba(235,250,255,0.75)'; ctx.lineWidth = 1.2;
    ctx.beginPath();
    if (!openW) { ctx.moveTo(wl.x, wl.y); ctx.lineTo(wc.x, wc.y); } else ctx.moveTo(wc.x, wc.y);
    if (!openN) ctx.lineTo(wr.x, wr.y);
    ctx.stroke();
    // two glints drifting on the surface
    ctx.strokeStyle = 'rgba(255,255,255,0.45)'; ctx.lineWidth = 1;
    for (let k = 0; k < 2; k++) {
      const u = 0.5 + 0.28 * Math.sin(tick * 0.021 + col * 1.7 + k * 2.4), v = 0.5 + 0.28 * Math.cos(tick * 0.017 + row * 2.3 + k * 1.3);
      const g1 = iso(col + u - 0.09, row + v + 0.09, zW), g2 = iso(col + u + 0.09, row + v - 0.09, zW);
      ctx.beginPath(); ctx.moveTo(g1.x, g1.y); ctx.lineTo(g2.x, g2.y); ctx.stroke();
    }
  }
  ctx.restore();
  ctx.globalAlpha = a0;
}

''' + src[b:]

# ── castle ring: same trench, each tile's level delayed by its distance from the sea-side corner ─
rep("""    ctx.save();
    clipTilePath(c,r); ctx.clip();
    ctx.fillStyle='#a8823f'; ctx.fill();                       // dry trench floor
    ctx.fillStyle='rgba(60,40,15,' + (0.24 + 0.22 * ringDamp).toFixed(2) + ')'; ctx.fill();   // darker while damp
    ctx.restore();
""", "")
rep("    drawPoolOnTile(c, r, tileCover, ringDepth, '#6fd0e2', '#3fa6c8');",
    "    drawTrenchOnTile(c, r, TRENCH_RING_DEPTH, ringDepth * tileCover, ringDamp, ['#b58c44','#8a6830'], ['#9a783a','#7e6030'], '#6fd0e2', '#3fa6c8');")

# ── placed moats ────────────────────────────────────────────────────────────────────────────────
rep("""      const gd = ctx.createLinearGradient(p.x,p.y,pb.x,pb.y);
      gd.addColorStop(0,dry[0]); gd.addColorStop(1,dry[1]);
      ctx.fillStyle=gd; ctx.beginPath();
      ctx.moveTo(p.x,p.y);ctx.lineTo(pr.x,pr.y);ctx.lineTo(pb.x,pb.y);ctx.lineTo(pf.x,pf.y);
      ctx.closePath();ctx.fill();
      if (mDamp > 0) { ctx.fillStyle = 'rgba(50,32,10,' + (0.3 * mDamp).toFixed(2) + ')'; ctx.fill(); }   // damp floor after it drains
      drawPoolOnTile(col, row, mCover, mDepth, c1, c2);
""",
"""      // sunken trench: the water level climbs the inner walls as it fills and drops as it dries (drawing only)
      drawTrenchOnTile(col, row, TRENCH_DEPTH[id], mDepth * mCover, mDamp, ['#c79c50','#96723a'], dry, c1, c2);
""")

assert "drawPoolOnTile" not in src
open(sys.argv[2], 'w', encoding='utf-8').write(src)
print('patched ->', sys.argv[2])
