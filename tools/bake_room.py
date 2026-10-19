"""房間預渲染：房間定義 → 每個機位的背景、前景深度遮罩、room.json、預覽圖。

用法：
  python3 tools/bake_room.py foyer           # 只做一個房間
  python3 tools/bake_room.py --all
  python3 tools/bake_room.py foyer --fast    # 低取樣，快速看構圖
  python3 tools/bake_room.py --all --json    # 只更新 room.json（改了可走範圍、門、區域時），不重新算圖
  python3 tools/bake_room.py gym --depth     # 只算 room.json 和深度遮罩：擺新鏡頭時，配合 tests/check_cameras.py 快速檢查

每個房間是 rooms/<名稱>.py，裡面有一個 build(k) 函式：
  - 用 tools/kit.py 擺設場景
  - 回傳一個 dict：
      cameras: [{id, pos, target, fov}]       攝影機（fov 是水平視角，度）
      walk:    [[(x, y), ...], ...]            可走區域（地面上的多邊形，可以有多個）
      blocks:  [[(x, y), ...], ...]            擋路的家具（在可走區域裡挖掉的部分）
      zones:   [{camera, poly: [(x, y), ...]}] 玩家站在這個區域時用哪個機位
      doors:   [{id, poly, to, spawn}]         門：走進 poly 就換到房間 to
      spawn:   {x, y, yaw}                     預設出生點
      tint:    (r, g, b)                       角色 sprite 在這個房間的色調

輸出（進 repo）：art/rooms/<房間>/
  <機位>_bg.png      320×240，256 色索引（每張自己的調色盤）
  <機位>_depth.png   16-bit 灰階，前景物件的深度（公分）；0 = 不會擋住角色
  room.json          攝影機參數、可走區域、機位區域、門
預覽（不進 repo）：build/rooms/<房間>/<機位>_preview.png

座標：Blender 慣例，x 右、y 前、z 上，單位公尺。地面是 z = 0。
"""
import importlib.util
import json
import math
import os
import sys
import time

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import kit  # noqa: E402

W, H = 320, 240


def load_room(name):
    path = os.path.join(ROOT, "rooms", name + ".py")
    spec = importlib.util.spec_from_file_location("room_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_camera(c):
    cd = bpy.data.cameras.new(c["id"])
    cd.sensor_fit = "HORIZONTAL"
    cd.angle = math.radians(c.get("fov", 60))
    cd.clip_start = 0.05
    cd.clip_end = 100
    ob = bpy.data.objects.new("cam_" + c["id"], cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = c["pos"]
    d = Vector(c["target"]) - Vector(c["pos"])
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    return ob


def depth_map(scene, cam, occluders):
    """對每個像素從攝影機射一條光線（ray cast），找出打到的物件。

    打到「前景物件」(occluder) 的像素記錄深度（沿攝影機前方的距離，公分）。
    引擎畫角色時：如果某個像素的前景深度 < 角色的深度，就不畫那個像素（角色被擋住）。
    """
    dg = bpy.context.evaluated_depsgraph_get()
    frame = cam.data.view_frame(scene=scene)       # 攝影機座標中的四個角
    xs = [v.x for v in frame]
    ys = [v.y for v in frame]
    z = frame[0].z
    left, right, bottom, top = min(xs), max(xs), min(ys), max(ys)
    R = cam.matrix_world.to_3x3()
    origin = cam.matrix_world.translation.copy()
    fwd = (R @ Vector((0, 0, -1))).normalized()
    out = np.zeros((H, W), np.uint16)
    hits = np.zeros((H, W), bool)
    for py in range(H):
        cy = top - (py + 0.5) / H * (top - bottom)
        for px in range(W):
            cx = left + (px + 0.5) / W * (right - left)
            d = (R @ Vector((cx, cy, z))).normalized()
            ok, loc, _n, _i, ob, _m = scene.ray_cast(dg, origin, d)
            if ok and ob is not None and ob.name in occluders:
                depth = (loc - origin).dot(fwd)
                out[py, px] = min(65535, max(1, int(depth * 100)))
                hits[py, px] = True
    return out, hits


def project(scene, cam, x, y, z=0.0):
    v = world_to_camera_view(scene, cam, Vector((x, y, z)))
    return v.x * W, (1 - v.y) * H, v.z


def quantize_bg(path_in, path_out):
    im = Image.open(path_in).convert("RGB")
    q = im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
    q.save(path_out)
    return q


def preview(q, hits, scene, cam, data, path):
    """預覽圖：放大 2 倍；紅色＝前景遮罩；綠線＝可走區域；黃線＝這個機位的區域；藍線＝門。"""
    base = q.convert("RGB")
    arr = np.asarray(base).astype(float)
    arr[hits] = arr[hits] * 0.55 + np.array([200, 30, 30]) * 0.45
    img = Image.fromarray(arr.astype(np.uint8)).resize((W * 2, H * 2), Image.NEAREST)
    d = ImageDraw.Draw(img)

    def poly(points, color, width=2):
        pts = []
        for (x, y) in points + [points[0]]:
            sx, sy, dz = project(scene, cam, x, y)
            if dz > 0:
                pts.append((sx * 2, sy * 2))
        if len(pts) > 1:
            d.line(pts, fill=color, width=width)

    for p in data.get("walk", []):
        poly(list(p), (60, 230, 90))
    for zn in data.get("zones", []):
        if zn["camera"] == cam.name[4:]:
            poly(list(zn["poly"]), (240, 210, 60), 1)
    for b in data.get("blocks", []):
        poly(list(b), (230, 80, 80), 1)
    for dr in data.get("doors", []):
        poly(list(dr["poly"]), (80, 160, 255), 2)
    img.save(path)


def bake(name, fast=False, json_only=False, depth_only=False):
    t0 = time.time()
    mod = load_room(name)
    kit.reset_scene()
    scene = bpy.context.scene
    if fast:
        scene.cycles.samples = 16
    k = kit.Kit()
    data = mod.build(k)
    out_dir = os.path.join(ROOT, "art", "rooms", name)
    prev_dir = os.path.join(ROOT, "build", "rooms", name)
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(prev_dir, exist_ok=True)

    cams_json = []
    for c in data["cameras"]:
        cam = make_camera(c)
        scene.camera = cam
        bpy.context.view_layer.update()
        if depth_only:
            # 只算深度（擺鏡頭時快速檢查遮擋用，背景沿用舊的）
            depth, _hits = depth_map(scene, cam, k.occluders)
            Image.fromarray(depth).save(os.path.join(out_dir, f"{c['id']}_depth.png"))
        elif not json_only:
            render_camera(c, cam, scene, k, data, out_dir, prev_dir)
        R = cam.matrix_world.to_3x3()
        cams_json.append({
            "id": c["id"],
            "pos": list(c["pos"]),
            "target": list(c["target"]),
            "fov": c.get("fov", 60),
            "right": list(R @ Vector((1, 0, 0))),
            "up": list(R @ Vector((0, 1, 0))),
            "forward": list(R @ Vector((0, 0, -1))),
            "bg": f"{c['id']}_bg.png",
            "depth": f"{c['id']}_depth.png",
        })
        print(f"  {name}/{c['id']}: {time.time() - t0:.1f}s")
    write_json(name, data, cams_json, out_dir)
    if not json_only and not depth_only:
        # 也存一份 .blend 方便用 Blender 打開檢查（不進 repo）
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(prev_dir, name + ".blend"))
    print(f"{name}: done in {time.time() - t0:.1f}s")


def render_camera(c, cam, scene, k, data, out_dir, prev_dir):
    """算一個機位的背景、深度遮罩、預覽圖。"""
    raw = os.path.join(prev_dir, f"{c['id']}_raw.png")
    scene.render.filepath = raw
    bpy.ops.render.render(write_still=True)
    q = quantize_bg(raw, os.path.join(out_dir, f"{c['id']}_bg.png"))
    depth, hits = depth_map(scene, cam, k.occluders)
    Image.fromarray(depth).save(os.path.join(out_dir, f"{c['id']}_depth.png"))
    preview(q, hits, scene, cam, data, os.path.join(prev_dir, f"{c['id']}_preview.png"))


def write_json(name, data, cams_json, out_dir):
    room = {
        "id": name,
        "coords": "x right, y forward, z up, meters; floor z = 0",
        "resolution": [W, H],
        "tint": list(data.get("tint", (1.0, 1.0, 1.0))),
        "cameras": cams_json,
        "walk": [[list(p) for p in poly] for poly in data.get("walk", [])],
        "blocks": [[list(p) for p in poly] for poly in data.get("blocks", [])],
        # 二樓以上的地板（level 1、2…）和樓梯（斜坡），見 rooms/foyer.py
        "floors": data.get("floors", []),
        "ramps": data.get("ramps", []),
        "zones": [{"camera": z["camera"], "poly": [list(p) for p in z["poly"]]} for z in data.get("zones", [])],
        "doors": data.get("doors", []),
        "door_props": list(kit.DOOR_PROPS),
        "spawn": data.get("spawn", {}),
    }
    with open(os.path.join(out_dir, "room.json"), "w", encoding="utf-8") as f:
        json.dump(room, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    fast = "--fast" in sys.argv
    json_only = "--json" in sys.argv      # 只更新 room.json（可走範圍、門），不重新算圖
    depth_only = "--depth" in sys.argv    # 只更新 room.json 和深度遮罩（擺鏡頭時用），不算背景
    if "--all" in sys.argv:
        args = sorted(f[:-3] for f in os.listdir(os.path.join(ROOT, "rooms")) if f.endswith(".py") and not f.startswith("_"))
    for n in args:
        bake(n, fast, json_only, depth_only)
