"""第 1 章：冷凍庫。主廚一開始從這裡衝出來；也可以把它引回來關住。

範圍：x 0–4、y 0–5、高 2.8 m。門在東牆 y = 2.5（通往廚房）。冷的藍白色燈光。
"""
import kit
from kit import mat


def build(k):
    kit.set_ambient((0.03, 0.04, 0.05), 1.0)
    frost = mat("frost_metal", "frost_metal", metal=0.4, rough=0.5)
    kit.room_shell(k, 0, 0, 4, 5, 2.8, floor=mat("floor_stone", "floor_stone"), wall=frost, ceiling=frost)
    kit.door(k, 4.0, 2.5, 90, w=1.1, h=2.3, tex="metal_steel")
    # 吊肉的軌道＋兩排肉
    iron = mat("iron", color=(0.03, 0.03, 0.03), metal=0.8, rough=0.5)
    for x in (1.0, 2.6):
        k.box((x - 0.02, 0.3, 2.4), (x + 0.02, 4.7, 2.45), iron, name="meat_rail")
        for y in (0.9, 1.8, 3.0, 4.0):
            kit.carcass(k, x, y + (0.2 if x > 2 else 0), 2.4)
    kit.shelf_unit(k, 3.75, 4.5, 90, w=0.9, h=2.0, items="boxes", metal=True)
    kit.shelf_unit(k, 0.25, 4.5, -90, w=0.9, h=2.0, items="boxes", metal=True)
    # 燈：天花板一盞冷白色的燈（罩著鐵網）
    k.cyl((2.0, 2.5, 2.6), 0.12, 0.15, mat("cage_glow", color=(0.8, 0.9, 1.0), emit=8.0), seg=6, name="cage_lamp")
    k.light("POINT", (2.0, 2.5, 2.45), (0.7, 0.85, 1.0), 70, radius=0.15, name="cold_light")
    # 地上的一攤血（主廚的「工作」痕跡）
    kit.blood_pool(k, 1.9, 2.6, 0.6, seed=3)
    kit.blood_pool(k, 3.2, 1.6, 0.25, seed=5)
    return {
        "tint": (0.72, 0.82, 0.95),
        "cameras": [
            # 兩排吊著的肉把房間隔成三條走道：每條走道從兩頭各拍一次，才不會有死角
            {"id": "aisle", "pos": (1.8, 0.4, 2.5), "target": (1.8, 4.6, 0.3), "fov": 72},
            {"id": "aisle_n", "pos": (1.8, 4.75, 2.5), "target": (1.8, 0.5, 0.3), "fov": 72},
            {"id": "right_n", "pos": (3.1, 4.75, 2.5), "target": (3.3, 0.5, 0.3), "fov": 72},
            {"id": "door", "pos": (3.7, 0.4, 2.4), "target": (2.9, 4.6, 0.8), "fov": 70},
            {"id": "back", "pos": (0.4, 4.7, 2.2), "target": (3.6, 1.2, 0.9), "fov": 70},
        ],
        "walk": [[(0.3, 0.3), (3.7, 0.3), (3.7, 4.7), (0.3, 4.7)]],
        "blocks": [[(0.8, 0.6), (1.2, 0.6), (1.2, 4.3), (0.8, 4.3)], [(2.4, 0.8), (2.8, 0.8), (2.8, 4.5), (2.4, 4.5)],
                   [(3.3, 4.0), (4.0, 4.0), (4.0, 5.0), (3.3, 5.0)], [(0.0, 4.0), (0.7, 4.0), (0.7, 5.0), (0.0, 5.0)]],
        "zones": [
            {"camera": "back", "poly": [(0, 0), (4, 0), (4, 2.5), (0, 2.5)]},
            {"camera": "door", "poly": [(0, 2.5), (4, 2.5), (4, 5), (0, 5)]},
        ],
        "doors": [{"id": "east", "poly": [(3.6, 1.9), (4.0, 1.9), (4.0, 3.1), (3.6, 3.1)], "to": "kitchen", "spawn": {}}],
        "spawn": {"x": 3.4, "y": 2.5, "yaw": -90},
    }
