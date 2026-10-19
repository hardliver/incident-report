"""看門犬：剝了皮的狗（第 2 章破窗而入）。四足骨架。

外觀：沒有皮的肌肉（暗紅褐色）、露出的肋骨、長牙；項圈上還掛著「年度最佳業績」的金牌。
骨架：身體一根骨頭、脖子、頭、尾巴，四條腿各三節。面向 -y。
"""
import math

HEIGHT = 1.82            # 不縮放（狗的尺寸直接用公尺建模）
FRAME = (112, 80)        # 狗是橫的：畫布寬一點、矮一點
CENTER_Z = 0.5

J = {
    "hip": (0, 0.3, 0.56), "chest": (0, -0.24, 0.6), "neck_top": (0, -0.42, 0.74), "nose": (0, -0.74, 0.66),
    "tail0": (0, 0.36, 0.6), "tail1": (0, 0.66, 0.5),
}
for s, x in (("L", 0.1), ("R", -0.1)):
    J.update({
        f"fs.{s}": (x, -0.22, 0.52), f"fe.{s}": (x, -0.25, 0.3), f"fw.{s}": (x, -0.24, 0.07), f"ft.{s}": (x, -0.32, 0.02),
        f"hh.{s}": (x, 0.3, 0.52), f"hk.{s}": (x, 0.2, 0.32), f"ha.{s}": (x, 0.32, 0.14), f"ht.{s}": (x, 0.28, 0.02),
    })
BONES = [("body", "hip", "chest", None), ("neck", "chest", "neck_top", "body"), ("head", "neck_top", "nose", "neck"),
         ("tail", "tail0", "tail1", "body")]
for s in ("L", "R"):
    BONES += [(f"fu.{s}", f"fs.{s}", f"fe.{s}", "body"), (f"fl.{s}", f"fe.{s}", f"fw.{s}", f"fu.{s}"), (f"fp.{s}", f"fw.{s}", f"ft.{s}", f"fl.{s}"),
              (f"hu.{s}", f"hh.{s}", f"hk.{s}", "body"), (f"hl.{s}", f"hk.{s}", f"ha.{s}", f"hu.{s}"), (f"hp.{s}", f"ha.{s}", f"ht.{s}", f"hl.{s}")]


def build(C):
    M = C.mats(C, "dog", {
        "muscle": ("#5a2018", 0.2, 111, {"rot": 0.2, "tears": 0.15}),
        "dark": ("#2a0e0a", 0.15, 112),
        "bone": ("#c8bca0", 0.08, 113),
        "collar": ("#1a1414", 0.08, 114),
        "eye": ("#d8c860", 0.0, 115),
    })
    M["gold"] = C.kit.mat("badge_gold", "brass", metal=0.8, rough=0.35)
    rig = C.make_armature("dog_rig", joints=J, bones=BONES)
    parts = []
    P = lambda ob, bone: parts.append((ob, bone))
    loft, block = C.loft, C.block
    # 身體：從臀部到胸口，胸口比較深（往下的 ry 大）
    body = [(-0.08, 0, 0.0, 0.1, 0.11), (0.3, 0, 0.0, 0.11, 0.12), (0.65, 0, -0.03, 0.13, 0.16), (1.0, 0, -0.02, 0.12, 0.15), (1.12, 0, 0, 0.08, 0.1)]
    P(loft("body", body, M["muscle"], J["hip"], J["chest"]), "body")
    # 露出的肋骨（側面的白色細條）
    for i in range(5):
        y = -0.02 - i * 0.05
        for sg in (1, -1):
            x0, x1 = sorted((sg * 0.12, sg * 0.135))
            P(block("rib", (x0, y - 0.008, 0.46), (x1, y + 0.008, 0.66), M["bone"]), "body")
    P(loft("neck", [(0, 0, 0, 0.075, 0.08), (1, 0, 0, 0.065, 0.07)], M["muscle"], J["chest"], J["neck_top"]), "neck")
    P(loft("collar", [(0, 0, 0, 0.08, 0.085), (1, 0, 0, 0.08, 0.085)], M["collar"], (0, -0.36, 0.68), (0, -0.38, 0.71), cap0=False, cap1=False), "neck")
    P(block("medal", (-0.025, -0.44, 0.6), (0.025, -0.43, 0.65), M["gold"]), "neck")
    # 頭：上顎＋下顎（張著嘴）＋牙齒
    P(loft("skull", [(0, 0, 0, 0.07, 0.075), (0.4, 0, 0, 0.065, 0.065), (1.0, 0, 0.02, 0.03, 0.035)], M["muscle"], J["neck_top"], J["nose"]), "head")
    P(block("jaw", (-0.035, -0.72, 0.58), (0.035, -0.5, 0.62), M["dark"]), "head")
    for i in range(4):
        y = -0.7 + i * 0.045
        P(block("tooth", (-0.03, y, 0.62), (0.03, y + 0.012, 0.645), M["bone"]), "head")
    for sg in (1, -1):
        x0, x1 = sorted((sg * 0.045, sg * 0.062))
        P(block("eye", (x0, -0.56, 0.72), (x1, -0.54, 0.735), M["eye"]), "head")
        P(block("ear", (min(sg * 0.03, sg * 0.06), -0.43, 0.78), (max(sg * 0.03, sg * 0.06), -0.41, 0.84), M["dark"]), "head")
    P(loft("tail", [(0, 0, 0, 0.025, 0.025), (1, 0, 0, 0.008, 0.008)], M["muscle"], J["tail0"], J["tail1"]), "tail")
    # 四條腿
    for s in ("L", "R"):
        P(loft(f"fu.{s}", [(-0.1, 0, 0, 0.045, 0.06), (1, 0, 0, 0.03, 0.035)], M["muscle"], J[f"fs.{s}"], J[f"fe.{s}"]), f"fu.{s}")
        P(loft(f"fl.{s}", [(0, 0, 0, 0.028, 0.03), (1, 0, 0, 0.02, 0.022)], M["muscle"], J[f"fe.{s}"], J[f"fw.{s}"]), f"fl.{s}")
        x = J[f"fw.{s}"][0]
        P(block(f"fp.{s}", (x - 0.025, -0.33, 0.0), (x + 0.025, -0.22, 0.05), M["dark"]), f"fp.{s}")
        P(loft(f"hu.{s}", [(-0.1, 0, 0, 0.06, 0.08), (1, 0, 0, 0.035, 0.04)], M["muscle"], J[f"hh.{s}"], J[f"hk.{s}"]), f"hu.{s}")
        P(loft(f"hl.{s}", [(0, 0, 0, 0.03, 0.032), (1, 0, 0, 0.02, 0.022)], M["muscle"], J[f"hk.{s}"], J[f"ha.{s}"]), f"hl.{s}")
        x = J[f"ha.{s}"][0]
        P(block(f"hp.{s}", (x - 0.025, 0.22, 0.0), (x + 0.025, 0.33, 0.05), M["dark"]), f"hp.{s}")
    return C.finish(C, rig, parts)


def dog_idle(t):
    """低吼：頭壓低、身體往前傾、尾巴下垂。"""
    b = math.sin(t * 2 * math.pi) * 2
    return {"neck": (-25, 0, 0), "head": (15 + b, 0, 0), "tail": (25, 0, 0),
            "fu.L": (-8, 0, 0), "fu.R": (-8, 0, 0), "hu.L": (10, 0, 0), "hu.R": (10, 0, 0),
            "hl.L": (-15, 0, 0), "hl.R": (-15, 0, 0)}, (0, 0, -0.03)


def dog_run(t):
    """奔跑（gallop）：前腳一起、後腳一起，身體一伸一縮。"""
    ph = t * 2 * math.pi
    f = 40 * math.sin(ph)
    h = 40 * math.sin(ph + math.pi * 0.8)
    return {"body": (8 * math.sin(ph), 0, 0), "neck": (-15 - 8 * math.sin(ph), 0, 0), "head": (10, 0, 0), "tail": (-10 + 10 * math.sin(ph), 0, 0),
            "fu.L": (f, 0, 0), "fu.R": (f + 10, 0, 0), "fl.L": (-30 * max(0, math.sin(ph)), 0, 0), "fl.R": (-30 * max(0, math.sin(ph + 0.4)), 0, 0),
            "hu.L": (h, 0, 0), "hu.R": (h + 10, 0, 0), "hl.L": (25 * max(0, -math.sin(ph)), 0, 0), "hl.R": (25 * max(0, -math.sin(ph + 0.4)), 0, 0)}, \
           (0, 0, 0.05 * abs(math.sin(ph)))


def dog_lunge(t):
    """撲咬：後腳蹬地、整隻往前上方撲、嘴張開。"""
    k = math.sin(t * math.pi)
    return {"body": (-25 * k, 0, 0), "neck": (-10 * k, 0, 0), "head": (-20 * k, 0, 0), "tail": (-20 * k, 0, 0),
            "fu.L": (-70 * k, 0, 0), "fu.R": (-60 * k, 0, 0), "fl.L": (-40 * k, 0, 0), "fl.R": (-40 * k, 0, 0),
            "hu.L": (50 * k, 0, 0), "hu.R": (45 * k, 0, 0)}, (0, -0.3 * k, 0.15 * k)


def ANIMS(C):
    return {"idle": (dog_idle, 2), "walk": (dog_run, 6), "attack": (dog_lunge, 4)}
