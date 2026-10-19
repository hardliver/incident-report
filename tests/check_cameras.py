"""檢查每個房間：站得住的每個地方，至少有一個鏡頭看得到角色（全身在畫面裡、沒被家具擋住）。

輸出 build/camera_maps/<房間>.png：俯視圖，每一格的顏色是那裡用的鏡頭，紅色 = 沒有鏡頭看得到。
用法：python3 tests/check_cameras.py [房間 …]
"""
import glob
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import roomgeo  # noqa: E402

COLORS = [(70, 130, 220), (80, 190, 110), (220, 180, 60), (180, 100, 220), (60, 200, 200), (230, 130, 70)]


def main():
    names = sys.argv[1:] or sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(ROOT, "art/rooms/*/room.json")))
    os.makedirs(os.path.join(ROOT, "build", "camera_maps"), exist_ok=True)
    bad = 0
    for n in names:
        room = roomgeo.load(n, ROOT)
        grids, cells = room.camera_grid()
        S = 8
        levels = sorted(grids)
        img = Image.new("RGB", (room.nx * S * len(levels) + 10 * (len(levels) - 1), room.ny * S), (20, 20, 24))
        d = ImageDraw.Draw(img)
        msgs = []
        for li, lv in enumerate(levels):
            g = grids[lv]
            ox = li * (room.nx * S + 10)
            miss = sum(1 for v in g.values() if v[0] == 0)
            for (i, j), (mask, best) in g.items():
                c = COLORS[(best - 1) % len(COLORS)] if mask else (230, 40, 40)
                x, y = ox + i * S, (room.ny - 1 - j) * S        # y 往上（北）在上面
                d.rectangle((x, y, x + S - 2, y + S - 2), fill=c)
            pct = 100 * miss / max(1, len(g))
            if miss:
                msgs.append(f"level {lv}：{miss}/{len(g)} 格（{pct:.0f}%）沒有鏡頭看得到")
        blind = {}
        for (_x, _y, ids) in room.door_blind:
            for i in ids:
                blind[i] = blind.get(i, 0) + 1
        for door_id, cnt in blind.items():
            msgs.append(f"門 {door_id} 附近有 {cnt} 格看不到門")
        img.save(os.path.join(ROOT, "build", "camera_maps", f"{n}.png"))
        legend = "、".join(f"{c['id']}" for c in room.cams)
        if msgs:
            bad += 1
            print(f"✗ {n}（{legend}）：" + "；".join(msgs))
        else:
            print(f"✓ {n}（{legend}）")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
