"""合成測試：把角色 sprite 放進預渲染的房間（和引擎做的事情一樣）。

這也是之後 Lua／C 引擎實作的參考：
  1. 角色在世界中的位置 (x, y)（地面 z = 0）→ 用攝影機參數投影到畫面
  2. 依深度縮放 sprite：scale = 焦距(像素) / (深度 × sprite 每公尺像素)
  3. 畫 sprite 的每個像素前，查前景深度圖：前景比角色近 → 這個像素被擋住，不畫

用法：python3 tools/preview_composite.py
"""
import json
import math
import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 320, 240


def load_room(name):
    d = os.path.join(ROOT, "art", "rooms", name)
    with open(os.path.join(d, "room.json"), encoding="utf-8") as f:
        room = json.load(f)
    return d, room


def project(cam, p):
    """世界座標 → (螢幕 x, 螢幕 y, 深度)。深度是沿著攝影機前方的距離。"""
    rel = np.array(p) - np.array(cam["pos"])
    x = rel @ np.array(cam["right"])
    y = rel @ np.array(cam["up"])
    z = rel @ np.array(cam["forward"])
    f = (W / 2) / math.tan(math.radians(cam["fov"]) / 2)
    return W / 2 + x / z * f, H / 2 - y / z * f, z, f


def sprite_dir(cam, yaw_deg):
    """角色面向的方向（世界）相對於攝影機 → 8 個方向的哪一個。

    yaw_deg：角色面向，0 = 面向 -y（和建模時一樣），順時針為正（從上往下看）。
    """
    fwd = np.array(cam["forward"])
    cam_yaw = math.degrees(math.atan2(fwd[0], fwd[1]))     # 攝影機看的方向
    # 角色面向相機 = 方向 0
    face = (yaw_deg + 180) % 360
    rel = (face - cam_yaw) % 360
    return int(round(rel / 45)) % 8


def get_frame(sheet, meta, anim, d, f=0):
    fw, fh = meta["frame"]
    row = next(i for i, r in enumerate(meta["rows"]) if r["anim"] == anim and r["dir"] == d)
    return sheet.crop((f * fw, row * fh, (f + 1) * fw, (row + 1) * fh))


def place(bg, depth, cam, sprite_rgba, meta, x, y):
    sx, sy, z, f = project(cam, (x, y, 0.0))
    scale = f / (z * meta["pixels_per_meter"])
    w = max(1, round(sprite_rgba.width * scale))
    h = max(1, round(sprite_rgba.height * scale))
    sp = np.asarray(sprite_rgba.resize((w, h), Image.NEAREST))
    px, py = meta["pivot"]
    ox = round(sx - px * scale)
    oy = round(sy - py * scale)
    char_cm = z * 100
    out = bg
    hidden = 0
    for j in range(h):
        yy = oy + j
        if not 0 <= yy < H:
            continue
        for i in range(w):
            xx = ox + i
            if not 0 <= xx < W or sp[j, i, 3] == 0:
                continue
            dpt = depth[yy, xx]
            if dpt and dpt < char_cm:       # 前景比角色近 → 擋住
                hidden += 1
                continue
            out[yy, xx] = sp[j, i, :3]
    return hidden


def main():
    char = os.path.join(ROOT, "art", "characters", "cole")
    sheet = Image.open(os.path.join(char, "cole_sheet.png")).convert("RGBA")
    with open(os.path.join(char, "cole_sheet.json")) as f:
        meta = json.load(f)
    shots = [
        # (房間, 機位, x, y, 角色面向, 動作, 格)
        ("foyer", "entrance", -0.3, 8.2, 200, "walk", 2),
        ("foyer", "honor", -3.75, 8.9, 200, "walk", 5),      # 走到柱子後面：一部分被擋住
        ("foyer", "balcony", -1.0, 6.0, 100, "aim", 0),
        ("save_room", "A", 1.6, 3.3, 180, "idle", 0),
    ]
    tiles = []
    for (room, cid, x, y, yaw, anim, fr) in shots:
        d, rj = load_room(room)
        cam = next(c for c in rj["cameras"] if c["id"] == cid)
        bg = np.asarray(Image.open(os.path.join(d, cam["bg"])).convert("RGB")).copy()
        depth = np.asarray(Image.open(os.path.join(d, cam["depth"]))).astype(np.int32)
        dr = sprite_dir(cam, yaw)
        frame = get_frame(sheet, meta, anim, dr, fr)
        hidden = place(bg, depth, cam, frame, meta, x, y)
        print(f"{room}/{cid}: dir {dr}, hidden px {hidden}")
        tiles.append(Image.fromarray(bg).resize((W * 2, H * 2), Image.NEAREST))
    out = Image.new("RGB", (W * 4, H * 4))
    for i, t in enumerate(tiles):
        out.paste(t, ((i % 2) * W * 2, (i // 2) * H * 2))
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    out.save(os.path.join(ROOT, "build", "composite_test.png"))


if __name__ == "__main__":
    main()
