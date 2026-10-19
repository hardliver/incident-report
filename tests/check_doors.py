"""檢查每個房間的每一扇門都走得到（和遊戲裡 world.lua 相同的碰撞規則）。

做法：把房間切成 10 公分的格子，標出角色站得住的格子（中心和前後左右各 28 公分都要能站），
從每扇門前面的格子出發做「淹水填充」，看看所有門是不是連在同一塊區域、而且每扇門前面都站得到。
家具擋住門、可走範圍畫錯，這裡都會抓出來。

用法：python3 tests/check_doors.py
"""
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = 0.28          # 角色半徑（world.lua 的 PLAYER_R）
REACH = 0.6       # 站在門的範圍往外多遠還算「在門前」（world.lua 的 door_at）
STEP = 0.1


def inpoly(p, x, y):
    inside = False
    j = len(p) - 1
    for i in range(len(p)):
        xi, yi = p[i]
        xj, yj = p[j]
        if (yi > y) != (yj > y) and x < xi + (y - yi) * (xj - xi) / (yj - yi):
            inside = not inside
        j = i
    return inside


def check_room(rj):
    def free(x, y):
        return any(inpoly(p, x, y) for p in rj["walk"]) and not any(inpoly(p, x, y) for p in rj.get("blocks", []))

    def stand(x, y):
        return free(x, y) and free(x + R, y) and free(x - R, y) and free(x, y + R) and free(x, y - R)

    xs = [x for p in rj["walk"] for x, _ in p]
    ys = [y for p in rj["walk"] for _, y in p]
    x0, y0 = min(xs), min(ys)
    nx, ny = int((max(xs) - x0) / STEP) + 1, int((max(ys) - y0) / STEP) + 1
    ok = [[stand(x0 + i * STEP, y0 + j * STEP) for j in range(ny)] for i in range(nx)]

    def door_cells(d):
        bx = [p[0] for p in d["poly"]]
        by = [p[1] for p in d["poly"]]
        return [(i, j) for i in range(nx) for j in range(ny) if ok[i][j]
                and min(bx) - REACH <= x0 + i * STEP <= max(bx) + REACH
                and min(by) - REACH <= y0 + j * STEP <= max(by) + REACH]

    problems = []
    region = {}   # 格子 → 區域編號
    def flood(start, label):
        stack = [start]
        while stack:
            c = stack.pop()
            if c in region:
                continue
            region[c] = label
            i, j = c
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = i + di, j + dj
                if 0 <= a < nx and 0 <= b < ny and ok[a][b] and (a, b) not in region:
                    stack.append((a, b))

    labels = {}
    for d in rj["doors"]:
        cells = door_cells(d)
        if not cells:
            problems.append(f"門 {d['id']}（往 {d['to']}）前面站不到")
            continue
        if cells[0] not in region:
            flood(cells[0], d["id"])
        labels[d["id"]] = region[cells[0]]
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
        probs = check_room(rj)
        if probs:
            bad += 1
            print(f"✗ {rj['id']}：" + "；".join(probs))
        else:
            print(f"✓ {rj['id']}")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
