"""介面素材：物品欄背景、柯爾的狀態立繪、打字機存檔畫面、文件閱讀背景、對話框。

全部是 320×240（或其中的一部分），量化成 256 色；文字由遊戲用 text() 畫上去，這裡只做底圖。
輸出：art/ui/
用法：python3 tools/ui.py
"""
import math
import os
import sys

import bpy  # noqa: I001
import numpy as np
from mathutils import Vector
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import kit  # noqa: E402
from kit import mat  # noqa: E402

OUT = os.path.join(ROOT, "art", "ui")
W, H = 320, 240


def q256(im, path, colors=256, dither=True):
    q = im.convert("RGB").quantize(colors=colors, method=Image.Quantize.MEDIANCUT,
                                   dither=Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE)
    q.save(path)
    return q


def tex(name, size=None):
    im = Image.open(os.path.join(ROOT, "art", "textures", name + ".png")).convert("RGB")
    return im


def tiled(name, w, h, scale=1, dark=1.0):
    t = tex(name)
    if scale != 1:
        t = t.resize((t.width * scale, t.height * scale), Image.NEAREST)
    out = Image.new("RGB", (w, h))
    for y in range(0, h, t.height):
        for x in range(0, w, t.width):
            out.paste(t, (x, y))
    if dark != 1.0:
        out = Image.eval(out, lambda v: int(v * dark))
    return out


def bevel(d, box, light, dark_, width=1):
    x0, y0, x1, y1 = box
    for i in range(width):
        d.line([(x0 + i, y1 - i), (x0 + i, y0 + i), (x1 - i, y0 + i)], fill=light)
        d.line([(x0 + i, y1 - i), (x1 - i, y1 - i), (x1 - i, y0 + i)], fill=dark_)


# ---------------------------------------------------------------- 物品欄

def inventory_bg():
    """物品欄的版面（文字與圖示由遊戲畫）：
       左上 狀態立繪框（96×128）＋狀態文字區；右上 8 格物品（4×2，每格 40×40）；
       右中 指令列；下方 道具說明框。
    """
    img = tiled("leather_brown", W, H, scale=2, dark=0.45)
    d = ImageDraw.Draw(img)
    gold, edge, shadow = (150, 120, 60), (90, 72, 40), (12, 10, 8)
    # 狀態立繪框
    d.rectangle([8, 8, 107, 139], fill=(8, 8, 10))
    bevel(d, (8, 8, 107, 139), edge, shadow, 2)
    d.rectangle([7, 7, 108, 140], outline=gold)
    # 狀態文字區（立繪下方）
    d.rectangle([8, 146, 107, 168], fill=(16, 12, 10))
    bevel(d, (8, 146, 107, 168), shadow, edge)
    # 物品格 4×2
    for r in range(2):
        for c in range(4):
            x = 120 + c * 48
            y = 12 + r * 48
            d.rectangle([x, y, x + 41, y + 41], fill=(18, 16, 14))
            bevel(d, (x, y, x + 41, y + 41), shadow, edge, 2)
    d.line([(118, 8), (312, 8)], fill=gold)
    d.line([(118, 108), (312, 108)], fill=gold)
    # 指令列（使用、檢查、組合、交換）
    for i in range(4):
        x = 120 + i * 48
        d.rectangle([x, 116, x + 41, 132], fill=(28, 22, 16))
        bevel(d, (x, 116, x + 41, 132), edge, shadow)
    # 道具說明框
    d.rectangle([8, 178, 311, 231], fill=(10, 9, 8))
    bevel(d, (8, 178, 311, 231), shadow, edge, 2)
    d.rectangle([7, 177, 312, 232], outline=gold)
    # 角落的鉚釘
    for (x, y) in ((4, 4), (315, 4), (4, 235), (315, 235)):
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=gold)
    q256(img, os.path.join(OUT, "inventory_bg.png"), 64, dither=False)
    layout = {
        "portrait": [10, 10, 96, 128], "status_text": [10, 148, 96, 20],
        "slots": [[120 + c * 48 + 4, 12 + r * 48 + 4] for r in range(2) for c in range(4)], "slot_size": 32,
        "commands": [[120 + i * 48, 116, 42, 17] for i in range(4)], "description": [14, 182, 292, 46],
    }
    import json
    with open(os.path.join(OUT, "inventory_layout.json"), "w") as f:
        json.dump(layout, f, indent=1)


def item_box_bg():
    """物流箱畫面：左邊是箱子裡的東西（捲動清單），右邊是身上的 8 格。"""
    img = tiled("wood_crate", W, H, scale=2, dark=0.4)
    d = ImageDraw.Draw(img)
    edge, shadow, green = (110, 90, 60), (12, 10, 8), (60, 110, 70)
    d.rectangle([8, 8, 150, 231], fill=(10, 9, 8))
    bevel(d, (8, 8, 150, 231), shadow, edge, 2)
    d.rectangle([8, 8, 150, 24], fill=(30, 50, 34))          # 標題列：長青當日到貨
    d.rectangle([12, 12, 22, 20], fill=green)
    for r in range(4):
        for c in range(2):
            x = 176 + c * 64
            y = 16 + r * 48
            d.rectangle([x, y, x + 41, y + 41], fill=(18, 16, 14))
            bevel(d, (x, y, x + 41, y + 41), shadow, edge, 2)
    q256(img, os.path.join(OUT, "itembox_bg.png"), 64, dither=False)


# ---------------------------------------------------------------- 文件、對話框

def document_bg():
    """閱讀文件：深色桌面上放著一張泛黃的紙（文字由遊戲畫在紙上）。"""
    img = tiled("wood_furniture", W, H, scale=2, dark=0.35)
    # 紙：重新產生一張不重複的（貼圖會看得出重複的格子）
    sys.path.insert(0, HERE)
    import psx_textures as PT
    n = PT.tile_noise(216, 5, 7, 4)[:, :216]
    n = np.asarray(Image.fromarray((n * 255).astype(np.uint8)).resize((240, 216), Image.BILINEAR)) / 255.0
    arr = PT.ramp(n * 0.45 + 0.45, ["#8a7e60", "#c8bc98", "#e4dcc0"])
    arr = PT.grime(np.asarray(Image.fromarray(arr.astype(np.uint8)).resize((256, 256))).astype(float), 8, 0.25)[:216, :240]
    sheet = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    shadow = Image.new("RGB", (240, 216), (8, 6, 4))
    img.paste(shadow, (44, 18))
    img.paste(sheet, (40, 12))
    d = ImageDraw.Draw(img)
    d.rectangle([40, 12, 279, 227], outline=(120, 110, 90))
    d.polygon([(260, 12), (279, 12), (279, 31)], fill=(150, 140, 115))      # 折角
    q256(img, os.path.join(OUT, "document_bg.png"), 64, dither=False)


def textbox():
    """對話框（畫面下方，320×60）：半透明感用深色＋細邊框表現。"""
    img = Image.new("RGBA", (W, 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([4, 2, W - 5, 57], fill=(6, 6, 8, 235))
    d.rectangle([4, 2, W - 5, 57], outline=(150, 140, 120, 255))
    d.rectangle([6, 4, W - 7, 55], outline=(50, 46, 40, 255))
    img.save(os.path.join(OUT, "textbox.png"))


# ---------------------------------------------------------------- 3D 渲染：打字機特寫、狀態立繪

def typewriter_closeup():
    """打字機存檔畫面：桌上的打字機特寫，紙上的報告由遊戲一行一行打出來。"""
    kit.reset_scene()
    s = bpy.context.scene
    s.cycles.samples = 96
    k = kit.Kit()
    kit.set_ambient((0.02, 0.018, 0.015), 1.0)
    k.box((-1.5, -1.0, 0.67), (1.5, 1.0, 0.77), mat("wood_furniture", "wood_furniture"), uv=1, name="desk")
    k.box((-1.5, 0.6, 0.77), (1.5, 0.62, 2.0), mat("plaster_cream", "plaster_cream"), uv=1, name="wall")
    kit.typewriter(k, 0, 0, 0.77, 0)
    # 一張比較大的紙（存檔文字的位置）
    k.box((-0.13, 0.072, 0.15 + 0.77), (0.13, 0.077, 0.46 + 0.77), mat("paper_blank", color=(0.78, 0.74, 0.62), rough=0.7), name="paper")
    kit.ribbon_tin(k, 0.32, -0.05, 0.77)
    kit.ribbon_tin(k, 0.38, 0.06, 0.77)
    kit.desk_lamp(k, -0.42, 0.25, 0.77, power=20)
    cd = bpy.data.cameras.new("cam")
    cd.sensor_fit = "HORIZONTAL"
    cd.angle = math.radians(42)
    cam = bpy.data.objects.new("cam", cd)
    s.collection.objects.link(cam)
    cam.location = (0.15, -0.75, 1.32)
    cam.rotation_euler = (Vector((0.0, 0.05, 1.02)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    s.camera = cam
    tmp = os.path.join(ROOT, "build", "ui_typewriter.png")
    s.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    q256(Image.open(tmp), os.path.join(OUT, "save_typewriter.png"))


def status_portraits():
    """狀態立繪：柯爾的上半身，三種狀態（良好、負傷、危急）。危急時偏紅、身體往前彎。"""
    import importlib
    import types
    sys.path.insert(0, HERE)
    import character as C
    mod = C.load_character("cole")
    states = {"fine": (C.idle_pose, (1.0, 0.95, 0.88)), "caution": (lambda t: C.hurt_pose(t), (1.0, 0.85, 0.6)),
              "danger": (lambda t: C.hurt_pose(t), (1.0, 0.45, 0.35))}
    for st, (fn, keycol) in states.items():
        kit.reset_scene()
        s = bpy.context.scene
        rig, parts = mod.build(C)
        ang, loc = fn(0.0)
        if st == "caution":           # 負傷：動作輕一點
            ang = {k_: tuple(v * 0.5 for v in a) for k_, a in ang.items()}
            loc = tuple(v * 0.5 for v in loc)
        C.pose(rig, ang, loc)
        s.render.engine = "CYCLES"
        s.cycles.samples = 48
        s.render.resolution_x, s.render.resolution_y = 96, 128
        s.render.film_transparent = True
        s.view_settings.view_transform = "Standard"
        k = kit.Kit()
        k.light("SUN", (0, 0, 5), keycol, 3.5, name="key", rot=(55, 0, -30))
        k.light("SUN", (0, 0, 5), (0.5, 0.6, 0.9), 1.5, name="rim", rot=(-50, 0, 160))
        kit.set_ambient((0.18, 0.18, 0.2), 1.0)
        cd = bpy.data.cameras.new("cam")
        cd.type = "ORTHO"
        cd.ortho_scale = 0.95
        cd.sensor_fit = "VERTICAL"
        cam = bpy.data.objects.new("cam", cd)
        s.collection.objects.link(cam)
        cam.location = (0.9, -3.0, 1.55)
        cam.rotation_euler = (Vector((0.0, 0.0, 1.45)) - cam.location).to_track_quat("-Z", "Y").to_euler()
        s.camera = cam
        tmp = os.path.join(ROOT, "build", f"ui_status_{st}.png")
        s.render.filepath = tmp
        bpy.ops.render.render(write_still=True)
        im = Image.open(tmp).convert("RGBA")
        # 背景：深色＋一點掃描線（像監視器）
        bg = Image.new("RGBA", im.size, (10, 12, 14, 255))
        dd = ImageDraw.Draw(bg)
        for y in range(0, im.height, 3):
            dd.line([(0, y), (im.width, y)], fill=(16, 20, 22, 255))
        bg.alpha_composite(im)
        q256(bg, os.path.join(OUT, f"status_cole_{st}.png"), 48, dither=False)


def contact_sheet():
    names = ["inventory_bg", "itembox_bg", "document_bg", "save_typewriter"]
    sheet = Image.new("RGB", (W * 2 + 8, H * 2 + 8 + 136), (20, 18, 22))
    for i, n in enumerate(names):
        sheet.paste(Image.open(os.path.join(OUT, n + ".png")).convert("RGB"), ((i % 2) * (W + 8), (i // 2) * (H + 8)))
    for i, st in enumerate(("fine", "caution", "danger")):
        sheet.paste(Image.open(os.path.join(OUT, f"status_cole_{st}.png")).convert("RGB"), (i * 104, H * 2 + 16))
    tb = Image.open(os.path.join(OUT, "textbox.png"))
    sheet.paste(tb, (330, H * 2 + 40), tb)
    sheet = sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST)
    sheet.save(os.path.join(ROOT, "build", "ui_sheet.png"))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    inventory_bg()
    item_box_bg()
    document_bg()
    textbox()
    typewriter_closeup()
    status_portraits()
    contact_sheet()
    print("ui done")
