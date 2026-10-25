// node runtime_src/scoop_sky/reactions.selftest.mjs  -> one PASS/FAIL line per case, exit 1 on any FAIL.
// Also checks props.json against the brief's table contract (>= 10 props, required fields, >= 6 reaction kinds,
// every route is one the web host handles).
import { readFileSync, existsSync } from 'node:fs';
import { litCream, rgbDist, lightNeutralMult, PLAIN } from './shade.mjs';
import { createHash } from 'node:crypto';
import { MIN_GAP_M, onPath, groundFootprints, projector, frameShare, framingProblems, MAX_COVER, EDGE_MARGIN_NDC } from './layout.mjs';
import { createReactions, COMBO_TAPS, COMBO_WINDOW_MS, SAY_FIRST, SAY_REST_MS, VARIANTS, KINDS } from './reactions.mjs';

let fails = 0;
const check = (name, ok, info = '') => { console.log(`${ok ? 'PASS' : 'FAIL'} ${name}${info ? ' - ' + info : ''}`); if (!ok) fails += 1; };
const clock = () => { let t = 0; return { now: () => t, step: (ms) => { t += ms; } }; };
const table = [{ id: 'flower', reaction: 'bloom', word: 'flower' }, { id: 'can', reaction: 'pour', word: 'water' }, { id: 'quiet', reaction: 'puff' }];

{
  const c = clock(); const r = createReactions(table, c);
  const v = []; for (let i = 0; i < 7; i++) { v.push(r.tap('flower').variant); c.step(1000); }
  check('variant cycles 0,1,2 per object', v.join() === '0,1,2,0,1,2,0', v.join());
  check('variant is per object', r.tap('can').variant === 0);
  check('unknown id -> null', r.tap('nope') === null);
  check('kind comes from table', r.tap('can').kind === 'pour');
}
{
  const c = clock(); const r = createReactions(table, c);
  const combos = []; for (let i = 0; i < COMBO_TAPS * 2; i++) { combos.push(r.tap('flower').combo); c.step(400); }
  check(`combo on tap ${COMBO_TAPS} within ${COMBO_WINDOW_MS} ms, then resets`, combos.map(Number).join('') === '0000100001', combos.map(Number).join(''));
}
{
  const c = clock(); const r = createReactions(table, c);
  const combos = []; for (let i = 0; i < COMBO_TAPS; i++) { combos.push(r.tap('flower').combo); c.step(COMBO_WINDOW_MS / (COMBO_TAPS - 1) + 50); }
  check('no combo when the 5 taps span more than the window', !combos.includes(true), combos.map(Number).join(''));
}
{
  const c = clock(); const r = createReactions(table, c);
  r.tap('flower'); c.step(100); r.tap('can'); c.step(100);
  const mix = []; for (let i = 0; i < 4; i++) { mix.push(r.tap('flower').combo); c.step(100); r.tap('can'); c.step(100); }
  check('combo counts the same object only', mix.filter(Boolean).length === 1 && mix[3] === true, mix.map(Number).join(''));
}
{
  const c = clock(); const r = createReactions(table, c);
  const says = []; for (let i = 0; i < 5; i++) { says.push(r.tap('flower').say); c.step(1000); }
  check(`say on taps 1-${SAY_FIRST}, then null`, JSON.stringify(says) === JSON.stringify(['flower', 'flower', 'flower', null, null]), JSON.stringify(says));
  c.step(SAY_REST_MS - 1000 - 1);
  check('still null just before the rest time', r.tap('flower').say === null);
  c.step(SAY_REST_MS);
  check(`say again after ${SAY_REST_MS / 1000} s without a tap`, r.tap('flower').say === 'flower');
  check('say has no word -> null', r.tap('quiet').say === null);
}
{
  const c = clock(); const r = createReactions([{ id: 'piyo', reaction: 'friend', word: 'bird', words: ['bird', 'sing'] }], c);
  const says = []; for (let i = 0; i < 4; i++) { says.push(r.tap('piyo').say); c.step(500); }
  check('words say in turn (bird, sing, bird) inside the 3-say throttle', JSON.stringify(says) === JSON.stringify(['bird', 'sing', 'bird', null]), JSON.stringify(says));
  c.step(SAY_REST_MS);
  check('word turn restarts after the rest', r.tap('piyo').say === 'bird');
  check('friend kind is a known KIND', KINDS.includes('friend'));
}
{
  const props = JSON.parse(readFileSync(new URL('./props.json', import.meta.url), 'utf8'));
  const need = ['id', 'stand', 'pos', 'height_m', 'word', 'reaction'];
  const bad = props.props.filter((p) => need.some((k) => p[k] === undefined) || !Array.isArray(p.pos) || p.pos.length !== 2);
  check('props.json has >= 10 props', props.props.length >= 10, String(props.props.length));
  check('every prop has id, stand, pos[x,z], height_m, word, reaction', bad.length === 0, bad.map((p) => p.id).join());
  check('prop ids unique', new Set(props.props.map((p) => p.id)).size === props.props.length);
  const kinds = new Set([...props.props.map((p) => p.reaction), props.moa.reaction]);
  check('>= 6 distinct reaction kinds', kinds.size >= 6, [...kinds].join());
  const missingKinds = [...kinds].filter((k) => !KINDS.includes(k));
  check('every kind in props.json is a known KIND (anim.mjs throws at load if one has no animation)', missingKinds.length === 0, missingKinds.join());
  const HOST_ROUTES = ['/books'];
  const routes = props.props.filter((p) => p.route).map((p) => p.route.route);
  check('every route is handled by the web host (host.mjs)', routes.every((x) => HOST_ROUTES.includes(x)), routes.join());
  check('variants constant is 3', VARIANTS === 3);
  const isl = props.island;
  const feet = [...groundFootprints(props.props), { id: 'moa', x: props.moa.start[0], z: props.moa.start[1], r: props.moa.footprint_m }];
  const tight = [];
  for (let i = 0; i < feet.length; i++) for (let j = i + 1; j < feet.length; j++) {
    const a = feet[i]; const b = feet[j]; const gap = Math.hypot(a.x - b.x, a.z - b.z) - a.r - b.r;
    if (gap < MIN_GAP_M - 1e-6) tight.push(`${a.id}/${b.id} ${gap.toFixed(2)}`);
  }
  check(`ground footprints keep >= ${MIN_GAP_M} m apart`, tight.length === 0, tight.join(', '));
  const out = feet.filter((f) => Math.hypot(f.x, f.z) + f.r > isl.radius_m);
  check('every footprint inside the island rim', out.length === 0, out.map((f) => f.id).join());
  const blocking = groundFootprints(props.props).filter((f) => f.id !== 'cottage' && onPath(f.x, f.z, isl.path, f.r));
  check('no prop sits on the cookie path (the cottage ends it)', blocking.length === 0, blocking.map((f) => f.id).join());
  const pk = ['pos', 'target', 'fov_landscape', 'fov_portrait', 'why'];
  const mf = props.camera.min_frame_frac;
  const P = projector(props.camera, mf.aspect[0] / mf.aspect[1]);
  const small = [];
  const moaS = frameShare(P, props.moa.start[0], 0, props.moa.start[1], props.moa.height_m);
  if (moaS.frac < mf.moa || !moaS.inFrame) small.push(`moa ${moaS.frac.toFixed(3)}`);
  for (const p of props.props) {
    if (p.sky) continue;
    const s = frameShare(P, p.pos[0], p.y || 0, p.pos[1], p.height_m);
    const need = p.friend ? mf.friend : mf.prop;
    if (s.frac < need || !s.inFrame) small.push(`${p.id} ${s.frac.toFixed(3)}${s.inFrame ? '' : ' out-of-frame'}`);
  }
  check(`at ${mf.aspect.join('x')} every prop/friend/Moa is in frame and >= its min share (${mf.prop}/${mf.friend}/${mf.moa})`, small.length === 0, small.join(', '));
  const fr = props.props.filter((p) => p.friend);
  const wordDir = new URL('../../reader/v2-20261012/classic-book/books/bo-sky-island/words/en/', import.meta.url);
  const allWords = new Set([props.moa.word, ...(props.moa.words || []), ...props.props.flatMap((p) => [p.word, ...(p.words || [])])].filter(Boolean));
  const noFile = [...allWords].filter((w) => !existsSync(new URL(w + '.mp3', wordDir)));
  check('every word has a book voice file (words/en/<word>.mp3)', noFile.length === 0, noFile.join());
  for (const asp of [[844, 390], [1280, 800]]) {
    const fp = framingProblems(props, asp[0] / asp[1]);
    check(`at ${asp.join('x')} every tappable keeps a ${EDGE_MARGIN_NDC / 2 * 100}% edge margin and is <= ${MAX_COVER * 100}% covered by a nearer one`, fp.length === 0, fp.join('; '));
  }
  check('4 friends, each with words from the book list and a style', fr.length === 4 && fr.every((p) => p.words?.length && p.style));
  check('camera block complete (pos, target, fovs, why) and fov <= 42', pk.every((k) => props.camera[k] !== undefined) && props.camera.fov_landscape <= 42);
  const skyZ = Math.min(...props.props.filter((p) => p.sky).map((p) => p.pos[1]));
  const near = props.set.clouds.filter(([x, , z]) => !(z < -3 || Math.abs(x) > 7) || z >= skyZ);
  check('clouds sit behind the island (z < -3 or |x| > 7) and behind every sky prop', near.length === 0, JSON.stringify(near));
  // look: GLB colour factor comes from the lights block only; look.json (tool/room_tex_means.py) reports texture vs sheet
  const LOOK = JSON.parse(readFileSync(new URL('../../assets/room/scoop/look.json', import.meta.url), 'utf8'));
  const lk = props.look; const glbIds = [...new Set(props.props.map((p) => p.glb).filter(Boolean)), 'moa'];
  const stale = glbIds.filter((g) => !LOOK[g] || createHash('sha256').update(readFileSync(new URL('../../' + LOOK[g].glb, import.meta.url))).digest('hex') !== LOOK[g].glb_sha256);
  check('look.json measured the GLBs that ship (sha256 match; rerun tool/room_tex_means.py)', stale.length === 0, stale.join());
  const mult = lightNeutralMult(props.lights, lk.normal);
  const s2l = (c) => (c / 255 <= 0.04045 ? c / 255 / 12.92 : ((c / 255 + 0.055) / 1.055) ** 2.4);
  const mid = glbIds.filter((g) => Math.max(...LOOK[g].basecolor_mean_srgb.map(s2l)) < 0.76);   // below the tone map shoulder
  const drift = mid.map((g) => [g, rgbDist(litCream(LOOK[g].basecolor_mean_srgb, { ...PLAIN, color_mult: mult, emissive: [1, 1, 1], emissive_intensity: lk.emissive_offset }, props.lights, lk.normal), LOOK[g].basecolor_mean_srgb)]).filter(([, e]) => e > 8);
  check(`with the GLB factor + offset a mid-tone front face shows its own texture colour (within 8 sRGB, ${mid.length} GLBs below the shoulder)`, mid.length >= 6 && drift.length === 0, drift.map(([g, e]) => `${g} ${e.toFixed(1)}`).join());
  const plain = glbIds.filter((g) => rgbDist(litCream(LOOK[g].basecolor_mean_srgb, PLAIN, props.lights, lk.normal), LOOK[g].basecolor_mean_srgb) > 12);
  check('without the factor the lights darken the textures (the check measures something)', plain.length === glbIds.length, `${plain.length}/${glbIds.length}`);
  const retex = glbIds.filter((g) => LOOK[g].sheet_front_mean_srgb && rgbDist(LOOK[g].basecolor_mean_srgb, LOOK[g].sheet_front_mean_srgb) > lk.report_tex_sheet_srgb);
  console.log(`INFO texture mean > ${lk.report_tex_sheet_srgb} sRGB from its sheet mean (retex candidates; atlas means are coarse, judge on a sheet-vs-room image): ${retex.map((g) => `${g} ${rgbDist(LOOK[g].basecolor_mean_srgb, LOOK[g].sheet_front_mean_srgb).toFixed(0)}`).join(', ') || 'none'}`);
}
console.log(fails ? `${fails} FAIL` : 'all PASS');
process.exit(fails ? 1 : 0);
