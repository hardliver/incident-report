"""幫房間找新鏡頭的位置：哪裡放一台攝影機，可以拍到目前沒有鏡頭拍得到的地方。

做法：
  1. 用 room.json 和現有鏡頭的深度圖，找出「紅色格子」（沒有鏡頭好好拍到角色的地方，見 tools/roomgeo.py）
  2. 紅色格子連成一塊一塊；每一塊的中心當作「要拍的地方」
  3. 沿著牆邊每 0.8 公尺、兩種高度試放攝影機，對著那一塊。
     每個候選鏡頭，對每個紅色格子的假人（腳、腰、頭）在 Blender 裡射光線，看會不會被擋住
  4. 印出每一塊拍到最多格子的鏡頭（門附近的格子加倍計分），複製到 rooms/<房間>.py 的 cameras

用法：python3 tools/suggest_cameras.py library            只印出建議
      python3 tools/suggest_cameras.py library --apply 2  把分數最高的 2 個建議直接加進 rooms/library.py（id 是 auto1、auto2…）
"""
import math
import os
import sys

import bpy  # noqa: F401
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import kit  # noqa: E402
import roomgeo  # noqa: E402
from bake_room import load_room  # noqa: E402


def components(cells):
    """紅色格子 → 相連的一塊一塊（同一層、上下左右相鄰）。"""
    left = {(i, j, lv): (x, y, z) for (i, j, x, y, z, lv) in cells}
    out = []
    while left:
        k, v = left.popitem()
        stack, comp = [k], {k: v}
        while stack:
            i, j, lv = stack.pop()
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (i + di, j + dj, lv)
                if n in left:
                    comp[n] = left.pop(n)
                    stack.append(n)
        out.append(comp)
    return out


def basis(pos, target):
    f = (Vector(target) - Vector(pos)).normalized()
    r = f.cross(Vector((0, 0, 1))).normalized()
    u = r.cross(f)
    return f, r, u


def sees(scene, dg, pos, f, r, u, fov, x, y, z):
    focal = 160 / math.tan(math.radians(fov) / 2)
    o = Vector(pos)
    vis, scale = 0, 0
    for hz in (0.15, 0.95, 1.65):
        p = Vector((x, y, z + hz))
        rel = p - o
        zf = rel.dot(f)
        if zf < 0.3:
            return False
        sx = 160 + rel.dot(r) / zf * focal
        sy = 120 - rel.dot(u) / zf * focal
        if not (6 <= sx <= 314 and 2 <= sy <= 238):
            return False
        scale = focal / (zf * roomgeo.PPM) * 256
        d = rel.length
        ok, loc, *_ = scene.ray_cast(dg, o, rel.normalized(), distance=d)
        if not ok or (loc - o).length > d - roomgeo.DEPTH_BIAS / 100:
            vis += 1
    # 新鏡頭要求角色大一點（90 以上）：太遠的鏡頭雖然「看得到」，但玩家看不清楚
    return vis >= 2 and roomgeo.MIN_SCALE + 15 <= scale <= 520


def door_seen(scene, dg, pos, f, r, u, fov, door):
    xs = [p[0] for p in door["poly"]]
    ys = [p[1] for p in door["poly"]]
    p = Vector((sum(xs) / len(xs), sum(ys) / len(ys), door.get("z", 0) + 1.0))
    o = Vector(pos)
    rel = p - o
    zf = rel.dot(f)
    if zf < 0.3:
        return False
    focal = 160 / math.tan(math.radians(fov) / 2)
    sx = 160 + rel.dot(r) / zf * focal
    sy = 120 - rel.dot(u) / zf * focal
    if not (4 <= sx <= 316 and 4 <= sy <= 236):
        return False
    ok, loc, *_ = scene.ray_cast(dg, o, rel.normalized(), distance=rel.length)
    return not ok or (loc - o).length > rel.length - 0.4


def main():
    name = sys.argv[1]
    room = roomgeo.load(name, ROOT)
    grids, cells = room.camera_grid()
    red = [c for c in cells if grids[c[5]][(c[0], c[1])][0] == 0]
    # 站在門邊、但目前的鏡頭看不到門的格子：新鏡頭要同時拍到角色和門
    blind_xy = {(round(x, 3), round(y, 3)): ids for (x, y, ids) in room.door_blind}
    red_set = {(c[0], c[1], c[5]) for c in red}
    for c in cells:
        if (round(c[2], 3), round(c[3], 3)) in blind_xy and (c[0], c[1], c[5]) not in red_set:
            red.append(c)
    door_of = {d["id"]: d for d in room.rj["doors"]}
    need_door = {(c[0], c[1], c[5]): [door_of[i] for i in blind_xy.get((round(c[2], 3), round(c[3], 3)), [])] for c in red}
    print(f"{name}：{len(red)} 個要補的格子（拍不到角色，或站在門邊卻看不到門）")
    if not red:
        return
    kit.reset_scene()
    mod = load_room(name)
    k = kit.Kit()
    mod.build(k)
    scene = bpy.context.scene
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    doors = room.rj["doors"]

    def near_door(x, y):
        for d in doors:
            xs = [p[0] for p in d["poly"]]
            ys = [p[1] for p in d["poly"]]
            if min(xs) - 1.2 <= x <= max(xs) + 1.2 and min(ys) - 1.2 <= y <= max(ys) + 1.2:
                return True
        return False

    xs = [x for _, p, _ in room.surfaces for x, _ in p]
    ys = [y for _, p, _ in room.surfaces for _, y in p]
    x0, x1, y0, y1 = min(xs) + 0.1, max(xs) - 0.1, min(ys) + 0.1, max(ys) - 0.1
    ring = []
    t = 0.0
    while t <= 1.0001:
        for (a, b) in ((x0 + (x1 - x0) * t, y0), (x0 + (x1 - x0) * t, y1), (x0, y0 + (y1 - y0) * t), (x1, y0 + (y1 - y0) * t)):
            ring.append((a, b))
        t += 0.8 / max(x1 - x0, y1 - y0)
    picks = []
    for comp in sorted(components(red), key=len, reverse=True):
        if len(comp) < 6:
            continue
        pts = list(comp.values())
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        cz = sum(p[2] for p in pts) / len(pts)
        best = None
        for (px, py) in ring:
            for hz in (2.3, 2.9):
                pos = (px, py, cz + hz)
                target = (cx, cy, cz + 0.6)
                if math.hypot(px - cx, py - cy) < 1.5:
                    continue
                f, r, u = basis(pos, target)
                score = 0
                for key, (x, y, z) in comp.items():
                    if sees(scene, dg, pos, f, r, u, 72, x, y, z) and all(
                            door_seen(scene, dg, pos, f, r, u, 72, d) for d in need_door.get(key, [])):
                        score += 3 if near_door(x, y) else 1
                if best is None or score > best[0]:
                    best = (score, pos, target)
        sc, pos, target = best
        fmt = lambda v: "(" + ", ".join(f"{a:.1f}" for a in v) + ")"  # noqa: E731
        print(f"  一塊 {len(comp)} 格（中心 {cx:.1f}, {cy:.1f}）：分數 {sc} → "
              f'{{"id": "?", "pos": {fmt(pos)}, "target": {fmt(target)}, "fov": 72}}')
        if sc > 0:
            picks.append((sc, fmt(pos), fmt(target)))
    if "--apply" in sys.argv:
        n = int(sys.argv[sys.argv.index("--apply") + 1])
        import re
        path = os.path.join(ROOT, "rooms", name + ".py")
        src = open(path, encoding="utf-8").read()
        used = set(re.findall(r'"id": "(auto\d+)"', src))
        m = re.search(r'"cameras": \[\n', src)
        k = 1
        lines = []
        for sc, pos, target in sorted(picks, reverse=True)[:n]:
            while f"auto{k}" in used:
                k += 1
            used.add(f"auto{k}")
            lines.append(f'            {{"id": "auto{k}", "pos": {pos}, "target": {target}, "fov": 72}},   # tools/suggest_cameras.py\n')
        src = src[:m.end()] + "".join(lines) + src[m.end():]
        open(path, "w", encoding="utf-8").write(src)
        print(f"  已加入 {len(lines)} 個鏡頭到 rooms/{name}.py")


if __name__ == "__main__":
    main()
