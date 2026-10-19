"""物品欄圖示：用 3D 模型渲染（和 PS1 時代的做法一樣），輸出 32×32。

每個道具是一個小函式，用 kit 的基本形狀組出來；攝影機固定是斜上方的正交視角。
輸出：art/icons/<道具>.png（32×32，透明背景）＋ art/icons/icons_sheet.png
用法：python3 tools/icons.py
"""
import math
import os
import sys

import bpy  # noqa: I001
import numpy as np
from mathutils import Matrix, Vector
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import kit  # noqa: E402
from kit import mat, T  # noqa: E402

SIZE = 32
RENDER = 128          # 先用 128 渲染，再縮成 32（邊緣比較乾淨）


def rotX(a):
    return Matrix.Rotation(math.radians(a), 4, "X")


def rotY(a):
    return Matrix.Rotation(math.radians(a), 4, "Y")


def rotZ(a):
    return Matrix.Rotation(math.radians(a), 4, "Z")


# ---------------------------------------------------------------- 道具模型（大約都在 0.3 m 的方框裡）

def handgun(k):
    steel = mat("gun_steel", color=(0.07, 0.07, 0.08), metal=0.85, rough=0.35)
    grip = mat("grip", "wood_furniture")
    k.box((-0.13, -0.015, 0.02), (0.1, 0.015, 0.06), steel, uv=0.2, name="barrel")
    k.cyl((0.0, 0, -0.025), 0.03, 0.05, steel, seg=8, uv=0.1, M=rotX(90) @ Matrix.Translation((0, 0, 0)), name="cyl")
    k.box((0.02, -0.018, -0.02), (0.08, 0.018, 0.04), steel, uv=0.2, name="frame")
    k.box((0.05, -0.016, -0.1), (0.1, 0.016, 0.0), grip, uv=0.2, M=Matrix.Translation((0.075, 0, -0.05)) @ rotY(-15) @ Matrix.Translation((-0.075, 0, 0.05)), name="grip")
    k.box((0.02, -0.004, -0.04), (0.035, 0.004, -0.01), steel, uv=0.1, name="trigger")


def shotgun(k):
    steel = mat("gun_steel", color=(0.07, 0.07, 0.08), metal=0.85, rough=0.35)
    wood = mat("stock", "wood_furniture")
    k.box((-0.3, -0.012, 0.0), (0.15, 0.012, 0.024), steel, uv=0.2, name="barrel")
    k.box((-0.2, -0.016, -0.025), (-0.05, 0.016, 0.0), wood, uv=0.2, name="pump")
    k.box((0.1, -0.018, -0.02), (0.18, 0.018, 0.03), steel, uv=0.2, name="receiver")
    k.box((0.17, -0.016, -0.06), (0.32, 0.016, 0.02), wood, uv=0.2, M=Matrix.Translation((0.17, 0, 0)) @ rotY(-10) @ Matrix.Translation((-0.17, 0, 0)), name="stock")


def flashlight(k):
    body = mat("torch_body", color=(0.08, 0.08, 0.09), metal=0.6, rough=0.4)
    lens = mat("lens", color=(1.0, 0.95, 0.75), emit=3.0)
    Mx = rotY(90) @ Matrix.Translation((0, 0, -0.14))
    k.cyl((0, 0, 0), 0.025, 0.22, body, seg=8, uv=0.2, M=Mx, name="tube")
    k.cyl((0, 0, 0.22), 0.04, 0.06, body, seg=8, uv=0.2, M=Mx, r_top=0.045, name="head")
    k.cyl((0, 0, 0.28), 0.042, 0.004, lens, seg=8, uv=0.1, M=Mx, name="lens")


def bandage(k):
    cloth = mat("bandage", color=(0.82, 0.8, 0.72), rough=0.9)
    k.cyl((0, 0, -0.05), 0.07, 0.1, cloth, seg=10, uv=0.2, name="roll")
    k.cyl((0, 0, -0.051), 0.02, 0.102, mat("core", color=(0.3, 0.25, 0.2)), seg=8, uv=0.1, name="core")
    k.box((0.06, -0.04, -0.05), (0.16, 0.0, -0.045), cloth, uv=0.2, name="tail")


def painkillers(k):
    bottle = mat("pill_bottle", color=(0.6, 0.3, 0.05), rough=0.25)
    cap = mat("pill_cap", color=(0.85, 0.85, 0.82), rough=0.5)
    label = mat("pill_label", color=(0.85, 0.82, 0.72), rough=0.6)
    k.cyl((0, 0, -0.03), 0.047, 0.02, mat("pill_stripe", color=(0.6, 0.1, 0.08)), seg=10, uv=0.1, cap=False, name="stripe")
    k.cyl((0, 0, -0.08), 0.045, 0.13, bottle, seg=10, uv=0.2, name="bottle")
    k.cyl((0, 0, -0.065), 0.0465, 0.075, label, seg=10, uv=0.2, cap=False, name="label")
    k.cyl((0, 0, 0.05), 0.048, 0.035, cap, seg=10, uv=0.2, name="cap")


def ink_ribbon(k):
    tin = mat("tin", color=(0.12, 0.1, 0.08), metal=0.6, rough=0.4)
    red = mat("ribbon_red", color=(0.55, 0.06, 0.05))
    k.cyl((0, 0, -0.02), 0.09, 0.04, tin, seg=12, uv=0.2, name="tin")
    k.cyl((0, 0, 0.02), 0.055, 0.003, red, seg=10, uv=0.1, name="label")
    k.cyl((0, 0, 0.023), 0.02, 0.002, mat("tin_center", color=(0.3, 0.28, 0.25), metal=0.8), seg=8, uv=0.1, name="center")


def rusty_key(k):
    iron = mat("metal_rusty", "metal_rusty", metal=0.4, rough=0.7)
    k.cyl((-0.1, 0, -0.008), 0.045, 0.016, iron, seg=8, uv=0.1, M=rotX(90) @ Matrix.Translation((0, 0, 0)), name="bow")
    k.cyl((-0.1, 0, -0.009), 0.022, 0.018, mat("hole", color=(0.0, 0.0, 0.0)), seg=6, uv=0.1, M=rotX(90), name="hole")
    k.box((-0.06, -0.008, -0.01), (0.12, 0.008, 0.01), iron, uv=0.1, name="shaft")
    k.box((0.08, -0.008, -0.05), (0.1, 0.008, -0.01), iron, uv=0.1, name="bit")
    k.box((0.105, -0.008, -0.04), (0.12, 0.008, -0.01), iron, uv=0.1, name="bit2")


def medal(color, name):
    def f(k):
        m = mat(name, color=color, metal=0.35, rough=0.3)      # 金屬感降低：沒有環境可以反射時，高金屬會變暗
        rib = mat("medal_ribbon", color=(0.1, 0.25, 0.15))
        k.cyl((0, 0, -0.01), 0.08, 0.02, m, seg=12, uv=0.1, M=rotX(90), name="disc")
        k.cyl((0, 0, -0.012), 0.055, 0.025, mat(name + "_hi", color=tuple(min(1, c * 1.35) for c in color), metal=0.2, rough=0.25),
              seg=5, uv=0.1, M=rotX(90), name="star")
        k.box((-0.03, -0.006, 0.07), (0.03, 0.006, 0.16), rib, uv=0.1, name="ribbon")
    return f


def id_card(k):
    white = mat("card_white", color=(0.85, 0.85, 0.82), rough=0.4)
    green = mat("card_green", color=(0.12, 0.32, 0.2), rough=0.4)
    photo = mat("card_photo", color=(0.45, 0.4, 0.35), rough=0.5)
    k.box((-0.1, -0.003, -0.065), (0.1, 0.003, 0.065), white, uv=0.2, name="card")
    k.box((-0.1, -0.004, 0.035), (0.1, 0.004, 0.065), green, uv=0.2, name="band")
    k.box((-0.085, -0.0045, -0.05), (-0.03, 0.0045, 0.02), photo, uv=0.2, name="photo")
    for z in (0.0, -0.025):
        k.box((-0.015, -0.0045, z), (0.08, 0.0045, z + 0.008), mat("card_text", color=(0.2, 0.2, 0.2)), uv=0.1, name="txt")


def ledger(k):
    cover = mat("leather_brown", "leather_brown")
    pages = mat("pages", color=(0.8, 0.76, 0.62), rough=0.8)
    k.box((-0.1, -0.13, -0.03), (0.1, 0.13, 0.03), cover, uv=0.3, name="cover")
    k.box((-0.092, -0.125, -0.024), (0.105, 0.125, 0.024), pages, uv=0.3, name="pages")
    k.box((-0.1, -0.03, 0.03), (0.1, 0.0, 0.032), mat("strap_gold", "brass", metal=0.7), uv=0.2, name="label")


def herbicide(k):
    plastic = mat("herb_bottle", color=(0.62, 0.66, 0.6), rough=0.4)
    label = mat("herb_label", color=(0.75, 0.6, 0.1), rough=0.5)
    k.box((-0.06, -0.035, -0.12), (0.06, 0.035, 0.06), plastic, uv=0.2, name="bottle")
    k.box((-0.061, -0.036, -0.08), (0.061, 0.036, 0.02), label, uv=0.2, name="label")
    k.cyl((0, 0, 0.06), 0.02, 0.04, plastic, seg=8, uv=0.1, name="neck")
    k.cyl((0, 0, 0.1), 0.024, 0.025, mat("herb_cap", color=(0.1, 0.1, 0.1)), seg=8, uv=0.1, name="cap")
    k.box((-0.02, -0.036, -0.07), (0.02, -0.037, -0.03), mat("skull", color=(0.05, 0.05, 0.05)), uv=0.1, name="mark")


def crowbar(k):
    steel = mat("crowbar", color=(0.35, 0.08, 0.06), metal=0.6, rough=0.5)
    k.box((-0.2, -0.01, -0.01), (0.18, 0.01, 0.01), steel, uv=0.2, M=rotY(-35), name="bar")
    k.box((0.13, -0.01, -0.01), (0.2, 0.01, 0.01), steel, uv=0.2, M=rotY(-35) @ Matrix.Translation((0.18, 0, 0)) @ rotY(60) @ Matrix.Translation((-0.18, 0, 0)), name="hook")


def lighter(k):
    chrome = mat("chrome", color=(0.6, 0.6, 0.62), metal=0.95, rough=0.25)
    k.box((-0.025, -0.012, -0.05), (0.025, 0.012, 0.03), chrome, uv=0.1, name="body")
    k.box((-0.025, -0.012, 0.03), (0.025, 0.012, 0.05), chrome, uv=0.1, M=Matrix.Translation((0.025, 0, 0.03)) @ rotY(-110) @ Matrix.Translation((-0.025, 0, -0.03)), name="lid")


def shells(k):
    red = mat("shell_red", color=(0.5, 0.05, 0.04), rough=0.4)
    brass = mat("brass", "brass", metal=0.8, rough=0.3)
    for i, (x, y) in enumerate(((-0.04, 0), (0.0, 0.02), (0.04, -0.01))):
        Mi = Matrix.Translation((x, y, -0.06)) @ rotZ(i * 20)
        k.cyl((0, 0, 0), 0.016, 0.08, red, seg=8, uv=0.1, M=Mi, name="shell")
        k.cyl((0, 0, 0), 0.0175, 0.02, brass, seg=8, uv=0.1, M=Mi, name="base")


# ---------------- 第 1–2 章的道具（2026-10-19）

def canned_food(k):
    tin = mat("can_tin", color=(0.55, 0.55, 0.56), metal=0.6, rough=0.35)
    label = mat("can_label", color=(0.55, 0.12, 0.08), rough=0.6)
    k.cyl((0, 0, -0.07), 0.055, 0.14, tin, seg=10, uv=0.2, name="can")
    k.cyl((0, 0, -0.05), 0.0565, 0.1, label, seg=10, uv=0.2, cap=False, name="label")
    k.cyl((0, 0, -0.02), 0.057, 0.03, mat("can_band", color=(0.85, 0.75, 0.3), rough=0.6), seg=10, uv=0.1, cap=False, name="band")


def cast_iron_pan(k):
    iron = mat("pan_iron", color=(0.06, 0.06, 0.065), metal=0.6, rough=0.5)
    k.cyl((-0.04, 0, -0.02), 0.1, 0.03, iron, seg=12, uv=0.2, name="pan")
    k.box((0.05, -0.012, 0.0), (0.2, 0.012, 0.016), iron, uv=0.1, name="handle")


def barbell_plate(k):
    iron = mat("plate_iron", color=(0.08, 0.08, 0.09), metal=0.5, rough=0.5)
    k.cyl((0, 0, -0.015), 0.12, 0.03, iron, seg=12, uv=0.2, M=rotX(90), name="plate")
    k.cyl((0, 0, -0.017), 0.025, 0.034, mat("plate_hole", color=(0.0, 0.0, 0.0)), seg=8, uv=0.1, M=rotX(90), name="hole")
    k.box((-0.05, -0.018, 0.06), (0.05, -0.016, 0.08), mat("plate_text", color=(0.75, 0.75, 0.7)), uv=0.1, name="txt")


def valve_handle(k):
    m = mat("valve_red_icon", color=(0.6, 0.08, 0.05), metal=0.5, rough=0.4)
    k.cyl((0, 0, -0.01), 0.11, 0.02, m, seg=10, uv=0.2, cap=False, name="rim")
    for a in (0, 60, 120):
        k.box((-0.11, -0.008, -0.008), (0.11, 0.008, 0.008), m, uv=0.1, M=rotZ(a), name="spoke")
    k.cyl((0, 0, -0.015), 0.025, 0.03, m, seg=8, uv=0.1, name="hub")


def room_card(k):
    plastic = mat("card_gold", color=(0.7, 0.55, 0.2), metal=0.4, rough=0.35)
    k.box((-0.1, -0.003, -0.063), (0.1, 0.003, 0.063), plastic, uv=0.2, name="card")
    k.box((-0.09, -0.0035, 0.02), (0.09, 0.0035, 0.04), mat("card_strip", color=(0.05, 0.05, 0.05)), uv=0.1, name="strip")
    k.box((-0.08, -0.0035, -0.045), (-0.02, 0.0035, -0.015), mat("card_num", color=(0.15, 0.1, 0.05)), uv=0.1, name="num")


def locker_key(k):
    steel = mat("key_steel", color=(0.6, 0.6, 0.62), metal=0.8, rough=0.3)
    tag = mat("key_tag", color=(0.15, 0.3, 0.2), rough=0.5)
    k.box((-0.11, -0.006, -0.03), (-0.03, 0.006, 0.03), steel, uv=0.1, name="head")
    k.box((-0.03, -0.006, -0.008), (0.1, 0.006, 0.008), steel, uv=0.1, name="shaft")
    for x in (0.03, 0.06, 0.085):
        k.box((x, -0.006, -0.025), (x + 0.012, 0.006, -0.008), steel, uv=0.1, name="tooth")
    k.cyl((-0.17, 0, -0.005), 0.045, 0.01, tag, seg=8, uv=0.1, M=rotX(90), name="tag")


def document(k):
    paper = mat("doc_paper", "paper")
    k.box((-0.09, -0.12, -0.003), (0.09, 0.12, 0.003), paper, uv=0.25, M=rotX(-60), name="page")
    k.box((-0.08, -0.11, 0.0), (0.1, 0.13, 0.002), paper, uv=0.25, M=rotX(-60) @ Matrix.Translation((0.02, 0.01, -0.006)) @ rotZ(8), name="page2")
    k.box((-0.09, 0.09, 0.0), (-0.07, 0.12, 0.006), mat("clip", color=(0.6, 0.6, 0.62), metal=0.8), uv=0.1, M=rotX(-60), name="clip")


ICONS = {
    "handgun": handgun, "shotgun": shotgun, "shells": shells, "flashlight": flashlight,
    "bandage": bandage, "painkillers": painkillers, "ink_ribbon": ink_ribbon, "rusty_key": rusty_key,
    "medal_silver": medal((0.6, 0.6, 0.62), "medal_silver"), "medal_gold": medal((0.85, 0.65, 0.2), "medal_gold"),
    "medal_platinum": medal((0.78, 0.8, 0.84), "medal_platinum"), "medal_diamond": medal((0.6, 0.85, 1.0), "medal_diamond"),
    "id_card": id_card, "ledger": ledger, "herbicide": herbicide, "crowbar": crowbar, "lighter": lighter,
    "canned_food": canned_food, "cast_iron_pan": cast_iron_pan, "barbell_plate": barbell_plate, "valve_handle": valve_handle,
    "room_card": room_card, "locker_key": locker_key, "document": document,
}


# 小東西放大一點（正交攝影機的視野寬度，公尺）
SCALE = {"shells": 0.24, "lighter": 0.16, "painkillers": 0.3, "ink_ribbon": 0.3, "rusty_key": 0.34,
         "medal_silver": 0.34, "medal_gold": 0.34, "medal_platinum": 0.34, "medal_diamond": 0.34, "bandage": 0.34,
         "id_card": 0.3, "herbicide": 0.3, "canned_food": 0.28, "valve_handle": 0.3, "room_card": 0.3,
         "locker_key": 0.36, "document": 0.34, "barbell_plate": 0.32}


def render_icon(name, fn, out_dir):
    kit.reset_scene()
    s = bpy.context.scene
    s.render.resolution_x = s.render.resolution_y = RENDER
    s.render.film_transparent = True
    s.cycles.samples = 48
    k = kit.Kit()
    fn(k)
    kit.set_ambient((0.3, 0.3, 0.32), 1.0)
    k.light("SUN", (0, 0, 5), (1.0, 0.95, 0.85), 3.5, name="key", rot=(40, 0, -40))
    k.light("SUN", (0, 0, 5), (0.6, 0.7, 1.0), 1.5, name="rim", rot=(-50, 0, 150))
    cd = bpy.data.cameras.new("icon_cam")
    cd.type = "ORTHO"
    cd.ortho_scale = SCALE.get(name, 0.42)
    cam = bpy.data.objects.new("icon_cam", cd)
    s.collection.objects.link(cam)
    s.camera = cam
    # 斜上方看（和 PS1 惡靈古堡物品欄的「轉動中的道具」一樣的角度）
    el, az = math.radians(30), math.radians(-30)
    cam.location = (math.sin(az) * math.cos(el) * 3, -math.cos(az) * math.cos(el) * 3, math.sin(el) * 3)
    cam.rotation_euler = (Vector((0, 0, 0)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    tmp = os.path.join(ROOT, "build", "icon_tmp.png")
    s.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    im = Image.open(tmp).convert("RGBA").resize((SIZE, SIZE), Image.LANCZOS)
    arr = np.asarray(im).copy()
    arr[..., 3] = np.where(arr[..., 3] > 90, 255, 0)
    out = Image.fromarray(arr)
    out.save(os.path.join(out_dir, name + ".png"))
    return out


def main():
    out_dir = os.path.join(ROOT, "art", "icons")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    names = sys.argv[1:] or list(ICONS)
    made = [(n, render_icon(n, ICONS[n], out_dir)) for n in names]
    # 合成總表（每列 6 個）＋量化成共用的 64 色
    cols = 6
    rows = (len(made) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * SIZE, rows * SIZE), (0, 0, 0, 0))
    for i, (_n, im) in enumerate(made):
        sheet.alpha_composite(im, ((i % cols) * SIZE, (i // cols) * SIZE))
    sheet.save(os.path.join(out_dir, "icons_sheet.png"))
    prev = Image.new("RGBA", sheet.size, (24, 20, 28, 255))
    prev.alpha_composite(sheet)
    prev.resize((sheet.width * 4, sheet.height * 4), Image.NEAREST).save(os.path.join(ROOT, "build", "icons_preview.png"))
    print(f"{len(made)} icons")


if __name__ == "__main__":
    main()
