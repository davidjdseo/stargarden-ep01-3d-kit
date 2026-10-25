// Scoop Sky play stations: tap a place or a friend -> Moa walks there -> both greet -> the child plays a tap-only activity in a
// fixed play box in front of the host -> both dance, a sprinkle-star flies, the ladder level is saved -> objects fold away.
// One data table (props.json `stations`), one state machine (this file), one module per activity (activities/*.mjs).
// No three.js import here (main injects THREE): the geometry, path, store and rules run under node (stations.selftest.mjs).
//
// Geometry is derived at run time from the host position and the locked camera, never from hard-coded coordinates:
//   c = unit ground vector host -> camera, r = screen-right on the ground (as seen from the camera);
//   spot = host + c*spot.dist + r*spot.side*(host footprint + clearance + SPOT_PAD)   (where Moa stands, facing the host);
//   box  = host + c*box.dist, w along r, d along c, shifted along r until it lies on the walkable lawn;
//   slots = the activity's maxTargets evenly across the box; each slot's hit sphere projects HIT_PX wide at the design
//           viewport (>= TARGET_PX = design/tokens.json size.targetChild), capped at HIT_FILL of the slot spacing.
import { groundFootprints, setOccluders, projector, MIN_GAP_M } from './layout.mjs';
import { createNavGrid, findPath, isFree } from '../aquarium_cafe/nav_core.mjs';
import { QUESTS, nextLevel } from '../aquarium_cafe/room_core.mjs';
import book from './activities/book.mjs';
import numbers from './activities/numbers.mjs';
import music from './activities/music.mjs';
import ball from './activities/ball.mjs';
import colours from './activities/colours.mjs';

export const ACTIVITIES = { book, numbers, music, ball, colours };
export const TARGET_PX = 88;
export const HIT_PX = 96;
export const HIT_FILL = 0.48;
export const DESIGN_VP = [844, 390];
export const VIEWPORTS = [[844, 390], [1280, 800], [390, 844]];
export const SPOT_PAD = 0.15;
export const SLOT_Y = 0.3;
export const GREET = 'wave';
export const CHEER = 'dance';
export const MS = { greet: 1000, celebrate: 1800, fold: 2000, foldFade: 350 };
export const STORE_FIELD = 'stations';
const MOA_FALLBACK = { kick: 'jump', happy: 'jump', count: 'sway', sing: 'sway', bounce: 'jump' };

const hyp = Math.hypot;
export const hostOf = (PROPS, st) => PROPS.props.find((p) => p.id === st.host) || null;
export const footOf = (p) => p.footprint_m ?? p.height_m * 0.5;
export const clearanceM = (PROPS) => Math.max(PROPS.island.prop_clearance_m ?? 0.6, MIN_GAP_M);

/** Ground frame at (x, z): c toward the camera, r = screen right. */
export function frameAt(PROPS, x, z) {
  const cx = PROPS.camera.pos[0] - x; const cz = PROPS.camera.pos[2] - z; const L = hyp(cx, cz) || 1;
  const c = [cx / L, cz / L];
  return { c, r: [c[1], -c[0]] };
}

/** Walk obstacles in nav_core's manifest format: ground props (circles) + set pieces (boxes from layout.setOccluders). */
export function navManifest(PROPS, skipIds = []) {
  const clr = clearanceM(PROPS);
  const R = PROPS.island.walk_radius_m + clr + 0.15;
  const obstacles = [
    ...groundFootprints(PROPS.props).filter((f) => !skipIds.includes(f.id)).map((f) => ({ id: f.id, kind: 'circle', center: [f.x, 0, f.z], radius: f.r })),
    ...setOccluders(PROPS).map((o) => ({ id: o.id, kind: 'box', center: [o.x, 0, o.z], size: [o.hw * 2, o.hd * 2], yaw: 0 })),
  ];
  return { room: { halfX: R, halfZ: R, cornerRadius: R }, obstacles };
}

let gridCache = null;
export function navGrid(PROPS) {
  if (gridCache && gridCache.PROPS === PROPS) return gridCache.g;
  const g = createNavGrid(navManifest(PROPS), { cell: 0.15, radius: clearanceM(PROPS) });
  gridCache = { PROPS, g };
  return g;
}
/** Waypoints [{x, z}] from `from` to `to` around props and set pieces (nav_core A* + string pulling), or null. */
export const planPath = (PROPS, from, to) => findPath(navGrid(PROPS), { x: from[0], z: from[1] }, { x: to[0], z: to[1] });
export const spotFree = (PROPS, p) => isFree(navManifest(PROPS), p[0], p[1], clearanceM(PROPS));

function slotHitR(P, W, x, y, z, r, spacing) {
  const a = P([x - r[0] * 0.5, y, z - r[1] * 0.5]); const b = P([x + r[0] * 0.5, y, z + r[1] * 0.5]);
  const pxPerM = Math.abs(b[0] - a[0]) * W / 2;
  const want = (HIT_PX / 2) / pxPerM;
  return Math.min(want, spacing * HIT_FILL);
}

/** Everything a station needs in world space. Pure; same numbers in node and in the browser. */
export function stationGeometry(PROPS, st) {
  const h = hostOf(PROPS, st);
  if (!h) return null;
  const [hx, hz] = h.pos; const { c, r } = frameAt(PROPS, hx, hz);
  const clr = clearanceM(PROPS);
  const side = st.spot?.side || 0; const sd = st.spot?.dist ?? footOf(h) + clr + SPOT_PAD;
  const lat = side ? footOf(h) + clr + SPOT_PAD : 0;
  const spot = [hx + c[0] * sd + r[0] * side * lat, hz + c[1] * sd + r[1] * side * lat];
  const geo = { station: st.id, host: h.id, hostPos: [hx, hz], hostH: h.height_m, c, r, spot, box: null, slots: [], at: null };
  const act = ACTIVITIES[st.activity];
  if (!st.box || !act?.maxTargets) return geo;
  const { w, d } = st.box; const walk = PROPS.island.walk_radius_m;
  const base = [hx + c[0] * st.box.dist, hz + c[1] * st.box.dist];
  const inside = (s) => [-0.5, 0.5].every((u) => [-0.5, 0.5].every((v) => hyp(base[0] + r[0] * (s + u * w) + c[0] * v * d, base[1] + r[1] * (s + u * w) + c[1] * v * d) <= walk));
  const toward = -Math.sign(base[0] * r[0] + base[1] * r[1]) || 1;
  let shift = 0;
  for (let k = 0; k <= 120 && !inside(shift); k++) shift = toward * k * 0.05;
  const centre = [base[0] + r[0] * shift, base[1] + r[1] * shift];
  const at = (u, v = 0) => [centre[0] + r[0] * u * w + c[0] * v * d, centre[1] + r[1] * u * w + c[1] * v * d];
  const P = projector(PROPS.camera, DESIGN_VP[0] / DESIGN_VP[1]);
  const n = act.maxTargets; const spacing = w / n;
  const slots = [];
  for (let i = 0; i < n; i++) {
    const [x, z] = at(-0.5 + (i + 0.5) / n, 0);
    slots.push({ i, x, y: SLOT_Y, z, hitR: slotHitR(P, DESIGN_VP[0], x, SLOT_Y, z, r, n > 1 ? spacing : Math.min(w, d * 2)) });
  }
  return { ...geo, box: { centre, w, d, shift, fits: inside(shift) }, slots, at, spacing };
}

/** Level of a station from a raw kids-room snapshot (new ids under STORE_FIELD; old fields are never read or written). */
export function levelOf(PROPS, snap, st) {
  const ladder = st.ladder && QUESTS[st.ladder];
  if (!ladder) return 0;
  const v = snap?.[STORE_FIELD]?.[st.id];
  return Number.isSafeInteger(v) ? Math.max(0, Math.min(ladder.length - 1, v)) : 0;
}
export const nextStationLevel = (st, level) => (st.ladder && QUESTS[st.ladder] ? nextLevel(st.ladder, level) : level);

/**
 * Levels kept in the existing kids-room v1 snapshot (host.mjs roomLoad/roomSave, key stargarden.kids-room.v1, revision guard).
 * The raw snapshot is carried through untouched (old ids stay readable); only snapshot[STORE_FIELD][stationId] changes.
 * Without a host bridge (standalone page) it keeps the snapshot in `storage` under the dev key, like room_store.mjs.
 */
export function createLevelStore({ post, hasHost, storage = null, devKey = 'stargarden.kids-room.dev.v1' }) {
  let snap = null; let seq = 0; let loaded = false;
  const waiting = new Map();
  const ask = (type, payload = {}) => new Promise((resolve) => {
    const requestId = `scoop-st-${++seq}`;
    waiting.set(requestId, resolve);
    post({ type, requestId, ...payload });
    setTimeout(() => { if (waiting.delete(requestId)) resolve({ ok: false, value: null }); }, 7000);
  });
  async function load() {
    if (hasHost) { const m = await ask('roomLoad'); snap = m.ok && m.value && m.value.v === 1 ? m.value : null; }
    else { try { snap = JSON.parse(storage?.getItem(devKey) || 'null'); } catch (_) { snap = null; } }
    loaded = true;
    return snap;
  }
  async function save(id, level, retry = 1) {
    if (!loaded) await load();
    const cur = snap && snap.v === 1 ? snap : null;
    const rev = cur && Number.isSafeInteger(cur.revision) ? cur.revision : 0;
    const value = { ...(cur || { v: 1 }), revision: rev + 1, [STORE_FIELD]: { ...(cur?.[STORE_FIELD] || {}), [id]: level } };
    if (!hasHost) { snap = value; try { storage?.setItem(devKey, JSON.stringify(value)); } catch (_) { /* private mode: level lives for this visit */ } return true; }
    const m = await ask('roomSave', { value, expectedRevision: rev });
    if (m.ok) { snap = m.value && m.value.v === 1 ? m.value : value; return true; }
    if (retry > 0) { await load(); return save(id, level, retry - 1); }
    console.warn('[scoop] station level not saved', id, level);
    return false;
  }
  function receive(msg) {
    if (!msg || msg.type !== 'roomState' || typeof msg.requestId !== 'string' || !msg.requestId.startsWith('scoop-st-')) return false;
    const done = waiting.get(msg.requestId);
    if (done) { waiting.delete(msg.requestId); done({ ok: !!msg.ok, value: msg.value ?? null }); }
    return true;
  }
  return { load, save, receive, get snapshot() { return snap; }, get loaded() { return loaded; } };
}

// ------------------------------------------------------------------------------------------------ runtime (browser only)
const ICON_LABEL = { book: 'book', note: 'music', ball: 'ball', '123': 'numbers', palette: 'colours' };
function drawIcon(ctx2, icon, S) {
  const g = ctx2; const k = S / 128;
  g.save(); g.scale(k, k);
  g.fillStyle = '#FFFDF8'; g.strokeStyle = '#F97086'; g.lineWidth = 7;
  g.beginPath(); g.arc(64, 60, 52, 0, Math.PI * 2); g.fill(); g.stroke();
  g.beginPath(); g.moveTo(52, 108); g.lineTo(64, 124); g.lineTo(76, 108); g.closePath(); g.fillStyle = '#FFFDF8'; g.fill(); g.stroke();
  g.lineWidth = 6; g.lineJoin = 'round'; g.lineCap = 'round';
  const ink = '#34528F';
  if (icon === 'book') {
    g.fillStyle = '#FFE3E8'; g.strokeStyle = ink;
    for (const s of [-1, 1]) { g.beginPath(); g.moveTo(64, 44); g.quadraticCurveTo(64 + s * 18, 36, 64 + s * 34, 42); g.lineTo(64 + s * 34, 82); g.quadraticCurveTo(64 + s * 18, 76, 64, 84); g.closePath(); g.fill(); g.stroke(); }
  } else if (icon === 'note') {
    g.fillStyle = ink; g.strokeStyle = ink;
    g.beginPath(); g.ellipse(52, 82, 13, 10, -0.4, 0, Math.PI * 2); g.fill();
    g.beginPath(); g.moveTo(64, 80); g.lineTo(64, 32); g.quadraticCurveTo(80, 44, 84, 58); g.stroke();
  } else if (icon === 'ball') {
    g.fillStyle = '#76D9FC'; g.strokeStyle = ink;
    g.beginPath(); g.arc(64, 60, 28, 0, Math.PI * 2); g.fill(); g.stroke();
    g.strokeStyle = '#FFFDF8'; g.beginPath(); g.arc(64, 60, 28, -0.9, 0.9); g.stroke(); g.beginPath(); g.arc(64, 60, 28, Math.PI - 0.9, Math.PI + 0.9); g.stroke();
  } else if (icon === '123') {
    const dot = (x, y, col) => { g.fillStyle = col; g.beginPath(); g.arc(x, y, 8, 0, Math.PI * 2); g.fill(); };
    dot(38, 60, '#DD4E67');
    dot(64, 48, '#FDCD70'); dot(64, 72, '#FDCD70');
    dot(90, 38, '#5094F7'); dot(90, 60, '#5094F7'); dot(90, 82, '#5094F7');
  } else if (icon === 'palette') {
    g.fillStyle = '#FDF5E7'; g.strokeStyle = ink;
    g.beginPath(); g.ellipse(64, 60, 34, 27, 0, 0, Math.PI * 2); g.fill(); g.stroke();
    [['#DD4E67', 48, 50], ['#FDCD70', 66, 42], ['#5094F7', 82, 54], ['#58b98a', 70, 72]].forEach(([col, x, y]) => { g.fillStyle = col; g.beginPath(); g.arc(x, y, 7.5, 0, Math.PI * 2); g.fill(); });
  }
  g.restore();
}

/**
 * ctx (from main.mjs): THREE, PROPS, scene, A (animator), KIND_ANIM, SPRINKLES, sound, post, pickables, propById,
 * moa() -> Moa or null, groundY(x, z), reduced(), friendClips(root, clips) (moa.mjs), canvas.
 */
export function createStations(ctx) {
  const { THREE, PROPS, scene, A, sound, pickables, propById } = ctx;
  const table = (PROPS.stations || []).filter((st) => ACTIVITIES[st.activity] && hostOf(PROPS, st));
  const byId = new Map(table.map((st) => [st.id, st]));
  const byHost = new Map();
  for (const st of table) for (const h of [st.host, ...(st.also || [])]) byHost.set(h, st);
  const store = createLevelStore({ post: ctx.post, hasHost: !!window.StarGarden, storage: (() => { try { return window.localStorage; } catch (_) { return null; } })() });
  const ready = store.load().catch(() => null);
  const clips = new Map();
  const icons = new Map();
  const log = [];
  let cur = null; let seq = 0; let phase = 'idle';
  const V = (x, y, z) => new THREE.Vector3(x, y, z);
  const now = () => Math.round(performance.now());
  const note = (e) => { log.push({ ...e, t: now() }); if (log.length > 80) log.shift(); };
  const later = (ms, fn, token = cur?.token) => A.tween({ key: `st:${++seq}`, dur: 1, delay: ms, motion: false, update() {}, done: () => { if (token === undefined || cur?.token === token) fn(); } });

  // ---- clips: a friend GLB with animations plays them by name; otherwise the prop's procedural reaction (anim.mjs)
  function attach(prop, gltf) {
    if (prop && gltf?.animations?.length && byHost.has(prop.id)) {
      const root = prop.body.children[0];
      const player = root && ctx.friendClips?.(root, gltf.animations);
      if (player) clips.set(prop.id, player);
    }
    return prop;
  }
  function hostPlay(prop, name, variant = 0) {
    const p = clips.get(prop.id);
    if (p?.play(name)) return 'clip';
    const fn = ctx.KIND_ANIM[prop.entry.reaction];
    A.squash(prop.squash, name === CHEER ? 1.4 : 0.8, `${prop.id}:squash`);
    if (fn) fn(A, prop, { variant, combo: name === CHEER });
    return 'procedural';
  }
  function moaPlay(name) {
    const moa = ctx.moa(); if (!moa) return null;
    if (moa.clipInfo?.gestures?.[name]) return moa.gesture(name);
    const fb = MOA_FALLBACK[name] || name;
    return moa.gesture(fb);
  }

  // ---- icon bubbles over every station host (quiet, always there; pulse on tap) + hidden accessible buttons
  function buildIcons() {
    for (const st of table) {
      if (icons.has(st.id)) continue;
      const prop = propById.get(st.host); if (!prop) continue;
      const cv = document.createElement('canvas'); cv.width = cv.height = 128;
      drawIcon(cv.getContext('2d'), st.icon, 128);
      const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, opacity: 0.92, depthWrite: false, toneMapped: false }));
      const s = st.icon_m || 0.5; sp.scale.set(s, s, 1);
      const base = V(prop.anchor.position.x, prop.anchor.position.y + prop.entry.height_m + 0.3 + s * 0.5, prop.anchor.position.z);
      sp.position.copy(base); sp.renderOrder = 5;
      scene.add(sp);
      icons.set(st.id, { sp, base, s, ph: Math.random() * 6 });
    }
    if (ctx.canvas && !document.getElementById('sg-scoop-stations')) {
      const box = document.createElement('div'); box.id = 'sg-scoop-stations'; box.setAttribute('role', 'group'); box.setAttribute('aria-label', 'play');
      box.style.cssText = 'position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap';
      for (const st of table) {
        const b = document.createElement('button'); b.type = 'button';
        b.setAttribute('aria-label', `${st.host}: ${ICON_LABEL[st.icon] || st.activity}`);
        b.addEventListener('click', () => window.__scoop?.tap?.(st.host));
        box.appendChild(b);
      }
      ctx.canvas.after(box);
    }
  }
  function pulseIcon(st) {
    const ic = icons.get(st.id); if (!ic) return;
    A.tween({ key: `st:icon:${st.id}`, dur: 420, motion: false, update: (k) => { const s = ic.s * (1 + 0.35 * Math.sin(Math.PI * k)); ic.sp.scale.set(s, s, 1); ic.sp.material.opacity = 0.92 + 0.08 * Math.sin(Math.PI * k); } });
  }

  // ---- state machine: idle -> walking -> greet -> play -> celebrate -> fold -> idle
  function begin(st) {
    const moa = ctx.moa(); const host = propById.get(st.host);
    if (!moa || !host) return;
    const geo = stationGeometry(PROPS, st);
    const token = ++seq;
    cur = { st, geo, host, token, act: null, level: levelOf(PROPS, store.snapshot, st) };
    phase = 'walking'; note({ station: st.id, phase });
    const goal = geo.spot;
    const path = planPath(PROPS, [moa.position.x, moa.position.z], goal) || [{ x: goal[0], z: goal[1] }];
    const face = V(geo.hostPos[0], 0, geo.hostPos[1]);
    const step = (i) => {
      if (cur?.token !== token) return;
      if (i >= path.length) { arrive(token); return; }
      moa.walkTo(path[i].x, path[i].z, { faceTo: i === path.length - 1 ? face : undefined, onArrive: () => step(i + 1) });
    };
    step(0);
  }
  function arrive(token) {
    if (cur?.token !== token) return;
    const { st, host, geo } = cur;
    phase = 'greet'; note({ station: st.id, phase });
    ctx.moa()?.faceTo(V(geo.hostPos[0], 0, geo.hostPos[1]));
    moaPlay(GREET); hostPlay(host, GREET);
    if (st.words?.[0]) sound.word(st.words[0], 250);
    later(MS.greet, () => mount(token), token);
  }
  function mount(token) {
    if (cur?.token !== token) return;
    ready.then(() => {
      if (cur?.token !== token) return;
      cur.level = levelOf(PROPS, store.snapshot, cur.st);
      const { st, host, geo } = cur;
      const group = new THREE.Group(); group.name = `station:${st.id}`; scene.add(group);
      cur.group = group; cur.targets = [];
      phase = 'play'; note({ station: st.id, phase, level: cur.level });
      const actx = {
        THREE, A, sound, group, geo, host, station: st, level: cur.level, reduced: ctx.reduced, SPRINKLES: ctx.SPRINKLES,
        groundY: ctx.groundY, moa: ctx.moa, post: ctx.post, V,
        hostPlay: (name, variant) => hostPlay(host, name, variant), moaPlay,
        say: (w, delay = 120) => sound.word(w, delay),
        later: (ms, fn) => later(ms, fn, token),
        target(mesh, i) { mesh.userData.pick = `${st.id}:${i}`; pickables.push(mesh); cur.targets.push(mesh); return mesh; },
        untarget(mesh) { const k = pickables.indexOf(mesh); if (k >= 0) pickables.splice(k, 1); },
        done: (result = {}) => celebrate(token, result),
      };
      cur.act = ACTIVITIES[st.activity].mount(actx);
    });
  }
  function star(from) {
    const shape = new THREE.Shape();
    for (let i = 0; i < 10; i++) { const a = Math.PI / 2 + (i * Math.PI) / 5; const rr = i % 2 ? 0.09 : 0.2; i ? shape.lineTo(Math.cos(a) * rr, Math.sin(a) * rr) : shape.moveTo(Math.cos(a) * rr, Math.sin(a) * rr); }
    const geo = new THREE.ExtrudeGeometry(shape, { depth: 0.06, bevelEnabled: true, bevelSize: 0.02, bevelThickness: 0.02, bevelSegments: 1 });
    const mat = new THREE.MeshStandardMaterial({ color: 0xffd84d, emissive: 0xffc23d, emissiveIntensity: 0.6, transparent: true });
    const m = new THREE.Mesh(geo, mat); m.position.copy(from); scene.add(m);
    const cam = PROPS.camera.pos; const to = V(cam[0] + 2.6, cam[1] - 0.6, cam[2] - 4.5);
    const done = () => { scene.remove(m); geo.dispose(); mat.dispose(); };
    if (ctx.reduced()) { A.tween({ key: `st:star:${++seq}`, dur: 900, motion: false, update: (k) => { mat.opacity = 1 - k; }, done }); return; }
    A.tween({ key: `st:star:${++seq}`, dur: 1100, update: (k) => {
      const e = 1 - Math.pow(1 - k, 2);
      m.position.lerpVectors(from, to, e); m.position.y += Math.sin(Math.PI * k) * 1.2;
      m.rotation.y = k * Math.PI * 4; m.scale.setScalar(1 + Math.sin(Math.PI * k) * 0.8);
      mat.opacity = k > 0.85 ? (1 - k) / 0.15 : 1;
    }, done: () => { A.sparkle(to.clone(), 14); done(); } });
  }
  function celebrate(token, result) {
    if (cur?.token !== token || phase !== 'play') return;
    const { st, host, geo } = cur;
    phase = 'celebrate'; note({ station: st.id, phase, quiet: !!result.quiet });
    if (result.quiet) { later(result.foldMs ?? MS.fold, () => fold('done'), token); return; }
    moaPlay(CHEER); hostPlay(host, CHEER);
    sound.sfx('combo', { gain: 0.8 }); ctx.post({ type: 'sting', ms: 1200 });
    sound.word('yay', 350);
    const c = geo.box ? geo.box.centre : geo.spot;
    star(V(c[0], 0.7, c[1]));
    A.sparkle(V(c[0], 0.6, c[1]), 22);
    if (st.ladder) {
      const next = nextStationLevel(st, cur.level);
      note({ station: st.id, saved: next });
      store.save(st.id, next).catch(() => null);
    }
    later(MS.celebrate + MS.fold, () => fold('done'), token);
  }
  /** Fold the open station now (objects fade out); Moa stays where it is. */
  function fold(why = 'leave') {
    if (!cur) return;
    const c = cur; cur = null; phase = 'idle'; note({ station: c.st.id, phase: 'fold', why });
    for (const m of c.targets || []) { const k = pickables.indexOf(m); if (k >= 0) pickables.splice(k, 1); }
    try { c.act?.dispose?.(); } catch (err) { console.warn('[scoop] station dispose', err); }
    const g = c.group; if (!g) return;
    const mats = []; g.traverse((o) => { if (o.material) for (const m of [].concat(o.material)) { m.transparent = true; mats.push([m, m.opacity]); } });
    A.tween({ key: `st:fold:${c.token}`, dur: MS.foldFade, motion: false, update: (k) => { for (const [m, o] of mats) m.opacity = o * (1 - k); }, done: () => {
      scene.remove(g);
      g.traverse((o) => { if (o.geometry && !o.geometry.userData.shared) o.geometry.dispose(); if (o.material) for (const m of [].concat(o.material)) if (!m.userData.shared) m.dispose(); });
    } });
  }

  // ---- tap routing (main.mjs hooks)
  const TARGET_RE = /^([a-z]+):(\d+|next)$/;
  function feedbackAt(point) { A.sparkle(point, 6); sound.sfx('tap', { gain: 0.5 }); }
  /** tapProp hook. Returns a result (main returns it, the tap is used here) or null (main's reaction runs). */
  function onTap(id, point) {
    const m = TARGET_RE.exec(id);
    if (m && byId.has(m[1])) {
      const p = point || (cur?.geo.box ? V(cur.geo.box.centre[0], 0.4, cur.geo.box.centre[1]) : V(0, 0.4, 0));
      if (!cur || cur.st.id !== m[1] || phase !== 'play' || !cur.act) { feedbackAt(p); note({ id, ignored: phase }); return { id, kind: 'station', ignored: phase }; }
      const i = m[2] === 'next' ? cur.act.next?.() ?? 0 : +m[2];
      const out = cur.act.onTap(i, p) || {};
      note({ id, i, ...out });
      return { id, kind: 'station', i, ...out };
    }
    const st = byHost.get(id);
    if (st) {
      pulseIcon(st);
      if (cur && cur.st === st) {
        const host = propById.get(id);
        if (host) { A.squash(host.squash, 0.8, `${host.id}:squash`); A.sparkle(host.anchor.localToWorld(V(0, host.entry.height_m * 0.7, 0)), 8); }
        sound.sfx('tap', { gain: 0.5 }); if (st.words?.[0]) sound.word(st.words[0], 200);
        note({ id, station: st.id, again: phase });
        return { id, kind: 'station-host', station: st.id, phase };
      }
      fold('switch');
      queueMicrotask(() => begin(st));
      note({ id, station: st.id, start: true });
      return null;
    }
    if (cur) fold('away');
    return null;
  }
  function onGround() { if (cur) fold('ground'); }
  /** The tapProp route for this host waits for the station (the book station opens the route after the walk). */
  const ownsRoute = (id) => !!ACTIVITIES[byHost.get(id)?.activity]?.ownsRoute;
  const has = (id) => id === 'wait' || (TARGET_RE.test(id) && byId.has(TARGET_RE.exec(id)[1]));
  function tapId(id) {
    if (id === 'wait') return { id, kind: 'wait' };
    return onTap(id, null);
  }
  function update(dt) {
    if (!icons.size && propById.size) buildIcons();
    if (!ctx.reduced()) for (const ic of icons.values()) ic.sp.position.y = ic.base.y + Math.sin(A.time * 1.6 + ic.ph) * 0.04;
    for (const p of clips.values()) p.update(dt);
    cur?.act?.update?.(dt);
  }
  function state() {
    return { phase, station: cur?.st.id || null, level: cur?.level ?? null, act: cur?.act?.state?.() || null, levels: { ...(store.snapshot?.[STORE_FIELD] || {}) }, clips: [...clips.keys()], log: log.slice(-24) };
  }
  return { attach, onTap, onGround, ownsRoute, has, tapId, update, receive: (c) => { let m = c; if (typeof m === 'string') { try { m = JSON.parse(m); } catch (_) { return false; } } return store.receive(m); }, state, fold, table };
}
