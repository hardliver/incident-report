"""小頭目 B2：年度體態冠軍（第 2 章，健身房）。

上半身的肌肉腫脹到撐破皮膚、背心只剩幾條布；腿卻很細（弱點）。脖子上掛著冠軍金牌。
"""
HEIGHT = 1.95
FRAME = (96, 152)
CENTER_Z = 1.0


def build(C):
    M = C.mats(C, "bb", {
        "skin": ("#8a7e70", 0.16, 131, {"rot": 0.25, "blood": 0.2, "tears": 0.12}),   # 撐裂的皮膚
        "shirt": ("#8a7e70", 0.16, 132, {"rot": 0.25, "blood": 0.2, "tears": 0.15}),
        "tank": ("#2a3a5a", 0.1, 133, {"tears": 0.4, "blood": 0.3}),
        "pants": ("#1a1a1e", 0.1, 134),
        "thigh": ("#8a7e70", 0.14, 135, {"rot": 0.35}),
        "shoes": ("#a8a49a", 0.1, 136),
        "hair": ("#1e1a16", 0.15, 137),
        "strap": ("#6a1414", 0.08, 138),
    })
    M["face"] = C.zombie_face(C, "bb", "#8a7e70")
    M["gold"] = C.kit.mat("badge_gold", "brass", metal=0.8, rough=0.35)

    def extra(P, M, J):
        # 只剩幾條布的背心
        P(C.loft("tank", [(0, 0, 0, 0.27, 0.19), (1, 0, 0, 0.29, 0.19)], M["tank"], (0, 0, 1.1), (0, 0, 1.38),
                 cap0=False, cap1=False, keep=lambda c: (c.z < 1.2) or (abs(c.x) < 0.1)), "spine")
        # 肩膀與背上腫起來的肌肉塊
        for sg in (1, -1):
            x0, x1 = sorted((sg * 0.12, sg * 0.3))
            P(C.block("trap", (x0, -0.08, 1.4), (x1, 0.12, 1.55), M["skin"]), "spine")
        P(C.block("hump", (-0.18, 0.08, 1.2), (0.18, 0.22, 1.5), M["skin"]), "spine")
        # 冠軍金牌
        P(C.block("medal_strap", (-0.05, -0.2, 1.3), (0.05, -0.19, 1.48), M["strap"]), "spine")
        P(C.block("medal", (-0.05, -0.21, 1.22), (0.05, -0.19, 1.31), M["gold"]), "spine")

    rig, parts, P = C.humanoid(C, "bb", M, build=extra,
                               o={"hair": "short", "torso_w": 1.45, "torso_d": 1.4, "chest": 1.35, "arm": 1.85, "leg": 0.72,
                                  "head": 0.9, "boot_top": 0.9})
    return C.finish(C, rig, parts)


def ANIMS(C):
    return {"idle": (C.zombie_idle_pose, 2), "walk": (C.heavy_walk_pose, 8), "throw": (C.throw_pose, 5),
            "charge": (C.run_pose, 6), "hurt": (C.hurt_pose, 1)}
