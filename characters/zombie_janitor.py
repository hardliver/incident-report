"""殭屍：清潔人員。灰藍色連身工作服、工作帽、黃色橡膠手套、胸前的名牌。

是莊園裡最常見的員工殭屍：鑽石之夜那晚，他們還在走廊上打掃。
"""
HEIGHT = 1.74
ANIMS = "zombie"


def build(C):
    M = C.mats(C, "zj", {
        "shirt": ("#3e4a52", 0.12, 81, {"blood": 0.2, "tears": 0.08}),
        "pants": ("#3e4a52", 0.12, 82, {"blood": 0.1}),
        "shoes": ("#141210", 0.08, 83),
        "skin": ("#8a8a7c", 0.12, 84, {"rot": 0.4, "blood": 0.12}),
        "hair": ("#2a2420", 0.18, 85),
        "glove": ("#b0901c", 0.1, 86, {"blood": 0.3}),
        "tag": ("#c8c4b8", 0.05, 87),
        "cap": ("#2e3a42", 0.1, 88),
    })
    M["hand"] = M["glove"]
    M["face"] = C.zombie_face(C, "zj", "#8a8a7c")

    def extra(P, M, J):
        P(C.block("name_tag", (0.07, -0.142, 1.32), (0.13, -0.135, 1.35), M["tag"]), "spine")
        P(C.block("pocket", (-0.12, -0.14, 1.28), (-0.05, -0.13, 1.36), M["shirt"]), "spine")
        P(C.loft("cap", [(0, 0, 0, 0.096, 0.112), (1, 0, -0.005, 0.08, 0.09)], M["cap"], (0, -0.012, 1.74), (0, -0.012, 1.83), cap0=False), "head")
        P(C.block("brim", (-0.07, -0.17, 1.74), (0.07, -0.1, 1.752), M["cap"]), "head")

    rig, parts, P = C.humanoid(C, "zj", M, o={"hair": "short", "boot_top": 0.82}, build=extra)
    return C.finish(C, rig, parts)
