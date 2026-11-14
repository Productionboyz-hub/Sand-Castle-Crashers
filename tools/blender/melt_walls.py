# melt_walls.py - the three placeable walls (small, medium, tall) as sprites that match the sprite castle.
#
#   blender -b --python-exit-code 1 -P melt_walls.py -- --out out
#
# Same sand, same lighting, same camera and the same melt method as the castle (crumble_castle.py): each wall is
# one mass of sand built from a height grid, sagging from the sea side into a low mound of wet sand.
# Writes into the output folder:
#   walls_melt.png / .json   one row per wall (small, medium, tall), one column per melt stage (default 8):
#                            column 0 = the whole wall, last column = a low mound. Pick the column by wall health.
#   frames/                  the individual frames
# Each frame is one tile plus room for the sand that runs out; the tile's back corner sits on the anchor.
# Everything is seeded, so the same command gives the same sprites.
import argparse
import os
import sys

import bpy  # noqa: F401
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_sprites as rs  # noqa: E402
import crumble_castle as cc  # noqa: E402

ZU = rs.ZU
MERLON = ((0.08, 0.08), (0.58, 0.08), (0.08, 0.58), (0.58, 0.58))   # even battlement rhythm when walls sit side by side
MERLON_W = 0.34


# The walls, in game units relative to the tile's back corner: (col0, col1, row0, row1, z1).
# Heights follow the game's walls: small 0.6, medium 1.1 + merlons to 1.38, tall 1.6 + merlons to 1.9.
def wall_blocks(kind):
    body, top = {'small': (0.6, 0.0), 'medium': (1.1, 1.38), 'tall': (1.6, 1.9)}[kind]
    b = [(0.0, 1.0, 0.0, 1.0, body)]
    if top:
        b += [(c, c + MERLON_W, r, r + MERLON_W, top) for c, r in MERLON]
    return b


WALLS = ('small', 'medium', 'tall')          # sheet rows, top to bottom
FULL_Z = {'small': 0.6, 'medium': 1.38, 'tall': 1.9}
LEAD = 0.5                                   # how far the sea side melts ahead of the back (0 = the whole wall sags evenly)
_LEVELS = {}


def wall_heightfield(kind, amount, seed, res=0.02):
    """Height of the melting wall at every grid point: (C, R, H, wet), like crumble_castle.melt_heightfield().
    amount 0 = the whole wall, 1 = a low mound of wet sand. Melts from the sea side (high col + row) first."""
    lo, hi = -1.4, 2.4
    n = int(round((hi - lo) / res)) + 1
    ax = np.linspace(lo, hi, n)
    C, R = np.meshgrid(ax, ax, indexing='ij')
    if kind not in _LEVELS:                                   # the wall from crisp to a puddle: worked out once
        H0 = np.zeros((n, n))
        for (c0, c1, r0, r1, z1) in wall_blocks(kind):
            inside = (C >= c0 - 1e-9) & (C <= c1 + 1e-9) & (R >= r0 - 1e-9) & (R <= r1 + 1e-9)
            H0[inside] = np.maximum(H0[inside], z1 * ZU)
        _LEVELS[kind] = [cc._blur(H0, s / res) for s in (0.02, 0.09, 0.20, 0.36)]
    levels = _LEVELS[kind]
    ph = seed * 0.37 + WALLS.index(kind) * 1.9                # each wall slumps a little differently
    wob = 0.16 * np.sin(5.1 * C + 0.6 + ph) * np.cos(3.9 * R + 2.1 - ph) + 0.10 * np.sin(9.3 * R - 3.6 * C + ph)
    d = np.clip((C + R + wob) / 2.0, 0.0, 1.0)                # 0 at the tile's back corner, 1 at its sea-side corner
    t = np.clip(amount * (1 + LEAD) - LEAD * (1 - d), 0.0, 1.0)   # the sea side leads, the back catches up by amount 1
    m = t * t * (3 - 2 * t)                                   # melt 0..1 at each point
    u = m * (len(levels) - 1)
    i0 = np.minimum(u.astype(int), len(levels) - 2)
    f = u - i0
    H = np.zeros_like(C)
    for i in range(len(levels) - 1):
        sel = i0 == i
        H[sel] = (levels[i] * (1 - f) + levels[i + 1] * f)[sel]
    H *= 1.0 - 0.40 * m                                       # wet sand packs down as it slumps
    H += 0.008 * m * np.sin(20.0 * C + 2.0 * np.sin(9.0 * R + ph)) * np.clip(H * 8, 0, 1)   # soft runnels
    H = np.maximum(0.0, H - 0.03 * m)                         # the apron ends in a soft lip
    H[H < 0.02] = 0.0
    wet = np.clip(0.15 + 0.95 * m, 0.0, 1.0)
    return C, R, H, wet


def top_height(kind, amount, seed, res=0.02):
    """Tallest point of the wall at this melt amount, in game z units."""
    return round(float(wall_heightfield(kind, amount, seed, res)[2].max()) / ZU, 2)


def main():
    ap = rs.add_args(argparse.ArgumentParser(description='The three walls and their melt, as one sprite sheet.'))
    ap.add_argument('--seed', type=int, default=7, help='random seed: same seed, same slump')
    ap.add_argument('--melt-stages', type=int, default=8, help='melt stages per wall, from whole wall to low mound')
    ap.add_argument('--save-blend', action='store_true', help='also save walls.blend (the whole tall wall) to open in Blender')
    # one tile, the tallest wall, and the sand that runs out; the tile's back corner sits at 64,62
    ap.set_defaults(frame_w=128, frame_h=112, anchor_x=64, anchor_y=62)
    cfg = ap.parse_args(rs.script_args())
    out = os.path.abspath(cfg.out)
    fdir = os.path.join(out, 'frames')
    os.makedirs(fdir, exist_ok=True)
    n = max(2, cfg.melt_stages)
    cfg.cols = n                                              # one row per wall
    amounts = [i / (n - 1) for i in range(n)]
    paths, names = [], []
    for kind in WALLS:
        for i, a in enumerate(amounts):
            scene = cc.fresh_scene(cfg)
            cc.add_heightfield(scene, *wall_heightfield(kind, a, cfg.seed))
            if cfg.save_blend and kind == 'tall' and i == 0:
                bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, 'walls.blend'))
            paths += rs.render_frames(scene, [1], fdir, 'wall_%s_%02d' % (kind, i))
            names.append('wall_%s_%02d' % (kind, i))
    rs.pack_sheet(paths, names, os.path.join(out, 'walls_melt.png'), os.path.join(out, 'walls_melt.json'), cfg,
                  extra={'kind': 'stages', 'footprint': {'cols': 1, 'rows': 1}, 'stages': n,
                         'amounts': [round(a, 4) for a in amounts],
                         # per wall: its sheet row and its tallest point at each stage (game z units)
                         'walls': [{'id': 'wall-' + k, 'row': r, 'z': [top_height(k, a, cfg.seed) for a in amounts]}
                                   for r, k in enumerate(WALLS)]})
    print('[melt_walls] done ->', out, flush=True)


if __name__ == '__main__':
    main()
