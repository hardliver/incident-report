"""第 1 章：餐廳。謎題 P2：依賓客名單的上下線關係，把 8 張名牌放到正確座位。

鑽石之夜的晚宴停在上菜的那一刻：保溫蓋還蓋著，蠟燭燒到一半。
範圍：x -5–5、y 0–12、高 4.5 m。門在東牆 y = 2（通往前廳）。
"""
import kit
from kit import mat


def build(k):
    kit.set_ambient((0.045, 0.04, 0.042), 1.0)
    kit.room_shell(k, -5, 0, 5, 12, 4.5,
                   floor=mat("floor_wood_dark", "floor_wood_dark"),
                   wall=mat("wallpaper_damask_green", "wallpaper_damask_green"),
                   ceiling=mat("ceiling_wood", "ceiling_wood"),
                   wainscot=mat("wainscot_dark", "wainscot_dark"), wainscot_h=1.2)
    kit.door(k, 5.0, 2.0, 90, w=1.0, h=2.5, double=True)
    kit.door(k, -4.0, 12.0, 180, w=0.9, h=2.3)          # 北牆西側：通往一樓西側走廊
    # 長桌＋座位（左右各 4、主位 1）
    kit.table_long(k, 0, 6.6, 0, length=6.4, width=1.25, occluder=True)
    seats = []
    for y in (4.4, 5.85, 7.3, 8.75):
        seats.append((-0.95, y, -90))
        seats.append((0.95, y, 90))
    for (x, y, yaw) in seats:
        kit.chair(k, x, y, yaw, occluder=True)
    kit.chair(k, 0, 10.2, 180, occluder=True)         # 主位：哈洛威的座位
    # 每個座位前面：餐盤（保溫蓋）＋名牌；有一個打開了
    for i, (x, y, yaw) in enumerate(seats):
        px = x * 0.5
        kit.cloche_plate(k, px, y, 0.8, open_=(i == 5))
        kit.name_card(k, px * 0.55, y, 0.8, 90)
    kit.cloche_plate(k, 0, 9.55, 0.8)
    kit.name_card(k, 0, 9.3, 0.8, 0)
    # 燭台（點燃，燒到一半）＋吊燈（熄了）
    for y in (5.1, 8.1):
        kit.candelabra(k, 0, y, 0.8, arms=3, lit=True, power=24)
    kit.chandelier(k, 0, 6.6, 4.1, lit=False, r=0.8)
    # 壁爐（西牆，面向 +x）＋上方的肖像
    kit.fireplace(k, -5.0, 6.6, 90, lit=True, power=110)
    kit.painting(k, -4.95, 6.6, 2.6, -90, w=1.2, h=1.5, tex="painting_portrait")
    # 東牆的窗、北牆的餐具櫃與畫
    for y in (6.0, 9.4):
        kit.window(k, 5.0, y, 1.2, 90, w=1.1, h=2.2, power=90)
    kit.cabinet(k, -1.6, 11.75, 180, w=1.6, d=0.5, h=1.0)
    kit.cabinet(k, 1.6, 11.75, 180, w=1.6, d=0.5, h=1.0)
    kit.candelabra(k, -1.6, 11.7, 1.04, arms=1, lit=True, power=10)
    kit.wall_sconce(k, 4.98, 4.0, 2.4, 90, power=18)
    kit.wall_sconce(k, -4.98, 2.5, 2.4, -90, power=18)
    kit.wall_sconce(k, -4.98, 10.5, 2.4, -90, power=18)
    kit.painting(k, 0, 11.95, 2.6, 180, w=2.2, h=1.3, tex="painting_dark")
    kit.grandfather_clock(k, 4.7, 11.6, 180)
    for (x, y) in ((-4.6, 0.4), (4.6, 0.4)):
        kit.plant_pot(k, x, y, 1.0)
    kit.rug(k, -2.2, 3.0, 2.2, 10.4, "carpet_red")

    return {
        "tint": (0.9, 0.78, 0.7),
        "cameras": [
            {"id": "auto1", "pos": (-4.6, 1.2, 2.9), "target": (-3.6, 10.4, 0.6), "fov": 72},   # tools/suggest_cameras.py
            {"id": "ne", "pos": (-4.6, 11.3, 2.3), "target": (4.1, 9.9, 0.6), "fov": 72},
            # 從門邊的高處往餐桌看
            {"id": "door", "pos": (4.4, 0.6, 3.1), "target": (-1.2, 8.0, 0.8), "fov": 70},
            # 從主位後面沿著長桌往門的方向看（招牌鏡頭）
            {"id": "head", "pos": (0.0, 11.5, 2.3), "target": (0.0, 2.0, 0.5), "fov": 66},
            # 壁爐旁的低角度
            {"id": "fire", "pos": (-4.4, 10.9, 1.5), "target": (2.0, 3.0, 1.0), "fov": 70},
        ],
        "walk": [[(-4.7, 0.3), (4.7, 0.3), (4.7, 11.4), (-4.7, 11.4)]],
        "blocks": [
            [(-1.3, 3.1), (1.3, 3.1), (1.3, 10.5), (-1.3, 10.5)],         # 長桌＋椅子
            [(-5.0, 5.4), (-4.1, 5.4), (-4.1, 7.8), (-5.0, 7.8)],         # 壁爐
            [(-2.5, 11.4), (2.5, 11.4), (2.5, 12), (-2.5, 12)],           # 餐具櫃
            [(4.4, 11.3), (5.0, 11.3), (5.0, 12), (4.4, 12)],             # 落地鐘
        ],
        "zones": [
            {"camera": "head", "poly": [(-5, 0), (5, 0), (5, 4.5), (-5, 4.5)]},
            {"camera": "door", "poly": [(-1.5, 4.5), (5, 4.5), (5, 12), (-1.5, 12)]},
            {"camera": "fire", "poly": [(-5, 4.5), (-1.5, 4.5), (-1.5, 12), (-5, 12)]},
        ],
        "doors": [{"id": "east", "poly": [(4.6, 1.0), (5.0, 1.0), (5.0, 3.0), (4.6, 3.0)],
                   "to": "foyer", "spawn": {}},
                  {"id": "north", "poly": [(-4.5, 11.6), (-3.5, 11.6), (-3.5, 12.0), (-4.5, 12.0)],
                   "to": "hall_west", "spawn": {}}],
        "spawn": {"x": 4.0, "y": 2.0, "yaw": 90},
    }
