#!/usr/bin/env python3
"""Room look review sheet (2026-10-25): per GLB prop/friend, its front sheet | crop from capture A | crop from capture B.

    python3 tool/room_look_sheet.py <capture_dir_A> <capture_dir_B> <out.jpg> [viewport=1280x800]

Crops come from the props.json screen boxes (layout.mjs, same maths as the gates); shots are DPR 2, boxes are fractions.
Judge colour here, against the art, not against a mean: atlas means mislead (scoop-v8-look turned flowers pink).
"""
import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parent.parent
a_dir, b_dir, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
vp = sys.argv[4] if len(sys.argv) > 4 else '1280x800'
js = ("import{readFileSync}from'node:fs';import{projector,screenBox,tappables}from'%s/runtime_src/scoop_sky/layout.mjs';"
      "const P=JSON.parse(readFileSync('%s/runtime_src/scoop_sky/props.json','utf8'));const[w,h]=[%s];const pr=projector(P.camera,w/h);const o={};"
      "for(const t of tappables(P)){const b=screenBox(pr,t.x,t.y0,t.z,t.h,t.hw,t.hd);o[t.id]=[(b.x0+1)/2,(1-b.y1)/2,(b.x1+1)/2,(1-b.y0)/2];}"
      "console.log(JSON.stringify(o));") % (REPO, REPO, vp.replace('x', ','))
boxes = json.loads(subprocess.run(['node', '--input-type=module', '-e', js], capture_output=True, text=True, check=True).stdout)
look = json.loads((REPO / 'assets/room/scoop/look.json').read_text())
glb = {p['id']: p.get('glb') for p in json.loads((REPO / 'runtime_src/scoop_sky/props.json').read_text())['props']}
A = Image.open(a_dir / f'shot-{vp}-0.png').convert('RGB')
B = Image.open(b_dir / f'shot-{vp}-0.png').convert('RGB')
W, H = A.size
ids = [i for i in boxes if glb.get(i) and look.get(glb[i], {}).get('sheet')]
T = 150
sheet = Image.new('RGB', (T * 9, T * ((len(ids) + 2) // 3)), 'white')
d = ImageDraw.Draw(sheet)
for k, i in enumerate(ids):
    x0, y0, x1, y1 = boxes[i]
    px, py = 0.15 * (x1 - x0), 0.15 * (y1 - y0)
    box = (int((x0 - px) * W), int((y0 - py) * H), int((x1 + px) * W), int((y1 + py) * H))
    art = Image.open(REPO / look[glb[i]]['sheet']).convert('RGBA')
    art = Image.alpha_composite(Image.new('RGBA', art.size, (255, 255, 255, 255)), art).convert('RGB')
    ox, oy = (k % 3) * T * 3, (k // 3) * T
    for j, t in enumerate((art, A.crop(box), B.crop(box))):
        t.thumbnail((T - 4, T - 4))
        sheet.paste(t, (ox + j * T + 2, oy + 2))
    d.text((ox + 4, oy + 2), i, fill='black')
sheet.save(out, quality=88)
print(f'room-look-sheet: {len(ids)} objects -> {out}')
