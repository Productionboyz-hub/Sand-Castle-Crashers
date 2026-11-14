# crumble_castle.py - the crumble test: a procedural sandcastle that collapses, as game-ready sprites.
#
#   blender -b --python-exit-code 1 -P crumble_castle.py -- --out out
#
# Builds the castle from blocks on the game's own 4 x 4 tile footprint (same heights as drawCastle()),
# splits every block into chunks (scripted Voronoi split - no add-on needed), and lets rigid-body physics
# pull it down. To read as SAND rather than stone: once a chunk starts to move it rounds off, goes lumpy and
# shrinks away, while a mound of loose sand builds up underneath. Writes into the output folder:
#   castle_crumble.png / .json   the collapse animation (default 20 frames; frame 0 is the intact castle)
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
from mathutils import Euler, Vector, noise

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_sprites as rs  # noqa: E402

ZU = rs.ZU


# The castle, in game units relative to its back corner: (col0, col1, row0, row1, z0, z1, chunks).
# Mirrors drawCastle(): 4x4 base to z 0.4, wall ring to 1.25, corner towers to 1.9 + merlons to 2.25,
# 2x2 keep to 1.4 with two turrets to 2.0.
def castle_blocks():
    b = [(0, 4, 0, 4, 0.0, 0.4, 26)]                                             # base slab
    b += [(1, 3, 0, 1, 0.4, 1.25, 14), (1, 3, 3, 4, 0.4, 1.25, 14),             # wall ring (between the towers)
          (0, 1, 1, 3, 0.4, 1.25, 14), (3, 4, 1, 3, 0.4, 1.25, 14)]
    for c, r in ((0, 0), (3, 0), (0, 3), (3, 3)):                                # corner towers + 4 merlons each
        b.append((c, c + 1, r, r + 1, 0.4, 1.9, 16))
        for dc, dr in ((0.04, 0.04), (0.62, 0.04), (0.04, 0.62), (0.62, 0.62)):
            b.append((c + dc, c + dc + 0.34, r + dr, r + dr + 0.34, 1.9, 2.25, 1))
    b.append((1, 3, 1, 3, 0.4, 1.4, 26))                                         # keep
    b += [(1.1, 1.9, 1.1, 1.9, 1.4, 2.0, 6), (2.1, 2.9, 2.1, 2.9, 1.4, 2.0, 6)]  # keep turrets
    return b


def sand_material(name, color, bump):
    """Matt sand: a speckled colour (light and dark grains) and a fine grain bump."""
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Roughness'].default_value = 1.0
    spec = bsdf.inputs.get('Specular IOR Level') or bsdf.inputs.get('Specular')
    if spec:
        spec.default_value = 0.0
    grain = nt.nodes.new('ShaderNodeTexNoise')                # individual grains: about 2 px across at scale 2
    grain.inputs['Scale'].default_value = 34.0
    grain.inputs['Detail'].default_value = 8.0
    grain.inputs['Roughness'].default_value = 0.75
    patch = nt.nodes.new('ShaderNodeTexNoise')                # slow drift: damper and drier patches
    patch.inputs['Scale'].default_value = 2.2
    patch.inputs['Detail'].default_value = 2.0
    mix = nt.nodes.new('ShaderNodeMath')                      # value = 0.62 + 0.52*grain + 0.24*patch  (about 0.8 .. 1.2)
    mix.operation = 'MULTIPLY_ADD'
    mix.inputs[1].default_value = 0.52
    mix.inputs[2].default_value = 0.62
    mix2 = nt.nodes.new('ShaderNodeMath')
    mix2.operation = 'MULTIPLY_ADD'
    mix2.inputs[1].default_value = 0.24
    hsv = nt.nodes.new('ShaderNodeHueSaturation')
    hsv.inputs['Color'].default_value = color
    nt.links.new(grain.outputs['Fac'], mix.inputs[0])
    nt.links.new(patch.outputs['Fac'], mix2.inputs[0])
    nt.links.new(mix.outputs['Value'], mix2.inputs[2])
    nt.links.new(mix2.outputs['Value'], hsv.inputs['Value'])
    nt.links.new(hsv.outputs['Color'], bsdf.inputs['Base Color'])
    bmp = nt.nodes.new('ShaderNodeBump')
    bmp.inputs['Strength'].default_value = bump
    bmp.inputs['Distance'].default_value = 0.03
    nt.links.new(grain.outputs['Fac'], bmp.inputs['Height'])
    nt.links.new(bmp.outputs['Normal'], bsdf.inputs['Normal'])
    return mat


def sand_materials():
    """Slot 0 = sun-dried outer sand, slot 1 = darker damp sand on the broken faces."""
    return [sand_material('SandDry', (0.80, 0.67, 0.46, 1.0), 0.45), sand_material('SandDamp', (0.60, 0.47, 0.29, 1.0), 0.8)]


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


def build_castle(scene, seed, fractured=True):
    """Create every chunk as its own object (fractured=False: one object per block). Returns the objects."""
    rng = random.Random(seed)
    mats = sand_materials()
    lump_tex = bpy.data.textures.new('Lump', 'CLOUDS')
    lump_tex.noise_scale = 0.16
    coll = bpy.data.collections.new('Castle')
    scene.collection.children.link(coll)
    chunks = []
    for (c0, c1, r0, r1, z0, z1, n) in castle_blocks():
        lo = Vector((c0, -r1, z0 * ZU))
        hi = Vector((c1, -r0, z1 * ZU))
        for bm, cen in voronoi_chunks(lo, hi, n if fractured else 1, rng):
            me = bpy.data.meshes.new('chunk')
            vol = bm.calc_volume()
            bm.to_mesh(me)
            bm.free()
            for m in mats:
                me.materials.append(m)
            me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
            ob = bpy.data.objects.new('chunk', me)
            ob.location = cen
            ob['volume'] = vol
            coll.objects.link(ob)
            # soft, patted-down edges (no hard outlines), and the handles the crumble animates
            bev = ob.modifiers.new('SoftEdge', 'BEVEL')
            bev.width = 0.035
            bev.segments = 2
            bev.limit_method = 'ANGLE'
            bev.angle_limit = math.radians(25)
            sub = ob.modifiers.new('Subdiv', 'SUBSURF')
            sub.subdivision_type = 'SIMPLE'
            sub.levels = sub.render_levels = 2 if fractured else 0
            rnd = ob.modifiers.new('Round', 'SMOOTH')          # 0 = crisp block, 1 = rounded clump
            rnd.factor = 0.0
            rnd.iterations = 30
            lmp = ob.modifiers.new('Lump', 'DISPLACE')         # 0 = flat faces, more = lumpy
            lmp.texture = lump_tex
            lmp.texture_coords = 'LOCAL'
            lmp.mid_level = 0.5
            lmp.strength = 0.0
            wn = ob.modifiers.new('Normals', 'WEIGHTED_NORMAL')  # flat faces stay flat, only the edges are rounded
            wn.keep_sharp = False
            chunks.append(ob)
    return chunks


def add_mound(scene, center, radius, height, seed, clumps=16):
    """A heap of loose sand: a smooth, slightly uneven cone. Returns the object (origin on the sand at its centre)."""
    rings, segs = 48, 120
    bm = bmesh.new()
    off = Vector((seed * 3.7, seed * 1.3, 0.0))
    rng = random.Random(seed + 9)
    humps = []                                                # clumps that did not break up: (x, y, radius, height)
    for _ in range(clumps):
        a, t = rng.uniform(0, 2 * math.pi), 0.12 + 0.6 * rng.random() ** 0.8
        humps.append((math.cos(a) * radius * t, math.sin(a) * radius * t, rng.uniform(0.26, 0.45), rng.uniform(0.03, 0.08)))
    top = bm.verts.new((0, 0, height))
    prev = None
    for i in range(1, rings + 1):
        t = i / rings
        ring = []
        for j in range(segs):
            a = 2 * math.pi * j / segs
            d = Vector((math.cos(a), math.sin(a), 0.0))
            wob = 1.0 + 0.16 * noise.noise(d * 1.4 + off)      # uneven outline
            p = d * (radius * wob * t)
            h = height * (0.5 * (1 + math.cos(math.pi * t))) ** 0.85          # steep in the middle, feathering out to nothing
            h *= 1.0 + 0.22 * noise.noise(Vector((p.x, p.y, 0.0)) * 1.1 + off)  # slumps and shoulders
            h += 0.035 * (1 - t) ** 0.5 * noise.noise(Vector((p.x, p.y, 0.0)) * 4.0 + off)
            for hx, hy, hr, hh in humps:
                d2 = ((p.x - hx) ** 2 + (p.y - hy) ** 2) / (hr * hr)
                if d2 < 4.0:
                    h += hh * math.exp(-2.2 * d2)
            ring.append(bm.verts.new((p.x, p.y, max(0.0, h) if i < rings else 0.0)))
        for j in range(segs):
            k = (j + 1) % segs
            if prev is None:
                bm.faces.new((top, ring[j], ring[k]))
            else:
                bm.faces.new((prev[j], ring[j], ring[k], prev[k]))
        prev = ring
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new('mound')
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    me.materials.append(sand_material('SandLoose', (0.74, 0.60, 0.39, 1.0), 0.9))
    ob = bpy.data.objects.new('mound', me)
    ob.location = (center[0], center[1], 0.0)
    scene.collection.objects.link(ob)
    return ob


def grow_mound(mound, first, last):
    """The heap starts flat and hidden under the castle, then rises and spreads as sand lands on it."""
    for f, sxy, sz in ((1, 0.5, 0.0), (first, 0.5, 0.0), (first + 0.45 * (last - first), 0.86, 0.62), (last, 1.0, 1.0)):
        mound.scale = (sxy, sxy, sz)
        mound.keyframe_insert('scale', frame=f)


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


def crumble_to_sand(scene, chunks, cfg, last):
    """Sand, not stone: from the moment a chunk starts to move it rounds off, goes lumpy and shrinks.
    and away to nothing, so what is left at the end is the heap of loose sand, never a pile of blocks.
    Only the look changes - the physics was baked with the full-size chunks."""
    rng = random.Random(cfg.seed + 3)
    start = {}
    home = {}
    for f in range(1, last + 1):                              # when does each chunk first move?
        scene.frame_set(f)
        for ob in chunks:
            p = ob.matrix_world.translation.copy()
            if f == 1:
                home[ob.name] = p
            elif ob.name not in start and (p - home[ob.name]).length > 0.04:
                start[ob.name] = f
    late = int(1 + 0.12 * last)                               # chunks that never move slump as the heap covers them
    for ob in chunks:
        t0 = start.get(ob.name, late + rng.randint(0, max(1, int(0.2 * last))))
        span = int(cfg.melt_frames * (0.7 + 0.6 * rng.random()))
        for mod, prop, v1 in (('Round', 'factor', 1.0), ('Lump', 'strength', 0.07)):
            m = ob.modifiers[mod]
            setattr(m, prop, 0.0)
            m.keyframe_insert(prop, frame=t0)
            setattr(m, prop, v1)
            m.keyframe_insert(prop, frame=t0 + max(3, span // 2))
        ob.scale = (1, 1, 1)
        ob.keyframe_insert('scale', frame=t0 + 1)
        ob.scale = (0.001,) * 3
        ob.keyframe_insert('scale', frame=t0 + 1 + span)
    scene.frame_set(1)


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
    ap.add_argument('--step', type=int, default=2, help='physics frames per rendered frame (bigger = faster collapse)')
    ap.add_argument('--seed', type=int, default=7, help='random seed: same seed, same chunks and same fall')
    ap.add_argument('--friction', type=float, default=0.3, help='chunk grip (lower = flows out more like dry sand)')
    ap.add_argument('--push', type=float, default=34.0, help='strength of the outward shove that starts the collapse')
    ap.add_argument('--push-frames', type=int, default=5, help='how many physics frames the shove lasts')
    ap.add_argument('--time-scale', type=float, default=0.8, help='physics speed')
    ap.add_argument('--melt-frames', type=int, default=20, help='physics frames a moving chunk takes to crumble away to sand')
    ap.add_argument('--clumps', type=int, default=16, help='number of damp clumps left on the heap (0 = smooth heap)')
    ap.add_argument('--mound-height', type=float, default=1.1, help='height of the final sand heap, in game z units')
    ap.add_argument('--mound-radius', type=float, default=2.9, help='radius of the final sand heap, in tiles')
    ap.add_argument('--only', default='all', choices=['all', 'crumble', 'states'], help='render just one part')
    ap.add_argument('--save-blend', action='store_true', help='also save crumble.blend so you can open the scene in Blender')
    # frame big enough for the 4x4 castle plus the sand it throws out; the castle's back corner sits at 192,136
    ap.set_defaults(frame_w=384, frame_h=304, anchor_x=192, anchor_y=136, cols=5)
    cfg = ap.parse_args(rs.script_args())
    out = os.path.abspath(cfg.out)
    fdir = os.path.join(out, 'frames')
    os.makedirs(fdir, exist_ok=True)

    # intact: whole blocks, nothing broken. Also frame 0 of the crumble, so the animation starts from the same picture.
    scene = fresh_scene(cfg)
    build_castle(scene, cfg.seed, fractured=False)
    intact = rs.render_frames(scene, [1], fdir, 'state_intact')

    if cfg.only in ('all', 'crumble'):
        cfg.sim_frames = 1 + cfg.step * (cfg.frames - 1)
        scene = fresh_scene(cfg)
        chunks = build_castle(scene, cfg.seed)
        add_physics(scene, chunks, cfg, lambda ob: True)
        crumble_to_sand(scene, chunks, cfg, cfg.sim_frames)
        mound = add_mound(scene, (2, -2), cfg.mound_radius, cfg.mound_height * ZU, cfg.seed, cfg.clumps)
        grow_mound(mound, 4, int(0.9 * cfg.sim_frames))
        if cfg.save_blend:
            bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, 'crumble.blend'))
        frames = [1 + cfg.step * i for i in range(1, cfg.frames)]
        paths = intact + rs.render_frames(scene, frames, fdir, 'crumble')
        rs.pack_sheet(paths, ['crumble_%02d' % i for i in range(len(paths))],
                      os.path.join(out, 'castle_crumble.png'), os.path.join(out, 'castle_crumble.json'), cfg,
                      extra={'kind': 'animation', 'footprint': {'cols': 4, 'rows': 4}, 'loop': False})

    if cfg.only in ('all', 'states'):
        paths = list(intact)
        # cracked: chunks shrink a little about their own centres (dark gaps open up) and the upper ones shift
        scene = fresh_scene(cfg)
        rng = random.Random(cfg.seed + 2)
        for ob in build_castle(scene, cfg.seed):
            h = ob.location.z / (2.25 * ZU)                   # 0 at the sand, 1 at the top
            ob.scale = (0.95, 0.95, 0.95)
            ob.rotation_euler = Euler([math.radians(rng.uniform(-5, 5)) * h for _ in range(3)])
            ob.location += Vector((rng.uniform(-0.03, 0.03) * h, rng.uniform(-0.03, 0.03) * h, -0.05 * h))
            ob.modifiers['Round'].factor = 0.25 * h           # the top is already starting to slump
        paths += rs.render_frames(scene, [1], fdir, 'state_cracked')
        # half: the sea-facing half above the base falls, crumbles and comes to rest as a heap; the rest stands
        cfg.sim_frames = 70
        scene = fresh_scene(cfg)
        chunks = build_castle(scene, cfg.seed)
        falls = lambda ob: ob.location.z > 0.42 * ZU and (ob.location.x - ob.location.y) > 4.0   # noqa: E731
        fallen = [ob for ob in chunks if falls(ob)]
        full_push = cfg.push
        cfg.push = full_push * 0.5
        add_physics(scene, chunks, cfg, falls)
        cfg.push = full_push
        crumble_to_sand(scene, fallen, cfg, cfg.sim_frames - 24)
        for ob in chunks:                                     # what still stands has slumped: softer, a little lumpy
            if ob not in fallen:
                ob.modifiers['Subdiv'].levels = ob.modifiers['Subdiv'].render_levels = 3
                ob.modifiers['Round'].factor = 1.0
                ob.modifiers['Lump'].strength = 0.07
        mound = add_mound(scene, (2.9, -2.9), 2.1, 0.95 * ZU, cfg.seed + 5, cfg.clumps // 2)
        grow_mound(mound, 4, cfg.sim_frames - 8)
        paths += rs.render_frames(scene, [cfg.sim_frames], fdir, 'state_half')
        rs.pack_sheet(paths, ['intact', 'cracked', 'half'],
                      os.path.join(out, 'castle_states.png'), os.path.join(out, 'castle_states.json'), cfg,
                      extra={'kind': 'states', 'footprint': {'cols': 4, 'rows': 4}})
    print('[crumble_castle] done ->', out, flush=True)


if __name__ == '__main__':
    main()
