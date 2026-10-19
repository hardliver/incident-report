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

# 這個場景裡擺了哪些門（位置、方向、寬度）。bake_room.py 寫進 room.json 的 door_props，
# 打包時沒有對應到「真的門」的，就變成「鎖住的門」：玩家看得到的門，調查時一定有反應
DOOR_PROPS = []


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()           # 舊場景的材質已經被清掉，快取也要清
    DOOR_PROPS.clear()
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
    if floor is not None:          # floor=None：自己鋪地板（例如泳池要在地上挖洞）
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
    if cloth:   # 垂下來的桌巾（取代桌板；兩個面重疊在同一高度會互相遮光而變黑）
        k.box((-W - 0.02, -L - 0.02, 0.5), (W + 0.02, L + 0.02, 0.8), top_m, uv=1.0, M=M, occluder=occluder, name="cloth")
    else:
        k.box((-W, -L, 0.74), (W, L, 0.8), top_m, uv=1.0, M=M, occluder=occluder, name="table_top")
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


def door(k, x, y, yaw=0, w=1.0, h=2.2, double=False, tex="wood_furniture", z=0.0):
    """門（只是外觀，貼在牆上）。門朝 +y。z：門底的高度（二樓的門）。"""
    M = T(x, y, z, yaw)
    DOOR_PROPS.append({"x": x, "y": y, "z": z, "yaw": yaw, "w": w * 2 if double else w})
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


# ======================================================================
# 第二批道具（2026-10-19）
# ======================================================================

def coat(k, x, y, z, yaw=0, tex="fabric_curtain_green", length=1.0):
    """掛著的大衣：肩膀＋往下的長方塊，略微展開。z 是衣架鉤子的高度。"""
    M = T(x, y, z, yaw)
    m = mat("coat_" + tex, tex)
    k.box((-0.22, -0.06, -0.12), (0.22, 0.06, 0.0), m, uv=0.6, M=M, name="coat_shoulder")
    k.cyl((0, 0, -length), 0.24, length - 0.1, m, seg=6, uv=0.6, r_top=0.2, M=M @ Matrix.Diagonal((1, 0.45, 1, 1)), name="coat_body")


def coat_rack_rail(k, x0, x1, y, z=1.75):
    """衣帽間的掛衣桿（橫桿＋兩根立柱）。"""
    br = mat("brass", "brass", metal=0.7, rough=0.35)
    k.box((x0, y - 0.015, z - 0.015), (x1, y + 0.015, z + 0.015), br, uv=0.3, name="rail")
    for x in (x0, x1):
        k.box((x - 0.02, y - 0.02, 0), (x + 0.02, y + 0.02, z), br, uv=0.3, name="rail_post")


def counter(k, x, y, yaw=0, w=2.0, occluder=True):
    """櫃台（衣帽間的寄物櫃台）：檯面＋前板＋服務鈴。"""
    M = T(x, y, 0, yaw)
    wood = mat("wood_furniture", "wood_furniture")
    panel = mat("wood_dark_panel", "wainscot_dark")
    k.box((-w / 2, -0.3, 0), (w / 2, 0.3, 1.0), panel, uv=1.0, M=M, occluder=occluder, name="counter_body")
    k.box((-w / 2 - 0.04, -0.34, 1.0), (w / 2 + 0.04, 0.34, 1.05), wood, uv=1, M=M, occluder=occluder, name="counter_top")
    br = mat("brass", "brass", metal=0.8, rough=0.3)
    k.cyl((0.4, 0, 1.05), 0.05, 0.04, br, seg=8, uv=0.2, r_top=0.01, M=M, name="bell")


def tag_board(k, x, y, z, yaw=0, rows=4, cols=6, missing=()):
    """號碼牌板：一格一格的小鉤子，掛著黃銅號碼牌。missing 是空著的格子。"""
    M = T(x, y, z, yaw)
    wood = mat("wood_furniture", "wood_furniture")
    br = mat("brass", "brass", metal=0.7, rough=0.4)
    w, h = cols * 0.12, rows * 0.14
    k.box((-w / 2 - 0.05, 0, -0.05), (w / 2 + 0.05, 0.03, h + 0.05), wood, uv=0.6, M=M, name="tagboard")
    for r in range(rows):
        for c in range(cols):
            if (r, c) in missing:
                continue
            cx = -w / 2 + 0.06 + c * 0.12
            cz = 0.04 + r * 0.14
            k.box((cx - 0.03, 0.03, cz), (cx + 0.03, 0.04, cz + 0.07), br, uv=0.2, M=M, name="tag")


def umbrella_stand(k, x, y):
    m = mat("brass", "brass", metal=0.6, rough=0.4)
    k.cyl((x, y, 0), 0.14, 0.55, m, seg=8, uv=0.4, cap=False, occluder=True, name="umb_stand")
    for i, c in enumerate(((0.02, 0.02, 0.02), (0.15, 0.03, 0.03), (0.05, 0.05, 0.1))):
        ang = i * 2.1
        Mi = Matrix.Translation((x + 0.05 * math.cos(ang), y + 0.05 * math.sin(ang), 0.1)) @ Matrix.Rotation(0.12, 4, "X")
        k.cyl((0, 0, 0), 0.04, 0.85, mat(f"umb{i}", color=c, rough=0.5), seg=6, uv=0.3, r_top=0.015, M=Mi, name="umbrella")


def cloche_plate(k, x, y, z, open_=False):
    """餐盤＋保溫蓋（銀色圓頂）。"""
    plate = mat("china", color=(0.75, 0.73, 0.68), rough=0.3)
    silver = mat("silver", color=(0.6, 0.6, 0.62), metal=0.9, rough=0.3)
    k.cyl((x, y, z), 0.15, 0.015, plate, seg=10, uv=0.2, name="plate")
    if not open_:
        k.cyl((x, y, z + 0.015), 0.13, 0.11, silver, seg=10, uv=0.2, r_top=0.03, name="cloche")
        k.cyl((x, y, z + 0.125), 0.015, 0.02, silver, seg=6, uv=0.1, name="cloche_knob")
    else:
        # 打開的：裡面是發黑的食物
        k.cyl((x, y, z + 0.015), 0.09, 0.05, mat("rotten_food", color=(0.12, 0.1, 0.05), rough=0.9), seg=7, uv=0.2, r_top=0.05, name="food")


def name_card(k, x, y, z, yaw=0):
    """桌上的名牌（折起來的小卡片）。"""
    M = T(x, y, z, yaw)
    card = mat("card", color=(0.8, 0.77, 0.68), rough=0.6)
    for sgn in (1, -1):
        Mt = M @ Matrix.Rotation(math.radians(20 * sgn), 4, "X")
        k.box((-0.05, -0.002 * sgn, 0), (0.05, 0.002 * sgn + 0.0001, 0.05), card, uv=0.1, M=Mt, name="namecard")


def patrol_car(k, x, y, yaw=0, lights_on=True, occluder=True):
    """柯爾的郡警巡邏車（1990 年代的四門轎車，低多邊形）：車身、車窗、車輪、警示燈、頭燈。

    車頭朝 -y（yaw 決定方向）。
    """
    M = T(x, y, 0, yaw)
    body = mat("car_white", color=(0.62, 0.6, 0.55), rough=0.35, metal=0.2)
    door = mat("car_green", color=(0.08, 0.14, 0.1), rough=0.4, metal=0.2)       # 郡警的深綠色車門
    glass = mat("car_glass", color=(0.02, 0.025, 0.03), rough=0.1, metal=0.3)
    tire = mat("tire", color=(0.02, 0.02, 0.02), rough=0.8)
    chrome = mat("chrome", color=(0.6, 0.6, 0.6), metal=0.9, rough=0.3)
    k.box((-0.88, -2.45, 0.3), (0.88, 2.45, 0.85), body, uv=1, M=M, occluder=occluder, name="car_body")
    k.box((-0.89, -0.9, 0.35), (0.89, 1.0, 0.8), door, uv=1, M=M, occluder=occluder, name="car_doors")
    # 車廂（略窄、前後傾斜：用兩個盒子近似）
    k.box((-0.78, -0.75, 0.85), (0.78, 1.15, 1.32), glass, uv=1, M=M, occluder=occluder, name="car_cabin")
    k.box((-0.8, -0.55, 1.32), (0.8, 0.95, 1.38), body, uv=1, M=M, occluder=occluder, name="car_roof")
    # 警示燈（紅藍）
    red = mat("lightbar_red", color=(0.9, 0.05, 0.03), emit=8.0 if lights_on else 0.0)
    blue = mat("lightbar_blue", color=(0.05, 0.15, 1.0), emit=8.0 if lights_on else 0.0)
    k.box((-0.55, -0.05, 1.38), (-0.02, 0.15, 1.48), red, M=M, name="lightbar_r")
    k.box((0.02, -0.05, 1.38), (0.55, 0.15, 1.48), blue, M=M, name="lightbar_b")
    # 車輪
    for sx in (-0.82, 0.82):
        for sy in (-1.5, 1.6):
            Mw = M @ Matrix.Translation((sx, sy, 0.32)) @ Matrix.Rotation(math.radians(90), 4, "Y") @ Matrix.Translation((0, 0, -0.11))
            k.cyl((0, 0, 0), 0.32, 0.22, tire, seg=8, uv=0.3, M=Mw, name="wheel")
    # 保險桿、頭燈、尾燈
    k.box((-0.9, -2.55, 0.3), (0.9, -2.45, 0.45), chrome, M=M, name="bumper_f")
    k.box((-0.9, 2.45, 0.3), (0.9, 2.55, 0.45), chrome, M=M, name="bumper_r")
    head = mat("headlight", color=(1.0, 0.95, 0.8), emit=12.0 if lights_on else 0.0)
    tail = mat("taillight", color=(0.7, 0.02, 0.02), emit=4.0 if lights_on else 0.0)
    for sx in (-0.62, 0.62):
        k.box((sx - 0.18, -2.47, 0.55), (sx + 0.18, -2.44, 0.72), head, M=M, name="headlight")
        k.box((sx - 0.18, 2.44, 0.6), (sx + 0.18, 2.47, 0.75), tail, M=M, name="taillight")
    if lights_on:
        for sx in (-0.62, 0.62):
            p = M @ Vector((sx, -2.6, 0.65))
            k.light("SPOT", tuple(p), (1.0, 0.95, 0.82), 400, radius=0.08, name="headbeam", spot_angle=55,
                    rot=(90 - 6, 0, yaw + 180))
        k.light("POINT", tuple(M @ Vector((-0.3, 0.05, 1.7))), (1.0, 0.1, 0.05), 25, radius=0.1, name="bar_red")
        k.light("POINT", tuple(M @ Vector((0.3, 0.05, 1.7))), (0.1, 0.25, 1.0), 25, radius=0.1, name="bar_blue")


def tree(k, x, y, h=7.0, occluder=True, dead=False):
    """樹：樹幹＋三層錐體樹冠（冬天的針葉樹）或光禿的枝幹。"""
    bark = mat("bark", color=(0.08, 0.06, 0.045), rough=0.9)
    k.cyl((x, y, 0), 0.22, h * 0.5, bark, seg=6, uv=0.5, r_top=0.12, occluder=occluder, name="trunk")
    if dead:
        for i in range(5):
            a = i * 1.3
            Mb = Matrix.Translation((x, y, h * (0.3 + 0.1 * i))) @ Matrix.Rotation(a, 4, "Z") @ Matrix.Rotation(0.9, 4, "X")
            k.cyl((0, 0, 0), 0.06, h * 0.35, bark, seg=4, uv=0.3, r_top=0.01, M=Mb, occluder=occluder, name="branch")
        return
    leaf = mat("pine", color=(0.02, 0.05, 0.03), rough=0.9)
    for i, (z, r, hh) in enumerate(((0.25, 1.6, 0.4), (0.5, 1.2, 0.35), (0.72, 0.75, 0.3))):
        k.cyl((x, y, h * z), r, h * hh, leaf, seg=7, uv=1, r_top=0.05, occluder=occluder, name="crown")


def lamp_post(k, x, y, h=3.0, power=80.0, occluder=True):
    iron = mat("iron", color=(0.04, 0.04, 0.04), metal=0.8, rough=0.5)
    glow = mat("lantern_glass", color=(0.9, 0.62, 0.32), emit=2.5)
    k.cyl((x, y, 0), 0.08, h, iron, seg=6, uv=0.5, r_top=0.05, occluder=occluder, name="post")
    k.box((x - 0.15, y - 0.15, h), (x + 0.15, y + 0.15, h + 0.35), glow, uv=0.3, name="lantern")
    k.box((x - 0.18, y - 0.18, h + 0.35), (x + 0.18, y + 0.18, h + 0.42), iron, uv=0.3, name="lantern_cap")
    k.light("POINT", (x, y, h + 0.15), (1.0, 0.75, 0.45), power, radius=0.15, name="post_light")


def steps(k, x0, x1, y0, n, rise, run, material=None, occluder=False):
    """寬的戶外階梯：從 y0 往 +y 上升。"""
    m = material or mat("stone_step", "floor_stone")
    for i in range(n):
        k.box((x0, y0 + i * run, 0), (x1, y0 + (n + 1) * run, (i + 1) * rise), m, uv=1.5, occluder=occluder, name="step")


# ======================================================================
# 第三批道具：廚房、冷凍庫、圖書室、配膳室（2026-10-19）
# ======================================================================

def kitchen_counter(k, x, y, yaw=0, w=2.0, d=0.65, occluder=True):
    """流理台：櫥櫃＋石材檯面。正面朝 +y。"""
    M = T(x, y, 0, yaw)
    k.box((-w / 2, -d / 2, 0.08), (w / 2, d / 2, 0.88), mat("wood_crate", "wood_crate"), uv=0.8, M=M, occluder=occluder, name="cnt_body")
    k.box((-w / 2 - 0.02, -d / 2, 0.88), (w / 2 + 0.02, d / 2 + 0.03, 0.93), mat("marble_dark", "marble_dark", rough=0.4), uv=1, M=M, occluder=occluder, name="cnt_top")
    k.box((-w / 2, -d / 2 + 0.03, 0), (w / 2, d / 2 - 0.05, 0.08), mat("dark", color=(0.03, 0.02, 0.015)), M=M, name="cnt_kick")
    n = max(1, int(w / 0.5))
    for i in range(n):
        cx = -w / 2 + (i + 0.5) * w / n
        k.box((cx - 0.005, d / 2, 0.12), (cx + 0.005, d / 2 + 0.005, 0.84), mat("dark", color=(0.03, 0.02, 0.015)), M=M, name="cnt_gap")
        k.box((cx + 0.05, d / 2, 0.74), (cx + 0.12, d / 2 + 0.02, 0.76), mat("brass", "brass", metal=0.7), M=M, name="cnt_handle")


def stove(k, x, y, yaw=0, occluder=True):
    """業務用瓦斯爐：爐台、四個爐口、烤箱門、後面接到牆上的瓦斯管（主廚戰：射爆它）。"""
    M = T(x, y, 0, yaw)
    steel = mat("metal_steel", "metal_steel", metal=0.6, rough=0.45)
    black = mat("iron", color=(0.03, 0.03, 0.03), metal=0.7, rough=0.5)
    k.box((-0.6, -0.4, 0.0), (0.6, 0.4, 0.9), steel, uv=0.8, M=M, occluder=occluder, name="stove_body")
    k.box((-0.6, -0.4, 0.9), (0.6, 0.4, 0.94), black, M=M, occluder=occluder, name="stove_top")
    for bx in (-0.3, 0.3):
        for by in (-0.15, 0.15):
            k.cyl((bx, by, 0.94), 0.11, 0.03, black, seg=8, uv=0.2, M=M, cap=False, name="burner")
    k.box((-0.45, 0.4, 0.12), (0.45, 0.42, 0.65), mat("glass_dark", color=(0.02, 0.02, 0.025), rough=0.15), M=M, name="oven_door")
    k.box((-0.4, 0.42, 0.68), (0.4, 0.45, 0.71), mat("chrome", color=(0.6, 0.6, 0.6), metal=0.9, rough=0.3), M=M, name="oven_handle")
    k.box((-0.6, -0.42, 0.94), (0.6, -0.36, 1.5), steel, uv=0.8, M=M, occluder=occluder, name="stove_back")
    # 瓦斯管（黃色）：從爐子背後到牆上
    gas = mat("gas_pipe", color=(0.6, 0.45, 0.05), metal=0.4, rough=0.5)
    k.box((0.45, -0.45, 0.2), (0.5, -0.4, 1.7), gas, M=M, name="gas_pipe")
    k.box((0.42, -0.47, 1.4), (0.53, -0.38, 1.48), mat("valve_red", color=(0.55, 0.05, 0.03)), M=M, name="gas_valve")


def sink(k, x, y, yaw=0):
    M = T(x, y, 0, yaw)
    steel = mat("metal_steel", "metal_steel", metal=0.6, rough=0.4)
    kitchen_counter(k, x, y, yaw, w=1.2)
    k.box((-0.4, -0.22, 0.75), (0.4, 0.22, 0.935), mat("sink_basin", color=(0.25, 0.26, 0.27), metal=0.7, rough=0.3), M=M, name="basin")
    k.box((-0.03, -0.3, 0.93), (0.03, -0.25, 1.2), steel, M=M, name="faucet")
    k.box((-0.03, -0.3, 1.17), (0.03, -0.1, 1.2), steel, M=M, name="spout")


def pot_rack(k, x, y, z, w=1.6):
    """天花板吊下來的鍋架，掛著鍋子和湯杓。"""
    iron = mat("iron", color=(0.03, 0.03, 0.03), metal=0.8, rough=0.5)
    copper = mat("copper", color=(0.45, 0.2, 0.1), metal=0.8, rough=0.35)
    k.box((x - w / 2, y - 0.25, z), (x + w / 2, y + 0.25, z + 0.03), iron, name="rack")
    for cx in (x - w / 2 + 0.03, x + w / 2 - 0.03):
        k.box((cx - 0.01, y - 0.01, z), (cx + 0.01, y + 0.01, z + 0.9), iron, name="rack_chain")
    for i in range(5):
        px = x - w / 2 + 0.2 + i * (w - 0.4) / 4
        r = 0.1 + 0.03 * (i % 3)
        k.box((px - 0.005, y - 0.005, z - 0.25), (px + 0.005, y + 0.005, z), iron, name="hook")
        k.cyl((px, y, z - 0.25 - r * 0.8), r, r * 0.8, copper, seg=8, uv=0.3, name="pot")


def chopping_block(k, x, y, occluder=True):
    wood = mat("wood_crate", "wood_crate")
    k.box((x - 0.35, y - 0.35, 0), (x + 0.35, y + 0.35, 0.9), wood, uv=0.8, occluder=occluder, name="block")
    k.box((x - 0.36, y - 0.36, 0.85), (x + 0.36, y + 0.36, 0.9), mat("blood_wood", color=(0.2, 0.05, 0.03), rough=0.7), name="block_stain")


def fridge(k, x, y, yaw=0, occluder=True):
    M = T(x, y, 0, yaw)
    white = mat("enamel", color=(0.62, 0.6, 0.55), rough=0.35)
    k.box((-0.4, -0.35, 0), (0.4, 0.35, 1.9), white, M=M, occluder=occluder, name="fridge")
    k.box((-0.005, 0.35, 0.1), (0.005, 0.36, 1.85), mat("dark", color=(0.03, 0.02, 0.015)), M=M, name="fridge_gap")
    for sx in (-0.06, 0.06):
        k.box((sx - 0.015, 0.35, 1.0), (sx + 0.015, 0.39, 1.4), mat("chrome", color=(0.6, 0.6, 0.6), metal=0.9, rough=0.3), M=M, name="fridge_handle")


def dumbwaiter(k, x, y, z, yaw=0, open_=False):
    """送餐升降機的牆上開口：木框＋上下拉的小門（P4）。朝 +y。"""
    M = T(x, y, z, yaw)
    frame = mat("wood_furniture", "wood_furniture")
    k.box((-0.45, -0.02, -0.05), (0.45, 0.06, 0.75), frame, uv=1, M=M, name="dw_frame")
    k.box((-0.38, -0.01, 0.02), (0.38, 0.0, 0.68), mat("dw_inside", color=(0.01, 0.01, 0.01)), M=M, name="dw_hole")
    if not open_:
        k.box((-0.38, 0.0, 0.02), (0.38, 0.04, 0.68), mat("metal_rusty", "metal_rusty", metal=0.5), uv=0.6, M=M, name="dw_door")
    k.box((0.5, 0.0, 0.25), (0.58, 0.05, 0.45), mat("brass", "brass", metal=0.7), M=M, name="dw_button")


def shelf_unit(k, x, y, yaw=0, w=1.4, h=2.0, d=0.4, items="cans", occluder=True, metal=False):
    """層架＋上面的東西：罐頭、瓶子、箱子、書。"""
    import random
    M = T(x, y, 0, yaw)
    m = mat("metal_steel", "metal_steel", metal=0.6, rough=0.5) if metal else mat("wood_furniture", "wood_furniture")
    for sx in (-w / 2, w / 2 - 0.04):
        k.box((sx, -d / 2, 0), (sx + 0.04, d / 2, h), m, uv=1, M=M, occluder=occluder, name="shelf_post")
    rnd = random.Random(int(x * 31 + y * 17))
    n = 4
    for i in range(n):
        z = 0.1 + i * (h - 0.1) / n
        k.box((-w / 2, -d / 2, z), (w / 2, d / 2, z + 0.03), m, uv=1, M=M, occluder=occluder, name="shelf_board")
        cx = -w / 2 + 0.1
        while cx < w / 2 - 0.12:
            if items == "cans":
                col = [(0.5, 0.1, 0.06), (0.15, 0.25, 0.12), (0.55, 0.45, 0.2), (0.4, 0.4, 0.42)][rnd.randrange(4)]
                k.cyl((cx, 0, z + 0.03), 0.04, 0.11, mat(f"can{col}", color=col, metal=0.4, rough=0.4), seg=6, uv=0.1, M=M, name="can")
                cx += 0.09
            elif items == "jars":
                k.cyl((cx, 0, z + 0.03), 0.05, 0.16, mat("jar", color=(0.3, 0.32, 0.22), rough=0.15), seg=6, uv=0.1, M=M, name="jar")
                cx += 0.12
            else:
                hh = 0.15 + rnd.random() * 0.15
                k.box((cx - 0.06, -d / 2 + 0.05, z + 0.03), (cx + 0.08, d / 2 - 0.05, z + 0.03 + hh), mat("cardboard", color=(0.42, 0.32, 0.2)), uv=0.5, M=M, name="sbox")
                cx += 0.18


def carcass(k, x, y, z_top=2.4):
    """吊在鉤子上的肉（冷凍庫）：鏈條＋鉤子＋不規則的大塊肉（看不出是什麼動物）。"""
    import random
    rnd = random.Random(int(x * 97 + y * 13))
    iron = mat("iron", color=(0.03, 0.03, 0.03), metal=0.8, rough=0.5)
    meat = mat("meat", "meat", rough=0.55)
    k.box((x - 0.01, y - 0.01, z_top - 0.35), (x + 0.01, y + 0.01, z_top), iron, name="hook_chain")
    k.box((x - 0.015, y - 0.05, z_top - 0.4), (x + 0.015, y + 0.0, z_top - 0.34), iron, name="hook")
    tw = rnd.uniform(-0.4, 0.4)
    M = Matrix.Translation((x, y, z_top - 0.4)) @ Matrix.Rotation(tw, 4, "Z") @ Matrix.Diagonal((1.0, 0.7, 1.0, 1.0))
    L = rnd.uniform(0.9, 1.15)
    k.cyl((0, 0, -L), 0.13, L, meat, seg=7, uv=0.5, r_top=0.17, M=M, occluder=True, name="carcass")
    # 下垂的一截（腿或肋排的形狀）
    Ml = M @ Matrix.Translation((rnd.uniform(-0.06, 0.06), 0, -L)) @ Matrix.Rotation(rnd.uniform(-0.3, 0.3), 4, "Y")
    k.cyl((0, 0, -0.35), 0.05, 0.38, meat, seg=5, uv=0.4, r_top=0.09, M=Ml, occluder=True, name="carcass_leg")


def blood_pool(k, x, y, r=0.5, seed=0):
    """地上的一攤血：幾個重疊的不規則扁平圓，暗紅、有一點反光。"""
    import random
    rnd = random.Random(seed)
    m = mat("blood_pool", color=(0.045, 0.0, 0.0), rough=0.45)
    for i in range(5):
        dx, dy = rnd.uniform(-r, r) * 0.6, rnd.uniform(-r, r) * 0.6
        rr = r * rnd.uniform(0.3, 0.6)
        k.cyl((x + dx, y + dy, 0.001 + i * 0.0005), rr, 0.002, m, seg=7, uv=0.3, name="blood")


def globe(k, x, y, occluder=True):
    wood = mat("wood_furniture", "wood_furniture")
    k.cyl((x, y, 0), 0.2, 0.05, wood, seg=8, uv=0.3, occluder=occluder, name="globe_base")
    k.cyl((x, y, 0.05), 0.03, 0.7, wood, seg=6, uv=0.3, occluder=occluder, name="globe_stand")
    k.cyl((x, y, 0.75), 0.25, 0.4, mat("globe", "painting_portrait"), seg=10, uv=0.5, r_top=0.2, occluder=occluder, name="globe_ball")


def library_ladder(k, x, y, yaw=0, h=2.6):
    M = T(x, y, 0, yaw)
    wood = mat("wood_furniture", "wood_furniture")
    tilt = Matrix.Rotation(math.radians(12), 4, "X")
    for sx in (-0.22, 0.22):
        k.box((sx - 0.025, -0.025, 0), (sx + 0.025, 0.025, h), wood, uv=0.5, M=M @ tilt, name="ladder_rail")
    for i in range(1, 9):
        z = i * h / 9
        k.box((-0.22, -0.015, z - 0.015), (0.22, 0.015, z + 0.015), wood, uv=0.5, M=M @ tilt, name="ladder_rung")


def vase_table(k, x, y, yaw=0, occluder=True):
    """走廊的小邊桌＋花瓶（插著枯掉的花）。"""
    M = T(x, y, 0, yaw)
    wood = mat("wood_furniture", "wood_furniture")
    k.box((-0.4, -0.2, 0.75), (0.4, 0.2, 0.8), wood, uv=0.6, M=M, occluder=occluder, name="side_top")
    for sx in (-0.35, 0.35):
        for sy in (-0.15, 0.15):
            k.box((sx - 0.02, sy - 0.02, 0), (sx + 0.02, sy + 0.02, 0.75), wood, uv=0.4, M=M, name="side_leg")
    p = M @ Vector((0, 0, 0.8))
    k.cyl(tuple(p), 0.08, 0.3, mat("vase", color=(0.15, 0.2, 0.3), rough=0.25), seg=8, uv=0.3, r_top=0.05, name="vase")
    for i in range(4):
        a = i * 1.6
        Mf = Matrix.Translation(tuple(p + Vector((0, 0, 0.3)))) @ Matrix.Rotation(a, 4, "Z") @ Matrix.Rotation(0.4, 4, "X")
        k.box((-0.005, -0.005, 0), (0.005, 0.005, 0.35), mat("dead_stem", color=(0.15, 0.12, 0.06)), M=Mf, name="stem")


def corridor(k, x0, y0, x1, y1, h, wall_tex="wallpaper_damask_green", floor_tex="floor_wood_dark", runner="carpet_red"):
    """走廊：房間外殼＋中間一條地毯。"""
    room_shell(k, x0, y0, x1, y1, h,
               floor=mat(floor_tex, floor_tex), wall=mat(wall_tex, wall_tex),
               ceiling=mat("plaster_grey", "plaster_grey"), wainscot=mat("wainscot_dark", "wainscot_dark"))
    if runner:
        if (x1 - x0) > (y1 - y0):
            cy = (y0 + y1) / 2
            rug(k, x0 + 0.2, cy - 0.6, x1 - 0.2, cy + 0.6, runner)
        else:
            cx = (x0 + x1) / 2
            rug(k, cx - 0.6, y0 + 0.2, cx + 0.6, y1 - 0.2, runner)


# ======================================================================
# 第四批道具：健身房、更衣室、泳池、機房、客房（2026-10-19）
# ======================================================================

def weight_plate(k, x, y, z, r=0.22, axis="x"):
    iron = mat("plate_iron", color=(0.04, 0.04, 0.045), metal=0.6, rough=0.5)
    R = Matrix.Rotation(math.radians(90), 4, "Y") if axis == "x" else Matrix.Rotation(math.radians(90), 4, "X")
    k.cyl((0, 0, -0.025), r, 0.05, iron, seg=10, uv=0.3, M=Matrix.Translation((x, y, z)) @ R, name="plate")


def bench_press(k, x, y, yaw=0, loaded=(0.22, 0.22), occluder=True):
    """臥推椅＋槓鈴架＋槓鈴（P6：槓片要左右對稱）。loaded = 左右兩邊的槓片半徑（0 = 沒裝）。"""
    M = T(x, y, 0, yaw)
    steel = mat("metal_steel", "metal_steel", metal=0.7, rough=0.4)
    pad = mat("leather_black", color=(0.04, 0.04, 0.045), rough=0.6)
    k.box((-0.15, -0.6, 0.42), (0.15, 0.6, 0.5), pad, M=M, occluder=occluder, name="bench_pad")
    for sy in (-0.5, 0.5):
        k.box((-0.04, sy - 0.04, 0), (0.04, sy + 0.04, 0.42), steel, M=M, name="bench_leg")
    for sx in (-0.5, 0.5):
        k.box((sx - 0.03, 0.45, 0), (sx + 0.03, 0.51, 1.15), steel, M=M, occluder=occluder, name="rack_post")
    p = M @ Vector((0, 0.48, 1.12))
    k.box((p.x - 1.0, p.y - 0.015, p.z - 0.015), (p.x + 1.0, p.y + 0.015, p.z + 0.015), mat("chrome", color=(0.6, 0.6, 0.6), metal=0.9, rough=0.3), name="barbell")
    for side, r in zip((-1, 1), loaded):
        if r > 0:
            weight_plate(k, p.x + side * 0.8, p.y, p.z, r)


def dumbbell_rack(k, x, y, yaw=0, occluder=True):
    M = T(x, y, 0, yaw)
    steel = mat("metal_steel", "metal_steel", metal=0.7, rough=0.4)
    iron = mat("plate_iron", color=(0.04, 0.04, 0.045), metal=0.6, rough=0.5)
    k.box((-0.9, -0.25, 0.0), (0.9, 0.25, 0.08), steel, M=M, occluder=occluder, name="dbr_base")
    for z, yy in ((0.45, -0.1), (0.75, 0.1)):
        k.box((-0.9, yy - 0.12, z - 0.03), (0.9, yy + 0.12, z), steel, M=M, occluder=occluder, name="dbr_tier")
        for i in range(6):
            cx = -0.75 + i * 0.3
            if (i + int(z * 10)) % 5 == 0:
                continue        # 有幾個不見了（被拿去當武器）
            for sx in (-0.09, 0.09):
                Mp = M @ Matrix.Translation((cx + sx, yy, z + 0.06)) @ Matrix.Rotation(math.radians(90), 4, "Y")
                k.cyl((0, 0, -0.02), 0.06, 0.04, iron, seg=6, uv=0.2, M=Mp, name="db_head")
    for sx in (-0.88, 0.85):
        k.box((sx, -0.25, 0), (sx + 0.03, 0.25, 0.8), steel, M=M, occluder=occluder, name="dbr_side")


def cable_machine(k, x, y, yaw=0, occluder=True):
    """滑輪機（B2：把冠軍引到下面，放下配重片）。"""
    M = T(x, y, 0, yaw)
    steel = mat("metal_steel", "metal_steel", metal=0.7, rough=0.4)
    iron = mat("plate_iron", color=(0.04, 0.04, 0.045), metal=0.6, rough=0.5)
    for sx in (-0.6, 0.6):
        k.box((sx - 0.05, -0.05, 0), (sx + 0.05, 0.05, 2.4), steel, M=M, occluder=occluder, name="cm_post")
    k.box((-0.65, -0.06, 2.35), (0.65, 0.06, 2.45), steel, M=M, occluder=occluder, name="cm_top")
    k.box((-0.15, -0.12, 1.4), (0.15, 0.12, 2.2), iron, M=M, occluder=occluder, name="cm_stack")      # 吊在上面的配重片
    k.box((-0.004, -0.004, 0.3), (0.004, 0.004, 1.4), mat("cable", color=(0.1, 0.1, 0.1)), M=M, name="cm_cable")
    k.box((-0.2, -0.3, 0), (0.2, 0.3, 0.08), steel, M=M, name="cm_base")


def treadmill(k, x, y, yaw=0, occluder=True):
    M = T(x, y, 0, yaw)
    black = mat("plastic_black", color=(0.04, 0.04, 0.045), rough=0.5)
    k.box((-0.4, -0.9, 0.0), (0.4, 0.9, 0.22), black, M=M, occluder=occluder, name="tm_deck")
    k.box((-0.35, -0.85, 0.22), (0.35, 0.8, 0.23), mat("belt", color=(0.02, 0.02, 0.02), rough=0.8), M=M, name="tm_belt")
    for sx in (-0.38, 0.38):
        k.box((sx - 0.03, -0.85, 0.22), (sx + 0.03, -0.75, 1.3), mat("metal_steel", "metal_steel", metal=0.7), M=M, occluder=occluder, name="tm_post")
    k.box((-0.4, -0.95, 1.2), (0.4, -0.75, 1.4), black, M=M, occluder=occluder, name="tm_console")
    k.box((-0.15, -0.76, 1.28), (0.15, -0.755, 1.36), mat("tm_screen", color=(0.1, 0.4, 0.15), emit=2.0), M=M, name="tm_screen")


def mirror_wall(k, x0, x1, y, z0=0.3, z1=2.4, cracked=True):
    """整面鏡子（朝 +y）。裂開的地方用暗色的線。"""
    m = mat("mirror", color=(0.75, 0.78, 0.8), metal=1.0, rough=0.05)
    k.box((x0, y, z0), (x1, y + 0.02, z1), m, name="mirror")
    if cracked:
        dark = mat("crack", color=(0.02, 0.02, 0.02))
        cx, cz = (x0 + x1) / 2 + 0.6, (z0 + z1) / 2
        for a in (0.3, 1.2, 2.0, 2.9, 4.0, 5.1):
            L = 0.8
            Mc = Matrix.Translation((cx, y + 0.021, cz)) @ Matrix.Rotation(a, 4, "Y")
            k.box((0, 0, -0.008), (L, 0.002, 0.008), dark, M=Mc, name="crack")


def lockers(k, x, y, yaw=0, n=6, h=1.9, open_idx=(), occluder=True):
    """一排鐵櫃（朝 +y）。open_idx：門打開的那幾個。"""
    M = T(x, y, 0, yaw)
    paint = mat("locker_green", "locker_green", metal=0.3, rough=0.5)
    w = 0.38
    W = n * w
    k.box((-W / 2, -0.45, 0.1), (W / 2, 0.0, h), paint, uv=0.5, M=M, occluder=occluder, name="locker_body")
    k.box((-W / 2, -0.45, 0), (W / 2, -0.02, 0.1), mat("dark", color=(0.03, 0.02, 0.015)), M=M, name="locker_base")
    for i in range(n):
        cx = -W / 2 + (i + 0.5) * w
        if i in open_idx:
            k.box((cx - w / 2 + 0.02, -0.4, 0.12), (cx + w / 2 - 0.02, 0.0, h - 0.02), mat("locker_inside", color=(0.02, 0.02, 0.02)), M=M, name="locker_open")
            Md = M @ Matrix.Translation((cx - w / 2 + 0.02, 0.0, 0)) @ Matrix.Rotation(math.radians(-100), 4, "Z") @ Matrix.Translation((-(cx - w / 2 + 0.02), 0, 0))
            k.box((cx - w / 2 + 0.02, 0.0, 0.12), (cx + w / 2 - 0.02, 0.02, h - 0.02), paint, uv=0.5, M=Md, name="locker_door")
        else:
            k.box((cx - w / 2 + 0.02, 0.0, 0.12), (cx + w / 2 - 0.02, 0.012, h - 0.02), paint, uv=0.5, M=M, name="locker_door")
            k.box((cx + w / 2 - 0.08, 0.012, 1.0), (cx + w / 2 - 0.05, 0.03, 1.12), mat("chrome", color=(0.6, 0.6, 0.6), metal=0.9, rough=0.3), M=M, name="locker_handle")


def bench(k, x, y, yaw=0, L=1.8, occluder=True):
    M = T(x, y, 0, yaw)
    wood = mat("wood_crate", "wood_crate")
    k.box((-L / 2, -0.18, 0.42), (L / 2, 0.18, 0.47), wood, uv=0.6, M=M, occluder=occluder, name="bench_top")
    for sx in (-L / 2 + 0.1, L / 2 - 0.1):
        k.box((sx - 0.03, -0.15, 0), (sx + 0.03, 0.15, 0.42), mat("metal_steel", "metal_steel", metal=0.6), M=M, name="bench_leg")


def pool_basin(k, x0, y0, x1, y1, depth=1.8, drained=True):
    """泳池：地面上挖下去的池子（池壁、池底都是藍磁磚）。drained = 水已經抽乾。"""
    tile = mat("pool_tile", "pool_tile")
    k.box((x0, y0, -depth - 0.1), (x1, y1, -depth), tile, uv=2, name="pool_floor")
    t = 0.1
    k.box((x0 - t, y0, -depth), (x0, y1, 0), tile, uv=2, name="pool_wall")
    k.box((x1, y0, -depth), (x1 + t, y1, 0), tile, uv=2, name="pool_wall")
    k.box((x0 - t, y0 - t, -depth), (x1 + t, y0, 0), tile, uv=2, name="pool_wall")
    k.box((x0 - t, y1, -depth), (x1 + t, y1 + t, 0), tile, uv=2, name="pool_wall")
    # 池邊的白色石材
    edge = mat("pool_edge", color=(0.55, 0.53, 0.48), rough=0.6)
    for (a, b, c, d) in ((x0 - 0.35, y0 - 0.35, x1 + 0.35, y0 - t), (x0 - 0.35, y1 + t, x1 + 0.35, y1 + 0.35),
                         (x0 - 0.35, y0 - t, x0 - t, y1 + t), (x1 + t, y0 - t, x1 + 0.35, y1 + t)):
        k.box((a, b, -0.02), (c, d, 0.03), edge, uv=1, name="pool_edge")
    if drained:
        # 池底殘留的污水、排水口
        k.box((x0 + 0.3, y0 + 0.3, -depth), (x1 - 0.3, y0 + 2.0, -depth + 0.01), mat("sludge", color=(0.06, 0.08, 0.05), rough=0.2), name="sludge")
        k.cyl(((x0 + x1) / 2, y1 - 1.0, -depth), 0.25, 0.012, mat("drain", color=(0.02, 0.02, 0.02), metal=0.6), seg=8, name="drain")
    else:
        k.box((x0, y0, -0.35), (x1, y1, -0.3), mat("water", color=(0.04, 0.12, 0.14), rough=0.05, metal=0.2), name="water")


def pool_ladder(k, x, y, depth=1.6, yaw=0):
    M = T(x, y, 0, yaw)
    chrome = mat("chrome", color=(0.6, 0.6, 0.6), metal=0.9, rough=0.3)
    for sx in (-0.25, 0.25):
        k.box((sx - 0.02, -0.02, -depth), (sx + 0.02, 0.02, 0.9), chrome, M=M, name="ladder_rail")
        k.box((sx - 0.02, -0.3, 0.88), (sx + 0.02, 0.0, 0.92), chrome, M=M, name="ladder_top")
    for i in range(5):
        z = -depth + 0.3 + i * 0.3
        k.box((-0.25, -0.05, z), (0.25, 0.05, z + 0.03), chrome, M=M, name="ladder_step")


def teddy_bear(k, x, y, z, yaw=0):
    """粉紅色的泰迪熊（少了一隻眼睛）。原創造型：圓胖、短手腳、一邊耳朵被扯掉一半。"""
    M = T(x, y, z, yaw) @ Matrix.Rotation(math.radians(70), 4, "X")      # 躺著
    pink = mat("bear_pink", color=(0.62, 0.32, 0.38), rough=0.9)
    burnt = mat("bear_burnt", color=(0.18, 0.08, 0.08), rough=0.9)
    k.cyl((0, 0, 0), 0.16, 0.3, pink, seg=8, uv=0.3, r_top=0.13, M=M, name="bear_body")
    k.cyl((0, 0, 0.3), 0.12, 0.2, pink, seg=8, uv=0.3, r_top=0.08, M=M, name="bear_head")
    k.cyl((0, -0.1, 0.36), 0.05, 0.05, pink, seg=6, uv=0.2, M=M @ Matrix.Rotation(math.radians(-90), 4, "X") @ Matrix.Translation((0, -0.36, -0.1)), name="bear_snout")
    k.box((-0.13, -0.03, 0.46), (-0.07, 0.03, 0.52), pink, M=M, name="bear_ear")
    k.box((0.07, -0.03, 0.46), (0.1, 0.03, 0.49), burnt, M=M, name="bear_ear_torn")
    k.box((-0.07, -0.12, 0.4), (-0.04, -0.11, 0.43), mat("black", color=(0.02, 0.02, 0.02)), M=M, name="bear_eye")
    for sx in (-0.15, 0.15):
        k.cyl((sx, 0, 0.05), 0.05, 0.14, pink, seg=6, uv=0.2, M=M, name="bear_leg")
    k.box((-0.1, -0.15, 0.05), (0.05, -0.13, 0.2), burnt, M=M, name="bear_burn")


def deck_chair(k, x, y, yaw=0, occluder=False):
    M = T(x, y, 0, yaw)
    white = mat("plastic_white", color=(0.55, 0.53, 0.5), rough=0.5)
    k.box((-0.32, -0.9, 0.3), (0.32, 0.4, 0.35), white, M=M, occluder=occluder, name="dc_seat")
    k.box((-0.32, 0.4, 0.3), (0.32, 0.45, 0.95), white, M=M @ Matrix.Translation((0, 0.4, 0.3)) @ Matrix.Rotation(math.radians(-35), 4, "X") @ Matrix.Translation((0, -0.4, -0.3)), occluder=occluder, name="dc_back")
    for sx in (-0.28, 0.28):
        for sy in (-0.85, 0.35):
            k.box((sx - 0.02, sy - 0.02, 0), (sx + 0.02, sy + 0.02, 0.3), white, M=M, name="dc_leg")


def pipes_valves(k, x0, x1, y, z, colors=("#a01a14", "#1a50a0", "#c8a018", "#2a8a3a"), occluder=False):
    """機房牆上的水管：四條不同顏色的水管＋閥門把手（P7：依顏色與順序開關）。朝 +y。"""
    def c(h):
        return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    for i, col in enumerate(colors):
        zz = z + i * 0.35
        m = mat(f"pipe{i}", color=c(col), metal=0.5, rough=0.45)
        k.box((x0, y, zz), (x1, y + 0.12, zz + 0.12), m, occluder=occluder, name="pipe")
        vx = x0 + (x1 - x0) * (0.25 + 0.15 * i)
        k.box((vx - 0.03, y + 0.12, zz + 0.02), (vx + 0.03, y + 0.22, zz + 0.1), m, name="valve_stem")
        k.cyl((vx, y + 0.22, zz + 0.06), 0.1, 0.02, mat("valve_wheel", color=(0.08, 0.08, 0.08), metal=0.7), seg=8, uv=0.2,
              M=Matrix.Translation((vx, y + 0.22, zz + 0.06)) @ Matrix.Rotation(math.radians(-90), 4, "X") @ Matrix.Translation((-vx, -(y + 0.22), -(zz + 0.06))),
              name="valve_wheel")


def pump_tank(k, x, y, r=0.5, h=1.8, occluder=True):
    steel = mat("metal_rusty", "metal_rusty", metal=0.5, rough=0.6)
    k.cyl((x, y, 0), r, h, steel, seg=10, uv=1, occluder=occluder, name="tank")
    k.cyl((x, y, h), r * 0.6, 0.15, steel, seg=10, uv=0.5, r_top=0.1, occluder=occluder, name="tank_top")
    k.box((x - 0.05, y - r - 0.15, 0.4), (x + 0.05, y - r, 0.5), steel, name="tank_outlet")
    k.cyl((x + r * 0.7, y - r * 0.7, 1.3), 0.08, 0.02, mat("gauge", color=(0.8, 0.78, 0.7)), seg=8, name="gauge")


def bed(k, x, y, yaw=0, double=True, messy=True, occluder=True):
    """客房的床（床頭朝 +y）。"""
    M = T(x, y, 0, yaw)
    wood = mat("wood_furniture", "wood_furniture")
    linen = mat("fabric_linen", "fabric_linen")
    cover = mat("fabric_velvet_red", "fabric_velvet_red")
    w = 0.8 if double else 0.5
    k.box((-w, -1.0, 0.0), (w, 1.0, 0.45), wood, uv=1, M=M, occluder=occluder, name="bed_frame")
    k.box((-w + 0.03, -0.97, 0.45), (w - 0.03, 0.97, 0.6), linen, uv=1, M=M, occluder=occluder, name="mattress")
    k.box((-w - 0.02, 0.97, 0.0), (w + 0.02, 1.05, 1.15), wood, uv=1, M=M, occluder=occluder, name="headboard")
    k.box((-w + 0.1, 0.55, 0.6), (-0.05, 0.9, 0.72), linen, M=M, name="pillow")
    if double:
        k.box((0.05, 0.55, 0.6), (w - 0.1, 0.9, 0.72), linen, M=M, name="pillow")
    Mc = M @ Matrix.Rotation(math.radians(6 if messy else 0), 4, "Z")
    k.box((-w - 0.03, -1.0, 0.5), (w + 0.03, 0.35, 0.66), cover, uv=1, M=Mc, name="cover")


def wardrobe(k, x, y, yaw=0, occluder=True):
    M = T(x, y, 0, yaw)
    wood = mat("wood_furniture", "wood_furniture")
    k.box((-0.55, -0.3, 0), (0.55, 0.3, 2.1), wood, uv=1, M=M, occluder=occluder, name="wardrobe")
    k.box((-0.005, 0.3, 0.1), (0.005, 0.31, 2.0), mat("dark", color=(0.03, 0.02, 0.015)), M=M, name="ward_gap")
    for sx in (-0.05, 0.05):
        k.box((sx - 0.01, 0.3, 1.0), (sx + 0.01, 0.33, 1.15), mat("brass", "brass", metal=0.7), M=M, name="ward_handle")


def room_door_number(k, x, y, z, yaw=0, text_col=(0.8, 0.65, 0.25)):
    """客房門上的號碼牌（只是一塊黃銅牌，數字由遊戲文字顯示）。"""
    M = T(x, y, z, yaw)
    k.box((-0.08, 0.05, -0.04), (0.08, 0.065, 0.04), mat("brass", "brass", metal=0.7, rough=0.35), M=M, name="room_number")


def broken_window(k, x, y, z, yaw=0, w=1.1, h=1.8, power=40.0):
    """被撞破的窗（看門犬從這裡跳進來）：窗框歪了、地上有碎玻璃。"""
    window(k, x, y, z, yaw, w=w, h=h, power=power, curtains=True)
    M = T(x, y, 0, yaw)
    glass = mat("glass_shard", color=(0.5, 0.6, 0.65), rough=0.05, metal=0.3)
    import random
    rnd = random.Random(int(x * 13 + y * 7))
    for i in range(14):
        px, py = rnd.uniform(-w, w), rnd.uniform(0.2, 1.6)
        Ms = M @ Matrix.Translation((px, py, 0.003)) @ Matrix.Rotation(rnd.uniform(0, 3), 4, "Z")
        k.box((-0.05, -0.02, 0), (0.05, 0.02, 0.004), glass, M=Ms, name="shard")
    k.box((-w / 2, 0.0, z + h * 0.35), (w / 2, 0.06, z + h * 0.65), mat("night_sky", color=(0.12, 0.17, 0.3), emit=1.2), M=M, name="hole")


def mop_bucket(k, x, y):
    """清潔人員的拖把桶＋拖把（走廊上的雜物）。"""
    yellow = mat("bucket_yellow", color=(0.6, 0.45, 0.05), rough=0.5)
    k.box((x - 0.2, y - 0.15, 0.05), (x + 0.2, y + 0.15, 0.4), yellow, occluder=True, name="bucket")
    for sx in (-0.15, 0.15):
        k.cyl((x + sx, y, 0), 0.04, 0.05, mat("wheel", color=(0.03, 0.03, 0.03)), seg=6, name="bucket_wheel")
    Mm = Matrix.Translation((x + 0.05, y, 0.1)) @ Matrix.Rotation(0.25, 4, "Y")
    k.box((-0.015, -0.015, 0), (0.015, 0.015, 1.3), mat("wood_crate", "wood_crate"), uv=0.4, M=Mm, occluder=True, name="mop")
