"""第 2 章：健身房。謎題 P6（槓鈴配重）、小頭目 B2（年度體態冠軍）。

北牆是整面鏡子（裂了）；滑輪機在東側（B2：引它到下面，放下配重片）。
範圍：x 0–9、y 0–8、高 3.4 m。門在西牆 y = 2（東側走廊）、南牆 x = 7（更衣室）。
"""
import kit
from kit import mat


def build(k):
    kit.set_ambient((0.04, 0.042, 0.045), 1.0)
    kit.room_shell(k, 0, 0, 9, 8, 3.4, floor=mat("floor_rubber", "floor_rubber"),
                   wall=mat("plaster_grey", "plaster_grey"), ceiling=mat("plaster_grey", "plaster_grey"))
    kit.door(k, 0.0, 2.0, -90, w=1.0, h=2.4, double=True)
    kit.door(k, 7.0, 0.0, 0, w=0.9, h=2.3)
    kit.mirror_wall(k, 0.5, 6.5, 7.96, 0.3, 2.5)
    k.box((0.4, 7.9, 0.2), (6.6, 8.0, 0.3), mat("wood_furniture", "wood_furniture"), name="mirror_ledge")
    # P6：槓鈴只裝了一邊（玩家要找到另一片裝上去）
    kit.bench_press(k, 2.0, 5.4, 0, loaded=(0.22, 0.0))
    kit.bench_press(k, 4.6, 5.4, 0, loaded=(0.16, 0.16))
    kit.dumbbell_rack(k, 3.3, 7.4, 0)
    kit.cable_machine(k, 7.8, 5.5, -90)
    for x in (1.2, 2.4, 3.6):
        kit.treadmill(k, x, 1.6, 180)
    kit.bench(k, 6.2, 2.4, 90, L=1.2)
    for (x, y) in ((5.2, 3.6), (1.0, 3.9)):
        kit.weight_plate(k, x, y, 0.22, 0.22, axis="y")       # 散落在地上的槓片
    # 白板：「今日目標」
    k.box((8.97, 1.0, 1.3), (9.0, 2.6, 2.3), mat("whiteboard", color=(0.72, 0.72, 0.7), rough=0.3), name="goal_board")
    for z in (2.1, 1.9, 1.7, 1.5):
        k.box((8.96, 1.15, z), (8.965, 2.3 - (z - 1.5), z + 0.04), mat("marker", color=(0.08, 0.1, 0.2)), name="goal_line")
    # 燈：日光燈管（一支在閃，烘焙時當作熄滅）
    for (x, on) in ((2.0, True), (4.5, True), (7.0, False)):
        k.box((x - 0.6, 3.9, 3.3), (x + 0.6, 4.1, 3.35), mat("fluoro" if on else "fluoro_off", color=(0.9, 0.95, 1.0) if on else (0.2, 0.2, 0.2), emit=6.0 if on else 0.0), name="fluoro")
        if on:
            k.light("AREA", (x, 4.0, 3.28), (0.85, 0.92, 1.0), 120, radius=1.2, name="fluoro_light", rot=(0, 0, 0))
    return {
        "tint": (0.82, 0.86, 0.9),
        "cameras": [
            {"id": "door", "pos": (0.5, 0.5, 2.9), "target": (5.0, 6.0, 0.6), "fov": 72},
            {"id": "mirror", "pos": (8.4, 7.5, 2.6), "target": (2.5, 1.5, 0.6), "fov": 72},
            {"id": "machine", "pos": (5.2, 3.0, 1.5), "target": (8.0, 6.0, 1.3), "fov": 70},     # 滑輪機（B2 的關鍵）
        ],
        "walk": [[(0.3, 0.3), (8.7, 0.3), (8.7, 7.7), (0.3, 7.7)]],
        "blocks": [
            [(1.6, 4.6), (2.4, 4.6), (2.4, 6.1), (1.6, 6.1)], [(4.2, 4.6), (5.0, 4.6), (5.0, 6.1), (4.2, 6.1)],
            [(2.3, 7.0), (4.3, 7.0), (4.3, 7.8), (2.3, 7.8)], [(0.7, 0.6), (4.1, 0.6), (4.1, 2.6), (0.7, 2.6)],
            [(5.6, 1.7), (6.8, 1.7), (6.8, 3.1), (5.6, 3.1)], [(7.5, 4.8), (8.2, 4.8), (8.2, 6.3), (7.5, 6.3)],
        ],
        "zones": [
            {"camera": "mirror", "poly": [(0, 0), (5.0, 0), (5.0, 4.2), (0, 4.2)]},
            {"camera": "door", "poly": [(0, 4.2), (6.4, 4.2), (6.4, 8), (0, 8)]},
            {"camera": "machine", "poly": [(5.0, 0), (9, 0), (9, 8), (6.4, 8), (6.4, 4.2), (5.0, 4.2)]},
        ],
        "doors": [
            {"id": "west", "poly": [(0.0, 1.0), (0.4, 1.0), (0.4, 3.0), (0.0, 3.0)], "to": "hall_east", "spawn": {}},
            {"id": "locker", "poly": [(6.5, 0.0), (7.5, 0.0), (7.5, 0.35), (6.5, 0.35)], "to": "locker_room", "spawn": {}},
        ],
        "spawn": {"x": 0.8, "y": 2.0, "yaw": 90},
    }
