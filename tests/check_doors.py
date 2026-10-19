"""檢查每個房間的每一扇門都走得到（和遊戲裡 world.lua 相同的規則，見 tools/roomgeo.py）。

做法：把房間切成 25 公分的格子，標出角色站得住的格子（包含二樓、樓梯），
從每扇門前面的格子出發做「淹水填充」（相鄰的格子高度差不到 35 公分才算連著），
看看所有門是不是連在同一塊區域。家具擋住門、樓梯接不上二樓，這裡都會抓出來。

用法：python3 tests/check_doors.py
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import roomgeo  # noqa: E402

REACH = 0.72      # 站在門的範圍往外多遠還算「在門前」（world.lua 的 door_at 是 0.6；格子有 25 公分的誤差）


def check_room(rj, d):
    room = roomgeo.Room(rj, d)
    cells = room.standable_cells()
    at = {}
    for (i, j, x, y, z, lv) in cells:
        at.setdefault((i, j), []).append((z, lv, x, y))
    region = {}

    def flood(start, label):
        stack = [start]
        while stack:
            c = stack.pop()
            if c in region:
                continue
            region[c] = label
            i, j, z = c
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                for (z2, _lv, _x, _y) in at.get((i + di, j + dj), []):
                    if abs(z2 - z) <= roomgeo.STEP_Z:
                        stack.append((i + di, j + dj, z2))

    problems, labels = [], {}
    for dr in rj["doors"]:
        xs = [p[0] for p in dr["poly"]]
        ys = [p[1] for p in dr["poly"]]
        dz = dr.get("z", 0)
        near = [(i, j, z) for (i, j), lst in at.items() for (z, _lv, x, y) in lst
                if min(xs) - REACH <= x <= max(xs) + REACH and min(ys) - REACH <= y <= max(ys) + REACH and abs(z - dz) < 1.0]
        if not near:
            problems.append(f"門 {dr['id']}（往 {dr['to']}）前面站不到")
            continue
        if near[0] not in region:
            flood(near[0], dr["id"])
        labels[dr["id"]] = region[near[0]]
    if len(set(labels.values())) > 1:
        groups = {}
        for k, v in labels.items():
            groups.setdefault(v, []).append(k)
        problems.append("門被分成好幾塊走不通的區域：" + "；".join("、".join(g) for g in groups.values()))
    return problems


def main():
    bad = 0
    for p in sorted(glob.glob(os.path.join(ROOT, "art", "rooms", "*", "room.json"))):
        rj = json.load(open(p))
        probs = check_room(rj, os.path.dirname(p))
        if probs:
            bad += 1
            print(f"✗ {rj['id']}：" + "；".join(probs))
        else:
            print(f"✓ {rj['id']}")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
