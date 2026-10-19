"""小頭目 B1：主廚（第 1 章，廚房＋冷凍庫）。

兩公尺高、體格巨大；廚師服的扣子被撐開、沾滿乾血；右手剁肉刀，左手和鐵鉤長在一起。
"""
HEIGHT = 2.05
FRAME = (88, 160)
CENTER_Z = 1.05


def build(C):
    M = C.mats(C, "bc", {
        "shirt": ("#a8a294", 0.12, 121, {"blood": 0.35, "tears": 0.08}),
        "pants": ("#2a2a2a", 0.08, 122, {"check": "#4a4842", "blood": 0.2}),
        "apron": ("#9a8e7c", 0.1, 123, {"blood": 0.5}),
        "shoes": ("#141414", 0.08, 124),
        "skin": ("#8a8072", 0.14, 125, {"rot": 0.4, "blood": 0.25}),
        "hair": ("#1a1612", 0.18, 126),
        "steel": ("#7a7a7c", 0.1, 127, {"blood": 0.3}),
        "rust": ("#4a2a1a", 0.15, 128),
        "handle": ("#2a1a10", 0.1, 129),
    })
    M["face"] = C.zombie_face(C, "bc", "#8a8072", scars=True)

    def extra(P, M, J):
        P(C.loft("apron", [(0.0, 0, -0.03, 0.24, 0.2), (1.0, 0, -0.02, 0.23, 0.18)], M["apron"], (0, 0, 0.5), (0, 0, 1.12),
                 cap0=False, cap1=False, keep=lambda c: c.y < -0.09), "pelvis")
        # 剁肉刀（右手）：刀柄＋寬刀面
        w = J["hand_end.R"]
        P(C.block("cleaver_handle", (w[0] - 0.02, w[1] - 0.02, w[2] - 0.02), (w[0] + 0.02, w[1] + 0.02, w[2] + 0.1), M["handle"]), "hand.R")
        P(C.block("cleaver_blade", (w[0] - 0.008, w[1] - 0.16, w[2] - 0.12), (w[0] + 0.008, w[1] + 0.04, w[2] - 0.0), M["steel"]), "hand.R")
        # 鐵鉤（左手，長在前臂上）
        e = J["wrist.L"]
        P(C.block("hook_shaft", (e[0] - 0.015, e[1] - 0.015, e[2] - 0.22), (e[0] + 0.015, e[1] + 0.015, e[2]), M["rust"]), "forearm.L")
        P(C.block("hook_tip", (e[0] - 0.015, e[1] - 0.12, e[2] - 0.24), (e[0] + 0.015, e[1] + 0.0, e[2] - 0.2), M["rust"]), "forearm.L")
        P(C.block("hook_point", (e[0] - 0.012, e[1] - 0.13, e[2] - 0.2), (e[0] + 0.012, e[1] - 0.1, e[2] - 0.13), M["rust"]), "forearm.L")

    rig, parts, P = C.humanoid(C, "bc", M, build=extra,
                               o={"hair": "patchy", "torso_w": 1.35, "torso_d": 1.35, "chest": 1.1, "arm": 1.45, "leg": 1.3,
                                  "head": 0.95, "boot_top": 0.88})
    return C.finish(C, rig, parts)


def ANIMS(C):
    return {"idle": (C.zombie_idle_pose, 2), "walk": (C.heavy_walk_pose, 8), "chop": (C.chop_pose, 6), "hurt": (C.hurt_pose, 1)}
