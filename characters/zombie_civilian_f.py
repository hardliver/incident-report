"""殭屍：普通百姓（女）。被朋友帶來參加鑽石之夜的鎮民：毛衣、長裙、長髮。"""
HEIGHT = 1.66
ANIMS = "zombie"


def build(C):
    M = C.mats(C, "zcf", {
        "shirt": ("#6a5a3a", 0.14, 71, {"blood": 0.3, "tears": 0.1}),     # 芥末色毛衣
        "pants": ("#2a2420", 0.1, 72),
        "skirt": ("#2a2a3a", 0.12, 73, {"blood": 0.15, "tears": 0.15}),
        "shin": ("#7a7462", 0.1, 74, {"tears": 0.2}),                     # 絲襪（破了）
        "shoes": ("#1a1414", 0.08, 75),
        "skin": ("#8e8a7c", 0.12, 76, {"rot": 0.3, "blood": 0.12}),
        "hair": ("#5a3a20", 0.18, 77),
    })
    M["face"] = C.zombie_face(C, "zcf", "#8e8a7c")
    J = dict(C.J)
    for k_, (x, y, z) in list(J.items()):
        if k_.split(".")[0] in ("shoulder", "elbow", "wrist", "hand_end"):
            J[k_] = (x * 0.87, y, z)
    rig, parts, P = C.humanoid(C, "zcf", M, joints=J,
                               o={"hair": "long", "torso_w": 0.9, "arm": 0.84, "leg": 0.8, "head": 0.95,
                                  "skirt": (0.5, 0.22), "boot_top": 0.9, "shoe_h": 0.07, "toe": -0.13,
                                  "skirt_keep": lambda c: not (c.z < 0.65 and c.x < -0.08)})
    return C.finish(C, rig, parts)
