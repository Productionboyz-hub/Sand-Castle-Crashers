# crumble_castle.py - the crumble test: a procedural sandcastle that collapses, as game-ready sprites.
#
#   blender -b --python-exit-code 1 -P crumble_castle.py -- --out out
#
# Builds the castle from blocks on the game's own 4 x 4 tile footprint (same heights as drawCastle()),
# splits every block into chunks (scripted Voronoi split - no add-on needed), and lets rigid-body physics
# pull it down. Writes into the output folder:
#   castle_crumble.png / .json   the collapse animation (default 20 frames)
#   castle_states.png  / .json   3 stills: intact, cracked, half
#   frames/                      the individual frames
# Everything is seeded, so the same command gives the same sprites.
import argparse
import math
import os
import random
import sys

import bpy
import bmesh  # noqa: E402  (bmesh needs bpy loaded first when run outside Blender)
from mathutils import Euler, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_sprites as rs  # noqa: E402

ZU = rs.ZU

# The castle, in game units relative to its back corner: (col0, col1, row0, row1, z0, z1, chunks).
# Mirrors drawCastle(): 4x4 base to z 0.4, wall ring to 1.25, corner towers to 1.9 + merlons to 2.25,
# 2x2 keep to 1.4 with two turrets to 2.0.
def castle_blocks():
    b = [(0, 4, 0, 4, 0.0, 0.4, 30)]                                             # base slab
    b += [(1, 3, 0, 1, 0.4, 1.25, 9), (1, 3, 3, 4, 0.4, 1.25, 9),               # wall ring (between the towers)
          (0, 1, 1, 3, 0.4, 1.25, 9), (3, 4, 1, 3, 0.4, 1.25, 9)]
    for c, r in ((0, 0), (3, 0), (0, 3), (3, 3)):                                # corner towers + 4 merlons each
        b.append((c, c + 1, r, r + 1, 0.4, 1.9, 10))
        for dc, dr in ((0.04, 0.04), (0.62, 0.04), (0.04, 0.62), (0.62, 0.62)):
            b.append((c + dc, c + dc + 0.34, r + dr, r + dr + 0.34, 1.9, 2.25, 1))
    b.append((1, 3, 1, 3, 0.4, 1.4, 18))                                         # keep
    b += [(1.1, 1.9, 1.1, 1.9, 1.4, 2.0, 4), (2.1, 2.9, 2.1, 2.9, 1.4, 2.0, 4)]  # keep turrets
    return b


def sand_materials():
    """Slot 0 = sun-dried outer sand, slot 1 = darker damp sand on the broken faces."""
    def make(name, color, bump):
        mat = bpy.data.materials.new(name)
        if mat.node_tree is None:
            mat.use_nodes = True
        nt = mat.node_tree
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = 1.0
        spec = bsdf.inputs.get('Specular IOR Level') or bsdf.inputs.get('Specular')
        if spec:
            spec.default_value = 0.0
        noise = nt.nodes.new('ShaderNodeTexNoise')            # sand grain
        noise.inputs['Scale'].default_value = 90.0
        noise.inputs['Detail'].default_value = 6.0
        bmp = nt.nodes.new('ShaderNodeBump')
        bmp.inputs['Strength'].default_value = bump
        bmp.inputs['Distance'].default_value = 0.02
        nt.links.new(noise.outputs['Fac'], bmp.inputs['Height'])
        nt.links.new(bmp.outputs['Normal'], bsdf.inputs['Normal'])
        return mat
    return [make('SandDry', (0.80, 0.67, 0.46, 1.0), 0.35), make('SandDamp', (0.50, 0.38, 0.23, 1.0), 0.6)]


def voronoi_chunks(lo, hi, n, rng):
    """Split the box lo..hi into n convex chunks. Returns a list of (bmesh, centroid)."""
    seeds = [Vector([lo[i] + (0.08 + 0.84 * rng.random()) * (hi[i] - lo[i]) for i in range(3)]) for _ in range(n)]
    out = []
    for i, s in enumerate(seeds):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co = Vector([lo[k] + (v.co[k] + 0.5) * (hi[k] - lo[k]) for k in range(3)])
        for j, t in enumerate(seeds):
            if i == j:
                continue
            res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(s + t) / 2,
                                         plane_no=(t - s).normalized(), clear_outer=True, clear_inner=False)
            edges = [e for e in res['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]
            if edges:
                for f in bmesh.ops.edgeloop_fill(bm, edges=edges)['faces']:
                    f.material_index = 1                      # broken face: damp sand
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        if len(bm.faces) < 4:
            bm.free()
            continue
        c = sum((v.co for v in bm.verts), Vector()) / len(bm.verts)
        for v in bm.verts:
            v.co -= c                                         # origin at the centroid = centre of mass
        out.append((bm, c))
    return out


def build_castle(scene, seed):
    """Create every chunk as its own object. Returns the list of objects."""
    rng = random.Random(seed)
    mats = sand_materials()
    coll = bpy.data.collections.new('Castle')
    scene.collection.children.link(coll)
    chunks = []
    for (c0, c1, r0, r1, z0, z1, n) in castle_blocks():
        lo = Vector((c0, -r1, z0 * ZU))
        hi = Vector((c1, -r0, z1 * ZU))
        for bm, cen in voronoi_chunks(lo, hi, n, rng):
            me = bpy.data.meshes.new('chunk')
            vol = bm.calc_volume()
            bm.to_mesh(me)
            bm.free()
            for m in mats:
                me.materials.append(m)
            ob = bpy.data.objects.new('chunk', me)
            ob.location = cen
            ob['volume'] = vol
            coll.objects.link(ob)
            chunks.append(ob)
    return chunks


def add_physics(scene, chunks, cfg, is_active):
    """Rigid bodies: chunks for which is_active(ob) is true fall, the rest stay put. Bakes the simulation."""
    if scene.rigidbody_world is None:
        bpy.ops.rigidbody.world_add()
    rbw = scene.rigidbody_world
    rb_coll = bpy.data.collections.new('RigidBodies')
    rbw.collection = rb_coll
    rbw.time_scale = cfg.time_scale
    rbw.substeps_per_frame = 20
    rbw.solver_iterations = 30
    # ground: an invisible slab under the sand line
    me = bpy.data.meshes.new('ground')
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(me)
    bm.free()
    ground = bpy.data.objects.new('ground', me)
    ground.scale = (60, 60, 1)
    ground.location = (2, -2, -0.5)
    ground.hide_render = True
    scene.collection.objects.link(ground)
    rb_coll.objects.link(ground)
    ground.rigid_body.type = 'PASSIVE'
    ground.rigid_body.collision_shape = 'BOX'
    ground.rigid_body.friction = 0.9
    ground.rigid_body.restitution = 0.0
    rng = random.Random(cfg.seed + 1)
    for ob in chunks:
        rb_coll.objects.link(ob)
        rb = ob.rigid_body
        rb.collision_shape = 'CONVEX_HULL'
        rb.restitution = 0.0                                  # sand does not bounce
        rb.use_margin = True
        rb.collision_margin = 0.0
        rb.mass = max(0.02, ob['volume'] * 1.6)
        if is_active(ob):
            rb.type = 'ACTIVE'
            rb.friction = cfg.friction * (0.6 + 0.8 * rng.random())   # uneven grip: some chunks slide first
            rb.linear_damping = 0.05
            rb.angular_damping = 0.35
        else:
            rb.type = 'PASSIVE'
            rb.friction = 0.9
    # the push that starts it: a short outward shove from inside the base, like a wave hitting and the sand letting go
    if cfg.push > 0:
        bpy.ops.object.effector_add(type='FORCE', location=(2, -2, 0.25))
        ff = bpy.context.object
        ff.field.falloff_power = 1.0
        ff.field.strength = cfg.push
        ff.field.keyframe_insert('strength', frame=1)
        ff.field.keyframe_insert('strength', frame=cfg.push_frames)
        ff.field.strength = 0.0
        ff.field.keyframe_insert('strength', frame=cfg.push_frames + 2)
    scene.frame_start = 1
    scene.frame_end = cfg.sim_frames
    rbw.point_cache.frame_start = 1
    rbw.point_cache.frame_end = cfg.sim_frames
    with bpy.context.temp_override(scene=scene, point_cache=rbw.point_cache):
        bpy.ops.ptcache.bake(bake=True)


def fresh_scene(cfg):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 24
    rs.setup_render(scene, cfg)
    rs.setup_camera(scene, cfg)
    rs.setup_lighting(scene)
    return scene


def main():
    ap = rs.add_args(argparse.ArgumentParser(description='Sandcastle crumble test.'))
    ap.add_argument('--frames', type=int, default=20, help='frames in the crumble animation')
    ap.add_argument('--step', type=int, default=3, help='physics frames per rendered frame (bigger = faster collapse)')
    ap.add_argument('--seed', type=int, default=7, help='random seed: same seed, same chunks and same fall')
    ap.add_argument('--friction', type=float, default=0.3, help='chunk grip (lower = flows out more like dry sand)')
    ap.add_argument('--push', type=float, default=42.0, help='strength of the outward shove that starts the collapse')
    ap.add_argument('--push-frames', type=int, default=5, help='how many physics frames the shove lasts')
    ap.add_argument('--time-scale', type=float, default=1.0, help='physics speed')
    ap.add_argument('--only', default='all', choices=['all', 'crumble', 'states'], help='render just one part')
    ap.add_argument('--save-blend', action='store_true', help='also save crumble.blend so you can open the scene in Blender')
    # frame big enough for the 4x4 castle plus the rubble it throws out; the castle's back corner sits at 192,136
    ap.set_defaults(frame_w=384, frame_h=304, anchor_x=192, anchor_y=136, cols=5)
    cfg = ap.parse_args(rs.script_args())
    out = os.path.abspath(cfg.out)
    fdir = os.path.join(out, 'frames')
    os.makedirs(fdir, exist_ok=True)

    if cfg.only in ('all', 'crumble'):
        cfg.sim_frames = 1 + cfg.step * (cfg.frames - 1)
        scene = fresh_scene(cfg)
        chunks = build_castle(scene, cfg.seed)
        add_physics(scene, chunks, cfg, lambda ob: True)
        if cfg.save_blend:
            bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, 'crumble.blend'))
        frames = [1 + cfg.step * i for i in range(cfg.frames)]
        paths = rs.render_frames(scene, frames, fdir, 'crumble')
        rs.pack_sheet(paths, ['crumble_%02d' % i for i in range(len(paths))],
                      os.path.join(out, 'castle_crumble.png'), os.path.join(out, 'castle_crumble.json'), cfg,
                      extra={'kind': 'animation', 'footprint': {'cols': 4, 'rows': 4}, 'loop': False})

    if cfg.only in ('all', 'states'):
        paths = []
        # intact: every chunk exactly in place
        scene = fresh_scene(cfg)
        build_castle(scene, cfg.seed)
        paths += rs.render_frames(scene, [1], fdir, 'state_intact')
        # cracked: chunks shrink a little about their own centres (dark gaps open up) and the upper ones shift
        scene = fresh_scene(cfg)
        rng = random.Random(cfg.seed + 2)
        for ob in build_castle(scene, cfg.seed):
            h = ob.location.z / (2.25 * ZU)                   # 0 at the sand, 1 at the top
            ob.scale = (0.94, 0.94, 0.94)
            ob.rotation_euler = Euler([math.radians(rng.uniform(-5, 5)) * h for _ in range(3)])
            ob.location += Vector((rng.uniform(-0.03, 0.03) * h, rng.uniform(-0.03, 0.03) * h, -0.05 * h))
        paths += rs.render_frames(scene, [1], fdir, 'state_cracked')
        # half: the sea-facing half above the base falls and comes to rest; the rest stands
        cfg.sim_frames = 70
        scene = fresh_scene(cfg)
        chunks = build_castle(scene, cfg.seed)
        half_push = cfg.push
        cfg.push = cfg.push * 0.5
        add_physics(scene, chunks, cfg, lambda ob: ob.location.z > 0.42 * ZU and (ob.location.x - ob.location.y) > 4.0)
        cfg.push = half_push
        paths += rs.render_frames(scene, [cfg.sim_frames], fdir, 'state_half')
        rs.pack_sheet(paths, ['intact', 'cracked', 'half'],
                      os.path.join(out, 'castle_states.png'), os.path.join(out, 'castle_states.json'), cfg,
                      extra={'kind': 'states', 'footprint': {'cols': 4, 'rows': 4}})
    print('[crumble_castle] done ->', out, flush=True)


if __name__ == '__main__':
    main()
