"""把房間的所有機位排成一張總覽圖。用法：python3 tools/room_sheet.py 輸出.png 房間1 房間2 ..."""
import json
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = sys.argv[1]
items = []
for r in sys.argv[2:]:
    rj = json.load(open(os.path.join(ROOT, "art", "rooms", r, "room.json")))
    for c in rj["cameras"]:
        items.append((r, c["id"], os.path.join(ROOT, "art", "rooms", r, c["bg"])))
cols = 3
rows = (len(items) + cols - 1) // cols
sheet = Image.new("RGB", (cols * 640, rows * 496), (16, 14, 18))
d = ImageDraw.Draw(sheet)
for i, (r, c, p) in enumerate(items):
    x, y = (i % cols) * 640, (i // cols) * 496
    sheet.paste(Image.open(p).convert("RGB").resize((640, 480), Image.NEAREST), (x, y + 16))
    d.text((x + 4, y + 2), f"{r} / {c}", fill=(230, 220, 180))
sheet.save(os.path.join(ROOT, "build", out))
