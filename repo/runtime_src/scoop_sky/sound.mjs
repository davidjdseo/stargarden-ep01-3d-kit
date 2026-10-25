// Scoop Sky sound: one AudioContext unlocked on the first pointerdown, decoded sample cache, synthesised marimba
// notes, book word voices (posts {type:'voice', ms} so the host ducks its music). Muted = nothing plays, nothing posts.
const SFX = {
  tap: 'assets/audio/dsp_v1/ui_touch_pearl.wav',
  sparkle: 'assets/audio/dsp_v1/word_reveal_sparkle.wav',
  bloom: 'reader/mirror/public/audio/sfx/shimmer.mp3',
  pour: 'reader/mirror/public/audio/sfx/splash.mp3',
  spin: 'reader/mirror/public/audio/sfx/gust.mp3',
  puff: 'reader/mirror/public/audio/sfx/fizz.mp3',
  hop: 'reader/mirror/public/audio/sfx/boing.mp3',
  door: 'reader/mirror/public/audio/sfx/snap.mp3',
  glow: 'reader/mirror/public/audio/sfx/bell.mp3',
  blink: 'assets/audio/dsp_v1/bubble_pop.wav',
  combo: 'reader/mirror/public/audio/sfx/cheer.mp3',
  giggle: 'reader/mirror/public/audio/sfx/giggle.mp3',
  flutter: 'reader/mirror/public/audio/sfx/flutter.mp3',
};
export const NOTE_HZ = [523.25, 587.33, 659.25, 783.99, 880.0];
const WORD_DIR = 'reader/v2-20261012/classic-book/books/bo-sky-island/words/en/';

export function createSound({ assetUrl, post }) {
  let ctx = null; let master = null; let muted = false;
  const buffers = new Map();
  const pending = new Map();

  function load(path) {
    if (buffers.has(path)) return Promise.resolve(buffers.get(path));
    if (pending.has(path)) return pending.get(path);
    const p = fetch(assetUrl(path)).then((r) => { if (!r.ok) throw new Error(r.status + ' ' + path); return r.arrayBuffer(); })
      .then((ab) => ctx.decodeAudioData(ab)).then((b) => { buffers.set(path, b); return b; })
      .catch((err) => { console.warn('[scoop] sound missing', path, err.message); buffers.set(path, null); return null; });
    pending.set(path, p);
    return p;
  }

  function unlock() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      ctx = new AC();
      master = ctx.createGain(); master.gain.value = muted ? 0 : 1; master.connect(ctx.destination);
      for (const p of Object.values(SFX)) load(p);
    }
    if (ctx.state === 'suspended') ctx.resume().catch(() => { /* resumes on the next gesture */ });
  }

  function playBuffer(b, { gain = 1, rate = 1 } = {}) {
    const src = ctx.createBufferSource(); src.buffer = b; src.playbackRate.value = rate;
    const g = ctx.createGain(); g.gain.value = gain;
    src.connect(g).connect(master); src.start();
    return b.duration / rate;
  }

  function sfx(name, opts = {}) {
    if (muted || !ctx) return 0;
    const path = SFX[name];
    if (!path) return 0;
    const b = buffers.get(path);
    if (b) return playBuffer(b, opts);
    if (b === undefined) load(path).then((bb) => { if (bb && !muted) playBuffer(bb, opts); });
    return 0;
  }

  /** Marimba-ish tone: sine + soft 4th partial, fast attack, exponential decay. */
  function note(i) {
    if (muted || !ctx) return;
    const f = NOTE_HZ[((i % NOTE_HZ.length) + NOTE_HZ.length) % NOTE_HZ.length];
    const t = ctx.currentTime;
    const g = ctx.createGain(); g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.5, t + 0.008); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.9);
    g.connect(master);
    for (const [mul, amp] of [[1, 1], [4, 0.18], [2.01, 0.08]]) {
      const o = ctx.createOscillator(); o.type = 'sine'; o.frequency.value = f * mul;
      const og = ctx.createGain(); og.gain.value = amp;
      o.connect(og).connect(g); o.start(t); o.stop(t + 0.95);
    }
  }

  function word(w, delayMs = 220) {
    if (muted || !ctx || !w) return;
    const path = WORD_DIR + w + '.mp3';
    load(path).then((b) => {
      if (!b || muted) return;
      setTimeout(() => {
        if (muted) return;
        playBuffer(b, { gain: 1 });
        post({ type: 'voice', ms: Math.round(b.duration * 1000) + 150 });
      }, delayMs);
    });
  }

  function setMuted(m) { muted = !!m; if (master) master.gain.setTargetAtTime(muted ? 0 : 1, ctx.currentTime, 0.03); }
  function pause(p) { if (!ctx) return; if (p) ctx.suspend().catch(() => { /* already suspended */ }); else ctx.resume().catch(() => { /* needs a gesture */ }); }

  return { unlock, sfx, note, word, setMuted, pause, get muted() { return muted; }, get unlocked() { return !!ctx; } };
}
