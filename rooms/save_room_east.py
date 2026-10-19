"""第 2 章：東翼安全房。原本是布草間：架上疊著毛巾和床單，角落一台打字機、一個物流箱。

和一樓的安全房一樣溫暖、偏亮；但空間更窄，讓玩家感覺東翼更壓迫。
範圍：x 0–3.5、y 0–4、高 2.6 m。門在東牆 y = 1（通往東側走廊）。
"""
import kit
from kit import mat


def build(k):
    kit.set_ambient((0.04, 0.034, 0.028), 1.0)
    kit.room_shell(k, 0, 0, 3.5, 4, 2.6, floor=mat("floor_wood_worn", "floor_wood_worn"),
                   wall=mat("plaster_cream", "plaster_cream"), ceiling=mat("plaster_grey", "plaster_grey"),
                   wainscot=mat("wainscot_dark", "wainscot_dark"), wainscot_h=0.9)
    kit.door(k, 3.5, 1.0, 90, w=0.9, h=2.2)
    kit.desk(k, 0.6, 2.8, -90, w=1.1, d=0.6)
    kit.typewriter(k, 0.55, 2.8, 0.77, -90)
    kit.ribbon_tin(k, 0.5, 3.25, 0.77)
    kit.desk_lamp(k, 0.5, 2.25, 0.77, power=20)
    kit.chair(k, 1.1, 2.8, 90, fabric="fabric_linen")
    kit.item_crate(k, 2.9, 3.5, 180)
    linen = mat("fabric_linen", "fabric_linen")
    for (x, y, yaw) in ((0.25, 0.9, -90),):
        kit.shelf_unit(k, x, y, yaw, w=1.4, h=2.1, items="boxes")
    for z in (0.15, 0.68, 1.2, 1.72):          # 架上疊著的毛巾
        k.box((0.08, 0.35, z + 0.03), (0.42, 1.45, z + 0.2), linen, uv=0.5, name="towels")
    kit.plant_pot(k, 3.15, 0.35, 0.7)
    k.cyl((1.75, 2.0, 2.45), 0.04, 0.07, mat("bulb", color=(1.0, 0.85, 0.6), emit=7.0), seg=6, name="bulb")
    k.light("POINT", (1.75, 2.0, 2.3), (1.0, 0.8, 0.55), 30, radius=0.1, name="bulb_light")
    return {
        "tint": (1.0, 0.86, 0.68),
        "cameras": [
            {"id": "A", "pos": (3.2, 0.35, 2.2), "target": (0.6, 3.2, 0.8), "fov": 72},
            {"id": "B", "pos": (1.7, 3.75, 2.25), "target": (2.4, 0.4, 0.7), "fov": 74},
        ],
        "walk": [[(0.3, 0.3), (3.2, 0.3), (3.2, 3.7), (0.3, 3.7)]],
        "blocks": [[(0.0, 2.15), (1.4, 2.15), (1.4, 3.45), (0.0, 3.45)], [(2.4, 3.1), (3.5, 3.1), (3.5, 4.0), (2.4, 4.0)],
                   [(0.0, 0.2), (0.5, 0.2), (0.5, 1.6), (0.0, 1.6)]],
        "zones": [
            {"camera": "A", "poly": [(0, 2.0), (3.5, 2.0), (3.5, 4), (0, 4)]},
            {"camera": "B", "poly": [(0, 0), (3.5, 0), (3.5, 2.0), (0, 2.0)]},
        ],
        "doors": [{"id": "east", "poly": [(3.1, 0.5), (3.5, 0.5), (3.5, 1.5), (3.1, 1.5)], "to": "hall_east", "spawn": {}}],
        "spawn": {"x": 2.8, "y": 1.0, "yaw": -90},
    }
