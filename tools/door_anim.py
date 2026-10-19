"""開門轉場動畫（早期惡靈古堡的招牌）：鏡頭對著門，門慢慢打開，門後是一片黑。

這段動畫同時用來掩蓋讀取下一個房間背景的時間（從 SD 卡讀約 77 KB）。
每種門輸出 FRAMES 格 320×240，整段共用一組 256 色調色盤（播放時不必換調色盤）。

輸出：art/doors/<種類>/frame_00.png …、art/doors/<種類>/door.json
用法：python3 tools/door_anim.py [種類 ...]
"""
import json
import math
import os
import sys

import bpy  # noqa: I001
from mathutils import Matrix, Vector
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import kit  # noqa: E402
from kit import mat  # noqa: E402

FRAMES = 20
FPS = 12          # 播放速度：20 格 ≈ 1.7 秒（加上前後的停頓約 2.5 秒）


def ease(t):
    """開門的速度：一開始慢（推不太動），中間快，最後慢下來。"""
    return t * t * (3 - 2 * t)


def build_door_scene(k, kind, open_t):
    """牆、門框、門板（依開門進度轉動）、門後的黑暗、一盞從上方照下來的燈。"""
    wall = mat("plaster_grey", "plaster_grey") if kind == "metal" else mat("wallpaper_damask_green", "wallpaper_damask_green")
    double_ = kind == "wood_double"
    Wd = 1.9 if double_ else 1.0
    # 牆分成門洞的左、右、上三塊（門洞要空著，門後才看得到黑暗）
    k.box((-3, 0.0, -0.1), (-Wd / 2, 0.2, 3.5), wall, uv=2, name="wall_l")
    k.box((Wd / 2, 0.0, -0.1), (3, 0.2, 3.5), wall, uv=2, name="wall_r")
    k.box((-Wd / 2, 0.0, 2.4), (Wd / 2, 0.2, 3.5), wall, uv=2, name="wall_top")
    k.box((-3, -4, -0.1), (3, 0.0, 0.0), mat("floor_stone", "floor_stone") if kind == "metal" else mat("floor_wood_dark", "floor_wood_dark"), uv=2, name="floor")
    # 門洞（黑）
    double = kind == "wood_double"
    W = 1.9 if double else 1.0
    H = 2.4
    k.box((-W / 2, 0.19, 0), (W / 2, 3.0, H), mat("void", color=(0.0, 0.0, 0.0)), name="void")
    frame_m = mat("metal_steel", "metal_steel", metal=0.6) if kind == "metal" else mat("wood_furniture", "wood_furniture")
    k.box((-W / 2 - 0.15, -0.05, 0), (-W / 2, 0.22, H + 0.15), frame_m, uv=1, name="frame")
    k.box((W / 2, -0.05, 0), (W / 2 + 0.15, 0.22, H + 0.15), frame_m, uv=1, name="frame")
    k.box((-W / 2 - 0.15, -0.05, H), (W / 2 + 0.15, 0.22, H + 0.2), frame_m, uv=1, name="frame")
    leaf_m = mat("metal_rusty", "metal_rusty", metal=0.5) if kind == "metal" else mat("door_wood", "wood_furniture")
    panel_m = mat("metal_steel", "metal_steel", metal=0.6) if kind == "metal" else mat("door_panel", "wainscot_dark")
    knob_m = mat("brass", "brass", metal=0.7, rough=0.35)
    a = math.radians(95 * ease(open_t))          # 門往門後（+y）推開
    leaves = [(-W / 2, W / 2, 1)] if not double else [(-W / 2, 0.0, 1), (0.0, W / 2, -1)]
    for (x0, x1, side) in leaves:
        hinge = x0 if side == 1 else x1
        Mh = Matrix.Translation((hinge, 0.05, 0)) @ Matrix.Rotation(-a * side, 4, "Z") @ Matrix.Translation((-hinge, -0.05, 0))
        k.box((x0 + 0.01, 0.0, 0.0), (x1 - 0.01, 0.06, H - 0.01), leaf_m, uv=1.2, M=Mh, name="leaf")
        for (z0, z1) in ((0.15, 1.0), (1.2, H - 0.15)):
            k.box((x0 + 0.1, -0.01, z0), (x1 - 0.1, 0.0, z1), panel_m, uv=1.2, M=Mh, name="panel")
        kx = x1 - 0.1 if side == 1 else x0 + 0.1
        k.box((kx - 0.03, -0.06, 1.0), (kx + 0.03, 0.0, 1.06), knob_m, M=Mh, name="knob")
    # 燈：一盞從鏡頭上方往門照的燈；門後完全沒有光
    k.light("SPOT", (0, -2.6, 2.8), (1.0, 0.78, 0.5) if kind != "metal" else (0.75, 0.85, 1.0), 180, radius=0.2,
            name="door_light", spot_angle=60, rot=(62, 0, 0))
    kit.set_ambient((0.01, 0.01, 0.012), 1.0)


def render_kind(kind):
    out_dir = os.path.join(ROOT, "art", "doors", kind)
    tmp_dir = os.path.join(ROOT, "build", "doors", kind)
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(tmp_dir, exist_ok=True)
    raws = []
    for f in range(FRAMES):
        t = f / (FRAMES - 1)
        kit.reset_scene()
        bpy.context.scene.cycles.samples = 48
        k = kit.Kit()
        build_door_scene(k, kind, t)
        cd = bpy.data.cameras.new("cam")
        cd.sensor_fit = "HORIZONTAL"
        cd.angle = math.radians(58)
        cam = bpy.data.objects.new("cam", cd)
        bpy.context.scene.collection.objects.link(cam)
        # 鏡頭慢慢往門推進（最後幾格穿過門）
        y = -3.2 + 1.6 * ease(t)
        cam.location = (0.0, y, 1.45)
        cam.rotation_euler = (Vector((0, 1.0, 1.25)) - cam.location).to_track_quat("-Z", "Y").to_euler()
        bpy.context.scene.camera = cam
        p = os.path.join(tmp_dir, f"raw_{f:02d}.png")
        bpy.context.scene.render.filepath = p
        bpy.ops.render.render(write_still=True)
        raws.append(Image.open(p).convert("RGB"))
    # 整段共用一組調色盤：把所有格拼成一張大圖量化，再切回來
    strip = Image.new("RGB", (320, 240 * FRAMES))
    for i, im in enumerate(raws):
        strip.paste(im, (0, i * 240))
    q = strip.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
    for i in range(FRAMES):
        q.crop((0, i * 240, 320, (i + 1) * 240)).save(os.path.join(out_dir, f"frame_{i:02d}.png"))
    with open(os.path.join(out_dir, "door.json"), "w") as fp:
        json.dump({"frames": FRAMES, "fps": FPS, "hold_start": 4, "hold_end": 6,
                   "note": "frames share one palette; play while the next room loads"}, fp, indent=1)
    # 預覽：每 4 格取一格
    prev = Image.new("RGB", (320 * 5, 240))
    for j, i in enumerate(range(0, FRAMES, 4)):
        prev.paste(q.crop((0, i * 240, 320, (i + 1) * 240)).convert("RGB"), (j * 320, 0))
    prev.save(os.path.join(ROOT, "build", f"door_{kind}.png"))
    print(kind, "done")


if __name__ == "__main__":
    kinds = sys.argv[1:] or ["wood_single", "wood_double", "metal"]
    for kd in kinds:
        render_kind(kd)
