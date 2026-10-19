"""第 2 章：客房走廊（二樓東翼）。謎題 P8（誰住哪一間）、上線第一戰（B3）、看門犬從東端的窗戶破窗而入。

範圍：x 0–16、y 0–2.6、高 3.0 m（東西向的長走廊）。客房 301–308 在南北兩側。
"""
import kit
from kit import mat


def build(k):
    kit.set_ambient((0.03, 0.028, 0.032), 1.0)
    kit.corridor(k, 0, 0, 16, 2.6, 3.0, wall_tex="wallpaper_damask_red", runner="carpet_red")
    kit.door(k, 0.0, 1.3, -90, w=1.0, h=2.4)          # 西：樓梯（往東側走廊）
    for i, x in enumerate((2.5, 6.0, 9.5, 13.0)):
        kit.door(k, x, 2.6, 180, w=0.9, h=2.3)          # 北側：301、303、305、307
        kit.room_door_number(k, x, 2.6, 2.45, 180)
        kit.door(k, x + 1.2, 0.0, 0, w=0.9, h=2.3)      # 南側：302、304、306、308
        kit.room_door_number(k, x + 1.2, 0.0, 2.45, 0)
    kit.broken_window(k, 16.0, 1.3, 0.9, 90, w=1.2, h=1.8, power=50)
    for x in (1.2, 4.5, 8.0, 11.5, 14.8):
        kit.wall_sconce(k, x, 2.58, 2.2, 180, power=14 if x != 8.0 else 0.2)
    kit.vase_table(k, 7.8, 0.25, 0)
    # 客房服務的推車（翻倒）
    k.box((10.4, 1.6, 0.0), (11.3, 2.2, 0.5), mat("metal_steel", "metal_steel", metal=0.6), occluder=True, name="cart")
    kit.cloche_plate(k, 10.2, 1.2, 0.0, open_=True)
    kit.blood_pool(k, 12.6, 1.4, 0.45, seed=21)
    return {
        "tint": (0.85, 0.75, 0.7),
        "cameras": [
            {"id": "west", "pos": (0.4, 0.3, 2.5), "target": (9.0, 1.6, 0.8), "fov": 62},
            {"id": "mid", "pos": (8.0, 2.3, 2.6), "target": (1.5, 0.8, 0.8), "fov": 66},
            {"id": "east", "pos": (9.0, 0.3, 2.5), "target": (16.0, 1.6, 1.0), "fov": 66},    # 對著破掉的窗（狗跳進來）
        ],
        "walk": [[(0.3, 0.3), (15.7, 0.3), (15.7, 2.3), (0.3, 2.3)]],
        "blocks": [[(7.3, 0.0), (8.3, 0.0), (8.3, 0.5), (7.3, 0.5)], [(10.3, 1.5), (11.4, 1.5), (11.4, 2.3), (10.3, 2.3)]],
        "zones": [
            {"camera": "mid", "poly": [(0, 0), (5.0, 0), (5.0, 2.6), (0, 2.6)]},
            {"camera": "west", "poly": [(5.0, 0), (10.0, 0), (10.0, 2.6), (5.0, 2.6)]},
            {"camera": "east", "poly": [(10.0, 0), (16, 0), (16, 2.6), (10.0, 2.6)]},
        ],
        "doors": [
            {"id": "west", "poly": [(0.0, 0.8), (0.4, 0.8), (0.4, 1.8), (0.0, 1.8)], "to": "hall_east", "spawn": {}},
            {"id": "306", "poly": [(10.2, 0.0), (11.2, 0.0), (11.2, 0.35), (10.2, 0.35)], "to": "guest_room", "spawn": {}},
        ],
        "spawn": {"x": 0.8, "y": 1.3, "yaw": 90},
    }
