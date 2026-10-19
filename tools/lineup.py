"""角色總覽圖：每個角色一列，放 正面／斜前／側面／背面／走路 五格。

用法：python3 tools/lineup.py 角色1 角色2 ... → build/lineup.png
"""
import json
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def cell(sheet, meta, anim, d, f=0):
    fw, fh = meta["frame"]
    row = next(i for i, r in enumerate(meta["rows"]) if r["anim"] == anim and r["dir"] == d)
    return sheet.crop((f * fw, row * fh, (f + 1) * fw, (row + 1) * fh))


def main(names, out="lineup.png", scale=2):
    rows = []
    for n in names:
        d = os.path.join(ROOT, "art", "characters", n)
        sheet = Image.open(os.path.join(d, f"{n}_sheet.png")).convert("RGBA")
        meta = json.load(open(os.path.join(d, f"{n}_sheet.json")))
        anims = [r["anim"] for r in meta["rows"]]
        first = anims[0]
        walk = "walk" if "walk" in anims else first
        cells = [cell(sheet, meta, first, 0), cell(sheet, meta, first, 1), cell(sheet, meta, first, 2),
                 cell(sheet, meta, first, 4), cell(sheet, meta, walk, 1, 2)]
        extra = [a for a in dict.fromkeys(anims) if a not in (first, "walk")]
        for a in extra[:2]:
            nfr = next(r["frames"] for r in meta["rows"] if r["anim"] == a)
            cells.append(cell(sheet, meta, a, 1, nfr // 2))
        rows.append((n, cells, meta["frame"]))
    fw, fh = rows[0][2]
    cols = max(len(r[1]) for r in rows)
    img = Image.new("RGBA", (cols * fw + 110, len(rows) * fh), (36, 32, 40, 255))
    dr = ImageDraw.Draw(img)
    for i, (n, cells, _) in enumerate(rows):
        dr.text((4, i * fh + fh // 2), n, fill=(220, 210, 180))
        for j, c in enumerate(cells):
            img.alpha_composite(c, (110 + j * fw, i * fh))
    img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    img.save(os.path.join(ROOT, "build", out))


if __name__ == "__main__":
    args = sys.argv[1:]
    out = "lineup.png"
    if args and args[0].endswith(".png"):
        out = args.pop(0)
    main(args, out)
