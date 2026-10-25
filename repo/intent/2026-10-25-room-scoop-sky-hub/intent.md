# Intent — Room = Scoop Sky 3D hub (seeded 2026-10-25 11:42 by the moa-shorts session)

## User's words (2026-10-25, verbatim core)
"룸 안에서 3D 캐릭터가 나와서 이렇게 돌아다니고 그 안에서 여러 가지 교육적 효과를 만드는 … 사실 이제 거기가 메인 통로야. … 수족관 형태로 돼 있는데 배경이 거기를 그냥 싹 다 리뉴얼 해가지고 지금 컨셉으로 바꿔줘. … 영상은 약간 홍보용 목적이고 중간중간에 1화, 2화, 3화, 4화를 그 공간 룸 안에서 아이들이 … 미션을 달성하고 그러면 영상이 풀리는 식 … 한 10분 남짓한 홍보용 영상을 유튜브나 틱톡으로 … 그 이상을 하려면 앱으로 … 메쉬 AI 이용해서 배경부터 싹 다 … 1화 컨셉이랑 똑같은 월드를 하나 만들고 … 지금 있는 캐릭터들 3D로 다 만들고 … 상호작용할 수 있게 … 꽃에 물을 주고 … 아이들이 생각보다 계속해서 누르거든. 누르고 반응하는 걸 되게 좋아해. 그러니까 그거를 메인 컨셉으로 … 그 공간을 진입점으로 해서 … 동화 연결해주고 영상도 연결해줘. 이거를 종합적으로 설계해 할 수 있는 오케스트레이션 할 수 있는 세션을 추가로 만들어줘."

## Goal
The Room (web/app room, today an aquarium-cafe theme) becomes the app's main entry: the EP01 Scoop Sky world rebuilt in 3D
(Meshy AI meshes + Blender cleanup), Moa and the friends as 3D characters walking in it, dense tap -> instant reaction
interactions (water the flowers, music box, music, the cream-puff clouds, the toy plane ...), English-word learning kept from
the existing room design, the storybook (bo-sky-island) and the EP01-04 videos opened from inside the room; episodes unlock
by completing room missions. Promo video (~10 min, YouTube/TikTok) -> app -> room. A comprehensive pre-reader language app.

## Owner
A separate orchestrator session (spawned 2026-10-25 11:42). The moa-shorts session (shorts EP01) and the bo-sky-island book session keep
their own files; the room session reads their assets (cast.json, EP01 sheets, world sheets, book, delivered videos) and never edits them.

## Done looks like (first milestone)
- Room design doc: core tap-reaction loop, mission -> unlock ladder, how book and videos are entered, which existing room
  education systems are kept (read docs/KIDS_ROOM_HUB_PLAN.md and the room code first).
- A Scoop Sky 3D room live on the room link (sg-room unit) with Moa walking and >= 5 tap reactions, checked on a phone-size
  capture with sound off; Meshy credit spend reported against a user-approved cap.

## Log
- 2026-10-25 12:28 Discovery and design done (docs/room-hub/DESIGN.md). Meshy: 14 props generating (cap 950); cast check PASS; W1 runtime skeleton and W2 Blender GLB lane running; host.mjs gained the ?room=scoop switch.

## Direction change 2026-10-25 16:19 (user, room-hub session) — plate-faithful, bigger world
User (verbatim core): "원화 보고 그 원래 시안 … 배경 플레이트 보고 분리할 거 싹 분리하고 다시 생성해가지고 텍스처 굽고 텍스처 입혀주고 거의 그거랑 똑같이 계속해서 작업해줘. 일단 배경도 별로고 구름도 별로고 별로인 것들 최대한 똑같이 … 그리고 사이즈도 좀 더 크게 세계관 확장해주고." + "코덱스 아스트라 미디움 서브 에이전트 … 블렌더 작업 … 지시서 상세하게 하고 너랑 좀 작업을 나눠가지고".
- Look truth: the approved world plates `out/shorts/ep01/anchors/world-theme-s1/A-scoop-sky/plate-v4.png` (hill garden: rolling fluffy lawn, cookie path, wafer fence, berry bushes, cotton-candy trees, soft-serve clouds, ice-cream dome hills on the horizon) + `sky-v1.png`, `reverse-r4-v1.png`, `r6-flowerbed-v1.png`, `r7-side-v1.png`.
- The floating whipped-cream disc + white sphere clouds are retired; the room becomes the plate's hill garden in real 3D, extending to a horizon (360°), so the world reads big.
- Split: Codex Astra 6 medium workers build every Blender asset on opi128 (A: env = sky dome, soft-serve clouds, far ice-cream hills, big lawn terrain; B: set pieces = cotton-candy trees, berry bushes, wafer fence, cookie stones), baked textures/vertex colours. Main: runtime loading, camera toward the plate's eye level, placement gates, capture, side-by-side judging vs plate-v4.
- Done looks like: a room capture at 844x390 and 1280x800 that a viewer would take for the plate's world (same sky, clouds, hills, lawn, trees), with every tappable still passing the framing gates.

## Interaction + cast polish 2026-10-25 16:36 (user)
"삐요 … 얼굴에 가운데 세로선 … 매끈하게 … 플러그인 … 리토폴로지 … UV … 바닥 텍스처와 배경 텍스처 … 넓게 … 월드를 구축 … 애니메이션 다 돼야 되고 서로 상호작용 … 책 읽기 … 음악놀이 … 공놀이, 숫자놀이".
- Piyo line: measured UV island seams down the face centre (180 seam groups front-centre on piyo.glb; also Moa 88, popo 81, mongsil 56, nuri 25) + three.js normal mapping without tangents; Blender renders hide it. Fix lane w6-cast (retopo, UV with seams off the face, bake, rig, clips).
- Stations design: docs/room-hub/DESIGN.md §10. Done = every station plays end to end on a phone capture.
