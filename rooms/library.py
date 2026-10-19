"""第 1 章：圖書室。謎題 P3：200 本同一本書（哈洛威的《30 天成為百萬富翁》），找出唯一的「第 0 版」。

範圍：x 0–8、y 0–10、高 4.5 m。門在西牆 y = 4（通往西側走廊）。
"""
import kit
from kit import mat


def build(k):
    kit.set_ambient((0.045, 0.04, 0.036), 1.0)
    kit.room_shell(k, 0, 0, 8, 10, 4.5,
                   floor=mat("floor_wood_worn", "floor_wood_worn"),
                   wall=mat("wallpaper_damask_red", "wallpaper_damask_red"),
                   ceiling=mat("ceiling_wood", "ceiling_wood"),
                   wainscot=mat("wainscot_dark", "wainscot_dark"))
    kit.door(k, 0.0, 4.0, -90, w=1.0, h=2.4, double=True)
    # 北牆整面書架；東牆兩組；中間兩排獨立書架（其中一排全是同一本書）
    for x in (0.9, 2.5, 4.1, 5.7, 7.2):
        kit.bookshelf(k, x, 9.78, 180, w=1.6, h=3.2, d=0.42)
    for y in (2.0, 6.5):
        kit.bookshelf(k, 7.78, y, 90, w=1.6, h=3.2, d=0.42)
    for x in (3.0, 4.6):
        kit.bookshelf(k, x, 6.0, 0, w=1.6, h=2.2, d=0.42)
    # 「同一本書」的書架：換成 books_same 貼圖
    k_books = mat("books_same", "books_same")
    for x in (3.0, 4.6):
        k.box((x - 0.75, 6.0 + 0.19, 0.05), (x + 0.75, 6.0 + 0.215, 2.15), k_books, uv=1.0, name="same_books")
    kit.library_ladder(k, 5.7, 9.4, 180)
    # 閱讀區：桌子、檯燈、扶手椅、地球儀、地毯
    kit.desk(k, 3.6, 2.6, 0, w=1.6, d=0.8)
    kit.desk_lamp(k, 3.0, 2.5, 0.77, power=16)
    k.box((3.7, 2.4, 0.77), (4.1, 2.7, 0.8), mat("book_open", "paper"), uv=0.3, name="open_book")
    kit.chair(k, 3.6, 1.9, 0, fabric="fabric_velvet_red")
    kit.armchair(k, 1.4, 1.4, 40)
    kit.armchair(k, 6.4, 3.8, -110)
    kit.globe(k, 1.3, 7.2)
    kit.rug(k, 1.8, 0.8, 6.0, 4.6, "carpet_green")
    kit.window(k, 4.0, 0.0, 1.2, 0, w=1.2, h=2.4, power=50)
    kit.chandelier(k, 4.0, 5.0, 4.1, lit=True, power=220, r=0.6)
    # 照著「同一本書」書架的燈（謎題要看得清楚）
    k.light("AREA", (3.8, 7.6, 3.2), (1.0, 0.82, 0.55), 160, radius=2.5, name="shelf_light", rot=(-55, 0, 180))
    kit.wall_sconce(k, 7.98, 4.3, 2.4, 90, power=18)
    kit.wall_sconce(k, 0.02, 7.5, 2.4, -90, power=20)
    return {
        "tint": (0.88, 0.76, 0.66),
        "cameras": [
            {"id": "reading", "pos": (0.6, 9.1, 2.7), "target": (6.6, 6.0, 0.7), "fov": 72},
            {"id": "door", "pos": (0.5, 0.5, 3.6), "target": (5.0, 7.0, 0.8), "fov": 70},
            {"id": "stacks", "pos": (7.3, 8.8, 2.2), "target": (2.0, 2.0, 1.0), "fov": 70},
            {"id": "aisle", "pos": (3.8, 9.1, 1.6), "target": (3.8, 6.2, 1.2), "fov": 72},    # 走到書架前：看到同一本書排滿
        ],
        "walk": [[(0.3, 0.3), (7.4, 0.3), (7.4, 9.4), (0.3, 9.4)]],
        "blocks": [
            [(2.1, 5.7), (5.5, 5.7), (5.5, 6.3), (2.1, 6.3)],     # 中間的書架
            [(2.7, 2.1), (4.5, 2.1), (4.5, 3.1), (2.7, 3.1)],     # 書桌
            [(7.4, 1.0), (8.0, 1.0), (8.0, 7.5), (7.4, 7.5)],     # 東牆書架
            [(0.9, 6.8), (1.7, 6.8), (1.7, 7.6), (0.9, 7.6)],     # 地球儀
        ],
        "zones": [
            {"camera": "stacks", "poly": [(0, 0), (8, 0), (8, 5.4), (0, 5.4)]},
            {"camera": "door", "poly": [(0, 5.4), (2.1, 5.4), (2.1, 10), (0, 10)]},
            {"camera": "door", "poly": [(5.5, 5.4), (8, 5.4), (8, 10), (5.5, 10)]},
            {"camera": "aisle", "poly": [(2.1, 6.3), (5.5, 6.3), (5.5, 10), (2.1, 10)]},
        ],
        "doors": [{"id": "west", "poly": [(0.0, 3.0), (0.4, 3.0), (0.4, 5.0), (0.0, 5.0)], "to": "hall_west", "spawn": {}}],
        "spawn": {"x": 0.8, "y": 4.0, "yaw": 90},
    }
