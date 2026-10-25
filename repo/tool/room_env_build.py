"""Scoop Sky room environment: one baked, unlit-at-runtime env GLB built from the approved plate.

Run (Blender 5.0.1, headless):
  blender -b --factory-startup -P tool/room_env_build.py -- <job.json>

job.json keys: repo, lane (scratch dir), mode ("build" | "check"), out_glb, out_json, render_dir,
seed, threads, samples, calib_samples, quick (bool: low-res drafts only).

mode "build": measure swatches from the plates -> build every layer from the DATA block -> render the
plate camera (beauty + class-ID) -> per-class gain so each surface's rendered mean lands on its swatch
-> re-paint -> export env.glb -> write env.json.
mode "check": fresh Blender: import env.glb, assert node names, flat-zone heights, COLOR_0 round trip,
triangle/byte counts, then render the shipped GLB unlit (map x COLOR_0) from the plate, room and
360-degree cameras and write the sheets into render_dir.

Coordinates: built in Blender Z-up; the glTF exporter writes Y-up (glTF x = Blender x, glTF y = Blender z,
glTF z = -Blender y). "Back" (behind the cottage, glTF -Z) = Blender +Y.
Every colour is linear inside this script; swatches are recorded in sRGB 0-255 (what the phone shows).
"""
import bpy, bmesh, json, sys, os, math, time, hashlib
import numpy as np
from mathutils import Vector, Matrix

T0 = time.time()
JOB = json.load(open(sys.argv[sys.argv.index('--') + 1]))
REPO = JOB['repo']
LANE = JOB['lane']
os.makedirs(LANE, exist_ok=True)
PLATES = 'out/shorts/ep01/anchors/world-theme-s1/A-scoop-sky/'


def log(*a):
    print(f'[env {time.time() - T0:6.1f}s]', *a, flush=True)


# ----------------------------------------------------------------------------------------------
# DATA: everything that defines the look. A new plate = a new block here, not new code.
# ----------------------------------------------------------------------------------------------
DATA = {
    'seed': 20261025,
    'eye_gltf': [0.0, 3.4, 12.5],
    # Plate camera: same eye as the room, fitted so the plate's horizon (sky peach peak / lavender
    # mountain base, measured at x 960: row 468-474) lands on row 474 of 941 with a 40 deg vertical fov.
    'plate_camera': {'img': 'plate-v4.png', 'w': 1672, 'h': 941, 'vfov': 40.0, 'horizon_row': 474.0},
    'room_camera': {'pos': [0.0, 3.4, 12.5], 'target': [0.0, 1.6, -6.0], 'vfov': 34.0, 'design_w': 844, 'design_h': 390},
    # Swatches: image, pixel box (x0, y0, x1, y1; top-left origin) list, statistic.
    'swatches': {
        'sky-top': {'img': 'plate-v4.png', 'boxes': [[960, 0, 990, 12]], 'stat': 'mean'},
        'sky-mid': {'img': 'plate-v4.png', 'boxes': [[960, 330, 990, 340]], 'stat': 'mean'},
        'sky-horizon': {'img': 'plate-v4.png', 'boxes': [[960, 452, 990, 470]], 'stat': 'mean'},
        'cloud-top': {'img': 'plate-v4.png', 'boxes': [[150, 175, 450, 255], [1350, 245, 1560, 300]], 'stat': 'nonsky'},
        'cloud-under': {'img': 'plate-v4.png', 'boxes': [[150, 340, 450, 390], [1350, 330, 1560, 395]], 'stat': 'nonsky'},
        'mountain': {'img': 'plate-v4.png', 'boxes': [[650, 452, 690, 466]], 'stat': 'mean'},
        'hill-pink': {'img': 'plate-v4.png', 'boxes': [[300, 450, 380, 480]], 'stat': 'mean'},
        'hill-mint': {'img': 'plate-v4.png', 'boxes': [[490, 440, 540, 458]], 'stat': 'mean'},
        'hill-cream': {'img': 'plate-v4.png', 'boxes': [[430, 490, 470, 510]], 'stat': 'mean'},
        'hill-lilac': {'img': 'plate-v4.png', 'boxes': [[1290, 450, 1340, 480]], 'stat': 'mean'},
        'icing': {'img': 'plate-v4.png', 'boxes': [[340, 400, 362, 410], [1300, 414, 1330, 424]], 'stat': 'mean'},
        'bush-mint': {'img': 'plate-v4.png', 'boxes': [[215, 465, 265, 490]], 'stat': 'mean'},
        'bush-green': {'img': 'plate-v4.png', 'boxes': [[230, 570, 270, 590], [1440, 560, 1490, 590]], 'stat': 'mean'},
        'lawn-light': {'img': 'plate-v4.png', 'boxes': [[1000, 700, 1300, 780]], 'stat': 'p_hi'},
        'lawn-mid': {'img': 'plate-v4.png', 'boxes': [[1000, 700, 1300, 780]], 'stat': 'p_mid'},
        'lawn-dark': {'img': 'plate-v4.png', 'boxes': [[1000, 700, 1300, 780]], 'stat': 'p_lo'},
        'haze': {'img': 'plate-v4.png', 'boxes': [[960, 452, 990, 470]], 'stat': 'mean'},
    },
    # Sky gradient: open-sky column of the plate (between the cloud banks), every row 0..470.
    'sky_strip': {'img': 'plate-v4.png', 'x0': 955, 'x1': 995, 'row0': 0, 'row1': 470},
    'sky_radius': 450.0,
    # Light model (stylised bake): warm key from the bright horizon behind the hills (plate: hills
    # are lit on the side facing the frame centre, lavender shadows) + cool sky fill from above.
    'key_dir_gltf': [0.0, 0.42, -1.0],
    'cloud_key_dir_gltf': [0.15, 1.0, 0.75],
    'key_rgb': [1.0, 0.93, 0.84],
    'fill_rgb': [0.90, 0.92, 1.0],
    # Clouds (from the room eye): az deg (+ = right of frame centre), dist m, base/top elevation deg,
    # width deg, towers [(s across -1..1, height frac, radius frac)], swirls [(tower index, scale)].
    'clouds': [
        {'az': -24.0, 'dist': 230, 'base': -1.0, 'top': 13.9, 'width': 26, 'towers': [[-0.75, 0.55, 0.20], [-0.25, 0.80, 0.24], [0.15, 0.62, 0.21], [0.55, 0.42, 0.17], [0.85, 0.30, 0.13]], 'swirls': [[1, 1.0]]},
        {'az': -10.5, 'dist': 190, 'base': -0.5, 'top': 8.8, 'width': 19, 'towers': [[-0.70, 0.45, 0.20], [-0.15, 0.78, 0.24], [0.35, 0.50, 0.20], [0.80, 0.28, 0.14]], 'swirls': [[1, 0.85]]},
        {'az': 26.5, 'dist': 240, 'base': -1.0, 'top': 13.6, 'width': 22, 'towers': [[-0.80, 0.35, 0.16], [-0.35, 0.62, 0.22], [0.15, 0.78, 0.24], [0.60, 0.84, 0.22]], 'swirls': [[3, 1.0]]},
        {'az': 12.0, 'dist': 200, 'base': -0.5, 'top': 5.6, 'width': 13, 'towers': [[-0.70, 0.55, 0.22], [-0.10, 0.85, 0.26], [0.50, 0.70, 0.24], [0.85, 0.45, 0.18]], 'swirls': []},
        {'az': 2.5, 'dist': 280, 'base': -0.2, 'top': 2.6, 'width': 8, 'towers': [[-0.5, 0.7, 0.3], [0.3, 0.9, 0.32]], 'swirls': []},
        {'az': -52.0, 'dist': 210, 'base': -1.0, 'top': 11.0, 'width': 22, 'towers': [[-0.6, 0.5, 0.2], [-0.05, 0.85, 0.24], [0.5, 0.55, 0.2]], 'swirls': [[1, 0.9]]},
        {'az': 55.0, 'dist': 220, 'base': -1.0, 'top': 10.5, 'width': 20, 'towers': [[-0.55, 0.6, 0.22], [0.1, 0.85, 0.25], [0.6, 0.45, 0.18]], 'swirls': [[1, 0.9]]},
        {'az': -95.0, 'dist': 250, 'base': -1.0, 'top': 8.5, 'width': 24, 'towers': [[-0.6, 0.55, 0.2], [0.0, 0.85, 0.24], [0.6, 0.5, 0.2]], 'swirls': [[1, 0.8]]},
        {'az': 98.0, 'dist': 260, 'base': -1.0, 'top': 9.0, 'width': 22, 'towers': [[-0.5, 0.8, 0.24], [0.2, 0.6, 0.22], [0.7, 0.4, 0.16]], 'swirls': [[0, 0.8]]},
        {'az': -140.0, 'dist': 270, 'base': -1.0, 'top': 8.0, 'width': 22, 'towers': [[-0.5, 0.6, 0.22], [0.1, 0.85, 0.25], [0.65, 0.45, 0.18]], 'swirls': [[1, 0.8]]},
        {'az': 142.0, 'dist': 260, 'base': -1.0, 'top': 7.5, 'width': 20, 'towers': [[-0.4, 0.85, 0.25], [0.3, 0.6, 0.22]], 'swirls': [[0, 0.75]]},
        {'az': 180.0, 'dist': 280, 'base': -1.0, 'top': 9.5, 'width': 26, 'towers': [[-0.65, 0.5, 0.2], [-0.1, 0.8, 0.24], [0.45, 0.6, 0.22], [0.85, 0.35, 0.15]], 'swirls': [[1, 0.85]]},
    ],
    # Hero hills read off plate-v4 (az from the eye, top elevation deg, half width deg, dist m, colour);
    # the rest of the ring is filled procedurally (fill_*).
    'hills': [
        {'az': -21.2, 'el': 4.2, 'hw': 4.7, 'dist': 92, 'col': 'pink'},
        {'az': -13.3, 'el': 2.6, 'hw': 3.6, 'dist': 112, 'col': 'mint'},
        {'az': -15.6, 'el': 0.3, 'hw': 3.0, 'dist': 52, 'col': 'cream'},
        {'az': -9.6, 'el': -0.1, 'hw': 3.6, 'dist': 50, 'col': 'pink'},
        {'az': 14.3, 'el': 1.7, 'hw': 3.3, 'dist': 100, 'col': 'pink'},
        {'az': 21.4, 'el': 3.1, 'hw': 4.6, 'dist': 86, 'col': 'lilac'},
        {'az': 17.4, 'el': -0.6, 'hw': 2.2, 'dist': 46, 'col': 'cream'},
        {'az': 15.2, 'el': -0.4, 'hw': 2.4, 'dist': 50, 'col': 'pink'},
        {'az': -2.5, 'el': 1.4, 'hw': 3.2, 'dist': 120, 'col': 'mint'},
        {'az': 4.0, 'el': 0.9, 'hw': 2.8, 'dist': 95, 'col': 'cream'},
        {'az': 29.0, 'el': 2.2, 'hw': 3.6, 'dist': 105, 'col': 'mint'},
        {'az': -31.0, 'el': 2.8, 'hw': 4.0, 'dist': 100, 'col': 'lilac'},
    ],
    'fill_hills': 20,
    'hill_colours': ['pink', 'mint', 'cream', 'lilac'],
    # Mountain ring: hero peaks from the plate (az, top el, half width deg) + procedural ridge.
    'mountain_peaks': [[-7.3, 1.35, 4.0], [8.0, 0.55, 4.5], [-1.5, 0.9, 3.0], [24.0, 1.1, 5.0], [-30.0, 1.4, 5.5]],
    'mountain_rings': [[300.0, 1.0], [325.0, 0.55]],
    'bush_clusters': 64,
    'terrain_radius': 200.0,
    'terrain_near_r': 70.0,
    'grass_tile_m': 4.0,
    'flat_r': 10.0,
    'corridor': {'x': 8.0, 'z0': 0.0, 'z1': 16.0},
}
RNG = np.random.default_rng(JOB.get('seed', DATA['seed']))
SEED = int(JOB.get('seed', DATA['seed']))
EYE_G = np.array(DATA['eye_gltf'])
EYE = np.array([EYE_G[0], -EYE_G[2], EYE_G[1]])  # Blender coords


def g2b(v):
    v = np.asarray(v, float)
    return np.array([v[0], -v[2], v[1]])


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


KEY = unit(g2b(DATA['key_dir_gltf']))
CKEY = unit(g2b(DATA['cloud_key_dir_gltf']))
KEY_RGB = np.array(DATA['key_rgb'])
FILL_RGB = np.array(DATA['fill_rgb'])


# ----------------------------------------------------------------------------------------------
# colour + noise helpers
# ----------------------------------------------------------------------------------------------
def s2l(c):
    c = np.asarray(c, float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def l2s(c):
    c = np.clip(np.asarray(c, float), 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055) * 255.0


def smoothstep(a, b, x):
    t = np.clip((np.asarray(x, float) - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def _hash(*ints):
    h = np.uint64(SEED * 2654435761 % 4294967296)
    out = np.full(np.shape(ints[0]), h, dtype=np.uint64)
    for k, iv in enumerate(ints):
        iv = np.asarray(iv).astype(np.int64).astype(np.uint64)
        out = (out ^ (iv * np.uint64([374761393, 668265263, 2246822519][k]))) & np.uint64(0xFFFFFFFF)
        out = (out * np.uint64(1274126177)) & np.uint64(0xFFFFFFFF)
        out = out ^ (out >> np.uint64(15))
    return out.astype(np.float64) / 4294967295.0


def vnoise2(x, y, salt=0):
    x = np.asarray(x, float) + salt * 17.13
    y = np.asarray(y, float) - salt * 9.71
    xi, yi = np.floor(x), np.floor(y)
    fx, fy = x - xi, y - yi
    u, v = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = _hash(xi, yi), _hash(xi + 1, yi)
    c, d = _hash(xi, yi + 1), _hash(xi + 1, yi + 1)
    return (a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v) * 2 - 1


def vnoise3(x, y, z, salt=0):
    x = np.asarray(x, float) + salt * 17.13
    y = np.asarray(y, float) - salt * 9.71
    z = np.asarray(z, float) + salt * 3.37
    xi, yi, zi = np.floor(x), np.floor(y), np.floor(z)
    fx, fy, fz = x - xi, y - yi, z - zi
    u, v, w = (f * f * (3 - 2 * f) for f in (fx, fy, fz))
    acc = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                wt = (u if dx else 1 - u) * (v if dy else 1 - v) * (w if dz else 1 - w)
                acc = acc + wt * _hash(xi + dx, yi + dy, zi + dz)
    return acc * 2 - 1


def fbm2(x, y, octaves=4, salt=0):
    s, a, f, n = 0, 0.5, 1.0, 0
    for o in range(octaves):
        s = s + a * vnoise2(x * f, y * f, salt + o * 7)
        n += a
        a *= 0.5
        f *= 2.03
    return s / n


def fbm3(x, y, z, octaves=3, salt=0):
    s, a, f, n = 0, 0.5, 1.0, 0
    for o in range(octaves):
        s = s + a * vnoise3(x * f, y * f, z * f, salt + o * 7)
        n += a
        a *= 0.5
        f *= 2.03
    return s / n


def periodic_noise(n, scale_px, seed, aniso=1.0):
    """Tileable gaussian-filtered noise, zero mean, unit std."""
    r = np.random.default_rng(seed)
    w = r.standard_normal((n, n))
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    f = np.sqrt(fx ** 2 + (fy * aniso) ** 2)
    out = np.real(np.fft.ifft2(np.fft.fft2(w) * np.exp(-(f * scale_px) ** 2)))
    return (out - out.mean()) / (out.std() + 1e-9)


# ----------------------------------------------------------------------------------------------
# images
# ----------------------------------------------------------------------------------------------
_IMG = {}


def load_img(name):
    """Plate pixels as sRGB 0-255 float array, row 0 = top (Blender buffers are bottom-up)."""
    if name in _IMG:
        return _IMG[name]
    path = name if os.path.isabs(name) else os.path.join(REPO, PLATES, name)
    im = bpy.data.images.load(path, check_existing=False)
    im.colorspace_settings.name = 'sRGB'
    w, h = im.size
    a = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)[::-1, :, :3].astype(np.float64)
    if im.is_float:
        a = l2s(a)
    else:
        a = a * 255.0
    bpy.data.images.remove(im)
    _IMG[name] = a
    return a


def save_png_srgb(arr255, path, quality=None):
    """arr255: HxWx3 sRGB 0-255 (row 0 = top). Writes a PNG/JPEG byte image without any transform."""
    h, w = arr255.shape[:2]
    im = bpy.data.images.new(os.path.basename(path), w, h, alpha=False, float_buffer=False)
    rgba = np.ones((h, w, 4), np.float32)
    rgba[:, :, :3] = np.clip(arr255[::-1], 0, 255) / 255.0
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = path
    if path.lower().endswith('.jpg'):
        im.file_format = 'JPEG'
        sc = bpy.context.scene
        sc.render.image_settings.quality = quality or 90
    else:
        im.file_format = 'PNG'
    im.save()
    return im


def texture_image(name, lin, lane_dir):
    """Linear float HxWx3 -> sRGB PNG on disk -> Blender image (sRGB) used by the material + exporter."""
    path = os.path.join(lane_dir, name + '.png')
    old = bpy.data.images.get(name + '.png')
    if old:
        bpy.data.images.remove(old)
    srgb = np.round(l2s(lin))
    im = save_png_srgb(srgb, path)
    bpy.data.images.remove(im)
    im = bpy.data.images.load(path, check_existing=False)
    im.name = name + '.png'
    im.colorspace_settings.name = 'sRGB'
    return im, srgb


# ----------------------------------------------------------------------------------------------
# swatches + sky gradient (measured)
# ----------------------------------------------------------------------------------------------
def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def measure_box(a, box, stat):
    x0, y0, x1, y1 = box
    px = a[y0:y1, x0:x1].reshape(-1, 3)
    if stat == 'nonsky':
        px = px[px[:, 0] > 200]
    if stat in ('p_lo', 'p_mid', 'p_hi'):
        order = np.argsort(lum(px))
        n = len(order)
        sl = {'p_lo': slice(0, n // 5), 'p_mid': slice(2 * n // 5, 3 * n // 5), 'p_hi': slice(n - n // 5, n)}[stat]
        px = px[order[sl]]
    return px


def measure_swatches():
    out = {}
    for k, s in DATA['swatches'].items():
        a = load_img(s['img'])
        px = np.concatenate([measure_box(a, b, s['stat']) for b in s['boxes']])
        out[k] = {'img': PLATES + s['img'], 'boxes': s['boxes'], 'stat': s['stat'], 'n': int(len(px)),
                  'srgb': [round(float(v), 1) for v in px.mean(0)]}
    return out


PC = DATA['plate_camera']
F_PLATE = (PC['h'] / 2) / math.tan(math.radians(PC['vfov'] / 2))


def row_to_el(row):
    return np.degrees(np.arctan((PC['horizon_row'] - np.asarray(row, float)) / F_PLATE))


def sky_gradient():
    """(elevation deg ascending, linear rgb) from the plate's open-sky column."""
    s = DATA['sky_strip']
    a = load_img(s['img'])
    rows = np.arange(s['row0'], s['row1'] + 1)
    cols = a[rows, s['x0']:s['x1']].mean(1)
    # light smoothing along rows (plate has jpeg-ish grain); keeps the gradient monotone and band-free
    k = np.ones(9) / 9
    sm = np.stack([np.convolve(np.pad(cols[:, c], 4, mode='edge'), k, mode='valid') for c in range(3)], 1)
    el = row_to_el(rows)
    order = np.argsort(el)
    return el[order], s2l(sm[order])


def sky_color_at(el, grad, haze_lin):
    els, cols = grad
    out = np.stack([np.interp(el, els, cols[:, c]) for c in range(3)], -1)
    below = smoothstep(0.0, -2.5, el)[..., None]
    return out * (1 - below) + haze_lin * below


# ----------------------------------------------------------------------------------------------
# geometry helpers
# ----------------------------------------------------------------------------------------------
def mesh_from_arrays(name, verts, faces, uvs=None, smooth=True):
    me = bpy.data.meshes.new(name)
    verts = np.asarray(verts, np.float64)
    faces = [list(map(int, f)) for f in faces]
    me.from_pydata(verts.tolist(), [], faces)
    if smooth:
        me.shade_smooth()
    if uvs is not None:
        uvl = me.uv_layers.new(name='UVMap')
        loops = np.empty(len(me.loops), np.int64)
        me.loops.foreach_get('vertex_index', loops)
        uv = np.asarray(uvs, np.float64)[loops]
        uvl.data.foreach_set('uv', uv.ravel())
    me.update()
    return me


def grid_faces(nr, nc, wrap_c=True):
    faces = []
    for i in range(nr - 1):
        for j in range(nc if wrap_c else nc - 1):
            j2 = (j + 1) % nc
            a, b, c, d = i * nc + j, i * nc + j2, (i + 1) * nc + j2, (i + 1) * nc + j
            faces.append((a, b, c, d))
    return faces


def mesh_arrays(me):
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get('co', co)
    nor = np.empty(n * 3)
    me.vertex_normals.foreach_get('vector', nor)
    return co.reshape(n, 3), nor.reshape(n, 3)


def set_color(me, name, rgb, domain='POINT'):
    a = me.color_attributes.get(name)
    if a is None:
        a = me.color_attributes.new(name, 'FLOAT_COLOR', domain)
    rgba = np.ones((len(rgb), 4))
    rgba[:, :3] = np.clip(rgb, 0, 1) if name == 'Col' else rgb
    a.data.foreach_set('color', rgba.ravel())
    if name == 'Col':
        me.color_attributes.active_color = a
        me.color_attributes.render_color_index = me.color_attributes.find('Col')
    return a


def tri_count(me):
    me.calc_loop_triangles()
    return len(me.loop_triangles)


def eval_to_mesh(obj, name):
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    ev = obj.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    me.name = name
    return me


def decimate(me, target_tris):
    t = tri_count(me)
    if t <= target_tris:
        return me
    ob = bpy.data.objects.new('tmp_dec', me)
    bpy.context.scene.collection.objects.link(ob)
    md = ob.modifiers.new('dec', 'DECIMATE')
    md.ratio = target_tris / t
    md.use_collapse_triangulate = True
    out = eval_to_mesh(ob, me.name + '_d')
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    return out


def metaball_mesh(name, balls, resolution, threshold, target_tris):
    """balls: list of (center xyz, visual radius). Returns a polygonised, decimated mesh."""
    mb = bpy.data.metaballs.new(name)
    mb.resolution = resolution
    mb.render_resolution = resolution
    mb.threshold = threshold
    # single-ball surface radius = r * sqrt(1 - sqrt(threshold)) for blender's (1-d^2/r^2)^2 field
    k = 1.0 / math.sqrt(1 - math.sqrt(threshold))
    for c, r in balls:
        e = mb.elements.new()
        e.co = Vector(c)
        e.radius = r * k
    ob = bpy.data.objects.new(name, mb)
    bpy.context.scene.collection.objects.link(ob)
    me = eval_to_mesh(ob, name + '_m')
    bpy.data.objects.remove(ob)
    bpy.data.metaballs.remove(mb)
    return decimate(me, target_tris)


def join_meshes(name, parts):
    """parts: list of meshes (already in the same local frame). Consumes them."""
    bm = bmesh.new()
    for me in parts:
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    out = bpy.data.meshes.new(name)
    bm.to_mesh(out)
    bm.free()
    out.shade_smooth()
    return out


def sphere_ao(p, n, centers, radii, strength=1.0):
    """Analytic occlusion of points p (normals n) by a set of spheres (Quilez sphere occlusion)."""
    ao = np.ones(len(p))
    for c, r in zip(centers, radii):
        d = c - p
        dl = np.linalg.norm(d, axis=1) + 1e-6
        ndl = np.einsum('ij,ij->i', n, d) / dl
        occ = np.clip(ndl * (r / dl) ** 2, 0, 1) * (dl > r * 1.02)
        ao *= 1 - strength * occ
    return ao


def light_rgb(n, ao, key, key_amt=0.55, wrap=0.45, fill_up=0.35):
    ndl = np.einsum('ij,j->i', n, key)
    k = np.clip((ndl + wrap) / (1 + wrap), 0, 1)
    fill = (1 - fill_up) + fill_up * np.clip(n[:, 2], -1, 1)
    l = FILL_RGB[None] * fill[:, None] + KEY_RGB[None] * (key_amt * k)[:, None]
    return l * ao[:, None]


def eye_dist(p):
    return np.linalg.norm(p - EYE[None], axis=1)


def haze_amount(d, d0=30.0, scale=420.0):
    return 1 - np.exp(-np.clip(d - d0, 0, None) / scale)


# ----------------------------------------------------------------------------------------------
# terrain height field (shared by terrain, hills, bushes)
# ----------------------------------------------------------------------------------------------
HILL_SWELLS = []  # (x, y, radius, height)


def flat_dist(x, y):
    """Distance (m, Blender xy) to the exact-flat zone: disc r 10 + corridor |x|<=8, glTF z 0..16."""
    c = DATA['corridor']
    d_disc = np.clip(np.hypot(x, y) - DATA['flat_r'], 0, None)
    ylo, yhi = -c['z1'], -c['z0']
    dx = np.clip(np.abs(x) - c['x'], 0, None)
    dy = np.clip(np.maximum(ylo - y, y - yhi), 0, None)
    return np.minimum(d_disc, np.hypot(dx, dy))


def terrain_h(x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    d = flat_dist(x, y)
    r = np.hypot(x, y) + 1e-6
    back = smoothstep(-0.35, 0.75, y / r)
    amp = smoothstep(0.0, 32.0, d) * (1.6 + 2.2 * back)
    n = fbm2(x / 46.0, y / 46.0, 3, salt=1)
    h = amp * (0.55 + 0.75 * n)
    for hx, hy, hr, hh in HILL_SWELLS:
        h = h + hh * np.exp(-((x - hx) ** 2 + (y - hy) ** 2) / (1.7 * hr) ** 2) * smoothstep(0, 20, d)
    return np.where(d <= 0, 0.0, h)


# ----------------------------------------------------------------------------------------------
# layer builders. Each returns dict(obj, cls_info, paint(gains)) so calibration can re-paint.
# ----------------------------------------------------------------------------------------------
COL = bpy.data.collections.new('env')
bpy.context.scene.collection.children.link(COL)


def new_obj(name, me, parent=None, loc=(0, 0, 0)):
    ob = bpy.data.objects.new(name, me)
    COL.objects.link(ob)
    ob.location = loc
    if parent is not None:
        ob.parent = parent
    return ob


def az_dir(az_deg):
    a = math.radians(az_deg)
    return np.array([math.sin(a), math.cos(a), 0.0])


def at_az(az, dist, z):
    p = EYE + az_dir(az) * dist
    return np.array([p[0], p[1], z])


class Layer:
    def __init__(self, name):
        self.name = name
        self.objs = []
        self.textures = {}


def build_sky(SW, grad):
    R = DATA['sky_radius']
    els = sorted(set([-90, -60, -35, -20, -12, -8, -5, -3.5] + list(np.round(np.arange(-2.4, 12.01, 0.4), 2))
                     + list(range(13, 31, 1)) + list(range(33, 90, 4)) + [89.5]))
    nseg = 64
    phis = np.linspace(0, 2 * np.pi, nseg, endpoint=False)
    V = []
    for e in els:
        er = math.radians(e)
        for ph in phis:
            V.append((R * math.cos(er) * math.sin(ph), R * math.cos(er) * math.cos(ph), R * math.sin(er)))
    V = np.array(V)
    nr = len(els)
    faces = [f[::-1] for f in grid_faces(nr, nseg)]  # inward facing
    top = len(V)
    V = np.vstack([V, [[0, 0, R]], [[0, 0, -R]]])
    for j in range(nseg):
        j2 = (j + 1) % nseg
        faces.append(((nr - 1) * nseg + j, (nr - 1) * nseg + j2, top))
        faces.append((j2, j, top + 1))
    me = mesh_from_arrays('env_sky', V, faces)
    ob = new_obj('env_sky', me)
    haze = s2l(SW['haze']['srgb'])
    rel = V - EYE[None]
    el_eye = np.degrees(np.arctan2(rel[:, 2], np.hypot(rel[:, 0], rel[:, 1])))
    lay = Layer('sky')
    lay.objs = [ob]

    def paint(G):
        c = sky_color_at(el_eye, grad, haze * G.get('haze', 1))
        set_color(me, 'Col', c)
        cls = np.where(el_eye < -0.5, CLS['haze'], CLS['sky'])
        set_color(me, 'ID', id_rgb(cls))
    lay.paint = paint
    return lay


def build_mountains(SW):
    peaks = DATA['mountain_peaks']
    nseg = 720
    az = np.linspace(-180, 180, nseg, endpoint=False)
    V, faces, meta = [], [], []
    base = 0
    for ring_i, (rad, vis) in enumerate(DATA['mountain_rings']):
        # elevation profile: procedural ridge (higher in the back arc) + hero peaks
        back = np.cos(np.radians(az)) * 0.5 + 0.5
        ridge = (0.35 + 0.9 * back) * vis
        nz = np.abs(vnoise2(az / 9.0, ring_i * 5.0, salt=11 + ring_i)) * 0.7 + 0.3 * (fbm2(az / 23.0, ring_i * 3.0, 3, salt=13) + 0.5)
        el = ridge * (0.45 + 1.1 * nz)
        if ring_i == 0:
            for paz, pel, phw in peaks:
                da = np.abs(((az - paz) + 180) % 360 - 180)
                el = np.maximum(el, pel * np.clip(1 - da / phw, 0, 1) ** 1.25 + 0.15)
        el = np.clip(el, 0.35, 2.6)
        for k, a in enumerate(az):
            p = np.array([math.sin(math.radians(a)) * rad, math.cos(math.radians(a)) * rad])
            d = np.hypot(p[0] - EYE[0], p[1] - EYE[1])
            zt = EYE[2] + d * math.tan(math.radians(el[k]))
            V.append((p[0], p[1], zt))
            V.append((p[0], p[1], -40.0))
            meta.append((ring_i, 1.0))
            meta.append((ring_i, 0.0))
        for k in range(nseg):
            k2 = (k + 1) % nseg
            a, b = base + 2 * k, base + 2 * k2
            faces.append((a, a + 1, b + 1, b))
        base = len(V)
    V = np.array(V)
    me = mesh_from_arrays('env_mountains', V, faces, smooth=False)
    ob = new_obj('env_mountains', me)
    meta = np.array(meta)
    rel = V - EYE[None]
    el_eye = np.degrees(np.arctan2(rel[:, 2], np.hypot(rel[:, 0], rel[:, 1])))
    lay = Layer('mountains')
    lay.objs = [ob]

    def paint(G):
        mcol = s2l(SW['mountain']['srgb']) * G.get('mountain', 1)
        haze = s2l(SW['haze']['srgb']) * G.get('haze', 1)
        # top = mountain colour, fading into the haze toward/below the horizon; far ring hazier
        t = smoothstep(-0.6, 1.4, el_eye) * np.where(meta[:, 1] > 0.5, 1.0, 0.0)
        t = np.where(meta[:, 1] > 0.5, smoothstep(-0.2, 1.0, el_eye) * 0.55 + 0.45, smoothstep(-1.2, 0.0, el_eye) * 0.45)
        t = t * np.where(meta[:, 0] > 0, 0.55, 1.0)
        c = haze[None] * (1 - t[:, None]) + mcol[None] * t[:, None]
        set_color(me, 'Col', c)
        set_color(me, 'ID', id_rgb(np.full(len(V), CLS['mountain'])))
    lay.paint = paint
    return lay


def swirl_mesh(name, R0, H, turns=2.6, lean=0.0):
    """Soft-serve swirl: tapered helical tube (curve bevel), base radius R0, height H, local origin at base."""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = 1.0
    cu.bevel_resolution = 3
    cu.use_fill_caps = True
    sp = cu.splines.new('POLY')
    n = 110
    sp.points.add(n - 1)
    for i in range(n):
        t = i / (n - 1)
        ang = 2 * math.pi * turns * t
        rr = R0 * (1 - t) ** 0.85 * 0.78
        z = H * (t ** 0.92) * 0.82 + 0.0
        x, y = rr * math.cos(ang), rr * math.sin(ang)
        if t > 0.88:  # curled tip leaning over
            q = (t - 0.88) / 0.12
            x += lean * R0 * 0.35 * q * q
            z += H * 0.10 * q
        sp.points[i].co = (x, y, z, 1)
        sp.points[i].radius = R0 * (0.56 * (1 - t) ** 0.9 + 0.035)
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    me = eval_to_mesh(ob, name + '_m')
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    return me


def build_clouds(SW):
    parent = bpy.data.objects.new('env_clouds', None)
    COL.objects.link(parent)
    lay = Layer('clouds')
    lay.objs = []
    infos = []
    rng = np.random.default_rng(SEED + 7)
    for ci, c in enumerate(DATA['clouds']):
        d = c['dist']
        dirv = az_dir(c['az'])
        tang = np.array([dirv[1], -dirv[0], 0.0]) * -1  # +s = to the right as seen from the eye
        tang = np.array([math.cos(math.radians(c['az'])), -math.sin(math.radians(c['az'])), 0.0])
        zb = EYE[2] + d * math.tan(math.radians(c['base']))
        zt = EYE[2] + d * math.tan(math.radians(c['top']))
        W = 2 * d * math.tan(math.radians(c['width'] / 2))
        Ht = zt - zb
        center_xy = EYE[:2] + dirv[:2] * d
        cz = zb + 0.45 * Ht
        center = np.array([center_xy[0], center_xy[1], cz])
        balls = []
        # base row of big puffs
        nb = 9
        for i in range(nb):
            s = -0.92 + 1.84 * i / (nb - 1) + rng.uniform(-0.05, 0.05)
            r = W * (0.10 - 0.035 * abs(s)) * rng.uniform(0.85, 1.15)
            p = center_xy + tang[:2] * s * W / 2 + dirv[:2] * rng.uniform(-0.25, 0.25) * W * 0.25
            balls.append(((p[0], p[1], zb + 0.55 * r), r))
        swirl_on = {int(t): sc for t, sc in c['swirls']}
        tops = []
        for ti, (s, hf, rf) in enumerate(c['towers']):
            r = rf * W * 0.5
            top = zb + hf * Ht
            if ti in swirl_on:
                top = zb + hf * Ht * 0.80  # the swirl supplies the last stretch
            z = zb + r * 0.8
            pxy = center_xy + tang[:2] * s * W / 2
            k = 0
            while z < top - r * 0.75:
                jit = rng.uniform(-0.12, 0.12, 2) * r
                balls.append(((pxy[0] + jit[0], pxy[1] + jit[1] + dirv[1] * 0.1 * r, z), r * rng.uniform(0.92, 1.05)))
                z += r * 0.62
                k += 1
            ztop = max(z, zb + r)
            balls.append(((pxy[0], pxy[1], top - r * 0.75), r))
            tops.append((pxy, top, r))
            # cauliflower bumps on the upper surface facing the eye
            for j in range(9):
                th = rng.uniform(0.15, 1.35)
                ph = rng.uniform(-1.9, 1.9)
                local = np.array([math.sin(th) * math.sin(ph), -math.sin(th) * math.cos(ph), math.cos(th)])
                world = tang * local[0] + dirv * local[1] + np.array([0, 0, local[2]])
                zc = rng.uniform(zb + r * 0.6, top - r * 0.6)
                cpos = np.array([pxy[0], pxy[1], zc]) + world * r * 0.85
                balls.append((tuple(cpos), r * rng.uniform(0.32, 0.48)))
        # local frame: origin at the cloud centre
        lb = [((b[0][0] - center[0], b[0][1] - center[1], b[0][2] - center[2]), b[1]) for b in balls]
        res = max(0.9, W / 46.0)
        big = c['top'] > 9
        body = metaball_mesh(f'mbc{ci:02d}', lb, res, 0.35, 4200 if big else 2600)
        parts = [body]
        swirl_pts = []
        for ti, sc in c['swirls']:
            pxy, top, r = tops[ti]
            R0 = r * 1.05 * sc
            H = (zb + c['towers'][ti][1] * Ht - (top - r * 0.75)) + r * 0.9
            H = max(H, R0 * 1.5)
            sm = swirl_mesh(f'sw{ci:02d}', R0, H, lean=1.0 if c['az'] < 0 else -1.0)
            base = np.array([pxy[0], pxy[1], top - r * 0.35]) - center
            sm.transform(Matrix.Translation(Vector(base)))
            parts.append(sm)
            for t in np.linspace(0, 1, 12):
                swirl_pts.append((base + np.array([0, 0, H * t * 0.8]), R0 * (0.5 * (1 - t) + 0.08)))
        me = join_meshes(f'env_cloud_{ci + 1:02d}', parts)
        me = decimate(me, 5200 if big else 3000)
        ob = new_obj(f'env_cloud_{ci + 1:02d}', me, parent=parent, loc=tuple(center))
        lay.objs.append(ob)
        occ_c = np.array([b[0] for b in lb] + [p for p, r in swirl_pts])
        occ_r = np.array([b[1] for b in lb] + [r for p, r in swirl_pts])
        infos.append({'obj': ob, 'me': me, 'zb': zb - cz, 'zt': zt - cz, 'occ': (occ_c, occ_r), 'center': center, 'W': W})
    lay.parent = parent

    def paint(G):
        top = s2l(SW['cloud-top']['srgb']) * G.get('cloud-top', 1)
        und = s2l(SW['cloud-under']['srgb']) * G.get('cloud-under', 1)
        for inf in infos:
            me = inf['me']
            p, n = mesh_arrays(me)
            t = (p[:, 2] - inf['zb']) / (inf['zt'] - inf['zb'])
            wpos = p + inf['center']
            nz = fbm3(wpos[:, 0] / 18, wpos[:, 1] / 18, wpos[:, 2] / 18, 3, salt=21)
            w = smoothstep(0.22, 0.62, t + 0.18 * nz)
            alb = und[None] * (1 - w[:, None]) + top[None] * w[:, None]
            ao = sphere_ao(p, n, inf['occ'][0], inf['occ'][1], 0.7) ** 0.6
            l = light_rgb(n, ao, CKEY, key_amt=0.35, wrap=0.6, fill_up=0.18)
            l = l / np.array([1.0, 1.0, 1.0])
            c = alb * l
            set_color(me, 'Col', c)
            set_color(me, 'ID', id_rgb(np.where(w > 0.5, CLS['cloud-top'], CLS['cloud-under'])))
    lay.paint = paint
    lay.infos = infos
    return lay


# ---- hills ------------------------------------------------------------------------------------
TILE_W, TILE_H, ATLAS = 256, 128, 1024
U_SPAN = math.radians(220.0)


def hill_list():
    hills = [dict(h) for h in DATA['hills']]
    rng = np.random.default_rng(SEED + 31)
    cols = DATA['hill_colours']
    tries = 0
    while len(hills) < len(DATA['hills']) + DATA['fill_hills'] and tries < 4000:
        tries += 1
        az = rng.uniform(-180, 180)
        back = abs(az) <= 75
        if not back and rng.random() < 0.45:
            continue
        if abs(az) <= 36:  # the plate frame is authored by the hero list
            continue
        dist = rng.uniform(55, 140) if back else rng.uniform(70, 140)
        el = rng.uniform(1.0, 6.0) if back else rng.uniform(1.0, 4.0)
        hw = rng.uniform(3.0, 5.5) * (90 / dist) ** 0.3
        ok = True
        for h in hills:
            if abs(((h['az'] - az) + 180) % 360 - 180) < (h['hw'] + hw) * 0.75 and abs(h['dist'] - dist) < 25:
                ok = False
                break
        if ok:
            hills.append({'az': float(az), 'el': float(el), 'hw': float(hw), 'dist': float(dist), 'col': cols[len(hills) % 4]})
    return hills


def hill_surface(R, H, th, ph, seed):
    """Scoop dome. th: 0 top .. pi/2 base; ph: azimuth. Returns xyz (local, base at z = 0)."""
    s = np.sin(th)
    lump = 1 + 0.045 * vnoise2(np.cos(ph) * 2.2 + seed, np.sin(ph) * 2.2, salt=41) \
        + 0.05 * np.sin(ph * 7 + seed) * smoothstep(0.55, 1.0, th / (np.pi / 2))
    r = R * s ** 0.72 * lump
    z = H * np.cos(th) ** 0.80 + 0.03 * H * vnoise2(np.cos(ph) * 3 + seed, th * 3, salt=43)
    return np.stack([r * np.cos(ph), r * np.sin(ph), z], -1)


def build_hills(SW):
    hills = hill_list()
    assert len(hills) <= (ATLAS // TILE_W) * (ATLAS // TILE_H), 'atlas full'
    rng = np.random.default_rng(SEED + 53)
    specs = []
    for i, h in enumerate(hills):
        dirv = az_dir(h['az'])
        cxy = EYE[:2] + dirv[:2] * h['dist']
        R = h['dist'] * math.tan(math.radians(h['hw'])) * 1.05
        ztop = EYE[2] + h['dist'] * math.tan(math.radians(h['el']))
        HILL_SWELLS.append((cxy[0], cxy[1], R, rng.uniform(0.6, 1.4)))
        specs.append(dict(h, cxy=cxy, R=R, ztop=ztop, seed=float(rng.uniform(0, 100)), tile=i))
    for sp in specs:
        foot = np.linspace(0, 2 * np.pi, 16, endpoint=False)
        zg = terrain_h(sp['cxy'][0] + 0.8 * sp['R'] * np.cos(foot), sp['cxy'][1] + 0.8 * sp['R'] * np.sin(foot))
        sp['zg'] = float(zg.min()) - 0.4
        sp['H'] = max(sp['ztop'] - sp['zg'], sp['R'] * 0.35)
        to_eye = EYE[:2] - sp['cxy']
        sp['ph_face'] = math.atan2(to_eye[1], to_eye[0])
    NU, NV = 44, 15
    V, F, UV, OWN = [], [], [], []
    for sp in specs:
        base = len(V)
        ph = sp['ph_face'] + np.pi + np.linspace(0, 2 * np.pi, NU + 1)  # seam at the back
        th = (np.linspace(0, 1, NV) ** 0.9) * (np.pi / 2) * 1.0
        TH, PH = np.meshgrid(th, ph, indexing='ij')
        P = hill_surface(sp['R'], sp['H'] + 0.4, TH, PH, sp['seed'])
        P[..., 0] += sp['cxy'][0]
        P[..., 1] += sp['cxy'][1]
        P[..., 2] += sp['zg']
        rel = ((PH - sp['ph_face'] + np.pi) % (2 * np.pi)) - np.pi
        u = np.clip(rel / U_SPAN + 0.5, 0, 1)
        v = TH / (np.pi / 2)
        tx, ty = sp['tile'] % (ATLAS // TILE_W), sp['tile'] // (ATLAS // TILE_W)
        inset = 2.0
        U = (tx * TILE_W + inset + u * (TILE_W - 2 * inset)) / ATLAS
        Vv = 1 - (ty * TILE_H + inset + v * (TILE_H - 2 * inset)) / ATLAS
        V.extend(P.reshape(-1, 3).tolist())
        UV.extend(np.stack([U, Vv], -1).reshape(-1, 2).tolist())
        nc = NU + 1
        for i in range(NV - 1):
            for j in range(NU):
                a, b = base + i * nc + j, base + i * nc + j + 1
                F.append((a, b, b + nc, a + nc))
        OWN.extend([sp['tile']] * (NV * nc))
    me = mesh_from_arrays('env_hills', np.array(V), F, uvs=np.array(UV))
    # orient faces outward (param order may give inward normals)
    co, nor = mesh_arrays(me)
    own = np.array(OWN)
    cen = np.array([[specs[o]['cxy'][0], specs[o]['cxy'][1], specs[o]['zg']] for o in own])
    if np.mean(np.einsum('ij,ij->i', nor, co - cen)) < 0:
        me.flip_normals()
        me.update()
    ob = new_obj('env_hills', me)
    lay = Layer('hills')
    lay.objs = [ob]
    lay.specs = specs

    # per-tile texel surface (same param as the mesh, at texture resolution) for the bake
    uu = (np.arange(TILE_W - 4) + 0.5) / (TILE_W - 4)
    vv = (np.arange(TILE_H - 4) + 0.5) / (TILE_H - 4)
    VV, UU = np.meshgrid(vv, uu, indexing='ij')
    sprinkle_cols = s2l(np.array([[245, 120, 160], [250, 222, 110], [120, 175, 245], [140, 222, 190], [255, 250, 245], [190, 140, 230]]))

    def tile_maps(sp):
        TH = VV * (np.pi / 2)
        PH = sp['ph_face'] + (UU - 0.5) * U_SPAN
        P = hill_surface(sp['R'], sp['H'] + 0.4, TH, PH, sp['seed'])
        eps = 1e-3
        Pt = hill_surface(sp['R'], sp['H'] + 0.4, TH + eps, PH, sp['seed'])
        Pp = hill_surface(sp['R'], sp['H'] + 0.4, TH, PH + eps, sp['seed'])
        N = np.cross(Pt - P, Pp - P)
        N = N / (np.linalg.norm(N, axis=-1, keepdims=True) + 1e-12)
        N = np.where(N[..., 2:3] < 0, -N, N)
        N[0] = [0, 0, 1]
        Pw = P + np.array([sp['cxy'][0], sp['cxy'][1], sp['zg']])
        # icing mask with wavy edge + drips (u, v in tile units)
        rr = np.random.default_rng(int(sp['seed'] * 1000))
        v0 = 0.36 + 0.035 * np.sin(UU * 2 * np.pi * rr.uniform(2.5, 4.5) + rr.uniform(0, 6)) + 0.02 * vnoise2(UU * 9, sp['seed'], salt=47)
        lim = v0.copy()
        ndr = rr.integers(7, 12)
        for k in range(ndr):
            uc = rr.uniform(0.04, 0.96)
            w = rr.uniform(0.022, 0.045)
            D = rr.uniform(0.07, 0.24)
            q = np.clip(1 - ((UU - uc) / w) ** 2, 0, 1)
            lim = np.maximum(lim, v0 + D * q ** 0.35)
        aa = 1.2 / (TILE_H - 4)
        ice = np.clip((lim - VV) / aa + 0.5, 0, 1)
        lip = np.clip(1 - np.abs(VV - lim - 0.012) / 0.018, 0, 1) * (1 - ice)  # thin shadow under the icing
        # sprinkles on the icing (and a few on the body)
        spr = np.zeros(UU.shape + (3,))
        sprm = np.zeros(UU.shape)
        ns = 70
        for k in range(ns):
            uc, vc = rr.uniform(0.02, 0.98), rr.uniform(0.02, 0.62)
            iu, iv = int(uc * (TILE_W - 4)), int(vc * (TILE_H - 4))
            if ice[min(iv, TILE_H - 5), min(iu, TILE_W - 5)] < 0.5 and rr.random() < 0.8:
                continue
            ang = rr.uniform(0, np.pi)
            col = sprinkle_cols[rr.integers(0, len(sprinkle_cols))]
            for du in range(-2, 3):
                for dv in range(-2, 3):
                    a = du * math.cos(ang) + dv * math.sin(ang)
                    b = -du * math.sin(ang) + dv * math.cos(ang)
                    if (a / 1.9) ** 2 + (b / 0.8) ** 2 <= 1.0:
                        y, x = iv + dv, iu + du
                        if 0 <= y < TILE_H - 4 and 0 <= x < TILE_W - 4:
                            spr[y, x] = col
                            sprm[y, x] = 1
        ao = 0.80 + 0.20 * smoothstep(1.0, 0.55, VV)  # ground contact
        return N, Pw, ice, lip, spr, sprm, ao

    maps = [tile_maps(sp) for sp in specs]
    lay.maps = maps

    def paint(G):
        atlas = np.zeros((ATLAS, ATLAS, 3))
        idat = np.zeros((ATLAS, ATLAS, 3))
        haze = s2l(SW['haze']['srgb']) * G.get('haze', 1)
        icing = s2l(SW['icing']['srgb']) * G.get('icing', 1)
        for sp, (N, Pw, ice, lip, spr, sprm, ao) in zip(specs, maps):
            key = 'hill-' + sp['col']
            body = s2l(SW[key]['srgb']) * G.get(key, 1)
            l = light_rgb(N.reshape(-1, 3), ao.reshape(-1), KEY, key_amt=0.42, wrap=0.55, fill_up=0.30).reshape(N.shape)
            l = l * (1 - 0.18 * lip[..., None])
            alb = body[None, None] * (1 - ice[..., None]) + icing[None, None] * ice[..., None]
            alb = alb * (1 - sprm[..., None]) + spr * sprm[..., None]
            c = alb * l
            hz = haze_amount(eye_dist(Pw.reshape(-1, 3))).reshape(ice.shape)[..., None] * 0.6
            c = c * (1 - hz) + haze[None, None] * hz
            tx, ty = sp['tile'] % (ATLAS // TILE_W), sp['tile'] // (ATLAS // TILE_W)
            y0, x0 = ty * TILE_H, tx * TILE_W
            pad = np.pad(c, ((2, 2), (2, 2), (0, 0)), mode='edge')
            atlas[y0:y0 + TILE_H, x0:x0 + TILE_W] = pad
            idt = np.where(ice[..., None] > 0.5, id_rgb(np.array([CLS['icing']]))[0], id_rgb(np.array([CLS[key]]))[0])
            idt = np.where(sprm[..., None] > 0, id_rgb(np.array([CLS['none']]))[0], idt)
            idat[y0:y0 + TILE_H, x0:x0 + TILE_W] = np.pad(idt, ((2, 2), (2, 2), (0, 0)), mode='edge')
        im, srgb = texture_image('env_hills_atlas', atlas, LANE)
        idim, _ = texture_image('env_hills_id', idat, LANE)
        lay.textures = {'base': im, 'id': idim}
        set_color(me, 'Col', np.ones((len(me.vertices), 3)))
    lay.paint = paint
    lay.vertex_white = True
    return lay


# ---- bushes -----------------------------------------------------------------------------------
def bush_texture():
    n = 512
    a = periodic_noise(n, 9.0, SEED + 61)
    b = periodic_noise(n, 3.0, SEED + 62)
    t = 0.80 + 0.13 * np.tanh(1.4 * a) + 0.05 * b
    t = np.clip(t, 0.55, 1.0)
    return np.repeat(t[..., None], 3, -1)


def build_bushes(SW):
    rng = np.random.default_rng(SEED + 71)
    placed = []
    tries = 0
    target = DATA['bush_clusters']
    while len(placed) < target and tries < 20000:
        tries += 1
        az = rng.uniform(-180, 180)
        back = abs(az) < 80
        if not back and rng.random() < 0.55:
            continue
        r = rng.uniform(24, 62) if back else rng.uniform(26, 60)
        x, y = math.sin(math.radians(az)) * r, math.cos(math.radians(az)) * r
        if flat_dist(np.array([x]), np.array([y]))[0] < 9:
            continue
        sz = rng.uniform(1.6, 3.4) * (r / 40) ** 0.35
        if any(math.hypot(x - px, y - py) < (sz + ps) * 1.1 for px, py, ps, _ in placed):
            continue
        placed.append((x, y, sz, 'green' if (r < 38 and rng.random() < 0.6) else 'mint'))
    parent_parts = []
    V_all = []
    meta = []
    occ_sets = []
    for bi, (x, y, sz, col) in enumerate(placed):
        zg = float(terrain_h(np.array([x]), np.array([y]))[0])
        nb = rng.integers(5, 10)
        balls = []
        for k in range(nb):
            ang = rng.uniform(0, 2 * np.pi)
            rad = rng.uniform(0, 0.75) * sz
            rb = sz * rng.uniform(0.45, 0.7)
            h = sz * (0.55 + 0.55 * (1 - rad / sz)) * rng.uniform(0.8, 1.1)
            balls.append(((x + math.cos(ang) * rad, y + math.sin(ang) * rad, zg + h - rb * 0.3), rb))
        balls.append(((x, y, zg + sz * 0.9), sz * 0.62))
        cen = np.array([x, y, zg])
        lb = [((b[0][0] - x, b[0][1] - y, b[0][2] - zg), b[1]) for b in balls]
        me = metaball_mesh(f'mbb{bi:03d}', lb, max(0.22, sz / 7.0), 0.5, 460)
        me.transform(Matrix.Translation(Vector(cen)))
        parent_parts.append(me)
        occ_sets.append((np.array([b[0] for b in balls]), np.array([b[1] for b in balls]), col, cen, sz))
    # join everything into one layer mesh but keep a per-vertex owner index
    owners = []
    for i, me in enumerate(parent_parts):
        owners.append(np.full(len(me.vertices), i))
    owners = np.concatenate(owners)
    me = join_meshes('env_bushes', parent_parts)
    # spherical UV per cluster for the floret texture
    co, nor = mesh_arrays(me)
    cen = np.array([occ_sets[o][3] + np.array([0, 0, occ_sets[o][4] * 0.7]) for o in owners])
    d = co - cen
    phi = np.arctan2(d[:, 1], d[:, 0])
    th = np.arctan2(np.hypot(d[:, 0], d[:, 1]), d[:, 2])
    sz = np.array([occ_sets[o][4] for o in owners])
    uv = np.stack([phi / (2 * np.pi) * 4 * (sz / 2.5), th / np.pi * 2.5 * (sz / 2.5)], -1)
    uvl = me.uv_layers.new(name='UVMap')
    loops = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get('vertex_index', loops)
    # fix the azimuth seam per polygon (unwrap jumps of a full turn)
    uvc = uv[loops].copy()
    poly_start = np.empty(len(me.polygons), np.int64)
    poly_tot = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get('loop_start', poly_start)
    me.polygons.foreach_get('loop_total', poly_tot)
    span = 4 * (sz[loops] / 2.5)
    for ps, pt in zip(poly_start, poly_tot):
        seg = uvc[ps:ps + pt, 0]
        sp_ = span[ps]
        if seg.max() - seg.min() > sp_ * 0.5:
            seg[seg < seg.mean()] += sp_
            uvc[ps:ps + pt, 0] = seg
    uvl.data.foreach_set('uv', uvc.ravel())
    ob = new_obj('env_bushes', me)
    lay = Layer('bushes')
    lay.objs = [ob]
    tex = bush_texture()
    tex_mean = tex.reshape(-1, 3).mean(0)

    def paint(G):
        co, nor = mesh_arrays(me)
        haze = s2l(SW['haze']['srgb']) * G.get('haze', 1)
        c = np.zeros_like(co)
        ids = np.zeros(len(co), int)
        for i, (oc, orr, col, cen_, sz_) in enumerate(occ_sets):
            m = owners == i
            key = 'bush-' + col
            alb = s2l(SW[key]['srgb']) * G.get(key, 1)
            p, n = co[m], nor[m]
            ao = sphere_ao(p, n, oc, orr, 0.8) ** 0.7
            ao *= 0.72 + 0.28 * smoothstep(0, sz_ * 0.9, p[:, 2] - cen_[2])
            var = 1 + 0.06 * fbm3(p[:, 0] / 2.0, p[:, 1] / 2.0, p[:, 2] / 2.0, 2, salt=73)
            l = light_rgb(n, ao, KEY, key_amt=0.45, wrap=0.5, fill_up=0.35)
            cc = alb[None] * l * var[:, None]
            hz = haze_amount(eye_dist(p))[:, None] * 0.6
            cc = cc * (1 - hz) + haze[None] * hz
            c[m] = cc / tex_mean[None]
            ids[m] = CLS[key]
        set_color(me, 'Col', np.clip(c, 0, 1))
        set_color(me, 'ID', id_rgb(ids))
        im, _ = texture_image('env_bush_florets', tex, LANE)
        lay.textures = {'base': im}
    lay.paint = paint
    return lay


# ---- terrain ----------------------------------------------------------------------------------
def grass_texture(SW, contrast):
    n = 1024
    macro = periodic_noise(n, 90.0, SEED + 81)
    clump = periodic_noise(n, 9.0, SEED + 82)
    tufts = periodic_noise(n, 3.5, SEED + 83, aniso=0.45)
    fine = periodic_noise(n, 1.3, SEED + 84)
    v = 0.22 * macro + 0.42 * clump + 0.26 * tufts + 0.10 * fine
    v = (v - v.mean()) / v.std()
    q = np.argsort(np.argsort(v.ravel())).reshape(v.shape) / (v.size - 1)  # rank 0..1
    dark, mid, light = (s2l(SW[k]['srgb']) for k in ('lawn-dark', 'lawn-mid', 'lawn-light'))
    dark = mid + contrast * (dark - mid)
    light = mid + contrast * (light - mid)
    xs = np.array([0.0, 0.10, 0.5, 0.90, 1.0])
    stops = np.stack([dark - (mid - dark) * 0.25, dark, mid, light, light + (light - mid) * 0.15])
    out = np.stack([np.interp(q, xs, stops[:, c]) for c in range(3)], -1)
    out = np.clip(out, 0, 1)
    peak = out.reshape(-1, 3).max()
    return out / max(peak, 1e-6) * 0.995


def build_terrain(SW):
    R = DATA['terrain_radius']
    radii = [0.0]
    r = 0.6
    while r < R:
        radii.append(r)
        r = r * 1.055 + 0.25
    radii.append(R)
    radii = np.array(radii)
    nseg = 176
    phis = np.linspace(0, 2 * np.pi, nseg, endpoint=False)
    RR, PP = np.meshgrid(radii[1:], phis, indexing='ij')
    X, Y = RR * np.sin(PP), RR * np.cos(PP)
    Z = terrain_h(X, Y)
    V = np.vstack([[[0, 0, 0]], np.stack([X, Y, Z], -1).reshape(-1, 3)])
    nr = len(radii) - 1
    F = []
    for j in range(nseg):
        F.append((0, 1 + j, 1 + (j + 1) % nseg))
    for f in grid_faces(nr, nseg):
        F.append(tuple(1 + i for i in f))
    tile = DATA['grass_tile_m']
    UV = np.stack([V[:, 0] / tile, V[:, 1] / tile], -1)
    me = mesh_from_arrays('env_terrain', V, F, uvs=UV)
    co, nor = mesh_arrays(me)
    if nor[:, 2].mean() < 0:
        me.flip_normals()
        me.update()
    # material split: near (grass texture) / far (vertex colour only)
    ring_of_face = np.array([0] * nseg + [i for i in range(nr - 1) for _ in range(nseg)])
    near = radii[1:][np.minimum(ring_of_face + 1, nr - 1)] <= DATA['terrain_near_r']
    me.polygons.foreach_set('material_index', np.where(near, 0, 1).astype(np.int32))
    ob = new_obj('env_terrain', me)
    lay = Layer('terrain')
    lay.objs = [ob]
    lay.contrast = 1.0
    # per-vertex lighting from the height field (normals + curvature)
    e = 0.75
    hx = (terrain_h(co[:, 0] + e, co[:, 1]) - terrain_h(co[:, 0] - e, co[:, 1])) / (2 * e)
    hy = (terrain_h(co[:, 0], co[:, 1] + e) - terrain_h(co[:, 0], co[:, 1] - e)) / (2 * e)
    N = unit(np.stack([-hx, -hy, np.ones_like(hx)], -1))
    e2 = 4.0
    lap = (terrain_h(co[:, 0] + e2, co[:, 1]) + terrain_h(co[:, 0] - e2, co[:, 1]) + terrain_h(co[:, 0], co[:, 1] + e2)
           + terrain_h(co[:, 0], co[:, 1] - e2) - 4 * co[:, 2]) / (e2 * e2)
    cur = np.clip(-lap * 6.0, -0.25, 0.25)
    rad = np.hypot(co[:, 0], co[:, 1])
    lay.near_poly = near

    def paint(G):
        tex = grass_texture(SW, lay.contrast)
        tex_mean = tex.reshape(-1, 3).mean(0)
        mid = s2l(SW['lawn-mid']['srgb']) * G.get('lawn', 1)
        haze = s2l(SW['haze']['srgb']) * G.get('haze', 1)
        l = light_rgb(N, np.ones(len(N)), KEY, key_amt=0.30, wrap=0.6, fill_up=0.5)
        l = l / l.mean(0, keepdims=True)
        var = 1 + 0.07 * fbm2(co[:, 0] / 9.0, co[:, 1] / 9.0, 3, salt=91)
        yel = 0.5 + 0.5 * fbm2(co[:, 0] / 23.0, co[:, 1] / 23.0, 2, salt=93)
        alb = mid[None] * (1 + np.outer(yel - 0.5, [0.10, 0.04, -0.12]))
        c = alb * l * (1 + cur)[:, None] * var[:, None]
        hz = haze_amount(eye_dist(co), d0=12.0, scale=300.0) * 0.55
        hz = np.maximum(hz, smoothstep(110.0, 192.0, rad))
        c = c * (1 - hz[:, None]) + haze[None] * hz[:, None]
        # corner colours: near faces carry Col / texture mean, far faces carry Col itself
        loops = np.empty(len(me.loops), np.int64)
        me.loops.foreach_get('vertex_index', loops)
        pstart = np.empty(len(me.polygons), np.int64)
        me.polygons.foreach_get('loop_start', pstart)
        ptot = np.empty(len(me.polygons), np.int64)
        me.polygons.foreach_get('loop_total', ptot)
        loop_near = np.repeat(lay.near_poly, ptot)
        cc = c[loops]
        cc = np.where(loop_near[:, None], cc / tex_mean[None], cc)
        set_color(me, 'Col', np.clip(cc, 0, 1), domain='CORNER')
        set_color(me, 'ID', id_rgb(np.full(len(loops), CLS['lawn'])), domain='CORNER')
        im, _ = texture_image('env_grass', tex, LANE)
        lay.textures = {'base': im}
        lay.tex_mean = tex_mean
    lay.paint = paint
    return lay


# ----------------------------------------------------------------------------------------------
# classes (ID pass) + materials
# ----------------------------------------------------------------------------------------------
CLS_NAMES = ['none', 'sky', 'haze', 'mountain', 'cloud-top', 'cloud-under', 'hill-pink', 'hill-mint', 'hill-cream',
             'hill-lilac', 'icing', 'bush-mint', 'bush-green', 'lawn']
CLS = {k: i for i, k in enumerate(CLS_NAMES)}


def id_rgb(cls):
    cls = np.asarray(cls, int)
    # distinct, exactly representable codes: index -> (i*16 + 8)/255 in R, fixed G/B tags
    r = (cls * 16 + 8) / 255.0
    return s2l(np.stack([r * 255, np.full_like(r, 128.0), np.full_like(r, 64.0)], -1))


def decode_id(srgb):
    return np.clip(np.round((srgb[..., 0] - 8) / 16.0), 0, len(CLS_NAMES) - 1).astype(int)


def mat_unlit(name, image=None, attr='Col', mode='beauty'):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Strength'].default_value = 1.0
    ca = nt.nodes.new('ShaderNodeVertexColor')
    ca.layer_name = attr
    if image is not None:
        tx = nt.nodes.new('ShaderNodeTexImage')
        tx.image = image
        tx.interpolation = 'Linear'
        mix = nt.nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        mix.blend_type = 'MULTIPLY'
        mix.inputs['Factor'].default_value = 1.0
        nt.links.new(tx.outputs['Color'], mix.inputs['A'])
        nt.links.new(ca.outputs['Color'], mix.inputs['B'])
        nt.links.new(mix.outputs['Result'], em.inputs['Color'])
    else:
        nt.links.new(ca.outputs['Color'], em.inputs['Color'])
    nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
    m.use_backface_culling = False
    return m


def mat_export(name, image=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bs = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    bs.inputs['Metallic'].default_value = 0.0
    bs.inputs['Roughness'].default_value = 1.0
    if image is not None:
        tx = nt.nodes.new('ShaderNodeTexImage')
        tx.image = image
        nt.links.new(tx.outputs['Color'], bs.inputs['Base Color'])
    m.use_backface_culling = False
    return m


def assign(ob, mats):
    ob.data.materials.clear()
    for m in mats:
        ob.data.materials.append(m)


def materials_for(layers, mode):
    """mode 'beauty' | 'id' | 'export'."""
    for lay in layers:
        for ob in lay.objs:
            nm = ob.name
            if lay.name == 'terrain':
                if mode == 'export':
                    assign(ob, [mat_export('env_terrain_near', lay.textures['base']), mat_export('env_terrain_far')])
                elif mode == 'beauty':
                    assign(ob, [mat_unlit('b_terrain_near', lay.textures['base']), mat_unlit('b_terrain_far')])
                else:
                    assign(ob, [mat_unlit('i_terrain', None, 'ID'), mat_unlit('i_terrain', None, 'ID')])
            elif lay.name == 'hills':
                if mode == 'export':
                    assign(ob, [mat_export('env_hills', lay.textures['base'])])
                elif mode == 'beauty':
                    assign(ob, [mat_unlit('b_hills', lay.textures['base'])])
                else:
                    assign(ob, [mat_unlit('i_hills', lay.textures['id'])])
            elif lay.name == 'bushes':
                if mode == 'export':
                    assign(ob, [mat_export('env_bushes', lay.textures['base'])])
                elif mode == 'beauty':
                    assign(ob, [mat_unlit('b_bushes', lay.textures['base'])])
                else:
                    assign(ob, [mat_unlit('i_bushes', None, 'ID')])
            else:
                key = 'env_' + lay.name
                if mode == 'export':
                    m = bpy.data.materials.get(key) or mat_export(key)
                    assign(ob, [m])
                elif mode == 'beauty':
                    assign(ob, [mat_unlit('b_' + lay.name)])
                else:
                    assign(ob, [mat_unlit('i_' + lay.name, None, 'ID')])


# ----------------------------------------------------------------------------------------------
# cameras + rendering
# ----------------------------------------------------------------------------------------------
def setup_render(threads, samples):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.render.threads_mode = 'FIXED'
    sc.render.threads = threads
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.cycles.use_adaptive_sampling = False
    sc.cycles.max_bounces = 0
    sc.cycles.diffuse_bounces = 0
    sc.cycles.glossy_bounces = 0
    sc.cycles.transmission_bounces = 0
    sc.cycles.transparent_max_bounces = 0
    sc.cycles.seed = 1
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    sc.display_settings.display_device = 'sRGB'
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.image_settings.color_depth = '8'
    sc.render.film_transparent = False
    if sc.world is None:
        sc.world = bpy.data.worlds.new('W')
    sc.world.use_nodes = True
    bg = next(n for n in sc.world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (0, 0, 0, 1)
    sc.cycles.pixel_filter_type = 'BLACKMAN_HARRIS'
    sc.cycles.filter_width = 1.5


def make_camera(pos_b, look_b, vfov_deg, name='cam'):
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    cd.sensor_fit = 'VERTICAL'
    cd.sensor_height = 24.0
    cd.lens = 12.0 / math.tan(math.radians(vfov_deg) / 2)
    cd.clip_start = 0.1
    cd.clip_end = 2000.0
    ob = bpy.data.objects.get(name) or bpy.data.objects.new(name, cd)
    if ob.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(ob)
    ob.location = Vector(pos_b)
    d = Vector(look_b) - Vector(pos_b)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = ob
    return ob


def plate_cam_pose():
    pitch = math.atan((PC['horizon_row'] - PC['h'] / 2) / F_PLATE)  # >0: looking up
    look = EYE + np.array([0, math.cos(pitch), math.sin(pitch)]) * 10
    return EYE, look, PC['vfov']


def room_cam_pose(w, h):
    rc = DATA['room_camera']
    pos, tgt = g2b(rc['pos']), g2b(rc['target'])
    vf = rc['vfov']
    asp, dasp = w / h, rc['design_w'] / rc['design_h']
    if asp < dasp:
        vf = math.degrees(2 * math.atan(math.tan(math.radians(vf / 2)) * dasp / asp))
    return pos, tgt, vf


def render(path, w, h, samples=None, id_pass=False):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    if id_pass:
        sc.cycles.samples = 1
        sc.cycles.pixel_filter_type = 'BOX'
        sc.cycles.filter_width = 0.01
    else:
        sc.cycles.samples = samples or JOB.get('samples', 24)
        sc.cycles.pixel_filter_type = 'BLACKMAN_HARRIS'
        sc.cycles.filter_width = 1.5
    sc.render.filepath = path
    t = time.time()
    bpy.ops.render.render(write_still=True)
    log('rendered', os.path.basename(path), f'{w}x{h}', f'{time.time() - t:.1f}s')
    return load_img(path) if False else read_png(path)


def read_png(path):
    im = bpy.data.images.load(path, check_existing=False)
    w, h = im.size
    a = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(a)
    bpy.data.images.remove(im)
    return a.reshape(h, w, 4)[::-1, :, :3].astype(np.float64) * 255.0


def resize_nn(a, w, h):
    H, W = a.shape[:2]
    ys = (np.arange(h) * H / h).astype(int)
    xs = (np.arange(w) * W / w).astype(int)
    return a[ys][:, xs]


def resize_box(a, w, h):
    H, W = a.shape[:2]
    if H % h == 0 and W % w == 0:
        return a.reshape(h, H // h, w, W // w, 3).mean((1, 3))
    return resize_nn(a, w, h)


# ----------------------------------------------------------------------------------------------
# calibration (bake table)
# ----------------------------------------------------------------------------------------------
def erode(mask):
    m = mask.copy()
    m[1:] &= mask[:-1]
    m[:-1] &= mask[1:]
    m[:, 1:] &= mask[:, :-1]
    m[:, :-1] &= mask[:, 1:]
    return m


def measure_render(beauty, ids, SW, scale):
    """Per-class rendered mean (sRGB) over eroded class masks; lawn/sky/haze by the swatch boxes."""
    out = {}
    cls = decode_id(ids)
    for name in ['mountain', 'cloud-top', 'cloud-under', 'hill-pink', 'hill-mint', 'hill-cream', 'hill-lilac', 'icing', 'bush-mint', 'bush-green']:
        m = erode(cls == CLS[name])
        if m.sum() >= 12:
            out[name] = (beauty[m].mean(0), int(m.sum()))
    for name in ['sky-top', 'sky-mid', 'sky-horizon', 'haze', 'lawn-light', 'lawn-mid', 'lawn-dark']:
        s = DATA['swatches'][name]
        px = np.concatenate([measure_box(beauty, [int(round(v * scale)) for v in b], s['stat']) for b in s['boxes']])
        if len(px):
            out[name] = (px.mean(0), int(len(px)))
    return out


def bake_table(meas, SW):
    rows = []
    for name, sw in SW.items():
        if name not in meas:
            rows.append({'surface': name, 'baked': None, 'swatch': sw['srgb'], 'distance': None, 'n_px': 0})
            continue
        b, n = meas[name]
        dist = float(np.linalg.norm(np.asarray(b) - np.asarray(sw['srgb'])))
        rows.append({'surface': name, 'baked': [round(float(v), 1) for v in b], 'swatch': sw['srgb'], 'distance': round(dist, 2), 'n_px': n})
    return rows


GAIN_KEYS = ['mountain', 'cloud-top', 'cloud-under', 'hill-pink', 'hill-mint', 'hill-cream', 'hill-lilac', 'icing', 'bush-mint', 'bush-green']


def update_gains(G, meas, SW, terrain):
    for k in GAIN_KEYS:
        if k in meas:
            g = s2l(SW[k]['srgb']) / np.maximum(s2l(meas[k][0]), 1e-4)
            G[k] = np.clip(G.get(k, 1) * g, 0.3, 3.0)
    if 'lawn-mid' in meas:
        g = s2l(SW['lawn-mid']['srgb']) / np.maximum(s2l(meas['lawn-mid'][0]), 1e-4)
        G['lawn'] = np.clip(G.get('lawn', 1) * g, 0.3, 3.0)
    if 'lawn-light' in meas and 'lawn-dark' in meas:
        want = np.linalg.norm(np.array(SW['lawn-light']['srgb']) - SW['lawn-dark']['srgb'])
        got = np.linalg.norm(meas['lawn-light'][0] - meas['lawn-dark'][0])
        terrain.contrast = float(np.clip(terrain.contrast * want / max(got, 1.0), 0.5, 3.0))
    return G


# ----------------------------------------------------------------------------------------------
# export + check
# ----------------------------------------------------------------------------------------------
def export_glb(path):
    for ob in bpy.data.objects:
        ob.select_set(ob.name.startswith('env_'))
        if ob.type == 'MESH':
            ida = ob.data.color_attributes.get('ID')
            if ida is not None:
                ob.data.color_attributes.remove(ida)
            col = ob.data.color_attributes.get('Col')
            if col is not None:
                ob.data.color_attributes.active_color = col
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_yup=True,
                              export_apply=True, export_cameras=False, export_lights=False,
                              export_image_format='WEBP', export_image_quality=88,
                              export_vertex_color='NAME', export_vertex_color_name='Col',
                              export_all_vertex_colors=False, export_materials='EXPORT',
                              export_draco_mesh_compression_enable=False)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()


def glb_json(path):
    import struct
    with open(path, 'rb') as f:
        data = f.read()
    ln = struct.unpack('<I', data[12:16])[0]
    return json.loads(data[20:20 + ln]), data


def glb_texture_info(path):
    import struct
    j, data = glb_json(path)
    ln = struct.unpack('<I', data[12:16])[0]
    bin0 = 20 + ln + 8
    out = []
    for im in j.get('images', []):
        bv = j['bufferViews'][im['bufferView']]
        blob = data[bin0 + bv.get('byteOffset', 0): bin0 + bv.get('byteOffset', 0) + bv['byteLength']]
        w = h = None
        if blob[:4] == b'RIFF' and blob[12:16] == b'VP8 ':
            w = struct.unpack('<H', blob[26:28])[0] & 0x3FFF
            h = struct.unpack('<H', blob[28:30])[0] & 0x3FFF
        elif blob[:4] == b'RIFF' and blob[12:16] == b'VP8L':
            b = blob[21:25]
            w = 1 + (((b[1] & 0x3F) << 8) | b[0])
            h = 1 + (((b[3] & 0xF) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
        elif blob[:4] == b'RIFF' and blob[12:16] == b'VP8X':
            w = 1 + int.from_bytes(blob[24:27], 'little')
            h = 1 + int.from_bytes(blob[27:30], 'little')
        out.append({'name': im.get('name'), 'mime': im.get('mimeType'), 'px': [w, h], 'bytes': bv['byteLength']})
    return out, j


# ----------------------------------------------------------------------------------------------
# sheets
# ----------------------------------------------------------------------------------------------
FONT = None


def label(a, text, x=8, y=8):
    """Tiny 5x7 bitmap label so the sheets need no PIL."""
    glyphs = {
        'A': '01110100011000111111100011000110001', 'B': '11110100011000111110100011000111110', 'C': '01110100011000010000100001000101110',
        'D': '11110100011000110001100011000111110', 'E': '11111100001000011110100001000011111', 'F': '11111100001000011110100001000010000',
        'G': '01110100011000010111100011000101111', 'H': '10001100011000111111100011000110001', 'I': '01110001000010000100001000010001110',
        'K': '10001100101010011000101001001010001', 'L': '10000100001000010000100001000011111', 'M': '10001110111010110101100011000110001',
        'N': '10001110011010110011100011000110001', 'O': '01110100011000110001100011000101110', 'P': '11110100011000111110100001000010000',
        'R': '11110100011000111110101001001010001', 'S': '01111100001000001110000010000111110', 'T': '11111001000010000100001000010000100',
        'U': '10001100011000110001100011000101110', 'V': '10001100011000110001100010101000100', 'W': '10001100011000110101101011010101010',
        'X': '10001100010101000100010101000110001', 'Y': '10001100010101000100001000010000100', 'Z': '11111000010001000100010001000011111',
        '0': '01110100011001110101110011000101110', '1': '00100011000010000100001000010001110', '2': '01110100010000100010001000100011111',
        '3': '11110000010000101110000010000111110', '4': '00010001100101010010111110001000010', '5': '11111100001111000001000011000101110',
        '6': '01110100001000011110100011000101110', '7': '11111000010001000100010000100001000', '8': '01110100011000101110100011000101110',
        '9': '01110100011000101111000010000101110', ' ': '0' * 35, '-': '00000000000000011111000000000000000', '.': '00000000000000000000000000110001100',
        '|': '00100001000010000100001000010000100', '(': '00010001000100001000010000010000010', ')': '01000001000001000010000100010001000',
        ',': '00000000000000000000000000110000100', '/': '00001000010001000100010001000010000', 'J': '00111000100001000010100101001001100',
        'Q': '01110100011000110001101011001001101',
    }
    s = 2
    cx = x
    for ch in text.upper():
        g = glyphs.get(ch, glyphs[' '])
        for i, bit in enumerate(g):
            if bit == '1':
                yy, xx = y + (i // 5) * s, cx + (i % 5) * s
                a[yy:yy + s, xx:xx + s] = [20, 20, 30]
        cx += 6 * s
    return a


# ----------------------------------------------------------------------------------------------
# modes
# ----------------------------------------------------------------------------------------------
def clean_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)


def mode_build():
    clean_scene()
    os.makedirs(JOB['render_dir'], exist_ok=True)
    setup_render(JOB['threads'], JOB.get('calib_samples', 8))
    SW = measure_swatches()
    for k, v in SW.items():
        log('swatch', k, v['srgb'])
    grad = sky_gradient()
    layers = []
    t = time.time()
    layers.append(build_sky(SW, grad))
    layers.append(build_mountains(SW))
    clouds = build_clouds(SW)
    layers.append(clouds)
    log('clouds built', f'{time.time() - t:.1f}s')
    hills = build_hills(SW)  # registers the hill swells before the terrain samples heights
    layers.append(hills)
    bushes = build_bushes(SW)
    layers.append(bushes)
    terrain = build_terrain(SW)
    layers.append(terrain)
    log('layers built', f'{time.time() - t:.1f}s')
    G = {}
    cw, ch = PC['w'] // 2, PC['h'] // 2
    scale = 0.5
    pos, look, vf = plate_cam_pose()
    make_camera(pos, look, vf)
    calib = []
    iters = JOB.get('calib_iters', 2)
    for it in range(iters + 1):
        for lay in layers:
            lay.paint(G)
        materials_for(layers, 'beauty')
        b = render(os.path.join(LANE, f'calib_{it}.png'), cw, ch, JOB.get('calib_samples', 8))
        if it == 0:
            materials_for(layers, 'id')
            ids = render(os.path.join(LANE, 'calib_id.png'), cw, ch, id_pass=True)
        meas = measure_render(b, ids, SW, scale)
        table = bake_table(meas, SW)
        worst = max((r['distance'] or 0) for r in table)
        calib.append({'iter': it, 'worst': worst, 'contrast': terrain.contrast})
        log('calib iter', it, 'worst', round(worst, 2), [(r['surface'], r['distance']) for r in table])
        if it == 0:
            draft = np.concatenate([resize_box(load_img(PC['img']), cw, ch), b], 1)
            save_png_srgb(label(draft.copy(), 'PLATE-V4 | ENV DRAFT (PLATE CAMERA)'), os.path.join(JOB['render_dir'], 'draft-plate-match.jpg'))
        if it < iters:
            G = update_gains(G, meas, SW, terrain)
    # final paint is the one measured last; export
    materials_for(layers, 'export')
    tris = {}
    for lay in layers:
        tris['env_' + lay.name] = int(sum(tri_count(ob.data) for ob in lay.objs))
    export_glb(JOB['out_glb'])
    texinfo, gj = glb_texture_info(JOB['out_glb'])
    env = {
        'glb': os.path.relpath(JOB['out_glb'], REPO),
        'bytes': os.path.getsize(JOB['out_glb']),
        'sha256': sha256(JOB['out_glb']),
        'triangles': tris,
        'textures': texinfo,
        'swatches': SW,
        'bake_table': table,
        'bake_route': 'analytic param-space/vertex bake: albedo from the swatch x stylised light (warm key + sky fill + analytic sphere AO) + aerial haze; per-surface gain calibrated so the plate-camera render mean lands on the swatch (Cycles emission render = unlit runtime)',
        'calibration': {'gains': {k: [round(float(x), 4) for x in np.atleast_1d(v)] for k, v in G.items()}, 'iterations': calib, 'render_px': [cw, ch]},
        'plate_camera': {'pos_gltf': DATA['eye_gltf'], 'target_gltf': [float(look[0]), float(look[2]), float(-look[1])], 'vfov': vf,
                         'image': PLATES + PC['img'], 'horizon_row': PC['horizon_row'], 'note': 'fitted: horizon row 474/941 (sky peach peak + lavender mountain base at x 960), vfov 40 makes the left/right swirl tips land at their plate pixels'},
        'room_camera': DATA['room_camera'],
        'clouds': [{'node': inf['obj'].name, 'centre_gltf': [round(float(inf['center'][0]), 2), round(float(inf['center'][2]), 2), round(float(-inf['center'][1]), 2)],
                    'radius': round(float(inf['W'] / 2), 1)} for inf in clouds.infos],
        'hills': len(hills.specs),
        'flat_zone': {'r': DATA['flat_r'], 'corridor_gltf': DATA['corridor'], 'y': 0.0},
        'seed': SEED,
        'runtime_contract': 'every mesh under env_* renders unlit: MeshBasicMaterial(map=baseColorTexture sRGB, vertexColors=COLOR_0 multiplied), toneMapped false, fog false, side DoubleSide; camera far >= 1000',
        'data': {k: DATA[k] for k in ('clouds', 'hills', 'mountain_peaks', 'mountain_rings', 'terrain_radius', 'terrain_near_r', 'grass_tile_m', 'sky_radius')},
    }
    with open(JOB['out_json'], 'w') as f:
        json.dump(env, f, indent=1)
    log('exported', env['bytes'], 'bytes', sum(tris.values()), 'tris', tris)


def unlit_from_import():
    """Re-imported GLB -> emission materials = map x COLOR_0 (what MeshBasicMaterial shows)."""
    for ob in bpy.data.objects:
        if ob.type != 'MESH':
            continue
        me = ob.data
        cname = me.color_attributes[0].name if len(me.color_attributes) else None
        for i, slot in enumerate(ob.material_slots):
            m = slot.material
            img = None
            if m and m.node_tree:
                tx = next((n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE'), None)
                img = tx.image if tx else None
            nm = mat_unlit('u_' + (m.name if m else ob.name), img, cname or 'Col')
            if cname is None:
                ca = next(n for n in nm.node_tree.nodes if n.type == 'VERTEX_COLOR')
                ca.layer_name = ''
            slot.material = nm


def mode_check():
    clean_scene()
    for m in list(bpy.data.meshes):
        bpy.data.meshes.remove(m)
    setup_render(JOB['threads'], JOB.get('samples', 24))
    glb = JOB['out_glb']
    bpy.ops.import_scene.gltf(filepath=glb)
    names = {ob.name: ob for ob in bpy.data.objects}
    report = {'ok': True, 'problems': []}
    for n in ['env_sky', 'env_mountains', 'env_clouds', 'env_hills', 'env_bushes', 'env_terrain']:
        if n not in names:
            report['problems'].append('missing node ' + n)
    kids = sorted(o.name for o in bpy.data.objects if o.parent and o.parent.name == 'env_clouds')
    report['cloud_nodes'] = kids
    if not (8 <= len(kids) <= 14) or not all(k.startswith('env_cloud_') for k in kids):
        report['problems'].append('cloud children ' + str(kids))
    # flat zone: raycast the terrain at 12 points (gltf x, z) -> blender (x, -z)
    ter = names.get('env_terrain')
    pts = [(0, 0), (5, 5), (-7, -6), (9.5, 0), (0, -9.5), (-6.5, 6.5), (7.9, 10), (-7.9, 15.9), (0, 16), (4, 13), (-3, 2), (6, -7.5)]
    hs = []
    dg = bpy.context.evaluated_depsgraph_get()
    mw = ter.matrix_world
    inv = mw.inverted()
    for gx, gz in pts:
        o = inv @ Vector((gx, -gz, 50.0))
        dvec = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
        hit, loc, nor, idx = ter.ray_cast(o, dvec)
        y = (mw @ loc).z if hit else None
        hs.append([gx, gz, None if y is None else round(y, 5)])
        if y is None or abs(y) > 0.005:
            report['problems'].append(f'flat zone height {gx},{gz}: {y}')
    report['flat_samples_gltf_x_z_y'] = hs
    tris = {}
    for ob in bpy.data.objects:
        if ob.type == 'MESH':
            tris[ob.name] = tri_count(ob.data)
    report['triangles'] = tris
    report['triangles_total'] = sum(tris.values())
    report['bytes'] = os.path.getsize(glb)
    texinfo, gj = glb_texture_info(glb)
    report['textures'] = texinfo
    prim_attrs = sorted({k for m in gj['meshes'] for p in m['primitives'] for k in p['attributes']})
    report['primitive_attributes'] = prim_attrs
    report['cameras_lights'] = [len(gj.get('cameras', [])), len(gj.get('extensions', {}).get('KHR_lights_punctual', {}).get('lights', []))]
    if report['bytes'] > 8e6:
        report['problems'].append('glb > 8 MB')
    if report['triangles_total'] > 150000:
        report['problems'].append('triangles > 150k')
    for t in texinfo:
        if t['mime'] != 'image/webp':
            report['problems'].append('texture not webp ' + str(t))
    report['ok'] = not report['problems']
    log('check', json.dumps({k: report[k] for k in ('ok', 'problems', 'cloud_nodes', 'triangles_total', 'bytes', 'primitive_attributes')}))
    unlit_from_import()
    rd = JOB['render_dir']
    os.makedirs(rd, exist_ok=True)
    # plate match (full plate resolution)
    pos, look, vf = plate_cam_pose()
    make_camera(pos, look, vf)
    W, H = (PC['w'], PC['h']) if not JOB.get('quick') else (PC['w'] // 2, PC['h'] // 2)
    b = render(os.path.join(LANE, 'plate_cam.png'), W, H)
    plate = load_img(PC['img'])
    if JOB.get('quick'):
        plate = resize_box(plate, W, H)
    sheet = np.concatenate([plate, b], 1)
    save_png_srgb(label(sheet.copy(), 'PLATE-V4  |  ENV.GLB UNLIT, PLATE CAMERA (EYE 0,3.4,12.5  VFOV 40)'), os.path.join(rd, 'plate-match.jpg'))
    # horizon/sky check rows (plate vs render)
    col = slice(int(955 * W / PC['w']), int(995 * W / PC['w']))
    hz = []
    for r in (0, 120, 240, 330, 400, 440, 460):
        rr = int(r * H / PC['h'])
        hz.append({'row': r, 'plate': [round(float(v)) for v in plate[rr, col].mean(0)], 'render': [round(float(v)) for v in b[rr, col].mean(0)]})
    report['sky_rows'] = hz
    for (w, h, nm) in ((844, 390, 'room-844.jpg'), (1280, 800, 'room-1280.jpg')):
        pos, tgt, vf = room_cam_pose(w, h)
        make_camera(pos, tgt, vf)
        img = render(os.path.join(LANE, nm.replace('.jpg', '.png')), w, h)
        save_png_srgb(label(img.copy(), f'ROOM CAMERA {w}X{h}  VFOV {vf:.1f}'), os.path.join(rd, nm))
    # 360: front/right/back/left from the eye, 90 deg horizontal each
    tiles = []
    for yaw, nm in ((0, 'FRONT (-Z)'), (90, 'RIGHT (+X)'), (180, 'BACK (+Z)'), (270, 'LEFT (-X)')):
        d = np.array([math.sin(math.radians(yaw)), math.cos(math.radians(yaw)), -math.tan(math.radians(4))])
        vf = math.degrees(2 * math.atan(math.tan(math.radians(45)) * 400 / 640))
        make_camera(EYE, EYE + d * 10, vf)
        tiles.append(label(render(os.path.join(LANE, f'wide_{yaw}.png'), 640, 400), nm))
    wide = np.concatenate([np.concatenate(tiles[:2], 1), np.concatenate(tiles[2:], 1)], 0)
    save_png_srgb(wide, os.path.join(rd, 'wide.jpg'))
    with open(os.path.join(LANE, 'check.json'), 'w') as f:
        json.dump(report, f, indent=1)
    # merge into env.json
    if os.path.exists(JOB['out_json']):
        env = json.load(open(JOB['out_json']))
        env['reimport_check'] = report
        with open(JOB['out_json'], 'w') as f:
            json.dump(env, f, indent=1)
    log('check done ok=', report['ok'])
    if not report['ok']:
        sys.exit(3)


if __name__ == '__main__':
    try:
        {'build': mode_build, 'check': mode_check}[JOB['mode']]()
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(2)
