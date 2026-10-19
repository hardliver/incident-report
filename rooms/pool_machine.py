"""第 2 章：泳池機房。謎題 P7：依水管顏色與閥門順序把泳池的水抽乾。

範圍：x 0–5、y 0–4、高 2.8 m。門在南牆 x = 1（通往泳池）。
"""
import kit
from kit import mat


def build(k):
    kit.set_ambient((0.03, 0.03, 0.032), 1.0)
    kit.room_shell(k, 0, 0, 5, 4, 2.8, floor=mat("floor_stone", "floor_stone"), wall=mat("wall_stone", "wall_stone"),
                   ceiling=mat("plaster_grey", "plaster_grey"))
    kit.door(k, 1.0, 0.0, 0, w=0.9, h=2.2, tex="metal_steel")
    kit.pipes_valves(k, 0.3, 4.7, 3.75, 0.5)
    kit.pump_tank(k, 3.8, 1.5, 0.55, 1.8)
    kit.pump_tank(k, 2.4, 1.3, 0.4, 1.4)
    kit.shelf_unit(k, 0.25, 2.0, -90, w=1.2, h=1.8, items="boxes", metal=True)
    # 牆上的閥門順序說明（被撕掉一半）
    k.box((1.7, 3.97, 1.95), (2.3, 4.0, 2.4), mat("paper", "paper"), uv=0.4, name="valve_notice")
    k.cyl((2.5, 2.0, 2.55), 0.05, 0.08, mat("bulb", color=(1.0, 0.85, 0.6), emit=7.0), seg=6, name="bulb")
    k.light("POINT", (2.5, 2.0, 2.4), (1.0, 0.8, 0.55), 45, radius=0.08, name="bulb_light")
    k.light("POINT", (0.6, 3.4, 0.4), (0.9, 0.2, 0.1), 6, radius=0.05, name="pump_led")
    return {
        "tint": (0.85, 0.8, 0.72),
        "cameras": [
            {"id": "back", "pos": (2.4, 3.4, 2.5), "target": (1.2, 0.4, 0.6), "fov": 74},
            {"id": "door", "pos": (0.4, 0.4, 2.4), "target": (3.0, 3.6, 0.9), "fov": 72},
            {"id": "valves", "pos": (3.0, 1.0, 1.7), "target": (2.2, 3.9, 1.0), "fov": 72},
        ],
        "walk": [[(0.3, 0.3), (4.7, 0.3), (4.7, 3.5), (0.3, 3.5)]],
        "blocks": [[(3.2, 0.9), (4.4, 0.9), (4.4, 2.1), (3.2, 2.1)], [(1.95, 0.85), (2.85, 0.85), (2.85, 1.75), (1.95, 1.75)],
                   [(0.0, 1.4), (0.5, 1.4), (0.5, 2.6), (0.0, 2.6)]],
        "zones": [
            {"camera": "door", "poly": [(0, 0), (5, 0), (5, 2.3), (0, 2.3)]},
            {"camera": "valves", "poly": [(0, 2.3), (5, 2.3), (5, 4), (0, 4)]},
        ],
        "doors": [{"id": "south", "poly": [(0.5, 0.0), (1.5, 0.0), (1.5, 0.35), (0.5, 0.35)], "to": "pool", "spawn": {}}],
        "spawn": {"x": 1.0, "y": 0.8, "yaw": 0},
    }
