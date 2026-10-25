// Pure layout helpers shared by world.mjs, main.mjs and the selftest (no three.js import).
export const MIN_GAP_M = 0.3;

/** True when (x, z) lies on the cookie path (props.json island.path) widened by `pad`. */
export function onPath(x, z, path, pad = 0) {
  const [fx, fz] = path.from; const [tx, tz] = path.to;
  const dx = tx - fx; const dz = tz - fz; const L2 = dx * dx + dz * dz;
  const k = Math.max(0, Math.min(1, ((x - fx) * dx + (z - fz) * dz) / L2));
  return Math.hypot(x - (fx + dx * k), z - (fz + dz * k)) < path.r + path.wobble + pad;
}

/** Ground props (not floating, not in the sky) with their footprint circle. */
export function groundFootprints(props) {
  return props.filter((p) => !p.sky && !p.y).map((p) => ({ id: p.id, x: p.pos[0], z: p.pos[1], r: p.footprint_m ?? p.height_m * 0.5 }));
}

/** Vertical fov for an aspect: landscape keeps the design aspect's HORIZONTAL field (narrower screens see more sky and
 * ground, never lose the island sides); portrait uses fov_portrait. Same rule in main.mjs resize(). */
export function verticalFov(cam, aspect) {
  if (aspect < 1) return cam.fov_portrait;
  const design = cam.design_aspect || aspect;
  if (aspect >= design) return cam.fov_landscape;
  const t = Math.tan((cam.fov_landscape * Math.PI) / 360) * (design / aspect);
  return (Math.atan(t) * 360) / Math.PI;
}

/** Pure perspective projection (same maths as THREE.PerspectiveCamera.lookAt + project): returns NDC [x, y]. */
export function projector(cam, aspect) {
  const c = cam.pos; const t = cam.target;
  let f = [t[0] - c[0], t[1] - c[1], t[2] - c[2]]; const l = Math.hypot(...f); f = f.map((v) => v / l);
  let r = [-f[2], 0, f[0]]; const rl = Math.hypot(...r); r = r.map((v) => v / rl);
  const u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]];
  const th = Math.tan((verticalFov(cam, aspect) * Math.PI) / 360);
  return (p) => {
    const d = [p[0] - c[0], p[1] - c[1], p[2] - c[2]];
    const z = d[0] * f[0] + d[1] * f[1] + d[2] * f[2];
    return [(d[0] * r[0] + d[1] * r[1] + d[2] * r[2]) / z / th / aspect, (d[0] * u[0] + d[1] * u[1] + d[2] * u[2]) / z / th, z];
  };
}

/** Share of the frame height an upright object (base y0, height h at x, z) covers, and whether it is inside |NDC| <= 0.95. */
export function frameShare(P, x, y0, z, h) {
  const a = P([x, y0, z]); const b = P([x, y0 + h, z]);
  return { frac: Math.abs(b[1] - a[1]) / 2, inFrame: Math.min(a[1], b[1]) >= -0.96 && Math.max(a[1], b[1]) <= 0.96 && Math.abs(a[0]) <= 0.96 && Math.abs(b[0]) <= 0.96 };
}

/** NDC margin from every frame edge for tappable objects (4% of the frame = 0.08 in NDC). */
export const EDGE_MARGIN_NDC = 0.08;
/** Max share of an object's screen box that a nearer object's screen box may cover. */
export const MAX_COVER = 0.2;

/** Screen bbox of an upright object: half width hw (x) and half depth hd (z), height h from y0; depth = camera-space z. */
export function screenBox(P, x, y0, z, h, hw, hd = hw) {
  let x0 = Infinity; let x1 = -Infinity; let yb = Infinity; let yt = -Infinity;
  for (const dx of [-hw, hw]) for (const dz of [-hd, hd]) for (const y of [y0, y0 + h]) {
    const q = P([x + dx, y, z + dz]);
    x0 = Math.min(x0, q[0]); x1 = Math.max(x1, q[0]); yb = Math.min(yb, q[1]); yt = Math.max(yt, q[1]);
  }
  return { x0, x1, y0: yb, y1: yt, depth: P([x, y0 + h / 2, z])[2] };
}

/** Tappable objects of a props.json as {id, x, y0, z, h, r}. */
export function tappables(props) {
  const half = (o) => o.half_wd || [o.footprint_m ?? o.height_m * 0.5, o.footprint_m ?? o.height_m * 0.5];
  const out = props.props.map((p) => ({ id: p.id, x: p.pos[0], y0: p.y || 0, z: p.pos[1], h: p.height_m, hw: half(p)[0], hd: half(p)[1] }));
  out.push({ id: 'moa', x: props.moa.start[0], y0: 0, z: props.moa.start[1], h: props.moa.height_m, hw: half(props.moa)[0], hd: half(props.moa)[1] });
  return out;
}

/** Cotton-candy tree canopy lumps [dx, y, dz, r] in tree units (world.mjs builds the trees from this; scaled by set.tree_scale). */
export const TREE_LUMPS = [[0, 1.45, 0, 0.55], [-0.38, 1.2, 0.1, 0.42], [0.36, 1.25, -0.08, 0.44]];

/** Non-tappable set pieces that can hide a tappable (canopies, fences) as {id, x, y0, z, h, hw, hd}; trunks are too thin to count. */
export function setOccluders(props) {
  const set = props.set || {}; const k = set.tree_scale || 1; const out = [];
  const lo = Math.min(...TREE_LUMPS.map(([, y, , r]) => y - r)); const hi = Math.max(...TREE_LUMPS.map(([, y, , r]) => y + r));
  const hw = Math.max(...TREE_LUMPS.map(([dx, , , r]) => Math.abs(dx) + r)); const hd = Math.max(...TREE_LUMPS.map(([, , dz, r]) => Math.abs(dz) + r));
  for (const [x, z] of set.trees || []) out.push({ id: `tree(${x},${z})`, x, y0: lo * k, z, h: (hi - lo) * k, hw: hw * k, hd: hd * k });
  for (const f of set.fences || []) out.push({ id: `fence(${f.x0}..${f.x1})`, x: (f.x0 + f.x1) / 2, y0: 0, z: f.z, h: f.h, hw: Math.abs(f.x1 - f.x0) / 2, hd: 0.06 });
  return out;
}

/** Edge-margin and occlusion problems at one aspect; [] when clean. Occluders = nearer tappables AND set pieces (setOccluders):
 * 2026-10-25 the sky-island (episode theatre) sat 100% behind a tree while this gate, counting tappables only, passed. */
export function framingProblems(props, aspect) {
  const P = projector(props.camera, aspect);
  const items = tappables(props).map((t) => ({ ...t, box: screenBox(P, t.x, t.y0, t.z, t.h, t.hw, t.hd) }));
  const blockers = [...items, ...setOccluders(props).map((t) => ({ ...t, box: screenBox(P, t.x, t.y0, t.z, t.h, t.hw, t.hd) }))];
  const lim = 1 - EDGE_MARGIN_NDC;
  const bad = [];
  for (const a of items) {
    const b = a.box;
    if (b.x0 < -lim || b.x1 > lim || b.y0 < -lim || b.y1 > lim) bad.push(`${a.id} edge [${b.x0.toFixed(2)},${b.x1.toFixed(2)}]x[${b.y0.toFixed(2)},${b.y1.toFixed(2)}]`);
    const area = (b.x1 - b.x0) * (b.y1 - b.y0);
    for (const o of blockers) {
      if (o === a || o.box.depth >= b.depth) continue;
      const w = Math.min(b.x1, o.box.x1) - Math.max(b.x0, o.box.x0); const h = Math.min(b.y1, o.box.y1) - Math.max(b.y0, o.box.y0);
      if (w > 0 && h > 0 && (w * h) / area > MAX_COVER) bad.push(`${a.id} covered ${((w * h) / area * 100).toFixed(0)}% by ${o.id}`);
    }
  }
  return bad;
}
