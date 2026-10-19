"""殭屍：莊園女僕。黑色連身裙、白色圍裙（已經被血染了一大片）、頭上的白色髮飾。

比宴會賓客瘦、動作一樣是拖行。圍裙的白色在暗處很顯眼，玩家遠遠就看得到。
"""
import os

HEIGHT = 1.64
ANIMS = "zombie"


def build(C):
    T = lambda n, c, k=0.1, seed=0, **kw: C.char_texture("zm_" + n, c, k, seed=seed, **kw)
    tex = {
        "dress": T("dress", "#1a1a20", 0.12, 51, blood=0.2, tears=0.1),
        "apron": T("apron", "#b0aca0", 0.08, 52, blood=0.55),
        "stock": T("stock", "#2a2828", 0.1, 53, tears=0.25),
        "shoes": T("shoes", "#0c0a0a", 0.08, 54),
        "skin": T("skin", "#8e8c80", 0.12, 55, rot=0.3, blood=0.12),
        "hair": T("hair", "#2a201a", 0.18, 56),
        "cap": T("cap", "#b8b4a8", 0.06, 57),
    }
    fpath = os.path.join(C.ROOT, "build", "chartex", "zm_face.png")
    C.face_texture(fpath, "#8e8c80", "#2a2620", "#1a1a12", "#3a2a24", zombie=True)
    tex["face"] = fpath
    M = {k: C.tex_mat("zm_" + k, v) for k, v in tex.items()}

    J = dict(C.J)
    for k_, (x, y, z) in list(J.items()):
        if k_.split(".")[0] in ("shoulder", "elbow", "wrist", "hand_end"):
            J[k_] = (x * 0.86, y, z)
    rig = C.make_armature("zm_rig", joints=J)
    parts = []
    P = lambda ob, bone: parts.append((ob, bone))
    loft, block = C.loft, C.block

    # 裙子（掛在骨盆上，裙擺到膝蓋）
    skirt = [(0.0, 0, 0, 0.23, 0.2), (0.5, 0, 0, 0.2, 0.17), (1.0, 0, 0, 0.16, 0.12)]
    P(loft("skirt", skirt, M["dress"], (0, 0, 0.5), (0, 0, 1.06), cap0=False,
           keep=lambda c: not (c.z < 0.62 and c.x > 0.08 and c.y < 0)), "pelvis")       # 裙擺被撕掉一角
    P(loft("apron_skirt", [(0.0, 0, -0.02, 0.17, 0.2), (1.0, 0, -0.01, 0.14, 0.14)], M["apron"], (0, 0, 0.55), (0, 0, 1.04),
           cap0=False, cap1=False, keep=lambda c: c.y < -0.07), "pelvis")
    torso = [(0.0, 0, 0, 0.14, 0.105), (0.3, 0, -0.005, 0.135, 0.1), (0.65, 0, -0.012, 0.155, 0.12), (0.9, 0, 0, 0.16, 0.105), (1.0, 0, 0, 0.1, 0.07)]
    P(loft("torso", torso, M["dress"], (0, 0, 1.0), (0, 0, 1.5)), "spine")
    P(loft("apron_top", [(0, 0, -0.01, 0.145, 0.11), (1, 0, -0.012, 0.15, 0.125)], M["apron"], (0, 0, 1.02), (0, 0, 1.35),
           cap0=False, cap1=False, keep=lambda c: c.y < -0.085 and abs(c.x) < 0.09), "spine")
    P(loft("collar", [(0, 0, 0, 0.07, 0.065), (1, 0, 0.004, 0.078, 0.072)], M["apron"], (0, 0, 1.47), (0, 0, 1.52), cap0=False, cap1=False), "spine")

    P(loft("neck", [(0, 0, 0, 0.045, 0.045), (1, 0, 0, 0.042, 0.042)], M["skin"], (0, 0, 1.48), (0, 0, 1.6)), "head")
    head_r = [(0.0, 0, -0.012, 0.04, 0.045), (0.12, 0, -0.024, 0.06, 0.068), (0.35, 0, -0.01, 0.076, 0.094),
              (0.6, 0, 0, 0.082, 0.098), (0.85, 0, 0.01, 0.078, 0.094), (1.0, 0, 0.01, 0.046, 0.054)]
    P(loft("head", head_r, M["face"], (0, -0.01, 1.58), (0, -0.01, 1.81), uv_mode="face",
           face_box=(-0.078, 0.078, 1.58, 1.78)), "head")
    # 盤起來但已經散掉的頭髮＋白色髮飾
    cap = [(0.0, 0, 0.0, 0.088, 0.104), (0.45, 0, -0.003, 0.085, 0.098), (1.0, 0, -0.005, 0.048, 0.058)]
    P(loft("hair_cap", cap, M["hair"], (0, -0.012, 1.74), (0, -0.012, 1.84), cap0=False), "head")
    back = [(0.0, 0, -0.012, 0.08, 0.09), (0.5, 0, -0.012, 0.092, 0.106), (1.0, 0, -0.005, 0.09, 0.104)]
    P(loft("hair_back", back, M["hair"], (0, -0.01, 1.52), (0, -0.01, 1.75), cap0=False, cap1=False,
           keep=lambda c: c.y > -0.04), "head")
    P(block("loose_hair", (0.06, -0.09, 1.5), (0.09, -0.02, 1.74), M["hair"]), "head")
    P(block("maid_cap", (-0.07, -0.07, 1.8), (0.07, 0.0, 1.86), M["cap"]), "head")

    C.arms(C, P, M["dress"], M["skin"], M["skin"], joints=J, thick=0.82)
    C.legs(C, P, M["stock"], M["stock"], M["shoes"], joints=J, thick=0.78, boot_top=0.88, shoe_h=0.07, toe=-0.13)
    return C.finish(C, rig, parts)
