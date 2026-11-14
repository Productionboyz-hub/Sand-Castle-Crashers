#!/usr/bin/env python3
# Sand Castle Crashers - water v3 polish, applied ON TOP of patch_water3.py's output.
#   fix 1: phone water was blocky. Pattern scale followed the tile size, and on a phone a tile is ~7 px,
#          so ripples/caustics/glints shrank below one texel. Pattern scale now has a floor, and small
#          screens build the texture at 1/2 resolution instead of 1/3. Desktop is unchanged (its tile > floor).
#   fix 2: tile grid showing through the shallows (per-tile shore tint removed) - see below.
# usage: patch_water4.py <v3.html> <out.html>
import sys
src = open(sys.argv[1], encoding='utf-8').read()

def rep(old, new, count=1):
    global src
    assert src.count(old) == count, (src.count(old), old[:80])
    src = src.replace(old, new)

rep("const W_SCALE = 3;",
    "const W_SCALE = SW * SH < 600000 ? 2 : 3;   // small screens (phones) get a finer water texture\n"
    "const WATER_PATTERN_MIN_PX = 24;             // ← TUNE: ripples/glints never shrink below this tile size (phones have ~7 px tiles)")
rep("""function buildWaterTex(t) {
  const data = wImg.data;
  const th = TH();""",
"""function buildWaterTex(t) {
  const data = wImg.data;
  const th = Math.max(TH(), WATER_PATTERN_MIN_PX);   // pattern scale, floored so phones don't alias""")

# fix 2: the tile grid showed through the see-through shallows. Cause: every isShore() tile got its own
#        blue tint clipped to its diamond (fine under the old opaque water, a stair-step under the new
#        clear water). drawWetSand() now darkens the sand along the real water edge, so the tint goes.
rep("""      const wet = isShore(col,row);
      ctx.save();
      clipTilePath(col,row); ctx.clip();
      ctx.drawImage(sCanvas,0,0);
      if(wet){
        ctx.fillStyle='rgba(40,80,120,0.22)'; ctx.fill();
      }
      ctx.restore();""",
"""      // v0.9: no per-tile shore tint - it showed through the clear shallows as a diamond stair-step.
      // drawWetSand() darkens the sand along the real water edge instead.
      ctx.save();
      clipTilePath(col,row); ctx.clip();
      ctx.drawImage(sCanvas,0,0);
      ctx.restore();""")

open(sys.argv[2], 'w', encoding='utf-8').write(src)
print('patched ->', sys.argv[2])
