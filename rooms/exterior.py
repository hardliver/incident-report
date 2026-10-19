"""序章：莊園大門外。暴風雨過後的深夜，柯爾的巡邏車停在碎石車道上，頭燈照著莊園。

範圍：車道 x -6–6、y 0–19.5；莊園正面在 y = 20。
"""
import kit
from kit import mat


def build(k):
    kit.set_ambient((0.035, 0.045, 0.07), 1.0)
    # 地面：碎石車道＋兩側的草地
    k.box((-7, -6, -0.1), (7, 20, 0), mat("ground_gravel", "ground_gravel"), uv=3, name="drive")
    for (a, b) in ((-30, -7), (7, 30)):
        k.box((a, -6, -0.1), (b, 20, -0.02), mat("ground_grass", "ground_grass"), uv=3, name="lawn")
    # 莊園正面：石砌的底座＋灰泥牆＋屋簷
    stone = mat("wall_stone", "wall_stone")
    plaster = mat("plaster_grey", "plaster_grey")
    k.box((-16, 20, 0), (16, 21, 1.2), stone, uv=2, name="facade_base")
    k.box((-16, 20, 1.2), (16, 21, 9.0), plaster, uv=3, name="facade")
    k.box((-16.3, 19.6, 9.0), (16.3, 21, 9.4), mat("wood_furniture", "wood_furniture"), uv=2, name="eave")
    k.box((-16, 21, 9.4), (16, 26, 12), mat("roof", color=(0.04, 0.04, 0.05), rough=0.8), name="roof")
    # 門廊：柱子＋屋頂
    for x in (-3.0, 3.0):
        kit.pillar(k, x, 18.6, 5.5, r=0.3)
    k.box((-3.8, 18.0, 5.5), (3.8, 20.0, 5.9), stone, uv=2, name="porch_roof")
    k.box((-3.8, 17.8, 0), (3.8, 20.0, 0.08), mat("porch_floor", "floor_stone"), uv=2, name="porch_floor")
    kit.door(k, 0, 19.98, 180, w=1.0, h=2.9, double=True)
    kit.wall_sconce(k, -1.6, 19.98, 2.6, 180, power=25)
    kit.wall_sconce(k, 1.6, 19.98, 2.6, 180, power=25)
    # 窗戶：一樓、二樓；有幾扇亮著
    lit = mat("window_lit", color=(0.9, 0.6, 0.3), emit=3.0)
    dark = mat("window_dark", color=(0.02, 0.025, 0.035), rough=0.2)
    frame = mat("wood_furniture", "wood_furniture")
    for row, z in enumerate((2.0, 5.8)):
        for i, x in enumerate((-12, -9, -6, 6, 9, 12)):
            m = lit if (row, i) in ((0, 1), (1, 4), (0, 5)) else dark
            k.box((x - 0.6, 19.95, z), (x + 0.6, 20.0, z + 2.0), m, name="win")
            k.box((x - 0.7, 19.9, z - 0.1), (x + 0.7, 19.97, z), frame, uv=1, name="win_sill")
            k.box((x - 0.04, 19.92, z), (x + 0.04, 19.96, z + 2.0), frame, uv=1, name="win_bar")
    k.light("POINT", (-9, 18.5, 3), (1.0, 0.6, 0.3), 20, radius=0.5, name="win_glow")
    k.light("POINT", (12, 18.5, 3), (1.0, 0.6, 0.3), 20, radius=0.5, name="win_glow")
    # 柯爾的巡邏車（頭燈照著莊園）
    kit.patrol_car(k, 3.4, 7.5, 165)
    # 路燈、樹
    for x in (-3.2, 3.2):
        kit.lamp_post(k, x, 14.0, 3.0, power=45)
    for (x, y, h, dead) in ((-8.5, 4, 8, False), (-10, 11, 9, False), (-8, 17, 7, True),
                            (8.5, 3, 7, True), (10, 12, 9, False), (9, 17.5, 8, False), (-12, -2, 10, False)):
        kit.tree(k, x, y, h, dead=dead)
    # 月光
    k.light("SUN", (0, 0, 20), (0.45, 0.55, 0.85), 0.35, name="moon", rot=(55, 0, 30))

    return {
        "tint": (0.62, 0.7, 0.95),
        "cameras": [
            {"id": "auto1", "pos": (-5.9, 7.1, 2.9), "target": (-2.6, 3.0, 0.6), "fov": 72},   # tools/suggest_cameras.py
            {"id": "auto2", "pos": (-5.9, 19.5, 2.3), "target": (-4.6, 14.7, 0.6), "fov": 72},   # tools/suggest_cameras.py
            {"id": "car", "pos": (5.9, 2.3, 2.3), "target": (3.8, 4.1, 0.6), "fov": 72},
            {"id": "garden", "pos": (-5.6, 12.8, 2.6), "target": (5.0, 18.2, 0.8), "fov": 72},
            {"id": "steps", "pos": (4.6, 12.6, 2.4), "target": (-0.6, 19.2, 1.2), "fov": 72},
            {"id": "drive", "pos": (-4.2, 1.0, 2.1), "target": (1.0, 18.0, 2.6), "fov": 72},
            {"id": "porch", "pos": (1.6, 17.4, 3.0), "target": (-0.5, 4.0, 0.4), "fov": 70},
        ],
        "walk": [[(-6, 2.2), (6, 2.2), (6, 19.6), (-6, 19.6)]],     # 南邊靠近道路的那一段鏡頭拍不到，不能走
        "blocks": [
            [(2.2, 4.8), (4.6, 4.8), (4.6, 10.2), (2.2, 10.2)],          # 巡邏車
            [(-3.4, 18.2), (-2.6, 18.2), (-2.6, 19.0), (-3.4, 19.0)],    # 柱子
            [(2.6, 18.2), (3.4, 18.2), (3.4, 19.0), (2.6, 19.0)],
            [(-3.4, 13.7), (-3.0, 13.7), (-3.0, 14.3), (-3.4, 14.3)],    # 路燈
            [(3.0, 13.7), (3.4, 13.7), (3.4, 14.3), (3.0, 14.3)],
        ],
        "zones": [
            {"camera": "porch", "poly": [(-6, 0), (6, 0), (6, 12), (-6, 12)]},
            {"camera": "drive", "poly": [(-6, 12), (6, 12), (6, 20), (-6, 20)]},
        ],
        "doors": [{"id": "front", "poly": [(-1.0, 19.4), (1.0, 19.4), (1.0, 19.9), (-1.0, 19.9)],
                   "to": "foyer", "spawn": {"x": 0, "y": 1.0, "yaw": 0}}],
        "spawn": {"x": 2.0, "y": 4.0, "yaw": 0},
    }
