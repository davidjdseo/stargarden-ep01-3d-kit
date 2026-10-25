# 작업 지시: Scoop Sky room set pieces in Blender (cotton-candy trees, berry bushes, wafer fence, cookie stones, lawn flowers) with baked textures that match the approved plate

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

Goal: build the near set pieces of the Scoop Sky room as phone-ready textured GLBs in Blender on opi128, each one looking like its counterpart in the approved world plate and object sheets: pink and mint cotton-candy trees with twisted waffle trunks, berry bushes (strawberries, blueberries, daisies), single daisies and fluffy grass tufts for the lawn, a mint broccoli bush, a wafer picket fence module + rolled-wafer post, and a cookie stepping stone. Main places them in the room; a parallel worker (w4-env) builds the far background.
Deliverable: `tool/room_setpieces_build.py` (new) (Blender script), `pipeline/room-setpieces.sh` (new) (lane runner), `assets/room/scoop/set/<piece>.glb` (new) for the 10 pieces in §3, `assets/room/scoop/set/pieces.json` (new), renders under `reviews/20261025/room/set-views/` (new); final message = report (§7).

## 0. 질문 먼저 (필수)
Read the whole brief first. If something is ambiguous, send ONE numbered batch of questions to main with `SendMessage` (recommended answer first) and keep doing every part that does not depend on the answer; never guess on the blocked part.
**Ask before any deviation:** if reality differs from §2 or a change outside the §6 file list looks necessary, stop that part and ask main (SendMessage) with your recommendation. Never apply it and report afterwards.

## 1. 목표 (사용자 말 인용 + 왜)
User (2026-10-25, room-hub session, speech-to-text): "원화 보고 그 원래 시안 있잖아 … 배경 플레이트 보고 분리할 거 싹 분리하고 다시 생성해가지고 텍스처 굽고 텍스처 입혀주고 거의 그거랑 똑같이 계속해서 작업해줘 … 별로인 것들 최대한 똑같이 작업해줘. 텍스처 입혀가지고. 그리고 사이즈도 좀 더 크게 세계관 확장해주고." Then: "코덱스 아스트라 미디움 … GPT-6 아스트라 모델이 그 블렌더 작업 잘하거든? … 지시서 상세하게 하고 너랑 좀 작업을 나눠가지고 해줘."
Why: today the room's trees are three plain pink spheres on a stick, the fence and path stones are flat primitives (see the current capture in §2-2). The plate's charm is in exactly these pieces: fluffy cotton-candy canopies with little white flowers, glossy berry bushes, wafer pickets, scalloped cookie stones. They sit next to tappable Meshy props, so they must hold up at the same viewing distance on a phone.

## 1-1. Expert lens
- Expert: a senior stylised-prop / technical artist for mobile 3D (pastel toy-world games): clean low-poly silhouettes with the fluff and fine detail in baked normal + albedo maps, pivots at the base, honest budgets per piece, colours sampled from the key art; never a raw high-poly sculpt, never guessed colours, never baked direct lighting on a piece that the runtime lights.
- Sources: the object sheets (`out/shorts/ep01/anchors/s1-objects/wafer-fence/turn/*.png`, `out/shorts/ep01/anchors/s1-objects/cookie-stone/turn/*.png`), the plates for the trees/bushes/flowers/grass (`plate-v4.png` left and right trees and fence-side bushes, `r7-side-v1.png` right tree seen whole, `r6-flowerbed-v1.png` berry bush and daisies, `reverse-r4-v1.png`), today's stand-ins in `runtime_src/scoop_sky/world.mjs` (trees from `TREE_LUMPS` in `runtime_src/scoop_sky/layout.mjs`, fences and path stones in `buildWorld`), the lights block of `runtime_src/scoop_sky/props.json`, Blender 5.0.1 bake + glTF exporter options read on opi128 (`help()`), not from memory.
- Method and tools: one data-driven bpy script (one function per piece, shared helpers for fluff/bake/export), high-detail source → low-poly game mesh → Cycles bake (normal + AO; albedo from swatch materials) → glTF WebP export; 4-view preview renders + a lineup render; PIL sheets. Runner rsyncs only your files to opi128 and back.
- Verified by: per-piece sheets (4 views next to the sheet/plate crop), an albedo swatch table (texel mean per part vs plate swatch, sRGB distance <= 12), budgets, re-import checks (pivot, size, facing), and a lineup render from the room camera with runtime-like lights. Wrong if: canopies read as smooth spheres, flowers float or clip, the fence pattern is missing, the stone is a plain disc, textures are blurry/stretched, pieces float above y = 0, or colours drift.
- Reframe: "would a child who saw the plate point at this tree and say 'that one'?" Match silhouette and colour masses first, then surface detail.

## 2. 확인된 사실 (메인이 확인한 것)
- Look truth (read-only): `out/shorts/ep01/anchors/world-theme-s1/A-scoop-sky/plate-v4.png` 1672x941 (trees cut by the left/right frame edges, fence row with bushes, cookie path), `r7-side-v1.png` (one whole pink/mint tree at the right with its twisted waffle trunk; fence in perspective), `r6-flowerbed-v1.png` (big berry bush: glossy round green leaves, strawberries, blueberries, white daisies with yellow centres; single daisies in the lawn), `reverse-r4-v1.png`. Object sheets with 4 views: `out/shorts/ep01/anchors/s1-objects/wafer-fence/turn/front.png` (wafer pickets with pointed tops and diagonal cream stripes, pink rails, a rolled-wafer post with a pink cap) and `out/shorts/ep01/anchors/s1-objects/cookie-stone/turn/front.png` (scalloped round biscuit with docking holes).
- Runtime lighting contract (already shipped, `runtime_src/scoop_sky/main.mjs` + `world.mjs` `calibrateLook` + `shade.mjs` `lightNeutralMult`): pieces render LIT with three.js MeshStandardMaterial from the GLB under props.json lights (hemi sky #cfe8ff / ground #ffe6cc x1.4, key #fff4e6 x1.2 from direction (-5, 9, 6)); main sets every material's base-colour factor so a face with normal (0, 0.45, 0.9) shows EXACTLY its texture colour, plus a 0.04 white emissive; the Khronos PBR Neutral tone map compresses channels above ~225 sRGB slightly. So: albedo texture = the plate's colour of that part on its lit side; bake ambient occlusion into the albedo mildly (crevices between canopy balls, under berries) but NO direct light or shadows; normal maps are welcome.
- Coordinates: glTF Y up, metres, pivot at the base centre (min y = 0), front faces +Z (the default room camera looks toward -Z, so +Z faces the camera). Keep the exporter default (+Y up) and verify with a re-import.
- opi128 (measured by main 2026-10-25 16:2x): Blender 5.0.1 at /usr/bin/blender, 8 cores, ~10 GB RAM available, 65 GB free disk. ANOTHER SESSION is rendering there (`/tmp/sg-layout-lane/`): never touch it, use at most 3 Cycles threads. w4-env also runs there with 3 threads. Headless `blender -b --factory-startup`; Cycles CPU is the safe renderer (software EGL for EEVEE is slow). The opi128 repo dir is an rsync lane copy, not git: never run git or setup scripts there.
- w4-env writes `assets/room/scoop/set/env.glb` (new) + `env.json` in the same folder: disjoint names, never touch them.

## 2-1. Pre-flight
- P1: paths checked by main with ls 2026-10-25: plates and the wafer-fence / cookie-stone turn sheets exist; `assets/room/scoop/` exists; `assets/room/scoop/set/` (new) and every output marked (new) do not exist yet.
- P2: plate sizes measured with PIL (1672x941); lights values copied from props.json `lights`; opi128 resources measured over ssh (values in §2).
- P3: N/A for placement (main's); previews at 384 px per view and the lineup at 844x390.
- P4: no gate changed; main commits.
- P5: runtime claim = main's existing `calibrateLook` path (world.mjs, shipped in commit 307126c0); main will load your GLBs with GLTFLoader and apply it, unchanged.
- P6: consumers of `assets/room/scoop/set/<piece>.glb`: only `runtime_src/scoop_sky/world.mjs` / `main.mjs` (main, after you finish).
- P7: perceived: on a phone next to the Meshy props, each piece reads as the plate's version (silhouette, colours, fluffy/glossy/wafer surface), sits on the lawn, no seams or stretched texture.
- P8: shared files — `assets/room/scoop/set/` shared with w4-env (disjoint names); opi128 `/tmp/sg-layout-lane/` is another session's.
- Generation auth: N/A — no generation API (no Meshy, no image model); everything is modelled and baked in Blender.
- Known unknowns: bake time at 3 threads (keep the high-detail sources modest); whether texture-space fibre noise is enough for the cotton-candy fluff or a displaced high-poly → normal bake is needed (try the cheaper one first and compare on the 4-view render).

## 2-2. Evidence
- ToneLock: out/shorts/ep01/anchors/world-theme-s1/A-scoop-sky/plate-v4.png
- IMG: out/shorts/ep01/anchors/world-theme-s1/A-scoop-sky/plate-v4.png
- IMG: out/shorts/ep01/anchors/world-theme-s1/A-scoop-sky/r7-side-v1.png
- IMG: out/shorts/ep01/anchors/world-theme-s1/A-scoop-sky/r6-flowerbed-v1.png
- IMG: out/shorts/ep01/anchors/s1-objects/wafer-fence/turn/front.png
- IMG: out/shorts/ep01/anchors/s1-objects/cookie-stone/turn/front.png
- IMG: reviews/20261025/room/scoop-v9-look/ab-844.jpg
- Where: Scoop Sky room `?room=scoop` at 844x390: the trees behind the cottage left/right, the fence either side of the cottage, the path stones from the cottage door to the front, the lawn between props. The last image is today's room (top = before colour fix, bottom = after) with the stand-ins you replace.

## 3. 메인 결정 (그대로 구현)
1. Pieces (id, size, notes). Sizes are final: main lays out the room in these units.
   - `tree-pink`: total height 4.0 m, canopy about 2.8 m wide; 5-7 fluffy canopy balls mostly cotton-candy pink with 1-2 mint balls; 10-16 small white 5-petal flowers with yellow centres sitting on the canopy surface; twisted waffle-cone trunk (golden-brown with the cross-hatch waffle pattern, a gentle spiral twist), slight root flare on the ground.
   - `tree-mint`: total height 3.6 m, mostly mint canopy with 1-2 pink balls, same flowers and trunk family (not a recolour only: different ball arrangement).
   - `berry-bush`: 1.5 m wide (x) x 1.0 m deep x 0.55 m tall: mound of glossy round green leaves, 6-8 strawberries (red with seeds, green calyx), 8-12 blueberries (dusty blue with a crown), 4-6 white daisies.
   - `berry-bush-s`: 0.8 x 0.6 x 0.38 m, same family, fewer berries.
   - `daisy`: 0.30 m tall single daisy (white petals, yellow centre) with a short stem and two leaves.
   - `grass-tuft`: 0.40 m wide x 0.20 m tall fluffy lawn tuft in the plate's lawn greens, <= 400 triangles (main instances hundreds of them).
   - `mint-bush`: 1.3 x 1.3 x 1.1 m broccoli/cauliflower cluster in mint and soft green, like the bushes between the hills of plate-v4 and r7-side.
   - `fence`: one module 1.0 m long along x, 0.70 m tall: 3 wafer pickets (pointed/rounded tops, diagonal cream stripes on golden wafer, waffle relief in the normal map) and 2 pink rails, matching the wafer-fence sheet; modules tile end to end along x with no gap or overlap (pivot at the module's left-bottom-centre of thickness OR base centre — pick base centre and state it; length exactly 1.0 m between tiling ends).
   - `fence-post`: rolled-wafer post 0.80 m tall, 0.14 m diameter, pink cap, like the sheet.
   - `cookie-stone`: scalloped biscuit stepping stone, radius 0.42 m, 0.08 m thick, rounded edge, 9-11 docking holes like the sheet, golden biscuit colour; lies flat (top at y = 0.08, base at 0).
2. Colour = measured: write a `swatches` block in pieces.json first: for each part (canopy-pink, canopy-mint, flower-white, flower-centre, trunk-light, trunk-dark, leaf, leaf-dark, strawberry, blueberry, wafer, wafer-stripe, rail-pink, cap-pink, cookie, cookie-hole, lawn-light, lawn-mid, bush-mint, bush-green) the source image, the pixel box (lit side) and the mean sRGB. Build materials from those swatches with procedural variation, bake to one albedo atlas per piece (max 2 materials per piece), plus a normal map where the surface detail needs it (canopy fluff, waffle pattern, leaf veins, cookie surface). Then table per part: albedo texel mean vs swatch, sRGB distance <= 12.
3. Budgets per piece: trees <= 15k triangles and <= 1.0 MB; bushes <= 8k and <= 600 KB; fence/post/stone/daisy/mint-bush <= 5k and <= 400 KB; grass-tuft <= 400 triangles and <= 120 KB. Textures WebP quality 85-90: trees 1024 px albedo + 1024 normal, others 512 px (fence may use 1024 for the waffle). One mesh per piece where possible (trees may keep trunk + canopy as 2 meshes), transforms applied, no cameras/lights.
4. Script and runner: `blender -b --factory-startup -P tool/room_setpieces_build.py -- <job.json>` (job = pieces to build, seed, threads 3, render flags). `bash pipeline/room-setpieces.sh (new) [piece ...] [--renders-only]` (default: all 10): `ssh opi128 'df -h /'` (abort under 10 GB free), rsync the script + the sheets/plates it samples to opi128 at the same absolute paths, run Blender there (`nice -n 5`), rsync back the GLBs, pieces.json and the renders, delete only your copies on the board and print what it deleted. Fixed seed: re-running gives the same GLBs.
5. Renders (Cycles CPU 3 threads, Standard view transform) into `reviews/20261025/room/set-views/` (new): per piece `<piece>.jpg` = 4 views at 384 px (front +Z, right +X, back -Z, left -X) beside the sheet front or the plate crop you matched (state the crop box); `lineup.jpg` = all pieces arranged like plate-v4 (fence modules + posts in a row either side of a gap at z = -5, cookie stones in a path toward the camera, a tree at each side behind the fence, bushes along the fence, daisies and tufts scattered on a plain green ground) from camera pos (0, 3.4, 12.5) looking at (0, 1.6, -6), vertical fov 34 deg, 844x390, lit like the runtime (world colour = hemi average, a sun from direction (-5, 9, 6) with #fff4e6) so main sees how they read together. Write a first draft render of `tree-pink` within your first ~30 minutes as `draft-tree-pink.jpg`.
6. pieces.json (new): per piece {glb, bytes, sha256, triangles, textures (name, px, bytes), bbox (min, max), pivot, front, swatch_table rows}, plus the top-level `swatches` and `seed`.
7. After export, re-import every GLB in a fresh Blender: assert bbox height within 1 % of §3.1, min y = 0 +/- 1 mm, centre x/z within 1 cm (fence: tiling length 1.000 m +/- 2 mm), texture sizes as exported, and print the table.

## 3-1. Root cause & prevention
- Symptom (measured): today's trees are three pink spheres on a stick (`TREE_LUMPS`, layout.mjs), fences and path stones are untextured primitives (world.mjs `buildWorld`), visible in reviews/20261025/room/scoop-v9-look/ab-844.jpg; user: "별로인 것들 최대한 똑같이 작업해줘. 텍스처 입혀가지고".
- Root-cause task: the direct cause is the procedural stand-ins in world.mjs / layout.mjs (main's files; main swaps them for your GLBs).
- Instruction-chain cause: the room-hub plan sent only tappable props through the art-sheet → Meshy → Blender route; the set dressing was ordered as "procedural stand-ins" in the first runtime brief and no later step gave it an art source or a production route. Your pieces close the gap; main records "every visible surface names its art source" in the room skill.
- Same-class count: 1 (first time the set dressing is built from the art).
- Cause type → prevention: process (layer without an art source) → pieces.json `swatches` + `swatch_table` are the single place each piece's colours come from; main adds the skill rule.
- Generalisation: the piece kit is data-driven (one function + one swatch block per piece), so another world (episode 2, a new room) reuses the script with new swatches and sizes; keep piece ids generic (tree-pink, fence, cookie-stone) and the sizes in the job data.
- Prevention: pieces.json swatches (yours) + skill rule (main's).

## 4. 실행 명령 (그대로)
```
ssh opi128 'df -h /; free -g | sed -n 2p; pgrep -fa blender | head -3'   # before each run; other lanes may be rendering — stay at 3 threads
bash pipeline/room-setpieces.sh (new) tree-pink        # first: one piece end to end, look at its sheet
bash pipeline/room-setpieces.sh (new)                  # then all 10 + lineup
```

## 5. 합격 기준
- Each `<piece>.jpg`: the front view reads as the sheet/plate counterpart (silhouette, colour masses, surface character); say per piece what still differs.
- swatch_table: every part within sRGB distance 12.
- Budgets of §3.3 met; re-import checks of §3.7 pass for all 10.
- `lineup.jpg` from the room camera reads like the plate's foreground and mid-ground.
- Board lane cleaned: report the output of `ssh opi128 'ls <your lane paths>'` (nothing left of yours).

## 5-1. 자체 검증
```
python3 -c "import json;p=json.load(open('assets/room/scoop/set/pieces.json'));print({k:(v['bytes'],v['triangles']) for k,v in p.items() if isinstance(v,dict) and 'glb' in v})"   # (new) expect 10 pieces within §3.3
bash -n pipeline/room-setpieces.sh                                                                            # (new) expect no output
ls reviews/20261025/room/set-views/                                                                           # (new) expect 10 piece jpgs + lineup.jpg
```
- Open every jpg yourself (view the image) before you report.

## 6. 금지
- Edit/create only: `tool/room_setpieces_build.py` (new), `pipeline/room-setpieces.sh` (new), `assets/room/scoop/set/<piece>.glb` (new) for the 10 ids in §3.1, `assets/room/scoop/set/pieces.json` (new), `reviews/20261025/room/set-views/**` (new). Main owns `runtime_src/scoop_sky/**`, `tool/build_scoop_sky_runtime.py`, `assets/runtime/**`; w4-env owns `assets/room/scoop/set/env.*`.
- Read-only: `out/shorts/**`, `docs/shorts/**`, `reader/**`, `build/room-meshy/**`, the existing `assets/room/scoop/*.glb`. No Meshy or any paid/generation API, never read `~/.config/meshy/` or any key file, no commits, no pushes.
- On opi128 touch only the paths you rsync; never touch `/tmp/sg-layout-lane/` or other sessions' processes; no git or setup scripts there; no `rm -rf` outside your own lane paths.
- No flat cards cut out of the plates (the user asked for separated, rebuilt 3D pieces with baked textures); sampling plate pixels for swatches and small texture detail is fine.

## 7. 보고 형식 (final message, 15-30 lines)
Headings in order: `## Root cause` · `## Prevention` · `## Symptom fix` (files, per-piece table: tris/bytes/textures/height) · `## Verification` (swatch_table summary, budgets, re-import, one line per piece on what still differs) · `## Unverified` · `## Assumptions` · `## Rejected alternatives` · `## Downstream` (what main must know to place them: pivots, fence tiling, instancing candidates) · `## Questions` (only if any). Last line REPORT-DONE.
