"""房間的幾何：哪裡站得住、有多高、每個鏡頭在哪裡看得到角色。

和遊戲裡的 world.lua 用同一套規則（改了一邊，另一邊也要改）：
  - 「地面」有好幾種：一樓的可走範圍（walk，level 0，高度 0）、樓上的地板（floors，level 1…）、
    樓梯（ramps：沿著 x 或 y 從 z0 線性升到 z1）
  - 一個點站不站得住：在某一塊地面上、那塊地面在這裡的高度和角色現在的高度差不到 35 公分，
    而且不在那一層的障礙物（blocks）裡
  - 角色站得住：中心和前後左右各 28 公分的點都站得住

鏡頭（camera_report / camera_grid）：
  把房間切成 25 公分的格子，在每一格放一個「假人」（腳、腰、頭三個點），
  看每個鏡頭能不能看到他：三個點都在畫面裡、至少兩點沒被前景的家具擋住、大小合理（不會大到只看到半個頭）。
  遊戲裡依格子切換鏡頭：目前的鏡頭還看得到就不換，看不到才換成那一格最好的鏡頭。
"""
import json
import math
import os

import numpy as np
from PIL import Image

R = 0.28            # 角色半徑
STEP_Z = 0.35       # 一步最多能上下多少（樓梯每一階 0.3）
CELL = 0.25         # 鏡頭格子的大小
PPM = 62            # 角色圖每公尺幾像素
W, H = 320, 240


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


class Room:
    def __init__(self, rj, art_dir=None):
        self.rj = rj
        self.art_dir = art_dir
        # 地面：(level, poly, 高度函式)
        self.surfaces = [(0, p, None) for p in rj["walk"]]
        self.blocks = [(0, p) for p in rj.get("blocks", [])]
        for f in rj.get("floors", []):
            for p in f["walk"]:
                self.surfaces.append((f["level"], p, f["z"]))
            for p in f.get("blocks", []):
                self.blocks.append((f["level"], p))
        for r in rj.get("ramps", []):
            self.surfaces.append((r["level"], r["poly"], r))
        self.cams = rj["cameras"]
        self._depth = {}

    @staticmethod
    def surf_z(spec, x, y):
        if spec is None:
            return 0.0
        if isinstance(spec, (int, float)):
            return float(spec)
        a = x if spec["axis"] == "x" else y
        t = (a - spec["a0"]) / (spec["a1"] - spec["a0"])
        t = min(1.0, max(0.0, t))
        return spec["z0"] + (spec["z1"] - spec["z0"]) * t

    def point(self, x, y, z):
        """(x, y) 在高度 z 附近站得住的地面：回傳 (level, 高度)，沒有回傳 None。"""
        best = None
        for lv, p, spec in self.surfaces:
            if inpoly(p, x, y):
                sz = self.surf_z(spec, x, y)
                if abs(sz - z) <= STEP_Z and not any(blv == lv and inpoly(bp, x, y) for blv, bp in self.blocks):
                    if best is None or abs(sz - z) < abs(best[1] - z):
                        best = (lv, sz)
        return best

    def stand(self, x, y, z):
        c = self.point(x, y, z)
        if c is None:
            return None
        for dx, dy in ((R, 0), (-R, 0), (0, R), (0, -R)):
            if self.point(x + dx, y + dy, c[1]) is None:
                return None
        return c

    def standable_cells(self):
        """所有站得住的格子：[(x, y, z, level)]。同一個 (x, y) 可能有好幾層。"""
        xs = [x for _, p, _ in self.surfaces for x, _ in p]
        ys = [y for _, p, _ in self.surfaces for _, y in p]
        self.x0, self.y0 = min(xs), min(ys)
        self.nx = int((max(xs) - self.x0) / CELL) + 1
        self.ny = int((max(ys) - self.y0) / CELL) + 1
        out = []
        for i in range(self.nx):
            for j in range(self.ny):
                x, y = self.x0 + (i + 0.5) * CELL, self.y0 + (j + 0.5) * CELL
                seen = set()
                for lv, p, spec in self.surfaces:
                    if inpoly(p, x, y):
                        z = self.surf_z(spec, x, y)
                        c = self.stand(x, y, z)
                        if c and c[0] not in seen:
                            seen.add(c[0])
                            out.append((i, j, x, y, c[1], c[0]))
        return out

    # ---------------- 鏡頭

    def depth(self, cam):
        if cam["id"] not in self._depth:
            self._depth[cam["id"]] = np.asarray(Image.open(os.path.join(self.art_dir, cam["depth"]))).astype(np.int32)
        return self._depth[cam["id"]]

    @staticmethod
    def project(cam, x, y, z):
        rel = np.array([x, y, z]) - np.array(cam["pos"])
        zf = rel @ np.array(cam["forward"])
        if zf < 0.2:
            return None
        f = (W / 2) / math.tan(math.radians(cam["fov"]) / 2)
        return W / 2 + (rel @ np.array(cam["right"])) / zf * f, H / 2 - (rel @ np.array(cam["up"])) / zf * f, zf, f

    def view(self, cam, x, y, z):
        """回傳 (看得到幾點 0–3, 縮放 256=原尺寸, 全部在畫面裡?)"""
        dep = self.depth(cam)
        feet = self.project(cam, x, y, z + 0.1)
        if feet is None:
            return 0, 0, False
        scale = feet[3] / (feet[2] * PPM) * 256
        vis, inside = 0, True
        for hz in (0.15, 0.95, 1.65):
            pr = self.project(cam, x, y, z + hz)
            if pr is None:
                return 0, 0, False
            sx, sy, zf, _ = pr
            if not (6 <= sx <= W - 6 and 2 <= sy <= H - 2):
                inside = False
                continue
            d = dep[int(sy), int(sx)]
            if d == 0 or d > zf * 100 - 15:
                vis += 1
        # 角色的寬度也要在畫面裡（左右各 0.25 公尺）
        for dx in (-0.25, 0.25):
            pr = self.project(cam, x + dx * cam["right"][0], y + dx * cam["right"][1], z + 0.95)
            if pr is None or not (2 <= pr[0] <= W - 2):
                inside = False
        return vis, scale, inside

    def good(self, cam, x, y, z):
        vis, scale, inside = self.view(cam, x, y, z)
        return inside and vis >= 2 and 60 <= scale <= 560, vis, scale

    def zone_cam(self, x, y):
        for zn in self.rj.get("zones", []):
            if inpoly(zn["poly"], x, y):
                return zn["camera"]
        return None

    def camera_grid(self):
        """每一格：(看得到的鏡頭位元遮罩, 最好的鏡頭編號 1 起算；0 = 都看不到)。依 level 分開。"""
        grids = {}
        cells = self.standable_cells()
        for (i, j, x, y, z, lv) in cells:
            zc = self.zone_cam(x, y) if lv == 0 else None
            mask, best, best_score = 0, 0, -1
            for k, cam in enumerate(self.cams):
                ok, vis, scale = self.good(cam, x, y, z)
                if ok:
                    mask |= 1 << k
                    # 優先：原本設計的鏡頭區 → 看得到的點多 → 大小接近 250（不會太遠、太近）
                    score = (500 if cam["id"] == zc else 0) + vis * 100 - abs(scale - 250) / 10
                    if score > best_score:
                        best, best_score = k + 1, score
            if best == 0:
                # 沒有鏡頭「好好地」看得到：退而求其次，選看得到最多點的（遊戲裡一定要有一個鏡頭）。
                # 檢查工具還是把這種格子算成紅色
                fb, fb_score = 0, -1
                for k, cam in enumerate(self.cams):
                    vis, scale, inside = self.view(cam, x, y, z)
                    sc = vis * 10 + (5 if inside else 0)
                    if sc > fb_score:
                        fb, fb_score = k + 1, sc
                grids.setdefault(lv, {})[(i, j)] = (0, fb)
                continue
            grids.setdefault(lv, {})[(i, j)] = (mask, best)
        return grids, cells


def load(room_id, root):
    d = os.path.join(root, "art", "rooms", room_id)
    return Room(json.load(open(os.path.join(d, "room.json"))), d)
