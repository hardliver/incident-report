"""前廳（主館中心）：兩側樓梯通往二樓迴廊，北牆正中央是「榮譽之牆」。

這是整個遊戲的中心：四枚獎章全部放回榮譽之牆，才能打開最後的門。
房間範圍：x -7–7、y 0–14、高 7 m。大門在南牆正中央（y = 0）。
二樓迴廊：y 10.4–14、高 3.6 m。
"""
import math

import kit
from kit import mat, T

BAL_Z = 3.6       # 迴廊高度
BAL_Y = 10.4      # 迴廊前緣


def balcony(k):
    wood = mat("wood_furniture", "wood_furniture")
    floor = mat("floor_wood_dark", "floor_wood_dark")
    k.box((-7, BAL_Y, BAL_Z - 0.3), (7, 14, BAL_Z), wood, uv=1.5, name="balcony_slab")
    k.box((-7, BAL_Y, BAL_Z), (7, 14, BAL_Z + 0.02), floor, uv=2, name="balcony_floor")
    # 欄杆
    k.box((-4.8, BAL_Y, BAL_Z + 0.95), (4.8, BAL_Y + 0.1, BAL_Z + 1.05), wood, uv=0.5, occluder=True, name="rail_top")
    k.box((-4.8, BAL_Y, BAL_Z), (4.8, BAL_Y + 0.1, BAL_Z + 0.12), wood, uv=0.5, occluder=True, name="rail_bottom")
    x = -4.7
    while x < 4.8:
        k.box((x - 0.035, BAL_Y + 0.015, BAL_Z + 0.12), (x + 0.035, BAL_Y + 0.085, BAL_Z + 0.95), wood, uv=0.5, occluder=True, name="baluster")
        x += 0.28
    # 迴廊前緣的飾帶
    k.box((-7, BAL_Y - 0.05, BAL_Z - 0.45), (7, BAL_Y + 0.02, BAL_Z - 0.3), mat("trim_gold", "brass", metal=0.5, rough=0.5), uv=0.5, name="balcony_trim")


def build(k):
    kit.set_ambient((0.04, 0.036, 0.045), 1.0)
    kit.room_shell(k, -7, 0, 7, 14, 7,
                   floor=mat("floor_marble_checker", "floor_marble_checker"),
                   wall=mat("wallpaper_damask_red", "wallpaper_damask_red"),
                   ceiling=mat("ceiling_wood", "ceiling_wood"),
                   wainscot=mat("wainscot_dark", "wainscot_dark"), wainscot_h=1.4)
    # 二樓迴廊下方的天花板（迴廊的底面已經是 slab）
    balcony(k)

    # 兩側樓梯：從 y=5 往北爬到迴廊
    steps, rise = 12, BAL_Z / 12
    run = (BAL_Y - 5.0) / steps
    kit.staircase(k, -5.6, 5.0, 1.6, rise, run, steps, occluder=True)
    kit.staircase(k, 5.6, 5.0, 1.6, rise, run, steps, occluder=True)

    # 地毯：從大門到榮譽之牆
    kit.rug(k, -1.2, 0.0, 1.2, 13.9, "carpet_red")

    # 大門（雙開）＋兩側的高窗
    kit.door(k, 0, 0.0, 0, w=1.0, h=2.9, double=True)
    for x in (-4.0, 4.0):
        kit.window(k, x, 0.0, 1.6, 0, w=1.3, h=2.8, power=140)
    # 側門：西（往餐廳）、東（往走廊）
    kit.door(k, -7.0, 3.0, -90, w=1.0, h=2.4, double=True)
    kit.door(k, 7.0, 3.0, 90, w=1.0, h=2.4)
    kit.door(k, -5.9, 0.0, 0, w=0.9, h=2.3)              # 南牆西側：衣帽間

    # 柱子：撐住迴廊
    for x in (-3.2, 3.2):
        kit.pillar(k, x, BAL_Y + 0.05, BAL_Z - 0.3, r=0.28)

    # 榮譽之牆（北牆正中，迴廊下方）＋兩側胸像與壁燈
    kit.honor_wall(k, 0, 13.92, 1.7, 180, filled=0)
    k.light("SPOT", (0, 12.2, BAL_Z - 0.35), (1.0, 0.85, 0.6), 120, radius=0.1, name="honor_spot",
            spot_angle=50, rot=(-60, 0, 180))
    for x in (-2.2, 2.2):
        kit.bust_pedestal(k, x, 12.9, 180)
        kit.wall_sconce(k, x * 1.6, 13.95, 2.3, 180, power=30)

    # 吊燈（點亮，但很昏暗：一半的蠟燭已經熄了）
    kit.chandelier(k, 0, 6.0, 6.2, lit=True, power=450, r=0.9)

    # 牆上的畫（二樓高度）
    kit.painting(k, -6.95, 7.6, 5.3, -90, w=1.6, h=2.0, tex="painting_portrait")
    kit.painting(k, 6.95, 7.6, 5.3, 90, w=1.6, h=2.0, tex="painting_dark")
    kit.painting(k, 0, 13.95, 5.6, 180, w=2.4, h=1.6, tex="painting_dark")

    # 落地鐘（東牆）、扶手椅與小桌（西側）、盆栽
    kit.grandfather_clock(k, 6.7, 1.3, 90)
    kit.armchair(k, -5.6, 2.0, 60)
    kit.armchair(k, -5.6, 3.9, 120)
    k.cyl((-6.1, 2.95, 0), 0.3, 0.6, mat("wood_furniture", "wood_furniture"), seg=8, uv=0.5, occluder=True, name="side_table")
    kit.candelabra(k, -6.1, 2.95, 0.6, arms=1, lit=True, power=4)
    for (x, y) in ((-1.9, 0.6), (1.9, 0.6), (-6.4, 12.9), (6.4, 12.9)):
        kit.plant_pot(k, x, y, 1.1)

    for y in (2.0, 8.5):
        kit.wall_sconce(k, -6.98, y, 2.4, -90, power=20)
        kit.wall_sconce(k, 6.98, y, 2.4, 90, power=20)
    # 迴廊上的壁燈
    for x in (-5.5, 5.5):
        kit.wall_sconce(k, x, 13.95, BAL_Z + 1.9, 180, power=25)

    blocks = [
        [(-6.45, 5.0), (-4.75, 5.0), (-4.75, 10.4), (-6.45, 10.4)],   # 西樓梯
        [(4.75, 5.0), (6.45, 5.0), (6.45, 10.4), (4.75, 10.4)],      # 東樓梯
        [(-3.55, 10.1), (-2.85, 10.1), (-2.85, 10.8), (-3.55, 10.8)],
        [(2.85, 10.1), (3.55, 10.1), (3.55, 10.8), (2.85, 10.8)],
        [(-2.5, 12.6), (-1.9, 12.6), (-1.9, 13.2), (-2.5, 13.2)],      # 胸像
        [(1.9, 12.6), (2.5, 12.6), (2.5, 13.2), (1.9, 13.2)],
        [(6.4, 0.9), (6.95, 0.9), (6.95, 1.7), (6.4, 1.7)],            # 落地鐘
        [(-6.95, 1.4), (-5.0, 1.4), (-5.0, 4.5), (-6.95, 4.5)],        # 扶手椅區
    ]
    return {
        # 角色 sprite 在這個房間的色調（乘在 sprite 的顏色上）
        "tint": (0.92, 0.8, 0.74),
        "cameras": [
            # 從大門上方往北看：玩家第一次進來看到的畫面
            {"id": "entrance", "pos": (4.6, 0.8, 5.0), "target": (-0.8, 10.5, 1.4), "fov": 74},
            # 從榮譽之牆旁的低角度往南看大門：胸像在前景
            {"id": "honor", "pos": (-2.9, 13.3, 1.35), "target": (1.2, 1.5, 1.9), "fov": 72},
            # 從二樓迴廊西北角往下看
            {"id": "balcony", "pos": (-6.3, 13.6, 6.3), "target": (1.0, 4.0, 0.3), "fov": 70},
        ],
        "walk": [[(-6.75, 0.3), (6.75, 0.3), (6.75, 13.7), (-6.75, 13.7)]],
        "blocks": blocks,
        "zones": [
            {"camera": "honor", "poly": [(-7, 0), (7, 0), (7, 5.5), (-7, 5.5)]},
            {"camera": "entrance", "poly": [(-4.7, 5.5), (7, 5.5), (7, 14), (-4.7, 14)]},
            {"camera": "balcony", "poly": [(-7, 5.5), (-4.7, 5.5), (-4.7, 14), (-7, 14)]},
        ],
        "doors": [
            {"id": "front", "poly": [(-1.0, 0.0), (1.0, 0.0), (1.0, 0.4), (-1.0, 0.4)], "to": "_locked", "spawn": {}},
            {"id": "west", "poly": [(-7.0, 2.0), (-6.6, 2.0), (-6.6, 4.0), (-7.0, 4.0)], "to": "dining", "spawn": {}},
            {"id": "east", "poly": [(6.6, 2.5), (7.0, 2.5), (7.0, 3.5), (6.6, 3.5)], "to": "hall_east", "spawn": {}},
            {"id": "cloak", "poly": [(-6.4, 0.0), (-5.4, 0.0), (-5.4, 0.4), (-6.4, 0.4)], "to": "cloakroom", "spawn": {}},
        ],
        "spawn": {"x": 0, "y": 1.2, "yaw": 0},
    }
