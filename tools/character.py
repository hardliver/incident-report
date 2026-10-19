"""角色建模＋動作＋sprite 輸出（Blender / bpy）。

做法和 PS1 時代的惡靈古堡一樣：**分段剛體角色**。
  - 每段肢體（大腿、小腿、上臂……）是獨立的硬模型，用「斷面環」（loft）做出來
  - 每段掛在骨架的一根骨頭上，跟著骨頭轉動；關節處讓模型互相重疊來遮住接縫
  - 不需要蒙皮權重，面數也低（整個角色約 1000 面）

斷面環（ring）：沿著肢體方向放幾個橢圓，相鄰的橢圓連成面。
  ring = (沿肢體的位置 t, 中心偏移 dx, dy, 半徑 rx, ry)

用法：
  python3 tools/character.py cole              → art/characters/cole/ 的 sprite
  python3 tools/character.py cole --turnaround → build/ 的轉身預覽
"""
import math
import os
import sys

import bpy  # noqa: I001  (bpy 要先 import，bmesh 才找得到)
import bmesh
import numpy as np
from mathutils import Euler, Matrix, Vector
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import kit  # noqa: E402

SEG = 8   # 每個斷面環的邊數（PS1 等級）


# ======================================================================
# 角色貼圖（小張、低色數）
# ======================================================================

def char_texture(name, base, noise=0.08, size=32, seed=0, stripes=None):
    """角色用的小貼圖：底色＋一點雜訊（布料、皮革的質感）。"""
    r = np.random.default_rng(seed)
    c = np.array([int(base[i:i + 2], 16) for i in (1, 3, 5)], float)
    n = r.random((size, size))
    n = (n + np.roll(n, 1, 0) + np.roll(n, 1, 1)) / 3
    arr = c[None, None, :] * (1 - noise + 2 * noise * n[..., None])
    if stripes:
        for (v0, v1, col) in stripes:     # 水平色帶（例如背心上的字樣條）
            cc = np.array([int(col[i:i + 2], 16) for i in (1, 3, 5)], float)
            arr[int(v0 * size):int(v1 * size)] = cc
    path = os.path.join(ROOT, "build", "chartex", name + ".png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(path)
    return path


def face_texture(path, skin, brow, eye, lip, stubble=None, size=64):
    """臉：膚色底＋眉、眼、鼻影、嘴。PS1 角色的五官就是畫在貼圖上的。

    座標：u 0..1 = 臉的左到右，v 0..1 = 下巴到頭頂（貼圖的上方是頭頂）。
    """
    def h(c):
        return np.array([int(c[i:i + 2], 16) for i in (1, 3, 5)], float)
    arr = np.zeros((size, size, 3)) + h(skin)
    yy, xx = np.mgrid[0:size, 0:size]
    v = 1 - (yy + 0.5) / size
    u = (xx + 0.5) / size
    # 臉頰到下巴的陰影
    arr *= (0.86 + 0.14 * np.clip(v * 2, 0, 1))[..., None]
    if stubble:
        m = (v < 0.32) & (np.abs(u - 0.5) < 0.3)
        arr[m] = arr[m] * 0.8 + h(stubble) * 0.2

    def rect(u0, v0, u1, v1, col, a=1.0):
        m = (u >= u0) & (u < u1) & (v >= v0) & (v < v1)
        arr[m] = arr[m] * (1 - a) + h(col) * a
    # 眉（粗、平、略往下壓：嚴肅）
    rect(0.25, 0.60, 0.44, 0.65, brow)
    rect(0.56, 0.60, 0.75, 0.65, brow)
    # 眼（深色細長）
    rect(0.29, 0.52, 0.42, 0.565, eye)
    rect(0.58, 0.52, 0.71, 0.565, eye)
    rect(0.29, 0.565, 0.42, 0.58, brow, 0.5)     # 上眼皮的陰影
    rect(0.58, 0.565, 0.71, 0.58, brow, 0.5)
    # 鼻影、嘴
    rect(0.47, 0.36, 0.53, 0.5, "#000000", 0.12)
    rect(0.44, 0.34, 0.56, 0.37, "#000000", 0.18)
    rect(0.40, 0.24, 0.60, 0.27, lip)
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(path)
    return path


def tex_mat(name, path, rough=0.8, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Specular IOR Level"].default_value = 0.2
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(path, check_existing=True)
    t.interpolation = "Closest"
    nt.links.new(t.outputs["Color"], p.inputs["Base Color"])
    return m


# ======================================================================
# 幾何：斷面環
# ======================================================================

def loft(name, rings, mat, axis_from, axis_to, cap0=True, cap1=True, uv_mode="cyl", face_box=None, seg=SEG, keep=None):
    """沿著 axis_from → axis_to 的方向，放一串斷面環，連成一段肢體。

    rings: [(t, dx, dy, rx, ry)]，t 是 0..1 的位置，dx/dy 是垂直於軸的偏移。
    「前方」固定是 -y（角色面向 -y）。
    """
    a = Vector(axis_from)
    b = Vector(axis_to)
    d = (b - a)
    L = d.length
    z = d.normalized()
    ref = Vector((0, -1, 0)) if abs(z.dot(Vector((0, -1, 0)))) < 0.9 else Vector((0, 0, 1))
    x = ref.cross(z).normalized()          # 垂直於軸的兩個方向
    y = z.cross(x).normalized()            # y ≈ 前方（-y 世界）
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    loops = []
    for (t, dx, dy, rx, ry) in rings:
        ring = []
        c = a + d * t + x * dx + y * dy
        for k in range(seg):
            ang = 2 * math.pi * k / seg + math.pi / seg
            p = c + x * (rx * math.cos(ang)) + y * (ry * math.sin(ang))
            ring.append(bm.verts.new(p))
        loops.append(ring)
    for i in range(len(loops) - 1):
        for k in range(seg):
            k2 = (k + 1) % seg
            bm.faces.new([loops[i][k], loops[i][k2], loops[i + 1][k2], loops[i + 1][k]])
    if cap0:
        bm.faces.new(list(reversed(loops[0])))
    if cap1:
        bm.faces.new(loops[-1])
    bm.normal_update()
    # 讓法線朝外
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if keep is not None:      # 只保留部分的面（例如頭髮只要後半圈）
        drop = [f for f in bm.faces if not keep(f.calc_center_median())]
        bmesh.ops.delete(bm, geom=drop, context="FACES")
    if keep is not None:      # 只保留部分的面（例如頭髮只要後半圈）
        drop = [f for f in bm.faces if not keep(f.calc_center_median())]
        bmesh.ops.delete(bm, geom=drop, context="FACES")
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for lp in f.loops:
            p = lp.vert.co
            if uv_mode == "face" and face_box is not None:
                # 頭部：正面用平面投影（臉的貼圖），其他地方用膚色區
                (x0, x1, z0, z1) = face_box
                uu = (p.x - x0) / (x1 - x0)
                vv = (p.z - z0) / (z1 - z0)
                center_y = (a + d * 0.5).y
                fc = sum((l.vert.co for l in f.loops), Vector()) / len(f.loops)
                if fc.y > center_y - 0.035:     # 不是正面（臉在 -y 側）→ 取貼圖邊緣的膚色
                    uu, vv = 0.05, 0.45
                lp[uv].uv = (min(max(uu, 0.01), 0.99), min(max(vv, 0.01), 0.99))
            else:
                rel = p - a
                ang = math.atan2(rel.dot(y), rel.dot(x)) / (2 * math.pi) + 0.5
                lp[uv].uv = (ang, rel.dot(z) / max(L, 1e-6))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(mat)
    return ob


def block(name, mn, mx, mat, M=None):
    """小配件用的盒子（槍套、口袋、警徽……）。"""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    M = M or Matrix()
    x0, y0, z0 = mn
    x1, y1, z1 = mx
    vs = [bm.verts.new(M @ Vector(v)) for v in [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                                 (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]]
    for f in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
        bm.faces.new([vs[i] for i in f])
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for i, lp in enumerate(f.loops):
            lp[uv].uv = ((i in (1, 2)) * 1.0, (i in (2, 3)) * 1.0)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(mat)
    return ob


# ======================================================================
# 骨架
# ======================================================================

# 關節位置（公尺，角色面向 -y，腳底 z = 0）。身高約 1.82 m、約 8 頭身。
J = {
    "hip":      (0.0, 0.0, 0.98),
    "chest":    (0.0, 0.0, 1.12),
    "neck":     (0.0, 0.0, 1.50),
    "head":     (0.0, -0.01, 1.58),
    "head_top": (0.0, -0.01, 1.82),
    "shoulder.L": (0.21, 0.0, 1.44), "elbow.L": (0.25, 0.01, 1.15), "wrist.L": (0.27, 0.0, 0.91), "hand_end.L": (0.275, -0.005, 0.80),
    "thigh.L":  (0.10, 0.0, 0.95), "knee.L": (0.11, -0.01, 0.52), "ankle.L": (0.115, 0.01, 0.09), "toe.L": (0.12, -0.15, 0.03),
}
for k_ in list(J):
    if k_.endswith(".L"):
        x, y, z = J[k_]
        J[k_[:-2] + ".R"] = (-x, y, z)

BONES = [
    # (骨頭, 頭, 尾, 父)
    ("pelvis", "hip", "chest", None),
    ("spine", "chest", "neck", "pelvis"),
    ("head", "neck", "head_top", "spine"),
]
for s in ("L", "R"):
    BONES += [
        (f"upperarm.{s}", f"shoulder.{s}", f"elbow.{s}", "spine"),
        (f"forearm.{s}", f"elbow.{s}", f"wrist.{s}", f"upperarm.{s}"),
        (f"hand.{s}", f"wrist.{s}", f"hand_end.{s}", f"forearm.{s}"),
        (f"thigh.{s}", f"thigh.{s}", f"knee.{s}", "pelvis"),
        (f"shin.{s}", f"knee.{s}", f"ankle.{s}", f"thigh.{s}"),
        (f"foot.{s}", f"ankle.{s}", f"toe.{s}", f"shin.{s}"),
    ]


def make_armature(name="rig"):
    ad = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, ad)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    for (bn, h, t, parent) in BONES:
        b = ad.edit_bones.new(bn)
        b.head = J[h]
        b.tail = J[t]
        b.roll = 0
        if parent:
            b.parent = ad.edit_bones[parent]
            b.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in ob.pose.bones:
        pb.rotation_mode = "XYZ"
    return ob


def attach(part, rig, bone):
    """把一段硬模型掛到骨頭上（保持目前的位置）。"""
    mw = part.matrix_world.copy()
    part.parent = rig
    part.parent_type = "BONE"
    part.parent_bone = bone
    bpy.context.view_layer.update()
    part.matrix_world = mw


# ======================================================================
# 柯爾
# ======================================================================

def build_cole():
    tex = {}
    tex["shirt"] = char_texture("cole_shirt", "#8a7a58", 0.10, seed=1)          # 卡其色制服襯衫
    tex["vest"] = char_texture("cole_vest", "#1a1c1e", 0.12, seed=2)
    tex["patch"] = char_texture("cole_patch", "#b8a038", 0.06, seed=10)          # SHERIFF 字樣（遠看是一條黃色）
    tex["vest_plain"] = char_texture("cole_vest_plain", "#1a1c1e", 0.12, seed=3)
    tex["pants"] = char_texture("cole_pants", "#2e3426", 0.10, seed=4)          # 深橄欖色長褲
    tex["boots"] = char_texture("cole_boots", "#141210", 0.10, seed=5)
    tex["belt"] = char_texture("cole_belt", "#0e0e0e", 0.08, seed=6)
    tex["skin"] = char_texture("cole_skin", "#c49274", 0.05, seed=7)
    tex["hair"] = char_texture("cole_hair", "#2a1c14", 0.15, seed=8)
    tex["glove"] = char_texture("cole_glove", "#121212", 0.08, seed=9)
    fpath = os.path.join(ROOT, "build", "chartex", "cole_face.png")
    face_texture(fpath, "#c49274", "#24180f", "#1a1410", "#8a5a48", stubble="#5a4636")
    tex["face"] = fpath

    M = {k: tex_mat("cole_" + k, v) for k, v in tex.items()}
    M["gold"] = kit.mat("badge_gold", "brass", metal=0.8, rough=0.35)
    M["steel"] = kit.mat("gun_steel", color=(0.08, 0.08, 0.09), metal=0.8, rough=0.4)

    rig = make_armature("cole_rig")
    parts = []

    def P(ob, bone):
        parts.append((ob, bone))

    # ---------------- 骨盆：褲子＋勤務腰帶
    P(loft("pelvis", [(0.0, 0, 0, 0.17, 0.12), (0.5, 0, 0, 0.175, 0.125), (1.0, 0, 0, 0.16, 0.11)],
           M["pants"], (0, 0, 0.86), (0, 0, 1.06)), "pelvis")
    P(loft("belt", [(0, 0, 0, 0.185, 0.135), (1, 0, 0, 0.185, 0.135)], M["belt"], (0, 0, 0.98), (0, 0, 1.04)), "pelvis")
    P(block("buckle", (-0.03, -0.142, 0.985), (0.03, -0.13, 1.035), M["gold"]), "pelvis")
    for x in (-0.12, 0.08):                     # 腰帶上的小包
        P(block("pouch", (x, -0.145, 0.95), (x + 0.05, -0.115, 1.03), M["belt"]), "pelvis")

    # ---------------- 軀幹：襯衫＋戰術背心（胸寬、腰窄）
    torso = [(0.0, 0, 0, 0.165, 0.115), (0.3, 0, -0.005, 0.172, 0.123), (0.7, 0, -0.01, 0.195, 0.133), (0.92, 0, 0, 0.2, 0.12), (1.0, 0, 0, 0.12, 0.08)]
    P(loft("torso", torso, M["shirt"], (0, 0, 1.03), (0, 0, 1.5)), "spine")
    vest = [(0.0, 0, 0, 0.178, 0.128), (0.35, 0, -0.005, 0.188, 0.138), (0.75, 0, -0.012, 0.205, 0.146), (0.95, 0, -0.005, 0.17, 0.13)]
    P(loft("vest", vest, M["vest"], (0, 0, 1.06), (0, 0, 1.45), cap0=False, cap1=False), "spine")
    # 背心正面的彈匣袋、無線電、警徽
    for x in (-0.09, -0.03, 0.03):
        P(block("mag_pouch", (x, -0.165, 1.1), (x + 0.05, -0.13, 1.2), M["vest_plain"]), "spine")
    P(block("radio", (0.1, -0.16, 1.3), (0.15, -0.12, 1.4), M["vest_plain"]), "spine")
    P(block("badge", (-0.12, -0.152, 1.32), (-0.07, -0.145, 1.37), M["gold"]), "spine")
    P(block("back_patch", (-0.13, 0.135, 1.33), (0.13, 0.148, 1.39), M["patch"]), "spine")
    # 衣領
    P(loft("collar", [(0, 0, 0, 0.075, 0.07), (1, 0, 0.005, 0.085, 0.078)], M["shirt"], (0, 0, 1.47), (0, 0, 1.53), cap0=False, cap1=False), "spine")

    # ---------------- 頭：脖子、頭、頭髮
    P(loft("neck", [(0, 0, 0, 0.055, 0.055), (1, 0, 0, 0.05, 0.05)], M["skin"], (0, 0, 1.48), (0, 0, 1.6)), "head")
    head_r = [(0.0, 0, -0.01, 0.045, 0.05), (0.12, 0, -0.025, 0.07, 0.075), (0.35, 0, -0.01, 0.085, 0.1),
              (0.6, 0, 0, 0.09, 0.105), (0.85, 0, 0.01, 0.085, 0.1), (1.0, 0, 0.01, 0.05, 0.06)]
    P(loft("head", head_r, M["face"], (0, -0.01, 1.58), (0, -0.01, 1.83), uv_mode="face",
           face_box=(-0.085, 0.085, 1.58, 1.80)), "head")
    # 頭髮：後腦＋頭頂的蓋子，略大於頭；前面留短瀏海，側分
    # 頭頂的蓋子（從額頭以上）
    cap = [(0.0, 0, 0.0, 0.094, 0.11), (0.45, 0, -0.003, 0.09, 0.104), (1.0, 0, -0.005, 0.05, 0.062)]
    P(loft("hair_cap", cap, M["hair"], (0, -0.012, 1.765), (0, -0.012, 1.86), cap0=False), "head")
    # 後腦的頭髮：只保留後半圈，蓋到後頸
    back = [(0.0, 0, -0.012, 0.07, 0.08), (0.3, 0, -0.012, 0.09, 0.103), (0.75, 0, -0.008, 0.095, 0.11), (1.0, 0, -0.005, 0.094, 0.11)]
    P(loft("hair_back", back, M["hair"], (0, -0.01, 1.6), (0, -0.01, 1.77), cap0=False, cap1=False,
           keep=lambda c: c.y > -0.035), "head")
    P(block("fringe", (-0.075, -0.118, 1.765), (0.05, -0.088, 1.8), M["hair"]), "head")
    P(block("fringe_side", (0.05, -0.112, 1.775), (0.085, -0.085, 1.81), M["hair"]), "head")
    P(block("sideburn.L", (0.082, -0.06, 1.66), (0.095, -0.02, 1.74), M["hair"]), "head")
    P(block("sideburn.R", (-0.095, -0.06, 1.66), (-0.082, -0.02, 1.74), M["hair"]), "head")
    P(block("ear.L", (0.088, -0.02, 1.66), (0.1, 0.01, 1.72), M["skin"]), "head")
    P(block("ear.R", (-0.1, -0.02, 1.66), (-0.088, 0.01, 1.72), M["skin"]), "head")

    # ---------------- 手臂（長袖襯衫、黑色手套）
    for s, sg in (("L", 1), ("R", -1)):
        sh, el, wr, he = (J[f"shoulder.{s}"], J[f"elbow.{s}"], J[f"wrist.{s}"], J[f"hand_end.{s}"])
        P(loft(f"upperarm.{s}", [(-0.15, 0, 0, 0.068, 0.068), (0.2, 0, 0, 0.065, 0.063), (1.0, 0, 0, 0.05, 0.05)],
               M["shirt"], sh, el), f"upperarm.{s}")
        P(loft(f"forearm.{s}", [(-0.05, 0, 0, 0.05, 0.05), (0.4, 0, 0, 0.048, 0.045), (1.0, 0, 0, 0.036, 0.033)],
               M["shirt"], el, wr), f"forearm.{s}")
        P(loft(f"hand.{s}", [(-0.1, 0, 0, 0.036, 0.022), (0.5, 0, 0, 0.044, 0.024), (1.0, 0, 0, 0.03, 0.018)],
               M["glove"], wr, he), f"hand.{s}")
        # 肩上的背心肩帶
        P(block(f"strap.{s}", (sg * 0.12 - 0.035, -0.12, 1.42), (sg * 0.12 + 0.035, 0.12, 1.47), M["vest_plain"]), "spine")

    # ---------------- 腿（褲子、靴子、右大腿槍套）
    for s, sg in (("L", 1), ("R", -1)):
        th, kn, an, to = (J[f"thigh.{s}"], J[f"knee.{s}"], J[f"ankle.{s}"], J[f"toe.{s}"])
        P(loft(f"thigh.{s}", [(-0.1, 0, 0, 0.088, 0.09), (0.3, 0, 0, 0.085, 0.085), (1.0, 0, 0, 0.06, 0.062)],
               M["pants"], th, kn), f"thigh.{s}")
        P(loft(f"shin.{s}", [(-0.05, 0, 0, 0.062, 0.064), (0.3, 0, 0, 0.058, 0.06), (0.62, 0, 0, 0.046, 0.048)],
               M["pants"], kn, an, cap1=False), f"shin.{s}")
        P(loft(f"boot.{s}", [(0.6, 0, 0, 0.05, 0.052), (0.85, 0, 0, 0.052, 0.054), (1.06, 0, 0, 0.055, 0.06)],
               M["boots"], kn, an), f"shin.{s}")
        x = J[f"ankle.{s}"][0]
        P(block(f"foot.{s}", (x - 0.048, -0.17, 0.0), (x + 0.048, 0.05, 0.1), M["boots"]), f"foot.{s}")
    # 槍套（右腿外側）＋配槍
    P(block("holster", (-0.2, -0.05, 0.68), (-0.155, 0.05, 0.9), M["belt"]), "thigh.R")
    P(block("holster_strap", (-0.19, -0.07, 0.72), (-0.07, 0.07, 0.75), M["belt"]), "thigh.R")
    P(block("gun_grip", (-0.195, -0.02, 0.9), (-0.16, 0.035, 0.98), M["steel"]), "thigh.R")

    for ob, bone in parts:
        for poly in ob.data.polygons:
            poly.use_smooth = False
        attach(ob, rig, bone)
    return rig, [p[0] for p in parts]


# ======================================================================
# 動作
# ======================================================================

def pose(rig, angles, loc=(0, 0, 0)):
    """angles: {骨頭: (x, y, z) 度}。沒寫到的骨頭回到原位。"""
    for pb in rig.pose.bones:
        a = angles.get(pb.name, (0, 0, 0))
        pb.rotation_euler = Euler([math.radians(v) for v in a], "XYZ")
    rig.pose.bones["pelvis"].location = loc
    bpy.context.view_layer.update()


def idle_pose(t=0.0):
    """待機：站直、手自然下垂，肩膀略往前（疲憊）。t 用來做輕微的呼吸。"""
    b = math.sin(t * 2 * math.pi) * 1.0
    return {
        "spine": (4 + b, 0, 0), "head": (-3, 0, 0),
        "upperarm.L": (2, 0, 4), "upperarm.R": (2, 0, -4),
        "forearm.L": (-8, 0, 0), "forearm.R": (-8, 0, 0),
    }, (0, 0, 0)


def walk_pose(t):
    """走路循環：t = 0..1。大腿前後擺、膝蓋在擺動期彎曲、手臂反向擺動、身體上下起伏。

    骨頭的區域座標：繞 x 軸轉 = 前後擺（正值往後）。
    """
    ph = t * 2 * math.pi
    swing = 26
    th_l = -swing * math.sin(ph)
    th_r = swing * math.sin(ph)
    # 膝蓋：腿往前擺的那半拍彎曲最多
    kn_l = 40 * max(0, math.sin(ph + 0.9)) + 6
    kn_r = 40 * max(0, math.sin(ph + 0.9 + math.pi)) + 6
    arm = 20
    bob = -0.02 * abs(math.cos(ph))
    return {
        "pelvis": (0, 0, 4 * math.sin(ph)),
        "spine": (6, 0, -6 * math.sin(ph)),
        "head": (-4, 0, 3 * math.sin(ph)),
        "thigh.L": (th_l, 0, 0), "thigh.R": (th_r, 0, 0),
        "shin.L": (kn_l, 0, 0), "shin.R": (kn_r, 0, 0),
        "foot.L": (-kn_l * 0.3, 0, 0), "foot.R": (-kn_r * 0.3, 0, 0),
        "upperarm.L": (arm * math.sin(ph), 0, 5), "upperarm.R": (-arm * math.sin(ph), 0, -5),
        "forearm.L": (-14 - 8 * max(0, -math.sin(ph)), 0, 0), "forearm.R": (-14 - 8 * max(0, math.sin(ph)), 0, 0),
    }, (0, 0, bob)


def aim_pose(t=0.0):
    """舉槍瞄準（雙手持槍，往前平舉）。"""
    return {
        "spine": (2, 0, 8), "head": (0, 0, -6),
        "upperarm.R": (-82, 0, 18), "forearm.R": (-8, 0, 0),
        "upperarm.L": (-78, 0, -28), "forearm.L": (-22, 0, 0),
        "thigh.L": (-8, 0, 0), "thigh.R": (6, 0, 0), "shin.L": (8, 0, 0), "shin.R": (4, 0, 0),
    }, (0, 0, -0.01)


ANIMS = {
    "idle": (idle_pose, 1),
    "walk": (walk_pose, 8),
    "aim": (aim_pose, 1),
}


# ======================================================================
# Sprite 輸出
# ======================================================================

SPRITE_W, SPRITE_H = 64, 128          # 一格 sprite 的畫布（像素）
PIX_PER_M = 62                        # 1.82 m ≈ 113 px（站在畫面最前景時的大小）


def setup_sprite_render():
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.cycles.device = "CPU"
    s.cycles.samples = 32
    s.cycles.use_denoising = True
    s.render.resolution_x = SPRITE_W
    s.render.resolution_y = SPRITE_H
    s.render.film_transparent = True
    s.render.filter_size = 0.7
    s.view_settings.view_transform = "Standard"
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGBA"
    cd = bpy.data.cameras.new("sprite_cam")
    cd.type = "ORTHO"
    cd.ortho_scale = SPRITE_H / PIX_PER_M
    cd.sensor_fit = "VERTICAL"
    cam = bpy.data.objects.new("sprite_cam", cd)
    s.collection.objects.link(cam)
    s.camera = cam
    # 燈光：中性的主光＋冷色輪廓光；房間裡的光線之後由引擎調色
    kit.Kit().light("SUN", (0, 0, 5), (1.0, 0.95, 0.88), 3.0, name="key", rot=(50, 0, -35))
    kit.Kit().light("SUN", (0, 0, 5), (0.6, 0.7, 1.0), 1.6, name="rim", rot=(-60, 0, 160))
    kit.set_ambient((0.25, 0.25, 0.28), 1.0)
    return cam


def place_sprite_cam(cam, direction, elevation=18):
    """direction 0..7：角色面向哪個方向（0 = 面向鏡頭，2 = 面向右）。

    做法：轉攝影機而不是轉角色。elevation 是俯角（固定視角大多從上往下看）。
    """
    yaw = math.radians(direction * 45)
    el = math.radians(elevation)
    dist = 10
    # 角色面向 -y；攝影機在角色前方（-y）時，看到的是正面
    cx = math.sin(yaw) * math.cos(el) * dist
    cy = -math.cos(yaw) * math.cos(el) * dist
    cz = math.sin(el) * dist + 0.91
    cam.location = (cx, cy, cz)
    d = Vector((0, 0, 0.91)) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def render_sprites(name, rig, out_dir, dirs=range(8), anims=ANIMS):
    cam = setup_sprite_render()
    os.makedirs(out_dir, exist_ok=True)
    s = bpy.context.scene
    tmp = os.path.join(ROOT, "build", "sprite_tmp.png")
    frames = {}
    for an, (fn, n) in anims.items():
        for d in dirs:
            place_sprite_cam(cam, d)
            for f in range(n):
                ang, loc = fn(f / n)
                pose(rig, ang, loc)
                s.render.filepath = tmp
                bpy.ops.render.render(write_still=True)
                im = Image.open(tmp).convert("RGBA")
                # alpha 二值化：平台的 sprite 只有透明 / 不透明
                a = np.asarray(im)[..., 3]
                arr = np.asarray(im).copy()
                arr[..., 3] = np.where(a > 100, 255, 0)
                frames[(an, d, f)] = Image.fromarray(arr)
    # 合成成一張 sprite sheet：每列 = 一個動作的一個方向，每欄 = 一格
    rows = [(an, d) for an in anims for d in dirs]
    cols = max(n for (_fn, n) in anims.values())
    sheet = Image.new("RGBA", (cols * SPRITE_W, len(rows) * SPRITE_H), (0, 0, 0, 0))
    for r, (an, d) in enumerate(rows):
        for f in range(anims[an][1]):
            sheet.paste(frames[(an, d, f)], (f * SPRITE_W, r * SPRITE_H))
    # 量化：和背景一樣用索引色（sprite 自己 63 色＋透明）
    alpha = np.asarray(sheet)[..., 3]
    rgb = sheet.convert("RGB").quantize(colors=63, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    q = np.asarray(rgb).astype(np.uint8) + 1
    q[alpha == 0] = 0
    pal = rgb.getpalette()[:63 * 3]
    out = Image.fromarray(q, mode="P")
    out.putpalette([255, 0, 255] + pal)
    out.info["transparency"] = 0
    out.save(os.path.join(out_dir, f"{name}_sheet.png"), transparency=0)
    import json
    meta = {
        "frame": [SPRITE_W, SPRITE_H],
        # 腳底在 sprite 裡的位置（引擎把這個點放到角色在地面上的投影位置）
        "pivot": [SPRITE_W // 2, round(SPRITE_H / 2 + 0.91 * math.cos(math.radians(18)) * PIX_PER_M)],
        "pixels_per_meter": PIX_PER_M,
        "directions": "0 = facing camera, then clockwise in 45 deg steps (2 = facing screen right)",
        "rows": [{"anim": an, "dir": d, "frames": anims[an][1]} for (an, d) in rows],
    }
    with open(os.path.join(out_dir, f"{name}_sheet.json"), "w") as f:
        json.dump(meta, f, indent=1)
    return frames


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "cole"
    kit.reset_scene()
    rig, parts = build_cole()
    out_dir = os.path.join(ROOT, "art", "characters", name)
    frames = render_sprites(name, rig, out_dir)
    # 預覽：轉身圖（idle 8 方向）＋走路 8 格，放大 3 倍
    prev = Image.new("RGBA", (8 * SPRITE_W, 2 * SPRITE_H), (40, 36, 44, 255))
    for d in range(8):
        prev.alpha_composite(frames[("idle", d, 0)], (d * SPRITE_W, 0))
    for f in range(8):
        prev.alpha_composite(frames[("walk", 1, f)], (f * SPRITE_W, SPRITE_H))
    prev = prev.resize((prev.width * 3, prev.height * 3), Image.NEAREST)
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    prev.save(os.path.join(ROOT, "build", f"{name}_turnaround.png"))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "build", f"{name}.blend"))
    print("done")


if __name__ == "__main__":
    main()
