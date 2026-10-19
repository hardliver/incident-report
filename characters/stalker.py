"""追擊者：上線（第 2 章末起）。前保鑣、最高階的「皇冠大使」。

2.3 公尺、剪裁完美的灰西裝、白襯衫、藍領帶、相對身體很小的頭、往後梳的頭髮、
耳麥、縫起來的嘴、發光的黃眼睛、巨大的手。動作穩定、不慌不忙。
避開：風衣、帽子（原作追擊者的造型）。
"""
HEIGHT = 2.3
FRAME = (96, 176)
CENTER_Z = 1.15


def build(C):
    M = C.mats(C, "st", {
        "coat": ("#4a4e58", 0.08, 141),
        "shirt": ("#c8c8c4", 0.05, 142),
        "pants": ("#42464e", 0.08, 143),
        "tie": ("#1c3c7a", 0.06, 144),
        "shoes": ("#0c0c0e", 0.05, 145),
        "skin": ("#7e8478", 0.1, 146, {"rot": 0.2}),
        "hair": ("#0e1012", 0.06, 147),
        "black": ("#0a0a0a", 0.04, 148),
        "red": ("#c01818", 0.0, 149),
    })
    M["face"] = C.zombie_face(C, "st", "#7e8478", stitches=True, glow_eyes="#f0d840")

    def extra(P, M, J):
        P(C.block("tie", (-0.022, -0.185, 1.12), (0.022, -0.174, 1.46), M["tie"]), "spine")
        P(C.block("pocket_sq", (0.1, -0.15, 1.36), (0.15, -0.142, 1.39), M["shirt"]), "spine")
        # 耳麥：頭箍＋耳罩＋麥克風桿＋紅色指示燈
        P(C.loft("headband", [(0, 0, 0, 0.085, 0.03), (1, 0, 0, 0.085, 0.03)], M["black"], (0, 0, 1.75), (0, 0, 1.77), cap0=False, cap1=False), "head")
        P(C.block("earcup", (0.075, -0.03, 1.62), (0.095, 0.02, 1.69), M["black"]), "head")
        P(C.block("mic_arm", (0.06, -0.12, 1.6), (0.075, -0.02, 1.615), M["black"]), "head")
        P(C.block("mic_led", (0.055, -0.125, 1.6), (0.07, -0.115, 1.615), M["red"]), "head")

    J = dict(C.J)
    rig, parts, P = C.humanoid(C, "st", M, joints=J, build=extra,
                               o={"hair": "short", "torso_w": 1.3, "torso_d": 1.15, "chest": 1.2, "arm": 1.3, "leg": 1.15,
                                  "head": 0.82, "boot_top": 0.94, "shoe_h": 0.09, "toe": -0.19, "coat_bottom": 0.78})
    # 巨大的手：以手腕為中心放大
    jj = C.J
    sw = 1.3 * 1.2 ** 0.5
    for ob, bone in parts:
        if bone.startswith("hand."):
            w = jj["wrist." + bone[-1]]
            C.scale_part(ob, 1.5, (w[0] * sw, w[1], w[2]))
    return C.finish(C, rig, parts)


def ANIMS(C):
    return {"idle": (C.idle_pose, 1), "walk": (C.heavy_walk_pose, 8), "punch": (C.punch_pose, 4), "down": (C.knockdown_pose, 3)}
