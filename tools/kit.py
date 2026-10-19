"""場景與道具套件（Blender / bpy）。

所有模型都用程式產生：
  - 幾何：盒子、圓柱、平面等基本形狀組合，面數維持在 PSX 等級
  - 貼圖：art/textures/ 裡的 PSX 貼圖，最近鄰取樣（看得到像素）
  - UV：依「世界座標」投影（box mapping），所以同一種材質在不同大小的物件上，
        貼圖的密度都一樣，不會被拉長

座標：x 往右、y 往前（遠離大門）、z 往上；1 單位 = 1 公尺（Blender 的慣例）。

每個物件可以標記：
  occluder=True  → 這個物件會擋住角色（寫進前景深度遮罩）
"""
import math
import os

import bpy  # noqa: I001  (bpy 要先 import，bmesh 才找得到)
import bmesh
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, "art", "textures")


# ======================================================================
# 場景設定
# ======================================================================

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()           # 舊場景的材質已經被清掉，快取也要清
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.cycles.device = "CPU"
    s.cycles.samples = 96
    s.cycles.use_denoising = True
    s.cycles.denoiser = "OPENIMAGEDENOISE"
    s.cycles.max_bounces = 4
    s.render.resolution_x = 320
    s.render.resolution_y = 240
    s.render.resolution_percentage = 100
    s.render.filter_size = 0.9            # 接近一個像素：邊緣銳利
    s.view_settings.view_transform = "Standard"
    s.view_settings.look = "None"
    s.render.image_settings.file_format = "PNG"
    world = bpy.data.worlds.new("World")
    s.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.01, 0.01, 0.015, 1)
    bg.inputs["Strength"].default_value = 1.0
    return s


def set_ambient(rgb, strength=1.0):
    bg = bpy.context.scene.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*rgb, 1)
    bg.inputs["Strength"].default_value = strength


# ======================================================================
# 材質
# ======================================================================

_mats = {}


def mat(name, tex=None, color=(0.5, 0.5, 0.5), rough=0.85, metal=0.0, emit=0.0, emit_color=None):
    """取得（或建立）材質。tex 是 art/textures/ 裡的檔名（不含 .png）。"""
    key = (name, tex, emit)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Specular IOR Level"].default_value = 0.25
    if tex:
        img_path = os.path.join(TEX, tex + ".png")
        img = bpy.data.images.load(img_path, check_existing=True)
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = img
        t.interpolation = "Closest"          # PSX：不平滑
        nt.links.new(t.outputs["Color"], p.inputs["Base Color"])
        if emit:
            nt.links.new(t.outputs["Color"], p.inputs["Emission Color"])
    else:
        p.inputs["Base Color"].default_value = (*color, 1)
    if emit:
        if emit_color is not None:
            p.inputs["Emission Color"].default_value = (*emit_color, 1)
        elif not tex:
            p.inputs["Emission Color"].default_value = (*color, 1)
        p.inputs["Emission Strength"].default_value = emit
    _mats[key] = m
    return m


# ======================================================================
# 幾何
# ======================================================================

class Kit:
    """收集場景中的物件。每個建立的物件都記錄它的標籤，給預渲染流程使用。"""

    def __init__(self):
        self.objects = []
        self.occluders = set()

    # ---------------------------------------------------- 內部：建立 mesh
    def _make(self, name, verts, faces, material, uv_size, M, occluder, smooth=False):
        me = bpy.data.meshes.new(name)
        bm = bmesh.new()
        bv = [bm.verts.new(M @ Vector(v)) for v in verts]
        for f in faces:
            try:
                bm.faces.new([bv[i] for i in f])
            except ValueError:
                pass
        bm.normal_update()
        uv = bm.loops.layers.uv.new("UVMap")
        for face in bm.faces:
            n = face.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for loop in face.loops:
                c = loop.vert.co
                if ax == 0:
                    u, v = c.y, c.z
                elif ax == 1:
                    u, v = c.x, c.z
                else:
                    u, v = c.x, c.y
                loop[uv].uv = (u / uv_size, v / uv_size)
        bm.to_mesh(me)
        bm.free()
        for poly in me.polygons:
            poly.use_smooth = smooth
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        if material is not None:
            me.materials.append(material)
        self.objects.append(ob)
        if occluder:
            self.occluders.add(ob.name)
        return ob

    # ---------------------------------------------------- 基本形狀
    def box(self, mn, mx, material, uv=2.0, M=None, occluder=False, name="box"):
        """軸對齊的盒子（在 M 的區域座標中）。mn、mx 是兩個角。"""
        M = M or Matrix()
        x0, y0, z0 = mn
        x1, y1, z1 = mx
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        return self._make(name, v, f, material, uv, M, occluder)

    def cyl(self, c, r, h, material, seg=8, uv=1.0, M=None, occluder=False, cap=True, r_top=None, name="cyl"):
        """直立的圓柱（或圓錐台，r_top）。c 是底面中心。"""
        M = M or Matrix()
        r_top = r if r_top is None else r_top
        v, f = [], []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            v.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a), c[2]))
            v.append((c[0] + r_top * math.cos(a), c[1] + r_top * math.sin(a), c[2] + h))
        for k in range(seg):
            a, b = 2 * k, 2 * ((k + 1) % seg)
            f.append((a, b, b + 1, a + 1))
        if cap:
            f.append(tuple(2 * k for k in reversed(range(seg))))
            f.append(tuple(2 * k + 1 for k in range(seg)))
        return self._make(name, v, f, material, uv, M, occluder)

    def plane(self, corners, material, uv=2.0, M=None, occluder=False, name="plane"):
        M = M or Matrix()
        return self._make(name, corners, [tuple(range(len(corners)))], material, uv, M, occluder)

    def light(self, kind, loc, color, power, radius=0.05, name="light", spot_angle=60, rot=None):
        ld = bpy.data.lights.new(name, kind)
        ld.color = color
        ld.energy = power
        if kind in ("POINT", "SPOT"):
            ld.shadow_soft_size = radius
        if kind == "SPOT":
            ld.spot_size = math.radians(spot_angle)
            ld.spot_blend = 0.4
        if kind == "AREA":
            ld.size = radius
        ob = bpy.data.objects.new(name, ld)
        ob.location = loc
        if rot:
            ob.rotation_euler = [math.radians(a) for a in rot]
        bpy.context.scene.collection.objects.link(ob)
        return ob


def T(x=0, y=0, z=0, yaw=0):
    """位移＋繞 z 軸旋轉（度）。"""
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(yaw), 4, "Z")


# ======================================================================
# 房間外殼
# ======================================================================

def room_shell(k, x0, y0, x1, y1, h, floor, wall, ceiling, wainscot=None, wainscot_h=1.1,
               skip_walls=(), thickness=0.1):
    """四面牆＋地板＋天花板。skip_walls 可以省略面向鏡頭的牆（'S','N','W','E'）。

    牆是有厚度的盒子，PSX 遊戲也常這樣做，避免光線從縫隙漏進來。
    """
    t = thickness
    k.box((x0, y0, -t), (x1, y1, 0), floor, name="floor")
    k.box((x0, y0, h), (x1, y1, h + t), ceiling, name="ceiling")
    walls = {
        "S": ((x0, y0 - t, 0), (x1, y0, h)),
        "N": ((x0, y1, 0), (x1, y1 + t, h)),
        "W": ((x0 - t, y0, 0), (x0, y1, h)),
        "E": ((x1, y0, 0), (x1 + t, y1, h)),
    }
    for key, (mn, mx) in walls.items():
        if key in skip_walls:
            continue
        if wainscot:
            lo_mx = (mx[0], mx[1], wainscot_h)
            k.box(mn, lo_mx, wainscot, uv=wainscot_h, name=f"wainscot_{key}")
            k.box((mn[0], mn[1], wainscot_h), mx, wall, name=f"wall_{key}")
            # 護牆板上緣的飾條
            dx = 0.03 if key in ("W", "E") else 0
            dy = 0.03 if key in ("S", "N") else 0
            sgn = {"S": 1, "N": -1, "W": 1, "E": -1}[key]
            k.box((mn[0] - (dx if sgn < 0 else 0), mn[1] - (dy if sgn < 0 else 0), wainscot_h - 0.03),
                  (mx[0] + (dx if sgn > 0 else 0), mx[1] + (dy if sgn > 0 else 0), wainscot_h + 0.03),
                  mat("trim", "wood_furniture"), uv=0.5, name="trim")
        else:
            k.box(mn, mx, wall, name=f"wall_{key}")


def wall_hole_box(k, axis, plane, a0, a1, z0, z1, h, mn_other, mx_other, material, hole):
    """（備用）在牆上開洞：把牆拆成洞的上、下、左、右四塊。"""
    pass


# ======================================================================
# 道具（每個函式的參數：kit、位置 x, y、朝向 yaw（度），其他選項）
# ======================================================================

def table_long(k, x, y, yaw=0, length=4.0, width=1.1, cloth=True, occluder=False):
    M = T(x, y, 0, yaw)
    wood = mat("wood_furniture", "wood_furniture")
    top_m = mat("linen", "fabric_linen") if cloth else wood
    L, W = length / 2, width / 2
    k.box((-W, -L, 0.74), (W, L, 0.8), top_m, uv=1.0, M=M, occluder=occluder, name="table_top")
    if cloth:   # 垂下來的桌巾
        k.box((-W - 0.02, -L - 0.02, 0.5), (W + 0.02, L + 0.02, 0.8), top_m, uv=1.0, M=M, occluder=occluder, name="cloth")
    for sx in (-W + 0.08, W - 0.08):
        for sy in (-L + 0.1, L - 0.1):
            k.box((sx - 0.05, sy - 0.05, 0), (sx + 0.05, sy + 0.05, 0.74), wood, uv=0.5, M=M, name="leg")


def chair(k, x, y, yaw=0, occluder=False, fabric="fabric_velvet_red"):
    M = T(x, y, 0, yaw)
    wood = mat("wood_furniture", "wood_furniture")
    seat = mat(fabric, fabric)
    k.box((-0.22, -0.22, 0.42), (0.22, 0.22, 0.5), seat, uv=0.5, M=M, occluder=occluder, name="chair_seat")
    for sx in (-0.19, 0.19):
        for sy in (-0.19, 0.19):
            k.box((sx - 0.025, sy - 0.025, 0), (sx + 0.025, sy + 0.025, 0.42), wood, uv=0.5, M=M, name="chair_leg")
    # 椅背在 -y 側（yaw 決定朝向）
    k.box((-0.22, -0.24, 0.5), (0.22, -0.19, 1.15), wood, uv=0.5, M=M, occluder=occluder, name="chair_back")
    k.box((-0.16, -0.235, 0.62), (0.16, -0.2, 1.05), seat, uv=0.5, M=M, occluder=occluder, name="chair_pad")


def armchair(k, x, y, yaw=0, occluder=True):
    M = T(x, y, 0, yaw)
    vel = mat("fabric_velvet_red", "fabric_velvet_red")
    wood = mat("wood_furniture", "wood_furniture")
    k.box((-0.42, -0.4, 0.12), (0.42, 0.4, 0.45), vel, uv=0.6, M=M, occluder=occluder, name="arm_base")
    k.box((-0.42, -0.4, 0.45), (0.42, -0.22, 1.05), vel, uv=0.6, M=M, occluder=occluder, name="arm_back")
    for sx in (-0.42, 0.3):
        k.box((sx, -0.4, 0.45), (sx + 0.12, 0.4, 0.68), vel, uv=0.6, M=M, occluder=occluder, name="arm_rest")
    for sx in (-0.36, 0.36):
        for sy in (-0.34, 0.34):
            k.box((sx - 0.03, sy - 0.03, 0), (sx + 0.03, sy + 0.03, 0.12), wood, uv=0.3, M=M, name="arm_foot")


def cabinet(k, x, y, yaw=0, w=1.0, d=0.45, h=0.9, occluder=True):
    M = T(x, y, 0, yaw)
    wood = mat("wood_furniture", "wood_furniture")
    br = mat("brass", "brass", metal=0.6, rough=0.4)
    k.box((-w / 2, -d / 2, 0.08), (w / 2, d / 2, h), wood, uv=1.0, M=M, occluder=occluder, name="cab_body")
    k.box((-w / 2 - 0.02, -d / 2 - 0.02, h), (w / 2 + 0.02, d / 2 + 0.02, h + 0.04), wood, uv=1.0, M=M, occluder=occluder, name="cab_top")
    k.box((-w / 2 + 0.03, -d / 2, 0), (w / 2 - 0.03, d / 2 - 0.03, 0.08), mat("dark", color=(0.03, 0.02, 0.015)), M=M, name="cab_kick")
    # 門板的分隔線與把手（朝 +y 正面）
    k.box((-0.005, d / 2, 0.12), (0.005, d / 2 + 0.005, h - 0.04), mat("dark", color=(0.03, 0.02, 0.015)), M=M, name="cab_gap")
    for sx in (-0.06, 0.06):
        k.box((sx - 0.012, d / 2, h * 0.55), (sx + 0.012, d / 2 + 0.02, h * 0.55 + 0.08), br, uv=0.2, M=M, name="cab_handle")


def bookshelf(k, x, y, yaw=0, w=1.6, h=2.2, d=0.4, occluder=True):
    M = T(x, y, 0, yaw)
    wood = mat("wood_furniture", "wood_furniture")
    books = mat("books", "books")
    k.box((-w / 2, -d / 2, 0), (-w / 2 + 0.05, d / 2, h), wood, uv=1, M=M, occluder=occluder, name="shelf_side")
    k.box((w / 2 - 0.05, -d / 2, 0), (w / 2, d / 2, h), wood, uv=1, M=M, occluder=occluder, name="shelf_side")
    k.box((-w / 2, -d / 2, h - 0.05), (w / 2, d / 2, h), wood, uv=1, M=M, occluder=occluder, name="shelf_top")
    k.box((-w / 2, -d / 2, 0), (w / 2, -d / 2 + 0.02, h), wood, uv=1, M=M, occluder=occluder, name="shelf_back")
    # 書：前面一整片書背貼圖（每 2 層 = 1 張貼圖高度 ≈ 1 m）
    k.box((-w / 2 + 0.05, -d / 2 + 0.02, 0.05), (w / 2 - 0.05, d / 2 - 0.06, h - 0.05), books, uv=1.0, M=M, occluder=occluder, name="shelf_books")


def desk(k, x, y, yaw=0, w=1.3, d=0.65, occluder=True):
    M = T(x, y, 0, yaw)
    wood = mat("wood_furniture", "wood_furniture")
    k.box((-w / 2, -d / 2, 0.72), (w / 2, d / 2, 0.77), wood, uv=1, M=M, occluder=occluder, name="desk_top")
    k.box((w / 2 - 0.45, -d / 2 + 0.02, 0.05), (w / 2 - 0.02, d / 2 - 0.02, 0.72), wood, uv=1, M=M, occluder=occluder, name="desk_drawers")
    for i in range(3):
        z = 0.12 + i * 0.2
        k.box((w / 2 - 0.42, d / 2 - 0.02, z), (w / 2 - 0.05, d / 2, z + 0.16), mat("wood_crate", "wood_crate"), uv=0.5, M=M, name="drawer")
    for sx, sy in ((-w / 2 + 0.05, -d / 2 + 0.05), (-w / 2 + 0.05, d / 2 - 0.05)):
        k.box((sx - 0.03, sy - 0.03, 0), (sx + 0.03, sy + 0.03, 0.72), wood, uv=0.5, M=M, name="desk_leg")


def typewriter(k, x, y, z, yaw=0):
    """打字機：機身、鍵盤斜面、滾筒、紙。這是存檔點，要一眼認得出來。"""
    M = T(x, y, z, yaw)
    body = mat("metal_typewriter", "metal_typewriter", metal=0.3, rough=0.5)
    keys = mat("keys", color=(0.75, 0.72, 0.62))
    blk = mat("black", color=(0.02, 0.02, 0.02), rough=0.4)
    k.box((-0.2, -0.14, 0), (0.2, 0.12, 0.08), body, uv=0.4, M=M, name="tw_base")
    # 鍵盤（階梯狀）
    for i in range(4):
        y0 = -0.14 + i * 0.04
        k.box((-0.17, y0 - 0.06, 0.08), (0.17, y0 - 0.02, 0.09 + i * 0.012), body, uv=0.4, M=M, name="tw_step")
        for j in range(9):
            kx = -0.15 + j * 0.0375
            k.box((kx - 0.011, y0 - 0.055, 0.09 + i * 0.012), (kx + 0.011, y0 - 0.03, 0.1 + i * 0.012), keys, uv=0.1, M=M, name="tw_key")
    k.box((-0.21, 0.04, 0.08), (0.21, 0.13, 0.13), body, uv=0.4, M=M, name="tw_top")
    # 滾筒（水平圓柱：用旋轉矩陣把直立圓柱轉成橫的）
    Mr = M @ Matrix.Translation((-0.24, 0.1, 0.16)) @ Matrix.Rotation(math.radians(90), 4, "Y")
    k.cyl((0, 0, 0), 0.03, 0.48, blk, seg=8, uv=0.2, M=Mr, name="tw_platen")
    # 紙
    k.box((-0.12, 0.08, 0.16), (0.12, 0.085, 0.34), mat("paper", "paper", emit=0.0), uv=0.3, M=M, name="tw_paper")
    k.box((0.21, 0.08, 0.15), (0.27, 0.1, 0.17), mat("chrome", color=(0.6, 0.6, 0.6), metal=0.9, rough=0.3), M=M, name="tw_lever")


def ribbon_tin(k, x, y, z):
    """色帶盒（存檔道具）。"""
    k.cyl((x, y, z), 0.045, 0.02, mat("tin", color=(0.12, 0.1, 0.08), metal=0.6, rough=0.4), seg=10, uv=0.1, name="ribbon")
    k.cyl((x, y, z + 0.02), 0.025, 0.002, mat("ribbon_red", color=(0.45, 0.05, 0.04)), seg=8, uv=0.1, name="ribbon_label")


def item_crate(k, x, y, yaw=0, occluder=True):
    """物流箱（互通的道具箱）：木頭貨箱＋金屬護角＋公司的油漆標誌。"""
    M = T(x, y, 0, yaw)
    wood = mat("wood_crate", "wood_crate")
    steel = mat("metal_rusty", "metal_rusty", metal=0.5, rough=0.6)
    w, d, h = 0.9, 0.6, 0.62
    k.box((-w / 2, -d / 2, 0), (w / 2, d / 2, h), wood, uv=0.6, M=M, occluder=occluder, name="crate")
    for sx in (-w / 2, w / 2 - 0.05):
        for sy in (-d / 2, d / 2 - 0.05):
            k.box((sx - 0.005, sy - 0.005, 0), (sx + 0.055, sy + 0.055, h + 0.005), steel, uv=0.3, M=M, name="crate_corner")
    k.box((-w / 2 - 0.01, -d / 2 - 0.01, h), (w / 2 + 0.01, d / 2 + 0.01, h + 0.03), wood, uv=0.6, M=M, occluder=occluder, name="crate_lid")
    # 正面的標誌：綠色的葉子＋白字橫條（只是油漆，不寫字，避免小字變成雜點）
    k.box((-0.3, d / 2, 0.36), (0.3, d / 2 + 0.004, 0.44), mat("paint_white", color=(0.75, 0.73, 0.66)), M=M, name="crate_band")
    k.cyl((0, d / 2 + 0.002, 0.18), 0.09, 0.004, mat("paint_green", color=(0.12, 0.35, 0.18)), seg=6, uv=0.2,
          M=M @ Matrix.Translation((0, d / 2 + 0.004, 0.2)) @ Matrix.Rotation(math.radians(90), 4, "X") @ Matrix.Translation((0, -d / 2 - 0.002, -0.18)),
          name="crate_leaf")


def candelabra(k, x, y, z, arms=3, lit=True, power=6.0):
    br = mat("brass", "brass", metal=0.7, rough=0.35)
    wax = mat("wax", color=(0.85, 0.8, 0.65), rough=0.6)
    flame = mat("flame", color=(1.0, 0.65, 0.25), emit=40.0)
    k.cyl((x, y, z), 0.07, 0.02, br, seg=8, uv=0.2, name="cand_base")
    k.cyl((x, y, z), 0.012, 0.3, br, seg=6, uv=0.2, name="cand_stem")
    xs = [0] if arms == 1 else [-0.12, 0, 0.12][:arms]
    for dx in xs:
        k.box((x + min(0, dx), y - 0.008, z + 0.28), (x + max(0, dx) + 0.001, y + 0.008, z + 0.295), br, uv=0.2, name="cand_arm")
        k.cyl((x + dx, y, z + 0.29), 0.015, 0.11, wax, seg=6, uv=0.2, name="candle")
        if lit:
            k.cyl((x + dx, y, z + 0.4), 0.006, 0.03, flame, seg=4, uv=0.2, cap=True, r_top=0.001, name="flame")
    if lit:
        k.light("POINT", (x, y, z + 0.45), (1.0, 0.62, 0.3), power, radius=0.05, name="candle_light")


def chandelier(k, x, y, z, lit=True, power=60.0, r=0.8):
    br = mat("brass", "brass", metal=0.7, rough=0.35)
    flame = mat("flame", color=(1.0, 0.7, 0.35), emit=30.0)
    k.cyl((x, y, z), 0.015, 1.2, mat("chain", color=(0.05, 0.04, 0.03), metal=0.8), seg=4, uv=0.2, name="chain")
    k.cyl((x, y, z - 0.1), r, 0.06, br, seg=12, uv=0.5, cap=False, name="ring")
    k.cyl((x, y, z - 0.35), 0.06, 0.4, br, seg=6, uv=0.2, r_top=0.12, name="chand_body")
    for i in range(8):
        a = 2 * math.pi * i / 8
        cx, cy = x + r * math.cos(a), y + r * math.sin(a)
        k.cyl((cx, cy, z - 0.04), 0.012, 0.09, mat("wax", color=(0.85, 0.8, 0.65)), seg=4, uv=0.2, name="ch_candle")
        if lit:
            k.cyl((cx, cy, z + 0.05), 0.006, 0.03, flame, seg=4, uv=0.2, r_top=0.001, name="ch_flame")
    if lit:
        k.light("POINT", (x, y, z), (1.0, 0.68, 0.38), power, radius=0.6, name="chandelier_light")


def fireplace(k, x, y, yaw=0, lit=True, power=40.0, occluder=False):
    """壁爐：石框＋爐膛＋爐台。y 是貼牆的那一側。"""
    M = T(x, y, 0, yaw)
    stone = mat("wall_stone", "wall_stone")
    marble = mat("marble", "floor_marble_checker")
    black = mat("soot", color=(0.015, 0.012, 0.01))
    k.box((-1.0, -0.5, 0), (-0.6, 0, 1.3), stone, uv=1, M=M, occluder=occluder, name="fp_l")
    k.box((0.6, -0.5, 0), (1.0, 0, 1.3), stone, uv=1, M=M, occluder=occluder, name="fp_r")
    k.box((-1.0, -0.5, 1.0), (1.0, 0, 1.3), stone, uv=1, M=M, occluder=occluder, name="fp_lintel")
    k.box((-1.15, -0.6, 1.3), (1.15, 0.0, 1.4), mat("wood_furniture", "wood_furniture"), uv=1, M=M, name="fp_mantel")
    k.box((-0.6, -0.1, 0), (0.6, 0, 1.0), black, M=M, name="fp_back")
    k.box((-1.1, -0.9, 0), (1.1, -0.5, 0.04), stone, uv=1, M=M, name="fp_hearth")
    if lit:
        fire = mat("fire", color=(1.0, 0.45, 0.12), emit=25.0)
        for i, dx in enumerate((-0.25, 0, 0.22)):
            k.cyl((dx, -0.3, 0.04), 0.1, 0.25 + 0.08 * (i == 1), fire, seg=5, r_top=0.01, uv=0.2, M=M, name="flame")
        p = M @ Vector((0, -0.7, 0.5))
        k.light("POINT", tuple(p), (1.0, 0.5, 0.2), power, radius=0.3, name="fire_light")
    for dx in (-0.3, 0.3):   # 柴架
        k.box((dx - 0.02, -0.4, 0.04), (dx + 0.02, -0.15, 0.08), mat("iron", color=(0.04, 0.04, 0.04), metal=0.8), M=M, name="andiron")


def grandfather_clock(k, x, y, yaw=0, occluder=True):
    M = T(x, y, 0, yaw)
    wood = mat("wood_furniture", "wood_furniture")
    face = mat("clockface", color=(0.75, 0.7, 0.55), rough=0.5)
    br = mat("brass", "brass", metal=0.7, rough=0.35)
    k.box((-0.3, -0.2, 0), (0.3, 0.2, 0.35), wood, uv=0.8, M=M, occluder=occluder, name="clk_base")
    k.box((-0.22, -0.16, 0.35), (0.22, 0.16, 1.55), wood, uv=0.8, M=M, occluder=occluder, name="clk_trunk")
    k.box((-0.28, -0.2, 1.55), (0.28, 0.2, 2.15), wood, uv=0.8, M=M, occluder=occluder, name="clk_hood")
    k.box((-0.32, -0.22, 2.15), (0.32, 0.22, 2.25), wood, uv=0.8, M=M, occluder=occluder, name="clk_crown")
    k.box((-0.18, 0.2, 1.63), (0.18, 0.205, 2.0), face, M=M, name="clk_face")
    k.box((-0.005, 0.205, 1.8), (0.005, 0.21, 1.95), mat("black", color=(0.02, 0.02, 0.02)), M=M, name="clk_hand")
    k.box((-0.005, 0.205, 1.72), (0.09, 0.21, 1.73), mat("black", color=(0.02, 0.02, 0.02)), M=M, name="clk_hand")
    k.box((-0.12, 0.16, 0.6), (0.12, 0.165, 1.4), mat("glass_dark", color=(0.02, 0.02, 0.025), rough=0.15), M=M, name="clk_glass")
    k.cyl((0, 0.17, 0.75), 0.08, 0.01, br, seg=10, uv=0.2,
          M=M @ Matrix.Translation((0, 0.165, 0.75)) @ Matrix.Rotation(math.radians(-90), 4, "X") @ Matrix.Translation((0, -0.17, -0.75)),
          name="clk_pendulum")


def painting(k, x, y, z, yaw=0, w=0.9, h=1.1, tex="painting_dark"):
    """掛在牆上的畫：y 方向是牆的法線（畫朝 +y）。"""
    M = T(x, y, z, yaw)
    gold = mat("gold_frame", "brass", metal=0.6, rough=0.45)
    k.box((-w / 2 - 0.08, 0, -h / 2 - 0.08), (w / 2 + 0.08, 0.05, h / 2 + 0.08), gold, uv=0.3, M=M, name="frame")
    k.box((-w / 2, 0.05, -h / 2), (w / 2, 0.055, h / 2), mat(tex, tex), uv=max(w, h), M=M, name="canvas")


def door(k, x, y, yaw=0, w=1.0, h=2.2, double=False, tex="wood_furniture"):
    """門（只是外觀，貼在牆上）。門朝 +y。"""
    M = T(x, y, 0, yaw)
    wood = mat("door_" + tex, tex)
    frame = mat("wood_furniture", "wood_furniture")
    br = mat("brass", "brass", metal=0.7, rough=0.35)
    W = w if not double else w * 2
    k.box((-W / 2 - 0.12, -0.02, 0), (-W / 2, 0.08, h + 0.12), frame, uv=1, M=M, name="door_frame")
    k.box((W / 2, -0.02, 0), (W / 2 + 0.12, 0.08, h + 0.12), frame, uv=1, M=M, name="door_frame")
    k.box((-W / 2 - 0.12, -0.02, h), (W / 2 + 0.12, 0.08, h + 0.2), frame, uv=1, M=M, name="door_frame")
    leaves = [(-W / 2, W / 2)] if not double else [(-W / 2, 0), (0, W / 2)]
    for (a, b) in leaves:
        k.box((a + 0.01, 0, 0), (b - 0.01, 0.05, h), wood, uv=1.2, M=M, name="door_leaf")
        # 兩塊凹板
        for (z0, z1) in ((0.15, 0.95), (1.15, h - 0.15)):
            k.box((a + 0.12, 0.05, z0), (b - 0.12, 0.06, z1), mat("wood_dark_panel", "wainscot_dark"), uv=1.2, M=M, name="door_panel")
        hx = b - 0.1 if (a, b) == leaves[0] else a + 0.1
        k.cyl((hx, 0.06, 1.0), 0.025, 0.05, br, seg=6, uv=0.1,
              M=M @ Matrix.Translation((hx, 0.06, 1.0)) @ Matrix.Rotation(math.radians(-90), 4, "X") @ Matrix.Translation((-hx, -0.06, -1.0)),
              name="door_knob")


def window(k, x, y, z, yaw=0, w=1.1, h=1.8, moon=True, power=30.0, curtains=True):
    """窗戶：窗框＋格子＋窗外的月光（發光面）＋一盞冷色的區域光。窗朝 +y（室內）。"""
    M = T(x, y, z, yaw)
    frame = mat("wood_furniture", "wood_furniture")
    sky = mat("night_sky", color=(0.12, 0.17, 0.3), emit=1.2 if moon else 0.15)
    k.box((-w / 2, -0.05, 0), (w / 2, 0.0, h), sky, M=M, name="window_sky")
    for dx in (-w / 2, -0.03, w / 2 - 0.06):
        k.box((dx, -0.02, 0), (dx + 0.06, 0.06, h), frame, uv=1, M=M, name="mullion")
    for dz in (0, h * 0.5, h - 0.06):
        k.box((-w / 2, -0.02, dz), (w / 2, 0.06, dz + 0.06), frame, uv=1, M=M, name="transom")
    k.box((-w / 2 - 0.08, 0.0, -0.06), (w / 2 + 0.08, 0.16, 0.0), frame, uv=1, M=M, name="sill")
    if curtains:
        cur = mat("fabric_curtain_green", "fabric_curtain_green")
        for sx in (-1, 1):
            x0 = sx * (w / 2 + 0.02)
            x1 = sx * (w / 2 + 0.3)
            k.box((min(x0, x1), 0.05, -0.2), (max(x0, x1), 0.15, h + 0.3), cur, uv=1, M=M, name="curtain")
    if moon:
        p = M @ Vector((0, 0.4, h * 0.6))
        k.light("AREA", tuple(p), (0.55, 0.65, 1.0), power, radius=w, name="moonlight",
                rot=(90 - 25, 0, yaw + 180))


def wall_sconce(k, x, y, z, yaw=0, power=15.0):
    M = T(x, y, z, yaw)
    br = mat("brass", "brass", metal=0.7, rough=0.35)
    glow = mat("lamp_glow", color=(1.0, 0.8, 0.5), emit=12.0)
    k.box((-0.06, 0, -0.1), (0.06, 0.03, 0.1), br, uv=0.2, M=M, name="sconce_plate")
    k.box((-0.015, 0.03, -0.02), (0.015, 0.15, 0.01), br, uv=0.2, M=M, name="sconce_arm")
    k.cyl((0, 0.15, 0.01), 0.06, 0.12, glow, seg=6, uv=0.2, r_top=0.04, M=M, name="sconce_shade")
    p = M @ Vector((0, 0.25, 0.08))
    k.light("POINT", tuple(p), (1.0, 0.72, 0.42), power, radius=0.08, name="sconce_light")


def desk_lamp(k, x, y, z, power=12.0):
    green = mat("lamp_green", color=(0.05, 0.25, 0.12), rough=0.3)
    br = mat("brass", "brass", metal=0.7, rough=0.35)
    k.cyl((x, y, z), 0.08, 0.02, br, seg=8, uv=0.2, name="lamp_base")
    k.cyl((x, y, z), 0.01, 0.32, br, seg=4, uv=0.2, name="lamp_stem")
    k.cyl((x, y + 0.08, z + 0.26), 0.13, 0.08, green, seg=8, uv=0.2, r_top=0.06, name="lamp_shade")
    k.cyl((x, y + 0.08, z + 0.255), 0.11, 0.004, mat("lamp_glow", color=(1.0, 0.85, 0.55), emit=15.0), seg=8, uv=0.2, name="lamp_bulb")
    k.light("SPOT", (x, y + 0.08, z + 0.25), (1.0, 0.82, 0.55), power * 6, radius=0.05, name="desk_lamp",
            spot_angle=110, rot=(0, 0, 0))
    k.light("POINT", (x, y + 0.08, z + 0.35), (1.0, 0.8, 0.5), power * 0.4, radius=0.1, name="desk_lamp_fill")


def plant_pot(k, x, y, scale=1.0, occluder=True):
    pot = mat("terracotta", color=(0.35, 0.16, 0.08))
    leaf = mat("leaf", color=(0.05, 0.16, 0.06), rough=0.6)
    s = scale
    k.cyl((x, y, 0), 0.2 * s, 0.4 * s, pot, seg=8, uv=0.4, r_top=0.25 * s, occluder=occluder, name="pot")
    import random
    rnd = random.Random(int(x * 100 + y * 7))
    for i in range(9):
        a = 2 * math.pi * i / 9 + rnd.random() * 0.4
        tilt = 0.5 + rnd.random() * 0.4
        Ml = (Matrix.Translation((x, y, 0.38 * s)) @ Matrix.Rotation(a, 4, "Z") @ Matrix.Rotation(tilt, 4, "X"))
        k.box((-0.05 * s, -0.01, 0), (0.05 * s, 0.01, 0.75 * s * (0.7 + rnd.random() * 0.5)), leaf, uv=0.3, M=Ml,
              occluder=occluder, name="leaf")


def bust_pedestal(k, x, y, yaw=0, occluder=True):
    """大理石台座＋石膏胸像（創辦人的半身像）。"""
    M = T(x, y, 0, yaw)
    marble = mat("marble_ped", "marble_white", rough=0.35)
    k.box((-0.22, -0.22, 0), (0.22, 0.22, 0.08), marble, M=M, occluder=occluder, name="ped_base")
    k.box((-0.16, -0.16, 0.08), (0.16, 0.16, 1.05), marble, M=M, occluder=occluder, name="ped_col")
    k.box((-0.22, -0.22, 1.05), (0.22, 0.22, 1.12), marble, M=M, occluder=occluder, name="ped_top")
    k.box((-0.2, -0.1, 1.12), (0.2, 0.1, 1.3), marble, M=M, occluder=occluder, name="bust_chest")
    k.cyl((0, 0, 1.3), 0.05, 0.08, marble, seg=6, M=M, occluder=occluder, name="bust_neck")
    k.cyl((0, 0.01, 1.38), 0.09, 0.2, marble, seg=8, r_top=0.07, M=M, occluder=occluder, name="bust_head")


def rug(k, x0, y0, x1, y1, tex="carpet_red", z=0.005):
    k.box((x0, y0, 0), (x1, y1, z), mat(tex, tex), uv=1.5, name="rug")


def pillar(k, x, y, h, r=0.3, occluder=True):
    marble = mat("marble_col", "marble_white", rough=0.35)
    k.box((x - r - 0.08, y - r - 0.08, 0), (x + r + 0.08, y + r + 0.08, 0.25), marble, occluder=occluder, name="pillar_base")
    k.cyl((x, y, 0.25), r, h - 0.5, marble, seg=10, uv=1, occluder=occluder, name="pillar")
    k.box((x - r - 0.1, y - r - 0.1, h - 0.25), (x + r + 0.1, y + r + 0.1, h), marble, occluder=occluder, name="pillar_cap")


def staircase(k, x, y, w, rise, run, steps, yaw=0, carpet_tex="carpet_red", rail=True, occluder=False):
    """直線樓梯：從 (x, y) 往 +y 方向往上。"""
    M = T(x, y, 0, yaw)
    stone = mat("marble_stair", "marble_white", rough=0.4)
    carpet = mat(carpet_tex, carpet_tex)
    wood = mat("wood_furniture", "wood_furniture")
    for i in range(steps):
        z = (i + 1) * rise
        k.box((-w / 2, i * run, 0), (w / 2, (i + 1) * run, z), stone, uv=1, M=M, occluder=occluder, name="step")
        k.box((-w / 2 + 0.25, i * run - 0.005, z - 0.005), (w / 2 - 0.25, (i + 1) * run, z + 0.01), carpet, uv=1, M=M, name="step_carpet")
    if rail:
        top = steps * rise
        L = steps * run
        for sx in (-w / 2 + 0.04, w / 2 - 0.04):
            for i in range(0, steps, 2):
                z = (i + 1) * rise
                k.box((sx - 0.02, i * run + run / 2 - 0.02, z), (sx + 0.02, i * run + run / 2 + 0.02, z + 0.9), wood, uv=0.5, M=M, name="baluster")
            # 斜的扶手：用一個傾斜的盒子
            ang = math.atan2(top, L)
            Mrail = M @ Matrix.Translation((sx, 0, rise + 0.9)) @ Matrix.Rotation(ang, 4, "X")
            k.box((-0.04, 0, -0.04), (0.04, math.hypot(top, L), 0.04), wood, uv=0.5, M=Mrail, occluder=occluder, name="handrail")


def honor_wall(k, x, y, z, yaw=0, filled=0):
    """榮譽之牆：四個獎章的嵌槽（主線大鎖）。filled = 已經放回去的數量。"""
    M = T(x, y, z, yaw)
    wood = mat("wood_furniture", "wood_furniture")
    br = mat("brass", "brass", metal=0.7, rough=0.35)
    k.box((-0.9, 0, -0.5), (0.9, 0.08, 0.5), wood, uv=1, M=M, name="honor_board")
    k.box((-0.95, 0, 0.5), (0.95, 0.12, 0.6), wood, uv=1, M=M, name="honor_cornice")
    pins = [(0.55, 0.55, 0.6), (0.85, 0.7, 0.25), (0.82, 0.82, 0.85), (0.6, 0.85, 0.95)]   # 銀、金、白金、鑽石
    for i in range(4):
        cx = -0.6 + i * 0.4
        k.cyl((cx, 0.08, 0), 0.13, 0.02, br, seg=10, uv=0.2,
              M=M @ Matrix.Translation((cx, 0.08, 0)) @ Matrix.Rotation(math.radians(-90), 4, "X") @ Matrix.Translation((-cx, -0.08, 0)),
              name="honor_ring")
        col = pins[i] if i < filled else (0.02, 0.02, 0.02)
        k.cyl((cx, 0.08, 0), 0.09, 0.025, mat(f"pin{i}_{i < filled}", color=col, metal=0.9 if i < filled else 0, rough=0.3), seg=8, uv=0.2,
              M=M @ Matrix.Translation((cx, 0.081, 0)) @ Matrix.Rotation(math.radians(-90), 4, "X") @ Matrix.Translation((-cx, -0.081, 0)),
              name="honor_pin")
    k.box((-0.5, 0.08, -0.42), (0.5, 0.09, -0.3), br, uv=0.3, M=M, name="honor_plaque")


def cot(k, x, y, yaw=0, occluder=True):
    """行軍床（安全房）。"""
    M = T(x, y, 0, yaw)
    steel = mat("metal_steel", "metal_steel", metal=0.6, rough=0.5)
    canvas = mat("fabric_linen", "fabric_linen")
    k.box((-0.4, -0.95, 0.38), (0.4, 0.95, 0.45), canvas, uv=1, M=M, occluder=occluder, name="cot_bed")
    for sx in (-0.38, 0.38):
        for sy in (-0.9, 0.9):
            k.box((sx - 0.02, sy - 0.02, 0), (sx + 0.02, sy + 0.02, 0.4), steel, uv=0.3, M=M, name="cot_leg")
    k.box((-0.32, 0.6, 0.45), (0.32, 0.9, 0.58), mat("pillow", color=(0.6, 0.58, 0.52)), M=M, name="pillow")
    k.box((-0.4, -0.5, 0.45), (0.4, 0.2, 0.5), mat("blanket", "fabric_curtain_green"), uv=1, M=M, name="blanket")


def boxes_stack(k, x, y, yaw=0, occluder=True):
    """紙箱堆（當日到貨的箱子，安全房和走廊的雜物）。"""
    M = T(x, y, 0, yaw)
    card = mat("cardboard", color=(0.42, 0.32, 0.2), rough=0.9)
    tape = mat("tape", color=(0.55, 0.45, 0.28), rough=0.4)
    for (a, b, h, z) in ((-0.35, 0.0, 0.4, 0), (0.0, 0.4, 0.4, 0), (-0.2, 0.2, 0.35, 0.4)):
        k.box((a, -0.25, z), (b, 0.25, z + h), card, uv=0.6, M=M, occluder=occluder, name="cbox")
        k.box((a + (b - a) / 2 - 0.03, -0.255, z), (a + (b - a) / 2 + 0.03, 0.255, z + h + 0.002), tape, M=M, name="ctape")
