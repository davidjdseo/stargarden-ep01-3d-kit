#!/usr/bin/env bash
# Scoop Sky room environment lane: build env.glb on opi128 (Blender 5.0.1, Cycles CPU 3 threads), bring it back.
#   bash pipeline/room-env.sh                 full: build + calibrate + export + re-import check + renders
#   bash pipeline/room-env.sh --renders-only  re-import the current env.glb and re-render the sheets
#   ROOM_ENV_QUICK=1 bash pipeline/room-env.sh   half-res drafts (look iteration)
# Copies only its own files to the board (same absolute paths) and deletes exactly those afterwards.
set -euo pipefail

REPO=/home/orangepi/stargarden-p1-continuation
BOARD=${ROOM_ENV_BOARD:-opi128}
LANE=/tmp/sg-room-env-lane
PLATE_DIR=out/shorts/ep01/anchors/world-theme-s1/A-scoop-sky
PLATES=(plate-v4.png)
SCRIPT=tool/room_env_build.py
GLB=assets/room/scoop/set/env.glb
JSON=assets/room/scoop/set/env.json
RDIR=reviews/20261025/room/env
MODE=full
[[ "${1:-}" == "--renders-only" ]] && MODE=renders
QUICK=${ROOM_ENV_QUICK:-0}
THREADS=3
SEED=20261025

cd "$REPO"
avail=$(ssh "$BOARD" "df -BG --output=avail / | tail -1 | tr -dc 0-9")
echo "[room-env] $BOARD free ${avail}G"
if (( avail < 10 )); then echo "[room-env] abort: under 10 GB free on $BOARD" >&2; exit 1; fi
ssh "$BOARD" 'free -g | sed -n 2p; pgrep -fa "blender" | grep -v pgrep | head -3 || true'

# remember which directories already existed on the board so cleanup only removes what we created
DIRS=(tool assets assets/room assets/room/scoop assets/room/scoop/set reviews reviews/20261025 reviews/20261025/room "$PLATE_DIR")
created=$(ssh "$BOARD" "cd $REPO; for d in ${DIRS[*]}; do [ -d \"\$d\" ] || echo \"\$d\"; done")
existing_plates=$(ssh "$BOARD" "cd $REPO; for p in ${PLATES[*]}; do [ -e $PLATE_DIR/\$p ] && echo \$p; done; true")
existing_script=$(ssh "$BOARD" "cd $REPO; [ -e $SCRIPT ] && echo yes || true")

cleanup() {
  local rm_list=("$LANE" "$REPO/$RDIR" "$REPO/$GLB" "$REPO/$JSON")
  [[ -z "$existing_script" ]] && rm_list+=("$REPO/$SCRIPT")
  for p in "${PLATES[@]}"; do
    grep -qx "$p" <<<"$existing_plates" || rm_list+=("$REPO/$PLATE_DIR/$p")
  done
  ssh "$BOARD" "rm -rf ${rm_list[*]}" || true
  echo "[room-env] deleted on $BOARD:"; printf '  %s\n' "${rm_list[@]}"
  # remove directories we created, deepest first, only if empty
  local rev
  rev=$(printf '%s\n' $created | awk '{print length, $0}' | sort -rn | cut -d' ' -f2-)
  for d in $rev; do
    ssh "$BOARD" "rmdir $REPO/$d 2>/dev/null && echo '  (rmdir) $REPO/$d'" || true
  done
}
trap cleanup EXIT

ssh "$BOARD" "mkdir -p $LANE $REPO/tool $REPO/$PLATE_DIR $REPO/assets/room/scoop/set $REPO/$RDIR"
rsync -a "$SCRIPT" "$BOARD:$REPO/$SCRIPT"
for p in "${PLATES[@]}"; do rsync -a "$PLATE_DIR/$p" "$BOARD:$REPO/$PLATE_DIR/$p"; done

job() {  # $1 mode
  printf '{"repo":"%s","lane":"%s","mode":"%s","out_glb":"%s","out_json":"%s","render_dir":"%s","seed":%d,"threads":%d,"samples":%d,"calib_samples":8,"calib_iters":2,"quick":%s}\n' \
    "$REPO" "$LANE" "$1" "$REPO/$GLB" "$REPO/$JSON" "$REPO/$RDIR" "$SEED" "$THREADS" "$([[ $QUICK == 1 ]] && echo 12 || echo 32)" \
    "$([[ $QUICK == 1 ]] && echo true || echo false)"
}
run_blender() {  # $1 mode
  job "$1" | ssh "$BOARD" "cat > $LANE/job_$1.json"
  ssh "$BOARD" "cd $REPO && nice -n 5 /usr/bin/blender -b --factory-startup -t $THREADS -P $SCRIPT -- $LANE/job_$1.json 2>&1 | grep -E '^\[env|Error|Traceback|File \"|  |Exception' | grep -v '^  *$' | grep -v 'Fra:' ; exit \${PIPESTATUS[0]}"
}

if [[ $MODE == full ]]; then
  run_blender build
else
  rsync -a "$GLB" "$JSON" "$BOARD:$REPO/assets/room/scoop/set/"
fi
rc=0
run_blender check || rc=$?

mkdir -p "$(dirname "$GLB")" "$RDIR"
rsync -a "$BOARD:$REPO/$GLB" "$BOARD:$REPO/$JSON" "$(dirname "$GLB")/"
rsync -a "$BOARD:$REPO/$RDIR/" "$RDIR/"
echo "[room-env] back: $(ls -l "$GLB" | awk '{print $5}') bytes; renders: $(ls "$RDIR" | tr '\n' ' ')"
if (( rc != 0 )); then echo "[room-env] re-import check FAILED (rc $rc): see reimport_check.problems in $JSON" >&2; exit $rc; fi
