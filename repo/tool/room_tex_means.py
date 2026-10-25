#!/usr/bin/env python3
"""Room look source (2026-10-25): measure each room GLB's base-colour texture and the front sheet it was made from.

    python3 tool/room_tex_means.py           # every asset in assets/room/scoop/manifest.json -> assets/room/scoop/look.json

The sheet is the 'front' input of the object's last Meshy gen/retex call in docs/room-hub/meshy-ledger.jsonl (its sha256
must still match the file). Means are over opaque pixels (alpha > 127), sRGB 0..255. The runtime (main.mjs) calibrates
each GLB's material colour from these two numbers and props.json lights; reactions.selftest.mjs re-hashes every GLB so a
stale look.json fails the gate. pipeline/room-glb.sh runs this after it writes GLBs, so the numbers have one writer.
"""
import hashlib, io, json, struct, sys
from pathlib import Path
from PIL import Image, ImageChops, ImageStat

REPO = Path(__file__).resolve().parent.parent
MAN = REPO / 'assets/room/scoop/manifest.json'
OUT = REPO / 'assets/room/scoop/look.json'
LEDGER = REPO / 'docs/room-hub/meshy-ledger.jsonl'


def opaque_mean(im):
    im = im.convert('RGBA')
    mask = im.split()[3].point(lambda v: 255 if v > 127 else 0)
    return [round(v, 1) for v in ImageStat.Stat(im.convert('RGB'), mask).mean]


def opaque_share(im):
    return ImageStat.Stat(im.convert('RGBA').split()[3].point(lambda v: 1 if v > 127 else 0)).mean[0]


def keyed_mean(im, tol=24):
    """Sheet without alpha: key out the flat background (all four corners the same colour), mean of the rest."""
    im = im.convert('RGB')
    w, h = im.size
    cs = [im.getpixel(p) for p in ((1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2))]
    if max(max(abs(a - b) for a, b in zip(c, cs[0])) for c in cs) > 6:
        return None
    bg = Image.new('RGB', im.size, cs[0])
    diff = ImageChops.difference(im, bg).convert('L').point(lambda v: 255 if v > tol else 0)
    return [round(v, 1) for v in ImageStat.Stat(im, diff).mean]


def basecolor_image(glb):
    b = glb.read_bytes()
    n = struct.unpack_from('<I', b, 12)[0]
    js = json.loads(b[20:20 + n])
    off = 20 + n
    binc = b[off + 8:off + 8 + struct.unpack_from('<I', b, off)[0]]
    ti = js['materials'][0]['pbrMetallicRoughness']['baseColorTexture']['index']
    t = js['textures'][ti]
    src = t.get('source', t.get('extensions', {}).get('EXT_texture_webp', {}).get('source'))
    bv = js['bufferViews'][js['images'][src]['bufferView']]
    o = bv.get('byteOffset', 0)
    return Image.open(io.BytesIO(binc[o:o + bv['byteLength']])), len(js['materials'])


def front_sheets():
    out = {}
    for line in LEDGER.read_text().splitlines():
        r = json.loads(line)
        if r.get('stage') not in ('gen', 'retex'):
            continue
        fr = [i for i in r.get('inputs') or [] if isinstance(i, dict) and i.get('view') == 'front']
        if fr:
            out[r['object']] = fr[0]
    return out


def main():
    man = json.loads(MAN.read_text())
    sheets = front_sheets()
    look, bad = {}, []
    for cid, e in sorted(man.items()):
        glb = REPO / e['out']
        im, nmat = basecolor_image(glb)
        row = {'glb': e['out'], 'glb_sha256': hashlib.sha256(glb.read_bytes()).hexdigest(),
               'basecolor_mean_srgb': opaque_mean(im), 'materials': nmat}
        s = sheets.get(cid)
        if s:
            p = REPO / s['path']
            if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != s['sha256']:
                bad.append(f'{cid}: sheet {s["path"]} missing or changed since the Meshy call')
            elif opaque_share(Image.open(p)) <= 0.98:
                row.update(sheet=s['path'], sheet_sha256=s['sha256'], sheet_mask='alpha', sheet_front_mean_srgb=opaque_mean(Image.open(p)))
            elif (k := keyed_mean(Image.open(p))):   # no cut-out: flat background keyed out by its corner colour
                row.update(sheet=s['path'], sheet_sha256=s['sha256'], sheet_mask='corner-key', sheet_front_mean_srgb=k)
            else:
                row.update(sheet=s['path'], sheet_note='no alpha and no flat background to key; not calibrated')
        look[cid] = row
        print(f'room-look: {cid}: tex {row["basecolor_mean_srgb"]} sheet {row.get("sheet_front_mean_srgb", "-")}')
    OUT.write_text(json.dumps(look, indent=1) + '\n')
    for m in bad:
        print('room-look: FAIL', m)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
