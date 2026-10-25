// Scoop Sky room: a floating whipped-cream sky island where Moa walks and every tap answers at once
// (squash + kind animation + sprinkles + sound, the book word by voice on the first taps).
//
// Host contract (docs/WEB_BRIDGE.md, web/app/host.mjs:151-201):
//   page -> host : StarGarden.postMessage(JSON) {type:'loadProgress', value} | {type:'ready'} | {type:'gesture'} |
//                  {type:'voice', ms} | {type:'sting', ms} | {type:'enter', route:'/books', book, preview:true} | {type:'error', reason}
//   host -> page : window.sgHostReceive({type:'pause'|'muted'|'reducedMotion'|'language', value})
// Camera: static locked-off establishing 3/4 high angle (props.json camera.why) so tap targets stay put.
// Test hook: window.__scoop = {ready, missing, taps, tap(id), walk(x, z), state()}.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import PROPS from './props.json';
import { buildWorld, makeStandIn, fitToHeight, blobShadow, groundY, calibrateLook } from './world.mjs';
import { lightNeutralMult } from './shade.mjs';
import { createAnimator, react, KIND_ANIM, tickProps, friendIdle, propIdle, SPRINKLES } from './anim.mjs';
import { createReactions } from './reactions.mjs';
import { createMoa } from './moa.mjs';
import { createSound } from './sound.mjs';
import { groundFootprints, verticalFov } from './layout.mjs';

const BASE = new URL(window.SG_ASSET_BASE || './', document.baseURI);
const assetUrl = (p) => new URL(p, BASE).href;
const post = (msg) => {
  try { window.StarGarden?.postMessage(JSON.stringify(msg)); } catch (_) { /* host gone */ }
};

const ISLAND = PROPS.island;
const CAM = PROPS.camera;
const state = {
  paused: false,
  reduced: window.matchMedia?.('(prefers-reduced-motion: reduce)').matches || false,
  language: 'en',
  ready: false,
};
const taps = [];
const missing = [];
const fallbacks = [];

// ---------------------------------------------------------------- renderer (aquarium main.mjs:84-97 rule)
const canvas = document.getElementById('sg-scoop-canvas');
const lowEnd = (navigator.hardwareConcurrency || 8) <= 4 || (navigator.deviceMemory || 8) <= 3;
const renderer = new THREE.WebGLRenderer({ canvas, antialias: !lowEnd, powerPreference: 'high-performance', stencil: false });
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.NeutralToneMapping;
renderer.toneMappingExposure = 1.0;
const phone = Math.min(innerWidth, innerHeight) < 600;
const maxRatio = lowEnd ? 1.25 : phone ? 1.75 : 2;
let pixelRatio = Math.min(window.devicePixelRatio || 1, maxRatio);
renderer.setPixelRatio(pixelRatio);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xfff0e2);
const camera = new THREE.PerspectiveCamera(CAM.fov_landscape, 1, 0.1, 200);
camera.position.set(...CAM.pos);
camera.lookAt(new THREE.Vector3(...CAM.target));
const LIGHTS = PROPS.lights;
const GLB_MULT = lightNeutralMult(LIGHTS, PROPS.look.normal);
scene.add(new THREE.HemisphereLight(LIGHTS.hemi.sky, LIGHTS.hemi.ground, LIGHTS.hemi.intensity));
const sunLight = new THREE.DirectionalLight(LIGHTS.key.color, LIGHTS.key.intensity);
sunLight.position.set(...LIGHTS.key.dir);
scene.add(sunLight);

function resize() {
  const w = window.innerWidth; const h = window.innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / Math.max(1, h);
  camera.fov = verticalFov(CAM, camera.aspect);
  camera.updateProjectionMatrix();
}
addEventListener('resize', resize);
resize();

// ---------------------------------------------------------------- world, feel, rules, sound
const world = buildWorld(scene, { eye: camera.position, island: ISLAND, set: PROPS.set, sky: CAM.sky, avoid: groundFootprints(PROPS.props) });
const A = createAnimator(scene, { reduced: () => state.reduced });
const reactions = createReactions([
  ...PROPS.props.map((p) => ({ id: p.id, reaction: p.reaction, word: p.word, words: p.words })),
  { id: PROPS.moa.id, reaction: PROPS.moa.reaction, word: PROPS.moa.word, words: PROPS.moa.words },
]);
const sound = createSound({ assetUrl, post });
const KIND_SFX = { door: 'door', hop: 'hop', spin: 'spin', bloom: 'bloom', pour: 'pour', puff: 'puff', glow: 'glow', blink: 'blink', fly: 'flutter' };

const props = [];
const propById = new Map();
const pickables = [];
let moa = null;
let noteIndex = 0;
let routeLock = 0;

const later = (ms, fn) => A.tween({ dur: 1, delay: ms, motion: false, update: fn });

function isolateMaterials(root) {
  const mats = [];
  root.traverse((o) => {
    if (!o.isMesh || !o.material) return;
    o.material = Array.isArray(o.material) ? o.material.map((m) => m.clone()) : o.material.clone();
    for (const m of [].concat(o.material)) if (m.emissive) mats.push(m);
  });
  return mats;
}

function buildProp(entry, gltf) {
  const [x, z] = entry.pos;
  const h = entry.height_m;
  const anchor = new THREE.Group();
  anchor.name = `prop:${entry.id}`;
  anchor.position.set(x, (entry.y || 0) + (entry.sky ? 0 : groundY(x, z, ISLAND.radius_m)), z);
  anchor.rotation.y = THREE.MathUtils.degToRad(entry.yaw || 0);
  const idle = new THREE.Group(); anchor.add(idle);
  const squash = new THREE.Group(); idle.add(squash);
  const body = new THREE.Group(); squash.add(body);
  let parts = {};
  if (gltf) {
    const model = gltf.scene.clone(true);
    fitToHeight(model, h);
    body.add(model);
  } else {
    const s = makeStandIn(entry.stand, entry.color, h);
    body.add(s.group);
    parts = s.parts;
  }
  const mats = isolateMaterials(body);
  if (gltf) calibrateLook(body, GLB_MULT, PROPS.look.emissive_offset);   // texture-faithful colour under the scene lights (props.json look)
  const foot = entry.footprint_m ?? h * 0.5;
  const r = entry.sky ? Math.max(0.6, h * 0.6) : Math.max(0.45, foot);
  const hitGeo = entry.sky ? new THREE.SphereGeometry(r, 12, 10) : new THREE.CylinderGeometry(r, r, h * 1.15, 12);
  const hit = new THREE.Mesh(hitGeo, new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false, colorWrite: false }));
  hit.position.y = entry.sky ? h * 0.5 : h * 0.575;
  hit.userData.pick = entry.id;
  anchor.add(hit);
  pickables.push(hit);
  if (!entry.sky) {
    const sh = blobShadow(0.25 + h * 0.4, entry.y ? 0.3 : 0.5);
    sh.position.y = -(entry.y || 0) + 0.012;
    anchor.add(sh);
  }
  scene.add(anchor);
  if (entry.billboard) anchor.lookAt(camera.position);
  const prop = { id: entry.id, entry, anchor, idle, squash, body, baseYaw: anchor.rotation.y, parts, mats, state: {}, radius: entry.sky ? r : foot, baseY: anchor.position.y, phase: Math.random() * 6 };
  props.push(prop);
  propById.set(entry.id, prop);
  return prop;
}

function nearestFlower(from) {
  let best = null; let bd = Infinity;
  for (const p of props) {
    if (p.entry.reaction !== 'bloom') continue;
    const d = p.anchor.position.distanceTo(from.anchor.position);
    if (d < bd) { bd = d; best = p; }
  }
  return best;
}

/** Keep a walk target on the island and out of the props' footprints. */
function clampWalk(x, z) {
  const v = new THREE.Vector2(x, z);
  if (v.length() > ISLAND.walk_radius_m) v.setLength(ISLAND.walk_radius_m);
  for (let pass = 0; pass < 2; pass++) {
    for (const p of props) {
      if (p.entry.sky || p.entry.y) continue;
      const c = new THREE.Vector2(p.anchor.position.x, p.anchor.position.z);
      const min = p.radius + ISLAND.prop_clearance_m;
      const d = v.clone().sub(c);
      if (d.length() < min) v.copy(c.add(d.lengthSq() > 1e-6 ? d.setLength(min) : new THREE.Vector2(0, min)));
    }
    if (v.length() > ISLAND.walk_radius_m) v.setLength(ISLAND.walk_radius_m);
  }
  return v;
}

function frontPoint(prop) {
  const yaw = prop.anchor.rotation.y;
  const reach = prop.entry.sky ? 0.9 : prop.radius + 0.9;
  return clampWalk(prop.anchor.position.x + Math.sin(yaw) * reach, prop.anchor.position.z + Math.cos(yaw) * reach);
}

function water(flower) {
  if (!flower) return;
  A.squash(flower.squash, 0.8, `${flower.id}:squash`);
  KIND_ANIM.bloom(A, flower, { variant: 0 });
  A.sparkle(flower.anchor.localToWorld(new THREE.Vector3(0, flower.entry.height_m * 0.9, 0)), 10);
  sound.sfx('bloom', { gain: 0.8 });
}

function propSound(prop, r, ctx) {
  sound.sfx('tap', { gain: 0.45 });
  if (r.kind === 'notes') sound.note(ctx.note);
  else sound.sfx(prop.entry.sfx || KIND_SFX[r.kind] || 'tap');
  if (r.combo) { sound.sfx('combo', { gain: 0.8 }); post({ type: 'sting', ms: 1200 }); }
  if (r.say) sound.word(r.say);
}

function tapProp(id, point) {
  const prop = propById.get(id);
  if (!prop) return null;
  const r = reactions.tap(id);
  taps.push({ id, kind: r.kind, variant: r.variant, combo: r.combo, say: r.say, t: Math.round(performance.now()) });
  const ctx = { point };
  if (r.kind === 'pour' || (r.kind === 'fly' && prop.entry.flight === 'flit')) ctx.target = nearestFlower(prop);
  if (r.kind === 'notes') {
    ctx.note = noteIndex++ % 5;
    ctx.color = prop.parts.bars?.[ctx.note]?.userData.color ?? SPRINKLES[ctx.note];
  }
  const out = react(A, prop, r, ctx);
  propSound(prop, r, ctx);
  if (out.waterAfterMs && ctx.target) later(out.waterAfterMs, () => water(ctx.target));
  if (out.routeAfterMs && prop.entry.route) {
    const now = performance.now();
    if (now > routeLock) {
      routeLock = now + 2500;
      const { route, book, preview } = prop.entry.route;
      later(out.routeAfterMs, () => post({ type: 'enter', route, book, preview }));
    }
  }
  if (moa && prop.entry.id !== 'swirl-sun') {
    const p = frontPoint(prop);
    moa.walkTo(p.x, p.y, {
      faceTo: prop.anchor.position,
      onArrive: () => {
        moa.faceTo(prop.anchor.position);
        A.squash(prop.squash, 0.6, `${prop.id}:squash`);
        if (['bloom', 'hop', 'spin', 'notes', 'puff', 'blink', 'friend'].includes(r.kind)) KIND_ANIM[r.kind](A, prop, { ...ctx, variant: r.variant, combo: false });
        if (r.combo) moa.gesture('dance');
        else if (r.kind === 'bloom' && prop.state.blooms > 0) moa.gesture('jump');
        A.sparkle(prop.anchor.localToWorld(new THREE.Vector3(0, prop.entry.height_m * 0.7, 0)), 6);
        sound.sfx(r.kind === 'notes' ? 'tap' : prop.entry.sfx || KIND_SFX[r.kind] || 'tap', { gain: 0.5 });
        if (r.kind === 'notes') sound.note(ctx.note);
      },
    });
  } else if (moa) { moa.faceTo(prop.anchor.position); if (r.combo) moa.gesture('dance'); }
  return r;
}

const MOA_TAP_GESTURES = ['wave', 'jump', 'sway'];
function tapMoa() {
  const r = reactions.tap(PROPS.moa.id);
  taps.push({ id: 'moa', kind: r.kind, variant: r.variant, combo: r.combo, say: r.say, t: Math.round(performance.now()) });
  r.gesture = r.combo ? 'dance' : MOA_TAP_GESTURES[r.variant % MOA_TAP_GESTURES.length];
  r.played = moa.gesture(r.gesture);
  A.sparkle(moa.position.clone().add(new THREE.Vector3(0, PROPS.moa.height_m * 1.05, 0)), r.combo ? 24 : 10);
  sound.sfx('tap', { gain: 0.45 });
  sound.sfx('giggle');
  if (r.combo) { sound.sfx('combo', { gain: 0.8 }); post({ type: 'sting', ms: 1200 }); }
  if (r.say) sound.word(r.say, 380);
  return r;
}

function tapGround(point) {
  taps.push({ id: 'ground', kind: 'walk', t: Math.round(performance.now()) });
  A.sparkle(point.clone().setY(point.y + 0.05), 6, [0xffffff, 0xbfe9d6, 0xffc2d6]);
  sound.sfx('tap', { gain: 0.6 });
  const v = clampWalk(point.x, point.z);
  moa?.walkTo(v.x, v.y);
}

function tapNothing(point) {
  taps.push({ id: 'sky', kind: 'sparkle', t: Math.round(performance.now()) });
  A.sparkle(point, 8);
  sound.sfx('sparkle', { gain: 0.5 });
}

// ---------------------------------------------------------------- input
const ray = new THREE.Raycaster();
const ndc = new THREE.Vector2();
let gestured = false;
canvas.addEventListener('pointerdown', (e) => {
  sound.unlock();
  if (!gestured) { gestured = true; post({ type: 'gesture' }); }
  if (!state.ready || state.paused) return;
  const rect = canvas.getBoundingClientRect();
  ndc.set(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
  ray.setFromCamera(ndc, camera);
  const targets = moa ? [...pickables, moa.hit, world.ground] : [...pickables, world.ground];
  const hit = ray.intersectObjects(targets, false)[0];
  if (!hit) { tapNothing(ray.ray.at(12, new THREE.Vector3())); return; }
  const id = hit.object.userData.pick;
  if (id === 'moa') tapMoa();
  else if (id) tapProp(id, hit.point);
  else tapGround(hit.point);
});

// ---------------------------------------------------------------- host bridge + test hook
window.sgHostReceive = (cmd) => {
  let c = cmd;
  if (typeof c === 'string') { try { c = JSON.parse(c); } catch (_) { return; } }
  if (!c || typeof c !== 'object') return;
  switch (c.type) {
    case 'pause': state.paused = !!c.value; sound.pause(state.paused); break;
    case 'muted': sound.setMuted(!!c.value); break;
    case 'reducedMotion': state.reduced = !!c.value; break;
    case 'language': if (typeof c.value === 'string') state.language = c.value; break;
    default: break;
  }
};
document.addEventListener('visibilitychange', () => sound.pause(document.hidden || state.paused));

window.__scoop = {
  ready: false,
  missing,
  fallbacks,
  taps,
  tap(id) {
    if (!state.ready) return null;
    if (id === 'moa') return tapMoa();
    const p = propById.get(id);
    if (!p) return null;
    return tapProp(id, p.anchor.localToWorld(new THREE.Vector3(0, p.entry.height_m * 0.6, 0)));
  },
  walk(x, z) { if (moa) { const v = clampWalk(x, z); moa.walkTo(v.x, v.y); return [v.x, v.y]; } return null; },
  state() {
    return {
      ready: state.ready, paused: state.paused, reduced: state.reduced, muted: sound.muted, language: state.language,
      pixelRatio, props: props.map((p) => p.id), missing: [...missing], fallbacks: [...fallbacks], taps: taps.length,
      moa: moa ? { x: +moa.position.x.toFixed(2), z: +moa.position.z.toFixed(2), walking: moa.walking, clips: moa.clipInfo } : null,
      tweens: A.busy,
    };
  },
};

// ---------------------------------------------------------------- loading
async function boot() {
  const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
  const glbs = [...new Set(PROPS.props.map((p) => p.glb).filter(Boolean))];
  const total = glbs.length + 1;
  let done = 0;
  const tick = () => { done += 1; post({ type: 'loadProgress', value: +(done / total).toFixed(3) }); };
  post({ type: 'loadProgress', value: 0 });
  const tryLoad = (path) => loader.loadAsync(assetUrl(path)).then((g) => g, () => null);
  const loaded = new Map();
  const moaLoad = (async () => {
    let g = await tryLoad(PROPS.moa.glb);
    if (!g) {
      console.warn('[scoop] missing', 'moa', PROPS.moa.glb, '-> raw fallback', PROPS.moa.fallback_glb);
      fallbacks.push('moa:' + PROPS.moa.fallback_glb);
      g = await tryLoad(PROPS.moa.fallback_glb);
      if (!g) { missing.push('moa'); console.warn('[scoop] missing', 'moa', '(procedural stand-in)'); }
    }
    tick();
    return g;
  })();
  await Promise.all(glbs.map((name) => tryLoad(`assets/room/scoop/${name}.glb`).then((g) => { loaded.set(name, g); tick(); })));
  for (const entry of PROPS.props) {
    const g = entry.glb ? loaded.get(entry.glb) : null;
    if (entry.glb && !g) { missing.push(entry.id); console.warn('[scoop] missing', entry.id); }
    buildProp(entry, g);
  }
  const moaGltf = await moaLoad;
  if (moaGltf) calibrateLook(moaGltf.scene, GLB_MULT, PROPS.look.emissive_offset);
  moa = createMoa(moaGltf, PROPS.moa, { island: ISLAND });
  scene.add(moa.carrier);
}

/** Friends turn to face Moa while Moa is within FRIEND_LOOK_M, and turn back to their placed yaw after. */
const FRIEND_LOOK_M = 1.5;
function faceFriends(dt) {
  for (const p of props) {
    if (!p.entry.style) continue;
    const dx = moa.position.x - p.anchor.position.x; const dz = moa.position.z - p.anchor.position.z;
    const goal = Math.hypot(dx, dz) < FRIEND_LOOK_M ? Math.atan2(dx, dz) : p.baseYaw;
    let d = goal - p.anchor.rotation.y;
    d = Math.atan2(Math.sin(d), Math.cos(d));
    p.anchor.rotation.y += d * (1 - Math.exp(-6 * dt));
  }
}

// ---------------------------------------------------------------- loop (adaptive pixel ratio: aquarium main.mjs:2092-2097)
let last = performance.now();
let frameAvg = 16;
let frames = 0;
function frame(now) {
  requestAnimationFrame(frame);
  const dt = Math.min(0.05, (now - last) / 1000);
  last = now;
  if (state.paused) return;
  world.tick(dt);
  A.tick(dt);
  tickProps(props, dt, state.reduced);
  if (!state.reduced) {
    for (const p of props) {
      if (p.entry.y) p.anchor.position.y = p.baseY + Math.sin(A.time * 1.3 + p.phase) * 0.06;
      if (p.entry.style) friendIdle(p, A.time);
      if (p.entry.idle) propIdle(p, A.time);
    }
  }
  if (moa) faceFriends(dt);
  moa?.update(dt, state.reduced);
  renderer.render(scene, camera);
  if (!state.ready && moa) {
    state.ready = true;
    window.__scoop.ready = true;
    post({ type: 'ready' });
  }
  frameAvg = frameAvg * 0.95 + dt * 1000 * 0.05;
  if (++frames % 90 === 0) {
    const target = frameAvg > 26 ? pixelRatio - 0.25 : frameAvg < 17.5 && frames % 450 === 0 ? pixelRatio + 0.25 : pixelRatio;
    const next = Math.min(maxRatio, Math.min(window.devicePixelRatio || 1, Math.max(1, target)));
    if (next !== pixelRatio) { pixelRatio = next; renderer.setPixelRatio(pixelRatio); resize(); }
  }
}

boot().then(() => requestAnimationFrame(frame)).catch((err) => {
  console.error(err);
  post({ type: 'error', reason: String((err && err.message) || err) });
});
