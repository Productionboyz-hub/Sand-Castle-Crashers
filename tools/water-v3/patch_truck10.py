#!/usr/bin/env python3
# Sand Castle Crashers - cleaner truck size, applied ON TOP of patch_water9.py's output.
# (Not water work: kept in this folder only so the branch file still rebuilds from main with one chain of scripts.)
#   - the truck was drawn in fixed pixels: it ignored zoom (tourists and crabs scale with camZoom) and was barely
#     longer than a tourist is tall. It now scales with camZoom like the enemies and is TRUCK_SCALE times bigger
#     (about 2.5 tourist-heights long).
#   - DRAWING ONLY: speed, pickup radius, coins and cooldown are untouched.
# usage: patch_truck10.py <v9.html> <out.html>
import sys
src = open(sys.argv[1], encoding='utf-8').read()

def rep(old, new, count=1):
    global src
    assert src.count(old) == count, (src.count(old), old[:80])
    src = src.replace(old, new)

rep("""function drawTruck() {
  if (!truck) return;
  const sp = iso(truck.col, truck.row, 0.02);
  const flip = truck.dirC < 0 ? -1 : 1;
  ctx.save();
  ctx.translate(sp.x, sp.y);
  ctx.scale(flip, 1);
  ctx.shadowColor = '#88aaff';
  ctx.shadowBlur = 6;
""",
"""const TRUCK_SCALE = 2;   // ← TUNE: truck size against a tourist (2 = about 2.5 tourist-heights long)
function drawTruck() {
  if (!truck) return;
  const sp = iso(truck.col, truck.row, 0.02);
  const flip = truck.dirC < 0 ? -1 : 1;
  const s = camZoom * 0.9 * TRUCK_SCALE;   // scales with zoom, same base factor as tourists and crabs
  ctx.save();
  ctx.translate(sp.x, sp.y);
  ctx.scale(flip * s, s);
  ctx.shadowColor = '#88aaff';
  ctx.shadowBlur = 6 * s;
""")

open(sys.argv[2], 'w', encoding='utf-8').write(src)
print('patched ->', sys.argv[2])
