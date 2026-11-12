#!/usr/bin/env python3
# Sand Castle Crashers - water v3: stronger pitch and fan-out, applied ON TOP of patch_water5.py's output.
#   - the see-saw pitch of the whole waterline is ~2.7x stronger (named knob SWASH_PITCH)
#   - waves land narrower and fan out to ~4-8x their landing width (was ~2-4.5x) (SWASH_FAN_MIN/MAX)
#   - sideways slosh is faster
# usage: patch_water6.py <v5.html> <out.html>
import sys
src = open(sys.argv[1], encoding='utf-8').read()

def rep(old, new, count=1):
    global src
    assert src.count(old) == count, (src.count(old), old[:80])
    src = src.replace(old, new)

rep("const BACKWASH_MIN    = 0.3;      // an incoming wave never drops below this fraction of its speed\n",
    "const BACKWASH_MIN    = 0.3;      // an incoming wave never drops below this fraction of its speed\n"
    "const SWASH_PITCH     = 1.6;      // see-saw: how far the waterline tips end to end (tile-heights; 0.6 = the old gentle rock)\n"
    "const SWASH_FAN_MIN   = 3;        // a wave ends at least this many times wider than it landed (plus 1)\n"
    "const SWASH_FAN_MAX   = 7;        // ...and at most this many\n")
rep("    dir, v: 2.5 + Math.random() * 5,                                    // sideways travel, px per (speed-1) tick",
    "    dir, v: 3.5 + Math.random() * 7.5,                                  // sideways travel, px per (speed-1) tick")
rep("    sig: SW * (0.07 + Math.random() * 0.12),                           // narrow where it lands...",
    "    sig: SW * (0.05 + Math.random() * 0.09),                           // narrow where it lands...")
rep("    fan: 1.2 + Math.random() * 2.3,                                     // ...and this many times wider by the time it is gone",
    "    fan: SWASH_FAN_MIN + Math.random() * (SWASH_FAN_MAX - SWASH_FAN_MIN), // ...and this many times wider by the time it is gone")
rep("  const tilt = Math.sin(tk * 0.021 + tiltPhase) * th * 0.6 * (noise2(tk * 0.003, 9.1) + 0.7);",
    "  const tilt = Math.sin(tk * 0.021 + tiltPhase) * th * SWASH_PITCH * (noise2(tk * 0.003, 9.1) + 0.7);")

open(sys.argv[2], 'w', encoding='utf-8').write(src)
print('patched ->', sys.argv[2])
