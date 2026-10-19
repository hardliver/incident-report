"""殭屍：宴會賓客（男）。鑽石之夜的經銷商，穿著被扯破的西裝。

外觀是恐怖的：灰白腐爛的皮膚、凹陷的眼窩、嘴邊的血；西裝與襯衫上都是乾掉的血。
「生前身分」只用胸前的經銷商名牌暗示（金色小牌），不做任何搞笑的造型。
"""
import os

HEIGHT = 1.78
ANIMS = "zombie"


def build(C):
    T = lambda n, c, k=0.1, seed=0, **kw: C.char_texture("zg_" + n, c, k, seed=seed, **kw)
    tex = {
        "suit": T("suit", "#2a2c34", 0.14, 41, blood=0.25, tears=0.12),
        "shirt": T("shirt", "#a8a290", 0.10, 42, blood=0.45, tears=0.05),
        "tie": T("tie", "#4a1414", 0.10, 43),
        "pants": T("pants", "#24262c", 0.12, 44, blood=0.15, tears=0.1),
        "shoes": T("shoes", "#0c0a0a", 0.08, 45),
        "skin": T("skin", "#8a8c7a", 0.12, 46, rot=0.35, blood=0.15),
        "hair": T("hair", "#3a342c", 0.18, 47),
    }
    fpath = os.path.join(C.ROOT, "build", "chartex", "zg_face.png")
    C.face_texture(fpath, "#8a8c7a", "#2a2620", "#1a1a12", "#3a2a24", zombie=True)
    tex["face"] = fpath
    M = {k: C.tex_mat("zg_" + k, v) for k, v in tex.items()}
    M["badge"] = C.kit.mat("badge_gold", "brass", metal=0.8, rough=0.35)

    rig = C.make_armature("zg_rig")
    parts = []
    P = lambda ob, bone: parts.append((ob, bone))
    loft, block = C.loft, C.block

    P(loft("pelvis", [(0.0, 0, 0, 0.175, 0.125), (0.5, 0, 0, 0.18, 0.13), (1.0, 0, 0, 0.17, 0.12)],
           M["pants"], (0, 0, 0.86), (0, 0, 1.06)), "pelvis")
    # 襯衫＋外套（外套前面敞開、一邊的衣襬被扯掉）
    torso = [(0.0, 0, 0, 0.17, 0.12), (0.3, 0, -0.01, 0.175, 0.13), (0.7, 0, -0.01, 0.18, 0.13), (0.92, 0, 0, 0.18, 0.115), (1.0, 0, 0, 0.11, 0.075)]
    P(loft("torso", torso, M["shirt"], (0, 0, 1.0), (0, 0, 1.5)), "spine")
    coat = [(0.0, 0, 0, 0.185, 0.136), (0.35, 0, -0.008, 0.19, 0.142), (0.75, 0, -0.01, 0.195, 0.14), (0.95, 0, 0, 0.17, 0.125)]
    P(loft("coat", coat, M["suit"], (0, 0, 0.9), (0, 0, 1.47), cap0=False, cap1=False,
           keep=lambda c: not (c.y < -0.1 and abs(c.x) < 0.07) and not (c.x < -0.1 and c.z < 1.05)), "spine")
    P(block("tie", (-0.018, -0.135, 1.15), (0.018, -0.125, 1.45), M["tie"],
            C.Matrix.Translation((0, 0, 1.45)) @ C.Matrix.Rotation(0.25, 4, "Y") @ C.Matrix.Translation((0, 0, -1.45))), "spine")
    P(block("name_badge", (0.08, -0.15, 1.33), (0.14, -0.142, 1.37), M["badge"]), "spine")
    P(loft("collar", [(0, 0, 0, 0.075, 0.07), (1, 0, 0.005, 0.085, 0.078)], M["shirt"], (0, 0, 1.47), (0, 0, 1.52), cap0=False, cap1=False), "spine")

    P(loft("neck", [(0, 0, 0, 0.052, 0.052), (1, 0, 0, 0.048, 0.048)], M["skin"], (0, 0, 1.48), (0, 0, 1.6)), "head")
    head_r = [(0.0, 0, -0.01, 0.045, 0.05), (0.12, 0, -0.025, 0.066, 0.074), (0.35, 0, -0.01, 0.082, 0.098),
              (0.6, 0, 0, 0.087, 0.104), (0.85, 0, 0.01, 0.083, 0.098), (1.0, 0, 0.01, 0.05, 0.058)]
    P(loft("head", head_r, M["face"], (0, -0.01, 1.58), (0, -0.01, 1.82), uv_mode="face",
           face_box=(-0.083, 0.083, 1.58, 1.79)), "head")
    P(block("nose", (-0.012, -0.125, 1.655), (0.012, -0.102, 1.7), M["skin"]), "head")
    # 稀疏、被扯掉一塊的頭髮
    cap = [(0.0, 0, 0.0, 0.09, 0.106), (0.45, 0, -0.003, 0.087, 0.1), (1.0, 0, -0.005, 0.048, 0.058)]
    P(loft("hair_cap", cap, M["hair"], (0, -0.012, 1.76), (0, -0.012, 1.85), cap0=False,
           keep=lambda c: not (c.x > 0.02 and c.y < 0.0)), "head")
    back = [(0.0, 0, -0.012, 0.07, 0.08), (0.4, 0, -0.012, 0.09, 0.103), (1.0, 0, -0.005, 0.09, 0.106)]
    P(loft("hair_back", back, M["hair"], (0, -0.01, 1.62), (0, -0.01, 1.77), cap0=False, cap1=False,
           keep=lambda c: c.y > -0.02), "head")

    C.arms(C, P, M["suit"], M["suit"], M["skin"])
    C.legs(C, P, M["pants"], M["pants"], M["shoes"], boot_top=0.9, shoe_h=0.08, toe=-0.15)
    return C.finish(C, rig, parts)
