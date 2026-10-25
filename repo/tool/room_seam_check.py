#!/usr/bin/env python3
"""Front-face UV seam measure for room characters (2026-10-25, w6-cast; RCCA for Piyo's face line).

    python3 tool/room_seam_check.py assets/room/scoop/{piyo,mongsil,popo,nuri,moa}.glb

Why: a UV island boundary on a character's face shows as a line on the phone (three.js mipmaps + derivative-tangent
normal maps), while Blender renders hide it. A glTF stores a UV seam as several vertices at one position with different
UVs, so a script can see seam placement directly.

Count, per file: duplicate-position vertex groups (positions rounded to 1e-5 m, bind pose, node transforms applied)
whose UVs differ by > 1e-4, inside the FRONT FACE ZONE = vertex normal z > 0.3, |x - centre x| < 30 % of the half
width, y above 45 % of the height (from the base). Pure python (struct + json): runs on boards without numpy.
Exit 1 if any file has a count > 0 (Moa included). One line per file.
"""
import json, math, struct, sys

ZONE_NZ, ZONE_X, ZONE_Y = 0.3, 0.30, 0.45
CT = {5126: ('f', 4), 5123: ('H', 2), 5125: ('I', 4), 5121: ('B', 1), 5122: ('h', 2), 5120: ('b', 1)}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def load(path):
    b = open(path, 'rb').read()
    n = struct.unpack_from('<I', b, 12)[0]
    js = json.loads(b[20:20 + n])
    off = 20 + n
    return js, b[off + 8:off + 8 + struct.unpack_from('<I', b, off)[0]]


def accessor(js, binc, i):
    a = js['accessors'][i]
    bv = js['bufferViews'][a['bufferView']]
    fmt, size = CT[a['componentType']]
    nc = NC[a['type']]
    stride = bv.get('byteStride') or size * nc
    o = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    rows = [struct.unpack_from('<%d%s' % (nc, fmt), binc, o + k * stride) for k in range(a['count'])]
    if a.get('normalized') and fmt != 'f':
        mx = float((1 << (8 * size - (0 if fmt.isupper() else 1))) - 1)
        rows = [tuple(v / mx for v in r) for r in rows]
    return rows


def mat_mul(a, b):
    return [sum(a[r + 4 * k] * b[k + 4 * c] for k in range(4)) for c in range(4) for r in range(4)]


def node_matrix(nd):
    if 'matrix' in nd:
        return list(nd['matrix'])
    t = nd.get('translation', [0, 0, 0]); s = nd.get('scale', [1, 1, 1]); x, y, z, w = nd.get('rotation', [0, 0, 0, 1])
    r = [1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w),
         2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w),
         2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y)]
    return [r[0] * s[0], r[1] * s[0], r[2] * s[0], 0, r[3] * s[1], r[4] * s[1], r[5] * s[1], 0,
            r[6] * s[2], r[7] * s[2], r[8] * s[2], 0, t[0], t[1], t[2], 1]


def world_meshes(js):
    """(mesh index, world matrix) for every mesh node; skinned meshes use their bind pose (node transform only)."""
    out, ident = [], [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    roots = js['scenes'][js.get('scene', 0)]['nodes']
    stack = [(r, ident) for r in roots]
    while stack:
        i, pm = stack.pop()
        nd = js['nodes'][i]
        m = mat_mul(pm, node_matrix(nd))
        if 'mesh' in nd:
            out.append((nd['mesh'], ident if 'skin' in nd else m))
        stack += [(c, m) for c in nd.get('children', [])]
    return out


def xf(m, v, w):
    return [m[r] * v[0] + m[4 + r] * v[1] + m[8 + r] * v[2] + m[12 + r] * w for r in range(3)]


def check(path):
    js, binc = load(path)
    P, N, UV = [], [], []
    for mi, m in world_meshes(js):
        for p in js['meshes'][mi]['primitives']:
            at = p['attributes']
            if 'TEXCOORD_0' not in at:
                continue
            pos = accessor(js, binc, at['POSITION']); nor = accessor(js, binc, at['NORMAL']); uv = accessor(js, binc, at['TEXCOORD_0'])
            for a, n, t in zip(pos, nor, uv):
                P.append(xf(m, a, 1)); nn = xf(m, n, 0); L = math.sqrt(sum(c * c for c in nn)) or 1
                N.append([c / L for c in nn]); UV.append(t)
    xs = [q[0] for q in P]; ys = [q[1] for q in P]
    cx, hw = (min(xs) + max(xs)) / 2, (max(xs) - min(xs)) / 2
    y0, h = min(ys), max(ys) - min(ys)
    groups = {}
    for k, q in enumerate(P):
        groups.setdefault((round(q[0], 5), round(q[1], 5), round(q[2], 5)), []).append(k)
    seams = total = 0
    for vs in groups.values():
        if len(vs) < 2:
            continue
        uvs = [UV[k] for k in vs]
        if max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a in uvs for b in uvs) <= 1e-4:
            continue
        total += 1
        q = P[vs[0]]
        nz = sum(N[k][2] for k in vs) / len(vs)
        if nz > ZONE_NZ and abs(q[0] - cx) < ZONE_X * hw and (q[1] - y0) > ZONE_Y * h:
            seams += 1
    return seams, total, len(P), h


def main(paths):
    bad = 0
    for p in paths:
        seams, total, nv, h = check(p)
        bad += seams > 0
        print(f'room-seam: {p}: front-face seam groups {seams} (all UV seam groups {total}, verts {nv}, height {h:.3f}) '
              + ('FAIL' if seams else 'ok'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
