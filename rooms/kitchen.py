"""第 1 章：廚房。主廚戰（B1）的場地；送餐升降機（P4）在東牆。

射爆北牆瓦斯爐旁的黃色瓦斯管，或把主廚引進西牆的冷凍庫。
範圍：x 0–7、y 0–8、高 3.2 m。門在東牆 y = 1.5（通往西側走廊）。
"""
import kit
from kit import mat


def build(k):
    kit.set_ambient((0.04, 0.042, 0.04), 1.0)
    kit.room_shell(k, 0, 0, 7, 8, 3.2,
                   floor=mat("floor_terracotta", "floor_terracotta"),
                   wall=mat("tiles_white", "tiles_white"),
                   ceiling=mat("plaster_grey", "plaster_grey"))
    kit.door(k, 7.0, 1.5, 90, w=0.9, h=2.3)
    # 冷凍庫的厚重金屬門（西牆）
    kit.door(k, 0.0, 5.5, -90, w=1.1, h=2.3, tex="metal_steel")
    k.box((0.0, 4.8, 1.1), (0.12, 4.9, 1.3), mat("chrome", color=(0.6, 0.6, 0.6), metal=0.9, rough=0.3), name="freezer_latch")
    # 北牆：瓦斯爐兩台＋流理台；東牆：水槽、送餐升降機
    kit.stove(k, 2.2, 7.6, 180)
    kit.stove(k, 3.5, 7.6, 180)
    kit.kitchen_counter(k, 5.3, 7.65, 180, w=2.0)
    kit.kitchen_counter(k, 0.9, 7.65, 180, w=1.4)
    kit.sink(k, 6.65, 4.8, 90)
    kit.dumbwaiter(k, 6.98, 3.2, 0.95, 90)
    kit.fridge(k, 6.55, 6.6, 90)
    # 中間的工作島＋鍋架；砧板
    kit.kitchen_counter(k, 3.2, 3.94, 0, w=2.6, d=0.5)      # 兩組背靠背（不能重疊：重疊的面會變黑）
    kit.kitchen_counter(k, 3.2, 4.46, 180, w=2.6, d=0.5)
    kit.pot_rack(k, 3.2, 4.2, 2.3, w=2.0)
    kit.chopping_block(k, 1.2, 2.2)
    # 架子：罐頭、玻璃罐
    kit.shelf_unit(k, 0.25, 2.8, -90, w=1.4, h=2.0, items="cans", metal=True)
    kit.shelf_unit(k, 4.6, 0.25, 0, w=1.6, h=2.0, items="jars", metal=True)
    # 白板菜單（被反覆塗改）
    k.box((5.0, 7.97, 1.4), (6.2, 8.0, 2.1), mat("whiteboard", color=(0.72, 0.72, 0.7), rough=0.3), name="menu_board")
    for z in (1.95, 1.8, 1.65):
        k.box((5.15, 7.96, z), (5.9, 7.965, z + 0.03), mat("marker", color=(0.08, 0.1, 0.2)), name="menu_line")
    k.box((5.5, 7.955, 1.5), (6.05, 7.96, 1.62), mat("marker_red", color=(0.4, 0.05, 0.04)), name="menu_scrawl")
    # 燈：工作島上的兩盞吊燈（其中一盞是熄的）＋瓦斯爐上的指示燈
    for x, on in ((2.4, True), (4.0, False)):
        k.cyl((x, 4.2, 2.6), 0.18, 0.15, mat("lampshade", color=(0.1, 0.12, 0.1), metal=0.4), seg=8, r_top=0.05, name="pendant")
        k.box((x - 0.005, 4.195, 2.75), (x + 0.005, 4.205, 3.2), mat("wire", color=(0.02, 0.02, 0.02)), name="pendant_wire")
        if on:
            k.cyl((x, 4.2, 2.6), 0.14, 0.004, mat("lamp_glow", color=(1.0, 0.85, 0.55), emit=12.0), seg=8, name="pendant_bulb")
            k.light("SPOT", (x, 4.2, 2.58), (1.0, 0.85, 0.6), 420, radius=0.08, name="pendant_light", spot_angle=100)
    k.light("POINT", (6.0, 2.0, 2.6), (0.75, 0.85, 1.0), 45, radius=0.3, name="fill")
    k.light("POINT", (2.8, 7.0, 2.2), (1.0, 0.6, 0.3), 25, radius=0.2, name="stove_pilot")
    return {
        "tint": (0.85, 0.82, 0.74),
        "cameras": [
            {"id": "door", "pos": (6.6, 0.4, 2.8), "target": (1.5, 6.5, 0.6), "fov": 70},
            {"id": "stove", "pos": (0.5, 7.4, 2.5), "target": (5.5, 1.5, 0.5), "fov": 72},
            {"id": "freezer", "pos": (1.4, 1.0, 1.4), "target": (0.6, 6.0, 1.2), "fov": 70},   # 冷凍庫門的低角度（主廚衝出來）
        ],
        "walk": [[(0.3, 0.3), (6.7, 0.3), (6.7, 7.7), (0.3, 7.7)]],
        "blocks": [
            [(1.8, 3.6), (4.6, 3.6), (4.6, 4.8), (1.8, 4.8)],     # 工作島
            [(0.0, 6.9), (6.4, 6.9), (6.4, 8.0), (0.0, 8.0)],     # 北牆的爐子、流理台
            [(6.2, 4.1), (7.0, 4.1), (7.0, 7.0), (6.2, 7.0)],     # 水槽、冰箱
            [(0.8, 1.8), (1.6, 1.8), (1.6, 2.6), (0.8, 2.6)],     # 砧板
            [(0.0, 2.0), (0.5, 2.0), (0.5, 3.6), (0.0, 3.6)],     # 架子
        ],
        "zones": [
            {"camera": "stove", "poly": [(0, 0), (7, 0), (7, 3.4), (0, 3.4)]},
            {"camera": "door", "poly": [(1.8, 3.4), (7, 3.4), (7, 8), (1.8, 8)]},
            {"camera": "freezer", "poly": [(0, 3.4), (1.8, 3.4), (1.8, 8), (0, 8)]},
        ],
        "doors": [
            {"id": "east", "poly": [(6.6, 1.0), (7.0, 1.0), (7.0, 2.0), (6.6, 2.0)], "to": "hall_west", "spawn": {}},
            {"id": "freezer", "poly": [(0.0, 4.9), (0.4, 4.9), (0.4, 6.1), (0.0, 6.1)], "to": "freezer", "spawn": {}},
        ],
        "spawn": {"x": 6.2, "y": 1.5, "yaw": -90},
    }
