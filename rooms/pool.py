"""第 2 章：室內泳池。謎題 P7：在機房把水抽乾，池底有金獎章——還有一隻少了一隻眼睛的粉紅泰迪熊。

範圍：x 0–14、y 0–10、高 5 m。池子 x 3–11、y 2–8、深 1.8 m（已經抽乾的版本）。
門在西牆 y = 2（東側走廊）、北牆 x = 12（機房）。
"""
import kit
from kit import mat


def build(k):
    kit.set_ambient((0.03, 0.04, 0.05), 1.0)
    tiles = mat("tiles_white", "tiles_white")
    kit.room_shell(k, 0, 0, 14, 10, 5.0, floor=None, wall=tiles, ceiling=mat("plaster_grey", "plaster_grey"))
    # 池邊的地板（在池子周圍鋪四塊）
    fl = mat("tiles_lab_green", "tiles_lab_green")
    for (a, b, c, d) in ((0, 0, 14, 1.65), (0, 8.35, 14, 10), (0, 1.65, 2.65, 8.35), (11.35, 1.65, 14, 8.35)):
        k.box((a, b, -0.1), (c, d, 0), fl, uv=2, name="deck")
    kit.pool_basin(k, 3, 2, 11, 8, depth=1.8, drained=True)
    kit.pool_ladder(k, 4.0, 8.05, 1.6, 180)
    kit.pool_ladder(k, 10.0, 1.95, 1.6, 0)
    kit.teddy_bear(k, 7.6, 6.3, -1.75, 30)
    # 池底的金獎章（P7 的獎勵：一點反光）
    k.cyl((5.2, 4.4, -1.79), 0.06, 0.01, mat("medal_gold_floor", color=(0.85, 0.65, 0.2), metal=0.8, rough=0.25), seg=10, name="medal")
    kit.door(k, 0.0, 2.0, -90, w=1.0, h=2.4, double=True)
    kit.door(k, 12.0, 10.0, 180, w=0.9, h=2.3, tex="metal_steel")
    for (x, y, yaw) in ((1.2, 4.0, 90), (1.2, 6.0, 90), (12.8, 4.0, -90), (12.8, 6.0, -90)):
        kit.deck_chair(k, x, y, yaw)
    # 東牆的大窗（夜色）＋天花板的燈
    for y in (2.5, 5.0, 7.5):
        kit.window(k, 14.0, y, 1.0, 90, w=1.8, h=3.2, power=60, curtains=False)
    for (x, on) in ((4.5, True), (7.0, False), (9.5, True)):
        k.cyl((x, 5.0, 4.6), 0.3, 0.2, mat("lampshade", color=(0.1, 0.12, 0.1), metal=0.4), seg=8, r_top=0.1, name="pool_lamp")
        if on:
            k.light("SPOT", (x, 5.0, 4.55), (0.9, 0.95, 1.0), 900, radius=0.15, name="pool_light", spot_angle=80)
    k.box((0.02, 6.5, 1.0), (0.04, 8.0, 2.0), mat("sign", color=(0.6, 0.55, 0.4)), name="rules_sign")
    return {
        "tint": (0.78, 0.86, 0.92),
        "cameras": [
            {"id": "door", "pos": (0.6, 0.6, 3.8), "target": (8.0, 6.5, -1.0), "fov": 72},
            {"id": "deep", "pos": (12.8, 9.4, 3.4), "target": (6.0, 3.0, -1.5), "fov": 70},
            {"id": "bottom", "pos": (3.6, 2.6, -0.6), "target": (8.5, 7.0, -1.5), "fov": 74},   # 走下池底
        ],
        "walk": [[(0.3, 0.3), (13.7, 0.3), (13.7, 1.6), (0.3, 1.6)], [(0.3, 8.4), (13.7, 8.4), (13.7, 9.7), (0.3, 9.7)],
                 [(0.3, 1.6), (2.6, 1.6), (2.6, 8.4), (0.3, 8.4)], [(11.4, 1.6), (13.7, 1.6), (13.7, 8.4), (11.4, 8.4)]],
        "blocks": [[(0.5, 3.0), (1.6, 3.0), (1.6, 7.0), (0.5, 7.0)], [(12.4, 3.0), (13.5, 3.0), (13.5, 7.0), (12.4, 7.0)]],
        "zones": [
            {"camera": "deep", "poly": [(0, 0), (7, 0), (7, 10), (0, 10)]},
            {"camera": "door", "poly": [(7, 0), (14, 0), (14, 10), (7, 10)]},
            {"camera": "bottom", "poly": [(3, 2), (11, 2), (11, 8), (3, 8)]},
        ],
        "doors": [
            {"id": "west", "poly": [(0.0, 1.0), (0.4, 1.0), (0.4, 3.0), (0.0, 3.0)], "to": "hall_east", "spawn": {}},
            {"id": "machine", "poly": [(11.5, 9.6), (12.5, 9.6), (12.5, 10.0), (11.5, 10.0)], "to": "pool_machine", "spawn": {}},
        ],
        "spawn": {"x": 0.8, "y": 2.0, "yaw": 90},
        "notes": "池底的高度是 z = -1.8；梯子在 (4, 8) 和 (10, 2)。walk 只列池邊，池底區域由遊戲在抽水後開放。",
    }
