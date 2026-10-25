#!/usr/bin/env python3
"""Scoop Sky room set pieces (2026-10-25, w5-set): trees, bushes, lawn flowers, wafer fence, cookie stone.

One data-driven kit: every piece = one builder function (geometry in metres, Blender Z up, front = -Y = glTF +Z)
+ part materials whose colours come ONLY from SWATCH_BOXES (pixel boxes on the approved plate / object sheets).
Pipeline per piece: build parts -> join -> fit to the size in PIECES -> UV -> Cycles bakes (part-id, albedo, AO,
tangent normal from the procedural bump) -> albedo = swatch x zero-mean variation x mild AO, each part's exposed
texel mean pinned to its swatch -> one material (albedo + optional normal) -> GLB (WebP).

Modes
  python3 tool/room_setpieces_build.py --swatches            # PIL: measure SWATCH_BOXES -> JSON on stdout (runner)
  python3 tool/room_setpieces_build.py --meta                # parts / pieces / sizes as JSON (runner)
  blender -b --factory-startup -P tool/room_setpieces_build.py -- job.json           # build + export
  blender -b --factory-startup -P tool/room_setpieces_build.py -- job.json --check   # fresh re-import checks + renders
Runner: pipeline/room-setpieces.sh. Another world reuses this file with new SWATCH_BOXES / PIECES rows.
"""
import json
import math
import sys
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLATE = 'out/shorts/ep01/anchors/world-theme-s1/A-scoop-sky/'
SHEET = 'out/shorts/ep01/anchors/s1-objects/'

# Single source of every set-piece colour: (image, lit-side pixel box). Order = part id order (do not reorder).
SWATCH_BOXES = {
    'canopy-pink': (PLATE + 'plate-v4.png', (14, 330, 60, 375)),
    'canopy-mint': (PLATE + 'plate-v4.png', (1600, 235, 1640, 275)),
    'flower-white': (PLATE + 'plate-v4.png', (160, 690, 172, 700)),
    'flower-centre': (PLATE + 'r6-flowerbed-v1.png', (1534, 596, 1548, 608)),
    'trunk-light': (PLATE + 'r7-side-v1.png', (1420, 380, 1436, 393)),
    'trunk-dark': (PLATE + 'r7-side-v1.png', (1400, 360, 1405, 366)),
    'leaf': (PLATE + 'r6-flowerbed-v1.png', (1395, 738, 1415, 752)),
    'leaf-dark': (PLATE + 'r6-flowerbed-v1.png', (1440, 770, 1460, 785)),
    'strawberry': (PLATE + 'r6-flowerbed-v1.png', (1560, 705, 1590, 735)),
    'blueberry': (PLATE + 'r6-flowerbed-v1.png', (1335, 742, 1355, 760)),
    'wafer': (SHEET + 'wafer-fence/turn/front.png', (56, 330, 72, 350)),
    'wafer-stripe': (SHEET + 'wafer-fence/turn/front.png', (95, 285, 108, 298)),
    'rail-pink': (SHEET + 'wafer-fence/turn/front.png', (135, 295, 155, 310)),
    'cap-pink': (SHEET + 'wafer-fence/turn/front.png', (415, 233, 450, 245)),
    'cookie': (SHEET + 'cookie-stone/turn/front.png', (290, 230, 320, 260)),
    'cookie-hole': (SHEET + 'cookie-stone/turn/front.png', (252, 243, 262, 251)),
    'lawn-light': (PLATE + 'plate-v4.png', (330, 685, 380, 705)),
    'lawn-mid': (PLATE + 'plate-v4.png', (600, 860, 700, 920)),
    'bush-mint': (PLATE + 'r7-side-v1.png', (300, 460, 330, 485)),
    'bush-green': (PLATE + 'plate-v4.png', (1450, 550, 1480, 575)),
}
PARTS = list(SWATCH_BOXES)

# size = glTF (x width, y height, z depth) in metres; height is exact, x/z are design targets (reported).
# fit: 'uniform' scales the whole piece to the height; 'z' scales height only (fence/cookie keep exact x/z by construction).
PIECES = {
    'tree-pink': dict(size=(2.8, 4.0, 2.2), tex=1024, normal=True, rough=0.85, ao=(0.5, 0.45), fit='uniform', budget=(15000, 1_000_000),
                      ref=(PLATE + 'r7-side-v1.png', (1150, 0, 1672, 540))),
    'tree-mint': dict(size=(2.6, 3.6, 2.0), tex=1024, normal=True, rough=0.85, ao=(0.5, 0.45), fit='uniform', budget=(15000, 1_000_000),
                      ref=(PLATE + 'plate-v4.png', (1440, 160, 1672, 640))),
    'berry-bush': dict(clamp=True, size=(1.5, 0.55, 1.0), tex=512, normal=True, rough=0.4, ao=(0.25, 0.5), fit='uniform', budget=(8000, 600_000),
                       ref=(PLATE + 'r6-flowerbed-v1.png', (1180, 540, 1672, 800))),
    'berry-bush-s': dict(clamp=True, size=(0.8, 0.38, 0.6), tex=512, normal=True, rough=0.4, ao=(0.2, 0.5), fit='uniform', budget=(8000, 600_000),
                         ref=(PLATE + 'plate-v4.png', (520, 600, 760, 700))),
    'daisy': dict(size=(0.16, 0.30, 0.16), tex=512, normal=False, rough=0.6, ao=(0.08, 0.3), fit='uniform', budget=(5000, 400_000),
                  ref=(PLATE + 'plate-v4.png', (90, 660, 250, 770))),
    'grass-tuft': dict(clamp=True, size=(0.40, 0.20, 0.40), tex=512, normal=False, rough=0.9, ao=(0.08, 0.4), fit='uniform', budget=(400, 120_000),
                       ref=(PLATE + 'plate-v4.png', (300, 680, 500, 760))),
    'mint-bush': dict(clamp=True, size=(1.3, 1.1, 1.3), tex=512, normal=True, rough=0.8, ao=(0.3, 0.5), fit='uniform', budget=(5000, 400_000),
                      ref=(PLATE + 'r7-side-v1.png', (270, 420, 420, 520))),
    'fence': dict(size=(1.0, 0.70, 0.07), tex=1024, normal=True, rough=0.7, ao=(0.12, 0.35), fit='z', budget=(5000, 400_000),
                  ref=(SHEET + 'wafer-fence/turn/front.png', (0, 0, 512, 512))),
    'fence-post': dict(size=(0.156, 0.80, 0.156), tex=512, normal=True, rough=0.7, ao=(0.08, 0.3), fit='z', budget=(5000, 400_000),
                       ref=(SHEET + 'wafer-fence/turn/front.png', (370, 200, 490, 490))),
    'cookie-stone': dict(size=(0.84, 0.08, 0.84), tex=512, normal=True, rough=0.75, ao=(0.05, 0.25), fit='z', budget=(5000, 400_000),
                         ref=(SHEET + 'cookie-stone/turn/front.png', (0, 0, 512, 512))),
}
ORDER = list(PIECES)
LIGHTS = {'sky': '#cfe8ff', 'ground': '#ffe6cc', 'hemi': 1.4, 'key': '#fff4e6', 'key_i': 1.2, 'dir': (-5, 9, 6), 'ref_normal': (0, 0.45, 0.9)}
EXPOSED_AO = 0.7   # texels with baked AO >= this are "lit side" (what the plate box measures)


def swatches_pil():
    from PIL import Image
    out = {}
    for k, (src, box) in SWATCH_BOXES.items():
        im = Image.open(REPO / src).convert('RGB').crop(box)
        px = im.tobytes()
        n = len(px) // 3
        m = [round(sum(px[i::3]) / n, 1) for i in range(3)]
        out[k] = {'src': src, 'box': list(box), 'srgb': m, 'hex': '#%02x%02x%02x' % tuple(round(v) for v in m)}
    return out


if __name__ == '__main__' and '--swatches' in sys.argv:
    print(json.dumps(swatches_pil(), indent=1))
    sys.exit(0)
if __name__ == '__main__' and '--meta' in sys.argv:   # plain-python view of the kit data for the runner
    print(json.dumps({'parts': PARTS, 'order': ORDER, 'exposed_ao': EXPOSED_AO, 'pieces': PIECES}))
    sys.exit(0)

# ---------------------------------------------------------------- Blender side
import bpy            # noqa: E402
import bmesh          # noqa: E402
import numpy as np    # noqa: E402
from mathutils import Vector, Matrix, Quaternion, noise  # noqa: E402
import random         # noqa: E402

ARGV = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
JOB = json.loads(Path(ARGV[0]).read_text()) if ARGV else {}
CHECK = '--check' in ARGV


def s2l(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def l2s(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055) * 255.0


def hex_lin(h):
    return [float(v) for v in s2l(np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], float))]


SW = {k: [float(v) for v in s2l(np.array(v['srgb'], float))] for k, v in JOB.get('swatches', {}).items()}


def mixc(a, b, t):
    return [SW[a][i] * (1 - t) + SW[b][i] * t for i in range(3)]


def idval(part):
    return (PARTS.index(part) + 1) / 32.0


# ---------------------------------------------------------------- scene helpers
def fresh():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.render.threads_mode = 'FIXED'
    sc.render.threads = int(JOB.get('threads', 3))
    sc.cycles.seed = 0
    w = bpy.data.worlds.new('w')
    sc.world = w
    return sc


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def mk(name, verts, faces, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate()
    me.update()
    me.polygons.foreach_set('use_smooth', [smooth] * len(me.polygons))
    return link(bpy.data.objects.new(name, me))


def from_bm(name, bm, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set('use_smooth', [smooth] * len(me.polygons))
    return link(bpy.data.objects.new(name, me))


def ellipsoid(segs, rings):
    """unit sphere: rings latitude bands, segs around; returns verts, faces"""
    vs = [(0, 0, -1)]
    for r in range(1, rings):
        ph = -math.pi / 2 + math.pi * r / rings
        for s in range(segs):
            th = 2 * math.pi * s / segs
            vs.append((math.cos(ph) * math.cos(th), math.cos(ph) * math.sin(th), math.sin(ph)))
    vs.append((0, 0, 1))
    fs, top = [], len(vs) - 1
    for s in range(segs):
        fs.append((0, 1 + (s + 1) % segs, 1 + s))
    for r in range(rings - 2):
        a, b = 1 + r * segs, 1 + (r + 1) * segs
        for s in range(segs):
            fs.append((a + s, a + (s + 1) % segs, b + (s + 1) % segs, b + s))
    a = 1 + (rings - 2) * segs
    for s in range(segs):
        fs.append((a + s, a + (s + 1) % segs, top))
    return [Vector(v) for v in vs], fs


def lathe(profile, segs, rfn=None):
    """profile [(r, z)] bottom->top; r == 0 at an end makes a pole. rfn(theta, z) -> radius factor."""
    vs, fs, rings = [], [], []
    for (r, z) in profile:
        if r <= 1e-9:
            vs.append(Vector((0, 0, z)))
            rings.append(('pole', len(vs) - 1))
        else:
            st = len(vs)
            for s in range(segs):
                th = 2 * math.pi * s / segs
                k = rfn(th, z) if rfn else 1.0
                vs.append(Vector((r * k * math.cos(th), r * k * math.sin(th), z)))
            rings.append(('ring', st))
    for (ka, a), (kb, b) in zip(rings, rings[1:]):
        for s in range(segs):
            s1 = (s + 1) % segs
            if ka == 'ring' and kb == 'ring':
                fs.append((a + s, a + s1, b + s1, b + s))
            elif ka == 'pole':
                fs.append((a, b + s1, b + s))
            elif kb == 'pole':
                fs.append((a + s, a + s1, b))
    return vs, fs


class Acc:
    """accumulate many small meshes into one object per material key"""
    def __init__(self):
        self.d = {}

    def add(self, key, verts, faces, M=None):
        vs, fs = self.d.setdefault(key, ([], []))
        o = len(vs)
        vs.extend([(M @ Vector(v)) if M is not None else Vector(v) for v in verts])
        fs.extend([tuple(i + o for i in f) for f in faces])

    def objects(self, smooth=True):
        return [(mk(k, vs, fs, smooth), k) for k, (vs, fs) in self.d.items()]


def frame(n, spin=0.0):
    """rotation taking +Z to n, spun about n"""
    q = Vector(n).normalized().to_track_quat('Z', 'Y')
    return q.to_matrix().to_4x4() @ Matrix.Rotation(spin, 4, 'Z')


# ---------------------------------------------------------------- shared geometry pieces
def floret_disp(p, R, cell, amp):
    d, _ = noise.voronoi(p / cell, distance_metric='DISTANCE')
    f = min(1.0, (d[1] - d[0]) * 2.2) ** 0.6
    return R * amp * (f - 0.5) + R * 0.035 * noise.noise(p * 1.7)


def fluff_balls(acc, balls, cell, amp, tris_per_ball, subdiv=4, ground_clip=False):
    """balls: [(centre Vector, R, matkey)]; displaced icospheres, faces hidden inside neighbours culled, decimated"""
    objs = []
    for i, (c, R, key) in enumerate(balls):
        others = [(oc, orr) for j, (oc, orr, _) in enumerate(balls) if j != i]
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
        for v in bm.verts:
            n = v.co.normalized()
            v.co = c + n * (R + floret_disp(c + n * R, R, cell, amp))
            if ground_clip and v.co.z < 0:
                v.co.z = 0.0
        kill = [f for f in bm.faces if all(any((v.co - oc).length < orr * 0.9 for oc, orr in others) for v in f.verts)]
        bmesh.ops.delete(bm, geom=kill, context='FACES')
        ob = from_bm(f'ball{i}', bm)
        n = len(ob.data.polygons)
        if n > tris_per_ball:
            m = ob.modifiers.new('dec', 'DECIMATE')
            m.ratio = tris_per_ball / n
            m.use_collapse_triangulate = True
            apply_mods(ob)
        objs.append((ob, key))
    return objs


def ball_surface(c, R, n, cell, amp):
    return c + n * (R + floret_disp(c + n * R, R, cell, amp))


def flower(acc, p, n, D, spin, petal_key='petal', centre_key='centre', petal_res=(6, 3), centre_res=(8, 4), petals=5, cup=0.22):
    F = Matrix.Translation(p) @ frame(n, spin)
    pv, pf = ellipsoid(*petal_res)
    for i in range(petals):
        a = 2 * math.pi * i / petals
        M = (F @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Translation((0.27 * D, 0, 0.02 * D)) @ Matrix.Rotation(-cup, 4, 'Y')
             @ Matrix.Diagonal((0.25 * D, 0.16 * D, 0.06 * D, 1)))
        acc.add(petal_key, pv, pf, M)
    cv, cf = ellipsoid(*centre_res)
    acc.add(centre_key, cv, cf, F @ Matrix.Translation((0, 0, 0.06 * D)) @ Matrix.Diagonal((0.15 * D, 0.15 * D, 0.08 * D, 1)))


def leaf_mesh(L, W, fold=0.35, curl=0.2):
    vs, fs = [], []
    S, T = 5, 3
    for i in range(S + 1):
        s = i / S
        w = W * (math.sin(math.pi * min(1, s * 1.05)) ** 0.75) * (1 - 0.25 * s) + 1e-4
        for j in range(T):
            t = -1 + 2 * j / (T - 1)
            vs.append(Vector((s * L, t * w / 2, abs(t) * w * fold - curl * L * s * s)))
    for i in range(S):
        for j in range(T - 1):
            a = i * T + j
            fs.append((a, a + 1, a + T + 1, a + T))
    return vs, fs


def apply_mods(ob):
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


# ---------------------------------------------------------------- materials (procedural, colours from SW only)
class NB:
    def __init__(self, mat):
        self.nt = mat.node_tree
        self.N, self.L = self.nt.nodes, self.nt.links
        for n in list(self.N):
            self.N.remove(n)
        self.obj = self.add('ShaderNodeTexCoord').outputs['Object']

    def add(self, t, **kw):
        n = self.N.new(t)
        for k, v in kw.items():
            setattr(n, k, v)
        return n

    def put(self, sock, v):
        if isinstance(v, bpy.types.NodeSocket):
            self.L.new(v, sock)
        elif isinstance(v, (list, tuple)):
            sock.default_value = tuple(v) + ((1.0,) if len(v) == 3 and len(sock.default_value) == 4 else ())
        else:
            sock.default_value = v

    def m(self, op, a, b=0.0, c=0.0, clamp=False):
        n = self.add('ShaderNodeMath', operation=op, use_clamp=clamp)
        self.put(n.inputs[0], a)
        self.put(n.inputs[1], b)
        self.put(n.inputs[2], c)
        return n.outputs[0]

    def xyz(self, v=None):
        n = self.add('ShaderNodeSeparateXYZ')
        self.L.new(v or self.obj, n.inputs[0])
        return n.outputs[0], n.outputs[1], n.outputs[2]

    def noise(self, scale, detail=2.0, rough=0.5, dist=0.0, v=None):
        n = self.add('ShaderNodeTexNoise')
        self.L.new(v or self.obj, n.inputs['Vector'])
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = rough
        n.inputs['Distortion'].default_value = dist
        return n.outputs['Fac']

    def voronoi(self, scale, feature='F1', rand=1.0, v=None):
        n = self.add('ShaderNodeTexVoronoi', feature=feature)
        self.L.new(v or self.obj, n.inputs['Vector'])
        n.inputs['Scale'].default_value = scale
        n.inputs['Randomness'].default_value = rand
        return n.outputs['Distance']

    def dist_to(self, p):
        n = self.add('ShaderNodeVectorMath', operation='DISTANCE')
        self.L.new(self.obj, n.inputs[0])
        n.inputs[1].default_value = p
        return n.outputs['Value']

    def mix(self, fac, a, b):
        n = self.add('ShaderNodeMix', data_type='RGBA')
        ins = [s for s in n.inputs if s.type in ('VALUE', 'RGBA') and s.enabled]
        self.put(ins[0], fac)
        self.put(ins[1], a)
        self.put(ins[2], b)
        return next(s for s in n.outputs if s.type == 'RGBA')

    def scale(self, col, f):
        n = self.add('ShaderNodeVectorMath', operation='SCALE')
        self.put(n.inputs[0], col)
        self.put(n.inputs['Scale'], f)
        return n.outputs['Vector']

    def var(self, col, amp, scale=6.0, detail=3.0):
        """zero-mean multiplicative variation"""
        return self.scale(col, self.m('MULTIPLY_ADD', self.noise(scale, detail), 2 * amp, 1 - amp))

    def step(self, x, edge):
        return self.m('GREATER_THAN', x, edge)


class Layered:
    """colour = base part with overlays; id = same overlays thresholded; detail overlays keep the parent id"""
    def __init__(self, nb, base, col=None):
        self.nb, self.col = nb, col if col is not None else SW[base]
        self.id = idval(base)

    def over(self, mask, col, part=None):
        self.col = self.nb.mix(mask, self.col, col)
        if part:
            self.id = self.nb.mix(self.nb.step(mask, 0.5), (self.id,) * 3 if isinstance(self.id, float) else self.id, (idval(part),) * 3)
        return self


def material(name, fn, rough):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nb = NB(mat)
    col, ident, h, bump = fn(nb)
    out = nb.add('ShaderNodeOutputMaterial')
    bsdf = nb.add('ShaderNodeBsdfPrincipled')
    nb.put(bsdf.inputs['Base Color'], col)
    bsdf.inputs['Roughness'].default_value = rough
    if h is not None:
        b = nb.add('ShaderNodeBump')
        b.inputs['Strength'].default_value = bump[0]
        b.inputs['Distance'].default_value = bump[1]
        nb.L.new(h, b.inputs['Height'])
        nb.L.new(b.outputs['Normal'], bsdf.inputs['Normal'])
    e_col = nb.add('ShaderNodeEmission')
    nb.put(e_col.inputs['Color'], col)
    e_id = nb.add('ShaderNodeEmission')
    nb.put(e_id.inputs['Color'], (ident,) * 3 if isinstance(ident, float) else ident)
    mat['sg'] = {'bsdf': bsdf.name, 'col': e_col.name, 'id': e_id.name, 'out': out.name}
    nb.L.new(bsdf.outputs[0], out.inputs['Surface'])
    return mat


def surface(mat, which):
    nt = mat.node_tree
    sg = mat['sg']
    src = nt.nodes[sg[which]]
    nt.links.new(src.outputs[0], nt.nodes[sg['out']].inputs['Surface'])


# material recipes: fn(nb) -> (colour, id, height or None, (bump strength, distance))
def m_fluff(part, cell=16.0, fib=70.0):
    def fn(nb):
        cells = nb.m('SUBTRACT', 1.0, nb.m('MULTIPLY', nb.voronoi(cell, 'SMOOTH_F1'), 1.5), clamp=True)
        fibres = nb.noise(fib, 8.0, 0.65, 0.9)
        h = nb.m('MULTIPLY_ADD', cells, 0.6, nb.m('MULTIPLY', fibres, 0.4))
        col = nb.scale(nb.var(SW[part], 0.05, 3.0), nb.m('MULTIPLY_ADD', h, 0.22, 0.89))
        return col, idval(part), h, (0.9, 0.02)
    return fn


def m_plain(part, amp=0.04, bumpscale=None, col=None):
    def fn(nb):
        c = nb.var(col or SW[part], amp, 8.0)
        h = nb.noise(bumpscale, 4.0, 0.6) if bumpscale else None
        return c, idval(part), h, (0.25, 0.01)
    return fn


def m_centre(nb):
    dots = nb.m('SUBTRACT', 1.0, nb.m('MULTIPLY', nb.voronoi(140.0), 2.5), clamp=True)
    c = nb.scale(nb.var(SW['flower-centre'], 0.04), nb.m('MULTIPLY_ADD', dots, 0.12, 0.94))
    return c, idval('flower-centre'), dots, (0.5, 0.005)


TWIST = 1.6


def m_trunk(nb):
    x, y, z = nb.xyz()
    th = nb.m('ARCTAN2', y, x)
    lobe = nb.m('ABSOLUTE', nb.m('COSINE', nb.m('MULTIPLY', nb.m('SUBTRACT', th, nb.m('MULTIPLY', z, TWIST)), 1.5)))
    u = nb.m('MULTIPLY', th, 1 / (2 * math.pi))
    a = nb.m('FRACT', nb.m('MULTIPLY_ADD', u, 12.0, nb.m('MULTIPLY', z, 8.0)))
    b = nb.m('FRACT', nb.m('MULTIPLY_ADD', u, 12.0, nb.m('MULTIPLY', z, -8.0)))
    da = nb.m('ABSOLUTE', nb.m('SUBTRACT', a, 0.5))
    db = nb.m('ABSOLUTE', nb.m('SUBTRACT', b, 0.5))
    groove = nb.m('SMOOTH_MAX', nb.m('GREATER_THAN', da, 0.43), nb.m('GREATER_THAN', db, 0.43), 0.0)
    crev = nb.m('LESS_THAN', lobe, 0.2)
    dark = nb.m('MAXIMUM', groove, crev)
    dots = nb.m('MULTIPLY', nb.m('LESS_THAN', nb.voronoi(26.0), 0.11), nb.m('GREATER_THAN', lobe, 0.55))
    L = Layered(nb, 'trunk-light', nb.var(SW['trunk-light'], 0.05, 9.0))
    L.over(dark, SW['trunk-dark'], 'trunk-dark')
    L.over(dots, mixc('flower-white', 'trunk-light', 0.15))
    h = nb.m('SUBTRACT', nb.m('POWER', lobe, 0.5), nb.m('MULTIPLY', groove, 0.25))
    return L.col, L.id, h, (0.8, 0.03)


def m_wafer(cyl=False, stripe=True):
    """flat pickets: pattern in (x, z) metres; cylinder: angle as a fraction of a turn x integer counts (seamless)"""
    def fn(nb):
        x, y, z = nb.xyz()
        if cyl:
            t = nb.m('MULTIPLY', nb.m('ARCTAN2', y, x), 1 / (2 * math.pi))
            a = nb.m('FRACT', nb.m('MULTIPLY_ADD', t, 4.0, nb.m('MULTIPLY', z, 10.0)))
            b = nb.m('FRACT', nb.m('MULTIPLY_ADD', t, 4.0, nb.m('MULTIPLY', z, -10.0)))
            sarg = nb.m('MULTIPLY_ADD', t, 2.0, nb.m('MULTIPLY', z, 2.6))
        else:
            a = nb.m('FRACT', nb.m('MULTIPLY', nb.m('ADD', x, z), 10.0))
            b = nb.m('FRACT', nb.m('MULTIPLY', nb.m('SUBTRACT', x, z), 10.0))
            sarg = nb.m('MULTIPLY', nb.m('ADD', nb.m('MULTIPLY', x, 0.85), nb.m('MULTIPLY', z, 0.55)), 3.8)
        g = nb.m('MAXIMUM', nb.m('ABSOLUTE', nb.m('SUBTRACT', a, 0.5)), nb.m('ABSOLUTE', nb.m('SUBTRACT', b, 0.5)))
        groove = nb.m('SMOOTH_MAX', nb.m('MULTIPLY', nb.m('SUBTRACT', g, 0.40), 10.0), 0.0, 0.02)
        L = Layered(nb, 'wafer', nb.var(SW['wafer'], 0.04, 9.0))
        if stripe:
            s = nb.m('FRACT', sarg)
            L.over(nb.m('LESS_THAN', s, 0.36), SW['wafer-stripe'], 'wafer-stripe')
        L.over(nb.m('MULTIPLY', groove, 0.5), mixc('wafer', 'trunk-light', 0.45))
        h = nb.m('SUBTRACT', 1.0, nb.m('MINIMUM', groove, 1.0))
        return L.col, L.id, h, (0.6, 0.006)
    return fn


def m_rail(nb):
    x, y, z = nb.xyz()
    a = nb.m('FRACT', nb.m('MULTIPLY', nb.m('ADD', x, z), 14.0))
    b = nb.m('FRACT', nb.m('MULTIPLY', nb.m('SUBTRACT', x, z), 14.0))
    g = nb.m('MAXIMUM', nb.m('ABSOLUTE', nb.m('SUBTRACT', a, 0.5)), nb.m('ABSOLUTE', nb.m('SUBTRACT', b, 0.5)))
    groove = nb.m('GREATER_THAN', g, 0.42)
    c = nb.var(SW['rail-pink'], 0.04, 9.0)
    return c, idval('rail-pink'), nb.m('SUBTRACT', 1.0, groove), (0.35, 0.004)


COOKIE_HOLES = [(0, .56), (-.39, .34), (.40, .34), (0, .09), (-.6, -.03), (.58, -.03), (-.26, -.31), (.27, -.31), (0, -.6)]
COOKIE_R, COOKIE_T = 0.42, 0.08


def m_cookie(nb):
    d = None
    for hx, hy in COOKIE_HOLES:
        di = nb.dist_to((hx * COOKIE_R * 0.92, hy * COOKIE_R * 0.92, COOKIE_T))
        d = di if d is None else nb.m('MINIMUM', d, di)
    hole = nb.m('LESS_THAN', d, 0.017)
    dimple = nb.m('SUBTRACT', 1.0, nb.m('DIVIDE', d, 0.04), clamp=True)
    pores = nb.noise(90.0, 6.0, 0.6)
    x, y, z = nb.xyz()
    rim = nb.m('SMOOTH_MAX', 0.0, nb.m('SUBTRACT', nb.m('SQRT', nb.m('ADD', nb.m('MULTIPLY', x, x), nb.m('MULTIPLY', y, y))), 0.3), 0.0)
    L = Layered(nb, 'cookie', nb.scale(nb.var(SW['cookie'], 0.04, 7.0), nb.m('MULTIPLY_ADD', rim, -0.6, 1.0)))
    L.over(nb.m('MULTIPLY', dimple, 0.6), mixc('cookie', 'cookie-hole', 0.35))
    L.over(hole, SW['cookie-hole'], 'cookie-hole')
    h = nb.m('SUBTRACT', nb.m('MULTIPLY', pores, 0.25), nb.m('POWER', dimple, 1.5))
    return L.col, L.id, h, (0.7, 0.01)


def m_strawberry(nb):
    dseed = nb.voronoi(58.0)
    seed = nb.m('LESS_THAN', dseed, 0.17)
    L = Layered(nb, 'strawberry', nb.var(SW['strawberry'], 0.05, 10.0))
    L.over(seed, mixc('flower-white', 'flower-centre', 0.35))
    h = nb.m('SUBTRACT', 0.0, nb.m('SUBTRACT', 1.0, nb.m('DIVIDE', dseed, 0.32), clamp=True))
    return L.col, L.id, h, (0.6, 0.004)


def m_grass(nb):
    x, y, z = nb.xyz()
    t = nb.m('POWER', nb.m('DIVIDE', z, 0.2, clamp=True), 0.8)
    L = Layered(nb, 'lawn-mid', nb.var(SW['lawn-mid'], 0.05, 20.0))
    L.over(t, nb.var(SW['lawn-light'], 0.05, 20.0))
    L.id = nb.mix(nb.step(t, 0.5), (idval('lawn-mid'),) * 3, (idval('lawn-light'),) * 3)
    return L.col, L.id, None, (0, 0)


# ---------------------------------------------------------------- piece builders: return [(obj, matkey)], {matkey: (fn, rough)}
def b_tree(rng, mint_major):
    s = 1.0
    if not mint_major:
        balls = [((0.0, 0.05, 3.22), 0.80, 'pink'), ((-0.78, 0.1, 2.72), 0.64, 'pink'), ((0.74, -0.05, 2.78), 0.68, 'pink'),
                 ((-0.22, -0.48, 2.36), 0.6, 'pink'), ((0.42, 0.42, 2.3), 0.56, 'pink'), ((-0.86, -0.22, 2.32), 0.5, 'mint'),
                 ((0.66, 0.38, 3.42), 0.52, 'mint')]
    else:
        balls = [((0.05, 0.0, 3.0), 0.66, 'mint'), ((-0.62, 0.05, 2.55), 0.62, 'mint'), ((0.66, -0.1, 2.5), 0.6, 'pink'),
                 ((0.1, -0.5, 2.25), 0.52, 'mint'), ((-0.25, 0.45, 2.35), 0.55, 'mint'), ((-0.45, -0.25, 3.15), 0.42, 'pink')]
    balls = [(Vector(c), R, k) for c, R, k in balls]
    cell, amp = 0.26, 0.15
    acc = Acc()
    objs = fluff_balls(acc, balls, cell, amp, 1300)
    # flowers on the canopy surface, front/sides biased, never inside a neighbour
    fl, tries = [], 0
    nwant = 14 if not mint_major else 12
    while len(fl) < nwant and tries < 4000:
        tries += 1
        c, R, _ = balls[rng.randrange(len(balls))]
        n = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))).normalized()
        if n.y > 0.45 or n.z < -0.35:
            continue
        p = ball_surface(c, R, n, cell, amp)
        if any((p - oc).length < orr * 1.05 for oc, orr, _ in balls if oc is not c):
            continue
        if any((p - q).length < 0.42 for q in fl):
            continue
        fl.append(p)
        flower(acc, p - n * 0.03, n, 0.27 * s, rng.uniform(0, 6.28))
    # twisted waffle trunk with a root flare + two branches into the canopy
    top = min(c.z for c, _, _ in balls) + 0.35 * s
    prof = [(0.0, 0.0), (0.36, 0.0), (0.33, 0.06), (0.27, 0.18), (0.23, 0.35)]
    nz = 22
    for i in range(1, nz + 1):
        z = 0.35 + (top - 0.35) * i / nz
        prof.append((0.21 - 0.07 * i / nz, z))
    prof = prof + [(0.0, top)]

    def rfn(th, z):
        return 0.86 + 0.2 * abs(math.cos(1.5 * (th - TWIST * z))) ** 0.6
    tv, tf = lathe(prof, 30, rfn)
    acc.add('trunk', tv, tf)
    for sx in (-1, 1):
        bv, bf = lathe([(0.0, 0.0), (0.1 * s, 0.0), (0.085 * s, 0.4), (0.06 * s, 0.8), (0.0, 0.85)], 10, rfn)
        M = Matrix.Translation((0.05 * sx, 0, top - 0.75 * s)) @ Matrix.Rotation(0.75 * sx, 4, 'Y') @ Matrix.Diagonal((1, 1, s, 1))
        acc.add('trunk', bv, bf, M)
    objs += acc.objects()
    mats = {'pink': m_fluff('canopy-pink'), 'mint': m_fluff('canopy-mint'), 'petal': m_plain('flower-white', 0.03),
            'centre': m_centre, 'trunk': m_trunk}
    return objs, mats


def b_berry_bush(rng, small):
    A, B, C = (0.72, 0.48, 0.5) if not small else (0.38, 0.28, 0.34)
    k = 1.0 if not small else 0.62
    acc = Acc()
    mv, mf = ellipsoid(14, 7)
    mv = [Vector((v.x * A * 0.9, v.y * B * 0.9, max(0.0, v.z) * C * 0.88)) for v in mv]
    mv = [v + v.normalized() * 0.03 * noise.noise(v * 4) if v.length > 0 else v for v in mv]
    acc.add('mound', mv, mf)

    def surf(rng, zmin=0.06):
        while True:
            n = Vector((rng.gauss(0, 1), rng.gauss(0, 1), abs(rng.gauss(0, 1)) + 0.15)).normalized()
            p = Vector((n.x * A, n.y * B, n.z * C))
            if p.z >= zmin * k:
                g = Vector((p.x / A ** 2, p.y / B ** 2, p.z / C ** 2)).normalized()
                return p, g
    lv, lf = leaf_mesh(0.17 * k, 0.12 * k)
    for _ in range(150 if not small else 60):
        p, g = surf(rng)
        t = g.cross(Vector((0, 0, 1)))
        if t.length < 1e-3:
            t = Vector((1, 0, 0))
        M = Matrix.Translation(p - g * 0.05 * k) @ frame(g, rng.uniform(0, 6.28)) @ Matrix.Rotation(rng.uniform(-0.5, 0.2), 4, 'Y')
        acc.add('leaf', lv, lf, M)
    sv, sf = lathe([(0.0, 0.0), (0.3, 0.1), (0.58, 0.28), (0.78, 0.52), (0.8, 0.74), (0.62, 0.92), (0.28, 1.0), (0.0, 1.0)], 10)
    cal_v = [Vector((0, 0, 0))] + [Vector((math.cos(a) * (0.5 if i % 2 else 1.0), math.sin(a) * (0.5 if i % 2 else 1.0), 0.15 * (i % 2)))
                                   for i, a in enumerate([2 * math.pi * j / 10 for j in range(10)])]
    cal_f = [(0, 1 + j, 1 + (j + 1) % 10) for j in range(10)]
    placed = []

    def free(p, r):
        return all((p - q).length > r + rr for q, rr in placed)
    ns = (7, 10, 5) if not small else (3, 5, 2)
    H = 0.17 * k
    for _ in range(ns[0]):
        for _t in range(200):
            p, g = surf(rng, 0.25)
            if free(p, H * 0.6):
                break
        placed.append((p, H * 0.55))
        axis = (g * 0.55 + Vector((0, 0, -1)) * 0.6).normalized()
        topc = p + g * 0.04 * k - axis * H * 0.15
        M = Matrix.Translation(topc) @ frame(-axis, rng.uniform(0, 6.28)) @ Matrix.Translation((0, 0, -H)) @ Matrix.Diagonal((0.08 * k, 0.08 * k, H, 1))
        acc.add('berry', sv, sf, M)
        acc.add('calyx', cal_v, cal_f, Matrix.Translation(topc + (-axis) * 0.005) @ frame(-axis, 0.3) @ Matrix.Diagonal((0.07 * k, 0.07 * k, 0.05 * k, 1)))
    bv, bf = ellipsoid(10, 6)
    star = [Vector((0, 0, 0))] + [Vector((math.cos(2 * math.pi * j / 10) * (1 if j % 2 else 0.55), math.sin(2 * math.pi * j / 10) * (1 if j % 2 else 0.55), 0.0)) for j in range(10)]
    star_f = [(0, 1 + j, 1 + (j + 1) % 10) for j in range(10)]
    r = 0.048 * k
    for _ in range(ns[1]):
        for _t in range(200):
            p, g = surf(rng, 0.1)
            if free(p, r):
                break
        placed.append((p, r))
        c = p + g * r * 0.5
        acc.add('blue', bv, bf, Matrix.Translation(c) @ frame(g) @ Matrix.Diagonal((r, r, r * 0.92, 1)))
        acc.add('crown', star, star_f, Matrix.Translation(c + g * r * 0.93) @ frame(g, rng.uniform(0, 6)) @ Matrix.Diagonal((r * 0.38, r * 0.38, 1, 1)))
    for _ in range(ns[2]):
        for _t in range(200):
            p, g = surf(rng, 0.3)
            if free(p, 0.08 * k):
                break
        placed.append((p, 0.08 * k))
        n = (g + Vector((0, -0.3, 0.6))).normalized()
        flower(acc, p + g * 0.03 * k, n, 0.16 * k, rng.uniform(0, 6.28))
    objs = acc.objects()
    mats = {'mound': m_plain('leaf-dark', 0.05, 30.0), 'leaf': m_plain('leaf', 0.06, 25.0), 'berry': m_strawberry,
            'calyx': m_plain('leaf', 0.03), 'blue': m_plain('blueberry', 0.05, 40.0),
            'crown': m_plain('blueberry', 0.0, None, col=[v * 0.45 for v in SW['blueberry']]),
            'petal': m_plain('flower-white', 0.03), 'centre': m_centre}
    return objs, mats


def b_daisy(rng):
    acc = Acc()
    head = Vector((0.0, -0.03, 0.255))
    n = Vector((0, -math.sin(math.radians(35)), math.cos(math.radians(35))))
    pts = [Vector((0, 0.0, 0.0)), Vector((0, 0.005, 0.09)), Vector((0, -0.005, 0.18)), head - n * 0.015]
    sv, sf = [], []
    seg = 6
    for i, p in enumerate(pts):
        r = 0.009 - 0.002 * i / 3
        for s in range(seg):
            a = 2 * math.pi * s / seg
            sv.append(p + Vector((math.cos(a) * r, math.sin(a) * r, 0)))
    for i in range(len(pts) - 1):
        for s in range(seg):
            a, b = i * seg + s, i * seg + (s + 1) % seg
            sf.append((a, b, b + seg, a + seg))
    acc.add('stem', sv, sf)
    lv, lf = leaf_mesh(0.10, 0.045, 0.3, 0.25)
    for ang, tilt in ((0.5, -0.6), (3.6, -0.7)):
        acc.add('stem', lv, lf, Matrix.Translation((0, 0, 0.012)) @ Matrix.Rotation(ang, 4, 'Z') @ Matrix.Rotation(tilt, 4, 'Y'))
    flower(acc, head, n, 0.15, 0.3, petal_res=(8, 4), centre_res=(10, 5), cup=0.18)
    mats = {'stem': m_plain('leaf', 0.04), 'petal': m_plain('flower-white', 0.03), 'centre': m_centre}
    return acc.objects(), mats


def b_grass(rng):
    acc = Acc()
    bv, bf = ellipsoid(8, 3)
    bv = [Vector((v.x * 0.15, v.y * 0.15, max(0.0, v.z) * 0.05)) for v in bv]
    acc.add('grass', bv, bf)
    for i in range(34):
        r = 0.16 * math.sqrt(rng.random())
        a = rng.uniform(0, 6.283)
        base = Vector((r * math.cos(a), r * math.sin(a), 0.0))
        h = rng.uniform(0.12, 0.2) * (1 - 0.3 * r / 0.16)
        lean = Vector((math.cos(a), math.sin(a), 0)) * (0.02 + 0.2 * r) + Vector((rng.uniform(-.02, .02), rng.uniform(-.02, .02), 0))
        w = rng.uniform(0.014, 0.022)
        vs, fs = [], []
        for k, (t, rr) in enumerate(((0.0, w), (0.55, w * 0.65))):
            c = base + lean * (t * t) + Vector((0, 0, h * t))
            for s in range(3):
                b = a + 2 * math.pi * s / 3
                vs.append(c + Vector((math.cos(b) * rr, math.sin(b) * rr, 0)))
        vs.append(base + lean + Vector((0, 0, h)))
        for s in range(3):
            fs.append((s, (s + 1) % 3, 3 + (s + 1) % 3, 3 + s))
            fs.append((3 + s, 3 + (s + 1) % 3, 6))
        acc.add('grass', vs, fs)
    return acc.objects(), {'grass': m_grass}


def b_mint_bush(rng):
    acc = Acc()
    balls = [((0.0, 0.05, 0.72), 0.42, 'mint'), ((-0.33, -0.18, 0.4), 0.36, 'green'), ((0.34, -0.15, 0.42), 0.36, 'mint'),
             ((-0.28, 0.3, 0.42), 0.36, 'mint'), ((0.3, 0.32, 0.38), 0.34, 'green'), ((0.0, -0.4, 0.26), 0.28, 'green'),
             ((0.02, 0.05, 0.3), 0.3, 'mint')]
    balls = [(Vector(c), R, k) for c, R, k in balls]
    objs = fluff_balls(acc, balls, 0.15, 0.2, 640, subdiv=4, ground_clip=True)
    mats = {'mint': m_fluff('bush-mint', 22.0, 50.0), 'green': m_fluff('bush-green', 22.0, 50.0)}
    return objs, mats


def picket(x, w=0.2, h=0.70, t=0.06):
    bm = bmesh.new()
    sh = h - 0.115
    outline = [(-w / 2, 0), (w / 2, 0), (w / 2, sh), (0.035, h - 0.012), (0.0, h), (-0.035, h - 0.012), (-w / 2, sh)]
    vs = [bm.verts.new((x + px, -t / 2, pz)) for px, pz in outline]
    f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    for v in [e for e in r['geom'] if isinstance(e, bmesh.types.BMVert)]:
        v.co.y += t
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.012, segments=2, profile=0.5, affect='EDGES', clamp_overlap=True)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    return bm


def b_fence(rng):
    objs = []
    for i, x in enumerate((-1 / 3, 0.0, 1 / 3)):
        objs.append((from_bm(f'picket{i}', picket(x), smooth=True), 'wafer'))
    for i, zc in enumerate((0.17, 0.43)):
        bm = bmesh.new()
        r = bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co = Vector((v.co.x * 1.0, v.co.y * 0.04, zc + v.co.z * 0.085))
        long_edges = [e for e in bm.edges if abs(e.verts[0].co.x - e.verts[1].co.x) > 0.5]
        bmesh.ops.bevel(bm, geom=long_edges, offset=0.01, segments=2, profile=0.5, affect='EDGES', clamp_overlap=True)
        objs.append((from_bm(f'rail{i}', bm), 'rail'))
    return objs, {'wafer': m_wafer(), 'rail': m_rail}


def b_post(rng):
    acc = Acc()
    R = 0.07
    bv, bf = lathe([(0.0, 0.0), (R - 0.008, 0.0), (R, 0.008), (R, 0.74), (0.0, 0.74)], 24)
    acc.add('body', bv, bf)
    cv, cf = lathe([(0.0, 0.73), (0.077, 0.73), (0.078, 0.745), (0.078, 0.785), (0.07, 0.797), (0.05, 0.8), (0.0, 0.8)], 24)
    acc.add('cap', cv, cf)
    return acc.objects(), {'body': m_wafer(cyl=True), 'cap': m_plain('cap-pink', 0.03, 40.0)}


def b_cookie(rng):
    R, T, segs = COOKIE_R, COOKIE_T, 160
    rho = 0.03
    prof = []
    for i in range(9):
        ph = -math.pi / 2 + math.pi * i / 8
        sgn = 1 if math.sin(ph) >= 0 else -1
        prof.append((rho * (abs(math.cos(ph)) ** 0.6), T / 2 + T / 2 * sgn * abs(math.sin(ph)) ** 0.6))

    def rr(th):
        return R - 0.02 * (1 - abs(math.cos(10 * th)) ** 0.5)
    vs, fs, rings = [Vector((0, 0, 0))], [], []
    for (dx, z) in prof:
        st = len(vs)
        for s in range(segs):
            th = 2 * math.pi * s / segs
            r = rr(th) - rho + dx
            vs.append(Vector((r * math.cos(th), r * math.sin(th), z)))
        rings.append(st)
    vs.append(Vector((0, 0, T)))
    top = len(vs) - 1
    for s in range(segs):
        fs.append((0, rings[0] + (s + 1) % segs, rings[0] + s))
    for a, b in zip(rings, rings[1:]):
        for s in range(segs):
            s1 = (s + 1) % segs
            fs.append((a + s, a + s1, b + s1, b + s))
    for s in range(segs):
        fs.append((rings[-1] + s, rings[-1] + (s + 1) % segs, top))
    ob = mk('cookie', vs, fs)
    return [(ob, 'cookie')], {'cookie': m_cookie}


BUILDERS = {
    'tree-pink': lambda r: b_tree(r, False), 'tree-mint': lambda r: b_tree(r, True),
    'berry-bush': lambda r: b_berry_bush(r, False), 'berry-bush-s': lambda r: b_berry_bush(r, True),
    'daisy': b_daisy, 'grass-tuft': b_grass, 'mint-bush': b_mint_bush, 'fence': b_fence, 'fence-post': b_post,
    'cookie-stone': b_cookie,
}


# ---------------------------------------------------------------- pipeline
def world_bbox(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def mesh_bbox(ob):
    co = np.empty(len(ob.data.vertices) * 3, np.float64)
    ob.data.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    M = np.array(ob.matrix_world)
    w = co @ M[:3, :3].T + M[:3, 3]
    return Vector(w.min(0)), Vector(w.max(0))


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def bake(ob, mats, img, kind, samples, margin):
    sc = bpy.context.scene
    sc.cycles.samples = samples
    for m in mats:
        nt = m.node_tree
        n = nt.nodes.get('bake_target') or nt.nodes.new('ShaderNodeTexImage')
        n.name = 'bake_target'
        n.image = img
        for x in nt.nodes:
            x.select = False
        n.select = True
        nt.nodes.active = n
        surface(m, {'EMIT_COL': 'col', 'EMIT_ID': 'id'}.get(kind, 'bsdf'))
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    t = {'EMIT_COL': 'EMIT', 'EMIT_ID': 'EMIT'}.get(kind, kind)
    kw = dict(type=t, margin=margin, margin_type='EXTEND', use_clear=True)
    if t == 'NORMAL':
        kw.update(normal_space='TANGENT')
    bpy.ops.object.bake(**kw)
    a = np.empty(img.size[0] * img.size[1] * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(img.size[1], img.size[0], 4)


def new_img(name, px, float_buf=True, cs='Non-Color'):
    im = bpy.data.images.new(name, px, px, alpha=False, float_buffer=float_buf)
    im.colorspace_settings.name = cs
    return im


def build_piece(pid, outdir):
    spec = PIECES[pid]
    seed = int(JOB.get('seed', 20261025)) ^ zlib.crc32(pid.encode())
    rng = random.Random(seed)
    noise.seed_set(seed & 0x7fffffff)
    sc = fresh()
    parts, recipes = BUILDERS[pid](rng)
    mats = {}
    for key, fn in recipes.items():
        mats[key] = material(f'{pid}:{key}', fn, spec['rough'])
    for ob, key in parts:
        ob.data.materials.clear()
        ob.data.materials.append(mats[key])
    objs = [o for o, _ in parts]
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = pid
    ob.data.name = pid
    if spec.get('clamp'):
        for v in ob.data.vertices:
            if v.co.z < 0:
                v.co.z = 0.0
    # fit: exact height, base on z = 0, bbox centred on x / y
    lo, hi = mesh_bbox(ob)
    H = spec['size'][1]
    if spec['fit'] == 'uniform':
        S = Matrix.Scale(H / (hi.z - lo.z), 4)
    else:
        S = Matrix.Diagonal((1, 1, H / (hi.z - lo.z), 1))
    ob.data.transform(S @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
    ob.data.update()
    if pid in ('fence', 'fence-post', 'cookie-stone'):
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(50))
    # UV
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.003, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(rotate=True, margin=0.003)
    bpy.ops.object.mode_set(mode='OBJECT')
    # bakes
    px = spec['tex']
    margin = 8 if px >= 1024 else 4
    sc.world.light_settings.distance = spec['ao'][0]
    used = list(mats.values())
    idm = bake(ob, used, new_img('id', px), 'EMIT_ID', 1, margin)
    col = bake(ob, used, new_img('col', px), 'EMIT_COL', 1, margin)
    ao = bake(ob, used, new_img('ao', px), 'AO', int(JOB.get('ao_samples', 32)), margin)
    nrm = bake(ob, used, new_img('nrm', px), 'NORMAL', 1, margin) if spec['normal'] else None
    # albedo = baked colour x mild AO; each part's exposed (lit-side) texel mean pinned to its swatch
    k = spec['ao'][1]
    aov = ao[..., 0]
    lin = col[..., :3] * (1 - k * (1 - aov))[..., None]
    pid_map = np.rint(idm[..., 0] * 32).astype(int) - 1
    gains = {}
    for i, part in enumerate(PARTS):
        mask = pid_map == i
        if not mask.any():
            continue
        exp = mask & (aov >= EXPOSED_AO)
        sel = exp if exp.sum() >= 50 else mask
        mean = lin[sel].mean(0)
        g = np.array(SW[part]) / np.maximum(mean, 1e-5)
        gains[part] = [round(float(v), 4) for v in g]
        lin[mask] *= g
    srgb = l2s(lin) / 255.0
    rgba = np.concatenate([srgb, np.ones(srgb.shape[:2] + (1,))], -1).astype(np.float32)
    alb = new_img(f'{pid}_albedo', px, False, 'sRGB')
    alb.pixels.foreach_set(rgba.ravel())
    alb.filepath_raw = str(outdir / f'{pid}_albedo.png')
    alb.file_format = 'PNG'
    alb.save()
    side = {'id': pid_map, 'ao': aov}
    for nm, arr in side.items():
        im = new_img(f'{pid}_{nm}', px, False, 'Non-Color')
        v = (arr + 1) / 32.0 if nm == 'id' else arr
        im.pixels.foreach_set(np.repeat(np.clip(v, 0, 1)[..., None], 4, -1).astype(np.float32).ravel())
        im.filepath_raw = str(outdir / f'{pid}_{nm}.png')
        im.file_format = 'PNG'
        im.save()
    nimg = None
    if nrm is not None:
        nimg = new_img(f'{pid}_normal', px, False, 'Non-Color')
        n4 = nrm.copy()
        n4[..., 3] = 1
        nimg.pixels.foreach_set(n4.ravel())
        nimg.filepath_raw = str(outdir / f'{pid}_normal.png')
        nimg.file_format = 'PNG'
        nimg.save()
    # final single material
    fm = bpy.data.materials.new(pid)
    fm.use_nodes = True
    fm.node_tree.nodes.clear()
    N, L = fm.node_tree.nodes, fm.node_tree.links
    out = N.new('ShaderNodeOutputMaterial')
    bsdf = N.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Roughness'].default_value = spec['rough']
    bsdf.inputs['Metallic'].default_value = 0.0
    ti = N.new('ShaderNodeTexImage')
    ti.image = alb
    L.new(ti.outputs['Color'], bsdf.inputs['Base Color'])
    if nimg is not None:
        tn = N.new('ShaderNodeTexImage')
        tn.image = nimg
        nm = N.new('ShaderNodeNormalMap')
        L.new(tn.outputs['Color'], nm.inputs['Color'])
        L.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    L.new(bsdf.outputs[0], out.inputs['Surface'])
    ob.data.materials.clear()
    ob.data.materials.append(fm)
    # export
    glb = outdir / f'{pid}.glb'
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format='GLB', use_selection=True, export_image_format='WEBP',
                              export_image_quality=int(JOB.get('webp_q', 88)), export_apply=True, export_cameras=False,
                              export_lights=False, export_extras=False, export_animations=False, export_tangents=False)
    lo, hi = mesh_bbox(ob)
    rep = {'id': pid, 'glb': str(glb), 'triangles': tris(ob), 'bbox_blender': [list(lo), list(hi)], 'gains': gains,
           'parts': sorted(gains), 'tex': px, 'normal': nimg is not None, 'seed': seed}
    print('SETPIECE', json.dumps(rep))
    return rep


# ---------------------------------------------------------------- check + renders (fresh Blender)
def lights(sc, world_strength, sky_cam=None):
    w = sc.world
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    sky, gnd = np.array(hex_lin(LIGHTS['sky'])), np.array(hex_lin(LIGHTS['ground']))
    avg = (sky + gnd) / 2
    lum = lambda c: 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    avg = avg / lum(avg)
    bg = nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Color'].default_value = (*avg, 1)
    bg.inputs['Strength'].default_value = world_strength
    out = nt.nodes.new('ShaderNodeOutputWorld')
    if sky_cam is not None:
        cam_bg = nt.nodes.new('ShaderNodeBackground')
        cam_bg.inputs['Color'].default_value = (*hex_lin(sky_cam), 1)
        lp = nt.nodes.new('ShaderNodeLightPath')
        mix = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(lp.outputs['Is Camera Ray'], mix.inputs[0])
        nt.links.new(bg.outputs[0], mix.inputs[1])
        nt.links.new(cam_bg.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs['Surface'])
    else:
        nt.links.new(bg.outputs[0], out.inputs['Surface'])
    # key: share of irradiance at the runtime reference normal (key 1.2 x cos vs hemi 1.4), sums to 1 there
    d = Vector(LIGHTS['dir']).normalized()
    rn = Vector(LIGHTS['ref_normal']).normalized()
    key_share = LIGHTS['key_i'] * max(0, d.dot(rn))
    key_frac = key_share / (key_share + LIGHTS['hemi'])
    kc = np.array(hex_lin(LIGHTS['key']))
    kc = kc / lum(kc)
    sun = bpy.data.lights.new('key', 'SUN')
    sun.energy = key_frac * math.pi / max(1e-3, d.dot(rn))
    sun.color = tuple(kc)
    sun.angle = math.radians(3)
    so = link(bpy.data.objects.new('key', sun))
    bdir = Vector((d.x, -d.z, d.y))
    so.rotation_euler = bdir.to_track_quat('Z', 'Y').to_euler()
    bg.inputs['Strength'].default_value = world_strength * (1 - key_frac)
    return key_frac


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [o for o in bpy.data.objects if o not in before]


def render_to(path, res, samples):
    sc = bpy.context.scene
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def check_piece(pid, glbdir, viewdir, render):
    sc = fresh()
    objs = [o for o in import_glb(glbdir / f'{pid}.glb') if o.type == 'MESH']
    los, his = zip(*[mesh_bbox(o) for o in objs])
    lo = Vector((min(v.x for v in los), min(v.y for v in los), min(v.z for v in los)))
    hi = Vector((max(v.x for v in his), max(v.y for v in his), max(v.z for v in his)))
    spec = PIECES[pid]
    H = spec['size'][1]
    g_lo = [lo.x, lo.z, -hi.y]
    g_hi = [hi.x, hi.z, -lo.y]
    h = hi.z - lo.z
    checks = {'height_1pct': abs(h - H) <= 0.01 * H, 'base_y0_1mm': abs(lo.z) <= 0.001,
              'centre_x_1cm': abs((lo.x + hi.x) / 2) <= 0.01, 'centre_z_1cm': abs((lo.y + hi.y) / 2) <= 0.01}
    if pid == 'fence':
        checks['tiling_len_2mm'] = abs((hi.x - lo.x) - 1.0) <= 0.002
    imgs = sorted({(im.name, tuple(im.size)) for im in bpy.data.images if im.size[0] > 0})
    checks['tex_px'] = all(max(s) == spec['tex'] for _, s in imgs)
    n_tris = sum(tris(o) for o in objs)
    rep = {'id': pid, 'bbox': {'min': [round(v, 4) for v in g_lo], 'max': [round(v, 4) for v in g_hi]}, 'height': round(h, 4),
           'tris': n_tris, 'images': [[n, list(s)] for n, s in imgs], 'materials': len({m for o in objs for m in o.data.materials}),
           'meshes': len(objs), 'checks': checks}
    if render:
        lights(sc, 1.0)
        sc.render.film_transparent = True
        cam = bpy.data.cameras.new('cam')
        cam.type = 'ORTHO'
        co = link(bpy.data.objects.new('cam', cam))
        sc.camera = co
        c = (lo + hi) / 2
        ext = hi - lo
        views = {'pz': ((0, -1, 0), (90, 0, 0), (ext.x, ext.z)), 'px': ((1, 0, 0), (90, 0, 90), (ext.y, ext.z)),
                 'nz': ((0, 1, 0), (90, 0, 180), (ext.x, ext.z)), 'nx': ((-1, 0, 0), (90, 0, -90), (ext.y, ext.z))}
        rep['views'] = {}
        for tag, (dv, rot, (w, hh)) in views.items():
            cam.ortho_scale = max(w, hh) * 1.12
            co.location = c + Vector(dv) * (max(ext) * 3 + 2)
            co.rotation_euler = [math.radians(a) for a in rot]
            cam.clip_end = max(ext) * 8 + 10
            p = viewdir / f'{pid}_{tag}.png'
            render_to(p, (384, 384), int(JOB.get('view_samples', 24)))
            rep['views'][tag] = str(p)
    print('SETCHECK', json.dumps(rep))
    return rep


def lineup(glbdir, out):
    sc = fresh()
    src = {}
    for pid in ORDER:
        objs = [o for o in import_glb(glbdir / f'{pid}.glb') if o.type == 'MESH']
        for o in objs:
            o.location = (0, 0, -100)
        src[pid] = objs[0]
    rng = random.Random(int(JOB.get('seed', 20261025)))

    def put(pid, x, z, yaw=0.0):
        o = src[pid].copy()
        link(o)
        o.location = (x, -z, 0)
        o.rotation_euler = (0, 0, yaw)
        return o
    xs = [1.2 + 0.5 + i for i in range(6)]
    for sx in (-1, 1):
        for x in xs:
            put('fence', sx * x, -5)
        for x in (1.2, 7.2):
            put('fence-post', sx * x, -5)
    z = -4.35
    i = 0
    while z < 4.2:
        put('cookie-stone', 0.12 * math.sin(i * 1.3), z, rng.uniform(0, 6.28))
        z += 0.98 + 0.05 * i
        i += 1
    put('tree-pink', -5.6, -7.4, 0.3)
    put('tree-mint', 5.4, -7.2, -0.4)
    for x, z, p in ((-3.4, -4.25, 'berry-bush'), (-1.85, -4.3, 'berry-bush-s'), (1.95, -4.3, 'berry-bush-s'), (3.5, -4.2, 'berry-bush'),
                    (-4.8, 2.6, 'berry-bush'), (4.9, 2.9, 'berry-bush'), (6.4, -4.1, 'berry-bush-s')):
        put(p, x, z, rng.uniform(-0.3, 0.3))
    for x, z in ((-3.2, -8.6), (-0.9, -9.6), (2.4, -9.0), (7.4, -8.4), (-7.6, -8.8)):
        put('mint-bush', x, z, rng.uniform(0, 6.28))
    n = 0
    while n < 16:
        x, z = rng.uniform(-6.5, 6.5), rng.uniform(-3.8, 4.5)
        if abs(x) < 0.8:
            continue
        put('daisy', x, z, rng.uniform(-0.6, 0.6))
        n += 1
    n = 0
    while n < 90:
        x, z = rng.uniform(-8, 8), rng.uniform(-4.8, 6)
        if abs(x) < 0.6:
            continue
        put('grass-tuft', x, z, rng.uniform(0, 6.28))
        n += 1
    for o in src.values():
        bpy.data.objects.remove(o)
    gm = bpy.data.materials.new('lawn')
    gm.use_nodes = True
    gm.node_tree.nodes.clear()
    b = gm.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    o_ = gm.node_tree.nodes.new('ShaderNodeOutputMaterial')
    b.inputs['Base Color'].default_value = (*[(SW['lawn-mid'][i] + SW['lawn-light'][i]) / 2 for i in range(3)], 1)
    b.inputs['Roughness'].default_value = 1.0
    gm.node_tree.links.new(b.outputs[0], o_.inputs['Surface'])
    me = bpy.data.meshes.new('ground')
    me.from_pydata([(-60, -60, 0), (60, -60, 0), (60, 60, 0), (-60, 60, 0)], [], [(0, 1, 2, 3)])
    me.materials.append(gm)
    link(bpy.data.objects.new('ground', me))
    lights(sc, 1.0 / 0.72, sky_cam='#8cc4f8')
    cam = bpy.data.cameras.new('cam')
    cam.sensor_fit = 'VERTICAL'
    cam.angle_y = math.radians(34)
    cam.clip_end = 200
    co = link(bpy.data.objects.new('cam', cam))
    co.location = (0, -12.5, 3.4)
    co.rotation_euler = (Vector((0, 6, 1.6)) - co.location).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = co
    sc.render.film_transparent = False
    render_to(out, (844, 390), int(JOB.get('lineup_samples', 48)))
    print('SETLINEUP', out)


def main():
    if not JOB:
        print('usage: see module docstring')
        return
    out = Path(JOB['out_dir'])
    out.mkdir(parents=True, exist_ok=True)
    views = Path(JOB['views_dir'])
    views.mkdir(parents=True, exist_ok=True)
    reps = {}
    if not CHECK:
        for pid in JOB['pieces']:
            try:
                reps[pid] = build_piece(pid, out)
            except Exception as e:  # report and continue with the next piece; the runner fails on a missing report
                import traceback
                traceback.print_exc()
                reps[pid] = {'id': pid, 'error': repr(e)}
        (out / 'build.json').write_text(json.dumps(reps, indent=1))
        return
    for pid in JOB['pieces']:
        try:
            reps[pid] = check_piece(pid, out, views, JOB.get('render', True))
        except Exception as e:
            import traceback
            traceback.print_exc()
            reps[pid] = {'id': pid, 'error': repr(e)}
    (out / 'check.json').write_text(json.dumps(reps, indent=1))
    if JOB.get('lineup') and all((out / f'{p}.glb').exists() for p in ORDER):
        lineup(out, views / 'lineup.png')


if __name__ == '__main__':
    main()
