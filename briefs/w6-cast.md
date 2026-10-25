# 작업 지시: Room cast clean-up in Blender (Piyo, Mongsil, Popo, Nuri, Moa): retopology, UV with no seam across the face, texture bake, simple rigs and the play-station animation clips

You are a StarGarden implementation worker (Claude Opus 5.5 sg-worker subagent, effort high) and the Blender character TD on this job. Report in English. Do not launch other agents or Claude/Codex runs. **Attitude (user-specified, every worker):** Be creative, autonomous and proactive. Work like an efficient early-stage startup (maximum results with minimum time and tokens). Work with courage. Go all out. RCCA: follow the canonical block below (docs/agents/RCCA.md), included verbatim.

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

Goal: make the five room characters smooth, seam-free and animated. Rebuild each one as a clean mesh whose UV seams never cross the face. Bake its texture from the Meshy source, rig it, and author the clips the new play stations need. Then ship the GLBs in place of today's `assets/room/scoop/<id>.glb`.

Deliverable (final message = report, §7):
- `tool/room_cast_build.py` (new): the Blender script.
- `pipeline/room-cast.sh` (new): the lane runner on macpro.
- `tool/room_seam_check.py` (new): a pure-python seam measure.
- Rebuilt `assets/room/scoop/{piyo,mongsil,popo,nuri,moa}.glb`.
- Updated entries for those five ids in `assets/room/scoop/manifest.json`.
- Renders under `reviews/20261025/room/cast-rig/` (new).

## 0. 질문 먼저 (필수)
Read the whole brief first. If something is ambiguous, send ONE numbered batch of questions to main with `SendMessage`, recommended answer first. Keep doing every part that does not depend on the answer. Never guess on the blocked part.

**Ask before any deviation:** if reality differs from §2, or a change outside the §6 file list looks necessary, stop that part and ask main (SendMessage) with your recommendation. Never apply it and report afterwards.

## 1. 목표 (사용자 말 인용 + 왜)
User (2026-10-25, speech-to-text): "병아리 모양 있잖아요. 삐요 걔 얼굴에 가운데 세로선으로 줄이 있는 것 같아요. 음영 같은 게. … 매끈하게 해주고 블렌더에 플러그인들이 … 적절한 거 사용해가지고 리터폴로지냐 블렌더 UV 믹스하고 그런 거 다 해주고 … 애니메이션 다 돼야 되고 서로 상호작용해야 돼. 예를 들어서 어디 갔을 때는 책 읽기, … 누구한테 갔을 때는 음악놀이, … 공놀이, 숫자놀이".

Why: the room's friends are the play stations (docs/room-hub/DESIGN.md §10). The child taps a friend, Moa walks over, and they greet and play: Piyo = music, Popo = ball, Nuri = numbers, Mongsil = colours. Today the friends are static meshes with no rig, and a line runs down Piyo's face on the phone.

## 1-1. Expert lens
- Expert: a senior character TD for stylised mobile games. They want:
  - clean quad topology that deforms;
  - UV seams hidden at the back and underside;
  - textures re-baked from the source with generous padding, so mipmaps never bleed;
  - smooth shading;
  - light rigs with readable, bouncy, kid-friendly clips.
  
  They would never ship a raw AI-scan unwrap (seams everywhere, one down the face) or auto-UV a face.
- Sources:
  - `assets/room/scoop/<id>.glb`: the placement truth (1 m tall, base at y 0, front +Z).
  - `build/room-meshy/<id>/retex/asset_model_urls_glb.glb`: the 2K-texture source.
  - Character sheets: `assets/room/cast-inputs/<id>/{front,back,left,right}.png`.
  - Main's measurement scripts `reviews/20261025/room/cast-seam/glbseam.py` and `faceseam.py`, with results in `reviews/20261025/room/cast-seam/before.txt`.
  - The runtime clip loader `runtime_src/scoop_sky/moa.mjs` lines 40-55. It finds clips by name; gestures are one-shot.
  - Blender 5.2.1 operators (`bpy.ops.object.quadriflow_remesh`, unwrap, bake, Data Transfer, glTF export). Read them with `help()` on macpro, not from memory.
- Method and tools:
  - One data-driven bpy script per character, run headless on macpro (Blender 5.2.1, Cycles Metal GPU for bakes).
  - Built-in QuadriFlow or Voxel remesh.
  - Seam marking + Unwrap; no Smart UV on the head.
  - Cycles bake selected-to-active.
  - Armature + automatic weights. Moa keeps its Meshy armature; transfer weights with Data Transfer.
  - NLA-tracked actions; glTF export with WebP.
  - Add-ons on macpro: looptools, bool_tool, ucupaint, grease_pencil_tools. Use LoopTools Relax if it helps the retopology; nothing else is required.
  - opi128 has only blender_mcp (no useful add-ons) and is busy with two other lanes, so use macpro.
- Verified by:
  - `tool/room_seam_check.py` (new) shows a front-face seam count of 0 for each friend. Before: piyo 180, mongsil 56, popo 81, nuri 25, moa 88.
  - Face close-ups, before | after, at 768 px, with an EEVEE preview using mipmapped 1K textures (the phone path).
  - A turntable of each clip.
  - Re-import checks: clip names, skin, height 1 m, base y 0, front +Z.
  - Budgets.
  
  It is wrong if:
  - any seam vertex sits on the front face;
  - the face, eyes, beak or cheeks lose detail or shift;
  - a bake seam is visible;
  - a clip is missing or named differently;
  - feet slide or limbs break in a clip.
- Reframe: "Where can a seam live so a child never sees it, and does the topology bend where the clips need it?" Plan seams and joints together.

## 2. 확인된 사실 (메인이 확인한 것)
- **Seam measurement.** Measured by main on 2026-10-25 (numpy over the GLB accessors; scripts in `reviews/20261025/room/cast-seam/`).
  - Piyo has UV island boundaries running down the front centre of the face, from y 0.39 to 0.95. That is 180 duplicate-position seam groups with UV jumps of 0.7-0.88; 76 of them also have split normals.
  - All five characters have the same class of defect (`before.txt`).
  - No GLB has a TANGENT attribute. All carry a normal map from Meshy retex.
- **Where the line shows.**
  - Blender Cycles renders of today's piyo.glb show NO line, in all four variants: as is, normal map off, welded, welded + normal map (`reviews/20261025/room/cast-seam/piyo-blender-variants.jpg`).
  - The phone shows a vertical line from the crown to the beak (`piyo-face-crop.png`). The phone path is three.js r186 with mipmapped textures; without tangents it does normal mapping by screen-space derivatives.
  - So the visible line comes from the face-centre UV seam under three.js mipmapping and derivative tangents, not from the mesh silhouette.
  - Removing the face seam (re-UV + re-bake) and dropping the Meshy normal map (smooth toy look) removes both mechanisms.
- **Today's GLBs.**

  | id | tris | size | rig |
  |---|---|---|---|
  | piyo | 11,939 | 494 KB | none |
  | mongsil | 11,940 | 409 KB | none |
  | popo | 11,940 | 575 KB | none |
  | nuri | 10,566 | 355 KB | none |
  | moa | 19,900 | 1.50 MB | Meshy rig, 24 joints, clips `idle` + `walk` |

  - Moa's source is `out/shorts/ep01/cast3d/moa/walk/asset_result_animation_glb_url.glb` (read-only).
  - All are normalised: height 1.0 m, base y 0, centred XZ, front +Z (manifest.json `bbox_after`; `yaw_deg` in `pipeline/room-glb-yaw.json`).
- **Nuri's Meshy rig.** Nuri also has a Meshy rig and one Meshy animation under `build/room-meshy/nuri/rig/` and `anim-01a1715b/` (read-only). You may ignore them and rig Nuri in Blender like the others, for one consistent clip set. Say which you chose.
- **Runtime colour contract (shipped).**
  - Main sets each material's base-colour factor so a face at normal (0, 0.45, 0.9) shows exactly its texture colour (`calibrateLook`, world.mjs).
  - `assets/room/scoop/look.json` is written by `tool/room_tex_means.py`. It stores each GLB's sha256, and the selftest fails when a GLB changes without a re-run.
  - So after you replace GLBs, run `python3 tool/room_tex_means.py` (it reads manifest.json).
- **macpro** (measured 2026-10-25 16:3x).
  - Blender 5.2.1 at `/Applications/Blender.app/Contents/MacOS/Blender`; 8 cores, 16 GB RAM, 28 GB free disk, Metal GPU.
  - The user's live Blender MCP processes run there (`blender-mcp`). Never touch them; run your own headless `Blender -b --factory-startup`.
  - Lane folder: `~/sg-lanes/room-cast/` (new) only.
- **Clip contract** (DESIGN.md §10). Exact names, 24 fps.
  - Every friend gets:
    - `idle`: loop, 2-3 s, gentle breathe/sway;
    - `happy`: one hop with squash, ~1 s;
    - `wave`: wing/arm wave, ~1.5 s;
    - `dance`: loop, 2 s, bouncy.
  - Plus one activity clip each:
    - Piyo `sing`: loop; head bob plus a beak/chest pulse;
    - Popo `kick`: ~1 s; one foot kicks forward;
    - Nuri `count`: ~1 s; nod plus point/arm forward;
    - Mongsil `bounce`: loop; springy body bounce.
  - Moa keeps `idle` and `walk` unchanged and gains `wave`, `happy`, `dance` and `kick`.

## 2-1. Pre-flight
- P1: main checked these paths with ls on 2026-10-25: the five GLBs, the retex sources, the cast sheets (popo has front/back only), the seam scripts and before.txt all exist. Outputs marked (new) do not exist yet.
- P2: main measured the seam counts and tri/byte numbers (scripts above, manifest.json) and the macpro resources over ssh.
- P3: N/A for layout. Renders: 768 px close-ups and 512 px turntables.
- P4: you change no gate except adding the new measure script. Main wires `tool/room_seam_check.py` (new) into the room checks after you finish.
- P5: runtime claims. Clips are found by name in `runtime_src/scoop_sky/moa.mjs` (Moa); friends will use the same loader (main's change). The phone check is main's Mac GPU capture.
- P6: consumers of the five GLBs: `runtime_src/scoop_sky/main.mjs`, `moa.mjs`, and `look.json`/selftest (main re-checks).
- P7: perceived result: on a phone, Piyo's face (and every friend's) is smooth with no line, characters look like their sheets, and each clip reads clearly at phone size.
- P8: shared files.
  - `assets/room/scoop/manifest.json` is also written by `pipeline/room-glb.sh` (nobody runs it now). Change only the five ids' entries.
  - Change `assets/room/scoop/look.json` only via `tool/room_tex_means.py`.
- Generation auth: N/A. No generation API; Meshy is not called (no credits).
- Known unknowns:
  - Whether QuadriFlow keeps the beak/eye/cheek shape at ~5k faces. Compare renders; if not, fall back to welding and cleaning the Meshy remesh topology and only re-UV + re-bake.
  - Moa's weight-transfer quality around the face and hands.
  - The bake cage distance for each character.

## 2-2. Evidence
- IMG: reviews/20261025/room/cast-seam/piyo-face-crop.png
- IMG: reviews/20261025/room/cast-seam/piyo-blender-variants.jpg
- IMG: assets/room/cast-inputs/piyo/front.png
- IMG: assets/room/cast-inputs/contact.jpg
- Where: Scoop Sky room `?room=scoop`, 1280x800 capture `reviews/20261025/room/scoop-v9-look/shot-1280x800-0.png`. Piyo is in the left foreground (screen box from props.json); the line runs from the crown tuft to the beak.

## 3. 메인 결정 (그대로 구현)
1. **Friends (piyo, mongsil, popo, nuri): low mesh.**
   - Import the retex source and place it exactly like today's GLB. Match the bbox: height 1.0 m, base 0, centre XZ, same yaw.
   - Weld (merge by distance).
   - Build the low mesh with QuadriFlow, target 4,000-7,000 faces, preserving sharp and boundary edges as needed.
   - If features degrade, use the welded, cleaned Meshy topology instead.
   - Smooth shading; no custom split normals.
2. **UV.**
   - Mark seams only on the back (a vertical seam on the back centre), under the base/feet and inside hidden folds.
   - NO seam in the front face zone (the front-facing faces of the head).
   - Unwrap (angle based or conformal); pack with a 16 px margin at 1024 px.
   - Write the seam plan for each character into the job data.
3. **Bake.**
   - Bake base colour from the source mesh's texture onto the low mesh: selected-to-active, with cage or extrusion tuned so no rays miss.
   - 1024 px, 16 px margin, extend.
   - No normal map; roughness constant 0.8; metallic 0.
   - Check the bake on the 4 views next to the sheet.
4. **Rig the friends.**
   - Armature: `root` → `body` → `head`, plus `wing_l/r` or `arm_l/r`, `foot_l/r`, and ears/tail if the character has them.
   - Automatic weights, then fix weights wherever the clips show breaks.
   - Author the §2 clips as actions on NLA tracks, so the glTF exporter writes them as separate named animations.
5. **Moa.**
   - Re-UV and re-bake like the friends, keeping its silhouette.
   - Retopology is optional. If you retopo, transfer skin weights from the original with Data Transfer and check that `walk` and `idle` still deform cleanly.
   - Keep the Meshy armature, and keep the existing `idle`/`walk` actions byte-for-byte in timing.
   - Add `wave`, `happy`, `dance` and `kick`.
   - Budget: <= 4 MB.
6. **Export** each `assets/room/scoop/<id>.glb`:
   - WebP 1024, quality 88;
   - friends <= 1.2 MB and <= 9k triangles; Moa <= 4 MB and <= 20k triangles;
   - skin and all clips; no cameras or lights;
   - front +Z, height 1.0 m, base y 0.
7. **`tool/room_seam_check.py` (new).**
   - Pure python 3 (struct + json, no numpy; opi500 has no numpy).
   - For each GLB, count the duplicate-position vertex groups whose UVs differ (UV seams) inside the front face zone: vertex normal z > 0.3, |x - centre| < 30 % of the half width, y above 0.45 of the height.
   - Print one line per file.
   - Exit 1 if any friend has a count > 0. Moa too, unless you report a reason.
   - Run it before (on git HEAD copies) and after.
8. **Runner `pipeline/room-cast.sh (new) [id ...]`.** In order:
   1. Run `ssh macpro 'df -h ~'`; abort under 5 GB free.
   2. Rsync the script and inputs to `~/sg-lanes/room-cast/`.
   3. Run Blender there with GPU bakes.
   4. Rsync back the GLBs and renders.
   5. Update the five manifest entries: src, src_sha256, out_bytes, sha256, tris, textures, clips, bbox_after.
   6. Run `python3 tool/room_tex_means.py` and `python3 tool/room_seam_check.py (new) assets/room/scoop/{piyo,mongsil,popo,nuri,moa}.glb`.
   7. Delete the lane folder on macpro and print what it deleted.
9. **Renders**, into `reviews/20261025/room/cast-rig/` (new). Per id:
   - `<id>-face.jpg`: before | after face close-ups, front and 3/4. Use EEVEE with mipmapped textures at a phone-like small size, upscaled, plus a large Cycles view.
   - `<id>-views.jpg`: 4 views next to the sheet.
   - `<id>-clips.jpg`: a contact sheet with 4 frames per clip.
   - `<id>-clips.mp4`: a turntable or front view cycling the clips (H.264, <= 3 MB).
   
   Start with Piyo end to end and write `piyo-face.jpg` first.

## 3-1. Root cause & prevention
- Symptom (measured): a vertical line down Piyo's face on the phone (capture crop above). The same seam class is measured on all five characters (before.txt).
- Root-cause task: the direct cause is the Meshy unwrap. UV islands meet on the face centre line, and three.js shows that seam through mipmapping and derivative-based normal mapping (no tangents). Blender's renders hide it.
- Instruction-chain cause: our GLB lane brief (reviews/workers/room-hub-20261025/w2-glb/BRIEF.md §3.1) allowed this:
  - it kept Meshy's UVs and normal map;
  - it judged results on 384 px Blender 4-view renders, never on the phone renderer path and never at face close-up;
  - it had no seam-placement rule for characters.
  
  So a seam on the face could pass.
- Same-class count: 1. This is the first measured seam defect; the earlier colour drift was a different class.
- Cause type → prevention:
  - Mechanical (a script can see seam placement) → `tool/room_seam_check.py` (new), run in the cast lane and in main's room checks.
  - Process → the room skill gets the rule "characters: re-UV with seams off the face + re-bake, verify on a mipmapped close-up" (main writes it).
- Generalisation: every future character or prop with a face (other episodes, other rooms) goes through the same cast lane (re-UV, re-bake, seam check) before the runtime. Keep `room_cast_build.py` data-driven per character: seam plan, bone list and clip list live in the job data.
- Prevention: the seam check script and the cast lane runner (yours), plus the skill rule (main's).

## 4. 실행 명령 (그대로)
```
ssh macpro 'df -h ~'
python3 tool/room_seam_check.py (new) assets/room/scoop/piyo.glb       # before: expect a count > 0
bash pipeline/room-cast.sh (new) piyo                                  # first: Piyo end to end, look at piyo-face.jpg
bash pipeline/room-cast.sh (new) mongsil popo nuri moa                 # then the rest
```

## 5. 합격 기준
- `room_seam_check.py`: 0 front-face seam groups for all five (or a stated reason for Moa).
- Face close-ups: no line or seam, either at phone size or large. The features (eyes, beak, cheeks, tuft) match the before render and the sheet.
- Every GLB:
  - clips exactly as in §2 (names);
  - skin present;
  - height 1.0 m +/- 1 %, base y 0 +/- 1 mm, front +Z;
  - within the §3.6 budgets;
  - Moa's `walk`/`idle` timing unchanged.
- Clip contact sheets and mp4s: clips are readable, no broken limbs, no foot sliding in `idle`/`happy`/`dance`.
- `python3 tool/room_tex_means.py` ran after the swap (look.json fresh), and the macpro lane is deleted.

## 5-1. 자체 검증
```
python3 tool/room_seam_check.py (new) assets/room/scoop/{piyo,mongsil,popo,nuri,moa}.glb     # expect 0 each, exit 0
python3 -c "import json;m=json.load(open('assets/room/scoop/manifest.json'));print({k:(m[k]['out_bytes'],m[k]['tris'],m[k].get('clips')) for k in ['piyo','mongsil','popo','nuri','moa']})"
node runtime_src/scoop_sky/reactions.selftest.mjs 2>&1 | tail -5                              # expect the look block to pass (fresh look.json)
```
- Open every jpg yourself (view the image) before you report.

## 6. 금지
- Edit or create only these files:
  - `tool/room_cast_build.py` (new), `pipeline/room-cast.sh` (new), `tool/room_seam_check.py` (new);
  - `assets/room/scoop/{piyo,mongsil,popo,nuri,moa}.glb`;
  - the five ids' entries in `assets/room/scoop/manifest.json`;
  - `assets/room/scoop/look.json`, only by running tool/room_tex_means.py;
  - `reviews/20261025/room/cast-rig/**` (new).
- Main owns `runtime_src/scoop_sky/**`. Workers w4-env and w5-set own `assets/room/scoop/set/**`.
- Read-only: `out/shorts/**`, `docs/shorts/**`, `reader/**`, `build/room-meshy/**`.
- No Meshy or any paid/generation API. Never read `~/.config/meshy/` or any key file. No commits, no pushes.
- On macpro, touch only `~/sg-lanes/room-cast/`. Never touch the running blender-mcp processes or the user's open Blender; no git there.
- Do not use opi128 (two other lanes run there).

## 7. 보고 형식 (final message, 15-30 lines)
Headings in this order:
- `## Root cause`
- `## Prevention`
- `## Symptom fix`: files, plus a per-id table of tris/bytes/clips/seams before→after.
- `## Verification`
- `## Unverified`
- `## Assumptions`
- `## Rejected alternatives`
- `## Downstream`: what main must wire (clip names per id, any rig notes).
- `## Questions`: only if any.

Last line: REPORT-DONE.
