// Scoop Sky procedural set: elevation-keyed sky, floating whipped-cream island, cookie path, wafer fences,
// cotton-candy trees, drifting cream clouds, plus the procedural stand-ins used when a prop GLB is missing.
// Clouds are white cream with a pink blush, never yellow or beige.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { SPRINKLES } from './anim.mjs';
import { onPath, TREE_LUMPS } from './layout.mjs';

export const PALETTE = {
  skyTop: 0x7fc3ff, skyHorizon: 0xfff0e2, skyBelow: 0xffe4ee,
  grass: 0xa6dc84, underside: 0xfff6ee, rimBlob: 0xfffaf6, rimBlush: 0xffd9e4,
  cookie: 0xe9b77a, waferPost: 0xf6d9a8, waferRail: 0xf7b6c8,
  pretzel: 0xc98a4b, candyPink: 0xffc2d6, candyMint: 0xbfe9d6,
  cloud: 0xfffaf7, cloudBlush: 0xffe3ec, sun: 0xffd76a, sunSwirl: 0xffc24a, face: 0x7a4a2a,
  cream: 0xffffff, creamGlow: 0xfff3ec, blush: 0xffd6e2, blushGlow: 0xffe6ee,
  grassCentre: 0xb6e59a, grassEdge: 0x9fd884,
};
// Whipped cream must read white under any light: a soft self-glow and a matte surface (main's v2 capture: plain lit
// spheres went grey). One definition for the rim, underside, clouds and stand-in clouds.
export const creamMat = () => new THREE.MeshStandardMaterial({ color: PALETTE.cream, emissive: PALETTE.creamGlow, emissiveIntensity: 0.42, roughness: 0.85, metalness: 0 });
/** Texture-faithful GLB colour: base-colour factor = shade.mjs lightNeutralMult, plus a flat white emissive equal to the
 * 0.04 the Neutral tone map subtracts (props.json look). Idempotent (sets, never multiplies). */
export function calibrateLook(root, mult, offset) {
  root.traverse((o) => {
    if (!o.isMesh) return;
    for (const m of [].concat(o.material)) {
      if (!m || !m.color) continue;
      m.color.setRGB(...mult, THREE.LinearSRGBColorSpace);
      if (m.emissive) { m.emissive.setRGB(1, 1, 1); m.emissiveIntensity = offset; }
    }
  });
  return root;
}
export const blushMat = () => new THREE.MeshStandardMaterial({ color: PALETTE.blush, emissive: PALETTE.blushGlow, emissiveIntensity: 0.35, roughness: 0.85, metalness: 0 });
const ROUGH = 0.55;
export const std = (color, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness: ROUGH, metalness: 0, ...extra });

export function mulberry(seed) {
  let a = seed >>> 0;
  return () => { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

export const DOME = 0.12;
export function groundY(x, z, radius = 6) {
  const r2 = (x * x + z * z) / (radius * radius);
  return r2 >= 1 ? 0 : DOME * (1 - r2);
}

let shadowTex = null;
/** Radial falloff alpha texture computed in code (no canvas, no DOM): a soft green-grey blob. */
function radialTexture() {
  if (shadowTex) return shadowTex;
  const N = 64;
  const data = new Uint8Array(N * N * 4);
  for (let y = 0; y < N; y++) {
    for (let x = 0; x < N; x++) {
      const d = Math.min(1, Math.hypot(x + 0.5 - N / 2, y + 0.5 - N / 2) / (N / 2));
      const a = d < 0.6 ? 0.55 - (0.3 * d) / 0.6 : 0.25 * (1 - (d - 0.6) / 0.4);
      data.set([60, 90, 60, Math.round(255 * Math.max(0, a))], (y * N + x) * 4);
    }
  }
  shadowTex = new THREE.DataTexture(data, N, N);
  shadowTex.colorSpace = THREE.SRGBColorSpace;
  shadowTex.needsUpdate = true;
  return shadowTex;
}

/** Soft blob shadow disc (no shadow maps in this runtime). */
export function blobShadow(radius, opacity = 0.5) {
  const m = new THREE.Mesh(new THREE.CircleGeometry(radius, 24), new THREE.MeshBasicMaterial({
    map: radialTexture(), transparent: true, opacity, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2,
  }));
  m.rotation.x = -Math.PI / 2;
  m.renderOrder = 1;
  m.name = 'blob-shadow';
  return m;
}

/** Sky sphere coloured by view elevation from `eye`: blue at -5 deg and above, cream at -35 deg, blush below. */
function buildSky(eye, blueDeg = -5, creamDeg = -35) {
  const R = 90;
  const geo = new THREE.SphereGeometry(R, 48, 48);
  const pos = geo.attributes.position;
  const col = new Float32Array(pos.count * 3);
  const top = new THREE.Color(PALETTE.skyTop);
  const hor = new THREE.Color(PALETTE.skyHorizon);
  const below = new THREE.Color(PALETTE.skyBelow);
  const c = new THREE.Color();
  for (let i = 0; i < pos.count; i++) {
    const el = THREE.MathUtils.radToDeg(Math.asin(pos.getY(i) / R));
    if (el >= blueDeg) c.copy(top).lerp(new THREE.Color(0x5fb0f5), Math.min(1, (el - blueDeg) / 40));
    else if (el >= creamDeg) c.copy(hor).lerp(top, THREE.MathUtils.smoothstep(el, creamDeg, blueDeg));
    else c.copy(below).lerp(hor, THREE.MathUtils.smoothstep(el, -90, creamDeg));
    col.set([c.r, c.g, c.b], i * 3);
  }
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  const sky = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide, depthWrite: false, toneMapped: false, fog: false }));
  sky.position.copy(eye);
  sky.renderOrder = -10;
  sky.name = 'sky';
  return sky;
}

function cloudGeometry(rand, lumps) {
  const parts = [];
  for (let i = 0; i < lumps; i++) {
    const r = 0.55 + rand() * 0.45;
    const g = new THREE.SphereGeometry(r, 16, 12);
    g.scale(1, 0.78, 0.9);
    g.translate((i - (lumps - 1) / 2) * 0.75 + (rand() - 0.5) * 0.2, (rand() - 0.3) * 0.35, (rand() - 0.5) * 0.4);
    parts.push(g);
  }
  return mergeGeometries(parts);
}

const cloudMat = creamMat;

/** Builds the whole static set into `scene` from props.json (island + set blocks); returns pick target and tick. */
export function buildWorld(scene, { eye, island, set, sky = {}, avoid = [] }) {
  const radius = island.radius_m;
  const rand = mulberry(20261025);
  const world = new THREE.Group();
  world.name = 'scoop-world';
  scene.add(world);
  scene.add(buildSky(eye, sky.blue_deg, sky.cream_deg));

  // ---- island top (slight dome) with a centre->edge grass gradient in vertex colours
  const prof = [];
  for (let i = 0; i <= 12; i++) { const r = (radius * i) / 12; prof.push(new THREE.Vector2(r, groundY(r, 0, radius))); }
  prof.push(new THREE.Vector2(radius, -0.18));
  const topGeo = new THREE.LatheGeometry(prof.reverse(), 72);
  const gp = topGeo.attributes.position;
  const gc = new Float32Array(gp.count * 3);
  const cIn = new THREE.Color(PALETTE.grassCentre); const cOut = new THREE.Color(PALETTE.grassEdge); const cc = new THREE.Color();
  for (let i = 0; i < gp.count; i++) {
    cc.copy(cIn).lerp(cOut, THREE.MathUtils.smoothstep(Math.hypot(gp.getX(i), gp.getZ(i)) / radius, 0.15, 1));
    gc.set([cc.r, cc.g, cc.b], i * 3);
  }
  topGeo.setAttribute('color', new THREE.BufferAttribute(gc, 3));
  const top = new THREE.Mesh(topGeo, std(0xffffff, { vertexColors: true }));
  top.name = 'island-top';
  world.add(top);
  // ---- cream underside cone + whipped lumps (sizes follow the island radius)
  const k6 = radius / 6;
  const cream = creamMat();
  const blush = blushMat();
  const under = new THREE.Mesh(new THREE.ConeGeometry(radius * 0.98, 3.4 * k6, 40, 1, true), cream);
  under.rotation.x = Math.PI;
  under.position.y = -1.7 * k6 - 0.16;
  world.add(under);
  const lumpGeo = new THREE.SphereGeometry(1, 18, 14);
  for (const [ringR, y, r, n] of [[4.9, -0.75, 1.25, 11], [3.2, -1.9, 1.05, 8], [1.4, -3.0, 0.8, 4]]) {
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2 + rand() * 0.3;
      const m = new THREE.Mesh(lumpGeo, cream);
      m.position.set(Math.cos(a) * ringR * k6, (y + (rand() - 0.5) * 0.3) * k6, Math.sin(a) * ringR * k6);
      m.scale.setScalar(r * k6 * (0.85 + rand() * 0.3));
      world.add(m);
    }
  }
  // ---- 26 whipped-cream blobs ON the rim (centre on the rim line = half embedded), every third blushed
  for (let i = 0; i < 26; i++) {
    const a = (i / 26) * Math.PI * 2;
    const m = new THREE.Mesh(lumpGeo, i % 3 === 2 ? blush : cream);
    const s = 0.25 + rand() * 0.09;
    m.scale.set(s, s * 0.7, s);
    m.position.set(Math.cos(a) * radius, 0, Math.sin(a) * radius);
    world.add(m);
  }
  // ---- cookie-stone path from the front to the cottage door
  const path = island.path;
  const cookieMat = std(PALETTE.cookie);
  for (let i = 0; i < path.stones; i++) {
    const k = i / (path.stones - 1);
    const z = path.from[1] + (path.to[1] - path.from[1]) * k;
    const x = path.from[0] + (path.to[0] - path.from[0]) * k + Math.sin(k * Math.PI * 1.5) * path.wobble;
    const r = path.r * (1.08 - k * 0.16);
    const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r * 1.04, 0.07, 20), cookieMat);
    m.position.set(x, groundY(x, z, radius) + 0.02, z);
    m.rotation.y = rand() * Math.PI;
    world.add(m);
  }
  // ---- 60 sprinkles lying flat on the grass (never on the path, never under a prop)
  const spr = set.sprinkles;
  const sGeo = new THREE.CapsuleGeometry(0.022, spr.length_m - 0.044, 3, 6);
  sGeo.rotateZ(Math.PI / 2);
  const sMesh = new THREE.InstancedMesh(sGeo, std(0xffffff, { roughness: 0.5 }), spr.count);
  const m4 = new THREE.Matrix4(); const q = new THREE.Quaternion(); const one = new THREE.Vector3(1, 1, 1); const Y = new THREE.Vector3(0, 1, 0);
  const sr = mulberry(spr.seed);
  let placed = 0; let guard = 0;
  while (placed < spr.count && guard++ < 5000) {
    const a = sr() * Math.PI * 2; const rr = Math.sqrt(sr()) * (radius - 0.45);
    const x = Math.cos(a) * rr; const z = Math.sin(a) * rr;
    if (onPath(x, z, path, 0.12) || avoid.some((c) => Math.hypot(x - c.x, z - c.z) < c.r + 0.1)) continue;
    q.setFromAxisAngle(Y, sr() * Math.PI);
    sMesh.setMatrixAt(placed, m4.compose(new THREE.Vector3(x, groundY(x, z, radius) + 0.02, z), q, one));
    sMesh.setColorAt(placed, cc.set(SPRINKLES[placed % SPRINKLES.length]));
    placed++;
  }
  sMesh.count = placed;
  sMesh.name = 'grass-sprinkles';
  world.add(sMesh);
  // ---- wafer fences left and right of the cottage
  const postMat = std(PALETTE.waferPost);
  const railMat = std(PALETTE.waferRail);
  for (const f of set.fences) {
    const n = Math.max(2, Math.round(Math.abs(f.x1 - f.x0) / 0.4) + 1);
    for (let i = 0; i < n; i++) {
      const x = f.x0 + ((f.x1 - f.x0) * i) / (n - 1);
      const p = new THREE.Mesh(new THREE.BoxGeometry(0.1, f.h, 0.1), postMat);
      p.position.set(x, groundY(x, f.z, radius) + f.h / 2, f.z);
      world.add(p);
    }
    for (const y of [0.36, 0.75]) {
      const rail = new THREE.Mesh(new THREE.BoxGeometry(Math.abs(f.x1 - f.x0) + 0.1, 0.07, 0.05), railMat);
      rail.position.set((f.x0 + f.x1) / 2, groundY((f.x0 + f.x1) / 2, f.z, radius) + f.h * y, f.z + 0.06);
      world.add(rail);
    }
  }
  // ---- cotton-candy trees at the back
  const trunkMat = std(PALETTE.pretzel);
  const candy = [std(PALETTE.candyPink), std(PALETTE.candyMint)];
  for (const [x, z, c0] of set.trees) {
    const t = new THREE.Group();
    t.position.set(x, groundY(x, z, radius), z);
    t.scale.setScalar(set.tree_scale);
    const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.11, 1.15, 10), trunkMat);
    trunk.position.y = 0.57;
    t.add(trunk);
    const twist = new THREE.Mesh(new THREE.TorusGeometry(0.12, 0.035, 8, 16), trunkMat);
    twist.position.y = 0.55; twist.rotation.x = Math.PI / 2;
    t.add(twist);
    TREE_LUMPS.forEach(([dx, y, dz, r], i) => {
      const s = new THREE.Mesh(lumpGeo, candy[(c0 + i) % 2]);
      s.position.set(dx, y, dz); s.scale.setScalar(r);
      t.add(s);
    });
    const sh = blobShadow(0.75, 0.45); sh.position.y = 0.012; t.add(sh);
    world.add(t);
  }
  // ---- 12 cream clouds in the sky band, all behind the island (z <= -12): they can never cover it
  const clouds = [];
  for (let i = 0; i < set.clouds.length; i++) {
    const [x, y, z, sc] = set.clouds[i];
    const m = new THREE.Mesh(cloudGeometry(rand, 3 + (i % 3)), cloudMat());
    m.position.set(x, y, z);
    m.scale.setScalar(sc);
    m.userData.speed = 0.05 * (0.7 + rand() * 0.6);
    m.name = 'drift-cloud';
    world.add(m);
    clouds.push(m);
  }
  const wrap = set.cloud_wrap_x;
  function tick(dt) {
    for (const c of clouds) {
      c.position.x += c.userData.speed * dt;
      if (c.position.x > wrap) c.position.x = -wrap;
    }
  }
  return { world, ground: top, tick };
}

/** Scale/centre any object so its base sits at y=0, centred on XZ, `height` metres tall. */
export function fitToHeight(obj, height) {
  obj.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(obj);
  const size = box.getSize(new THREE.Vector3());
  if (size.y > 1e-6) obj.scale.multiplyScalar(height / size.y);
  obj.updateMatrixWorld(true);
  box.setFromObject(obj);
  const c = box.getCenter(new THREE.Vector3());
  obj.position.x -= c.x; obj.position.z -= c.z; obj.position.y -= box.min.y;
  return obj;
}

// ------------------------------------------------------------------ stand-ins (sheet colours, unit-free; fitted after)
const eye = (mat, r = 0.05) => { const m = new THREE.Mesh(new THREE.SphereGeometry(r, 12, 10), mat); m.scale.set(0.8, 1.2, 0.5); return m; };

const BUILDERS = {
  cottage(color) {
    const g = new THREE.Group(); const parts = {};
    const walls = new THREE.Mesh(new THREE.BoxGeometry(1.9, 1.3, 1.6), std(0xfff1e6));
    walls.position.y = 0.65; g.add(walls);
    const roof = new THREE.Mesh(new THREE.ConeGeometry(1.6, 1.0, 4), std(color));
    roof.position.y = 1.8; roof.rotation.y = Math.PI / 4; roof.scale.z = 0.85; g.add(roof);
    const drip = new THREE.Mesh(new THREE.TorusGeometry(1.12, 0.09, 8, 4), std(0xffffff));
    drip.rotation.x = Math.PI / 2; drip.rotation.z = Math.PI / 4; drip.position.y = 1.32; drip.scale.y = 0.85; g.add(drip);
    const hinge = new THREE.Group(); hinge.position.set(-0.32, 0, 0.81);
    const door = new THREE.Mesh(new THREE.BoxGeometry(0.64, 0.92, 0.06), std(PALETTE.pretzel));
    door.position.set(0.32, 0.46, 0); hinge.add(door);
    const knob = new THREE.Mesh(new THREE.SphereGeometry(0.045, 10, 8), std(0xffd84d)); knob.position.set(0.54, 0.46, 0.05); hinge.add(knob);
    g.add(hinge); parts.door = hinge;
    for (const x of [-0.65, 0.65]) { const w = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.36, 0.05), std(0xbfe6ff, { emissive: 0xbfe6ff, emissiveIntensity: 0.2 })); w.position.set(x, 0.85, 0.81); g.add(w); }
    const chim = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.5, 0.26), std(PALETTE.waferPost)); chim.position.set(0.5, 2.0, -0.25); g.add(chim); parts.chimney = chim;
    return { group: g, parts };
  },
  mailbox(color) {
    const g = new THREE.Group(); const parts = {};
    const post = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.06, 0.62, 10), std(PALETTE.waferPost)); post.position.y = 0.31; g.add(post);
    const box = new THREE.Mesh(new THREE.BoxGeometry(0.46, 0.34, 0.6), std(color)); box.position.y = 0.79; g.add(box);
    const lid = new THREE.Group(); lid.position.set(0, 0.96, -0.3);
    const lidM = new THREE.Mesh(new THREE.CylinderGeometry(0.23, 0.23, 0.62, 16, 1, false, 0, Math.PI), std(0xfff1e6));
    lidM.rotation.z = Math.PI / 2; lidM.rotation.y = Math.PI / 2; lidM.position.z = 0.3; lid.add(lidM);
    g.add(lid); parts.lid = lid;
    const flag = new THREE.Group(); flag.position.set(0.25, 0.72, 0.1);
    const stick = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.03, 0.03), std(0x8a5a3c)); stick.position.x = 0.16; flag.add(stick);
    const cloth = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.1, 0.02), std(0xff6f91)); cloth.position.set(0.28, 0.06, 0); flag.add(cloth);
    g.add(flag); parts.flag = flag;
    return { group: g, parts };
  },
  pinwheel() {
    const g = new THREE.Group(); const parts = {};
    const stick = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.045, 0.85, 10), std(PALETTE.waferPost)); stick.position.y = 0.43; g.add(stick);
    const bowl = new THREE.Mesh(new THREE.SphereGeometry(0.07, 12, 10), std(0xffffff)); bowl.position.y = 0.02; g.add(bowl);
    const blades = new THREE.Group(); blades.position.set(0, 0.88, 0.06);
    for (let i = 0; i < 4; i++) {
      const b = new THREE.Mesh(new THREE.CircleGeometry(0.24, 3), std(SPRINKLES[i], { side: THREE.DoubleSide }));
      b.position.set(Math.cos((i * Math.PI) / 2) * 0.13, Math.sin((i * Math.PI) / 2) * 0.13, 0);
      b.rotation.z = (i * Math.PI) / 2;
      blades.add(b);
    }
    const hub = new THREE.Mesh(new THREE.SphereGeometry(0.045, 10, 8), std(0xffd84d)); hub.position.z = 0.02; blades.add(hub);
    g.add(blades); parts.blades = blades;
    return { group: g, parts };
  },
  flower(color) {
    const g = new THREE.Group(); const parts = {};
    const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.024, 0.36, 8), std(0x7cc46a)); stem.position.y = 0.18; g.add(stem);
    for (const s of [-1, 1]) { const leaf = new THREE.Mesh(new THREE.SphereGeometry(0.06, 10, 8), std(0x8fd77a)); leaf.scale.set(1.4, 0.35, 0.7); leaf.position.set(0.06 * s, 0.1, 0); leaf.rotation.z = -0.5 * s; g.add(leaf); }
    const head = new THREE.Group(); head.position.y = 0.38; g.add(head); parts.head = head;
    const petals = new THREE.Group(); petals.rotation.x = -0.75; head.add(petals); parts.petals = petals;
    const pm = std(color);
    for (let i = 0; i < 6; i++) {
      const a = (i / 6) * Math.PI * 2;
      const p = new THREE.Mesh(new THREE.SphereGeometry(0.065, 12, 10), pm);
      p.scale.set(1, 1, 0.45); p.position.set(Math.cos(a) * 0.085, Math.sin(a) * 0.085, 0);
      petals.add(p);
    }
    const centre = new THREE.Mesh(new THREE.SphereGeometry(0.05, 12, 10), std(0xffe46b)); centre.scale.z = 0.6; centre.position.z = 0.02; petals.add(centre);
    return { group: g, parts };
  },
  can(color) {
    const g = new THREE.Group(); const parts = {};
    const body = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.24, 0.38, 20), std(color)); body.position.y = 0.19; g.add(body);
    const cap = new THREE.Mesh(new THREE.SphereGeometry(0.22, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), std(color)); cap.position.y = 0.38; cap.scale.y = 0.45; g.add(cap);
    const leaf = new THREE.Mesh(new THREE.SphereGeometry(0.06, 10, 8), std(0x8fd77a)); leaf.scale.set(1.5, 0.4, 0.7); leaf.position.set(0.04, 0.5, 0); g.add(leaf);
    const spoutM = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.04, 0.34, 10), std(0xfff1e6));
    spoutM.position.set(0, 0.32, 0.3); spoutM.rotation.x = 0.95; g.add(spoutM);
    const tip = new THREE.Group(); tip.position.set(0, 0.43, 0.44); g.add(tip); parts.spout = tip;
    const handle = new THREE.Mesh(new THREE.TorusGeometry(0.11, 0.025, 8, 16, Math.PI), std(0xfff1e6)); handle.position.set(0, 0.24, -0.24); handle.rotation.set(0, Math.PI / 2, Math.PI / 2); g.add(handle);
    return { group: g, parts };
  },
  xylophone() {
    const g = new THREE.Group(); const parts = { bars: [] };
    const cols = [0xff8fb8, 0xffd84d, 0x7fe0c0, 0x7cc4ff, 0xc6a2ff];
    for (const z of [-0.16, 0.16]) { const rail = new THREE.Mesh(new THREE.BoxGeometry(0.95, 0.06, 0.06), std(PALETTE.waferPost)); rail.position.set(0, 0.3, z); rail.rotation.y = 0.12 * Math.sign(z); g.add(rail); }
    for (const x of [-0.42, 0.42]) for (const z of [-0.16, 0.16]) { const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.3, 8), std(PALETTE.waferPost)); leg.position.set(x, 0.15, z); g.add(leg); }
    cols.forEach((c, i) => {
      const len = 0.5 - i * 0.05;
      const bar = new THREE.Group(); bar.position.set(-0.36 + i * 0.18, 0.36, 0); bar.userData.color = c;
      const m = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.06, len), std(c)); bar.add(m);
      const stick = new THREE.Mesh(new THREE.CylinderGeometry(0.015, 0.015, 0.14, 6), std(0xfff1e6)); stick.rotation.x = Math.PI / 2; stick.position.z = len / 2 + 0.06; bar.add(stick);
      g.add(bar); parts.bars.push(bar);
    });
    return { group: g, parts };
  },
  cloud() {
    const g = new THREE.Group(); const parts = {};
    const m = new THREE.Mesh(cloudGeometry(mulberry(7), 4), cloudMat()); m.scale.setScalar(0.5); g.add(m);
    const em = std(PALETTE.face);
    parts.eyes = [-0.16, 0.16].map((x) => { const e = eye(em, 0.05); e.position.set(x, 0.05, 0.42); g.add(e); return e; });
    for (const x of [-0.3, 0.3]) { const b = new THREE.Mesh(new THREE.CircleGeometry(0.06, 14), new THREE.MeshBasicMaterial({ color: 0xffb3c8, transparent: true, opacity: 0.8 })); b.position.set(x, -0.04, 0.44); g.add(b); }
    return { group: g, parts };
  },
  skyisland(color) {
    const g = new THREE.Group(); const parts = {};
    const topM = new THREE.Mesh(new THREE.CylinderGeometry(0.8, 0.78, 0.12, 24), std(color)); topM.position.y = 0.9; g.add(topM);
    const cone = new THREE.Mesh(new THREE.ConeGeometry(0.8, 0.85, 24), creamMat()); cone.rotation.x = Math.PI; cone.position.y = 0.42; g.add(cone);
    for (let i = 0; i < 9; i++) { const a = (i / 9) * Math.PI * 2; const b = new THREE.Mesh(new THREE.SphereGeometry(0.16, 12, 10), (i % 3 === 2 ? blushMat() : creamMat())); b.scale.y = 0.65; b.position.set(Math.cos(a) * 0.76, 0.93, Math.sin(a) * 0.76); g.add(b); }
    const hut = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.28, 0.3), std(0xfff1e6)); hut.position.set(0.05, 1.1, 0); g.add(hut);
    const roof = new THREE.Mesh(new THREE.ConeGeometry(0.3, 0.26, 4), std(0xff9fb8)); roof.rotation.y = Math.PI / 4; roof.position.set(0.05, 1.37, 0); g.add(roof);
    const star = new THREE.Mesh(new THREE.OctahedronGeometry(0.1), std(0xffd84d, { emissive: 0xffd84d, emissiveIntensity: 0.4 })); star.position.set(0.05, 1.6, 0); g.add(star);
    return { group: g, parts };
  },
  sun(color, height) {
    const g = new THREE.Group(); const parts = {};
    const r = height / 2 / 1.3;
    const basic = (c) => new THREE.MeshBasicMaterial({ color: c, toneMapped: false, transparent: true });
    const face = new THREE.Group(); face.position.y = height / 2; g.add(face);
    const disc = new THREE.Mesh(new THREE.CircleGeometry(r, 40), std(color, { emissive: color, emissiveIntensity: 0.55 })); face.add(disc);
    for (const [rr, w] of [[0.62, 0.05], [0.34, 0.045]]) { const ring = new THREE.Mesh(new THREE.TorusGeometry(r * rr, r * w, 6, 36, Math.PI * 1.6), basic(PALETTE.sunSwirl)); ring.position.z = 0.01; ring.rotation.z = rr * 4; face.add(ring); }
    const em = basic(PALETTE.face);
    parts.eyes = [-0.3, 0.3].map((x) => { const e = eye(em, r * 0.09); e.position.set(x * r, r * 0.12, 0.03); face.add(e); return e; });
    const smile = new THREE.Mesh(new THREE.TorusGeometry(r * 0.22, r * 0.035, 6, 16, Math.PI), em); smile.rotation.z = Math.PI; smile.position.set(0, -r * 0.12, 0.03); face.add(smile);
    const rays = new THREE.Group(); rays.position.z = -0.01; face.add(rays); parts.rays = rays;
    for (let i = 0; i < 10; i++) { const a = (i / 10) * Math.PI * 2; const t = new THREE.Mesh(new THREE.CircleGeometry(r * 0.2, 3), basic(0xffe28a)); t.position.set(Math.cos(a) * r * 1.15, Math.sin(a) * r * 1.15, 0); t.rotation.z = a; rays.add(t); }
    return { group: g, parts, fitted: true };
  },
};

/** Procedural stand-in in the prop's sheet colour, fitted to `height`. Unknown stands get a rounded blob. */
export function makeStandIn(stand, color, height) {
  const build = BUILDERS[stand];
  const hex = color ? new THREE.Color(color).getHex() : PALETTE.candyPink;
  const out = build ? build(hex, height) : { group: new THREE.Mesh(new THREE.SphereGeometry(0.5, 20, 16), std(hex)), parts: {} };
  const holder = new THREE.Group();
  holder.add(out.group);
  if (!out.fitted) fitToHeight(out.group, height);
  return { group: holder, parts: out.parts };
}
