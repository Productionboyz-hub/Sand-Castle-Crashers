# render_sprites.py - render any .blend to a game-ready sprite sheet for Sand Castle Crashers.
#
#   blender -b <file.blend> --python-exit-code 1 -P render_sprites.py -- --name tower --frames 1 20
#
# What it does:
#   1. adds an orthographic camera that matches the game's iso() projection exactly
#   2. transparent background, one fixed lighting rig (sun upper LEFT, cool sky fill - see CONTEXT.md)
#   3. renders the frames, packs them into one sprite sheet PNG, writes a JSON with frame rects + anchor
#
# The game's projection (sandcastle_iso2.html, iso()):
#   screen x = (col - row) * TW/2        TW = 56 px at zoom 1
#   screen y = (col + row) * TH/2 - z*TH TH = 28 px at zoom 1   (2:1)
# In Blender terms: 1 tile side = 1 unit, col = +X, row = -Y, orthographic camera rotated X 60 deg, Z 45 deg
# (looking down 30 deg from the horizon - NOT true isometric, which is 35.26 deg).
# One game z unit is 28 px, which is ZU = 0.8165 Blender units of height.
#
# Model convention: put the piece's BACK corner (the game's iso(col,row,0) anchor) at the world origin,
# and build it toward +X (col) and -Y (row).
#
# Only uses what ships inside Blender (bpy, mathutils, numpy). No extra installs.
import argparse
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Euler, Vector

TILE_W, TILE_H = 56, 28                              # game tile size in px at zoom 1
PPU = TILE_W / math.sqrt(2)                          # px per Blender unit across the screen at zoom 1 (39.6)
CAM_ROT = (math.radians(60), 0.0, math.radians(45))  # looks down 30 deg -> ground squashed 2:1
ZU = TILE_H / (PPU * math.cos(math.radians(30)))     # Blender height of one game z unit (0.8165)


def grid_to_world(col, row, z=0.0):
    """Game grid position (relative to the piece's anchor tile corner) -> Blender world position."""
    return Vector((col, -row, z * ZU))


def add_args(ap):
    ap.add_argument('--out', default='out', help='output folder')
    ap.add_argument('--name', default='sprite', help='base name of the sheet and JSON')
    ap.add_argument('--scale', type=float, default=2.0, help='render px per game px at zoom 1 (2 = tile 112 px wide)')
    ap.add_argument('--frame-w', type=int, default=320, help='frame width in game px at zoom 1')
    ap.add_argument('--frame-h', type=int, default=288, help='frame height in game px at zoom 1')
    ap.add_argument('--anchor-x', type=float, default=160, help='where the world origin lands in the frame, game px from the left')
    ap.add_argument('--anchor-y', type=float, default=128, help='... game px from the top')
    ap.add_argument('--samples', type=int, default=48, help='Cycles samples per pixel')
    ap.add_argument('--device', default='CPU', choices=['CPU', 'GPU'], help='Cycles device')
    ap.add_argument('--cols', type=int, default=0, help='sheet columns (0 = automatic)')
    return ap


def script_args():
    return sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def setup_render(scene, cfg):
    scene.render.engine = 'CYCLES'
    scene.cycles.device = cfg.device
    scene.cycles.samples = cfg.samples
    scene.cycles.use_denoising = True
    scene.render.film_transparent = True                     # transparent background
    scene.render.resolution_x = int(round(cfg.frame_w * cfg.scale))
    scene.render.resolution_y = int(round(cfg.frame_h * cfg.scale))
    scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x = scene.render.pixel_aspect_y = 1.0
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.view_settings.view_transform = 'Standard'          # colours come out as authored, no filmic curve
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0


def setup_camera(scene, cfg, origin=(0.0, 0.0, 0.0)):
    """Orthographic camera matching iso(). The world `origin` lands exactly on the frame's anchor pixel."""
    data = bpy.data.cameras.new('SpriteCam')
    data.type = 'ORTHO'
    data.sensor_fit = 'HORIZONTAL'
    data.ortho_scale = cfg.frame_w / PPU                     # frame width in Blender units
    data.clip_start, data.clip_end = 0.1, 500.0
    cam = bpy.data.objects.new('SpriteCam', data)
    scene.collection.objects.link(cam)
    rot = Euler(CAM_ROT, 'XYZ')
    m = rot.to_matrix()
    right, up, back = m @ Vector((1, 0, 0)), m @ Vector((0, 1, 0)), m @ Vector((0, 0, 1))
    dx = (cfg.frame_w / 2 - cfg.anchor_x) / PPU              # frame centre relative to the anchor, in units
    dy = -(cfg.frame_h / 2 - cfg.anchor_y) / PPU
    cam.rotation_euler = rot
    cam.location = Vector(origin) + right * dx + up * dy + back * 100.0
    scene.camera = cam
    return cam


def setup_lighting(scene, keep_existing=False):
    """One fixed rig for every sprite (CONTEXT.md): warm sun from the upper LEFT, cool sky fill in the shadows."""
    if not keep_existing:
        for ob in [o for o in scene.objects if o.type == 'LIGHT']:
            bpy.data.objects.remove(ob, do_unlink=True)
    sun_data = bpy.data.lights.new('SpriteSun', 'SUN')
    sun_data.energy = 2.1
    sun_data.color = (1.0, 0.94, 0.84)
    sun_data.angle = math.radians(6)                         # soft shadow edges
    sun = bpy.data.objects.new('SpriteSun', sun_data)
    scene.collection.objects.link(sun)
    travel = Vector((0.30, 0.72, -0.63)).normalized()        # light travels this way: lights the -Y (screen-left) faces
    sun.rotation_euler = travel.to_track_quat('-Z', 'Y').to_euler()
    world = bpy.data.worlds.new('SpriteWorld')
    scene.world = world
    if world.node_tree is None:
        world.use_nodes = True
    bg = next((n for n in world.node_tree.nodes if n.type == 'BACKGROUND'), None)
    if bg is None:
        bg = world.node_tree.nodes.new('ShaderNodeBackground')
        outn = world.node_tree.nodes.new('ShaderNodeOutputWorld')
        world.node_tree.links.new(bg.outputs['Background'], outn.inputs['Surface'])
    bg.inputs['Color'].default_value = (0.94, 0.94, 1.0, 1.0)   # sky bounce: shadowed faces go slightly blue
    bg.inputs['Strength'].default_value = 0.66
    return sun


def render_frames(scene, frames, out_dir, prefix):
    """Render the given frame numbers. Returns the PNG paths in order."""
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for i, f in enumerate(frames):
        scene.frame_set(f)
        path = os.path.join(out_dir, '%s_%03d.png' % (prefix, i))
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        paths.append(path)
        print('[render_sprites] frame %d/%d -> %s' % (i + 1, len(frames), path), flush=True)
    return paths


def _read_png(path):
    img = bpy.data.images.load(path, check_existing=False)
    img.colorspace_settings.name = 'Non-Color'               # pass the bytes straight through
    img.alpha_mode = 'STRAIGHT'
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)[::-1]                         # Blender stores rows bottom-up; flip to top-down


def pack_sheet(paths, names, out_png, out_json, cfg, extra=None):
    """Pack same-size frames into one sheet PNG and write the JSON the game loads."""
    frames = [_read_png(p) for p in paths]
    fh, fw = frames[0].shape[:2]
    n = len(frames)
    cols = min(cfg.cols, n) if cfg.cols > 0 else int(math.ceil(math.sqrt(n)))
    rows = int(math.ceil(n / cols))
    sheet = np.zeros((rows * fh, cols * fw, 4), dtype=np.float32)
    rects = []
    for i, fr in enumerate(frames):
        x, y = (i % cols) * fw, (i // cols) * fh
        sheet[y:y + fh, x:x + fw] = fr
        rects.append({'name': names[i], 'x': x, 'y': y, 'w': fw, 'h': fh})
    img = bpy.data.images.new('sheet', width=cols * fw, height=rows * fh, alpha=True)
    img.colorspace_settings.name = 'Non-Color'
    img.alpha_mode = 'STRAIGHT'
    img.pixels.foreach_set(sheet[::-1].ravel())
    img.filepath_raw = out_png
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    meta = {
        'image': os.path.basename(out_png),
        'scale': cfg.scale,                                  # sheet px per game px at zoom 1
        'frameW': fw, 'frameH': fh,
        'anchor': {'x': cfg.anchor_x * cfg.scale, 'y': cfg.anchor_y * cfg.scale},   # px inside a frame = the game's iso(col,row,0)
        'tile': {'w': TILE_W * cfg.scale, 'h': TILE_H * cfg.scale},
        'frames': rects,
    }
    if extra:
        meta.update(extra)
    with open(out_json, 'w', encoding='utf-8') as fjson:
        json.dump(meta, fjson, indent=2)
    print('[render_sprites] sheet %dx%d (%d frames) -> %s' % (cols * fw, rows * fh, n, out_png), flush=True)
    return meta


def main():
    ap = add_args(argparse.ArgumentParser(description='Render the open .blend to a sprite sheet.'))
    ap.add_argument('--frames', type=int, nargs=2, default=None, metavar=('FIRST', 'LAST'), help='frame range (default: the scene range)')
    ap.add_argument('--step', type=int, default=1, help='render every Nth frame')
    ap.add_argument('--keep-lights', action='store_true', help="keep the file's own lights as well as the standard rig")
    cfg = ap.parse_args(script_args())
    scene = bpy.context.scene
    setup_render(scene, cfg)
    setup_camera(scene, cfg)
    setup_lighting(scene, keep_existing=cfg.keep_lights)
    first, last = cfg.frames if cfg.frames else (scene.frame_start, scene.frame_end)
    frames = list(range(first, last + 1, cfg.step))
    out = os.path.abspath(cfg.out)
    paths = render_frames(scene, frames, os.path.join(out, 'frames'), cfg.name)
    names = ['%s_%02d' % (cfg.name, i) for i in range(len(paths))]
    pack_sheet(paths, names, os.path.join(out, cfg.name + '.png'), os.path.join(out, cfg.name + '.json'), cfg)


if __name__ == '__main__':
    main()
