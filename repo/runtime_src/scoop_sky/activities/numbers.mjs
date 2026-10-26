// Numbers station: the host lays berries in the play box, BATCH at a time (three: 88 px targets fit the lawn); each tap pops one into the
// basket and the voice says the next number; at the goal Nuri cheers. Goal ladder = room_core QUESTS.counting.
import { QUESTS } from '../../aquarium_cafe/room_core.mjs';
import { COUNT_EN } from '../../aquarium_cafe/nav_core.mjs';
import * as K from './kit.mjs';

export const BATCH = 3;
/** Pure counting round: lay() puts the next batch out, take() counts one berry. */
export function rules(level) {
  const goal = QUESTS.counting[K.clampLevel(QUESTS.counting, level)];
  let count = 0; let laid = 0;
  return {
    goal,
    get count() { return count; }, get laid() { return laid; },
    lay() { const k = Math.min(BATCH, goal - laid); laid += k; return k; },
    take() {
      if (count >= laid) return { result: 'empty' };
      count += 1;
      return { result: count === goal ? 'done' : 'ok', n: count, word: COUNT_EN[count - 1], refill: count === laid && count < goal };
    },
  };
}

function mount(ctx) {
  const R = rules(ctx.level);
  const { geo, A } = ctx;
  const slots = geo.slots.map((s) => ({ ...s, hit: K.hitSphere(ctx, s), item: null }));
  const bpos = geo.at(0, -0.5);
  const bask = K.basket(ctx); bask.position.copy(K.ground(ctx, bpos[0], bpos[1])); ctx.group.add(bask); K.popIn(ctx, bask);
  let finished = false;
  function lay(delay) {
    const k = R.lay();
    ctx.hostPlay(ctx.station.host_clip || 'count');
    for (let i = 0; i < k; i++) {
      const s = slots[i]; const b = K.berry(ctx, (R.laid - k + i) % 2 ? 'blue' : 'straw');
      b.position.copy(K.ground(ctx, s.x, s.z)); b.rotation.y = i * 0.7; ctx.group.add(b);
      s.item = b; K.popIn(ctx, b, delay + i * 110);
    }
    ctx.later(delay + 60, () => ctx.sound.sfx('bloom', { gain: 0.5 }));
  }
  lay(250);
  return {
    onTap(i, point) {
      const s = slots[i];
      if (!s || !s.item || finished) { A.sparkle(point, 5); ctx.sound.sfx('tap', { gain: 0.45 }); return { result: 'empty' }; }
      const r = R.take();
      const b = s.item; s.item = null;
      ctx.sound.sfx('blink', { gain: 0.7 });
      ctx.say(r.word, 60);
      A.sparkle(b.position.clone().setY(b.position.y + 0.3), 8);
      const pile = r.n - 1; const ang = pile * 2.4; const rad = 0.06 + Math.min(0.2, pile * 0.015);
      const to = bask.position.clone().add(new ctx.THREE.Vector3(Math.cos(ang) * rad * 1.3, 0.2 + Math.min(0.3, pile * 0.016), Math.sin(ang) * rad * 1.3));
      A.tween({ key: `${b.uuid}:shrink`, dur: 450, update: (k) => b.scale.setScalar(1 - 0.35 * k) });
      K.arc(ctx, b, b.position, to, { dur: 450, h: 0.55, done: () => { A.squash(bask, 0.6); } });
      if (r.refill) ctx.later(700, () => lay(0));
      if (r.result === 'done') {
        finished = true;
        ctx.later(600, () => { ctx.hostPlay('happy'); ctx.done({ count: r.n }); });
      }
      return { result: r.result, n: r.n, word: r.word };
    },
    next: () => Math.max(0, slots.findIndex((s) => s.item)),
    update() {},
    state: () => ({ goal: R.goal, count: R.count, laid: R.laid }),
    dispose() {},
  };
}

export default {
  id: 'numbers', maxTargets: BATCH, ownsRoute: false, levels: QUESTS.counting.length,
  words: (level) => [...COUNT_EN.slice(0, QUESTS.counting[K.clampLevel(QUESTS.counting, level)]), 'yay'],
  rules, mount,
};
