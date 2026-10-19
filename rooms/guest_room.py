"""第 2 章：客房 306（「從不退房」的那一間，P8 的答案）。房卡在這裡。

範圍：x 0–4.5、y 0–5.5、高 2.9 m。門在北牆 x = 1（通往客房走廊）。
"""
import kit
from kit import mat


def build(k):
    kit.set_ambient((0.028, 0.025, 0.026), 1.0)
    kit.room_shell(k, 0, 0, 4.5, 5.5, 2.9, floor=mat("carpet_green", "carpet_green"),
                   wall=mat("wallpaper_damask_cream", "wallpaper_damask_cream"), ceiling=mat("plaster_grey", "plaster_grey"),
                   wainscot=mat("wainscot_dark", "wainscot_dark"), wainscot_h=0.9)
    kit.door(k, 1.0, 5.5, 180, w=0.9, h=2.3)
    kit.door(k, 4.5, 4.2, 90, w=0.8, h=2.2)              # 浴室門（關著）
    kit.bed(k, 2.2, 1.3, 180, double=True)                # 床頭靠南牆
    kit.wardrobe(k, 0.32, 3.6, -90)
    kit.desk(k, 3.9, 2.6, 90, w=1.1, d=0.55)
    kit.desk_lamp(k, 3.95, 3.0, 0.77, power=14)
    kit.chair(k, 3.4, 2.6, 270, fabric="fabric_velvet_red")
    kit.armchair(k, 0.7, 0.7, 45)
    # 床邊的行李箱、散落的產品傳單、床頭櫃
    k.box((3.2, 0.3, 0.0), (3.9, 0.55, 0.5), mat("leather_brown", "leather_brown"), uv=0.5, occluder=True, name="suitcase")
    for i, (x, y) in enumerate(((2.8, 3.0), (3.0, 3.3), (2.5, 3.5), (1.6, 3.1))):
        k.box((x, y, 0.001), (x + 0.21, y + 0.3, 0.003), mat("paper", "paper"), uv=0.3, name="flyer")
    k.box((3.35, 0.05, 0.0), (3.85, 0.0, 0.0), mat("dark", color=(0.03, 0.02, 0.015)), name="nightstand_dummy")
    kit.cabinet(k, 0.85, 0.3, 0, w=0.5, d=0.4, h=0.55)
    kit.window(k, 0.0, 2.0, 1.0, -90, w=1.0, h=1.6, power=30)
    k.light("POINT", (2.2, 2.8, 2.6), (1.0, 0.8, 0.55), 18, radius=0.15, name="ceiling")
    return {
        "tint": (0.88, 0.8, 0.72),
        "cameras": [
            {"id": "door", "pos": (0.4, 5.1, 2.4), "target": (3.0, 1.0, 0.6), "fov": 72},
            {"id": "window", "pos": (4.1, 0.4, 2.3), "target": (1.0, 4.8, 0.8), "fov": 72},
        ],
        "walk": [[(0.3, 0.3), (4.2, 0.3), (4.2, 5.2), (0.3, 5.2)]],
        "blocks": [[(1.35, 0.0), (3.05, 0.0), (3.05, 2.4), (1.35, 2.4)], [(0.0, 3.0), (0.65, 3.0), (0.65, 4.2), (0.0, 4.2)],
                   [(3.1, 2.0), (4.5, 2.0), (4.5, 3.2), (3.1, 3.2)], [(0.2, 0.2), (1.2, 0.2), (1.2, 1.2), (0.2, 1.2)],
                   [(3.1, 0.2), (4.0, 0.2), (4.0, 0.7), (3.1, 0.7)]],
        "zones": [
            {"camera": "door", "poly": [(0, 0), (4.5, 0), (4.5, 2.8), (0, 2.8)]},
            {"camera": "window", "poly": [(0, 2.8), (4.5, 2.8), (4.5, 5.5), (0, 5.5)]},
        ],
        "doors": [{"id": "north", "poly": [(0.5, 5.1), (1.5, 5.1), (1.5, 5.5), (0.5, 5.5)], "to": "guest_corridor", "spawn": {}}],
        "spawn": {"x": 1.0, "y": 4.8, "yaw": 180},
    }
