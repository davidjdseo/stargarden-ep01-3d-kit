// Colours station (Mongsil): sprinkle-candies in the play box and 1-4 cloud cushions tinted by colour; the called colour's
// cushion glows and the voice names it; tap a candy of that colour and it hops onto its cushion saying the colour; a wrong
// candy wiggles and the call is repeated. Rules: sort_core createSortRound (ladder QUESTS.sorting).
import { QUESTS } from '../../aquarium_cafe/room_core.mjs';
import { createSortRound } from '../../aquarium_cafe/sort_core.mjs';
import * as K from './kit.mjs';

export const SLOTS = 3;
export const rules = (level) => createSortRound(K.clampLevel(QUESTS.sorting, level));
/**
 * Which colour goes into a free slot: the called colour when none of it is on the lawn, then a colour with candies left and
 * none visible, then the colour with most left; -1 when none are left. With 3 slots and up to 4 colours this keeps the called
 * colour visible: one slot frees per correct tap and it refills with the new call first.
 */
export function pickColour(unshown, visible, call = -1) {
  if (call >= 0 && unshown[call] > 0 && visible[call] === 0) return call;
  for (let k = 0; k < unshown.length; k++) if (unshown[k] > 0 && visible[k] === 0) return k;
  let best = -1; for (let k = 0; k < unshown.length; k++) if (unshown[k] > 0 && (best < 0 || unshown[k] > unshown[best])) best = k;
  return best;
}
/** Initial fill of `n` slots, one of each colour first. Pure; returns colour per slot (-1 = empty) and the counters. */
export function fillSlots(round, n = SLOTS) {
  const unshown = round.colors.map(() => round.perColor); const visible = round.colors.map(() => 0); const slots = [];
  for (let i = 0; i < n; i++) { const k = pickColour(unshown, visible, round.call); slots.push(k); if (k >= 0) { unshown[k] -= 1; visible[k] += 1; } }
  return { slots, unshown, visible };
}

function mount(ctx) {
  const round = rules(ctx.level);
  const { geo, A } = ctx;
  const nC = round.colors.length;
  const fill = fillSlots(round, geo.slots.length);
  const order = fill.slots.map((k, i) => [k, i]);
  const cushions = round.colors.map((c, k) => {
    const p = geo.at(-0.5 + (k + 0.5) / nC, -0.5);
    const g = K.cushion(ctx, c.hex); g.position.copy(K.ground(ctx, p[0], p[1])); ctx.group.add(g); K.popIn(ctx, g, 100 + k * 90);
    return { g, n: 0 };
  });
  const slots = geo.slots.map((s) => ({ ...s, hit: K.hitSphere(ctx, s), item: null, k: -1 }));
  function place(i, k, delay) {
    const s = slots[i]; s.k = k; if (k < 0) { s.item = null; return; }
    const c = K.candy(ctx, round.colors[k].hex); c.position.copy(K.ground(ctx, s.x, s.z)); c.rotation.y = (i - 1.5) * 0.4;
    ctx.group.add(c); s.item = c; K.popIn(ctx, c, delay);
  }
  order.forEach(([k, i]) => place(i, k, 350 + i * 110));
  let finished = false; let cueKey = 0;
  function cue(delay) {
    const k = round.call; const my = ++cueKey;
    ctx.later(delay, () => {
      if (my !== cueKey || finished) return;
      ctx.say(round.colors[k].en, 0);
      const g = cushions[k].g; K.flash(ctx, g, 0xffffff, 700, 0.7);
      ctx.A.squash(g, 0.7);
    });
  }
  ctx.hostPlay('happy');
  cue(900);
  return {
    onTap(i, point) {
      const s = slots[i];
      if (!s || !s.item || finished) { A.sparkle(point, 5); ctx.sound.sfx('tap', { gain: 0.45 }); return { result: 'empty' }; }
      const k = s.k; const r = round.press(k);
      if (r.result === 'retry') { K.wiggle(ctx, s.item); ctx.sound.sfx('tap', { gain: 0.5 }); cue(350); return { result: 'retry', want: round.colors[round.call].en }; }
      const item = s.item; s.item = null; s.k = -1; fill.visible[k] -= 1;
      const cu = cushions[k]; const n = cu.n++;
      const to = cu.g.position.clone().add(new ctx.THREE.Vector3((n % 3 - 1) * 0.2, 0.18 + Math.floor(n / 3) * 0.18, 0));
      ctx.say(round.colors[k].en, 40);
      ctx.sound.sfx('hop', { gain: 0.6 });
      K.arc(ctx, item, item.position, to, { dur: 480, h: 0.6, done: () => { A.squash(cu.g, 0.6); A.sparkle(to.clone().setY(to.y + 0.2), 8, [parseInt(round.colors[k].hex.slice(1), 16), 0xffffff]); } });
      A.tween({ key: `${item.uuid}:sm`, dur: 480, update: (q) => item.scale.setScalar(1 - 0.3 * q) });
      if (r.result === 'done') { finished = true; ctx.later(700, () => { ctx.hostPlay(ctx.station.host_clip || 'bounce'); ctx.done({ sorted: true }); }); return { result: 'done' }; }
      const nk = pickColour(fill.unshown, fill.visible, round.call);
      if (nk >= 0) { fill.unshown[nk] -= 1; fill.visible[nk] += 1; ctx.later(380, () => place(i, nk, 0)); s.k = nk; }
      cue(950);
      return { result: 'ok', colour: round.colors[k].en };
    },
    next: () => Math.max(0, slots.findIndex((s) => s.item && s.k === round.call)),
    update() {},
    state: () => ({ call: round.colors[round.call]?.en, remaining: round.remaining, slots: slots.map((s) => s.k) }),
    dispose() {},
  };
}

export default {
  id: 'colours', maxTargets: SLOTS, ownsRoute: false, levels: QUESTS.sorting.length,
  words: (level) => [...rules(level).colors.map((c) => c.en), 'rainbow', 'yay'],
  rules, mount,
};
