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

def char_texture(name, base, noise=0.08, size=32, seed=0, stripes=None, blood=0.0, tears=0.0, rot=0.0, plaid=None, check=None):
    """角色用的小貼圖：底色＋一點雜訊（布料、皮革的質感）。

    blood：血跡的面積比例（暗紅色斑塊）；tears：破洞（更深的顏色）；
    rot：腐爛的斑（偏綠灰），殭屍的皮膚用。
    """
    r = np.random.default_rng(seed)
    c = np.array([int(base[i:i + 2], 16) for i in (1, 3, 5)], float)
    n = r.random((size, size))
    n = (n + np.roll(n, 1, 0) + np.roll(n, 1, 1)) / 3
    arr = c[None, None, :] * (1 - noise + 2 * noise * n[..., None])
    def blotches(frac, color, mix):
        if frac <= 0:
            return
        # 兩種大小的斑點混合：大塊的污漬＋細碎的噴濺
        low = r.random((size // 4, size // 4))
        fine = r.random((size // 2, size // 2))
        up = lambda a: np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((size, size), Image.BILINEAR)) / 255.0
        big = up(low) * 0.45 + up(fine) * 0.55
        m = (big > 1 - frac)[..., None]
        cc = np.array(color, float)
        arr[:] = np.where(m, arr * (1 - mix) + cc * mix, arr)
    if plaid:        # 格子布：橫豎的色帶
        pc = np.array([int(plaid[i:i + 2], 16) for i in (1, 3, 5)], float)
        for k_ in range(0, size, 8):
            arr[k_:k_ + 3, :] = arr[k_:k_ + 3, :] * 0.4 + pc * 0.6
            arr[:, k_:k_ + 3] = arr[:, k_:k_ + 3] * 0.4 + pc * 0.6
    if check:        # 小方格（廚師褲）
        cc = np.array([int(check[i:i + 2], 16) for i in (1, 3, 5)], float)
        yy, xx = np.mgrid[0:size, 0:size]
        m = (((yy // 4) + (xx // 4)) % 2 == 0)[..., None]
        arr[:] = np.where(m, cc, arr)
    blotches(rot, (70, 80, 62), 0.45)
    blotches(blood, (58, 8, 6), 0.75)
    blotches(tears, (10, 8, 8), 0.8)
    if stripes:
        for (v0, v1, col) in stripes:     # 水平色帶（例如背心上的字樣條）
            cc = np.array([int(col[i:i + 2], 16) for i in (1, 3, 5)], float)
            arr[int(v0 * size):int(v1 * size)] = cc
    path = os.path.join(ROOT, "build", "chartex", name + ".png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(path)
    return path


def face_texture(path, skin, brow, eye, lip, stubble=None, size=64, zombie=False, stitches=False, glow_eyes=None, scars=False):
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
    if zombie:
        # 凹陷的眼窩、混濁的眼白、嘴邊的血
        rect(0.24, 0.46, 0.46, 0.6, "#1a1612", 0.55)
        rect(0.54, 0.46, 0.76, 0.6, "#1a1612", 0.55)
        rect(0.31, 0.52, 0.40, 0.56, "#b8b8a0", 0.9)
        rect(0.60, 0.52, 0.69, 0.56, "#b8b8a0", 0.9)
        rect(0.38, 0.12, 0.64, 0.28, "#4a0a08", 0.6)
        rect(0.42, 0.22, 0.58, 0.27, "#120806", 0.9)
    if glow_eyes:      # 發光的眼睛（追擊者）
        rect(0.30, 0.52, 0.42, 0.565, glow_eyes)
        rect(0.58, 0.52, 0.70, 0.565, glow_eyes)
    if stitches:       # 縫起來的嘴：一條橫線＋直的縫線
        rect(0.34, 0.245, 0.66, 0.265, "#0e0806")
        for x0 in (0.36, 0.42, 0.48, 0.54, 0.6):
            rect(x0, 0.22, x0 + 0.02, 0.29, "#0e0806")
    if scars:          # 臉頰的刀疤
        rect(0.62, 0.3, 0.66, 0.5, "#3a0a08", 0.8)
        rect(0.2, 0.36, 0.3, 0.38, "#3a0a08", 0.8)
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


def make_armature(name="rig", joints=None, bones=None):
    joints = joints or J
    bones = bones or BONES
    ad = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, ad)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    for (bn, h, t, parent) in bones:
        b = ad.edit_bones.new(bn)
        b.head = joints[h]
        b.tail = joints[t]
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
# 共用的身體部位（每個角色檔可以直接用，也可以自己寫）
# ======================================================================

def arms(C, P, M_upper, M_lower, M_hand, joints=None, thick=1.0, bare_lower=None):
    """兩隻手臂：上臂、前臂、手（含拇指）。thick 調整粗細。"""
    joints = joints or C.J
    for s in ("L", "R"):
        sg = 1 if s == "L" else -1
        sh, el, wr, he = (joints[f"shoulder.{s}"], joints[f"elbow.{s}"], joints[f"wrist.{s}"], joints[f"hand_end.{s}"])
        t = thick
        P(C.loft(f"upperarm.{s}", [(-0.15, 0, 0, 0.068 * t, 0.068 * t), (0.2, 0, 0, 0.065 * t, 0.063 * t), (1.0, 0, 0, 0.05 * t, 0.05 * t)],
                 M_upper, sh, el), f"upperarm.{s}")
        P(C.loft(f"forearm.{s}", [(-0.05, 0, 0, 0.05 * t, 0.05 * t), (0.4, 0, 0, 0.048 * t, 0.045 * t), (1.0, 0, 0, 0.034 * t, 0.031 * t)],
                 bare_lower or M_lower, el, wr), f"forearm.{s}")
        P(C.loft(f"hand.{s}", [(-0.1, 0, 0, 0.034 * t, 0.021 * t), (0.5, 0, 0, 0.042 * t, 0.023 * t), (1.0, 0, 0, 0.028 * t, 0.017 * t)],
                 M_hand, wr, he), f"hand.{s}")
        # 拇指（往前、往內）
        P(C.block(f"thumb.{s}", (wr[0] - 0.012, wr[1] - 0.045, wr[2] - 0.075), (wr[0] + 0.008, wr[1] - 0.02, wr[2] - 0.03), M_hand), f"hand.{s}")


def legs(C, P, M_thigh, M_shin, M_boot, joints=None, thick=1.0, boot_top=0.6, shoe_h=0.1, toe=-0.17):
    joints = joints or C.J
    for s in ("L", "R"):
        th, kn, an = (joints[f"thigh.{s}"], joints[f"knee.{s}"], joints[f"ankle.{s}"])
        t = thick
        P(C.loft(f"thigh.{s}", [(-0.1, 0, 0, 0.088 * t, 0.09 * t), (0.3, 0, 0, 0.085 * t, 0.085 * t), (1.0, 0, 0, 0.06 * t, 0.062 * t)],
                 M_thigh, th, kn), f"thigh.{s}")
        P(C.loft(f"shin.{s}", [(-0.05, 0, 0, 0.062 * t, 0.064 * t), (0.3, 0, 0, 0.058 * t, 0.06 * t), (boot_top + 0.02, 0, 0, 0.046 * t, 0.048 * t)],
                 M_shin, kn, an, cap1=False), f"shin.{s}")
        P(C.loft(f"boot.{s}", [(boot_top, 0, 0, 0.05 * t, 0.052 * t), (0.85, 0, 0, 0.052 * t, 0.054 * t), (1.06, 0, 0, 0.055 * t, 0.06 * t)],
                 M_boot, kn, an), f"shin.{s}")
        x = an[0]
        P(C.block(f"foot.{s}", (x - 0.046 * t, toe, 0.0), (x + 0.046 * t, 0.05, shoe_h), M_boot), f"foot.{s}")


def scale_part(ob, factor, center):
    """把一個部件以 center 為中心放大（直接改頂點，不動物件的變換）。"""
    c = Vector(center)
    for v in ob.data.vertices:
        v.co = c + (v.co - c) * factor


def finish(C, rig, parts):
    for ob, bone in parts:
        for poly in ob.data.polygons:
            poly.use_smooth = False
        C.attach(ob, rig, bone)
    return rig, [p[0] for p in parts]


# ======================================================================
# 人形角色的共用建模：只要描述「穿什麼」
# ======================================================================

def humanoid(C, prefix, M, joints=None, build=None, o=None):
    """標準人形：骨盆、軀幹、（外套）、脖子、頭、頭髮、手臂、腿。

    M：材質字典，需要的鍵：
      pants, shirt, skin, face, hair, shoes
      可選：coat（外套）、sleeve（袖子，預設 = coat 或 shirt）、forearm、hand、thigh、shin
    o：選項字典（都有預設值）：
      torso_w 軀幹寬度倍率、arm/leg 粗細、boot_top 鞋子高度、coat_keep 外套保留哪些面、
      hair = "short" | "long" | "bald" | "patchy" | "bun" | None、skirt (長度, 寬度)
    build：額外的部件 build(P, M, J) → 加帽子、配件
    回傳 (rig, parts, P)，最後呼叫 C.finish(C, rig, parts)。
    """
    o = o or {}
    J = dict(joints or C.J)
    sw = o.get("torso_w", 1.0) * o.get("chest", 1.0) ** 0.5
    if sw != 1.0:                 # 軀幹變寬時，肩膀以下的關節跟著往外移
        for k_, (x, y, z) in list(J.items()):
            if k_.split(".")[0] in ("shoulder", "elbow", "wrist", "hand_end"):
                J[k_] = (x * sw, y, z)
    rig = C.make_armature(prefix + "_rig", joints=J)
    parts = []
    P = lambda ob, bone: parts.append((ob, bone))
    loft, block = C.loft, C.block
    w = o.get("torso_w", 1.0)
    d = o.get("torso_d", 1.0)
    # 骨盆
    P(loft("pelvis", [(0.0, 0, 0, 0.17 * w, 0.12 * d), (0.5, 0, 0, 0.175 * w, 0.126 * d), (1.0, 0, 0, 0.165 * w, 0.115 * d)],
           M["pants"], (0, 0, 0.86), (0, 0, 1.06)), "pelvis")
    if "skirt" in o:
        L, R = o["skirt"]
        P(loft("skirt", [(0.0, 0, 0, R, R * 0.85), (0.6, 0, 0, R * 0.85, R * 0.72), (1.0, 0, 0, 0.17 * w, 0.125 * d)],
               M.get("skirt", M["pants"]), (0, 0, 1.04 - L), (0, 0, 1.06), cap0=False, keep=o.get("skirt_keep")), "pelvis")
    # 軀幹（胸的寬度 chest 可以調：健身房員工比較壯）
    ch = o.get("chest", 1.0)
    torso = [(0.0, 0, 0, 0.165 * w, 0.118 * d), (0.3, 0, -0.005, 0.17 * w, 0.122 * d), (0.7, 0, -0.01, 0.185 * w * ch, 0.13 * d * ch),
             (0.9, 0, 0, 0.185 * w * ch, 0.118 * d), (1.0, 0, 0, 0.11, 0.075)]
    has_coat = "coat" in M
    P(loft("torso", torso, M["coat"] if has_coat else M["shirt"], (0, 0, 1.0), (0, 0, 1.5)), "spine")
    if has_coat:      # 外套裡面只露出胸前的一條襯衫
        P(block("shirt_front", (-0.055, -0.15 * d, 1.22), (0.055, -0.13 * d, 1.48), M["shirt"]), "spine")
    if "coat" in M:
        z0 = o.get("coat_bottom", 0.92)
        coat = [(0.0, 0, 0, 0.185 * w, 0.138 * d), (0.35, 0, -0.008, 0.19 * w, 0.142 * d), (0.75, 0, -0.01, 0.195 * w * ch, 0.142 * d * ch), (0.95, 0, 0, 0.17 * w, 0.125 * d)]
        P(loft("coat", coat, M["coat"], (0, 0, z0), (0, 0, 1.47), cap0=False, cap1=False, keep=o.get("coat_keep")), "spine")
    P(loft("collar", [(0, 0, 0, 0.072, 0.068), (1, 0, 0.004, 0.08, 0.075)], M.get("collar", M["shirt"]), (0, 0, 1.47), (0, 0, 1.52),
           cap0=False, cap1=False), "spine")
    # 頭
    hs = o.get("head", 1.0)
    P(loft("neck", [(0, 0, 0, 0.05 * hs, 0.05 * hs), (1, 0, 0, 0.046 * hs, 0.046 * hs)], M["skin"], (0, 0, 1.48), (0, 0, 1.6)), "head")
    top = 1.58 + 0.24 * hs
    head_r = [(0.0, 0, -0.01, 0.044 * hs, 0.05 * hs), (0.12, 0, -0.025, 0.066 * hs, 0.074 * hs), (0.35, 0, -0.01, 0.082 * hs, 0.098 * hs),
              (0.6, 0, 0, 0.087 * hs, 0.104 * hs), (0.85, 0, 0.01, 0.083 * hs, 0.098 * hs), (1.0, 0, 0.01, 0.05 * hs, 0.058 * hs)]
    P(loft("head", head_r, M["face"], (0, -0.01, 1.58), (0, -0.01, top), uv_mode="face",
           face_box=(-0.083 * hs, 0.083 * hs, 1.58, 1.58 + 0.21 * hs)), "head")
    P(block("nose", (-0.011 * hs, -0.104 * hs - 0.02, 1.58 + 0.075 * hs), (0.011 * hs, -0.1 * hs, 1.58 + 0.12 * hs), M["skin"]), "head")
    hair = o.get("hair", "short")
    hz = 1.58 + 0.18 * hs
    if hair in ("short", "patchy", "long", "bun"):
        keep = (lambda c: not (c.x > 0.02 and c.y < 0.0)) if hair == "patchy" else None
        cap = [(0.0, 0, 0.0, 0.092 * hs, 0.108 * hs), (0.45, 0, -0.003, 0.088 * hs, 0.102 * hs), (1.0, 0, -0.005, 0.05 * hs, 0.06 * hs)]
        P(loft("hair_cap", cap, M["hair"], (0, -0.012, hz), (0, -0.012, top + 0.03), cap0=False, keep=keep), "head")
        low = 1.5 if hair == "long" else 1.61
        back = [(0.0, 0, -0.012, 0.075 * hs, 0.085 * hs), (0.4, 0, -0.012, 0.09 * hs, 0.104 * hs), (1.0, 0, -0.005, 0.092 * hs, 0.107 * hs)]
        P(loft("hair_back", back, M["hair"], (0, -0.01, low), (0, -0.01, hz + 0.01), cap0=False, cap1=False,
               keep=lambda c: c.y > -0.03), "head")
        if hair == "long":
            for sg in (1, -1):
                x0, x1 = sorted((sg * 0.07 * hs, sg * 0.1 * hs))
                P(block("side_hair", (x0, -0.07, 1.47), (x1, 0.04, 1.78), M["hair"]), "head")
        if hair == "bun":
            P(loft("bun", [(0, 0, 0, 0.04, 0.04), (0.5, 0, 0, 0.05, 0.05), (1, 0, 0, 0.02, 0.02)], M["hair"], (0, 0.1, 1.74), (0, 0.17, 1.78)), "head")
    # 手臂、腿
    C.arms(C, P, M.get("sleeve", M.get("coat", M["shirt"])), M.get("forearm", M.get("sleeve", M.get("coat", M["shirt"]))),
           M.get("hand", M["skin"]), joints=J, thick=o.get("arm", 1.0))
    C.legs(C, P, M.get("thigh", M["pants"]), M.get("shin", M["pants"]), M["shoes"], joints=J, thick=o.get("leg", 1.0),
           boot_top=o.get("boot_top", 0.88), shoe_h=o.get("shoe_h", 0.08), toe=o.get("toe", -0.15))
    if build:
        build(P, M, J)
    return rig, parts, P


def mats(C, prefix, spec):
    """spec：{名稱: (顏色, 雜訊, 種子, {其他參數})} → 材質字典。face 另外處理。"""
    out = {}
    for k_, v in spec.items():
        color, noise, seed = v[:3]
        kw = v[3] if len(v) > 3 else {}
        out[k_] = C.tex_mat(f"{prefix}_{k_}", C.char_texture(f"{prefix}_{k_}", color, noise, seed=seed, **kw))
    return out


def zombie_face(C, prefix, skin, **kw):
    """殭屍的臉；kw 可以加 stitches / glow_eyes / scars。"""
    path = os.path.join(C.ROOT, "build", "chartex", f"{prefix}_face.png")
    C.face_texture(path, skin, "#2a2620", "#1a1a12", "#3a2a24", zombie=True, **kw)
    return C.tex_mat(f"{prefix}_face", path)


# ======================================================================
# 動作
# ======================================================================

def pose(rig, angles, loc=(0, 0, 0)):
    """angles: {骨頭: (x, y, z) 度}。沒寫到的骨頭回到原位。"""
    for pb in rig.pose.bones:
        a = angles.get(pb.name, (0, 0, 0))
        pb.rotation_euler = Euler([math.radians(v) for v in a], "XYZ")
    root = next(pb for pb in rig.pose.bones if pb.parent is None)    # 人形是 pelvis，四足是 body
    # loc 是骨架空間的位移（x 右、y 前後（角色面向 -y）、z 上下）。
    # 骨頭的 location 卻是「骨頭自己的座標」：人形的骨盆骨是直立的，它的 y 軸朝上。
    # 不換算的話，「往下 0.78 公尺」會變成「往後 0.78 公尺」，所以先轉換到骨頭的座標
    root.location = root.bone.matrix_local.to_3x3().inverted() @ Vector(loc)
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

def run_pose(t):
    """跑步：擺幅比走路大、身體前傾、雙腳有騰空期。"""
    ph = t * 2 * math.pi
    th_l = -40 * math.sin(ph)
    th_r = 40 * math.sin(ph)
    kn_l = 75 * max(0, math.sin(ph + 1.1)) + 10
    kn_r = 75 * max(0, math.sin(ph + 1.1 + math.pi)) + 10
    return {
        "pelvis": (8, 0, 6 * math.sin(ph)),
        "spine": (12, 0, -8 * math.sin(ph)),
        "head": (-10, 0, 4 * math.sin(ph)),
        "thigh.L": (th_l, 0, 0), "thigh.R": (th_r, 0, 0),
        "shin.L": (kn_l, 0, 0), "shin.R": (kn_r, 0, 0),
        "foot.L": (-kn_l * 0.25, 0, 0), "foot.R": (-kn_r * 0.25, 0, 0),
        "upperarm.L": (35 * math.sin(ph), 0, 8), "upperarm.R": (-35 * math.sin(ph), 0, -8),
        "forearm.L": (-70, 0, 0), "forearm.R": (-70, 0, 0),
    }, (0, 0, 0.03 * abs(math.sin(ph)) - 0.03)


def hurt_pose(t=0.0):
    """受傷：按著腹部、身體縮起來、腳步不穩。"""
    return {
        "pelvis": (-6, 0, 0), "spine": (22, 0, 6), "head": (8, 0, 0),
        "upperarm.R": (-20, 0, -22), "forearm.R": (-95, 0, 0),
        "upperarm.L": (8, 0, 10), "forearm.L": (-30, 0, 0),
        "thigh.L": (-14, 0, 0), "shin.L": (24, 0, 0), "thigh.R": (6, 0, 0), "shin.R": (10, 0, 0),
    }, (0, 0, -0.04)


def shamble_pose(t):
    """殭屍的拖行：一隻腳拖在後面、身體歪一邊、手臂往前垂。"""
    ph = t * 2 * math.pi
    th_l = -18 * math.sin(ph)
    th_r = 10 * math.sin(ph)                  # 右腳擺幅小：拖著走
    kn_l = 30 * max(0, math.sin(ph + 0.9)) + 10
    return {
        "pelvis": (0, 6, 6 * math.sin(ph)),
        "spine": (18, -8, -5 * math.sin(ph)),
        "head": (10, 12, 18),
        "thigh.L": (th_l, 0, 0), "thigh.R": (th_r, 0, 6),
        "shin.L": (kn_l, 0, 0), "shin.R": (14, 0, 0),
        "foot.R": (-20, 0, 0),
        "upperarm.L": (-55 + 8 * math.sin(ph), 0, 6), "upperarm.R": (-40 - 6 * math.sin(ph), 0, -10),
        "forearm.L": (-20, 0, 0), "forearm.R": (-35, 0, 0),
        "hand.L": (20, 0, 0), "hand.R": (25, 0, 0),
    }, (0, 0, -0.03 + 0.015 * math.sin(ph * 2))


def zombie_idle_pose(t=0.0):
    """殭屍站著：駝背、頭垂到一邊、手臂無力地垂著。"""
    sway = math.sin(t * 2 * math.pi) * 3
    return {
        "pelvis": (0, 4, 0), "spine": (20 + sway, -6, 0), "head": (24, 14, 20),
        "upperarm.L": (-6, 0, 6), "upperarm.R": (4, 0, -8),
        "forearm.L": (-14, 0, 0), "forearm.R": (-6, 0, 0),
        "thigh.R": (4, 0, 4), "shin.R": (10, 0, 0), "thigh.L": (-4, 0, 0), "shin.L": (6, 0, 0),
    }, (0, 0, -0.02)


def zombie_grab_pose(t):
    """殭屍撲抓：雙手往前伸、身體前傾、頭往前咬。t 0→1 是撲過去的過程。"""
    k = math.sin(min(1.0, t * 1.3) * math.pi / 2)
    return {
        "pelvis": (6 * k, 0, 0), "spine": (14 + 18 * k, 0, 0), "head": (-10 * k, 0, 0),
        "upperarm.L": (-80 * k - 10, 0, -8), "upperarm.R": (-82 * k - 10, 0, 8),
        "forearm.L": (-10, 0, 0), "forearm.R": (-10, 0, 0),
        "thigh.L": (-20 * k, 0, 0), "shin.L": (18 * k, 0, 0), "thigh.R": (14 * k, 0, 0), "shin.R": (10 * k, 0, 0),
    }, (0, -0.15 * k, -0.04 * k)


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def fall_pose(t):
    """倒地（往前撲倒）：膝蓋先軟掉，再整個人往前倒，最後趴在地上。t = 0..1，最後一格就是「死了」的樣子。

    做法：整個身體以骨盆為中心往前轉將近 90°，同時把骨盆降到離地 15 公分。
    """
    buckle = ease(t * 2.5)                 # 前 40%：膝蓋彎下去
    k = ease((t - 0.2) / 0.8)              # 之後：往前倒
    return {
        "pelvis": (86 * k, 0, 0), "spine": (12 * buckle - 8 * k, 0, 0), "head": (-30 * k, 0, 14 * k),
        "thigh.L": (-30 * buckle * (1 - k), 0, 0), "shin.L": (50 * buckle * (1 - k) + 8 * k, 0, 0),
        "thigh.R": (-24 * buckle * (1 - k), 0, 4 * k), "shin.R": (40 * buckle * (1 - k) + 14 * k, 0, 0),
        "upperarm.L": (-140 * k, 0, 18 * k), "upperarm.R": (-120 * k, 0, -30 * k),
        "forearm.L": (-20 * k, 0, 0), "forearm.R": (-40 * k, 0, 0),
    }, (0, 0, -0.25 * buckle * (1 - k) - 0.78 * k)


def zombie_hurt_pose(t=0.0):
    """殭屍中彈：上身被打得往後仰、頭甩到一邊、手臂往兩旁張開。"""
    return {
        "pelvis": (-4, 0, 0), "spine": (-14, 0, 6), "head": (-28, 10, 16),
        "upperarm.L": (-30, 0, 24), "upperarm.R": (-22, 0, -26),
        "forearm.L": (-18, 0, 0), "forearm.R": (-12, 0, 0),
        "thigh.L": (-10, 0, 0), "shin.L": (14, 0, 0),
    }, (0, 0.05, -0.01)


def feed_pose(t):
    """跪在地上啃食：跪姿、身體壓低、頭往下一點一點的（序章第一隻殭屍）。"""
    nod = math.sin(t * 2 * math.pi)
    return {
        "pelvis": (16, 0, 0), "spine": (38 + 4 * nod, 0, 0), "head": (24 + 10 * nod, 0, 0),
        "thigh.L": (-78, 0, 0), "shin.L": (100, 0, 0), "thigh.R": (-22, 0, 0), "shin.R": (112, 0, 0),
        "upperarm.L": (-62, 0, 10), "upperarm.R": (-58, 0, -10),
        "forearm.L": (-50 - 6 * nod, 0, 0), "forearm.R": (-46 + 6 * nod, 0, 0),
    }, (0, -0.08, -0.46)


def shoot_pose(t):
    """開槍：瞄準姿勢＋後座力（第 0 格槍口往上跳，第 1 格回來）。"""
    ang, loc = aim_pose()
    kick = 1.0 if t < 0.5 else 0.3
    ang = dict(ang)
    ang["upperarm.R"] = (-82 - 14 * kick, 0, 18)
    ang["upperarm.L"] = (-78 - 12 * kick, 0, -28)
    ang["head"] = (-4 * kick, 0, -6)
    return ang, loc


def limp_pose(t):
    """危急時的走路：一隻手按著腹部、身體縮著、步伐小而拖。"""
    ang, loc = walk_pose(t)
    ph = t * 2 * math.pi
    ang = dict(ang)
    ang["spine"] = (18, 0, 6 - 3 * math.sin(ph))
    ang["upperarm.R"] = (-20, 0, -22)
    ang["forearm.R"] = (-95, 0, 0)
    ang["thigh.R"] = (ang["thigh.R"][0] * 0.5, 0, 0)
    ang["shin.R"] = (ang["shin.R"][0] * 0.4 + 6, 0, 0)
    return ang, (loc[0], loc[1], loc[2] - 0.03)


HUMAN_ANIMS = {
    "idle": (idle_pose, 1),
    "walk": (walk_pose, 8),
    "run": (run_pose, 6),
    "aim": (aim_pose, 1),
    "hurt": (hurt_pose, 1),
    "shoot": (shoot_pose, 2),
    "limp": (limp_pose, 8),
    "down": (fall_pose, 6),
}
ZOMBIE_ANIMS = {
    "idle": (zombie_idle_pose, 2),
    "walk": (shamble_pose, 8),
    "grab": (zombie_grab_pose, 4),
    "hurt": (zombie_hurt_pose, 1),
    "down": (fall_pose, 6),
    "feed": (feed_pose, 2),
}

# ---------------- 頭目用的動作
def heavy_walk_pose(t):
    """沉重、穩定的步伐（追擊者、主廚）：擺幅小、不拖腳、身體幾乎不晃。"""
    ph = t * 2 * math.pi
    th = 18 * math.sin(ph)
    return {
        "pelvis": (0, 0, 2 * math.sin(ph)), "spine": (4, 0, -3 * math.sin(ph)), "head": (-2, 0, 0),
        "thigh.L": (-th, 0, 0), "thigh.R": (th, 0, 0),
        "shin.L": (28 * max(0, math.sin(ph + 0.9)) + 4, 0, 0), "shin.R": (28 * max(0, math.sin(ph + 0.9 + math.pi)) + 4, 0, 0),
        "upperarm.L": (10 * math.sin(ph), 0, 10), "upperarm.R": (-10 * math.sin(ph), 0, -10),
        "forearm.L": (-12, 0, 0), "forearm.R": (-12, 0, 0),
    }, (0, 0, -0.01 * abs(math.cos(ph)))


def chop_pose(t):
    """由上往下的揮砍（右手）：舉高 → 砍下。"""
    k = t
    up = math.sin(min(1, k * 2) * math.pi / 2)            # 前半舉起
    down = max(0.0, (k - 0.5) * 2)                         # 後半砍下
    a = -150 * up + 170 * down
    return {
        "spine": (6 + 20 * down, 0, 15 - 25 * down), "head": (-6, 0, 0),
        "upperarm.R": (a, 0, -15), "forearm.R": (-30 + 20 * down, 0, 0),
        "upperarm.L": (-30, 0, 20), "forearm.L": (-40, 0, 0),
        "thigh.L": (-15, 0, 0), "shin.L": (15, 0, 0), "thigh.R": (10, 0, 0),
    }, (0, -0.05 * down, -0.03 * down)


def punch_pose(t):
    """重拳（右手）：收拳 → 打出。"""
    k = math.sin(t * math.pi)
    return {
        "spine": (8, 0, 20 - 45 * k), "head": (0, 0, -10 * k),
        "upperarm.R": (-20 - 65 * k, 0, -25 + 20 * k), "forearm.R": (-90 + 85 * k, 0, 0),
        "upperarm.L": (-25, 0, 15), "forearm.L": (-80, 0, 0),
        "thigh.L": (-18 * k, 0, 0), "shin.L": (12 * k, 0, 0), "thigh.R": (12 * k, 0, 0),
    }, (0, -0.08 * k, -0.02)


def throw_pose(t):
    """把東西舉過頭丟出去（雙手）。"""
    up = math.sin(min(1, t * 1.6) * math.pi / 2)
    rel = max(0.0, (t - 0.6) / 0.4)
    a = -160 * up + 120 * rel
    return {
        "spine": (-10 * up + 30 * rel, 0, 0), "head": (-10 * up, 0, 0),
        "upperarm.L": (a, 0, 15), "upperarm.R": (a, 0, -15),
        "forearm.L": (-40, 0, 0), "forearm.R": (-40, 0, 0),
        "thigh.L": (-10 * rel, 0, 0), "shin.L": (10 * rel, 0, 0),
    }, (0, 0, 0)


def knockdown_pose(t):
    """被擊倒：跪下 → 雙手撐地（追擊者會再站起來）。"""
    k = math.sin(min(1, t * 1.2) * math.pi / 2)
    return {
        "pelvis": (20 * k, 0, 0), "spine": (35 * k, 0, 0), "head": (20 * k, 0, 0),
        "thigh.L": (-80 * k, 0, 0), "shin.L": (95 * k, 0, 0),
        "thigh.R": (-20 * k, 0, 0), "shin.R": (110 * k, 0, 0),
        "upperarm.L": (-40 * k, 0, 10), "upperarm.R": (-40 * k, 0, -10),
        "forearm.L": (-20 * k, 0, 0), "forearm.R": (-20 * k, 0, 0),
    }, (0, -0.1 * k, -0.45 * k)




# ======================================================================
# Sprite 輸出
# ======================================================================

SPRITE_W, SPRITE_H = 64, 128          # 一格 sprite 的畫布（像素）
PIX_PER_M = 62                        # 1.82 m ≈ 113 px（站在畫面最前景時的大小）
CENTER_Z = 0.91                       # sprite 攝影機對準的高度（大型頭目會調高）


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
    """direction 0..7：角色面向哪個方向（0 = 面向鏡頭，2 = 面向畫面左邊，4 = 背對鏡頭，6 = 面向畫面右邊）。

    做法：轉攝影機而不是轉角色。elevation 是俯角（固定視角大多從上往下看）。
    """
    yaw = math.radians(direction * 45)
    el = math.radians(elevation)
    dist = 10
    # 角色面向 -y；攝影機在角色前方（-y）時，看到的是正面
    cx = math.sin(yaw) * math.cos(el) * dist
    cy = -math.cos(yaw) * math.cos(el) * dist
    cz = math.sin(el) * dist + CENTER_Z
    cam.location = (cx, cy, cz)
    d = Vector((0, 0, CENTER_Z)) - cam.location
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
        "pivot": [SPRITE_W // 2, round(SPRITE_H / 2 + CENTER_Z * math.cos(math.radians(18)) * PIX_PER_M)],
        "pixels_per_meter": PIX_PER_M,
        "directions": "0 = facing camera, 2 = facing screen left, 4 = facing away, 6 = facing screen right",
        "rows": [{"anim": an, "dir": d, "frames": anims[an][1]} for (an, d) in rows],
    }
    with open(os.path.join(out_dir, f"{name}_sheet.json"), "w") as f:
        json.dump(meta, f, indent=1)
    return frames


def load_character(name):
    import importlib.util
    path = os.path.join(ROOT, "characters", name + ".py")
    spec = importlib.util.spec_from_file_location("char_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    import types
    name = sys.argv[1] if len(sys.argv) > 1 else "cole"
    mod = load_character(name)
    kit.reset_scene()
    C = sys.modules[__name__] if __name__ in sys.modules else types.SimpleNamespace(**globals())
    rig, parts = mod.build(C)
    # 身高：整副骨架等比例縮放（建模一律用 1.82 m 的骨架）
    sc = getattr(mod, "HEIGHT", 1.82) / 1.82
    rig.scale = (sc, sc, sc)
    bpy.context.view_layer.update()
    global SPRITE_W, SPRITE_H, CENTER_Z
    # 角色可以指定自己的 sprite 畫布。人形預設 144 × 160：倒在地上的身體（約 1.8 公尺、往鏡頭這邊倒）才放得下；
    # 匯出資源包時會裁掉透明的邊，畫布大一點不佔空間
    SPRITE_W, SPRITE_H = getattr(mod, "FRAME", (144, 160))
    CENTER_Z = getattr(mod, "CENTER_Z", 0.91)
    anims = getattr(mod, "ANIMS", "human")
    if isinstance(anims, str):
        anims = {"human": HUMAN_ANIMS, "zombie": ZOMBIE_ANIMS}[anims]
    elif callable(anims):
        anims = anims(sys.modules[__name__])        # 角色檔可以用函式組合自己的動作
    out_dir = os.path.join(ROOT, "art", "characters", name)
    frames = render_sprites(name, rig, out_dir, anims=anims)
    # 預覽：第一個動作的 8 方向＋每個動作在方向 1 的所有格，放大 3 倍
    first = next(iter(anims))
    rows = 1 + len(anims)
    cols = max(8, max(n for (_f, n) in anims.values()))
    prev = Image.new("RGBA", (cols * SPRITE_W, rows * SPRITE_H), (40, 36, 44, 255))
    for d in range(8):
        prev.alpha_composite(frames[(first, d, 0)], (d * SPRITE_W, 0))
    for r, (an, (_fn, n)) in enumerate(anims.items()):
        for f in range(n):
            prev.alpha_composite(frames[(an, 1, f)], (f * SPRITE_W, (r + 1) * SPRITE_H))
    prev = prev.resize((prev.width * 2, prev.height * 2), Image.NEAREST)
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    prev.save(os.path.join(ROOT, "build", f"{name}_turnaround.png"))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "build", f"{name}.blend"))
    print("done")


if __name__ == "__main__":
    sys.modules.setdefault("character", sys.modules[__name__])
    main()
