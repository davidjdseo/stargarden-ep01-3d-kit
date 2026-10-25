// Scoop Sky feel layer: keyed tweens, squash-stretch, instanced sprinkle particles and one animation per reaction kind.
// Reduced motion: tweens flagged `motion` jump straight to their end state at their start time and particles are off;
// colour/emissive tweens (motion:false) still play, so every tap still shows a change.
import * as THREE from 'three';
import { KINDS } from './reactions.mjs';

export const SPRINKLES = [0xff8fb8, 0x7fe0c0, 0x7cc4ff, 0xffd84d, 0xc6a2ff, 0xffad7a];
const C1 = 1.70158;
export const easeOutBack = (k) => 1 + (C1 + 1) * Math.pow(k - 1, 3) + C1 * Math.pow(k - 1, 2);
export const easeOut = (k) => 1 - Math.pow(1 - k, 3);
const lerp = (a, b, k) => a + (b - a) * k;

/** Squash-stretch curve: y 1 -> 0.82 -> 1.12 -> 1.0 (ease-out-back settle); `amp` scales the deviation. */
export function squashY(k, amp = 1) {
  let y;
  if (k < 0.3) y = lerp(1, 0.82, easeOut(k / 0.3));
  else if (k < 0.65) y = lerp(0.82, 1.12, easeOut((k - 0.3) / 0.35));
  else y = lerp(1.12, 1.0, easeOutBack((k - 0.65) / 0.35));
  return 1 + (y - 1) * amp;
}

export function createAnimator(scene, { reduced = () => false } = {}) {
  const tweens = new Map();
  let seq = 0;
  let time = 0;

  function tween({ key, dur = 300, delay = 0, motion = true, update, done }) {
    const id = key || `t${seq++}`;
    tweens.set(id, { t0: time + delay / 1000, dur: Math.max(1, dur) / 1000, motion, update, done });
    return id;
  }

  // ---- particles: one InstancedMesh pool, per-instance colour
  const POOL = 220;
  const geo = new THREE.OctahedronGeometry(0.055, 0);
  const mat = new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false });
  const mesh = new THREE.InstancedMesh(geo, mat, POOL);
  mesh.frustumCulled = false;
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  const colour = new THREE.Color();
  for (let i = 0; i < POOL; i++) mesh.setColorAt(i, colour.set(0xffffff));
  scene.add(mesh);
  const P = Array.from({ length: POOL }, () => ({ live: false, pos: new THREE.Vector3(), vel: new THREE.Vector3(), age: 0, life: 1, g: -4, spin: 0, size: 1, delay: 0 }));
  const m4 = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  const s = new THREE.Vector3();
  const axis = new THREE.Vector3(0.3, 1, 0.2).normalize();
  let cursor = 0;
  for (let i = 0; i < POOL; i++) mesh.setMatrixAt(i, m4.makeScale(0, 0, 0));

  function emit(pos, vel, { life = 0.8, g = -4, size = 1, color = 0xffffff, delay = 0 } = {}) {
    const i = cursor; cursor = (cursor + 1) % POOL;
    const p = P[i];
    Object.assign(p, { live: true, age: -delay, life, g, size, spin: Math.random() * 6 });
    p.pos.copy(pos); p.vel.copy(vel);
    mesh.setColorAt(i, colour.set(color));
    mesh.instanceColor.needsUpdate = true;
  }

  function sparkle(point, count = 10, colors = SPRINKLES) {
    if (reduced()) return;
    for (let i = 0; i < count; i++) {
      const a = Math.random() * Math.PI * 2;
      const sp = 1.0 + Math.random() * 1.4;
      emit(point, new THREE.Vector3(Math.cos(a) * sp * 0.7, 1.6 + Math.random() * 1.4, Math.sin(a) * sp * 0.7),
        { life: 0.6 + Math.random() * 0.3, g: -5, size: 0.8 + Math.random() * 0.7, color: colors[i % colors.length] });
    }
  }

  /** Ballistic water drops that land on `to` after `T` seconds. */
  function drops(from, to, count = 10, T = 0.55) {
    if (reduced()) return;
    const g = -9.8;
    for (let i = 0; i < count; i++) {
      const jitter = new THREE.Vector3((Math.random() - 0.5) * 0.12, 0, (Math.random() - 0.5) * 0.12);
      const d = to.clone().add(jitter).sub(from);
      const v = new THREE.Vector3(d.x / T, (d.y - 0.5 * g * T * T) / T, d.z / T);
      emit(from, v, { life: T, g, size: 0.9, color: i % 3 ? 0x6cc6ff : 0xbfe8ff, delay: i * 0.04 });
    }
  }

  function squash(node, amp = 1, key) {
    if (reduced()) return;
    tween({ key: key || `${node.uuid}:squash`, dur: 260, update: (k) => {
      const y = squashY(k, amp);
      const xz = 1 / Math.sqrt(y);
      node.scale.set(xz, y, xz);
    } });
  }

  function tick(dt) {
    time += dt;
    const red = reduced();
    for (const [id, tw] of tweens) {
      if (time < tw.t0) continue;
      let k = (time - tw.t0) / tw.dur;
      if (red && tw.motion) k = 1;
      if (k >= 1) { tw.update(1); tweens.delete(id); tw.done?.(); } else tw.update(k);
    }
    let any = false;
    for (let i = 0; i < POOL; i++) {
      const p = P[i];
      if (!p.live) continue;
      any = true;
      p.age += dt;
      if (p.age < 0) { mesh.setMatrixAt(i, m4.makeScale(0, 0, 0)); continue; }
      if (p.age >= p.life) { p.live = false; mesh.setMatrixAt(i, m4.makeScale(0, 0, 0)); continue; }
      p.vel.y += p.g * dt;
      p.pos.addScaledVector(p.vel, dt);
      const fade = p.age / p.life;
      const sc = p.size * (fade < 0.7 ? 1 : 1 - (fade - 0.7) / 0.3);
      q.setFromAxisAngle(axis, p.spin + p.age * 8);
      mesh.setMatrixAt(i, m4.compose(p.pos, q, s.set(sc, sc, sc)));
    }
    if (any || cursor) mesh.instanceMatrix.needsUpdate = true;
  }

  return { tween, squash, sparkle, drops, tick, get reduced() { return reduced(); }, get time() { return time; }, get busy() { return tweens.size; } };
}

const v3 = () => new THREE.Vector3();
const worldOf = (node, y = 0) => node.localToWorld(v3().set(0, y, 0));

/** Per-kind animation. prop = {id, entry, anchor, squash, body, parts, mats, state}; ctx carries main's extras. */
export const KIND_ANIM = {
  door(A, prop, { variant }) {
    const door = prop.parts.door;
    A.tween({ key: `${prop.id}:bounce`, dur: 380, update: (k) => { prop.body.position.y = Math.sin(Math.PI * k) * 0.14; } });
    if (door) {
      A.tween({ key: `${prop.id}:door`, dur: 320, update: (k) => { door.rotation.y = -1.45 * easeOutBack(k); } });
      A.tween({ key: `${prop.id}:doorShut`, dur: 320, delay: 1300, update: (k) => { door.rotation.y = -1.45 * (1 - easeOut(k)); } });
    }
    if (variant === 2 && prop.parts.chimney) A.sparkle(worldOf(prop.parts.chimney, 0.2), 8, [0xffffff, 0xffe3ec]);
    return { routeAfterMs: 520 };
  },
  hop(A, prop, { variant }) {
    const h = [0.22, 0.32, 0.42][variant] * (prop.entry.height_m || 1);
    A.tween({ key: `${prop.id}:hop`, dur: 440, update: (k) => { prop.body.position.y = Math.sin(Math.PI * k) * h; } });
    const { lid, flag } = prop.parts;
    if (lid) A.tween({ key: `${prop.id}:lid`, dur: 520, update: (k) => { lid.rotation.x = -1.1 * Math.sin(Math.PI * k); } });
    if (flag) {
      prop.state.flagUp = !prop.state.flagUp;
      const from = flag.rotation.z; const to = prop.state.flagUp ? 1.35 : 0;
      A.tween({ key: `${prop.id}:flag`, dur: 300, update: (k) => { flag.rotation.z = lerp(from, to, easeOutBack(k)); } });
    }
    return {};
  },
  spin(A, prop, { variant, combo }) {
    const blades = prop.parts.blades;
    if (blades) {
      prop.state.spinVel = (prop.state.spinVel || 0) + [7, 12, 18][variant] + (combo ? 25 : 0);
      if (A.reduced) blades.rotation.z -= 1.05;
    } else {
      A.tween({ key: `${prop.id}:spin`, dur: 700, update: (k) => { prop.body.rotation.y = Math.PI * 2 * easeOut(k); } });
    }
    return {};
  },
  bloom(A, prop, { variant }) {
    prop.state.blooms = (prop.state.blooms || 0) + 1;
    const target = Math.min(1.3, 1 + 0.1 * prop.state.blooms);
    const petals = prop.parts.petals;
    if (petals) {
      const from = Math.max(0.55, petals.scale.x * 0.6);
      A.tween({ key: `${prop.id}:petals`, dur: 420, update: (k) => { petals.scale.setScalar(lerp(from, target, easeOutBack(k))); } });
    }
    const head = prop.parts.head || prop.body;
    const dir = variant === 1 ? -1 : 1;
    A.tween({ key: `${prop.id}:wiggle`, dur: 620, update: (k) => { head.rotation.z = dir * 0.28 * Math.sin(k * Math.PI * 4) * (1 - k); } });
    glowPulse(A, prop, 0xffffff, 0.35, 500);
    return {};
  },
  pour(A, prop, { target }) {
    const body = prop.body;
    let yaw = 0;
    if (target) {
      const d = target.anchor.getWorldPosition(v3()).sub(prop.anchor.getWorldPosition(v3()));
      d.y = 0;
      if (d.lengthSq() > 1e-6) {
        d.normalize().applyQuaternion(prop.anchor.getWorldQuaternion(new THREE.Quaternion()).invert());
        yaw = Math.atan2(d.x, d.z);
      }
    }
    const qy = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), yaw);
    const qx = new THREE.Quaternion();
    const X = new THREE.Vector3(1, 0, 0);
    const tilt = THREE.MathUtils.degToRad(35);
    const set = (a) => { body.quaternion.copy(qy).multiply(qx.setFromAxisAngle(X, a)); };
    A.tween({ key: `${prop.id}:tilt`, dur: 280, update: (k) => set(tilt * easeOutBack(k)) });
    A.tween({ key: `${prop.id}:untilt`, dur: 300, delay: 1000, update: (k) => set(tilt * (1 - easeOut(k))) });
    if (target) {
      const head = worldOf(target.anchor, (target.entry.height_m || 0.5) * 0.85);
      A.tween({ key: `${prop.id}:drops`, dur: 1, delay: 240, motion: false, update: () => {
        prop.anchor.updateMatrixWorld(true);
        const spout = prop.parts.spout ? worldOf(prop.parts.spout) : worldOf(prop.body, (prop.entry.height_m || 0.6) * 0.9);
        A.drops(spout, head, 12);
      } });
    }
    return { waterAfterMs: 780 };
  },
  notes(A, prop, { note = 0, color = 0xffffff }) {
    const bar = prop.parts.bars?.[note % (prop.parts.bars.length || 1)];
    const node = bar || prop.body;
    const base = node.userData.baseY ?? (node.userData.baseY = node.position.y);
    A.tween({ key: `${prop.id}:dip${bar ? note : ''}`, dur: 260, update: (k) => { node.position.y = base - Math.sin(Math.PI * k) * 0.07; } });
    if (bar) A.sparkle(worldOf(bar, 0.05), 8, [color, 0xffffff]);
    return {};
  },
  puff(A, prop, { variant, combo }) {
    A.tween({ key: `${prop.id}:puff`, dur: 520, update: (k) => {
      const sc = k < 0.35 ? lerp(1, 1.3, easeOut(k / 0.35)) : lerp(1.3, 1, easeOutBack((k - 0.35) / 0.65));
      prop.body.scale.setScalar(sc);
    } });
    A.sparkle(worldOf(prop.body, (prop.entry.height_m || 0.9) * 0.5), combo ? 24 : 12);
    const eyes = prop.parts.eyes;
    if (eyes) {
      const sleepy = variant === 2;
      A.tween({ key: `${prop.id}:eyes`, dur: 200, motion: false, update: (k) => { for (const e of eyes) e.scale.y = sleepy ? lerp(1, 0.2, k) : lerp(e.scale.y, 1, k); } });
    }
    return {};
  },
  glow(A, prop) {
    A.tween({ key: `${prop.id}:bob`, dur: 900, update: (k) => { prop.body.position.y = Math.sin(Math.PI * k) * 0.3; } });
    glowPulse(A, prop, 0xfff2b0, 0.9, 900);
    return {};
  },
  blink(A, prop, { variant }) {
    const eyes = prop.parts.eyes || [];
    const blinks = variant === 2 ? 2 : 1;
    A.tween({ key: `${prop.id}:blink`, dur: 260 * blinks, motion: false, update: (k) => {
      const y = 1 - 0.9 * Math.abs(Math.sin(Math.PI * k * blinks));
      for (const e of eyes) e.scale.y = k >= 1 ? 1 : y;
    } });
    const rays = prop.parts.rays;
    if (rays) { const from = rays.rotation.z; A.tween({ key: `${prop.id}:rays`, dur: 500, update: (k) => { rays.rotation.z = from + (Math.PI / 8) * easeOut(k); } }); }
    glowPulse(A, prop, 0xffe28a, 0.5, 500);
    return {};
  },
  friend(A, prop, { variant, combo }) {
    const h = prop.entry.height_m || 1;
    const b = prop.body;
    const big = combo ? 1.5 : 1;
    const style = prop.entry.style;
    if (style === 'piyo') {
      A.tween({ key: `${prop.id}:hop`, dur: 460, update: (k) => { b.position.y = Math.sin(Math.PI * k) * 0.4 * h * big; b.rotation.z = Math.sin(Math.PI * 2 * k) * 0.3 * (variant === 1 ? -1 : 1); } });
    } else if (style === 'mongsil') {
      A.tween({ key: `${prop.id}:boing`, dur: 620, update: (k) => {
        const y = k < 0.3 ? lerp(1, 0.7, easeOut(k / 0.3)) : lerp(0.7, 1, easeOutBack((k - 0.3) / 0.7));
        b.scale.set(1 / Math.sqrt(y), y, 1 / Math.sqrt(y));
        b.position.y = k > 0.3 ? Math.sin(Math.PI * (k - 0.3) / 0.7) * 0.3 * h * big : 0;
      } });
    } else if (style === 'popo') {
      A.tween({ key: `${prop.id}:spinhop`, dur: 640, update: (k) => { b.position.y = Math.sin(Math.PI * k) * 0.3 * h * big; b.rotation.y = Math.PI * 2 * easeOut(k) * (variant === 1 ? -1 : 1); } });
    } else {
      A.tween({ key: `${prop.id}:wiggle`, dur: 700, update: (k) => { b.rotation.y = Math.sin(k * Math.PI * 5) * 0.5 * (1 - k) * big; b.position.y = Math.sin(Math.PI * k) * 0.12 * h; } });
    }
    return {};
  },
  fly(A, prop, { variant, combo, target }) {
    const b = prop.body;
    const h = prop.entry.height_m || 1;
    if (prop.entry.flight === 'flit' && target) {
      // butterfly: arc to the nearest flower, land (slow wings), arc back; the flower answers with a sparkle + squash
      // idle flap scales the idle group in x; it pauses while flying (state.flying) so the path is not stretched
      prop.state.flying = true; prop.idle.scale.x = 1; prop.idle.rotation.z = 0;
      const land = prop.anchor.worldToLocal(worldOf(target.anchor, (target.entry.height_m || 0.8) * 1.02));
      const lift = 0.35 + 0.15 * variant;
      const pos = (k) => (k < 0.4 ? easeOut(k / 0.4) : k < 0.62 ? 1 : 1 - easeOut((k - 0.62) / 0.38));
      A.tween({ key: `${prop.id}:fly`, dur: 1900, update: (k) => {
        const u = pos(k); const air = k < 0.4 ? Math.sin(Math.PI * k / 0.4) : k < 0.62 ? 0 : Math.sin(Math.PI * (k - 0.62) / 0.38);
        b.position.set(land.x * u, land.y * u + air * lift, land.z * u);
        const resting = k >= 0.4 && k < 0.62;
        b.scale.x = k >= 1 ? 1 : 1 - (resting ? 0.25 : 0.55) * Math.abs(Math.sin(k * Math.PI * (resting ? 5 : 16)));
      }, done: () => { prop.state.flying = false; } });
      A.tween({ key: `${prop.id}:land`, dur: 1, delay: 760, motion: false, update: () => {
        A.sparkle(worldOf(target.anchor, (target.entry.height_m || 0.8) * 1.05), combo ? 18 : 10, [0xff6b6b, 0xffffff, 0xffd84d]);
        A.squash(target.squash, 0.5, `${target.id}:squash`);
      } });
      return {};
    }
    // plane: 0 loop-the-loop, 1 barrel roll, 2 dash and back (model nose = local +Z); combo = two loops
    const R = 0.6 * h;
    const turns = combo ? 2 : 1;
    if (variant === 1) {
      A.tween({ key: `${prop.id}:fly`, dur: 900, update: (k) => { b.rotation.z = Math.PI * 2 * easeOut(k); b.position.z = Math.sin(Math.PI * k) * R * 0.6; } });
    } else if (variant === 2) {
      A.tween({ key: `${prop.id}:fly`, dur: 1000, update: (k) => { b.position.z = Math.sin(Math.PI * k) * R * 1.6; b.rotation.z = Math.sin(Math.PI * 2 * k) * 0.45; } });
    } else {
      A.tween({ key: `${prop.id}:fly`, dur: 1100 * turns, update: (k) => {
        const th = Math.PI * 2 * turns * (k < 1 ? k - Math.sin(Math.PI * 2 * k) / (Math.PI * 2) : 1);
        b.position.z = Math.sin(th) * R; b.position.y = (1 - Math.cos(th)) * R; b.rotation.x = -th;
      } });
    }
    return {};
  },
};

/** Code idles for floating props (entry.idle): butterfly wing flap, plane bank, cream-puff drift. Writes the idle group only. */
export function propIdle(prop, t) {
  const g = prop.idle; const ph = t + prop.phase;
  switch (prop.entry.idle) {
    case 'flap': if (prop.state.flying) break; g.scale.x = 1 - 0.3 * Math.abs(Math.sin(ph * 7)); g.rotation.z = Math.sin(ph * 1.7) * 0.08; break;
    case 'hover': g.rotation.z = Math.sin(ph * 0.9) * 0.1; g.position.y = Math.sin(ph * 1.8) * 0.05; break;
    case 'drift': { const s = 1 + Math.sin(ph * 1.2) * 0.03; g.scale.set(s, s, s); g.rotation.y = Math.sin(ph * 0.5) * 0.15; break; }
    default: break;
  }
}

function glowPulse(A, prop, hex, peak, dur) {
  const mats = prop.mats || [];
  if (!mats.length) return;
  const c = new THREE.Color(hex);
  for (const m of mats) if (m.emissive && !m.userData.baseEmissive) { m.userData.baseEmissive = m.emissive.clone(); m.userData.baseEI = m.emissiveIntensity; }
  A.tween({ key: `${prop.id}:glow`, dur, motion: false, update: (k) => {
    const w = Math.sin(Math.PI * k) * peak;
    for (const m of mats) {
      if (!m.emissive) continue;
      m.emissive.copy(m.userData.baseEmissive).lerp(c, Math.min(1, w * 1.5));
      m.emissiveIntensity = lerp(m.userData.baseEI, 1, w);
    }
  } });
}

/** Code idles for the static friend meshes; writes only the prop's `idle` group so taps (body/squash) never fight it. */
export function friendIdle(prop, t) {
  const g = prop.idle; const h = prop.entry.height_m || 1; const ph = t + prop.phase;
  switch (prop.entry.style) {
    case 'piyo': { const hop = Math.max(0, Math.sin(ph * 5.2)); g.position.y = hop * hop * 0.05 * h; g.rotation.z = Math.sin(ph * 1.3) * 0.12; break; }
    case 'mongsil': { const y = 1 + Math.sin(ph * 3.0) * 0.045; g.scale.set(1 / Math.sqrt(y), y, 1 / Math.sqrt(y)); break; }
    case 'popo': g.rotation.z = Math.sin(ph * 3.4) * 0.1; g.position.x = Math.sin(ph * 3.4) * 0.03; break;
    case 'nuri': g.rotation.y = Math.sin(ph * 1.1) * 0.12 + Math.sin(ph * 4.4) * 0.05; g.rotation.z = Math.sin(ph * 1.1) * 0.04; break;
    default: break;
  }
}

/** Every-frame continuous motion (pinwheel blades keep turning and slow down). */
export function tickProps(props, dt, reduced) {
  for (const p of props) {
    if (p.parts.blades && p.state.spinVel) {
      if (!reduced) p.parts.blades.rotation.z -= p.state.spinVel * dt;
      p.state.spinVel *= Math.exp(-0.9 * dt);
      if (p.state.spinVel < 0.05) p.state.spinVel = 0;
    }
  }
}

/** One tap: squash + the kind animation + sprinkles at the tap point; combo = bigger + a spin. */
export function react(A, prop, r, ctx = {}) {
  const fn = KIND_ANIM[r.kind];
  A.squash(prop.squash, r.combo ? 1.6 : 1, `${prop.id}:squash`);
  const out = fn ? fn(A, prop, { ...ctx, variant: r.variant, combo: r.combo }) || {} : {};
  const at = ctx.point || worldOf(prop.anchor, (prop.entry.height_m || 1) * 0.6);
  const n = 8 + Math.floor(Math.random() * 7);
  A.sparkle(at, r.combo ? n * 2 : n);
  if (r.combo) A.tween({ key: `${prop.id}:combo`, dur: 620, update: (k) => { prop.squash.rotation.y = Math.PI * 2 * easeOut(k); } });
  return out;
}

const missingKinds = KINDS.filter((k) => typeof KIND_ANIM[k] !== 'function');
if (missingKinds.length) throw new Error('[scoop] reaction kinds without animation: ' + missingKinds.join());
