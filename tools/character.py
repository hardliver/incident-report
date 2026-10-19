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

def char_texture(name, base, noise=0.08, size=32, seed=0, stripes=None, blood=0.0, tears=0.0, rot=0.0):
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
        low = r.random((size // 4, size // 4))
        big = np.asarray(Image.fromarray((low * 255).astype(np.uint8)).resize((size, size), Image.BILINEAR)) / 255.0
        m = (big > 1 - frac)[..., None]
        cc = np.array(color, float)
        arr[:] = np.where(m, arr * (1 - mix) + cc * mix, arr)
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


def face_texture(path, skin, brow, eye, lip, stubble=None, size=64, zombie=False):
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


def make_armature(name="rig", joints=None):
    joints = joints or J
    ad = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, ad)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    for (bn, h, t, parent) in BONES:
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


def finish(C, rig, parts):
    for ob, bone in parts:
        for poly in ob.data.polygons:
            poly.use_smooth = False
        C.attach(ob, rig, bone)
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


HUMAN_ANIMS = {
    "idle": (idle_pose, 1),
    "walk": (walk_pose, 8),
    "run": (run_pose, 6),
    "aim": (aim_pose, 1),
    "hurt": (hurt_pose, 1),
}
ZOMBIE_ANIMS = {
    "idle": (zombie_idle_pose, 2),
    "walk": (shamble_pose, 8),
    "grab": (zombie_grab_pose, 4),
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
    anims = getattr(mod, "ANIMS", "human")
    if isinstance(anims, str):
        anims = {"human": HUMAN_ANIMS, "zombie": ZOMBIE_ANIMS}[anims]
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
