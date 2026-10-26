// Book station (cottage): Moa reaches the door, the door opens (host clip `open`, else the door reaction), the host's own
// route (props.json cottage.route) opens the storybook. No targets; the station owns the route so the tap does not open it early.
export default {
  id: 'book', maxTargets: 0, ownsRoute: true, levels: 1,
  words: () => ['book', 'house'],
  rules: () => null,
  mount(ctx) {
    const route = ctx.host.entry.route;
    ctx.hostPlay(ctx.station.host_clip || 'open');
    ctx.sound.sfx('door');
    ctx.moaPlay(ctx.station.moa_clip || 'happy');
    ctx.later(650, () => {
      if (route) ctx.post({ type: 'enter', route: route.route, book: route.book, preview: route.preview });
      ctx.done({ quiet: true, foldMs: 600 });
    });
    return { onTap: () => ({ result: 'none' }), next: () => 0, update() {}, state: () => ({ route: route?.book || null }), dispose() {} };
  },
};
