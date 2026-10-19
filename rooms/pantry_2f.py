"""第 1 章：二樓配膳室。送餐升降機的上端；諾拉躲在升降機裡（P4 之後在這裡第一次見面）。

範圍：x 0–3、y 0–4、高 2.6 m。門在南牆 x = 1.5（通往二樓迴廊，第 2 章之後才會用到）。
"""
import kit
from kit import mat


def build(k):
    kit.set_ambient((0.022, 0.022, 0.026), 1.0)
    kit.room_shell(k, 0, 0, 3, 4, 2.6,
                   floor=mat("floor_wood_worn", "floor_wood_worn"),
                   wall=mat("plaster_cream", "plaster_cream"),
                   ceiling=mat("plaster_grey", "plaster_grey"),
                   wainscot=mat("wainscot_dark", "wainscot_dark"), wainscot_h=0.9)
    kit.door(k, 1.5, 0.0, 0, w=0.9, h=2.2)
    kit.dumbwaiter(k, 1.0, 3.98, 0.9, 180, open_=True)
    kit.shelf_unit(k, 2.75, 2.4, 90, w=1.6, h=2.1, items="jars")
    kit.shelf_unit(k, 0.25, 1.5, -90, w=1.4, h=2.1, items="cans")
    kit.boxes_stack(k, 2.4, 3.6, 0)
    kit.kitchen_counter(k, 2.2, 3.7, 180, w=1.0, d=0.5)
    kit.window(k, 3.0, 1.0, 1.3, 90, w=0.6, h=0.8, power=12, curtains=False)
    k.cyl((1.5, 2.0, 2.45), 0.04, 0.07, mat("bulb", color=(1.0, 0.85, 0.6), emit=6.0), seg=6, name="bulb")
    k.light("POINT", (1.5, 2.0, 2.3), (1.0, 0.8, 0.55), 22, radius=0.08, name="bulb_light")
    return {
        "tint": (0.85, 0.8, 0.75),
        "cameras": [
            {"id": "A", "pos": (2.7, 0.35, 2.2), "target": (0.9, 3.6, 0.8), "fov": 72},
            {"id": "B", "pos": (0.3, 3.6, 2.1), "target": (2.2, 0.4, 0.8), "fov": 72},
        ],
        "walk": [[(0.3, 0.3), (2.7, 0.3), (2.7, 3.7), (0.3, 3.7)]],
        "blocks": [[(2.5, 1.6), (3.0, 1.6), (3.0, 3.2), (2.5, 3.2)], [(0.0, 0.8), (0.5, 0.8), (0.5, 2.2), (0.0, 2.2)],
                   [(1.6, 3.2), (3.0, 3.2), (3.0, 4.0), (1.6, 4.0)]],
        "zones": [
            {"camera": "A", "poly": [(0, 1.8), (3, 1.8), (3, 4), (0, 4)]},
            {"camera": "B", "poly": [(0, 0), (3, 0), (3, 1.8), (0, 1.8)]},
        ],
        "doors": [{"id": "south", "poly": [(1.0, 0.0), (2.0, 0.0), (2.0, 0.35), (1.0, 0.35)], "to": "hall_2f", "spawn": {}}],
        "spawn": {"x": 1.0, "y": 3.2, "yaw": 180},
    }
