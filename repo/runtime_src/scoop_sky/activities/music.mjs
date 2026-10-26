// Music station (Piyo + the ice-pop xylophone): Piyo sings a phrase on five coloured ice-pop bars (marimba NOTE_HZ, bars
// light up), the child repeats it; a wrong bar replays the phrase gently. Rules: nav_core createEchoGame (listen-and-repeat
// core) on five-bar phrases whose lengths are room_core QUESTS.xylophone.
import { QUESTS } from '../../aquarium_cafe/room_core.mjs';
import { createEchoGame } from '../../aquarium_cafe/nav_core.mjs';
import * as K from './kit.mjs';

/** Bars low -> high (sound.mjs NOTE_HZ order). */
export const BARS = [{ hex: '#f97086', en: 'pink' }, { hex: '#ffad7a', en: 'orange' }, { hex: '#fdcd70', en: 'yellow' }, { hex: '#58b98a', en: 'green' }, { hex: '#5094f7', en: 'blue' }];
/** One phrase per level; length = QUESTS.xylophone[level] (the selftest checks), notes 0..4 only. */
export const PHRASES = [[0, 2, 4], [4, 2, 0], [0, 1, 2, 3, 4], [4, 3, 2, 1, 0], [0, 2, 4, 2], [0, 0, 2, 2, 4, 4], [4, 4, 3, 3, 2], [2, 4, 3, 1, 0]];
export const NOTE_MS = 560;
export const rules = (level) => createEchoGame(PHRASES, K.clampLevel(QUESTS.xylophone, level));

function mount(ctx) {
  const game = rules(ctx.level);
  const phrase = game.phrase;
  const { geo, A } = ctx;
  const bars = geo.slots.map((s, i) => {
    const b = K.bar(ctx, BARS[i].hex, 0.3 - i * 0.03);
    b.position.copy(K.ground(ctx, s.x, s.z)); ctx.group.add(b); K.popIn(ctx, b, 120 + i * 90);
    return { ...s, b, hit: K.hitSphere(ctx, s) };
  });
  let mode = 'demo'; let done = false;
  function ring(i, loud = true) {
    const { b } = bars[i];
    ctx.sound.note(i);
    K.flash(ctx, b, 0xffffff, 380, 0.8);
    const pop = b.userData.pop; const y0 = pop.userData.y0 ?? (pop.userData.y0 = pop.position.y);
    A.tween({ key: `${b.uuid}:dip`, dur: 260, update: (k) => { pop.position.y = y0 - Math.sin(Math.PI * k) * 0.06; } });
    if (loud) A.sparkle(b.position.clone().setY(b.position.y + 0.75), 6, [parseInt(BARS[i].hex.slice(1), 16), 0xffffff]);
  }
  function sing(delay) {
    mode = 'demo';
    ctx.later(delay, () => ctx.hostPlay(ctx.station.host_clip || 'sing'));
    phrase.forEach((n, k) => ctx.later(delay + 200 + k * NOTE_MS, () => ring(n)));
    ctx.later(delay + 200 + phrase.length * NOTE_MS, () => { if (!done) mode = 'listen'; });
  }
  sing(700);
  return {
    onTap(i, point) {
      if (!bars[i] || done) { A.sparkle(point, 5); ctx.sound.sfx('tap', { gain: 0.45 }); return { result: 'none' }; }
      ring(i);
      if (mode !== 'listen') return { result: 'heard', mode };
      const r = game.press(i);
      if (r.result === 'retry') { mode = 'demo'; K.wiggle(ctx, bars[i].b); sing(650); return { result: 'retry' }; }
      if (r.result === 'phrase_done') {
        done = true; mode = 'done';
        ctx.later(500, () => { ctx.hostPlay('happy'); ctx.done({ phrase: phrase.length }); });
      }
      return { result: r.result === 'phrase_done' ? 'done' : 'ok' };
    },
    next: () => (mode === 'listen' ? phrase[game.position] : 0),
    update() {},
    state: () => ({ phrase, pos: game.position, mode }),
    dispose() {},
  };
}

export default {
  id: 'music', maxTargets: BARS.length, ownsRoute: false, levels: QUESTS.xylophone.length,
  words: () => ['music', 'song', 'yay'],
  rules, mount,
};
