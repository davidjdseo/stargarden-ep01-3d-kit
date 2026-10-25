"""Room cast lane (2026-10-25, w6-cast): rebuild each room character as a clean, seam-hidden, rigged, animated GLB.

    Blender -b --factory-startup --python tool/room_cast_build.py -- job.json      (pipeline/room-cast.sh writes job.json)

Why (RCCA): Piyo showed a vertical line down its face on the phone. Direct cause: Meshy's unwrap puts UV island borders on
the face centre line; three.js shows that seam through mipmapping and derivative tangents (the GLBs had a normal map and no
TANGENT). The earlier GLB lane kept Meshy UVs + normal map and judged on Blender renders only. This lane re-UVs with seams
placed by a visibility cost (back / underside / hidden folds, never the front face zone), re-bakes colour with full
push-pull padding, drops the normal map, rigs, authors the play-station clips and exports. tool/room_seam_check.py measures
the result on the shipped GLB.

Data-driven: everything per character lives in CAST below (source, remesh, seam cuts, bones, clips). Coordinates are
metres in the placed frame: height 1 m, base z 0, centred XY, FRONT = -Y (glTF +Z), character's left = +X.

Stages per id (friends): place -> weld -> voxel + QuadriFlow + shrinkwrap -> seams (forced cuts + tree/co-tree handle cuts,
weighted by visibility) -> ABF unwrap + pack (16 px @ 1024) -> Cycles bake DIFFUSE colour selected-to-active from the
Meshy retex source (2K) -> push-pull fill -> armature + automatic weights -> clips on NLA tracks -> export WebP -> re-import
check -> renders. Moa: start from the shipped GLB (Meshy rig + 6 clips kept), weld + re-seam + same-mesh bake from the
4K walk texture (old UV -> new UV), add happy/kick, export.
"""
import bpy, bmesh, json, math, os, sys, heapq, time, hashlib
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion, kdtree
import numpy as np

FPS = 24
TEX = 1024
MARGIN_PX = 16
FRONT = Vector((0, -1, 0))

# ---------------------------------------------------------------------------------------------------------------- data
# bones: name -> (head, tail, parent). Roles map clip generators onto bones (missing role = that part is skipped).
# cuts: forced seam paths [from, to]; to=None joins the nearest existing cut. Endpoints snap to the nearest vertex.
CAST = {
    'piyo': {
        'qf_faces': 4300, 'voxel': 0.006, 'cage': 0.03,
        'cuts': [[(0, 0.0, 0.0), (0, 0.10, 0.93)]],
        'bones': {
            'root': ((0, 0, 0), (0, 0, 0.1), None),
            'body': ((0, 0.02, 0.12), (0, 0.02, 0.46), 'root'),
            'head': ((0, 0.02, 0.46), (0, 0.02, 0.86), 'body'),
            'tuft': ((0, 0.02, 0.86), (0, 0.0, 1.0), 'head'),
            'wing_l': ((0.27, 0.02, 0.42), (0.40, 0.0, 0.22), 'body'),
            'wing_r': ((-0.27, 0.02, 0.42), (-0.40, 0.0, 0.22), 'body'),
            'foot_l': ((0.13, -0.02, 0.09), (0.14, -0.14, 0.0), 'root'),
            'foot_r': ((-0.13, -0.02, 0.09), (-0.14, -0.14, 0.0), 'root'),
            'tail': ((0, 0.28, 0.30), (0, 0.42, 0.24), 'body'),
        },
        'roles': {'arm_l': 'wing_l', 'arm_r': 'wing_r', 'top': ['tuft'], 'tail': 'tail'},
        'clips': ['idle', 'happy', 'wave', 'dance', 'sing'],
        'face_z': 0.66,
    },
    'mongsil': {
        'qf_faces': 4300, 'voxel': 0.006, 'cage': 0.03,
        'cuts': [[(0, 0.0, 0.0), (0, 0.30, 0.92)], [(0.58, 0.0, 0.45), None], [(-0.58, 0.0, 0.45), None]],
        'bones': {
            'root': ((0, 0, 0), (0, 0, 0.1), None),
            'body': ((0, 0.02, 0.12), (0, 0.02, 0.48), 'root'),
            'head': ((0, 0.02, 0.48), (0, 0.02, 0.92), 'body'),
            'ear_l': ((0.30, -0.02, 0.62), (0.57, -0.02, 0.45), 'head'),
            'ear_r': ((-0.30, -0.02, 0.62), (-0.57, -0.02, 0.45), 'head'),
            'arm_l': ((0.20, -0.18, 0.40), (0.07, -0.33, 0.31), 'body'),
            'arm_r': ((-0.20, -0.18, 0.40), (-0.07, -0.33, 0.31), 'body'),
            'foot_l': ((0.11, 0.0, 0.11), (0.11, -0.06, 0.0), 'root'),
            'foot_r': ((-0.11, 0.0, 0.11), (-0.11, -0.06, 0.0), 'root'),
            'tail': ((0, 0.30, 0.24), (0, 0.40, 0.22), 'body'),
        },
        'roles': {'arm_l': 'arm_l', 'arm_r': 'arm_r', 'ears': ['ear_l', 'ear_r'], 'tail': 'tail'},
        'clips': ['idle', 'happy', 'wave', 'dance', 'bounce'],
        'face_z': 0.62,
    },
    'popo': {
        'qf_faces': 4300, 'voxel': 0.006, 'cage': 0.03,
        'cuts': [[(0, 0.0, 0.0), (0, 0.05, 1.0)]],
        'bones': {
            'root': ((0, 0, 0), (0, 0, 0.1), None),
            'body': ((0, 0.02, 0.10), (0, 0.02, 0.48), 'root'),
            'head': ((0, 0.02, 0.48), (0, 0.02, 0.88), 'body'),
            'crest': ((0, 0.02, 0.88), (0, 0.02, 1.0), 'head'),
            'wing_l': ((0.25, 0.02, 0.42), (0.39, 0.0, 0.22), 'body'),
            'wing_r': ((-0.25, 0.02, 0.42), (-0.39, 0.0, 0.22), 'body'),
            'foot_l': ((0.15, -0.02, 0.08), (0.17, -0.16, 0.0), 'root'),
            'foot_r': ((-0.15, -0.02, 0.08), (-0.17, -0.16, 0.0), 'root'),
            'tail': ((0, 0.22, 0.22), (0, 0.32, 0.16), 'body'),
        },
        'roles': {'arm_l': 'wing_l', 'arm_r': 'wing_r', 'top': ['crest'], 'tail': 'tail'},
        'clips': ['idle', 'happy', 'wave', 'dance', 'kick'],
        'face_z': 0.66,
    },
    'nuri': {
        'qf_faces': 4300, 'voxel': 0.006, 'cage': 0.03,
        'cuts': [[(0, 0.0, 0.0), (0, 0.10, 0.97)]],
        'bones': {
            'root': ((0, 0, 0), (0, 0, 0.1), None),
            'body': ((0, 0.02, 0.10), (0, 0.02, 0.48), 'root'),
            'head': ((0, 0.02, 0.48), (0, 0.02, 0.92), 'body'),
            'arm_l': ((0.16, 0.0, 0.42), (0.34, -0.03, 0.29), 'body'),
            'arm_r': ((-0.16, 0.0, 0.42), (-0.34, -0.03, 0.29), 'body'),
            'foot_l': ((0.08, 0.0, 0.10), (0.08, -0.08, 0.0), 'root'),
            'foot_r': ((-0.08, 0.0, 0.10), (-0.08, -0.08, 0.0), 'root'),
            'tail': ((0, 0.16, 0.20), (0, 0.30, 0.14), 'body'),
        },
        'roles': {'arm_l': 'arm_l', 'arm_r': 'arm_r', 'tail': 'tail'},
        'clips': ['idle', 'happy', 'wave', 'dance', 'count'],
        'face_z': 0.66,
    },
    'moa': {
        'cuts': [[(0, 0.0, 0.43), (0, 0.12, 0.90)], [(0.20, 0.0, 0.0), None], [(-0.20, 0.0, 0.0), None],
                 [(0.40, 0.0, 0.50), None], [(-0.40, 0.0, 0.50), None]],
        'keep_clips': ['idle', 'walk', 'wave', 'dance', 'jump', 'sway'],
        'clips': ['happy', 'kick'],
        'face_z': 0.68,
    },
}

# ----------------------------------------------------------------------------------------------------------- helpers
def log(*a):
    print('CAST', *a, flush=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    for o in [o for o in new if o.type == 'MESH' and o.name.startswith('Icosphere') and o.parent is None and not o.users_collection]:
        new.remove(o)
    return new


def select_only(objs, active=None):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or (objs[0] if objs else None)


def tri_count(objs):
    n = 0
    for o in objs:
        for p in o.data.polygons:
            n += len(p.vertices) - 2
    return n


def world_bbox(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi


def mesh_bbox(o):
    M = o.matrix_world
    P = np.array([tuple(M @ v.co) for v in o.data.vertices])
    return P.min(0), P.max(0)


def gpu_cycles(scene):
    scene.render.engine = 'CYCLES'
    try:
        pr = bpy.context.preferences.addons['cycles'].preferences
        pr.compute_device_type = 'METAL'
        pr.get_devices()
        for d in pr.devices:
            d.use = True
        scene.cycles.device = 'GPU'
    except Exception as e:
        log('gpu fallback cpu', e)


# ---------------------------------------------------------------------------------------------------- place + remesh
def place_friend(src, yaw_deg):
    objs = import_glb(src)
    meshes = [o for o in objs if o.type == 'MESH']
    select_only(meshes)
    if len(meshes) > 1:
        bpy.ops.object.join()
    hi = bpy.context.view_layer.objects.active
    for o in objs:
        if o != hi and o.name in bpy.data.objects:
            bpy.data.objects.remove(o)
    hi.parent = None
    hi.matrix_world = Matrix.Rotation(math.radians(yaw_deg or 0), 4, 'Z') @ hi.matrix_world
    select_only([hi])
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    lo, up = mesh_bbox(hi)
    s = 1.0 / (up[2] - lo[2])
    c = Vector(((lo[0] + up[0]) / 2, (lo[1] + up[1]) / 2, lo[2]))
    hi.data.transform(Matrix.Scale(s, 4) @ Matrix.Translation(-c))
    hi.name = 'hi'
    return hi


def weld(o, dist):
    bm = bmesh.new(); bm.from_mesh(o.data)
    n0 = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    n1 = len(bm.verts)
    bm.to_mesh(o.data); bm.free(); o.data.update()
    return n0 - n1


def build_low(hi, spec):
    low = hi.copy(); low.data = hi.data.copy(); low.name = 'low'
    bpy.context.scene.collection.objects.link(low)
    low.data.materials.clear()
    while low.data.uv_layers:
        low.data.uv_layers.remove(low.data.uv_layers[0])
    select_only([low])
    m = low.modifiers.new('vox', 'REMESH'); m.mode = 'VOXEL'; m.voxel_size = spec['voxel']; m.use_smooth_shade = True
    bpy.ops.object.modifier_apply(modifier='vox')
    log('voxel faces', len(low.data.polygons))
    r = bpy.ops.object.quadriflow_remesh(target_faces=spec['qf_faces'], use_mesh_symmetry=False, use_preserve_sharp=False,
                                         use_preserve_boundary=False, smooth_normals=False, seed=0)
    log('quadriflow', r, 'faces', len(low.data.polygons))
    m = low.modifiers.new('sw', 'SHRINKWRAP'); m.target = hi; m.wrap_method = 'NEAREST_SURFACEPOINT'
    bpy.ops.object.modifier_apply(modifier='sw')
    m = low.modifiers.new('cs', 'CORRECTIVE_SMOOTH'); m.iterations = 3; m.factor = 0.5; m.use_only_smooth = True
    m.rest_source = 'ORCO'
    bpy.ops.object.modifier_apply(modifier='cs')
    for p in low.data.polygons:
        p.use_smooth = True
    return low


# -------------------------------------------------------------------------------------------------------------- seams
def face_zone(p, n, hw, wide=True):
    """Front face zone of the check (room_seam_check.py), widened here so seams keep a margin from it."""
    nz = -n.y
    if wide:
        return nz > 0.05 and abs(p.x) < 0.55 * hw and p.z > 0.38
    return nz > 0.3 and abs(p.x) < 0.30 * hw and p.z > 0.45


def plan_seams(obj, cuts):
    """Forced cuts (Dijkstra, front-avoiding) + tree/co-tree cut graph so every island is a disk; pruned to the minimum."""
    M = obj.matrix_world
    N3 = M.to_3x3().inverted().transposed()
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    W = [M @ v.co for v in bm.verts]
    hw = max(abs(p.x) for p in W)
    fn = [(N3 @ f.normal).normalized() for f in bm.faces]
    fc = [M @ f.calc_center_median() for f in bm.faces]
    vis = []
    for e in bm.edges:
        fs = e.link_faces
        v = sum(max(0.0, -fn[f.index].y) for f in fs) / max(1, len(fs))
        mid = (W[e.verts[0].index] + W[e.verts[1].index]) / 2
        n = sum((fn[f.index] for f in fs), Vector()).normalized() if fs else Vector((0, 1, 0))
        zone = face_zone(mid, n, hw)
        vis.append(v + (50.0 if zone else 0.0) + (0.6 if n.z < -0.6 else 0.0) * -1)
    cut = set()
    kd = kdtree.KDTree(len(W))
    for i, p in enumerate(W):
        kd.insert(p, i)
    kd.balance()

    def dijkstra(src, targets):
        dist = {src: 0.0}; prev = {}; pq = [(0.0, src)]
        while pq:
            d, v = heapq.heappop(pq)
            if v in targets and v != src:
                path = []
                while v in prev:
                    path.append(prev[v][1]); v = prev[v][0]
                return path
            if d > dist.get(v, 1e18):
                continue
            for e in bm.verts[v].link_edges:
                u = e.other_vert(bm.verts[v]).index
                L = (W[u] - W[v]).length
                c = d + L * (1.0 + 40.0 * max(0.0, vis[e.index]) ** 1.5) + (0 if vis[e.index] < 10 else 1000 * L)
                if c < dist.get(u, 1e18):
                    dist[u] = c; prev[u] = (v, e.index); heapq.heappush(pq, (c, u))
        return []

    for a, b in cuts:
        ia = kd.find(Vector(a))[1]
        if b is None:
            tv = {v for ei in cut for v in (bm.edges[ei].verts[0].index, bm.edges[ei].verts[1].index)}
        else:
            tv = {kd.find(Vector(b))[1]}
        cut |= set(dijkstra(ia, tv))
    forced = set(cut)
    # dual spanning forest (Kruskal), most visible edges first so the tree crosses them (= they stay uncut)
    parent = list(range(len(bm.faces)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    order = sorted((e for e in bm.edges if len(e.link_faces) == 2 and e.index not in forced), key=lambda e: -vis[e.index])
    tree = set()
    for e in order:
        a, b = find(e.link_faces[0].index), find(e.link_faces[1].index)
        if a != b:
            parent[a] = b; tree.add(e.index)
    cand = {e.index for e in bm.edges if len(e.link_faces) == 2 and e.index not in tree} | forced
    bound = {e.index for e in bm.edges if len(e.link_faces) != 2}
    # prune dangling non-forced edges
    deg = {}
    for ei in cand | bound:
        for v in bm.edges[ei].verts:
            deg[v.index] = deg.get(v.index, 0) + 1
    stack = [ei for ei in cand if ei not in forced and any(deg[v.index] == 1 for v in bm.edges[ei].verts)]
    while stack:
        ei = stack.pop()
        if ei not in cand:
            continue
        vs = bm.edges[ei].verts
        if not any(deg[v.index] == 1 for v in vs):
            continue
        cand.discard(ei)
        for v in vs:
            deg[v.index] -= 1
            if deg[v.index] == 1:
                for e2 in v.link_edges:
                    if e2.index in cand and e2.index not in forced:
                        stack.append(e2.index)
    for e in bm.edges:
        e.seam = e.index in cand
    zone_edges = 0
    for ei in cand:
        e = bm.edges[ei]
        mid = (W[e.verts[0].index] + W[e.verts[1].index]) / 2
        fs = e.link_faces
        n = sum((fn[f.index] for f in fs), Vector()).normalized()
        zone_edges += face_zone(mid, n, hw, wide=False)
    bm.to_mesh(obj.data); bm.free(); obj.data.update()
    rep = {'forced_edges': len(forced), 'handle_edges': len(cand - forced), 'seam_edges': len(cand), 'zone_seam_edges': zone_edges}
    log('seams', rep)
    return rep


def unwrap(obj, uv_name='UVMap'):
    me = obj.data
    if uv_name not in me.uv_layers:
        me.uv_layers.new(name=uv_name)
    me.uv_layers.active = me.uv_layers[uv_name]
    select_only([obj])
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT') if hasattr(bpy.ops.uv, 'select_all') else None
    bpy.ops.uv.unwrap(method='ANGLE_BASED', fill_holes=True, correct_aspect=True, margin=0.0)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, scale=True, margin_method='FRACTION', margin=MARGIN_PX / TEX, shape_method='CONCAVE')
    bpy.ops.object.mode_set(mode='OBJECT')
    # island report
    bm = bmesh.new(); bm.from_mesh(me)
    uvl = bm.loops.layers.uv[uv_name]
    seen = set(); islands = 0
    for f in bm.faces:
        if f.index in seen:
            continue
        islands += 1; st = [f]; seen.add(f.index)
        while st:
            g = st.pop()
            for e in g.edges:
                if e.seam:
                    continue
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index); st.append(h)
    # area distortion spread: 3D area / UV area per face, normalised
    ratios = []
    for f in bm.faces:
        uv = [l[uvl].uv for l in f.loops]
        a = 0.0
        for i in range(1, len(uv) - 1):
            a += abs((uv[i] - uv[0]).cross(uv[i + 1] - uv[0])) / 2
        ratios.append(a / max(f.calc_area(), 1e-12))
    bm.free()
    r = np.array(ratios); med = float(np.median(r))
    rep = {'islands': islands, 'uv_texel_ratio_p05': round(float(np.percentile(r, 5)) / med, 3),
           'uv_texel_ratio_p95': round(float(np.percentile(r, 95)) / med, 3)}
    log('unwrap', rep)
    return rep


# --------------------------------------------------------------------------------------------------------------- bake
def new_image(name, fill=(1, 0, 1, 1)):
    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])
    im = bpy.data.images.new(name, TEX, TEX, alpha=True)
    im.generated_color = fill
    im.colorspace_settings.name = 'sRGB'
    return im


def toy_material(name, img, uv_name='UVMap'):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img; tex.interpolation = 'Linear'
    uvn = nt.nodes.new('ShaderNodeUVMap'); uvn.uv_map = uv_name
    nt.links.new(uvn.outputs['UV'], tex.inputs['Vector'])
    nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.8
    bsdf.inputs['Metallic'].default_value = 0.0
    return mat, tex


def raster_mask(obj, uv_name):
    """Pixels covered by UV triangles (numpy, half-pixel centres)."""
    me = obj.data; me.calc_loop_triangles()
    uv = np.array([d.uv[:] for d in me.uv_layers[uv_name].data]) * TEX - 0.5
    mask = np.zeros((TEX, TEX), bool)
    for t in me.loop_triangles:
        a, b, c = uv[list(t.loops)]
        x0, y0 = np.floor(np.minimum(np.minimum(a, b), c)).astype(int)
        x1, y1 = np.ceil(np.maximum(np.maximum(a, b), c)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, TEX - 1), min(y1, TEX - 1)
        if x1 < x0 or y1 < y0:
            continue
        X, Y = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-12:
            continue
        l1 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / d
        l2 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / d
        inside = (l1 >= -1e-6) & (l2 >= -1e-6) & (1 - l1 - l2 >= -1e-6)
        mask[y0:y1 + 1, x0:x1 + 1] |= inside
    return mask


def push_pull(img_np, mask):
    """Fill every uncovered pixel from its covered neighbours at all scales (mip-safe padding for the whole atlas)."""
    rgb = img_np[..., :3].copy(); w = mask.astype(np.float32)
    levels = [(rgb * w[..., None], w)]
    while levels[-1][1].shape[0] > 1:
        c, m = levels[-1]
        h = c.shape[0] // 2
        c2 = c.reshape(h, 2, h, 2, 3).sum((1, 3)); m2 = m.reshape(h, 2, h, 2).sum((1, 3))
        levels.append((c2, m2))
    col = levels[-1][0] / np.maximum(levels[-1][1], 1e-8)[..., None]
    for c, m in reversed(levels[:-1]):
        up = np.repeat(np.repeat(col, 2, 0), 2, 1)
        own = c / np.maximum(m, 1e-8)[..., None]
        k = np.clip(m, 0, 1)[..., None]
        col = own * k + up * (1 - k)
    out = img_np.copy(); out[..., :3] = np.where(mask[..., None], rgb, col); out[..., 3] = 1.0
    return out


def finish_image(img, obj, uv_name, report):
    px = np.array(img.pixels[:], dtype=np.float32).reshape(TEX, TEX, 4)
    mask = raster_mask(obj, uv_name)
    magenta = (px[..., 0] > 0.98) & (px[..., 1] < 0.02) & (px[..., 2] > 0.98)
    report['bake_texels'] = int(mask.sum())
    report['bake_misses'] = int((mask & magenta).sum())
    good = mask & ~magenta
    # grow the baked area by the Cycles margin ring too (everything Cycles wrote that is not the fill colour)
    written = ~magenta
    px = push_pull(px, written | good)
    img.pixels[:] = px.ravel()
    img.update()
    log('bake', {k: report[k] for k in ('bake_texels', 'bake_misses')})


def bake_selected_to_active(hi, low, cage):
    sc = bpy.context.scene
    gpu_cycles(sc)
    sc.cycles.samples = 8
    img = new_image('bake_basecolor')
    mat, tex = toy_material('toy', img)
    low.data.materials.clear(); low.data.materials.append(mat)
    for n in mat.node_tree.nodes:
        n.select = False
    tex.select = True; mat.node_tree.nodes.active = tex
    # hi: make sure base colour is a plain texture (normal map does not matter for a COLOR pass)
    select_only([hi, low], active=low)
    sc.render.bake.use_selected_to_active = True
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, use_selected_to_active=True, cage_extrusion=cage,
                        max_ray_distance=cage * 3, margin=MARGIN_PX, margin_type='EXTEND', use_clear=False, uv_layer='UVMap')
    return mat, img


def bake_same_mesh(obj, src_img, old_uv, new_uv):
    sc = bpy.context.scene
    gpu_cycles(sc)
    sc.cycles.samples = 8
    img = new_image('bake_basecolor')
    mat = bpy.data.materials.new('bakesrc'); mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    t0 = nt.nodes.new('ShaderNodeTexImage'); t0.image = src_img
    u0 = nt.nodes.new('ShaderNodeUVMap'); u0.uv_map = old_uv
    nt.links.new(u0.outputs['UV'], t0.inputs['Vector']); nt.links.new(t0.outputs['Color'], bsdf.inputs['Base Color'])
    t1 = nt.nodes.new('ShaderNodeTexImage'); t1.image = img
    for n in nt.nodes:
        n.select = False
    t1.select = True; nt.nodes.active = t1
    obj.data.materials.clear(); obj.data.materials.append(mat)
    obj.data.uv_layers.active = obj.data.uv_layers[new_uv]
    select_only([obj])
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, use_selected_to_active=False, margin=MARGIN_PX,
                        margin_type='EXTEND', use_clear=False, uv_layer=new_uv)
    return img


# ---------------------------------------------------------------------------------------------------------------- rig
def build_rig(low, spec):
    arm_d = bpy.data.armatures.new('rig'); arm = bpy.data.objects.new('rig', arm_d)
    bpy.context.scene.collection.objects.link(arm)
    select_only([arm])
    bpy.ops.object.mode_set(mode='EDIT')
    for name, (h, t, par) in spec['bones'].items():
        b = arm_d.edit_bones.new(name); b.head = Vector(h); b.tail = Vector(t); b.roll = 0
        b.use_deform = name != 'root'
    for name, (h, t, par) in spec['bones'].items():
        if par:
            arm_d.edit_bones[name].parent = arm_d.edit_bones[par]
    bpy.ops.object.mode_set(mode='OBJECT')
    select_only([low, arm], active=arm)
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    unweighted = sum(1 for v in low.data.vertices if not v.groups or sum(g.weight for g in v.groups) < 1e-4)
    if unweighted:
        # heat weighting failed for some vertices: give them the nearest bone by envelope distance
        log('unweighted verts', unweighted, '-> nearest-bone fill')
        segs = {n: (Vector(h), Vector(t)) for n, (h, t, p) in spec['bones'].items() if n != 'root'}
        for v in low.data.vertices:
            if v.groups and sum(g.weight for g in v.groups) >= 1e-4:
                continue
            best = min(segs, key=lambda n: dist_seg(v.co, *segs[n]))
            low.vertex_groups[best].add([v.index], 1.0, 'REPLACE')
    return arm, unweighted


def dist_seg(p, a, b):
    ab = b - a; t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-12)))
    return (a + ab * t - p).length


# -------------------------------------------------------------------------------------------------------------- clips
class Keyer:
    """Key pose bones with world-axis rotations / offsets (converted to each bone's rest frame)."""

    def __init__(self, arm, base=None):
        self.arm = arm
        self.base = base or {}
        for pb in arm.pose.bones:
            pb.rotation_mode = 'QUATERNION'

    def rest3(self, name):
        return self.arm.data.bones[name].matrix_local.to_3x3()

    def pose(self, frame, rot=None, loc=None, scl=None):
        rot = rot or {}; loc = loc or {}; scl = scl or {}
        AW = self.arm.matrix_world.to_3x3()
        for pb in self.arm.pose.bones:
            n = pb.name
            bq, bl = self.base.get(n, (Quaternion(), Vector()))
            q = bq.copy()
            for axis, deg in rot.get(n, []):
                R = self.rest3(n)
                a = (R.inverted() @ Vector(axis)).normalized()
                q = Quaternion(a, math.radians(deg)) @ q
            pb.rotation_quaternion = q
            off = Vector(loc.get(n, (0, 0, 0)))
            pb.location = bl + (self.rest3(n).inverted() @ (AW.inverted() @ off))
            s = scl.get(n, (1, 1, 1))
            pb.scale = Vector((s[0], s[1], s[2]))
            pb.keyframe_insert('rotation_quaternion', frame=frame)
            pb.keyframe_insert('location', frame=frame)
            pb.keyframe_insert('scale', frame=frame)


def squash(k):
    """Volume-keeping scale for a vertical bone: bone Y is up."""
    return (1 / math.sqrt(k), k, 1 / math.sqrt(k))


X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)


def gen_clip(name, roles):
    """Return {frame: (rot, loc, scl)} for a friend clip. Angles in degrees about WORLD axes; FRONT is -Y.
    Wing/arm raise: character's right arm (-X side) rises by rotating about -Y ... we use the sign per side."""
    b, h = 'body', 'head'
    al, ar = roles.get('arm_l'), roles.get('arm_r')
    tops = roles.get('top', []); ears = roles.get('ears', []); tail = roles.get('tail')
    keys = {}

    def put(f, rot=None, loc=None, scl=None):
        keys[f] = (rot or {}, loc or {}, scl or {})

    def arm_up(side, deg):
        # raise an arm sideways: left arm (+X) tip goes up = rotate about +Y (front is -Y), right arm about -Y
        return [((0, 1, 0) if side == 'l' else (0, -1, 0), deg)]

    if name == 'idle':                                    # 2.5 s loop: breathe + gentle sway
        for f, ph in ((0, 0), (15, 1), (30, 2), (45, 3), (60, 0)):
            s = [1.0, 1.025, 1.0, 1.025][ph]; sway = [0, 3, 0, -3][ph]
            rot = {h: [(Y, sway)], b: [(Y, -sway * 0.3)]}
            if al: rot[al] = arm_up('l', [0, 4, 0, 4][ph])
            if ar: rot[ar] = arm_up('r', [0, 4, 0, 4][ph])
            if tail: rot[tail] = [(Z, sway * 3)]
            for e, sg in zip(ears, (1, -1)): rot[e] = [((0, sg, 0), [0, 5, 0, 5][ph])]
            put(f, rot, {}, {b: squash(s)})
    elif name == 'happy':                                 # 1 s: anticipation, hop with stretch, land squash, settle
        seq = [(0, 0, 1.0, 0), (5, 0, 0.86, 0), (8, 0.02, 1.12, 40), (13, 0.20, 1.06, 60), (18, 0.0, 0.84, 20),
               (21, 0, 1.04, 5), (24, 0, 1.0, 0)]
        for f, z, s, w in seq:
            rot = {}
            if al: rot[al] = arm_up('l', w)
            if ar: rot[ar] = arm_up('r', w)
            for e, sg in zip(ears, (1, -1)): rot[e] = [((0, sg, 0), -w * 0.4)]
            for t in tops: rot[t] = [(X, (s - 1) * 60)]
            put(f, rot, {'root': (0, 0, z)}, {b: squash(s)})
    elif name == 'wave':                                  # 1.5 s: right arm up, three waves, head tilt
        for f, a in ((0, 0), (6, 95), (11, 125), (16, 95), (21, 125), (26, 95), (31, 30), (36, 0)):
            k = min(1.0, a / 95.0)
            rot = {h: [(Y, -6 * k)], b: [(Y, 3 * k)]}
            if ar: rot[ar] = arm_up('r', a)
            for e, sg in zip(ears, (1, -1)): rot[e] = [((0, sg, 0), 8 * k)]
            put(f, rot)
    elif name == 'dance':                                 # 2 s loop: rock + bounce on the beat, arms alternate
        for f in range(0, 49, 6):
            ph = (f // 6) % 4
            side = [1, 0, -1, 0][ph]; down = ph % 2 == 1
            rot = {b: [(Y, 9 * side)], h: [(Y, -6 * side)]}
            if al: rot[al] = arm_up('l', 70 if side > 0 else 15)
            if ar: rot[ar] = arm_up('r', 70 if side < 0 else 15)
            if tail: rot[tail] = [(Z, 20 * side)]
            for e, sg in zip(ears, (1, -1)): rot[e] = [((0, sg, 0), 12 if down else -6)]
            for t in tops: rot[t] = [(Y, -10 * side)]
            put(f, rot, {b: (0, 0, -0.03 if down else 0.0)}, {b: squash(0.92 if down else 1.03)})
    elif name == 'sing':                                  # Piyo 2 s loop: head bob + chest pulse per beat
        for f in range(0, 49, 6):
            beat = (f // 6) % 2 == 1
            rot = {h: [(X, -8 if beat else 4), (Y, 4 if (f // 12) % 2 else -4)]}
            if al: rot[al] = arm_up('l', 20 if beat else 8)
            if ar: rot[ar] = arm_up('r', 20 if beat else 8)
            for t in tops: rot[t] = [(X, 10 if beat else -5)]
            put(f, rot, {}, {b: (1.06, 0.97, 1.06) if beat else (1.0, 1.02, 1.0)})
    elif name == 'kick':                                  # Popo 1 s: wind-up, kick forward with the right foot
        fr = 'foot_r'
        for f, k, lean in ((0, 0, 0), (6, 1, -1), (10, 2, 1), (14, 3, 1), (19, 4, 0.5), (24, 0, 0)):
            ang = [0, 35, -70, -60, -10][k]               # about +X: positive swings the toe back, negative forward
            rot = {fr: [(X, ang)], b: [(X, 6 * lean)], h: [(X, -3 * lean)]}
            if al: rot[al] = arm_up('l', 35 * abs(lean))
            if ar: rot[ar] = arm_up('r', 35 * abs(lean))
            put(f, rot, {fr: (0, 0, [0, 0.03, 0.07, 0.06, 0.01][k])})
    elif name == 'count':                                 # Nuri 1 s: nod + point forward with the right arm
        for f, k in ((0, 0), (5, 1), (10, 2), (14, 2), (19, 1), (24, 0)):
            rot = {h: [(X, [0, -12, 6][k])]}
            if ar: rot[ar] = arm_up('r', [0, 45, 70][k]) + [((0, 0, 1), [0, 25, 45][k])]
            put(f, rot)
    elif name == 'bounce':                                # Mongsil 1 s loop: springy body bounce, ears lag
        for f, z, s, ea in ((0, 0, 1.0, 0), (5, -0.03, 0.85, 10), (10, 0.05, 1.10, -12), (15, 0.02, 1.03, -4),
                            (20, -0.01, 0.95, 6), (24, 0, 1.0, 0)):
            rot = {}
            for e, sg in zip(ears, (1, -1)): rot[e] = [((0, sg, 0), ea)]
            if al: rot[al] = arm_up('l', -ea)
            if ar: rot[ar] = arm_up('r', -ea)
            put(f, rot, {b: (0, 0, z)}, {b: squash(s)})
    else:
        raise SystemExit(f'unknown clip {name}')
    return keys


def author_clips(arm, clips_keys, base=None):
    ad = arm.animation_data or arm.animation_data_create()
    made = {}
    for name, keys in clips_keys.items():
        act = bpy.data.actions.new(name); act.use_fake_user = True
        ad.action = act
        k = Keyer(arm, base)
        for f in sorted(keys):
            rot, loc, scl = keys[f]
            k.pose(f, rot, loc, scl)
        made[name] = act
        ad.action = None
    for pb in arm.pose.bones:
        pb.rotation_quaternion = Quaternion(); pb.location = Vector(); pb.scale = Vector((1, 1, 1))
    return made


def nla_tracks(arm, clips):
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = None
    for tr in list(ad.nla_tracks):
        ad.nla_tracks.remove(tr)
    for name, act in sorted(clips.items()):
        tr = ad.nla_tracks.new(); tr.name = name
        st = tr.strips.new(name, int(act.frame_range[0]), act)
        if hasattr(st, 'action_slot') and getattr(act, 'slots', None):
            st.action_slot = act.slots[0]
    keep = set(clips.values())
    for a in list(bpy.data.actions):
        if a not in keep:
            bpy.data.actions.remove(a)


# ------------------------------------------------------------------------------------------------------- Moa clips
def moa_clips(arm, idle):
    """happy + kick on the Meshy skeleton, offsets on top of the idle clip's first pose (arms down, standing)."""
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = idle
    if hasattr(ad, 'action_slot') and idle.slots:
        ad.action_slot = idle.slots[0]
    bpy.context.scene.frame_set(int(idle.frame_range[0]))
    base = {pb.name: (pb.rotation_quaternion.copy() if pb.rotation_mode == 'QUATERNION' else pb.matrix_basis.to_quaternion(),
                      pb.location.copy()) for pb in arm.pose.bones}
    ad.action = None
    bpy.context.view_layer.update()
    bl = arm.data.bones
    S = arm.matrix_world.to_scale()[0]
    thigh = (bl['LeftUpLeg'].head_local - bl['LeftLeg'].head_local).length * S
    shin = (bl['LeftLeg'].head_local - bl['LeftFoot'].head_local).length * S

    def crouch(a):
        return (thigh + shin) * (1 - math.cos(math.radians(a)))

    happy, kick = {}, {}
    for f, a, z, arm_up in ((0, 0, 0, 0), (5, 28, None, -10), (8, 0, 0.02, 60), (13, 12, 0.16, 140), (18, 30, None, 40),
                            (21, 8, None, 10), (24, 0, 0, 0)):
        lift = (-crouch(a) if z is None else z)
        rot = {'LeftUpLeg': [(X, -a)], 'RightUpLeg': [(X, -a)], 'LeftLeg': [(X, 2 * a)], 'RightLeg': [(X, 2 * a)],
               'LeftFoot': [(X, -a)], 'RightFoot': [(X, -a)], 'Spine': [(X, -a * 0.4)],
               'LeftArm': [(Y, arm_up)], 'RightArm': [(Y, -arm_up)]}
        happy[f] = (rot, {'Hips': (0, 0, lift)}, {})
    for f, k in ((0, 0), (6, 1), (10, 2), (14, 3), (19, 4), (24, 0)):
        leg = [0, 30, -75, -65, -10][k]
        knee = [0, 50, 10, 0, 10][k]
        lean = [0, -1, 1, 1, 0.5][k]
        rot = {'RightUpLeg': [(X, leg)], 'RightLeg': [(X, knee)], 'Spine': [(X, 8 * lean)],
               'LeftArm': [(Y, 30 * abs(lean))], 'RightArm': [(Y, -30 * abs(lean))], 'LeftUpLeg': [(X, -6 * abs(lean))],
               'LeftLeg': [(X, 12 * abs(lean))], 'LeftFoot': [(X, -6 * abs(lean))]}
        kick[f] = (rot, {'Hips': (0, 0, -crouch(6 * abs(lean)))}, {})
    return author_clips(arm, {'happy': happy, 'kick': kick}, base)


# ------------------------------------------------------------------------------------------------------------- export
def export(path, objs):
    select_only(objs)
    bpy.context.scene.render.fps = FPS
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True, export_image_format='WEBP',
                              export_image_quality=88, export_apply=False, export_cameras=False, export_lights=False,
                              export_extras=False, export_animations=True, export_animation_mode='NLA_TRACKS',
                              export_skins=True, export_force_sampling=True, export_tangents=False,
                              export_morph=False, export_def_bones=True)


def glb_json(path):
    import struct
    b = Path(path).read_bytes(); n = int.from_bytes(b[12:16], 'little')
    return json.loads(b[20:20 + n])


def verify(path, expect_clips):
    js = glb_json(path)
    anims = {}
    for a in js.get('animations', []):
        t = max(js['accessors'][s['input']]['max'][0] for s in a['samplers'])
        anims[a['name']] = round(t, 4)
    reset()
    objs = import_glb(path)
    meshes = [o for o in objs if o.type == 'MESH']
    arms = [o for o in objs if o.type == 'ARMATURE']
    for a in arms:
        if a.animation_data:
            a.animation_data.action = None
        a.data.pose_position = 'REST'
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    P = []
    for o in meshes:
        e = o.evaluated_get(deps)
        P += [tuple(e.matrix_world @ v.co) for v in e.data.vertices]
    P = np.array(P)
    lo, hi = P.min(0), P.max(0)
    imgs = [(i['name'], i.get('mimeType')) for i in js.get('images', [])]
    rep = {'clips': sorted(anims), 'clip_seconds': anims, 'skins': len(js.get('skins', [])),
           'joints': [len(s['joints']) for s in js.get('skins', [])], 'tris': tri_count(meshes),
           'height': round(float(hi[2] - lo[2]), 4), 'base_z': round(float(lo[2]), 4),
           'centre_xy': [round(float((lo[i] + hi[i]) / 2), 4) for i in (0, 1)],
           'bbox_after_gltf': {'min': [round(float(lo[0]), 5), round(float(lo[2]), 5), round(float(-hi[1]), 5)],
                               'max': [round(float(hi[0]), 5), round(float(hi[2]), 5), round(float(-lo[1]), 5)]},
           'images': imgs, 'textures_px': [list(i.size) for i in bpy.data.images if i.size[0]],
           'normal_maps': sum('normalTexture' in m for m in js['materials']), 'cameras': len(js.get('cameras', [])),
           'bytes': Path(path).stat().st_size}
    rep['clips_ok'] = sorted(anims) == sorted(expect_clips)
    log('verify', json.dumps(rep))
    return rep, objs


# ------------------------------------------------------------------------------------------------------------ renders
def render_setup(engine, res):
    sc = bpy.context.scene
    if engine == 'CYCLES':
        gpu_cycles(sc); sc.cycles.samples = 64; sc.cycles.use_denoising = True
    else:
        sc.render.engine = 'BLENDER_EEVEE'
        try:
            sc.eevee.taa_render_samples = 16
        except Exception:
            pass
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = 'PNG'
    sc.view_settings.view_transform = 'Standard'
    w = sc.world or bpy.data.worlds.new('w'); sc.world = w
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (0.78, 0.82, 0.86, 1); bg.inputs['Strength'].default_value = 0.9
    if 'key' not in bpy.data.objects:
        for nm, rot, en in (('key', (math.radians(50), 0, math.radians(-30)), 2.6), ('fill', (math.radians(60), 0, math.radians(150)), 0.8)):
            ld = bpy.data.lights.new(nm, 'SUN'); ld.energy = en; ld.angle = math.radians(20)
            lo = bpy.data.objects.new(nm, ld); lo.rotation_euler = rot; sc.collection.objects.link(lo)
    if 'cam' not in bpy.data.objects:
        cd = bpy.data.cameras.new('cam'); co = bpy.data.objects.new('cam', cd); sc.collection.objects.link(co); sc.camera = co
    return sc


def aim(cam, target, yaw_deg, dist, elev_deg=8, ortho=None, lens=50):
    t = Vector(target)
    a = math.radians(yaw_deg); e = math.radians(elev_deg)
    d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    cam.location = t + d * dist
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    if ortho:
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho
    else:
        cam.data.type = 'PERSP'; cam.data.lens = lens
    cam.data.clip_start = 0.01


def shoot(path, engine, res, target, yaw, dist, ortho=None, elev=8):
    sc = render_setup(engine, res)
    aim(bpy.data.objects['cam'], target, yaw, dist, elev, ortho)
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def face_shots(tag, outdir, fz):
    """Phone path: EEVEE (GPU mipmaps) at 128 px, upscaled later; large: Cycles 512 px. Front and 3/4 (character's right)."""
    for yaw, nm in ((0, 'front'), (-35, 'q')):
        shoot(outdir / f'face-{tag}-{nm}-small.png', 'EEVEE', 128, (0, 0, fz), yaw, 1.6)
        shoot(outdir / f'face-{tag}-{nm}-large.png', 'CYCLES', 512, (0, 0, fz), yaw, 1.6)


def view_shots(outdir):
    for yaw, nm in ((0, 'front'), (90, 'left'), (180, 'back'), (-90, 'right')):
        shoot(outdir / f'view-{nm}.png', 'EEVEE', 512, (0, 0, 0.5), yaw, 4, ortho=1.2, elev=0)


def clip_shots(arm, clips, outdir):
    """4 frames per clip (contact) + every frame for the mp4, 3/4 front, EEVEE."""
    sc = bpy.context.scene
    ad = arm.animation_data
    tracks = {t.name: t for t in ad.nla_tracks}
    for t in tracks.values():
        t.mute = True
    seq = []
    for name in clips:
        tr = tracks[name]; tr.mute = False
        st = tr.strips[0]; f0, f1 = int(st.frame_start), int(st.frame_end)
        n = f1 - f0
        for i in range(4):
            sc.frame_set(f0 + round(i * n / 4))
            shoot(outdir / f'clip-{name}-{i}.png', 'EEVEE', 256, (0, 0, 0.5), -30, 4.2, ortho=1.35, elev=6)
        reps = 2 if n < 40 else 1
        for r in range(reps):
            for f in range(f0, f1 + 1):
                sc.frame_set(f)
                p = outdir / f'mp4-{len(seq):04d}.png'
                shoot(p, 'EEVEE', 384, (0, 0, 0.5), -30, 4.2, ortho=1.35, elev=6)
                seq.append(name)
        tr.mute = True
    for t in tracks.values():
        t.mute = False
    (outdir / 'mp4-labels.json').write_text(json.dumps(seq))


def hide_render(objs, hide):
    for o in objs:
        o.hide_render = hide


# --------------------------------------------------------------------------------------------------------------- jobs
def run_friend(job, out):
    cid = job['id']; spec = CAST[cid]
    rep = {'id': cid, 't0': time.time()}
    # before renders (shipped GLB as is: Meshy UVs + normal map)
    reset()
    before = import_glb(job['before'])
    face_shots('before', out, spec['face_z'])
    reset()
    hi = place_friend(job['src'], job.get('yaw_deg', 0))
    lo_, up_ = mesh_bbox(hi)
    rep['src_bbox'] = [lo_.round(5).tolist(), up_.round(5).tolist()]
    rep['welded'] = weld(hi, 1e-5)
    low = build_low(hi, spec)
    rep['low_faces'] = len(low.data.polygons); rep['low_tris'] = tri_count([low])
    rep['seams'] = plan_seams(low, spec['cuts'])
    rep['uv'] = unwrap(low)
    mat, img = bake_selected_to_active(hi, low, spec['cage'])
    finish_image(img, low, 'UVMap', rep)
    bpy.data.objects.remove(hi)
    arm, unw = build_rig(low, spec)
    rep['rig'] = {'bones': list(spec['bones']), 'unweighted_filled': unw}
    clips = author_clips(arm, {c: gen_clip(c, spec['roles']) for c in spec['clips']})
    nla_tracks(arm, clips)
    img.filepath_raw = str(out / 'basecolor.png'); img.file_format = 'PNG'; img.save()
    glb = out / f'{cid}.glb'
    export(glb, [arm, low])
    rep['verify'], objs = verify(glb, spec['clips'])
    arm = next(o for o in objs if o.type == 'ARMATURE'); arm.data.pose_position = 'POSE'
    face_shots('after', out, spec['face_z'])
    view_shots(out)
    clip_shots(arm, spec['clips'], out)
    rep['seconds'] = round(time.time() - rep.pop('t0'), 1)
    return rep


def run_moa(job, out):
    spec = CAST['moa']
    rep = {'id': 'moa', 't0': time.time()}
    reset()
    import_glb(job['before'])
    face_shots('before', out, spec['face_z'])
    # 4K source texture from the Meshy walk GLB (UVs verified identical on the decimated mesh, median err 2e-4)
    reset()
    walk = import_glb(job['walk'])
    wmesh = next(o for o in walk if o.type == 'MESH' and o.data.uv_layers and o.name.startswith('char'))
    src_img = None
    for m in wmesh.data.materials:
        for n in m.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED' and n.inputs['Base Color'].is_linked:
                src_img = n.inputs['Base Color'].links[0].from_node.image
    src_img.pack()
    src_name = src_img.name
    for o in walk:
        bpy.data.objects.remove(o)
    objs = import_glb(job['before'])
    src_img = bpy.data.images[src_name]
    rep['src_tex_px'] = list(src_img.size)
    arm = next(o for o in objs if o.type == 'ARMATURE')
    me_o = next(o for o in objs if o.type == 'MESH' and o.parent == arm and o.data.uv_layers)
    for o in objs:
        if o not in (arm, me_o):
            bpy.data.objects.remove(o)
    keep = {a.name: a for a in bpy.data.actions if a.name in spec['keep_clips']}
    rep['kept_clips'] = {n: [round(x, 3) for x in a.frame_range] for n, a in sorted(keep.items())}
    me_o.data.uv_layers[0].name = 'old'
    S = me_o.matrix_world.to_scale()[0]
    rep['welded'] = weld(me_o, 2e-5 / S)
    me_o.data.uv_layers.new(name='UVMap')
    rep['seams'] = plan_seams(me_o, spec['cuts'])
    rep['uv'] = unwrap(me_o, 'UVMap')
    img = bake_same_mesh(me_o, src_img, 'old', 'UVMap')
    finish_image(img, me_o, 'UVMap', rep)
    me_o.data.uv_layers.remove(me_o.data.uv_layers['old'])
    mat, _ = toy_material('toy', img)
    me_o.data.materials.clear(); me_o.data.materials.append(mat)
    for p in me_o.data.polygons:
        p.use_smooth = True
    if hasattr(me_o.data, 'has_custom_normals') and me_o.data.has_custom_normals:
        select_only([me_o]); bpy.ops.mesh.customdata_custom_splitnormals_clear()
    new = moa_clips(arm, keep['idle'])
    clips = dict(keep); clips.update(new)
    nla_tracks(arm, clips)
    img.filepath_raw = str(out / 'basecolor.png'); img.file_format = 'PNG'; img.save()
    glb = out / 'moa.glb'
    export(glb, [arm, me_o])
    rep['tris'] = tri_count([me_o])
    rep['verify'], objs = verify(glb, spec['keep_clips'] + spec['clips'])
    arm = next(o for o in objs if o.type == 'ARMATURE'); arm.data.pose_position = 'POSE'
    face_shots('after', out, spec['face_z'])
    view_shots(out)
    clip_shots(arm, ['idle', 'walk', 'wave', 'dance', 'happy', 'kick'], out)
    rep['seconds'] = round(time.time() - rep.pop('t0'), 1)
    return rep


def main():
    argv = sys.argv[sys.argv.index('--') + 1:]
    job = json.loads(Path(argv[0]).read_text())
    lane = Path(job['lane'])
    reports = {}
    for j in job['jobs']:
        out = lane / 'out' / j['id']; out.mkdir(parents=True, exist_ok=True)
        try:
            rep = run_moa(j, out) if j['id'] == 'moa' else run_friend(j, out)
            rep['ok'] = True
        except Exception as e:
            import traceback; traceback.print_exc()
            rep = {'id': j['id'], 'ok': False, 'error': repr(e)}
        (out / 'report.json').write_text(json.dumps(rep, indent=1, default=str))
        reports[j['id']] = rep
        log('done', j['id'], rep.get('ok'))
    (lane / 'out' / 'reports.json').write_text(json.dumps(reports, indent=1, default=str))


if __name__ == '__main__':
    main()
