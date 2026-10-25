// Scoop Sky tap-reaction engine (pure: no three.js, no DOM, no clock of its own).
// Every tap of an object answers with {kind, variant, combo, say}:
//   variant  cycles 0,1,2 per object so repeated taps look different;
//   combo    is true on the COMBO_TAPS-th tap of the same object inside COMBO_WINDOW_MS (then the streak resets);
//   say      is the object's word on its first SAY_FIRST taps, null after (no nagging), and the count starts
//            again once the object has rested SAY_REST_MS without a tap. An entry with `words` says them in turn
//            (piyo: bird, sing, bird ...) within the same throttle.
// The numbers live here only; main.mjs and the selftest import them.
export const VARIANTS = 3;
export const COMBO_TAPS = 5;
export const COMBO_WINDOW_MS = 3000;
export const SAY_FIRST = 3;
export const SAY_REST_MS = 20000;
// The reaction kinds the runtime animates; anim.mjs refuses to load if one of these has no animation.
export const KINDS = ['door', 'hop', 'spin', 'bloom', 'pour', 'notes', 'puff', 'glow', 'blink', 'friend', 'fly'];

export function createReactions(table, { now = () => Date.now() } = {}) {
  const byId = new Map();
  for (const e of table) {
    if (!e || typeof e.id !== 'string' || typeof e.reaction !== 'string') throw new Error('reaction entry needs id + reaction');
    byId.set(e.id, e);
  }
  const state = new Map();

  function tap(id) {
    const entry = byId.get(id);
    if (!entry) return null;
    const t = now();
    let s = state.get(id);
    if (!s) { s = { taps: 0, said: 0, last: -Infinity, streak: [] }; state.set(id, s); }
    if (t - s.last >= SAY_REST_MS) s.said = 0;
    const variant = s.taps % VARIANTS;
    s.taps += 1;
    s.streak = s.streak.filter((x) => t - x < COMBO_WINDOW_MS);
    s.streak.push(t);
    let combo = false;
    if (s.streak.length >= COMBO_TAPS) { combo = true; s.streak = []; }
    let say = null;
    const words = Array.isArray(entry.words) && entry.words.length ? entry.words : entry.word ? [entry.word] : [];
    if (words.length && s.said < SAY_FIRST) { say = words[s.said % words.length]; s.said += 1; }
    s.last = t;
    return { id, kind: entry.reaction, variant, combo, say };
  }

  function stats(id) {
    const s = state.get(id);
    return s ? { taps: s.taps, said: s.said, streak: s.streak.length } : { taps: 0, said: 0, streak: 0 };
  }

  return { tap, stats, has: (id) => byId.has(id), reset: () => state.clear() };
}
