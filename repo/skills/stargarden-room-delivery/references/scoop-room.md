# Scoop Sky 룸: 규칙·게이트·검증 예시

상위 문서: [../SKILL.md](../SKILL.md)의 「Scoop Sky 룸」 절. 2026-10-25 scoop_sky 룸 작업에서 나온 네 규칙의 근거다.

- 근본 원인: 룸 전달 절차가 Flutter·aquarium 시대에서 멈춰 있었고, 증류 단계가 새 룸 런타임의 게이트를 이 스킬에 연결하지 않았다. 같은 부류는 이번이 첫 번째다.
- 범위: 룸 런타임 공통 규칙이다. `scoop_sky`가 첫 사례이고, 다른 룸은 자기 selftest와 aspect 목록을 같은 방식으로 둔다.
- 룸 선택: `?room=scoop`이 rea-config `roomRuntime`보다 우선하고, 둘 다 없으면 aquarium이다(`web/app/host.mjs:33` ROOM_RUNTIMES, `:272`). 이 선택은 커밋 425a49bb에 들어갔다(main 확인, 2026-10-25).

## 1. 브라우저 프로브: delivered-look 또는 look-exempt

- 분류: 프로브 린트(pre-commit).
- 증상: pre-commit이 `pipeline/room-cap.cjs`를 막았다(`.goto(`에 `delivered-look` import가 없었다. 2026-10-25 측정).
- 직접 원인: 룸 호스트 링크를 여는 새 프로브가 `p.goto(url)`만 썼다. 이 프로브는 책 리더 페이지가 아니어서 LOOK 질의 대상이 아니다.
- 지시 연쇄 원인: 이 스킬이 프로브 규칙을 말하지 않아, 워커는 훅 실패 메시지에서 처음 알았다.
- 규칙: `pipeline/*.cjs`·`*.mjs`의 `.goto(` 프로브는 `delivered-look.cjs`를 require 또는 import하거나, 같은 줄이나 바로 윗줄에 `// look-exempt: <사유>`를 둔다. 사유에는 무엇을 캡처하는지 쓴다(예: `pipeline/room-cap.cjs:26`).
- 게이트: `pipeline/git-hooks/pre-commit:17`은 `pipeline/*.cjs|*.mjs` 또는 `probe-look-lint.py`가 스테이징되면 `pipeline/probe-look-lint.py`를 돌린다. 린트는 최상위 추적 파일을 인덱스 바이트(`git show :<path>`)로 검사한다(`probe-look-lint.py:79-81`).
- 검증 예시: `python3 -I pipeline/probe-look-lint.py --selftest` → `probe-look-lint selftest PASS (...)`, 종료 0. 2026-10-25 이 워커에서 실행해 확인했다.
- 근거: `pipeline/probe-look-lint.py:23-46`(검사), `:49-66`(셀프테스트), `pipeline/room-cap.cjs:26-27`.

## 2. 커밋: 공유 인덱스에 스테이징하지 않는다

- 분류: 공유 상태 경쟁(모든 세션이 같은 `.git/index`를 쓴다).
- 증상·근거: RCA 74e2b94b. `pipeline/git-private.sh` 머리말(1-14행)에 적힌 사고다. 느린 pre-commit이 도는 동안 다른 세션의 `git commit`이 워커 파일 9개를 자기 커밋에 쓸어 넣었다.
- 직접 원인: 공유 인덱스에 `git add`를 한 뒤 훅이 몇 분 돌았다.
- 지시 연쇄 원인: RCA가 지목한 옛 절차(`git add` → pre-commit → `git reset`)는 더 이상 없다(main 확인, 2026-10-25). 이 스킬은 공유 인덱스 위험을 말하지 않았다.
- 규칙: 커밋은 `git-private.sh`로만 한다.
  - 파일 단위(파일 전체가 내 변경일 때): `bash pipeline/git-private.sh commit -F <msg.txt> <paths...>`(또는 `-m <msg>`). 임시 인덱스에 `HEAD + 내 경로`를 만들고, 추적 중인 pre-commit을 그 인덱스에 돌린 뒤, 브랜치를 compare-and-swap으로 옮긴다. HEAD가 그사이 움직이면 새 HEAD에서 최대 3번 다시 만든다. 움직인 커밋이 내 경로를 건드렸으면 종료 2다.
  - 검사만: `bash pipeline/git-private.sh check <paths...>` → `PRIVATE-CHECK PASS rc=0`(커밋하지 않는다).
  - 같은 파일을 다른 세션도 고쳤으면(hunk 단위): 아래 배관 절차를 쓴다. 425a49bb가 이 방식으로 만들어졌다(main 확인).
    1. `HEAD`의 파일 사본에 내 hunk만 적용하고 `git hash-object -w <사본>`으로 blob을 만든다.
    2. 임시 인덱스 `GIT_INDEX_FILE=<tmp>`에서 `git read-tree HEAD`, 이어서 `git update-index --cacheinfo 100644,<blob>,<path>`(원래 모드를 쓴다).
    3. 저장소 루트에서 `GIT_INDEX_FILE=<tmp> bash pipeline/git-hooks/pre-commit`을 돌린 뒤 `GIT_INDEX_FILE=<tmp> git write-tree`, `git commit-tree <tree> -p <base> -F <msg.txt>`.
    4. `git update-ref refs/heads/<branch> <new> <base>`(compare-and-swap).
    5. `git reset -q -- <path>`(공유 인덱스에서 내 경로만 맞춘다).
- 게이트: `bash pipeline/git-private.sh --selftest`(임시 저장소에서 경쟁 상황을 재현한다). 2026-10-25 이 워커는 git 금지 때문에 실행하지 않았다(미검증).
- 근거: `pipeline/git-private.sh:1-14`(머리말·RCA), `:50-56`(check), `:61`(commit), `:106`(selftest), `:202-204`(CLI).

## 3. 탭 반응: `room-cap.sh`의 TAP_IDS (Mac GPU)

- 분류: 캡처 절차 누락(룸 테스트 훅을 쓰는 절차가 스킬에 없었다).
- 증상: 탭 반응을 확인할 명령이 없어 워커가 실화면 탭을 다시 찾아야 했다.
- 직접 원인: 탭 확인 절차가 스킬에 없었다.
- 지시 연쇄 원인: 스킬은 보드 Chromium이 SwiftShader라 탭 재현에 쓰지 않는다고만 말하고 Mac GPU 확인을 언급했지만(「기본」 절 보드 항목), 실행 절차(`room-cap.sh`)를 연결하지 않았다.
- 규칙: 탭 반응은 `pipeline/room-cap.sh`(호스트 `mac2`, ssh, `GPU=1`)로 확인한다. `TAP_IDS='id;id'`는 룸 iframe에서 `window.__scoop.tap(id)`를 id마다 한 번 부르고, id마다 샷 한 장을 찍는다(`pipeline/room-cap.cjs:37-43`). 좌표 탭은 `TAP_MS`(기본 1200), id 탭 간격은 `TAPID_MS`(기본 350)다(`room-cap.cjs:34`, `:41`).
- 전달: `BOOT_MS`·`TAP_IDS`·`TAP_MS`·`TAPID_MS`는 `room-cap.sh:16`의 FWD 목록 하나로 만들어져 원격 `env`에 전달된다(`:23`). TAPID_MS: forwarded by room-cap.sh (fixed 2026-10-25).
- 검증 예시(실캡처):
  ```
  ROOM_URL='<링크>/app/?room=scoop' BOOT_MS=15000 TAP_IDS='piyo;lemon-can' TAPID_MS=500 bash pipeline/room-cap.sh <이름> 844x390,1280x800 ""
  ```
  결과는 `reviews/<yyyymmdd>/room/<이름>/`에 온다(`log.json`과 `shot-<WxH>-<n>[-<id>].png`). `room-cap.sh`는 시작 전에 링크가 HTTP 200인지 먼저 본다(`room-cap.sh:12`).
- `log.json`이 보여야 하는 것:
  - 요약 항목(`errs` 키가 있는 것)마다 `errs`가 `[]`다(페이지 오류·HTTP 4xx·5xx 없음).
  - `scoop.missing`이 `[]`다(GLB 로드 실패 id 없음, `runtime_src/scoop_sky/main.mjs:336,344`). `scoop.ready`는 true다.
  - tap 항목(`tapId` 키)마다 `ok`가 `"ok"`다.
  - `shots` = 1 + TAP_IDS 개수다(좌표 탭이 없을 때).
  검사 코드(stdin으로 읽는다, 종료 0이면 통과):
  ```
  python3 -I -c 'import json,sys
  L=json.load(sys.stdin)
  S=[e for e in L if "errs" in e]
  T=[e for e in L if "tapId" in e]
  sc=lambda e: e.get("scoop") or {}
  bad=[(e["vp"],e["errs"]) for e in S if e["errs"]]
  miss=[(e["vp"],sc(e).get("missing")) for e in S if sc(e).get("missing")!=[] or not sc(e).get("ready")]
  tapf=[(t["vp"],t["tapId"],t["ok"]) for t in T if t["ok"]!="ok"]
  shot=[(e["vp"],e["shots"]) for e in S if e["shots"]!=1+sum(1 for t in T if t["vp"]==e["vp"])]
  print("errs",bad,"missing/notready",miss,"tap-fail",tapf,"shots",shot)
  sys.exit(1 if bad or miss or tapf or shot else 0)' < reviews/<yyyymmdd>/room/<이름>/log.json
  ```
- 샷 크기: 촬영본은 기기 픽셀 비율 2배로 저장된다(844x390 → 1688x780, 1280x800 → 2560x1600). 비교 이미지·시트는 원본 전체를 비율대로 줄여 만들고, CSS 크기(390 등)로 자르지 않는다. 2026-10-25 실제 사례: 1688x780 원본을 1688x390으로 자른 비교 이미지에서 "위쪽만 보이는 구도"를 결함으로 오판했다. 원본 샷은 정상이었다.
- 근거: `pipeline/room-cap.sh:15-23`, `pipeline/room-cap.cjs:34-45`, `runtime_src/scoop_sky/main.mjs:297`(`__scoop` 형태), `:336`·`:344`(missing), `:388`(ready).
- 검증 상태: 이 워커는 Mac 실캡처를 돌리지 않았다. 위 검사 코드는 합성 JSON의 통과·실패 두 경우로만 확인했다. 전달 목록은 원격 없이 같은 quoting을 로컬에서 흉내 내 확인했다.

## 4. 룸 배치: 투영 게이트를 기본으로 둔다

- 분류: 배치 검사 누락(배치를 눈으로만 맞췄다).
- 증상: v1–v3 배치가 게이트 이전에 실패했다. v3는 게이트에서 17개 문제가 났다(가림 53%, 가장자리 밖 소품 등, `runtime_src/scoop_sky/props.json` 메모 30행).
- 직접 원인: 배치를 바꿔도 점유율·가림·여백을 재는 검사가 없었다.
- 지시 연쇄 원인: 스킬이 투영 게이트와 selftest 이름을 말하지 않아, 다음 세션은 확인할 명령을 몰랐다.
- 규칙: `props.json`·`layout.mjs`·카메라를 바꾸면 캡처 전에 `node runtime_src/scoop_sky/reactions.selftest.mjs`가 `all PASS`로 끝나고 종료 0이어야 한다.
- 게이트 내용:
  - 최소 점유율: `props.json`의 `camera.min_frame_frac`(소품 0.12, 친구 0.14, Moa 0.16)은 `min_frame_frac.aspect`인 844x390 하나에서만 검사한다. 하늘 소품은 뺀다(`reactions.selftest.mjs:84-95`).
  - 가장자리 여백 4%(`layout.mjs:48` EDGE_MARGIN_NDC = 0.08 NDC)와 가림 20% 이하(`layout.mjs:50` MAX_COVER = 0.2)는 844x390과 1280x800 모두에서 검사한다(`reactions.selftest.mjs:101-104`, 계산은 `layout.mjs:71` framingProblems).
  - 물체 사이 간격 0.3 m 이상(`layout.mjs:2` MIN_GAP_M).
- 일반화: 새 룸 런타임은 자기 selftest를 두고 같은 세 게이트를 쓴다. aspect 목록만 바꾼다.
- 검증 예시: `node runtime_src/scoop_sky/reactions.selftest.mjs; echo rc=$?` → 마지막 줄 `all PASS`, `rc=0`. 2026-10-25 이 워커에서 실행해 확인했다.

## 5. GLB 색: 조명 보정 하나, 판정은 원화 대조 시트 (2026-10-25)

- 분류: 색 기준이 두 곳에 있음(저장된 측정값과 실제 GLB) + 물체별 손 튜닝.
- 증상: v7에서 cream-puff가 원화(옅은 분홍 크림)와 달리 어두운 라일락으로 나왔다. 실캡처를 재 보니 크림 설정이 없는 GLB는 모두 원화보다 15–40% 어둡고 채도가 높았다.
- 직접 원인: 조명이 정면에서 텍스처를 선형 0.63배로 그렸다(`shade.mjs` 추정, 반구광+주광 합 ≈ 2.0 < π). cream-cloud만 발광 손 튜닝을 받았고, 그 게이트는 리텍스처 전 텍스처 평균(저장값)으로 통과하고 있었다(실제 GLB로 재면 오차 10.9 > 8).
- 지시 연쇄 원인: 색 게이트가 크림 소품 하나만 보고 숫자를 손으로 적어 두게 했다. 새 GLB를 넣는 절차에 색 확인이 없었다.
- 규칙:
  - 모든 GLB(소품·친구·Moa)는 `props.json look`의 조명 보정 하나만 받는다. 기본색 계수는 `shade.mjs lightNeutralMult`(π/조도, lights 블록에서 계산)이고, 여기에 Neutral 톤맵이 빼는 0.04만큼 흰 발광을 더한다. 물체마다 색을 손으로 맞추지 않는다.
  - 원화 평균에 채널별로 맞추는 보정은 쓰지 않는다. 텍스처 아틀라스와 정면 원화는 면적 비율이 달라서 v8에서 꽃과 비행기가 분홍으로 변했다.
  - `assets/room/scoop/look.json`은 `tool/room_tex_means.py`만 쓴다(`pipeline/room-glb.sh`가 GLB를 쓴 뒤 자동 실행). selftest는 GLB sha256으로 오래된 값을 막고, 텍스처-원화 거리 40 초과는 리텍스처 후보로 INFO에 적는다.
  - 색 판정은 평균이 아니라 원화 대조 시트로 한다: `python3 tool/room_look_sheet.py <이전캡처> <새캡처> <out.jpg>` (원화 | 이전 | 새).
- 일반화: 새 룸·새 GLB도 같은 조명 보정 하나를 쓴다. 조명 블록을 바꾸면 보정이 따라가므로 손댈 숫자가 없다. 리텍스처 후보(2026-10-25: berry-flower 55, nuri 45, sky-plane 40, piyo 원화보다 주황)는 원화 대조 시트로 확인한 뒤 Meshy retex를 정한다.
- 검증 예시: `scoop-v9-look/sheet-vs-room.jpg`(17개 모두 v7보다 원화에 가까움), selftest `all PASS`.

## 6. 보이는 면마다 그림 출처를 적는다 (2026-10-25)

- 분류: 화면에 보이는 면이 승인된 원화가 아니라 "임시 절차 생성"으로 남음.
- 증상: 하늘, 구름, 언덕, 바닥이 원화(`plate-v4.png`)와 달랐다(사용자: "배경도 별로고 구름도 별로고").
- 직접 원인: world.mjs의 원반, 원뿔, 구 구름이 코드 색으로만 칠해져 있었고 원화에서 뽑은 색이 없었다.
- 지시 연쇄 원인: 룸 지시서와 게이트가 GLB 소품의 색만 원화와 대조했다. 환경은 "procedural stand-in"으로 허용됐고, 무엇을 원화에서 가져오는지 묻는 단계가 없었다.
- 규칙: 보이는 모든 면(env 층, 세트 소품, GLB)은 `env.json`/`pieces.json`의 `swatches`(원화 좌표에서 잰 sRGB)나 `bake_table`에 그림 출처를 적는다. 출처가 없는 면은 넣지 않는다. 원화가 아닌 세계(룸, 쇼츠 세계)의 지시서는 `- ToneLock: <plate>`를 쓰고 같은 파일을 `- IMG:`로 붙인다(brief-lint 검사).
- 일반화: 새 룸이나 새 세계도 먼저 원화 플레이트를 층으로 나누고(하늘, 먼 산, 구름, 언덕, 덤불, 바닥), 층마다 견본 색과 거리를 정한 뒤에 만든다.

## 7. 캐릭터 얼굴 이음선: UV 섬 경계를 얼굴 밖으로 (2026-10-25)

- 분류: 내보낸 메쉬의 UV 이음선이 화면에서 중요한 부위(얼굴)를 지나감.
- 증상: 폰에서 삐요 얼굴 한가운데에 세로 음영선이 보였다. Blender Cycles 384px 렌더에는 안 보였다.
- 직접 원인: Meshy UV의 섬 경계가 얼굴 정중앙을 지났다(얼굴 앞 이음선 그룹 180개, UV 점프 0.7–0.88). three.js의 밉맵과 도함수 탄젠트 노멀맵이 그 경계를 선으로 그렸다.
- 지시 연쇄 원인: w2-glb 지시서가 Meshy UV와 노멀맵을 그대로 두게 했고, 판정을 실제 엔진이 아닌 작은 Blender 렌더로 했다.
- 규칙: 캐릭터 GLB는 얼굴 앞(정면 ±35°, 머리 높이)에 UV 이음선이 없어야 한다. 다시 UV를 펴고 기존 텍스처를 새 UV로 굽고, 노멀맵은 넣지 않는다. 검사는 `python3 tool/room_seam_check.py <glb>`로 한다. 판정은 three.js 실캡처 확대로 한다.
- 일반화: 쇼츠와 책의 3D 캐스트에도 같은 검사를 쓴다. 새 Meshy 출력은 이 검사를 통과하기 전에는 들이지 않는다.

## 8. 미검증

- Mac 실캡처와 실제 `log.json`: 2026-10-25 메인이 `scoop-v5-glb`(844x390·1280x800, 탭 6개)로 실행했고 위 검사 코드가 통과했다(errs [], missing [], 탭 모두 ok).
- `git-private.sh check`·`commit`·`--selftest`: git 금지 작업이라 실행하지 않았다.
- 425a49bb 배관 절차: main이 확인했다고 전달받았다. 이 워커는 git을 돌리지 않았다.
