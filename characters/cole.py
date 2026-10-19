"""柯爾・哈特利（主角）：松脊郡警局菜鳥副警長。

造型：卡其色制服襯衫、黑色戰術背心（正面警徽、背面 SHERIFF 字樣條）、勤務腰帶、
右大腿槍套、深橄欖色長褲、靴子；深棕色短髮側分。身高 1.82 m。
"""
import os

HEIGHT = 1.82
ANIMS = "human"


def build(C):
    T = lambda n, c, k=0.1, seed=0: C.char_texture("cole_" + n, c, k, seed=seed)
    tex = {
        "shirt": T("shirt", "#8a7a58", 0.10, 1),        # 卡其色制服襯衫
        "vest": T("vest", "#1a1c1e", 0.12, 2),
        "patch": T("patch", "#b8a038", 0.06, 10),       # SHERIFF 字樣（遠看是一條黃色）
        "vest_plain": T("vest_plain", "#1a1c1e", 0.12, 3),
        "pants": T("pants", "#2e3426", 0.10, 4),        # 深橄欖色長褲
        "boots": T("boots", "#141210", 0.10, 5),
        "belt": T("belt", "#0e0e0e", 0.08, 6),
        "skin": T("skin", "#c49274", 0.05, 7),
        "hair": T("hair", "#2a1c14", 0.15, 8),
        "glove": T("glove", "#121212", 0.08, 9),
    }
    fpath = os.path.join(C.ROOT, "build", "chartex", "cole_face.png")
    C.face_texture(fpath, "#c49274", "#24180f", "#1a1410", "#8a5a48", stubble="#5a4636")
    tex["face"] = fpath
    M = {k: C.tex_mat("cole_" + k, v) for k, v in tex.items()}
    M["gold"] = C.kit.mat("badge_gold", "brass", metal=0.8, rough=0.35)
    M["steel"] = C.kit.mat("gun_steel", color=(0.08, 0.08, 0.09), metal=0.8, rough=0.4)

    rig = C.make_armature("cole_rig")
    parts = []
    P = lambda ob, bone: parts.append((ob, bone))
    loft, block, J = C.loft, C.block, C.J

    # ---------------- 骨盆：褲子＋勤務腰帶
    P(loft("pelvis", [(0.0, 0, 0, 0.17, 0.12), (0.5, 0, 0, 0.175, 0.125), (1.0, 0, 0, 0.16, 0.11)],
           M["pants"], (0, 0, 0.86), (0, 0, 1.06)), "pelvis")
    P(loft("belt", [(0, 0, 0, 0.185, 0.135), (1, 0, 0, 0.185, 0.135)], M["belt"], (0, 0, 0.98), (0, 0, 1.04)), "pelvis")
    P(block("buckle", (-0.03, -0.142, 0.985), (0.03, -0.13, 1.035), M["gold"]), "pelvis")
    for x in (-0.12, 0.08):
        P(block("pouch", (x, -0.145, 0.95), (x + 0.05, -0.115, 1.03), M["belt"]), "pelvis")

    # ---------------- 軀幹：襯衫＋戰術背心（胸寬、腰窄）
    torso = [(0.0, 0, 0, 0.165, 0.115), (0.3, 0, -0.005, 0.17, 0.122), (0.7, 0, -0.01, 0.19, 0.132), (0.9, 0, 0, 0.19, 0.12), (1.0, 0, 0, 0.12, 0.08)]
    P(loft("torso", torso, M["shirt"], (0, 0, 1.03), (0, 0, 1.5)), "spine")
    vest = [(0.0, 0, 0, 0.178, 0.128), (0.35, 0, -0.005, 0.186, 0.137), (0.75, 0, -0.012, 0.198, 0.145), (0.95, 0, -0.005, 0.165, 0.13)]
    P(loft("vest", vest, M["vest"], (0, 0, 1.06), (0, 0, 1.45), cap0=False, cap1=False), "spine")
    for x in (-0.09, -0.03, 0.03):
        P(block("mag_pouch", (x, -0.165, 1.1), (x + 0.05, -0.13, 1.2), M["vest_plain"]), "spine")
    P(block("radio", (0.1, -0.16, 1.3), (0.15, -0.12, 1.4), M["vest_plain"]), "spine")
    P(block("badge", (-0.12, -0.152, 1.32), (-0.07, -0.145, 1.37), M["gold"]), "spine")
    P(block("back_patch", (-0.13, 0.135, 1.33), (0.13, 0.148, 1.39), M["patch"]), "spine")
    P(loft("collar", [(0, 0, 0, 0.075, 0.07), (1, 0, 0.005, 0.085, 0.078)], M["shirt"], (0, 0, 1.47), (0, 0, 1.53), cap0=False, cap1=False), "spine")
    for sg in (1, -1):    # 肩上的背心肩帶
        P(block("strap", (sg * 0.12 - 0.035, -0.12, 1.42), (sg * 0.12 + 0.035, 0.12, 1.47), M["vest_plain"]), "spine")

    # ---------------- 頭：脖子、頭、鼻樑、頭髮
    P(loft("neck", [(0, 0, 0, 0.055, 0.055), (1, 0, 0, 0.05, 0.05)], M["skin"], (0, 0, 1.48), (0, 0, 1.6)), "head")
    head_r = [(0.0, 0, -0.01, 0.045, 0.05), (0.12, 0, -0.025, 0.068, 0.075), (0.35, 0, -0.01, 0.083, 0.1),
              (0.6, 0, 0, 0.088, 0.105), (0.85, 0, 0.01, 0.085, 0.1), (1.0, 0, 0.01, 0.05, 0.06)]
    P(loft("head", head_r, M["face"], (0, -0.01, 1.58), (0, -0.01, 1.83), uv_mode="face",
           face_box=(-0.085, 0.085, 1.58, 1.80)), "head")
    P(block("nose", (-0.012, -0.128, 1.655), (0.012, -0.105, 1.71), M["skin"]), "head")
    cap = [(0.0, 0, 0.0, 0.094, 0.11), (0.45, 0, -0.003, 0.09, 0.104), (1.0, 0, -0.005, 0.05, 0.062)]
    P(loft("hair_cap", cap, M["hair"], (0, -0.012, 1.765), (0, -0.012, 1.86), cap0=False), "head")
    back = [(0.0, 0, -0.012, 0.07, 0.08), (0.3, 0, -0.012, 0.09, 0.103), (0.75, 0, -0.008, 0.095, 0.11), (1.0, 0, -0.005, 0.094, 0.11)]
    P(loft("hair_back", back, M["hair"], (0, -0.01, 1.6), (0, -0.01, 1.77), cap0=False, cap1=False,
           keep=lambda c: c.y > -0.035), "head")
    P(block("fringe", (-0.075, -0.118, 1.765), (0.05, -0.088, 1.8), M["hair"]), "head")
    P(block("fringe_side", (0.05, -0.112, 1.775), (0.085, -0.085, 1.81), M["hair"]), "head")
    for sg in (1, -1):
        P(block("sideburn", (min(sg * 0.082, sg * 0.095), -0.06, 1.66), (max(sg * 0.082, sg * 0.095), -0.02, 1.74), M["hair"]), "head")
        P(block("ear", (min(sg * 0.088, sg * 0.1), -0.02, 1.66), (max(sg * 0.088, sg * 0.1), 0.01, 1.72), M["skin"]), "head")

    # ---------------- 手臂（長袖襯衫、黑色手套）、腿（褲子、靴子）
    C.arms(C, P, M["shirt"], M["shirt"], M["glove"])
    C.legs(C, P, M["pants"], M["pants"], M["boots"])
    # 槍套（右腿外側）＋配槍
    P(block("holster", (-0.2, -0.05, 0.68), (-0.155, 0.05, 0.9), M["belt"]), "thigh.R")
    P(block("holster_strap", (-0.19, -0.07, 0.72), (-0.07, 0.07, 0.75), M["belt"]), "thigh.R")
    P(block("gun_grip", (-0.195, -0.02, 0.9), (-0.16, 0.035, 0.98), M["steel"]), "thigh.R")
    return C.finish(C, rig, parts)
