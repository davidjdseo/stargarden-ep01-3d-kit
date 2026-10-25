# 작업 지시: Scoop Sky room environment in Blender (sky dome, soft-serve clouds, ice-cream hills, big lawn) that reads as the approved plate

You are a StarGarden implementation worker (Claude Opus 5.5 sg-worker subagent, effort high) and the Blender specialist on this job (the user's first choice, Codex gpt-6-astra, is out of quota until 2026-10-31 02:41, measured on launch). Do not launch other agents or Claude/Codex runs. Report in English. **Attitude (user-specified, every worker):** Be creative, autonomous and proactive. Work like an efficient early-stage startup (maximum results with minimum time and tokens). Work with courage. Go all out. RCCA: follow the canonical block below (docs/agents/RCCA.md), included verbatim.

<!-- RCCA-RULE:BEGIN — canonical: docs/agents/RCCA.md; same bytes on every device; edit there, then redistribute -->
## 최우선 규칙: 근본 원인 시정조치(RCCA) — 증상 억제로 끝내지 않는다 (사용자 지정 2026-10-24, 모든 세션·모든 기기·Claude/Codex 공통)
- **용어.** *증상 억제(Containment)* = 나타난 결과만 누르는 조치다. 배가 아플 때 진통제·소화제를 계속 먹이는 것, 값 하나를 맞추는 것, 예외 처리로 숨기는 것, 증상 검사·게이트를 조이는 것이 여기에 든다. *근본 원인 시정조치(RCCA, Root Cause Corrective Action — ISO 9001의 corrective action)* = 왜 그 결과가 생겼는지(상한 음식을 먹어서), 그리고 왜 우리가 그것을 먹게 됐는지(장보기·보관·확인 단계)를 찾아 그 단계를 고치는 조치다. 이 문서들에서 "재발 방지"는 항상 RCCA를 뜻한다.
- **순서.** ① 증상을 기록한다(측정·화면·로그·사용자 원문). ② 직접 원인을 근거와 함께 찾는다(코드·데이터·프레임). ③ 근본 원인은 "왜?"를 우리 과정까지 묻는다(5 Whys). 어떤 디렉팅 판단·지시서·스킬/가이드 문구·리뷰 질문·이전 결정 인계가 이것을 허용했고, 그 자리에서 무엇을 말했어야 했는지 찾는다. ④ 그 단계를 고친다(스킬·가이드·지시서 기본값·리뷰 질문·도구 기본값). ⑤ 증상을 고친다. ⑥ 같은 부류가 숨어 있을 다른 곳(다른 장면·편·프로젝트)에 일반화한다.
- **자동 검사는 원인이 기계적일 때만 둔다.** 값이 두 곳에 있음·배선 누락·조용히 삼키는 catch처럼 원인 자체가 스크립트로 보일 때만 검사를 둔다. 증상이 다시 안 보이게 하는 수치 lint·게이트·반복 검수는 RCCA가 아니다.
- **같은 부류가 2회 나오면 구조를 바꾼다.** 값이 아니라 모델·절차·스킬 구조를 바꾼다.
- **원인을 못 찾으면** 증상 패치로 덮지 않는다. 가설과 다음 측정을 보고한다.
- **보고 순서:** 증상 → 직접 원인(근거) → 근본 원인(우리가 놓친 단계) → 시정조치(고친 파일·절) → 증상 수정 → 검증·미검증.
- **서브에이전트·워커 지시서**에는 이 블록을 그대로 넣는다(워커는 CLAUDE.md를 못 볼 수 있다).
<!-- RCCA-RULE:END -->

Goal: replace the room's procedural background (floating grass disc, white sphere clouds, flat gradient sky) with ONE baked environment GLB built in Blender on opi128 that, seen from the room camera, looks like the approved world plate: saturated-blue-to-peach sky, soft-serve swirl cream clouds with peach undersides, pastel ice-cream dome hills with drip icing, mint broccoli bush bands, faint lavender far mountains, and a bright fluffy rolling lawn that runs to the horizon in every direction (a much bigger world than today's 4.4 m disc).
Deliverable: `tool/room_env_build.py` (new) (Blender script), `pipeline/room-env.sh` (new) (lane runner), `assets/room/scoop/set/env.glb` (new), `assets/room/scoop/set/env.json` (new), renders under `reviews/20261025/room/env/` (new); final message = report (§7).

## 0. 질문 먼저 (필수)
Read the whole brief first. If something is ambiguous, send ONE numbered batch of questions to main with `SendMessage` (recommended answer first) and keep doing every part that does not depend on the answer; never guess on the blocked part.
**Ask before any deviation:** if reality differs from §2 or a change outside the §6 file list looks necessary, stop that part and ask main (SendMessage) with your recommendation. Never apply it and report afterwards.

## 1. 목표 (사용자 말 인용 + 왜)
User (2026-10-25, room-hub session, speech-to-text): "원화 보고 그 원래 시안 있잖아 … 배경 플레이트 보고 분리할 거 싹 분리하고 다시 생성해가지고 텍스처 굽고 텍스처 입혀주고 거의 그거랑 똑같이 계속해서 작업해줘. 일단 배경도 별로고 구름도 별로고 별로인 것들 최대한 똑같이 작업해줘. 텍스처 입혀가지고. 그리고 사이즈도 좀 더 크게 세계관 확장해주고." Then: "코덱스 아스트라 미디움 … GPT-6 아스트라 모델이 그 블렌더 작업 잘하거든? … 지시서 상세하게 하고 너랑 좀 작업을 나눠가지고 해줘."
Why: the room (three.js, phone landscape 844x390 first) is the kids' hub for the Scoop Sky episode; its world must be the same place the episode art shows. Today's background is the weakest part (see the current capture in §2-2: white sphere clouds, a grass disc floating on a cream cone, a plain gradient). Main (Claude) does the runtime: loading your GLB, camera, prop layout, capture. A second worker (w5-set) builds the near set pieces (trees, berry bushes, fence, cookie stones, grass tufts) at the same time; you build everything that is background.

## 1-1. Expert lens
- Expert: a senior environment / technical artist for stylised mobile 3D worlds (pastel "toy world" games) who turns approved 2D key art into a 3D matte-painting-style set: layered depth bands (sky dome, cloud banks, far mountains, far hills, mid bush band, near terrain), every colour measured from the key art, lighting baked into the textures, rendered unlit at runtime; never generic primitives with guessed colours, never real-time lighting on far layers.
- Sources: the plate pixels themselves (`plate-v4.png`, `plate-v4-noisland.png`, `sky-v1.png`, `r7-side-v1.png`, `reverse-r4-v1.png`, `r6-flowerbed-v1.png` in `out/shorts/ep01/anchors/world-theme-s1/A-scoop-sky/`), the current runtime background in `runtime_src/scoop_sky/world.mjs` (`buildSky`, `buildWorld`, lines 80-260: what you replace), the camera block in `runtime_src/scoop_sky/props.json`, Blender 5.0.1 bake + glTF exporter options (read them with `help()`/`bpy.ops.object.bake` and `bpy.ops.export_scene.gltf` on opi128, not from memory).
- Method and tools: one bpy script that builds the whole env from a small data block (swatches, layer distances, counts, seed), Cycles CPU bake (3 threads) to textures or colour attributes, glTF export (WebP), preview renders with the Standard view transform, PIL side-by-side sheets. Runner rsyncs only your files to opi128 and back.
- Verified by: (1) a side-by-side sheet plate-v4 | your render from a plate-matched camera: same horizon height, cloud bank placement/size/shape, hill colours and spacing; (2) a swatch table: each named surface's baked/exported colour vs its plate swatch, sRGB distance <= 12; (3) budgets and a re-import check of env.glb. Wrong if: banding in the sky, a visible terrain edge or a seam at the horizon, hard card edges on clouds, hills that read as plain spheres, colours off by more than 12, or a lawn that reads as flat paint.
- Reframe: "what makes a child think this is the same place as the plate when standing at the room camera?" Match the horizon band first (silhouettes, colours, cloud masses), detail second.

## 2. 확인된 사실 (메인이 확인한 것)
- Look truth (read-only): `out/shorts/ep01/anchors/world-theme-s1/A-scoop-sky/plate-v4.png` 1672x941 RGB (and `plate-v4-noisland.png`, same plate without the small floating sky-island). Other angles of the same world: `sky-v1.png` (clouds + sky only, gradient blue to peach horizon, faint lavender mountains on the horizon), `r7-side-v1.png` (side view: hills with drip icing and sprinkles, mint broccoli bushes), `reverse-r4-v1.png`, `r6-flowerbed-v1.png` (lawn close-up). All 1672x941.
- What the plate shows (main's reading; you measure the real values): rolling bright-green fluffy lawn with lighter yellow-green tips; soft-serve cumulus clouds (cream tops with a soft-serve swirl peak, peach/pink undersides); pastel ice-cream dome hills (pink, mint, cream, lilac) with white drip icing and coloured sprinkles; mint/green broccoli bush clusters between hills; faint lavender mountain silhouettes at the very horizon; sky from saturated blue at the top to warm peach-cream at the horizon.
- Runtime today (`runtime_src/scoop_sky/world.mjs`): `buildSky` = gradient sphere keyed to view elevation; `buildWorld` = lathe grass disc r 4.4 m, cream underside cone, 26 rim blobs, 12 sphere clouds at z -16..-22 drifting along x (`set.clouds`, `cloud_wrap_x` 22 in props.json). Main will delete these and load your env.glb instead.
- Coordinates (three.js = glTF): Y up, metres, origin = centre of the play area, the default room camera looks toward -Z (so "behind the cottage" = -Z, "behind the camera" = +Z). Blender's glTF exporter converts Blender Z-up to glTF Y-up (+Y up on export); build in Blender with Blender -Y = glTF +Z, i.e. keep the exporter default and check one marker after re-import.
- Room camera (main is re-solving it now for the bigger world; design for this whole range): eye height 2.5-4.5 m, z +10..+14, pitch 4-12 deg down, vertical fov 30-40 deg at 844x390; the horizon lands 25-40 % from the frame top. Use this candidate for your room previews: pos (0, 3.4, 12.5), target (0, 1.6, -6), vertical fov 34 deg, 844x390 and 1280x800 (at 1280x800 widen the vertical fov so the horizontal field stays the same: vfov = 2*atan(tan(17 deg) * (844/390) / (1280/800))).
- Runtime rendering contract (main implements): every mesh under an `env_*` node renders UNLIT: three.js MeshBasicMaterial, `map` = your base-colour texture (sRGB), `vertexColors` when COLOR_0 exists (multiplied with the map), alpha when the material is BLEND/MASK, `toneMapped = false`, no fog, camera far plane 1000 m. So the colour you bake is the colour on the phone, pixel for pixel (Standard view transform, never AgX/Filmic in the baked data).
- opi128 (measured by main 2026-10-25 16:2x): Blender 5.0.1 at /usr/bin/blender, 8 cores, 15 GB RAM with ~10 GB available, 65 GB free disk. ANOTHER SESSION is rendering there right now (`/tmp/sg-layout-lane/`, shorts layout lane): never touch it, use at most 3 Cycles threads. Headless works with `blender -b --factory-startup`; for EEVEE/Workbench previews the other lane uses `EGL_PLATFORM=surfaceless LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe` (software, slow); Cycles CPU is the safe default. The opi128 repo dir is an rsync lane copy, not git: never run git or setup scripts there.
- The w5-set worker writes `assets/room/scoop/set/<piece>.glb` + `set/pieces.json` in the same folder and also uses opi128 (3 threads). Disjoint file names; do not touch theirs.

## 2-1. Pre-flight
- P1: paths checked by main with ls 2026-10-25: the six plates exist; `assets/room/scoop/` exists; `assets/room/scoop/set/` (new) and every output marked (new) do not exist yet.
- P2: plate sizes measured with PIL (1672x941 RGB each); opi128 disk/RAM/cores measured with ssh `df -h /`, `free -g`, `nproc` (values in §2).
- P3: N/A for layout decisions (main's); your previews are at 844x390 and 1280x800 plus the plate camera.
- P4: no gate changed. pre-commit hooks touch nothing under assets/room/scoop/set (main commits).
- P5: runtime claims: main's loader renders `env_*` unlit (MeshBasicMaterial, toneMapped false) — not implemented yet; your colour verification is on the baked data and your Blender preview (Standard view transform), main verifies on a real phone-sized GPU capture.
- P6: consumers of env.glb: only `runtime_src/scoop_sky/world.mjs` (main, after you finish).
- P7: perceived: from the room camera on a phone the background reads as the plate's world (same sky, clouds, hills, lawn), nothing looks like a flat card or a primitive sphere, and the world feels big (lawn and hills continue past the frame edges and behind the camera).
- P8: shared files — `assets/room/scoop/set/` shared with w5-set (disjoint names: yours = env.glb, env.json); opi128 `/tmp/sg-layout-lane/` belongs to another session.
- Generation auth: N/A — no generation API (no Meshy, no image model); everything is built in Blender from measured plate colours.
- Known unknowns: whether Blender 5.0.1 bakes to colour attributes headless on the board (test on one mesh first); bake time at 3 threads (keep samples low, 16-32, denoise optional); the exact glTF COLOR_0 colour space round trip (verify by re-import + reading the attribute).

## 2-2. Evidence
- ToneLock: out/shorts/ep01/anchors/world-theme-s1/A-scoop-sky/plate-v4.png
- IMG: out/shorts/ep01/anchors/world-theme-s1/A-scoop-sky/plate-v4.png
- IMG: out/shorts/ep01/anchors/world-theme-s1/A-scoop-sky/sky-v1.png
- IMG: out/shorts/ep01/anchors/world-theme-s1/A-scoop-sky/r7-side-v1.png
- IMG: out/shorts/ep01/anchors/world-theme-s1/A-scoop-sky/reverse-r4-v1.png
- IMG: reviews/20261025/room/scoop-v9-look/ab-844.jpg
- Where: Scoop Sky room `?room=scoop`, whole frame at 844x390 and 1280x800: everything behind the props (sky, clouds, horizon band, lawn). The last image is today's room (top = before colour fix, bottom = after): the background you replace.

## 3. 메인 결정 (그대로 구현)
1. Layers and distances (metres from origin; all built in one .blend, exported as one GLB; every top node named `env_*`):
   - `env_sky`: sky dome radius 450, inverted sphere or hemisphere + lower skirt, gradient measured from `sky-v1.png` (sample a vertical strip of open sky from the top row to the horizon; at least 6 stops). Must be smooth (no banding): use a 1D/2D texture of at least 512 px along the gradient or enough vertex rings. Below the horizon the dome continues with the far haze colour so no gap can show.
   - `env_mountains`: faint lavender far mountain silhouettes at 260-330 m, tops at +0.5..+2.5 deg elevation from the room eye (0, 3.4, 12.5), colour measured from `sky-v1.png` horizon, ring all around (denser in the back arc, z < 0).
   - `env_clouds`: 8-14 soft-serve cloud banks at 150-300 m, each its own child node `env_cloud_NN` with its pivot at its own centre (main may drift them slowly by rotating around Y). Shape: puffy cumulus (union of many blobs/metaballs, smoothed) with 1-3 soft-serve swirl peaks on top (screw/spiral profile like soft ice cream), cream tops and peach-pink undersides measured from the plates, soft baked shading (not flat white, not grey). As seen from the room eye: bases tucked at -1..+3 deg (behind the hills), tops up to +12..+16 deg; big banks left and right of the frame centre and a smaller gap of open blue above the centre, like plate-v4 and sky-v1. A few smaller banks all around 360 deg.
   - `env_hills`: 20-40 ice-cream dome hills at 45-140 m: rounded scoop domes (not perfect spheres: slightly flattened, lumpy rim), pastel pink / mint / cream / lilac measured from plate-v4 and r7-side, white drip-icing caps with wavy drip edges, tiny sprinkles (texture or small geometry), heights so tops sit at +1..+6 deg from the room eye; overlapping rows with lighter, hazier colours with distance (aerial perspective measured from the plates). Dense in the back arc (z < -30, within +/-75 deg of -Z), sparser to the sides and behind the camera.
   - `env_bushes`: mint and green broccoli bush clusters (lumpy cauliflower canopies) at 20-60 m along the hill bases and as a band between lawn and hills, colours from plate-v4 / r7-side.
   - `env_terrain`: one lawn surface out to radius 200 m (fading into the far haze colour before the mountain ring). EXACTLY flat at y = 0 inside radius 10 m from the origin AND inside the camera corridor |x| <= 8, 0 <= z <= 16; smooth gentle rolling (amplitude rising from 0 at r = 10 to about 1.5-4 m at r >= 40) outside that, rising a little more behind (z < 0) so the hills sit on swells. The lawn look: bright fluffy green with lighter yellow-green tips and soft darker dips, measured from plate-v4 and r6-flowerbed; a tileable fluffy-grass texture (1024 px, repeat every 2-4 m near the camera; use a second UV or a separate far material so far terrain does not show tiling) plus large-scale colour/shading variation in COLOR_0 or a baked macro texture.
2. Colour = measured, then baked: first write a `swatches` block in env.json: for every named surface (sky-top, sky-mid, sky-horizon, cloud-top, cloud-under, mountain, hill-pink, hill-mint, hill-cream, hill-lilac, icing, bush-mint, bush-green, lawn-light, lawn-mid, lawn-dark, haze) the source image, the pixel box you sampled and the mean sRGB. Build the Blender materials from those swatches (procedural noise for variation), light the scene like the plate (soft warm key from the upper front, bright sky fill; read the plate's light direction from the cloud and hill shading), and bake so the LIT result (what the camera sees) of each surface lands on its swatch: table of baked mean vs swatch, sRGB distance <= 12 for each. Recommended route: bake lighting/AO as a separate grey factor normalised so the plate-facing side = 1.0 and multiply with the swatch albedo, which makes the colour match by construction; any route is fine if the table passes.
3. Budgets: env.glb <= 8 MB, <= 150k triangles total, textures WebP (quality 85-90), <= 2048 px for the sky and the terrain macro texture, <= 1024 px for the rest; no cameras or lights in the GLB; materials PBR metallic 0 (main swaps them to unlit anyway). Join meshes per layer except the separate cloud nodes.
4. Script and runner: `blender -b --factory-startup -P tool/room_env_build.py -- <job.json>` where job.json holds output paths, seed, thread count (3) and render flags. `bash pipeline/room-env.sh (new) [--renders-only]`: `ssh opi128 'df -h /'` (abort under 10 GB free), rsync the script + the plates it samples to opi128 at the same absolute paths, run Blender there (`nice -n 5`), rsync back `assets/room/scoop/set/env.glb` (new), `env.json` and `reviews/20261025/room/env/`, then delete only your copies on the board and print the board paths it deleted. Re-running gives the same GLB (fixed seed).
5. Renders (Standard view transform, Cycles CPU 3 threads, 24-64 samples) into `reviews/20261025/room/env/` (new): (a) `plate-match.jpg`: plate-v4 left | your render from a camera you match to the plate (fit horizon height, hill line and cloud masses; report the camera you found) — env only (no props, no near set pieces) is expected to leave the foreground empty; (b) `room-844.jpg` and `room-1280.jpg` from the room candidate camera in §2; (c) `wide.jpg`: a 2:1 equirectangular or a 4-view (front/right/back/left from the eye) sheet proving the world continues 360 deg; (d) `draft-*.jpg` early drafts: write a first plate-match draft within your first ~30 minutes so main can see the direction.
6. env.json (new): {glb, bytes, sha256, triangles per layer, textures (name, px, bytes), swatches (see 2), bake_table (surface, baked mean, swatch, distance), plate_camera (pos, target, vfov) you matched, room_camera used, clouds (node name, centre, radius), flat_zone (r 10 + corridor), seed}.
7. After export, re-import env.glb in a fresh Blender: assert node names `env_sky`, `env_mountains`, `env_clouds` (with `env_cloud_NN` children), `env_hills`, `env_bushes`, `env_terrain`; sample the terrain height at 12 points inside the flat zone (all |y| <= 0.005); print triangle and byte counts.

## 3-1. Root cause & prevention
- Symptom (measured): today's room background is a 4.4 m grass disc on a cream cone with white sphere clouds and a two-stop gradient sky (capture reviews/20261025/room/scoop-v9-look/ab-844.jpg); user: "배경도 별로고 구름도 별로고".
- Root-cause task: the direct cause is in `world.mjs` (`buildSky`/`buildWorld`): background built from primitives with hand-picked colours; main owns that file and deletes those parts when your env lands.
- Instruction-chain cause: the room-hub plan gave every tappable prop an art source (its object sheet, then Meshy) but never assigned the environment an art source; the first runtime brief asked for a "procedural stand-in world", and no later step replaced it with the plate. You fix the env half by building it from measured plate swatches recorded in env.json; main records the rule in the room skill.
- Same-class count: 1 (first time the background is measured against the plate).
- Cause type → prevention: process (missing art source for a whole layer) → env.json `swatches` + `bake_table` become the single place where each background colour comes from; main adds "every visible surface names its art source" to the room skill.
- Generalisation: any future world built from approved 2D art (other episodes' worlds, other rooms) uses the same layered build: swatches measured from the key art → baked layers → unlit runtime; keep the script data-driven so a new plate needs a new swatch block, not new code.
- Prevention: env.json swatches/bake_table (yours) + skill rule (main's).

## 4. 실행 명령 (그대로)
```
ssh opi128 'df -h /; free -g | sed -n 2p; pgrep -fa blender | head -3'   # before each run; other lane's Blender may be running — fine, stay at 3 threads
bash pipeline/room-env.sh            # (new) full build + renders
bash pipeline/room-env.sh --renders-only   # (new) re-render after a look tweak
```

## 5. 합격 기준
- `plate-match.jpg`: your render and plate-v4 read as the same place: horizon height within 3 % of the frame height, cloud banks in the same regions with the same soft-serve swirl character, hill row colours and sizes alike, no flat-card edges, no sky banding.
- bake_table: every surface within sRGB distance 12 of its swatch.
- Budgets of §3.3 met; re-import check of §3.7 passes; terrain flat zone exact.
- `room-844.jpg` / `room-1280.jpg`: top 25-40 % of the frame is sky + clouds + hills, the lawn fills the lower part, no edge of the world visible anywhere; `wide.jpg` shows lawn and hills continuing all around.
- Board lane cleaned: report the output of `ssh opi128 'ls <your lane paths>'` (nothing left of yours).

## 5-1. 자체 검증
```
python3 -c "import json;e=json.load(open('assets/room/scoop/set/env.json'));print(e['bytes'],sum(e['triangles'].values()));print([r for r in e['bake_table'] if r['distance']>12])"   # (new) expect bytes <= 8e6, tris <= 150000, []
bash -n pipeline/room-env.sh                                 # (new) expect no output
ls reviews/20261025/room/env/                                # (new) expect plate-match.jpg room-844.jpg room-1280.jpg wide.jpg
```
- Open every jpg yourself (view the image) before you report, and say in one line per image what still differs from the plate.

## 6. 금지
- Edit/create only: `tool/room_env_build.py` (new), `pipeline/room-env.sh` (new), `assets/room/scoop/set/env.glb` (new), `assets/room/scoop/set/env.json` (new), `reviews/20261025/room/env/**` (new). Main owns `runtime_src/scoop_sky/**`, `tool/build_scoop_sky_runtime.py`, `assets/runtime/**`; w5-set owns the other files in `assets/room/scoop/set/`.
- Read-only: `out/shorts/**`, `docs/shorts/**`, `reader/**`, `build/room-meshy/**`. No Meshy or any paid/generation API, never read `~/.config/meshy/` or any key file, no commits, no pushes.
- On opi128 touch only the paths you rsync; never touch `/tmp/sg-layout-lane/` or other sessions' processes; no git or setup scripts there; no `rm -rf` outside your own lane paths.
- No card/billboard image cut out of the plates for clouds or hills (the user asked for real separated, regenerated 3D layers with baked textures); sampling plate pixels for colour swatches and for a tileable grass texture is fine.

## 7. 보고 형식 (final message, 15-30 lines)
Headings in order: `## Root cause` · `## Prevention` · `## Symptom fix` (files, layer table: tris/bytes/textures) · `## Verification` (bake_table summary, budgets, re-import, one line per render on what still differs) · `## Unverified` · `## Assumptions` · `## Rejected alternatives` · `## Downstream` (what main must do in the runtime: node names, unlit contract, cloud nodes, flat zone) · `## Questions` (only if any). Last line REPORT-DONE.
