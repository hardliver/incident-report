"""第 2 章：更衣室（健身房旁）。兩排鐵櫃、長凳、後面是淋浴間。P6 的另一片槓片藏在打開的櫃子裡。

範圍：x 0–5、y 0–6、高 3.0 m。門在北牆 x = 2（通往健身房）。
"""
import kit
from kit import mat


def build(k):
    kit.set_ambient((0.035, 0.038, 0.04), 1.0)
    kit.room_shell(k, 0, 0, 5, 6, 3.0, floor=mat("tiles_white", "tiles_white"), wall=mat("tiles_white", "tiles_white"),
                   ceiling=mat("plaster_grey", "plaster_grey"))
    kit.door(k, 2.0, 6.0, 180, w=0.9, h=2.3)
    kit.lockers(k, 2.5, 5.97, 180, n=8, open_idx=(2, 6))
    kit.lockers(k, 0.02, 3.0, -90, n=6, open_idx=(4,))
    kit.bench(k, 2.6, 3.8, 0, L=2.4)
    kit.bench(k, 1.4, 2.2, 90, L=1.6)
    # 淋浴間：南側的隔板
    tile = mat("tiles_white", "tiles_white")
    for x in (2.0, 3.2, 4.4):
        k.box((x - 0.03, 0.0, 0.0), (x + 0.03, 1.3, 2.1), tile, uv=1, occluder=True, name="stall")
        k.box((x + 0.45, 0.02, 1.9), (x + 0.55, 0.12, 2.0), mat("chrome", color=(0.6, 0.6, 0.6), metal=0.9), name="shower_head")
    k.box((2.0, 0.0, 0.0), (5.0, 1.3, 0.004), mat("wet_tile", color=(0.05, 0.06, 0.06), rough=0.08), name="wet_floor")
    kit.blood_pool(k, 3.8, 0.7, 0.35, seed=9)
    k.light("POINT", (2.5, 3.0, 2.8), (0.85, 0.92, 1.0), 60, radius=0.2, name="ceiling_light")
    k.box((2.2, 2.9, 2.95), (2.8, 3.1, 3.0), mat("fluoro", color=(0.9, 0.95, 1.0), emit=6.0), name="fluoro")
    return {
        "tint": (0.82, 0.88, 0.9),
        "cameras": [
            {"id": "door", "pos": (1.4, 5.6, 2.6), "target": (3.4, 0.8, 0.8), "fov": 72},
            {"id": "showers", "pos": (4.7, 0.4, 2.3), "target": (1.2, 5.0, 0.9), "fov": 72},
        ],
        "walk": [[(0.5, 0.3), (4.7, 0.3), (4.7, 5.5), (0.5, 5.5)]],
        "blocks": [[(1.6, 3.5), (3.8, 3.5), (3.8, 4.1), (1.6, 4.1)], [(1.1, 1.4), (1.7, 1.4), (1.7, 3.0), (1.1, 3.0)],
                   [(0.0, 1.8), (0.5, 1.8), (0.5, 4.2), (0.0, 4.2)]],
        "zones": [
            {"camera": "door", "poly": [(0, 0), (5, 0), (5, 3.0), (0, 3.0)]},
            {"camera": "showers", "poly": [(0, 3.0), (5, 3.0), (5, 6), (0, 6)]},
        ],
        "doors": [{"id": "north", "poly": [(1.5, 5.6), (2.5, 5.6), (2.5, 6.0), (1.5, 6.0)], "to": "gym", "spawn": {}}],
        "spawn": {"x": 2.0, "y": 5.2, "yaw": 180},
    }
