"""殭屍：健身房員工（第 2 章）。深色運動外套、運動褲、跑鞋；體格比一般殭屍壯。"""
HEIGHT = 1.8
ANIMS = "zombie"


def build(C):
    M = C.mats(C, "zgy", {
        "shirt": ("#1e2a3a", 0.1, 101, {"blood": 0.25, "tears": 0.1, "stripes": [(0.45, 0.52, "#a8a8a0")]}),
        "pants": ("#1a1e26", 0.1, 102, {"blood": 0.1, "tears": 0.1}),
        "shoes": ("#a8a49a", 0.1, 103),
        "skin": ("#8a8c7a", 0.12, 104, {"rot": 0.3, "blood": 0.15}),
        "hair": ("#1e1a16", 0.15, 105),
    })
    M["face"] = C.zombie_face(C, "zgy", "#8a8c7a")
    rig, parts, P = C.humanoid(C, "zgy", M, o={"hair": "short", "chest": 1.12, "arm": 1.12, "leg": 1.05, "boot_top": 0.9})
    return C.finish(C, rig, parts)
