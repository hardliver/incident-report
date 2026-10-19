"""殭屍：普通百姓（男）。被叫來幫忙搬貨的鎮民：格子法蘭絨襯衫、牛仔褲、球鞋。"""
HEIGHT = 1.76
ANIMS = "zombie"


def build(C):
    M = C.mats(C, "zcm", {
        "shirt": ("#5a1e1a", 0.1, 61, {"plaid": "#1e1a14", "blood": 0.25, "tears": 0.1}),
        "pants": ("#2c3448", 0.12, 62, {"blood": 0.12, "tears": 0.15}),
        "shoes": ("#6a665e", 0.1, 63),
        "skin": ("#8c8a78", 0.12, 64, {"rot": 0.35, "blood": 0.15}),
        "hair": ("#4a3a2a", 0.18, 65),
        "cap": ("#2a3a2a", 0.1, 66),
    })
    M["face"] = C.zombie_face(C, "zcm", "#8c8a78")

    def extra(P, M, J):
        # 棒球帽（帽簷往前）
        P(C.loft("cap", [(0, 0, 0, 0.095, 0.11), (1, 0, -0.005, 0.07, 0.08)], M["cap"], (0, -0.012, 1.75), (0, -0.012, 1.84), cap0=False), "head")
        P(C.block("brim", (-0.075, -0.2, 1.75), (0.075, -0.1, 1.765), M["cap"]), "head")

    rig, parts, P = C.humanoid(C, "zcm", M, o={"hair": "short"}, build=extra)
    return C.finish(C, rig, parts)
