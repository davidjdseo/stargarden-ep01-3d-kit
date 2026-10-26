// Shared pieces for the station activities (no three.js import: the station passes ctx.THREE).
// Every activity module exports the same shape: { id, maxTargets, ownsRoute, levels, words(level), rules(level), mount(ctx) },
// and mount returns { onTap(i, point), next(), update(dt), state(), dispose() }. Rules are pure and run under node.
const C1 = 1.70158;
export const easeOutBack = (k) => 1 + (C1 + 1) * Math.pow(k - 1, 3) + C1 * Math.pow(k - 1, 2);
export const easeOut = (k) => 1 - Math.pow(1 - k, 3);
export const clampLevel = (ladder, level) => Math.max(0, Math.min(ladder.length - 1, level | 0));
export const pastel = (hex, k = 0.35) => {
  const n = parseInt(hex.slice(1), 16); const mix = (c) => Math.round(c + (255 - c) * k);
  return (mix(n >> 16) << 16) | (mix((n >> 8) & 255) << 8) | mix(n & 255);
};

export function mat(ctx, color, { emissive = 0.12, rough = 0.5 } = {}) {
  const m = new ctx.THREE.MeshStandardMaterial({ color, roughness: rough, metalness: 0 });
  m.emissive.set(color).multiplyScalar(emissive); m.userData.baseEmissive = m.emissive.clone();
  return m;
}
/** World point on the lawn at (x, z), lifted by y. */
export const ground = (ctx, x, z, y = 0) => new ctx.THREE.Vector3(x, ctx.groundY(x, z) + y, z);

/** Invisible hit sphere for slot i (radius from the station geometry: >= 88 px at the design viewport). */
export function hitSphere(ctx, slot) {
  const { THREE } = ctx;
  const m = new THREE.Mesh(new THREE.SphereGeometry(slot.hitR, 14, 10), new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false, colorWrite: false }));
  m.position.copy(ground(ctx, slot.x, slot.z, slot.y));
  ctx.group.add(m);
  return ctx.target(m, slot.i);
}
export function popIn(ctx, obj, delay = 0, to = 1) {
  obj.scale.setScalar(0.001);
  ctx.A.tween({ key: `${obj.uuid}:pop`, dur: 380, delay, update: (k) => obj.scale.setScalar(Math.max(0.001, to * easeOutBack(k))) });
}
export function wiggle(ctx, obj) {
  ctx.A.tween({ key: `${obj.uuid}:wig`, dur: 460, update: (k) => { obj.rotation.z = Math.sin(k * Math.PI * 5) * 0.32 * (1 - k); } });
}
/** Arc from -> to over dur ms with apex height h; spin = roll radians. */
export function arc(ctx, obj, from, to, { dur = 500, h = 0.5, delay = 0, spin = 0, done } = {}) {
  const a = from.clone(); const b = to.clone();
  ctx.A.tween({ key: `${obj.uuid}:arc`, dur, delay, update: (k) => {
    obj.position.lerpVectors(a, b, k); obj.position.y += Math.sin(Math.PI * k) * h;
    if (spin) obj.rotation.x = spin * k;
  }, done });
}
/** Emissive flash on every material under obj (colour change also shows with reduced motion). */
export function flash(ctx, obj, color = 0xffffff, dur = 420, peak = 0.9) {
  const mats = []; obj.traverse((o) => { if (o.material?.emissive) mats.push(o.material); });
  const c = new ctx.THREE.Color(color);
  ctx.A.tween({ key: `${obj.uuid}:flash`, dur, motion: false, update: (k) => {
    const w = Math.sin(Math.PI * k) * peak;
    for (const m of mats) m.emissive.copy(m.userData.baseEmissive || m.emissive).lerp(c, w);
  } });
}

// ---- toy pieces (procedural). TOY = how much bigger than life the play pieces are, so they read at the locked wide camera
// (a 0.3 m berry is ~30 px at 844x390); their parts are scaled in place, so tweens on the returned group keep scale 1 = rest.
export const TOY = 1.6;
const grow = (g, k = TOY) => { for (const c of g.children) { c.position.multiplyScalar(k); c.scale.multiplyScalar(k); } return g; };
export function berry(ctx, kind) {
  const { THREE } = ctx; const g = new THREE.Group();
  const red = kind === 'straw';
  const body = new THREE.Mesh(new THREE.SphereGeometry(0.16, 18, 14), mat(ctx, red ? 0xe5484d : 0x4f6fd8));
  body.scale.set(1, red ? 1.15 : 0.95, 1); body.position.y = 0.17; g.add(body);
  const cap = new THREE.Mesh(new THREE.ConeGeometry(red ? 0.11 : 0.06, 0.07, 6), mat(ctx, red ? 0x58b98a : 0x34528f));
  cap.position.y = red ? 0.36 : 0.33; cap.rotation.x = Math.PI; g.add(cap);
  if (red) for (let i = 0; i < 6; i++) { const s = new THREE.Mesh(new THREE.SphereGeometry(0.014, 6, 4), mat(ctx, 0xfff3c4)); const a = i * 1.05; s.position.set(Math.cos(a) * 0.15, 0.17 + (i % 2 ? 0.05 : -0.05), Math.sin(a) * 0.15); g.add(s); }
  return grow(g);
}
export function basket(ctx) {
  const { THREE } = ctx; const g = new THREE.Group();
  const bowl = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.3, 0.32, 20, 1, true), mat(ctx, 0xe8b46a));
  bowl.material.side = THREE.DoubleSide; bowl.position.y = 0.16; g.add(bowl);
  const floor = new THREE.Mesh(new THREE.CircleGeometry(0.3, 20), mat(ctx, 0xd29a52)); floor.rotation.x = -Math.PI / 2; floor.position.y = 0.02; g.add(floor);
  const rim = new THREE.Mesh(new THREE.TorusGeometry(0.42, 0.04, 8, 24), mat(ctx, 0xfdf5e7)); rim.rotation.x = Math.PI / 2; rim.position.y = 0.32; g.add(rim);
  return grow(g, 1.3);
}
export function candy(ctx, hex) {
  const { THREE } = ctx; const g = new THREE.Group();
  const c = parseInt(hex.slice(1), 16);
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.13, 0.26, 6, 14), mat(ctx, c, { emissive: 0.18, rough: 0.35 }));
  body.rotation.z = Math.PI / 2; body.position.y = 0.15; g.add(body);
  const shine = new THREE.Mesh(new THREE.SphereGeometry(0.035, 8, 6), mat(ctx, 0xffffff, { emissive: 0.6 })); shine.position.set(-0.1, 0.25, 0.08); g.add(shine);
  return grow(g);
}
export function cushion(ctx, hex) {
  const { THREE } = ctx; const g = new THREE.Group(); const m = mat(ctx, pastel(hex, 0.3), { emissive: 0.15, rough: 0.8 });
  for (const [x, y, z, r] of [[0, 0.1, 0, 0.26], [-0.22, 0.08, 0.02, 0.18], [0.22, 0.08, -0.02, 0.19], [0.05, 0.16, -0.08, 0.17]]) {
    const s = new THREE.Mesh(new THREE.SphereGeometry(r, 16, 12), m); s.position.set(x, y, z); s.scale.y = 0.55; g.add(s);
  }
  return grow(g, 1.3);
}
export function bar(ctx, hex, h) {
  const { THREE } = ctx; const g = new THREE.Group();
  const pop = new THREE.Mesh(new THREE.CapsuleGeometry(0.13, h, 6, 14), mat(ctx, parseInt(hex.slice(1), 16), { emissive: 0.15, rough: 0.35 }));
  pop.scale.z = 0.55; pop.position.y = 0.16 + h / 2 + 0.13; g.add(pop);
  const stick = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.2, 8), mat(ctx, 0xe8c48a)); stick.position.y = 0.1; g.add(stick);
  g.userData.pop = pop;
  return grow(g, 1.3);
}
export function ballMesh(ctx) {
  const { THREE } = ctx; const g = new THREE.Group(); const spin = new THREE.Group(); g.add(spin);
  spin.add(new THREE.Mesh(new THREE.SphereGeometry(0.22, 22, 16), mat(ctx, 0xfffdf8, { emissive: 0.1 })));
  for (const [col, rx, ry] of [[0xf97086, 0, 0], [0x5094f7, Math.PI / 2, 0], [0xfdcd70, 0, Math.PI / 2]]) {
    const t = new THREE.Mesh(new THREE.TorusGeometry(0.222, 0.035, 8, 32), mat(ctx, col, { emissive: 0.15 })); t.rotation.set(rx, ry, 0); spin.add(t);
  }
  spin.position.y = 0.22; g.userData.spin = spin;
  return grow(g, 1.5);
}
