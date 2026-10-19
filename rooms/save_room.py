"""安全房（主館一樓）：原本是傭人的房間，現在有打字機、物流箱、行軍床。

比其他房間亮、偏暖，玩家一進來就知道這裡安全。
房間範圍：x 0–4、y 0–5、高 2.8 m。門在南牆（y = 0）。
"""
import kit
from kit import mat


def build(k):
    kit.set_ambient((0.035, 0.03, 0.025), 1.0)
    kit.room_shell(k, 0, 0, 4, 5, 2.8,
                   floor=mat("floor_wood_worn", "floor_wood_worn"),
                   wall=mat("plaster_cream", "plaster_cream"),
                   ceiling=mat("plaster_grey", "plaster_grey"),
                   wainscot=mat("wainscot_dark", "wainscot_dark"))
    # 門（南牆，朝室內 +y）
    kit.door(k, 2.0, 0.0, 0)
    # 書桌＋打字機（北牆）
    kit.desk(k, 1.4, 4.55, 180)
    kit.typewriter(k, 1.35, 4.45, 0.77, 0)
    kit.ribbon_tin(k, 1.75, 4.45, 0.77)
    kit.ribbon_tin(k, 1.82, 4.6, 0.77)
    kit.desk_lamp(k, 0.82, 4.62, 0.77, power=22)
    kit.chair(k, 2.05, 3.95, 215, fabric="fabric_linen")
    # 牆上的公告（貼在北牆）
    k.box((2.2, 4.97, 1.4), (2.75, 5.0, 1.95), mat("paper", "paper"), uv=0.6, name="notice")
    # 物流箱（東牆）
    kit.item_crate(k, 3.5, 3.4, 90)
    kit.boxes_stack(k, 3.55, 4.5, 90)
    # 行軍床（西牆）
    kit.cot(k, 0.5, 2.1, 0)
    # 小書架、盆栽
    kit.bookshelf(k, 3.75, 1.4, 90, w=1.0, h=1.8, d=0.35)
    kit.plant_pot(k, 0.35, 4.6, 0.8)
    # 東牆高處的小窗（月光）
    kit.window(k, 3.99, 2.4, 1.4, 90, w=0.8, h=0.9, power=15, curtains=False)
    # 天花板的燈泡（昏暗）
    k.cyl((2.0, 2.5, 2.62), 0.05, 0.08, mat("bulb", color=(1.0, 0.85, 0.6), emit=8.0), seg=6, name="bulb")
    k.cyl((2.0, 2.5, 2.7), 0.005, 0.1, mat("wire", color=(0.02, 0.02, 0.02)), seg=4, name="wire")
    k.light("POINT", (2.0, 2.5, 2.5), (1.0, 0.78, 0.5), 35, radius=0.1, name="ceiling_bulb")

    return {
        "cameras": [
            {"id": "A", "pos": (3.55, 0.5, 2.4), "target": (1.4, 4.3, 0.8), "fov": 66},
            {"id": "B", "pos": (0.35, 4.7, 2.4), "target": (2.6, 1.0, 0.6), "fov": 70},
        ],
        "walk": [[(0.25, 0.25), (3.75, 0.25), (3.75, 4.75), (0.25, 4.75)]],
        "blocks": [
            [(0.7, 3.65), (2.4, 3.65), (2.4, 4.9), (0.7, 4.9)],     # 書桌＋椅子
            [(3.15, 2.9), (3.95, 2.9), (3.95, 4.95), (3.15, 4.95)],  # 物流箱、紙箱
            [(0.05, 1.1), (0.95, 1.1), (0.95, 3.1), (0.05, 3.1)],    # 行軍床
            [(3.5, 0.85), (3.95, 0.85), (3.95, 1.95), (3.5, 1.95)],  # 書架
        ],
        "zones": [
            {"camera": "A", "poly": [(0, 2.2), (4, 2.2), (4, 5), (0, 5)]},
            {"camera": "B", "poly": [(0, 0), (4, 0), (4, 2.2), (0, 2.2)]},
        ],
        "doors": [{"id": "south", "poly": [(1.5, 0.0), (2.5, 0.0), (2.5, 0.35), (1.5, 0.35)],
                   "to": "hall_west", "spawn": {"x": 0, "y": 0, "yaw": 0}}],
        "spawn": {"x": 2.0, "y": 0.8, "yaw": 0},
    }
