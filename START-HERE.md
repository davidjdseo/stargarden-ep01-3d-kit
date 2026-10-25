# START HERE — StarGarden EP01 "Scoop Sky" 3D kit: Blender job (2026-10-25)

You work alone in a cloud Linux box that has Blender. Nobody can answer questions live. When something is ambiguous:
- pick the recommended default written here or in the briefs;
- write it under "Assumptions" in REPORT.md;
- keep going.

Never stop at a demo or skeleton.

## 0. Owner's rules (verbatim, they apply to you)

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

- **Go all out (user rule):** do everything creatively, with courage, at full effort. The bar is maximum result for minimum time and minimum tokens. Root-cause corrective action follows the RCCA block above, and lessons go into the scripts and REPORT.md.
- **Locked art:** the character sheets, the object sheets and the background plates in this kit are APPROVED. Match them; never redesign a character, change a colour scheme or add objects that are not on a sheet.
- **No paid services:** no API calls (no Meshy, no image or video generation), no purchases, no uploads anywhere. The only hand-back is your result zip (section 5).

## 1. Expert lens (answer it again yourself before you start)
- **Expert.** You are a senior character TD plus an environment artist for stylised mobile games: three.js r186, WebGL, phone first, for children aged 3–6 who cannot read yet.
  - Do:
    - clean quads that deform;
    - UV seams hidden at the back and underside, never on the face;
    - textures re-baked with generous padding so mipmaps never bleed;
    - smooth shading with no normal map;
    - light rigs with bouncy, readable clips;
    - a world that reads exactly like the painted plate.
  - Never do:
    - ship a raw AI-scan unwrap;
    - auto-UV a face;
    - judge only from tiny renders. Judge from 1024 px face close-ups and the plate side-by-side sheet.
- **Sources first.**
  - The plate: `repo/out/shorts/ep01/anchors/world-theme-s1/A-scoop-sky/plate-v4.png`, plus `sky-v1`, `r7-side-v1`, `reverse-r4-v1`, `r6-flowerbed-v1` and `plate-v4-noisland`.
  - The character sheets: `repo/out/shorts/ep01/cast/s1/*-sheet.png` and `*-expr.png`, `repo/out/shorts/ep01/pack/character-moa-sheet.png`, and the turnarounds in `repo/assets/room/cast-inputs/<id>/`.
  - The object sheets and turnarounds: `repo/out/shorts/ep01/anchors/s1-objects/<id>/`.
  - The current GLBs: `repo/assets/room/scoop/`.
  - The Meshy sources: `repo/build/room-meshy/<id>/retex/`.
  - The runtime that loads everything: `repo/runtime_src/scoop_sky/`.
  - The three detailed briefs: `briefs/`.
- **Method.** Run data-driven bpy scripts headless with `blender -b --python <script> -- <args>`. Reuse and fix the scripts in `repo/tool/`, which are a head start (see STATUS.md).
- **Verified by.**
  - Exit 0 from `python3 tool/room_seam_check.py <glb>` on all five characters.
  - The swatch/bake tables in env.json and pieces.json are all at distance 12 or less in sRGB.
  - Budgets met.
  - A fresh-Blender re-import check passes.
  - Side-by-side sheets against the plate and the character sheets.
  
  Any FAIL means not done; say so in REPORT.md.

## 2. Setup
```
sha256sum stargarden-ep01-3d-kit.zip        # must equal the sha256 given with the link
unzip -q stargarden-ep01-3d-kit.zip && cd stargarden-ep01-3d-kit/repo   # ALWAYS work with cwd = repo/
blender --version                            # write it into REPORT.md
python3 tool/room_seam_check.py assets/room/scoop/piyo.glb   # expect FAIL (446) before your fix
```
Optional free add-ons:
- Install them only if they install cleanly offline-or-from-GitHub. Never block on them: the built-ins are enough. The built-ins are QuadriFlow/Voxel remesh, Mark Seam + Unwrap, Cycles bake selected-to-active, Armature with automatic weights, Data Transfer and the glTF exporter.
- QRemeshify (github.com/ksami/QRemeshify): quad retopology.
- TexTools (github.com/Oxicid/TexTools-Blender): UV and bake helpers.
- LoopTools (Blender Extensions): Relax.
- Rigify (bundled).
- The user also named "ArtCraft"/"VectorCraft". If a free add-on by that name exists, you may use it; otherwise skip it and say so.

Environment overrides. The briefs were written for the owner's own machines, so:
- Ignore everything about opi128, macpro, ssh, rsync, the `pipeline/*.sh` runners, `SendMessage`, git commits and Mac GPU captures. Run the same Blender scripts locally.
- Questions: write each one under "Questions" in REPORT.md with the default you chose, then continue.
- `tool/room_env_build.py` takes a JOB json whose `repo` key is the absolute path of your `repo/`. Read `pipeline/room-env.sh` to see the keys it writes.

## 3. Jobs, in this order

### Job A — cast: smooth faces, rigs, clips (do first; the user saw the face line)
Full spec: `briefs/w6-cast.md`. Previous attempt: STATUS.md §A.
Done when:
1. `python3 tool/room_seam_check.py assets/room/scoop/<id>.glb` exits 0 for each of piyo, mongsil, popo, nuri and moa.
2. The GLB has no normal map. The base colour is baked onto the new UVs with 16 px or more of padding, as WebP. The texture still matches the character sheet: compare it in a sheet-vs-render image.
3. Placement is unchanged: height 1.0 m, base at y 0, front +Z, same yaw as today's GLB (`pipeline/room-glb-yaw.json`).
4. Budgets:
   - friends: 1.2 MB or less, 9k triangles or less;
   - Moa: 4 MB or less, 20k triangles or less;
   - skin and all clips present; no cameras or lights.
5. Clips use exact names at 24 fps, written as NLA tracks so glTF exports separate animations:
   - Friends: `idle`, `happy`, `wave`, `dance`, plus one activity clip each: piyo `sing`, popo `kick`, nuri `count`, mongsil `bounce`.
   - Moa: keeps its 6 Meshy clips (`idle`, `walk`, `wave`, `dance`, `jump`, `sway`) and gains `happy` and `kick`.
   - No foot sliding and no broken limbs.
6. The five entries in `assets/room/scoop/manifest.json` are updated: src, src_sha256, out_bytes, sha256, tris, textures, clips and bbox_after.
7. Renders in `reviews/20261025/room/cast-rig/`:
   - `<id>-face.jpg`: 1024 px front and 3/4 face close-ups, smooth shading, no line;
   - `<id>-views.jpg`;
   - `<id>-clips.jpg`: 4 frames per clip;
   - `<id>-clips.mp4`: H.264, 3 MB or less.

### Job B — env: the plate world out to a 360° horizon
Full spec: `briefs/w4-env.md`. Previous attempt and its 7-point fix list: STATUS.md §B.
Done when:
- `assets/room/scoop/set/env.glb` is 8 MB or less and has 150k triangles or less.
- Its node names are `env_sky`, `env_mountains`, `env_clouds` (with `env_cloud_NN` children), `env_hills`, `env_bushes` and `env_terrain`.
- The terrain is exactly flat at y 0 inside radius 10 m and inside the corridor |x| ≤ 8, 0 ≤ z ≤ 16.
- Textures are WebP, 2048 px or less.
- Every row of `env.json` `bake_table` is at distance 12 or less.
- `reviews/20261025/room/env/plate-match.jpg`, plate-v4 next to your render from the plate camera, shows the same horizon height, cloud bank shapes, hill colours and spacing.
- A 360° sheet shows no hard edge at the horizon.

### Job C — set pieces: trees, bushes, fence, flowers, stones
Full spec: `briefs/w5-set.md`. Previous attempt: STATUS.md §C. Only tree-pink is built, and there is a PNG id-map bug.
Done when:
- All 10 pieces are in `assets/room/scoop/set/`: tree-pink, tree-mint, berry-bush, berry-bush-s, daisy, grass-tuft, mint-bush, fence, fence-post and cookie-stone.
- Sizes and budgets follow the brief.
- The `pieces.json` swatch table is valid, with every row at 12 or less.
- `reviews/20261025/room/set-views/<piece>.jpg` shows the reference crop next to 4 views, and there is a `lineup.jpg`.

## 4. How the runtime uses your files (do not edit the runtime; read it)
- `runtime_src/scoop_sky/moa.mjs` finds clips by exact name; gestures are one-shot.
- `world.mjs` will load `set/env.glb` unlit (MeshBasic map + vertex colours, no tone mapping) and drift the `env_cloud_NN` nodes.
- Set pieces and characters render lit with one light-neutral colour factor (see `shade.mjs`), so bake albedo only, with no lighting baked into character textures.
- Play stations (docs/room-hub/DESIGN.md §10):
  - Piyo = music (xylophone)
  - Popo = ball (counting passes)
  - Nuri = numbers
  - Mongsil = colours
  
  The friend clips are what the child sees while playing, so make them read at phone size.

## 5. Hand-back
1. Make `stargarden-room-3d-result.zip` with:
   - `REPORT.md` at the top level;
   - only new or changed files, at their paths under `repo/` (for example `repo/assets/room/scoop/piyo.glb`, `repo/tool/room_cast_build.py`).
2. Attach that zip to your final answer so the user can download it. Also put the five face close-ups and the plate-match sheet inline in the answer.
3. REPORT.md gives, per job:
   - what you built;
   - the measured numbers against each "Done when" line, marked PASS or FAIL;
   - the exact rebuild commands;
   - Assumptions;
   - Questions;
   - known issues;
   - what you did not verify.

## 6. Kit contents
See `MANIFEST.txt` (path, bytes, sha256, role). `briefs/` holds the three original briefs, unchanged except for this file's overrides.
