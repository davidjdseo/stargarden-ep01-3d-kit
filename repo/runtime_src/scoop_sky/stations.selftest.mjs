// node runtime_src/scoop_sky/stations.selftest.mjs -> one line per check, per station and viewport.
// Exit 0 = all pass; 1 = a LOGIC FAIL (station code, data contract, rules, store, wiring); 2 = logic clean but a station is
// BLOCKED-BY-LAYOUT <ids> (props.json positions/camera: the prop/set ids that block it are named; fix the layout or the row).
// Reads props.json (live layout: main moves hosts/camera) and the station modules only. NEED lines print what each station
// asks of the layout (free lawn strip, depth band, px per target). Missing room-word files are listed as pending_words.
// Portrait (390x844, host always shows landscape): only stations with <= 3 targets must be in frame; the rest is INFO.
import { readFileSync, existsSync } from 'node:fs';
import { projector, tappables, setOccluders, screenBox, EDGE_MARGIN_NDC, MAX_COVER } from './layout.mjs';
import { ACTIVITIES, TARGET_PX, VIEWPORTS, DESIGN_VP, stationGeometry, hostOf, planPath, spotFree, navManifest, clearanceM, footOf, createLevelStore, levelOf, nextStationLevel, STORE_FIELD } from './stations.mjs';
import { wordPath, ROOM_WORDS } from './sound.mjs';
import { KINDS } from './reactions.mjs';
import { hostPlan, moaPlan, MOA_PROCEDURAL, GREET, CHEER, iconPos, PIECE_M } from './stations.mjs';
import { QUESTS } from '../aquarium_cafe/room_core.mjs';
import { obstacleDistance } from '../aquarium_cafe/nav_core.mjs';
import { PHRASES } from './activities/music.mjs';
import { fillSlots, pickColour } from './activities/colours.mjs';

let fails = 0; let blocked = 0;
const check = (name, ok, info = '') => { console.log(`${ok ? 'PASS' : 'FAIL'} ${name}${info ? ' - ' + info : ''}`); if (!ok) fails += 1; };
/** Layout check: a failure is BLOCKED-BY-LAYOUT with the blocking ids (props.json), not a logic FAIL. */
const layout = (name, ok, ids = [], info = '') => {
  const u = [...new Set(ids)];
  console.log(`${ok ? 'PASS' : 'BLOCKED-BY-LAYOUT ' + (u.join(',') || 'camera/frame')} ${name}${info ? ' - ' + info : ''}`);
  if (!ok) blocked += 1;
};
const PROPS = JSON.parse(readFileSync(new URL('./props.json', import.meta.url), 'utf8'));
const ROOT = new URL('../../', import.meta.url);
const ST = PROPS.stations || [];
const NEED = { book: 'cottage', music: 'piyo', ball: 'popo', numbers: 'nuri', colours: 'mongsil' };
const ICONS = ['book', 'note', 'ball', '123', 'palette'];

// ---- 1. table
check('props.json has a stations array with book, music, ball, numbers, colours', Array.isArray(ST) && Object.keys(NEED).every((id) => ST.some((s) => s.id === id)), ST.map((s) => s.id).join());
check('station ids unique', new Set(ST.map((s) => s.id)).size === ST.length);
for (const st of ST) {
  const miss = ['id', 'host', 'activity', 'icon', 'words', 'host_clip', 'moa_clip', 'ladder', 'spot', 'box'].filter((k) => !(k in st));
  check(`${st.id}: fields {id, host, activity, icon, words, host_clip, moa_clip, ladder, spot, box}`, miss.length === 0, miss.join());
  check(`${st.id}: host '${st.host}' exists in props${st.also ? ' (also ' + st.also.join() + ')' : ''}`, !!hostOf(PROPS, st) && (st.also || []).every((id) => PROPS.props.some((p) => p.id === id)));
  check(`${st.id}: host matches the design table (${NEED[st.id] || 'extra station'})`, !NEED[st.id] || st.host === NEED[st.id], st.host);
  check(`${st.id}: activity module '${st.activity}' exists`, !!ACTIVITIES[st.activity]);
  check(`${st.id}: icon is a drawn glyph (${ICONS.join('/')})`, ICONS.includes(st.icon), st.icon);
  check(`${st.id}: ladder is null or a room_core QUESTS key`, st.ladder === null || !!QUESTS[st.ladder], String(st.ladder));
  check(`${st.id}: box present iff the activity has targets`, !!st.box === !!ACTIVITIES[st.activity]?.maxTargets);
}
const hostIds = ST.flatMap((s) => [s.host, ...(s.also || [])]);
check('one station per host (a tap names exactly one station)', new Set(hostIds).size === hostIds.length, hostIds.join());

// ---- 2. spots and walking
const clr = clearanceM(PROPS);
const moaStart = PROPS.moa.start;
const geos = new Map(ST.filter((s) => hostOf(PROPS, s)).map((s) => [s.id, stationGeometry(PROPS, s)]));
const man = navManifest(PROPS);
for (const [id, g] of geos) {
  const [x, z] = g.spot;
  layout(`${id}: spot (${x.toFixed(2)}, ${z.toFixed(2)}) on the walkable lawn (r <= ${PROPS.island.walk_radius_m})`, Math.hypot(x, z) <= PROPS.island.walk_radius_m, ['island'], Math.hypot(x, z).toFixed(2));
  const near = man.obstacles.map((o) => [o.id, obstacleDistance(o, x, z)]).filter(([, d]) => d < clr);
  layout(`${id}: spot >= ${clr} m (island prop_clearance / MIN_GAP) from every prop and set footprint`, spotFree(PROPS, g.spot) && near.length === 0, near.map(([o]) => o), near.map(([o, d]) => `${o} ${d.toFixed(2)}`).join(', '));
  const path = planPath(PROPS, moaStart, g.spot);
  layout(`${id}: Moa can walk there from the start around every footprint`, !!path, near.map(([o]) => o), path ? `${path.length} legs` : 'no path');
  const unreach = [...geos].filter(([id2, g2]) => id2 !== id && !planPath(PROPS, g2.spot, g.spot)).map(([id2]) => id2);
  layout(`${id}: reachable from every other station spot`, unreach.length === 0, near.map(([o]) => o), unreach.join());
  const onTargets = g.slots.filter((s) => Math.hypot(s.x - x, s.z - z) < s.hitR + PROPS.moa.footprint_m * 0.5);
  layout(`${id}: Moa's spot clear of its own targets`, onTargets.length === 0, ['station row spot/box'], onTargets.map((s) => 't' + s.i).join());
}

// ---- 3. play boxes: on the lawn, clear of props, targets in frame, >= 88 px, no overlap, not covered
for (const [id, g] of geos) {
  if (!g.box) continue;
  layout(`${id}: box ${g.box.w}x${g.box.d} m fits on the lawn (shift ${g.box.shift.toFixed(2)} m)`, g.box.fits, ['island']);
  const hits = [];
  for (let u = -0.5; u <= 0.5001; u += 0.25) for (let v = -0.5; v <= 0.5001; v += 0.5) {
    const [x, z] = g.at(u, v);
    for (const o of man.obstacles) { const d = obstacleDistance(o, x, z); if (d < 0.12) hits.push([o.id, `${o.id}@(${u},${v}) ${d.toFixed(2)}`]); }
  }
  const h = hostOf(PROPS, { host: g.host });
  layout(`${id}: box area free of prop/set footprints (host ${g.host} included)`, hits.length === 0, hits.map(([o]) => o), hits.slice(0, 4).map(([, t]) => t).join(', '));
  layout(`${id}: box clears its host's footprint`, Math.hypot(...g.at(0, -0.5).map((v, k) => v - h.pos[k])) >= footOf(h) + 0.25, [g.host]);
  {
    const P = projector(PROPS.camera, DESIGN_VP[0] / DESIGN_VP[1]);
    const zb = g.slots.map((s) => P([s.x, s.y, s.z])[1]);
    console.log(`NEED ${id}: ${g.slots.length} target(s) need a free lawn strip ${g.box.w.toFixed(2)} x ${g.box.d.toFixed(2)} m centred (${g.box.centre.map((v) => v.toFixed(2)).join(', ')}), along screen-right, ${g.spacing.toFixed(2)} m per target (hit r ${Math.min(...g.slots.map((s) => s.hitR)).toFixed(2)} m), target centres at NDC y ${Math.min(...zb).toFixed(2)}..${Math.max(...zb).toFixed(2)} @844x390 (frame bottom -0.92); Moa spot (${g.spot.map((v) => v.toFixed(2)).join(', ')})`);
  }
  const blockersBase = [...tappables(PROPS).filter((t) => t.id !== 'moa'), ...setOccluders(PROPS)];
  const moaAt = { id: 'moa@spot', x: g.spot[0], y0: 0, z: g.spot[1], h: PROPS.moa.height_m, hw: (PROPS.moa.half_wd || [PROPS.moa.footprint_m])[0], hd: (PROPS.moa.half_wd || [0, PROPS.moa.footprint_m])[1] };
  for (const [W, H] of VIEWPORTS) {
    const P = projector(PROPS.camera, W / H);
    const lim = 1 - EDGE_MARGIN_NDC;
    const blockers = [...blockersBase, moaAt].map((t) => ({ ...t, box: screenBox(P, t.x, t.y0, t.z, t.h, t.hw, t.hd) }));
    const bad = []; const px = []; const who = [];
    const boxes = g.slots.map((s) => {   // a sphere projects as a circle: centre +- its projected radius (screen-right width)
      const c = P([s.x, s.y, s.z]); const a = P([s.x - g.r[0] * s.hitR, s.y, s.z - g.r[1] * s.hitR]); const b = P([s.x + g.r[0] * s.hitR, s.y, s.z + g.r[1] * s.hitR]);
      const rx = Math.abs(b[0] - a[0]) / 2; const ry = rx * W / H;
      return { x0: c[0] - rx, x1: c[0] + rx, y0: c[1] - ry, y1: c[1] + ry, depth: c[2] };
    });
    g.slots.forEach((s, k) => {
      const b = boxes[k];
      if (b.x0 < -lim || b.x1 > lim || b.y0 < -lim || b.y1 > lim) { bad.push(`t${s.i} edge [${b.x0.toFixed(2)},${b.x1.toFixed(2)}]x[${b.y0.toFixed(2)},${b.y1.toFixed(2)}]`); who.push('camera/frame'); }
      const c = P([s.x, s.y, s.z]); const l = P([s.x - g.r[0] * s.hitR, s.y, s.z - g.r[1] * s.hitR]); const r = P([s.x + g.r[0] * s.hitR, s.y, s.z + g.r[1] * s.hitR]);
      px.push({ d: Math.abs(r[0] - l[0]) * W / 2, cx: c[0] * W / 2, cy: c[1] * H / 2 });
      const area = (b.x1 - b.x0) * (b.y1 - b.y0);
      for (const o of blockers) {
        if (o.box.depth >= b.depth) continue;
        const w = Math.min(b.x1, o.box.x1) - Math.max(b.x0, o.box.x0); const hh = Math.min(b.y1, o.box.y1) - Math.max(b.y0, o.box.y0);
        if (w > 0 && hh > 0 && (w * hh) / area > MAX_COVER) { bad.push(`t${s.i} covered ${((w * hh) / area * 100).toFixed(0)}% by ${o.id}`); who.push(o.id); }
      }
    });
    for (let k = 1; k < px.length; k++) {
      const gap = Math.hypot(px[k].cx - px[k - 1].cx, px[k].cy - px[k - 1].cy);
      if (gap < (px[k].d + px[k - 1].d) / 2 - 0.5) { bad.push(`t${k - 1}/t${k} overlap ${gap.toFixed(0)}px < ${((px[k].d + px[k - 1].d) / 2).toFixed(0)}px`); who.push('station-row'); }
    }
    const minPx = Math.min(...px.map((p) => p.d));
    {   // the host stays visible: play pieces (upright PIECE_M box per slot) in front of it cover <= MAX_COVER of it (w7 music capture: a bar hid Piyo)
      const hb = blockers.find((o) => o.id === g.host)?.box;
      const cov = hb ? g.slots.map((s) => { const b = screenBox(P, s.x, 0, s.z, PIECE_M[0], PIECE_M[1], PIECE_M[1]); if (b.depth >= hb.depth) return 0; const w = Math.min(b.x1, hb.x1) - Math.max(b.x0, hb.x0); const hh = Math.min(b.y1, hb.y1) - Math.max(b.y0, hb.y0); return w > 0 && hh > 0 ? (w * hh) / ((hb.x1 - hb.x0) * (hb.y1 - hb.y0)) : 0; }) : [];
      const worst = Math.max(0, ...cov);
      if (W >= H) layout(`${id} @${W}x${H}: its play pieces cover <= ${MAX_COVER * 100}% of the host ${g.host}`, worst <= MAX_COVER, ['station row spot/box', g.host], `${(worst * 100).toFixed(0)}% by t${cov.indexOf(worst)}`);
    }
    const name = `${id} @${W}x${H}: ${g.slots.length} targets inside the ${EDGE_MARGIN_NDC / 2 * 100}% margin, no overlap, <= ${MAX_COVER * 100}% covered by a nearer object`;
    if (W < H && g.slots.length > 3) console.log(`INFO ${name}: ${bad.length ? bad.slice(0, 3).join('; ') : 'ok'} (portrait checks <= 3-target stations only)`);
    else if (W < H) { const edge = bad.filter((b) => b.includes('edge')); layout(`${id} @${W}x${H}: ${g.slots.length} targets in frame (portrait)`, edge.length === 0, ['camera/frame'], edge.slice(0, 3).join('; ')); }
    else layout(name, bad.length === 0, who, bad.slice(0, 4).join('; '));
    if (W === DESIGN_VP[0] && H === DESIGN_VP[1]) layout(`${id} @${W}x${H}: every target >= ${TARGET_PX} px (min ${minPx.toFixed(0)} px)`, minPx >= TARGET_PX, ['box too narrow for the depth: widen box.w or move the strip nearer the camera'], px.map((p) => p.d.toFixed(0)).join('/'));
    else console.log(`INFO ${id} @${W}x${H}: target px ${px.map((p) => p.d.toFixed(0)).join('/')}`);
  }
}
// icon bubbles in frame
for (const [W, H] of VIEWPORTS) {
  const P = projector(PROPS.camera, W / H);
  const out = ST.filter((s) => hostOf(PROPS, s)).filter((s) => { const q = P(iconPos(PROPS, s)); return Math.abs(q[0]) > 0.94 || Math.abs(q[1]) > 0.94; });
  if (W < H) console.log(`INFO @${W}x${H}: icon bubbles out of frame: ${out.map((s) => s.id).join() || 'none'}`);
  else layout(`@${W}x${H}: every station icon bubble is in frame`, out.length === 0, out.map((s) => s.host), out.map((s) => s.id).join());
}

// ---- 4. words: every word a station can say has a voice file, or is pending (room words main is generating)
const pending = new Set(); const missingBook = new Set(); const said = new Set();
for (const st of ST) {
  const act = ACTIVITIES[st.activity]; if (!act) continue;
  const words = new Set(st.words || []);
  for (let l = 0; l < (act.levels || 1); l++) for (const w of act.words(l)) words.add(w);
  for (const w of words) {
    said.add(w);
    if (existsSync(new URL(wordPath(w), ROOT))) continue;
    if (ROOM_WORDS.has(w)) pending.add(w); else missingBook.add(w);
  }
}
check('every station word is a book word file or a listed room word (no fetch can 404 on an unknown word)', missingBook.size === 0, [...missingBook].join());
console.log(`INFO station words: ${said.size}; pending_words: ${pending.size ? [...pending].join(',') : 'none'}`);

// ---- 5. ladders: every level of every activity can be finished by taps alone, and levels persist
{
  check('music: one phrase per QUESTS.xylophone level, same lengths, bars 0..4', PHRASES.length === QUESTS.xylophone.length && PHRASES.every((p, i) => p.length === QUESTS.xylophone[i] && p.every((n) => n >= 0 && n <= 4)));
  for (let l = 0; l < QUESTS.xylophone.length; l++) {
    const g = ACTIVITIES.music.rules(l); const ph = g.phrase; let r = null;
    const wrong = g.press((ph[0] + 1) % 5); for (const n of ph) r = g.press(n);
    if (r?.result !== 'phrase_done' || wrong.result !== 'retry') check(`music level ${l} finishes by repeating the phrase (a wrong bar restarts)`, false, `${wrong.result}/${r?.result}`);
  }
  for (let l = 0; l < QUESTS.counting.length; l++) {
    const R = ACTIVITIES.numbers.rules(l); let r; let taps = 0; let maxBatch = 0;
    while (R.count < R.goal && taps < 100) { const k = R.lay(); maxBatch = Math.max(maxBatch, k); for (let i = 0; i < k; i++) { r = R.take(); taps += 1; } }
    if (r?.result !== 'done' || R.count !== QUESTS.counting[l] || maxBatch > ACTIVITIES.numbers.maxTargets) check(`numbers level ${l} counts to ${QUESTS.counting[l]} in batches <= ${ACTIVITIES.numbers.maxTargets}`, false, `${R.count} ${r?.result}`);
    const B = ACTIVITIES.ball.rules(l); let b; for (let i = 0; i < B.goal; i++) b = B.pass();
    if (b.result !== 'done' || b.n !== QUESTS.counting[l]) check(`ball level ${l} ends after ${QUESTS.counting[l]} passes`, false);
  }
  for (let l = 0; l < QUESTS.sorting.length; l++) {
    const round = ACTIVITIES.colours.rules(l); const f = fillSlots(round); let r = null; let n = 0; let stuck = '';
    while (!round.done && n < 60) {
      const i = f.slots.findIndex((k) => k === round.call);
      if (i < 0) { stuck = `call ${round.colors[round.call].en} not on the lawn`; break; }
      const k = f.slots[i]; r = round.press(k); f.visible[k] -= 1; n += 1;
      const nk = pickColour(f.unshown, f.visible, round.call); f.slots[i] = nk; if (nk >= 0) { f.unshown[nk] -= 1; f.visible[nk] += 1; }
    }
    if (r?.result !== 'done' || stuck) check(`colours level ${l} sorts every candy with the called colour always visible`, false, stuck || r?.result);
  }
  check('numbers/ball/colours/music ladders all finish (silent = pass)', true);
  // clip fallback: GLBs without clips (today's friends) -> the host's procedural reaction kind; Moa -> a procedural gesture
  const names = [GREET, CHEER, 'happy', ...ST.flatMap((s) => [s.host_clip, s.moa_clip])].filter(Boolean);
  const badPlan = [];
  for (const st of ST) {
    const h = hostOf(PROPS, st); if (!h) continue;
    for (const n of names) {
      const none = hostPlan(h, () => false, n); const some = hostPlan(h, (x) => x === n, n);
      if (!KINDS.includes(none.procedural) || some.clip !== n) badPlan.push(`${st.host}:${n}`);
    }
  }
  for (const n of names) { const m = moaPlan({}, n); if (!MOA_PROCEDURAL.includes(m.procedural) || moaPlan({ [n]: 'x' }, n).clip !== n) badPlan.push(`moa:${n}`); }
  check(`clip fallback: with no clips every host (${ST.map((s) => s.host).join()}) and Moa play a procedural move for ${[...new Set(names)].join('/')}; with the clip they play it`, badPlan.length === 0, badPlan.join());
  // persistence through the host protocol (host.mjs roomStorage copy: revision guard, raw value kept)
  const KEY = 'stargarden.kids-room.v1'; const ls = new Map([[KEY, JSON.stringify({ v: 1, revision: 4, hearts: 7, quests: { counting: 3, xylophone: 2 } })]]);
  let store;
  const hostPost = (m) => queueMicrotask(() => {
    let cur = JSON.parse(ls.get(KEY) || 'null'); if (!cur || cur.v !== 1) cur = null;
    const reply = (ok, value) => store.receive({ type: 'roomState', requestId: m.requestId, ok, value });
    if (m.type === 'roomLoad') return reply(true, cur);
    const v = m.value;
    if (!v || v.v !== 1 || (cur ? cur.revision : 0) !== m.expectedRevision || v.revision !== m.expectedRevision + 1) return reply(false);
    ls.set(KEY, JSON.stringify(v)); return reply(true, v);
  });
  store = createLevelStore({ post: hostPost, hasHost: true });
  await store.load();
  const num = ST.find((s) => s.id === 'numbers');
  const l0 = levelOf(PROPS, store.snapshot, num);
  await store.save('numbers', nextStationLevel(num, l0));
  const bump = JSON.parse(ls.get(KEY)); bump.revision += 1; ls.set(KEY, JSON.stringify(bump));   // another writer saved meanwhile
  await store.save('ball', 2);
  const store2 = createLevelStore({ post: (m) => { store = store2; hostPost(m); }, hasHost: true }); store = store2;
  await store2.load();
  const snap = store2.snapshot;
  check('levels persist: numbers 0 -> 1, ball 2, saved through roomLoad/roomSave after a stale revision', levelOf(PROPS, snap, num) === 1 && snap[STORE_FIELD]?.ball === 2, JSON.stringify(snap[STORE_FIELD]));
  check('old ids stay readable: quests/hearts untouched, revision advanced', snap.quests?.counting === 3 && snap.quests?.xylophone === 2 && snap.hearts === 7 && snap.revision === 7, `rev ${snap.revision}`);
  check('level caps at the top of the ladder', nextStationLevel(num, QUESTS.counting.length - 1) === QUESTS.counting.length - 1 && levelOf(PROPS, { [STORE_FIELD]: { numbers: 99 } }, num) === QUESTS.counting.length - 1);
}

// ---- 6. wiring and generality (mechanical causes only)
{
  const main = readFileSync(new URL('./main.mjs', import.meta.url), 'utf8');
  const hooks = main.split('\n').filter((l) => /\/\/ stations\b/.test(l) && !/stations \(w7\)/.test(l));
  const block = /\/\/ ---- stations \(w7\)[^\n]*BEGIN[\s\S]*\/\/ ---- stations \(w7\)[^\n]*END/.test(main);
  const calls = ['stations.onTap(', 'stations.onGround(', 'stations.ownsRoute(', 'stations.tapId(', 'stations.update(', 'stations.attach('];
  const missing = calls.filter((c) => !main.includes(c));
  check('main.mjs: marked block + every hook wired (onTap, onGround, ownsRoute, tapId, update, attach)', block && missing.length === 0, missing.join());
  check('main.mjs: at most 6 tagged hook lines outside the block', hooks.length <= 6, String(hooks.length));
  const ids = [...PROPS.props.map((p) => p.id), 'moa'];
  const leaks = Object.keys(ACTIVITIES).flatMap((a) => {
    const src = readFileSync(new URL(`./activities/${a}.mjs`, import.meta.url), 'utf8');
    return ids.filter((id) => new RegExp(`['"\`]${id}['"\`]`).test(src)).map((id) => `${a}:${id}`);
  });
  check('activity modules are world-agnostic (no prop/host ids inside; hosts and words come from data)', leaks.length === 0, leaks.join());
}
console.log(fails ? `${fails} FAIL (logic), ${blocked} BLOCKED-BY-LAYOUT` : blocked ? `logic all PASS; ${blocked} BLOCKED-BY-LAYOUT (exit 2: props.json layout)` : 'all PASS');
process.exit(fails ? 1 : blocked ? 2 : 0);
