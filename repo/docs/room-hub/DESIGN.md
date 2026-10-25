# Room = Scoop Sky 3D hub — design (2026-10-25, room-hub session)

Intent: [intent/2026-10-25-room-scoop-sky-hub/intent.md](../../intent/2026-10-25-room-scoop-sky-hub/intent.md).
Baseline capture of today's room (Mac GPU, sound off): `reviews/20261025/room/baseline-aquarium/sheet.jpg`.

## 0. What exists (discovery, file:line evidence)

| Layer | Today | Keep / replace |
|---|---|---|
| Host | `web/app/host.mjs` — room iframe (srcdoc of `assets/runtime/aquarium_cafe.html`, host.mjs:151-156) + ONE REA book iframe; bridge in `docs/WEB_BRIDGE.md` | **keep**; add a video overlay + a runtime switch |
| 3D | three.js r186 inline bundle (`tool/build_aquarium_cafe_runtime.py`), GLTFLoader + meshopt, MeshBasic baked room (world.mjs:25-45), blob shadows, adaptive pixel ratio (main.mjs:84-97, 2092-2097) | **keep the stack**, new scene |
| Cast | Moa = `ocean_moa` node inside the whale-story stage GLB (main.mjs:283, cast.mjs:125); Ruu, Miru (whale) | **replace** with EP01 cast |
| Play modes | 13 modes, rule engines pure (`*_core.mjs`): counting 1-20, colours/sort, xylophone echo, compose, pattern, order, habit, safety, shape, calm, seabook, share, move; quests in room_core.mjs:31-55 saved under localStorage `stargarden.kids-room.v1` (host.mjs:185-196) | **keep the cores**, re-theme the UIs |
| Stations | data table `assets/worlds/aquarium_cafe.zones.json` (6 stations) but 21 station-id literals in main.mjs/ui.mjs | replace with a reaction table |
| Words | room voice `assets/audio/kids_room/en_*.wav` (193 files); the book's words `reader/.../bo-sky-island/words/en/*.mp3` (water, island, balloon, up, bird, song, sheep, bounce, flower, cloud, sun, star, rainbow, house, mailbox, pinwheel, wind, fly, hop, glow, sleep ...) | room speaks **the book's word files** (one storyteller voice) |
| Unlocks | none — no video/episode code in runtime_src | **new** |
| Known dead paths | post_office / star_tent / bookshelf main CTAs route to paths the web host ignores (host.mjs:174-177) | fixed by design (§5 one route table) |
| 3D assets | Meshy Moa textured + rigged + walk + idle: `out/shorts/ep01/cast3d/moa/{rig,walk,idle}/` (14 MB each, 4K tex, on-model); Piyo/Mongsil/Popo/Nuri cast3d were made from **outdated v4 inputs** (Nuri = old whale) — not usable as is | reuse Moa (0 credits); regenerate the four from S1 sheets |
| Object sheets | 20 EP01 objects, each with `turn/{front,right,back,left}.png` 512² RGBA + named states + idle + reaction (`out/shorts/ep01/anchors/s1-objects/contact.jpg`) | **the reaction design source** + Meshy multi-image input |

## 1. Architecture decision

New runtime `runtime_src/scoop_sky/` bundled to `assets/runtime/scoop_sky.html`, same host bridge, chosen by `rea-config.json`
`"roomRuntime": "scoop_sky"` (or `?room=scoop`); the aquarium stays as the fallback until the hub passes its phone check.
It imports the theme-free modules unchanged (`*_core.mjs`, room_core, room_store, learn_core, audio engine, cast.mjs walker, nav_core).

Rejected (looks right): reskin main.mjs in place — 2.1 k lines with 21 aquarium station literals and the whale-story
asset dependency; the live room would be broken for days, and two sessions' assets would be coupled.

## 2. The core loop (kids keep tapping — make every tap pay)

```
tap anything  ->  < 100 ms: squash-stretch + sound + sparkle (never nothing)
              ->  first taps of an object: the book voice says its word ("water!")
              ->  repeated taps: cycle 2-3 reaction variants; 5 quick taps = a combo surprise
              ->  care / discovery actions drop a sprinkle-star that flies to the star jar
stars + mission icons  ->  mailbox letter (pictures only)  ->  unlock: book page / EP video
```
Rules: no instruction sentences, labels 1-2 words, all meaning by voice/picture; touch targets >= 88 px; reduced motion =
no squash/camera moves, same sounds; mute = everything still readable by picture.

## 3. Reaction table (from the EP01 object sheets: idle / reaction / states)

| Object (sheet) | Tap reaction | Combo (5 taps) | Word (book file) | Teaches |
|---|---|---|---|---|
| lemon-can | Moa walks over, tilts the can, water arc (states full→pouring→empty) | refill splash | water | verb, cause→effect |
| berry-flower ×3 | thirsty→drink→revived→bloom (7 states) | butterfly lands | flower | care, counting 1-3 |
| berry-sprout | seed→sprout→bud grows with each watering | bud pops into a flower | grow* | sequence |
| icepop-xylophone | bar dips + note; echo game from the xylophone core | Moa dances | song / sing | colours, music |
| scoop-mailbox | lid pops, flag up; holds the mission letter | letter flutters | mailbox | — |
| spoon-pinwheel | slow→fast spin | wind gust moves clouds | pinwheel / wind | speed |
| cream-cloud | puff + sleepy/awake face | sprinkle shower | cloud / sleep | feelings |
| swirl-sun | blink smile, rays turn | day↔sunset tint | sun | — |
| balloon | tug → floats up and back | rises to the sky-island | balloon / up | direction |
| sprinkle-star ×6 | pop + colour name | all six = rainbow | star + colours | colours |
| jelly-rainbow | each band lights + colour | full arc chime | rainbow | colours 7 |
| roll-snail | hides in shell, peeks | — | peek | — |
| berry-butterfly | flies to a flower | — | fly | — |
| cottage | door bounces open → **storybook** | chimney puff | house | — |
| sky-island (floating) | glows, descends → **episode theatre** | sparkle burst | island | — |
| Moa / friends | wave, hop, giggle; follow the child's tap | dance together | hi / hop / bounce (Mongsil) | greeting |

`*` words without a book file need the same storyteller voice (stargarden-gemini-voice) before use.
Room words deliberately equal the book's page words (p1 water/island, p2 balloon/up, p3 bird/song, p4 sheep/bounce):
the child meets a word in the room, then hears it in the story.

## 4. Mission → unlock ladder (picture letters, voiced)

| Step | Letter (icons) | Unlock |
|---|---|---|
| 1 | 💧 + 🌸×3 (water three flowers) | EP01 video on the sky-island theatre |
| 2 | 🎵 echo three notes on the xylophone | storybook bo-sky-island opens in the cottage |
| 3 | ⭐×6 colours | EP02 |
| 4 | 🎈 up + 🌱 grow a sprout | EP03 |
| 5 | play with every friend | EP04 |
Levels persist in the existing quest store (`stargarden.kids-room.v1`), new ids only (old ids stay readable: room_core.mjs:131-156).
Locked episodes are a sleeping cloud (zZ), never a padlock or text.

## 5. Book and video entry

- One route table in the runtime (`routes.json`): `book:<id>` → host `enter` `/books/<id>` (existing REA preview flow);
  `video:<ep>` → host `enter` `/video/<ep>`. A build-time check fails if a route kind is not handled in host.mjs
  (RCCA for today's three dead CTAs: two independent lists → one table + a mechanical cross-check).
- Host gets a full-screen `<video>` overlay with the home button and progress ring; the episode catalogue
  `docs/room-hub/episodes.json` pins exact delivered files (never "latest" in a folder another session writes).
  Today: EP01 `out/shorts/ep01/deliver/ep01-s1-v29-1025-0818.mp4` (121.6 s) until the shorts session names a release cut.

## 6. 3D set and cast

- Set (code, 0 credits): floating grass island with a whipped-cream rim, sky dome gradient, white-with-pink-blush cream
  clouds (never yellow/beige), cookie-stone path, wafer fence, simple shapes (balloon, stars, rainbow) built procedurally.
- Meshy props (multi-image-to-3d, meshy-7.1, textured 2K, remeshed 10 k tris, 30 credits each; `pipeline/room-meshy.py`):
  phase 1 lemon-can (probe), berry-flower, icepop-xylophone, scoop-mailbox, spoon-pinwheel, cream-cloud;
  phase 2 cottage, sky-island, swirl-sun, berry-sprout, roll-snail, berry-butterfly, sky-plane, cream-puff.
- Meshy chain (user 12:1x: "메시에서 사용할 수 있는 거 최대한 다 적극적으로"): gen (multi-image, textured) → **remesh** (quad
  retopology, 6 k / 12 k for cottage + sky-island) → **retexture** (PBR base+normal+metallic+roughness on the remeshed UV, the 4
  sheet views as multiview input) → Blender lane on opi128 (`pipeline/room-glb.sh`: cleanup, facing from a 4-view render,
  1 K WebP, unit height) → `assets/room/scoop/<id>.glb`. Chain validated on lemon-can before the batch. Smart-topology A/B on lemon-can.
- Cast: Moa = existing Meshy rig (walk/idle) merged into one light GLB with clips `idle`/`walk`; Piyo, Mongsil, Popo, Nuri regenerated
  from the S1 sheets (inputs checked against cast.json 2026-10-25.6: [CAST-CHECK.md](CAST-CHECK.md)). Nuri (now a small upright
  dino) gets a Meshy humanoid rig + library actions; Piyo, Mongsil, Popo stay static meshes animated in code (hop, bounce, waddle) —
  a humanoid rig deforms round bodies badly (Popo's Meshy walk was rejected before).
- Phone budget: <= 2 MB per prop GLB, <= 4 MB Moa, total first load <= 15 MB, 60 fps target on a mid phone (adaptive DPR kept).
- Optimise in Blender (macpro/mac2, `tool/optimize_sea_life.py` pattern: decimate, centre, unit scale, WebP textures).

## 7. Credit plan (balance 1,400 on 2026-10-25; monthly 784 resets 2026-11-22)

| Phase | Items | Credits |
|---|---|---|
| probe | lemon-can | 30 (spent under the handoff's probe rule) |
| 1 | 5 core props | 150 |
| 2 | 8 set props | 240 |
| cast | 4 friends | 120 |
| total | | **540** (user pick, 2026-10-25) |
| chain | remesh 5 + retexture 10 for 18 models, Nuri rig 5 + actions, smart A/B 15 | ~310 |
| **cap** | raised to **950** after the user's "자금 사용해도 되는" (docs/room-hub/meshy-cap.json) | ledger: docs/room-hub/meshy-ledger.jsonl |

## 8. Build order (small verified steps)

1. scoop_sky runtime skeleton: island + sky + clouds + Moa walking + tap-reaction engine with 5 procedural reactions → room link, phone capture.
2. Swap in Meshy props as they pass review (one GLB → look → place).
3. Mission letter + EP01 theatre + cottage → book.
4. Friends, combo surprises, remaining modes re-themed (counting with stars, colours with sprinkles, xylophone echo).

## 9. Verification

`pipeline/room-cap.sh <name> 390x844,844x390 "<taps>"` — Mac GPU capture of the public room link, sound off; judge by eye:
every tap shows a reaction within one frame pair, Moa visible and walking, no text instructions, readable with sound off.

## 10. Play stations: walk to a place or a friend, play there (user 2026-10-25 16:36)
User: "어디 갔을 때는 책 읽기, … 누구한테 갔을 때는 음악놀이, 누구한테 갔을 때는 … 공놀이, 숫자놀이 이런 식으로 서로 상호작용할 수 있는 거를 만들어야 … 애니메이션 다 돼야 되고".
One model for every station (data in props.json `stations`, one runtime module, no per-station special code paths):
tap the host → Moa walks to the station spot (walk clip) → arrival: Moa and the host greet (`wave` clip) and the host says
the activity word (book voice) → the activity mounts in a fixed play box in front of the host (inside the frame, >= 88 px
targets) → the child plays by tapping only → success: both `dance`, a sprinkle-star flies to the jar, the ladder level is
saved → objects fold away after 2 s idle; Moa stays. A small floating icon bubble over each host (book / note / ball /
123 / palette) says what is there without text. Camera stays locked (tap targets never move); reduced motion = no hops.

| Station | Host (where) | Activity | Rules / ladder (existing cores) | Host clip | Words |
|---|---|---|---|---|---|
| 책 읽기 Book | cottage door | storybook bo-sky-island (existing route) | — | door open | house, book |
| 영상 Theatre | sky-island | EP01 video (episodes.json) | — | descend | island |
| 음악놀이 Music | Piyo + icepop-xylophone | Piyo sings N notes, child repeats on the bars | QUESTS.xylophone (echo), later compose | sing | song, colour names |
| 공놀이 Ball | Popo | a ball rolls in; tap it → Moa kicks to Popo, Popo kicks back; count the passes | QUESTS.counting for the pass count, move_core later | kick | ball, kick, one…ten |
| 숫자놀이 Numbers | Nuri | Nuri lays berries on the lawn; tap each, the voice counts one…N; at N Nuri cheers | QUESTS.counting [3,5,7,10,12,15,20] | count | one…twenty |
| 색깔놀이 Colours | Mongsil | coloured sprinkle-candies; drop each on the matching cloud cushion | sort_core QUESTS.sorting | bounce | red, blue, … |
| 물주기 Care | lemon-can + flowers | existing watering (thirsty → bloom) | — | — | water, flower |

Clip contract (Blender rig lane w6-cast, all friends + Moa): `idle` (loop), `happy` (hop), `wave`, `dance` (loop) +
activity clip (`sing` Piyo, `kick` Popo, `count` Nuri, `bounce` Mongsil); Moa keeps `idle`/`walk` and gains
`wave`/`happy`/`dance`/`kick`. Every station must play end to end on a phone capture before it counts as done.
Build order: (1) world + cast fix (workers) and the station model with Book + Numbers; (2) Music + Ball; (3) Colours.
