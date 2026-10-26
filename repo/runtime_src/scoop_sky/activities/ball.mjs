// Ball station (Popo): a ball rolls into the play box; tap it -> it rolls to Moa, Moa kicks it to Popo, Popo kicks it back to
// its place and the voice counts the pass; at the goal both dance. Pass ladder = room_core QUESTS.counting.
import { QUESTS } from '../../aquarium_cafe/room_core.mjs';
import { COUNT_EN } from '../../aquarium_cafe/nav_core.mjs';
import * as K from './kit.mjs';

/** Pure pass counter. */
export function rules(level) {
  const goal = QUESTS.counting[K.clampLevel(QUESTS.counting, level)];
  let passes = 0;
  return { goal, get passes() { return passes; }, pass() { if (passes >= goal) return { result: 'done', n: passes }; passes += 1; return { result: passes === goal ? 'done' : 'ok', n: passes, word: COUNT_EN[passes - 1] }; } };
}
export const LEG_MS = 560;

function mount(ctx) {
  const R = rules(ctx.level);
  const { geo, A, THREE } = ctx;
  const s = geo.slots[0];
  K.hitSphere(ctx, s);
  const home = K.ground(ctx, s.x, s.z);
  const ball = K.ballMesh(ctx); ctx.group.add(ball);
  const toward = (a, b, d) => { const v = new THREE.Vector3(b[0] - a[0], 0, b[1] - a[1]); const L = v.length() || 1; return [a[0] + (v.x / L) * d, a[1] + (v.z / L) * d]; };
  const hostFoot = ctx.host.entry.footprint_m ?? ctx.host.entry.height_m * 0.5;
  const popoAt = toward(geo.hostPos, [s.x, s.z], hostFoot + 0.25);
  const moaAt = toward(geo.spot, [s.x, s.z], 0.45);
  const P = (xz) => K.ground(ctx, xz[0], xz[1]);
  const roll = (from, to, dur, h, done) => {
    const dist = from.distanceTo(to); K.arc(ctx, ball, from, to, { dur, h, done });
    const sp = ball.userData.spin; const r0 = sp.rotation.x;
    A.tween({ key: `${ball.uuid}:roll`, dur, update: (k) => { sp.rotation.x = r0 + (dist / 0.22) * k; } });
    const dir = to.clone().sub(from); ball.rotation.y = Math.atan2(dir.x, dir.z);
  };
  let busy = true; let finished = false;
  const start = P(popoAt);
  ball.position.copy(start);
  K.popIn(ctx, ball, 150);
  ctx.later(350, () => roll(start, home, 700, 0.05, () => { busy = false; ctx.say('ball', 60); }));
  return {
    onTap(i, point) {
      if (busy || finished || i !== 0) { A.sparkle(point, 5); ctx.sound.sfx('tap', { gain: 0.45 }); return { result: busy ? 'busy' : 'none' }; }
      busy = true;
      ctx.sound.sfx('tap', { gain: 0.6 });
      A.squash(ball, 0.8);
      roll(home, P(moaAt), 300, 0.04, () => {
        ctx.moaPlay(ctx.station.moa_clip || 'kick'); ctx.sound.sfx('hop', { gain: 0.6 });
        roll(P(moaAt), P(popoAt), LEG_MS, 0.6, () => {
          ctx.hostPlay(ctx.station.host_clip || 'kick'); ctx.sound.sfx('hop', { gain: 0.6 });
          roll(P(popoAt), home, LEG_MS, 0.5, () => {
            const r = R.pass();
            ctx.say(r.word, 40);
            A.sparkle(home.clone().setY(home.y + 0.4), 8);
            if (r.result === 'done') { finished = true; ctx.later(400, () => ctx.done({ passes: r.n })); } else busy = false;
          });
        });
      });
      return { result: 'kick', n: R.passes + 1 };
    },
    next: () => 0,
    update() {},
    state: () => ({ goal: R.goal, passes: R.passes, busy }),
    dispose() {},
  };
}

export default {
  id: 'ball', maxTargets: 1, ownsRoute: false, levels: QUESTS.counting.length,
  words: (level) => ['ball', 'kick', ...COUNT_EN.slice(0, QUESTS.counting[K.clampLevel(QUESTS.counting, level)]), 'yay'],
  rules, mount,
};
