"""序章：衣帽間（前廳旁）。謎題 P1：從賓客大衣口袋裡找出寄物牌號碼，領回手電筒。

範圍：x 0–3.5、y 0–4.5、高 2.8 m。門在南牆 x = 1.2。櫃台把房間分成前後兩半。
"""
import kit
from kit import mat


def build(k):
    kit.set_ambient((0.03, 0.026, 0.022), 1.0)
    kit.room_shell(k, 0, 0, 3.5, 4.5, 2.8,
                   floor=mat("floor_wood_dark", "floor_wood_dark"),
                   wall=mat("wallpaper_damask_cream", "wallpaper_damask_cream"),
                   ceiling=mat("plaster_grey", "plaster_grey"),
                   wainscot=mat("wainscot_dark", "wainscot_dark"))
    kit.door(k, 1.2, 0.0, 0)
    # 櫃台（x 0–2.6；右邊留通道到後面）
    kit.counter(k, 1.3, 2.4, 0, w=2.6)
    # 後面：兩排掛衣桿＋大衣
    kit.coat_rack_rail(k, 0.2, 3.3, 3.5, 1.75)
    kit.coat_rack_rail(k, 0.2, 2.4, 4.15, 1.85)
    coats = ["fabric_curtain_green", "leather_brown", "fabric_velvet_red", "fabric_linen", "leather_brown", "fabric_curtain_green"]
    for i, x in enumerate((0.45, 0.95, 1.45, 2.0, 2.55, 3.05)):
        kit.coat(k, x, 3.5, 1.75, 0, tex=coats[i], length=1.1 if i % 2 else 0.95)
    for i, x in enumerate((0.5, 1.15, 1.9)):
        kit.coat(k, x, 4.15, 1.85, 0, tex=coats[(i + 2) % 6], length=1.2)
    # 號碼牌板（東牆），有一格空著：被領走的就是柯爾的手電筒
    kit.tag_board(k, 3.48, 1.4, 1.2, 90, rows=4, cols=6, missing=((2, 3),))
    kit.umbrella_stand(k, 0.3, 0.5)
    kit.plant_pot(k, 3.2, 0.35, 0.8)
    kit.wall_sconce(k, 0.02, 1.6, 2.0, -90, power=14)
    kit.wall_sconce(k, 1.75, 4.48, 2.2, 180, power=12)
    # 櫃台上的服務鈴旁邊：一盞小檯燈
    kit.desk_lamp(k, 0.4, 2.45, 1.05, power=8)

    return {
        "tint": (0.95, 0.85, 0.72),
        "cameras": [
            {"id": "A", "pos": (0.35, 0.35, 2.4), "target": (2.4, 3.6, 1.0), "fov": 70},
            {"id": "B", "pos": (3.25, 4.2, 2.3), "target": (1.0, 0.6, 0.8), "fov": 70},
        ],
        "walk": [[(0.25, 0.25), (3.25, 0.25), (3.25, 4.25), (0.25, 4.25)]],
        "blocks": [
            [(0.0, 2.0), (2.65, 2.0), (2.65, 2.8), (0.0, 2.8)],           # 櫃台
            [(0.1, 3.3), (3.35, 3.3), (3.35, 4.4), (0.1, 4.4)],           # 大衣
            [(0.1, 0.3), (0.5, 0.3), (0.5, 0.7), (0.1, 0.7)],             # 傘架
        ],
        "zones": [
            {"camera": "A", "poly": [(0, 0), (3.5, 0), (3.5, 2.2), (0, 2.2)]},
            {"camera": "B", "poly": [(0, 2.2), (3.5, 2.2), (3.5, 4.5), (0, 4.5)]},
        ],
        "doors": [{"id": "south", "poly": [(0.7, 0.0), (1.7, 0.0), (1.7, 0.35), (0.7, 0.35)],
                   "to": "foyer", "spawn": {}}],
        "spawn": {"x": 1.2, "y": 0.8, "yaw": 0},
    }
