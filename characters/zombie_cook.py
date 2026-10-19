"""殭屍：廚師（一般敵人，不是主廚頭目）。雙排扣白色廚師服、黑白小格子褲、圍裙、高帽。"""
HEIGHT = 1.78
ANIMS = "zombie"


def build(C):
    M = C.mats(C, "zk", {
        "shirt": ("#b8b4a8", 0.08, 91, {"blood": 0.4}),
        "pants": ("#2a2a2a", 0.08, 92, {"check": "#55534c", "blood": 0.1}),
        "apron": ("#c0bcb0", 0.06, 93, {"blood": 0.6}),
        "shoes": ("#141414", 0.08, 94),
        "skin": ("#8a8a7a", 0.12, 95, {"rot": 0.35, "blood": 0.2}),
        "hair": ("#2a2420", 0.18, 96),
        "hat": ("#c8c4b8", 0.05, 97),
        "button": ("#2a2a2a", 0.05, 98),
    })
    M["face"] = C.zombie_face(C, "zk", "#8a8a7a")

    def extra(P, M, J):
        for z in (1.18, 1.26, 1.34):          # 雙排扣
            for x in (-0.06, 0.06):
                P(C.block("button", (x - 0.01, -0.136, z), (x + 0.01, -0.13, z + 0.02), M["button"]), "spine")
        P(C.loft("apron", [(0.0, 0, -0.02, 0.17, 0.15), (1.0, 0, -0.01, 0.17, 0.13)], M["apron"], (0, 0, 0.55), (0, 0, 1.08),
                 cap0=False, cap1=False, keep=lambda c: c.y < -0.07), "pelvis")
        P(C.loft("hat", [(0, 0, 0, 0.09, 0.1), (0.4, 0, 0, 0.1, 0.11), (1, 0, 0, 0.11, 0.12)], M["hat"], (0, -0.01, 1.77), (0, -0.01, 1.98)), "head")

    rig, parts, P = C.humanoid(C, "zk", M, o={"hair": "short", "coat_bottom": 0.95}, build=extra)
    return C.finish(C, rig, parts)
