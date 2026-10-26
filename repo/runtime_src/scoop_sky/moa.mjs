// Moa on the island: idle loop, walk-to-point (1.4 m/s, slerped heading), procedural hop.
// Clips are resolved BY NAME with fallbacks (props.json moa.clips), never by index. When the GLB has no idle clip,
// idle = the walk clip held at frame 0 plus a procedural breathe/bob. One-shot gestures (wave, jump, sway, dance)
// play their clip when the GLB has it and otherwise fall back to a procedural move (hop / sway / hop + spin).
import * as THREE from 'three';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';
import { fitToHeight, blobShadow, groundY, std } from './world.mjs';

const UP = new THREE.Vector3(0, 1, 0);

export function findClip(clips, names) {
  for (const n of names) { const c = clips.find((x) => x.name === n); if (c) return c; }
  for (const n of names) { if (n.includes('|')) continue; const c = clips.find((x) => x.name.toLowerCase().includes(n.toLowerCase())); if (c) return c; }
  return null;
}

function standInMoa() {
  const g = new THREE.Group();
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.26, 0.38, 6, 14), std(0xffc9dc)); body.position.y = 0.45; g.add(body);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.27, 18, 14), std(0xffd6e4)); head.position.y = 0.86; g.add(head);
  const em = std(0x5a3a2a);
  for (const x of [-0.09, 0.09]) { const e = new THREE.Mesh(new THREE.SphereGeometry(0.035, 10, 8), em); e.position.set(x, 0.9, 0.25); g.add(e); }
  return g;
}

/**
 * @param gltf    loaded GLTF or null (procedural stand-in)
 * @param cfg     props.json `moa` block
 */
export function createMoa(gltf, cfg, { island }) {
  const carrier = new THREE.Group();
  carrier.name = 'moa';
  const lift = new THREE.Group();
  carrier.add(lift);
  let model; let mixer = null; let walkA = null; let idleA = null;
  const gestures = {};
  if (gltf) {
    model = SkeletonUtils.clone(gltf.scene);
    model.traverse((o) => { if (o.isMesh) o.frustumCulled = false; });
    const fit = new THREE.Group(); fit.add(model);
    fitToHeight(model, cfg.height_m || 1);
    lift.add(fit);
    mixer = new THREE.AnimationMixer(model);
    const walk = findClip(gltf.animations, cfg.clips?.walk || ['walk']);
    const idle = findClip(gltf.animations.filter((c) => c !== walk), cfg.clips?.idle || ['idle']);
    if (walk) { walkA = mixer.clipAction(walk); walkA.play(); walkA.setEffectiveWeight(0); }
    if (idle) { idleA = mixer.clipAction(idle); idleA.play(); }
    else if (walkA) { walkA.setEffectiveWeight(1); walkA.paused = true; walkA.time = 0; }
    for (const [name, names] of Object.entries(cfg.clips?.gestures || {})) {
      const clip = findClip(gltf.animations.filter((c) => c !== walk && c !== idle), names);
      if (clip) { const a = mixer.clipAction(clip); a.setLoop(THREE.LoopOnce, 1); a.clampWhenFinished = false; gestures[name] = a; }
    }
  } else {
    model = standInMoa();
    lift.add(model);
  }
  const foot = cfg.footprint_m || 0.42;
  const shadow = blobShadow(foot, 0.55); shadow.position.y = 0.015; carrier.add(shadow);
  const hit = new THREE.Mesh(new THREE.CylinderGeometry(foot, foot, (cfg.height_m || 1) * 1.1, 12), new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false, colorWrite: false }));
  hit.position.y = (cfg.height_m || 1) * 0.55; hit.userData.pick = 'moa'; carrier.add(hit);

  const [sx, sz] = cfg.start || [0, 0];
  carrier.position.set(sx, groundY(sx, sz, island.radius_m), sz);
  const st = { target: null, onArrive: null, faceTo: null, walking: false, hopT: -1, hopH: 0.35, breathe: 0, blend: 0, gest: null, pending: null, swayT: -1, spinT: -1 };
  const H = cfg.hop_m || 0.35;
  const speed = cfg.speed_mps || 1.4;
  const tmpQ = new THREE.Quaternion();

  function setWalking(on) {
    if (st.walking === on) return;
    st.walking = on;
    if (!walkA) return;
    if (!idleA) { walkA.paused = !on; if (!on) walkA.time = 0; }
  }

  function walkTo(x, z, { onArrive, faceTo } = {}) {
    st.target = new THREE.Vector3(x, 0, z);
    st.onArrive = onArrive || null;
    st.faceTo = faceTo || null;
    const d = Math.hypot(x - carrier.position.x, z - carrier.position.z);
    if (d < 0.08) { st.target = null; arrive(); return; }
    stopGesture();
    setWalking(true);
  }
  function arrive() {
    setWalking(false);
    const cb = st.onArrive; st.onArrive = null;
    cb?.();
    if (st.pending) { const g = st.pending; st.pending = null; gesture(g); }
  }
  function hop(h = H) { st.hopT = 0; st.hopH = h; }

  function stopGesture() { if (st.gest) { st.gest.act.stop(); st.gest = null; } }
  /** One-shot gesture by name; queued until arrival when Moa is walking. Returns 'clip' | 'procedural' | 'queued'. */
  function gesture(name) {
    if (st.walking) { st.pending = name; hop(H * 0.4); return 'queued'; }
    const act = gestures[name];
    if (act) {
      stopGesture();
      act.reset(); act.setEffectiveWeight(0); act.play();
      st.gest = { act, t: 0, dur: act.getClip().duration };
      return 'clip';
    }
    if (name === 'jump') hop(H);
    else if (name === 'wave') hop(H * 0.45);
    else if (name === 'sway') st.swayT = 0;
    else if (name === 'dance') { hop(H * 0.8); st.spinT = 0; }
    return 'procedural';
  }

  function yawTo(dx, dz, dt, rate = 10) {
    tmpQ.setFromAxisAngle(UP, Math.atan2(dx, dz));
    carrier.quaternion.slerp(tmpQ, 1 - Math.exp(-rate * dt));
  }

  function update(dt, reduced) {
    if (st.target) {
      const dx = st.target.x - carrier.position.x; const dz = st.target.z - carrier.position.z;
      const d = Math.hypot(dx, dz);
      const step = speed * dt;
      if (d <= step) { carrier.position.x = st.target.x; carrier.position.z = st.target.z; st.target = null; arrive(); }
      else { carrier.position.x += (dx / d) * step; carrier.position.z += (dz / d) * step; yawTo(dx, dz, dt); }
    } else if (st.faceTo) {
      yawTo(st.faceTo.x - carrier.position.x, st.faceTo.z - carrier.position.z, dt, 8);
    }
    carrier.position.y = groundY(carrier.position.x, carrier.position.z, island.radius_m);
    st.blend += ((st.walking ? 1 : 0) - st.blend) * (1 - Math.exp(-10 * dt));
    let gw = 0;
    if (st.gest) {
      st.gest.t += dt;
      const { t, dur } = st.gest;
      gw = Math.min(1, t / 0.2, Math.max(0, (dur - t) / 0.2));
      st.gest.act.setEffectiveWeight(gw);
      if (t >= dur) { st.gest.act.stop(); st.gest = null; gw = 0; }
    }
    if (walkA && idleA) { walkA.setEffectiveWeight(st.blend * (1 - gw)); idleA.setEffectiveWeight((1 - st.blend) * (1 - gw)); }
    else if (walkA) walkA.setEffectiveWeight(1 - gw);
    mixer?.update(dt);
    st.breathe += dt;
    const breathe = (!idleA && !st.walking && !reduced) ? 1 + 0.018 * Math.sin(st.breathe * 2.6) : 1;
    let y = 0;
    if (st.hopT >= 0) {
      st.hopT += dt / 0.45;
      if (st.hopT >= 1) st.hopT = -1;
      else if (!reduced) y = Math.sin(Math.PI * st.hopT) * st.hopH;
    }
    const bob = (!st.walking && !idleA && !reduced) ? 0.012 * Math.sin(st.breathe * 2.6) : 0;
    lift.position.y = y + bob;
    lift.rotation.z = 0; lift.rotation.y = 0;
    if (st.swayT >= 0) { st.swayT += dt / 1.2; if (st.swayT >= 1) st.swayT = -1; else if (!reduced) lift.rotation.z = Math.sin(st.swayT * Math.PI * 4) * 0.18 * (1 - st.swayT); }
    if (st.spinT >= 0) { st.spinT += dt / 0.9; if (st.spinT >= 1) st.spinT = -1; else if (!reduced) lift.rotation.y = Math.PI * 2 * (1 - Math.pow(1 - st.spinT, 3)); }
    lift.scale.set(1 / Math.sqrt(breathe), breathe, 1 / Math.sqrt(breathe));
    shadow.scale.setScalar(1 - Math.min(0.4, y));
  }

  return {
    carrier, lift, hit, walkTo, hop, gesture, update, faceTo: (p) => { st.faceTo = p.clone(); },
    get walking() { return st.walking; },
    get position() { return carrier.position; },
    clipInfo: { walk: walkA?.getClip().name || null, idle: idleA?.getClip().name || (walkA ? 'walk@0+breathe' : 'procedural'), gestures: Object.fromEntries(Object.entries(gestures).map(([k, a]) => [k, a.getClip().name])) },
  };
}

// stations (w7): friend clips: mixer + looping idle, play(name) one-shot (false = no clip -> procedural); skinned clone(true) meshes re-bound to the clone's bones by name.
export function friendClips(root, clips) {
  if (!root || !clips?.length) return null;
  root.traverse((o) => { if (o.isSkinnedMesh) o.bind(new THREE.Skeleton(o.skeleton.bones.map((b) => root.getObjectByName(b.name) || b), o.skeleton.boneInverses), o.bindMatrix); });
  const mixer = new THREE.AnimationMixer(root); const idleClip = findClip(clips, ['idle']);
  const idle = idleClip ? mixer.clipAction(idleClip).play() : null; let cur = null;
  mixer.addEventListener('finished', (e) => { if (e.action === cur) { cur.fadeOut(0.25); idle?.reset().fadeIn(0.25).play(); cur = null; } });
  function play(name) {
    const c = findClip(clips.filter((x) => x !== idleClip), [name]); if (!c) return false;
    cur?.stop(); cur = mixer.clipAction(c).reset(); cur.setLoop(THREE.LoopOnce, 1); cur.clampWhenFinished = false; cur.fadeIn(0.2).play(); idle?.fadeOut(0.2);
    return true;
  }
  return { play, has: (n) => !!findClip(clips, [n]), update: (dt) => mixer.update(dt) };
}
