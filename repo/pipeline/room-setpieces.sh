#!/usr/bin/env bash
# Scoop Sky set pieces lane (2026-10-25, w5-set). Blender on opi128 builds textured GLBs from tool/room_setpieces_build.py.
#   bash pipeline/room-setpieces.sh [piece ...] [--renders-only]     default: all 10 pieces + lineup
# Colours: tool/room_setpieces_build.py SWATCH_BOXES (plate / sheet pixel boxes) is the single source; measured here with PIL,
# passed to Blender in job.json, written to assets/room/scoop/set/pieces.json `swatches`, and re-measured on the shipped
# WebP albedo per part (`swatch_table`, sRGB distance <= 12).
# Board: the script is rsync'd at its same absolute path (deleted again if this run created it), everything else lives in
# /tmp/sg-setpieces-lane/run-*; nothing else on the board is touched. Blender: nice -n 5, 3 Cycles threads.
set -euo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd)
HOST=${ROOM_SET_HOST:-opi128}
SSH="ssh -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=30"
SCRIPT=$REPO/tool/room_setpieces_build.py
ALL=(tree-pink tree-mint berry-bush berry-bush-s daisy grass-tuft mint-bush fence fence-post cookie-stone)
PIECES=(); RENDERS_ONLY=0
for a in "$@"; do
  case $a in --renders-only) RENDERS_ONLY=1 ;; -*) echo "room-setpieces: unknown flag $a" >&2; exit 2 ;; *) PIECES+=("$a") ;; esac
done
[ ${#PIECES[@]} -gt 0 ] || PIECES=("${ALL[@]}")
for p in "${PIECES[@]}"; do [[ " ${ALL[*]} " == *" $p "* ]] || { echo "room-setpieces: unknown piece $p" >&2; exit 2; }; done
ROOT=/tmp/sg-setpieces-lane
LANE=$ROOT/run-$(date +%Y%m%d-%H%M%S)-$$
SETDIR=$REPO/assets/room/scoop/set
VIEWS=$REPO/reviews/20261025/room/set-views
mkdir -p "$LANE/out/views" "$SETDIR" "$VIEWS"

python3 "$SCRIPT" --swatches > "$LANE/swatches.json"
python3 - "$LANE" "$SETDIR" "$RENDERS_ONLY" "${PIECES[@]}" <<'PY'
import json, shutil, sys
from pathlib import Path
lane, setdir, ro, pieces = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3] == '1', sys.argv[4:]
ALL = ['tree-pink', 'tree-mint', 'berry-bush', 'berry-bush-s', 'daisy', 'grass-tuft', 'mint-bush', 'fence', 'fence-post', 'cookie-stone']
# GLBs this run does not build but the check / lineup reads: copy the shipped ones into the lane
pre = []
for p in ALL:
    if (ro or p not in pieces) and (setdir / f'{p}.glb').exists():
        shutil.copyfile(setdir / f'{p}.glb', lane / f'out/{p}.glb'); pre.append(p)
have = set(pre) | (set() if ro else set(pieces))
job = {'pieces': pieces, 'seed': 20261025, 'threads': 3, 'out_dir': str(lane / 'out'), 'views_dir': str(lane / 'out/views'),
       'swatches': json.loads((lane / 'swatches.json').read_text()), 'render': True, 'lineup': have >= set(ALL),
       'ao_samples': 32, 'view_samples': 24, 'lineup_samples': 48, 'webp_q': 88}
(lane / 'job.json').write_text(json.dumps(job, indent=1))
print('room-setpieces: pieces', pieces, '| renders-only' if ro else '| build', '| lineup', job['lineup'], '| pre-shipped', pre)
PY

FREE=$($SSH "$HOST" "df -Pk / | awk 'NR==2{printf \"%d\", \$4/1048576}'")
[ "$FREE" -ge 10 ] || { echo "room-setpieces: $HOST has only ${FREE} GB free (< 10) - abort" >&2; exit 1; }
echo "room-setpieces: $HOST ${FREE} GB free"
SCRIPT_CREATED=0
$SSH -n "$HOST" "test -e '$SCRIPT'" || SCRIPT_CREATED=1
cleanup_board() {
  local del="$LANE"
  [ "$SCRIPT_CREATED" = 1 ] && del="$del $SCRIPT"
  $SSH -n "$HOST" "rm -rf '$LANE'; [ '$SCRIPT_CREATED' = 1 ] && rm -f '$SCRIPT'; rmdir '$ROOT' 2>/dev/null; true" || true
  echo "room-setpieces: deleted on $HOST: $del"
}
trap cleanup_board EXIT
$SSH -n "$HOST" "mkdir -p '$(dirname "$SCRIPT")' '$LANE'"
rsync -a -e "$SSH" "$SCRIPT" "$HOST:$SCRIPT"
rsync -a -e "$SSH" "$LANE/" "$HOST:$LANE/"
BL="cd '$LANE' && nice -n 5 blender -b --factory-startup -P '$SCRIPT' -- '$LANE/job.json'"
if [ "$RENDERS_ONLY" = 0 ]; then
  echo "room-setpieces: build on $HOST ..."
  $SSH -n "$HOST" "$BL > '$LANE/out/build.log' 2>&1; grep -E '^SETPIECE|Error|Traceback' '$LANE/out/build.log' | cut -c1-300 | tail -40" || true
fi
echo "room-setpieces: re-import checks + renders on $HOST ..."
$SSH -n "$HOST" "$BL --check > '$LANE/out/check.log' 2>&1; grep -E '^SETCHECK|^SETLINEUP|Error|Traceback' '$LANE/out/check.log' | cut -c1-240 | tail -40" || true
rsync -a -e "$SSH" "$HOST:$LANE/out/" "$LANE/out/"
cleanup_board; trap - EXIT
echo "room-setpieces: board after cleanup:"; $SSH -n "$HOST" "ls -d '$ROOT' '$SCRIPT' 2>&1 || true"

python3 - "$REPO" "$LANE" "$RENDERS_ONLY" "${PIECES[@]}" <<'PY'
import hashlib, json, math, shutil, struct, sys, io
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageStat
repo, lane, ro, pieces = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3] == '1', sys.argv[4:]
out, setdir, views = lane / 'out', repo / 'assets/room/scoop/set', repo / 'reviews/20261025/room/set-views'
import subprocess, types
meta = json.loads(subprocess.check_output([sys.executable, str(repo / 'tool/room_setpieces_build.py'), '--meta']))
kit = types.SimpleNamespace(PIECES=meta['pieces'], PARTS=meta['parts'], ORDER=meta['order'], EXPOSED_AO=meta['exposed_ao'])
PIECES, PARTS = kit.PIECES, kit.PARTS
sw = json.loads((lane / 'swatches.json').read_text())
build = json.loads((out / 'build.json').read_text()) if (out / 'build.json').exists() else {}
check = json.loads((out / 'check.json').read_text()) if (out / 'check.json').exists() else {}
pj = setdir / 'pieces.json'
man = json.loads(pj.read_text()) if pj.exists() else {}
man['_about'] = ('Scoop Sky set pieces (tool/room_setpieces_build.py, pipeline/room-setpieces.sh). glTF Y up, metres, pivot = base centre '
                 '(min y = 0, bbox centred on x/z), front = +Z. Colours come only from `swatches` (pixel boxes on the plate / sheets); '
                 'swatch_table re-measures the shipped albedo per part on lit-side texels (baked AO >= %.2f).' % kit.EXPOSED_AO)
man['seed'] = 20261025
man['swatches'] = sw

def glb_parts(path):
    b = path.read_bytes()
    n = struct.unpack('<I', b[12:16])[0]
    js = json.loads(b[20:20 + n])
    off = 20 + n
    bn = struct.unpack('<I', b[off:off + 4])[0]
    binc = b[off + 8: off + 8 + bn]
    imgs = []
    for i, im in enumerate(js.get('images', [])):
        bv = js['bufferViews'][im['bufferView']]
        data = binc[bv.get('byteOffset', 0): bv.get('byteOffset', 0) + bv['byteLength']]
        imgs.append((im.get('name', f'img{i}'), im.get('mimeType'), data))
    def tex_img(t):
        tx = js['textures'][t['index']]
        return tx.get('extensions', {}).get('EXT_texture_webp', {}).get('source', tx.get('source'))
    mat = js['materials'][0]
    alb = tex_img(mat['pbrMetallicRoughness']['baseColorTexture'])
    return js, imgs, alb

fails = []
P = 384
def panel(path, bg=(255, 255, 255)):
    im = Image.open(path).convert('RGBA'); im.thumbnail((P, P))
    t = Image.new('RGB', (P, P), bg); t.paste(im, ((P - im.width) // 2, (P - im.height) // 2), im); return t

for pid in pieces:
    if not ro:
        b = build.get(pid, {})
        if 'error' in b or not (out / f'{pid}.glb').exists():
            print(f'room-setpieces: {pid}: BUILD FAIL {b.get("error")}'); fails.append(pid); continue
        shutil.copyfile(out / f'{pid}.glb', setdir / f'{pid}.glb')
    c = check.get(pid, {})
    if 'error' in c or not c:
        print(f'room-setpieces: {pid}: CHECK FAIL {c.get("error")}'); fails.append(pid); continue
    glb = setdir / f'{pid}.glb'
    js, imgs, alb_i = glb_parts(glb)
    spec_ = PIECES[pid]
    e = man.get(pid, {})
    row = {'glb': str(glb.relative_to(repo)), 'bytes': glb.stat().st_size, 'sha256': hashlib.sha256(glb.read_bytes()).hexdigest(),
           'triangles': c['tris'], 'textures': [], 'bbox': c['bbox'], 'height': c['height'], 'size_target': list(spec_['size']),
           'pivot': 'base centre: min y = 0, bbox centre x/z = 0' + (' ; tiles end to end along x every 1.000 m (x = -0.5 .. 0.5)' if pid == 'fence' else ''),
           'front': '+Z', 'materials': c['materials'], 'meshes': c['meshes'], 'ref': {'src': spec_['ref'][0], 'box': list(spec_['ref'][1])},
           'budget': {'tris': spec_['budget'][0], 'bytes': spec_['budget'][1]}}
    for name, mime, data in imgs:
        im = Image.open(io.BytesIO(data))
        row['textures'].append({'name': name, 'mime': mime, 'px': list(im.size), 'bytes': len(data)})
    if not ro:
        alb = Image.open(io.BytesIO(imgs[alb_i][2])).convert('RGB')
        idm = Image.open(out / f'{pid}_id.png').convert('L')
        ao = Image.open(out / f'{pid}_ao.png').convert('L')
        exp = ao.point(lambda v: 255 if v >= round(kit.EXPOSED_AO * 255) else 0)
        table = []
        gains = build[pid].get('gains', {})
        for k, part in enumerate(PARTS):
            val = round((k + 1) * 255 / 32)
            m = idm.point(lambda v, val=val: 255 if abs(v - val) <= 1 else 0)
            if not m.getbbox():
                continue
            me = ImageChops.multiply(m, exp)
            use = me if me.getbbox() and ImageStat.Stat(me).sum[0] / 255 >= 50 else m
            mean = ImageStat.Stat(alb, use).mean
            mean_all = ImageStat.Stat(alb, m).mean
            s = sw[part]['srgb']
            d = math.dist(mean, s); da = math.dist(mean_all, s)
            table.append({'part': part, 'swatch': [round(v, 1) for v in s], 'texel_mean_lit': [round(v, 1) for v in mean], 'dist': round(d, 2),
                          'texel_mean_all': [round(v, 1) for v in mean_all], 'dist_all': round(da, 2),
                          'texels': int(ImageStat.Stat(m).sum[0] / 255), 'gain_to_pin': gains.get(part)})
        row['swatch_table'] = table
    else:
        row['swatch_table'] = e.get('swatch_table', [])
    ch = dict(c['checks'])
    ch['tris_budget'] = c['tris'] <= spec_['budget'][0]
    ch['bytes_budget'] = row['bytes'] <= spec_['budget'][1]
    ch['swatch_dist_12'] = all(r['dist'] <= 12 for r in row['swatch_table']) and bool(row['swatch_table'])
    row['checks'] = ch
    row['pass'] = all(ch.values())
    man[pid] = row
    # sheet: reference crop | front | right | back | left
    src, box = spec_['ref']
    ref = Image.open(repo / src).convert('RGB').crop(box); ref.thumbnail((P, P))
    rt = Image.new('RGB', (P, P), (255, 255, 255)); rt.paste(ref, ((P - ref.width) // 2, (P - ref.height) // 2))
    tiles = [rt] + [panel(out / 'views' / Path(c['views'][t]).name) for t in ('pz', 'px', 'nz', 'nx')]
    labels = [f'ref {Path(src).name} {list(box)}', 'front +Z', 'right +X', 'back -Z', 'left -X']
    sheet = Image.new('RGB', (P * 5, P + 26), (236, 236, 236)); d = ImageDraw.Draw(sheet)
    for i, (t, lab) in enumerate(zip(tiles, labels)):
        sheet.paste(t, (i * P, 26)); d.text((i * P + 6, 7), lab if i else lab, fill=(20, 20, 20))
    d.text((P + 120, 7), f'{pid}  {c["tris"]} tris  {row["bytes"] // 1024} KB  h={c["height"]:.3f}', fill=(20, 20, 20))
    sheet.save(views / f'{pid}.jpg', quality=88)
    worst = max([r['dist'] for r in row['swatch_table']] or [99])
    print(f'room-setpieces: {pid:13s} {"PASS" if row["pass"] else "FAIL"} tris={c["tris"]:6d} bytes={row["bytes"]:8d} h={c["height"]:.4f} '
          f'tex={[t["px"][0] for t in row["textures"]]} worst_swatch={worst:.1f} ' + ' '.join(k for k, v in ch.items() if not v))
    for r in row['swatch_table']:
        print(f'    {r["part"]:14s} swatch={r["swatch"]} lit={r["texel_mean_lit"]} d={r["dist"]:5.2f} all={r["texel_mean_all"]} d_all={r["dist_all"]:5.2f} gain={r["gain_to_pin"]}')
    if not row['pass']:
        fails.append(pid)
if (out / 'views/lineup.png').exists():
    Image.open(out / 'views/lineup.png').convert('RGB').save(views / 'lineup.jpg', quality=90)
    print('room-setpieces: lineup', (views / 'lineup.jpg').relative_to(repo))
ordered = {k: man[k] for k in ['_about', 'seed', 'swatches'] + [p for p in kit.ORDER if p in man]}
pj.write_text(json.dumps(ordered, indent=1) + '\n')
print('room-setpieces: wrote', pj.relative_to(repo), '| lane', lane)
sys.exit(1 if fails else 0)
PY
