"""諾拉・維加（女主角）：機車快遞員，來找失蹤的姊姊艾琳。

造型：磨損的黑色騎士皮夾克（背後有快遞公司的反光條）、深色牛仔褲、工作靴、
斜背的快遞包；深色長髮綁成低馬尾。身高 1.70 m（骨架以 1.82 m 建模後等比縮放）。
避開：紅色夾克、高馬尾、短褲（見 docs/art-style.md）。
"""
import os

HEIGHT = 1.70
ANIMS = "human"


def build(C):
    T = lambda n, c, k=0.1, seed=0: C.char_texture("nora_" + n, c, k, seed=seed)
    tex = {
        "jacket": T("jacket", "#2c2826", 0.18, 21),     # 磨損的黑色皮革（雜訊大一點＝磨損）
        "reflect": T("reflect", "#8ab0a8", 0.05, 22),   # 反光條（偏青的銀色）
        "shirt": T("shirt", "#5a5248", 0.08, 23),       # 灰褐色的 T 恤
        "jeans": T("jeans", "#232a38", 0.12, 24),       # 深色牛仔褲
        "boots": T("boots", "#2a1e16", 0.10, 25),       # 深棕色工作靴
        "bag": T("bag", "#3a3a2a", 0.10, 26),           # 橄欖灰的帆布快遞包
        "strap": T("strap", "#141414", 0.06, 27),
        "skin": T("skin", "#d0a084", 0.05, 28),
        "hair": T("hair", "#1e1410", 0.14, 29),
        "glove": T("glove", "#1a1414", 0.08, 30),
    }
    fpath = os.path.join(C.ROOT, "build", "chartex", "nora_face.png")
    C.face_texture(fpath, "#d0a084", "#2a1a12", "#120c0a", "#9a5a52")
    tex["face"] = fpath
    M = {k: C.tex_mat("nora_" + k, v) for k, v in tex.items()}
    M["zip"] = C.kit.mat("zip_steel", color=(0.35, 0.35, 0.36), metal=0.9, rough=0.35)

    # 骨架：肩膀窄一點、骨盆略寬
    J = dict(C.J)
    for s, sg in (("L", 1), ("R", -1)):
        for k_, (x, y, z) in list(J.items()):
            if k_.endswith("." + s) and k_.split(".")[0] in ("shoulder", "elbow", "wrist", "hand_end"):
                J[k_] = (x * 0.88, y, z)
            if k_.endswith("." + s) and k_.split(".")[0] in ("thigh", "knee", "ankle", "toe"):
                J[k_] = (x * 1.05, y, z)
    rig = C.make_armature("nora_rig", joints=J)
    parts = []
    P = lambda ob, bone: parts.append((ob, bone))
    loft, block = C.loft, C.block

    # ---------------- 骨盆：牛仔褲＋皮帶
    P(loft("pelvis", [(0.0, 0, 0, 0.17, 0.12), (0.5, 0, 0, 0.18, 0.13), (1.0, 0, 0, 0.155, 0.11)],
           M["jeans"], (0, 0, 0.86), (0, 0, 1.06)), "pelvis")
    P(loft("belt", [(0, 0, 0, 0.18, 0.13), (1, 0, 0, 0.18, 0.13)], M["strap"], (0, 0, 1.0), (0, 0, 1.035)), "pelvis")

    # ---------------- 軀幹：T 恤＋敞開的皮夾克（腰窄）
    torso = [(0.0, 0, 0, 0.15, 0.11), (0.3, 0, -0.005, 0.14, 0.105), (0.65, 0, -0.012, 0.16, 0.125), (0.9, 0, 0, 0.165, 0.11), (1.0, 0, 0, 0.11, 0.075)]
    P(loft("torso", torso, M["shirt"], (0, 0, 1.03), (0, 0, 1.5)), "spine")
    jacket = [(0.0, 0, 0, 0.168, 0.124), (0.3, 0, -0.004, 0.158, 0.118), (0.65, 0, -0.01, 0.176, 0.138), (0.92, 0, 0, 0.175, 0.124)]
    # 皮夾克：正面中央留開口（拉鍊敞開，看得到裡面的 T 恤）
    P(loft("jacket", jacket, M["jacket"], (0, 0, 1.0), (0, 0, 1.47), cap0=False, cap1=False,
           keep=lambda c: not (c.y < -0.09 and abs(c.x) < 0.045)), "spine")
    for sg in (1, -1):
        P(block("zip", (sg * 0.05 - 0.006, -0.133, 1.02), (sg * 0.05 + 0.006, -0.124, 1.42), M["zip"]), "spine")
    # 背後的反光條＋快遞公司標誌位置
    P(block("reflect_back", (-0.15, 0.124, 1.2), (0.15, 0.136, 1.235), M["reflect"]), "spine")
    P(block("reflect_back2", (-0.15, 0.13, 1.33), (0.15, 0.142, 1.365), M["reflect"]), "spine")
    # 衣領（立領）
    P(loft("collar", [(0, 0, 0, 0.08, 0.075), (1, 0, 0.003, 0.088, 0.082)], M["jacket"], (0, 0, 1.45), (0, 0, 1.53), cap0=False, cap1=False), "spine")
    # 快遞包的背帶（從右肩斜到左腰）＋包
    P(block("bag_strap", (-0.03, -0.135, 1.0), (0.03, -0.12, 1.47), M["strap"],
            C.Matrix.Translation((0, 0, 1.24)) @ C.Matrix.Rotation(0.55, 4, "Y") @ C.Matrix.Translation((0, 0, -1.24))), "spine")
    P(block("bag", (0.13, -0.08, 0.86), (0.2, 0.12, 1.06), M["bag"]), "pelvis")
    P(block("bag_flap", (0.13, -0.085, 0.98), (0.205, 0.125, 1.07), M["bag"]), "pelvis")

    # ---------------- 頭：脖子、頭（略小）、鼻、頭髮＋低馬尾
    P(loft("neck", [(0, 0, 0, 0.048, 0.048), (1, 0, 0, 0.045, 0.045)], M["skin"], (0, 0, 1.48), (0, 0, 1.6)), "head")
    head_r = [(0.0, 0, -0.012, 0.04, 0.045), (0.12, 0, -0.024, 0.062, 0.07), (0.35, 0, -0.01, 0.078, 0.096),
              (0.6, 0, 0, 0.084, 0.1), (0.85, 0, 0.01, 0.08, 0.096), (1.0, 0, 0.01, 0.048, 0.056)]
    P(loft("head", head_r, M["face"], (0, -0.01, 1.58), (0, -0.01, 1.82), uv_mode="face",
           face_box=(-0.08, 0.08, 1.58, 1.79)), "head")
    P(block("nose", (-0.01, -0.122, 1.66), (0.01, -0.1, 1.705), M["skin"]), "head")
    cap = [(0.0, 0, 0.0, 0.09, 0.106), (0.45, 0, -0.003, 0.087, 0.1), (1.0, 0, -0.005, 0.05, 0.06)]
    P(loft("hair_cap", cap, M["hair"], (0, -0.012, 1.75), (0, -0.012, 1.85), cap0=False), "head")
    back = [(0.0, 0, -0.012, 0.075, 0.085), (0.3, 0, -0.012, 0.09, 0.104), (0.75, 0, -0.008, 0.093, 0.108), (1.0, 0, -0.005, 0.09, 0.106)]
    P(loft("hair_back", back, M["hair"], (0, -0.01, 1.56), (0, -0.01, 1.76), cap0=False, cap1=False,
           keep=lambda c: c.y > -0.05), "head")
    # 側邊垂下的頭髮（蓋住耳朵，臉的兩側）
    for sg in (1, -1):
        x0, x1 = sorted((sg * 0.07, sg * 0.098))
        P(block("side_hair", (x0, -0.08, 1.6), (x1, 0.02, 1.78), M["hair"]), "head")
    # 斜瀏海（往一邊撥）
    P(block("fringe", (-0.08, -0.112, 1.74), (0.03, -0.085, 1.8), M["hair"]), "head")
    # 低馬尾：綁在後頸，往下垂到背
    P(loft("ponytail", [(0.0, 0, 0, 0.03, 0.03), (0.4, 0, 0, 0.034, 0.03), (1.0, 0, 0, 0.012, 0.012)],
           M["hair"], (0, 0.1, 1.63), (0, 0.15, 1.36)), "head")
    P(block("hair_tie", (-0.025, 0.085, 1.61), (0.025, 0.12, 1.645), M["strap"]), "head")

    # ---------------- 手臂（皮夾克袖子、無指手套）、腿（牛仔褲、工作靴）
    C.arms(C, P, M["jacket"], M["jacket"], M["glove"], joints=J, thick=0.88)
    C.legs(C, P, M["jeans"], M["jeans"], M["boots"], joints=J, thick=0.9, boot_top=0.72)
    return C.finish(C, rig, parts)
