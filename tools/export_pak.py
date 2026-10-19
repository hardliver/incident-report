"""把 art/ 裡的素材打包成 Comet 的資源包（build/incident.pak），並產生遊戲用的資料表（src/gen_data.lua）。

資源包的格式見 comet/core/pak.h。這支程式做的事：
  1. 房間背景：每個鏡頭一張。原本 256 色 → 重新量化成 128 色（調色盤 128–255），
     深度圖 320×240（公分）→ 160×120（單位 8 公分，每 2×2 取最近的遮擋物）
  2. 角色、道具圖示、狀態立繪、對話框：全部一起量化成 112 色（調色盤 16–127，所有角色共用），
     每格動畫裁掉透明的邊，記下左上角相對腳底的位置，一列一列壓縮。
     角色只存 5 個方向（0 正面 … 4 背面），5–7 由遊戲用 1–3 左右翻轉畫出來
  3. 開門動畫、物品欄等全螢幕介面：當成背景（128 色）
  4. 道具檢查畫面（轉一圈 12 格）：顏色放在 128–255（檢查時畫面上沒有房間背景，借用那一段）
  5. src/gen_data.lua：房間（鏡頭、可走範圍、門）、角色動畫索引等，全部換成整數
     （位置用公釐，方向向量放大 4096 倍），遊戲裡不用小數也不用三角函數

用法：python3 tools/export_pak.py
"""
import glob
import hashlib
import json
import math
import os
import struct

import numpy as np
from PIL import Image

sys_path_tools = os.path.dirname(os.path.abspath(__file__))
import sys  # noqa: E402
sys.path.insert(0, sys_path_tools)
import roomgeo  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ART = os.path.join(ROOT, "art")
OUT_PAK = os.path.join(ROOT, "build", "incident.pak")
OUT_LUA = os.path.join(ROOT, "src", "gen_data.lua")

PAK_BG, PAK_SPRITES, PAK_PAL, PAK_DATA = 1, 2, 3, 4
ACTOR_FIRST, ACTOR_COLORS = 16, 112        # 角色共用 16–127
BG_COLORS = 128                            # 背景 128–255
DEPTH_UNIT = 8                             # 深度單位：8 公分
VEC = 4096                                 # 方向向量放大倍數

CHARACTERS = ["cole", "nora", "zombie_guest", "zombie_maid", "zombie_civilian_m", "zombie_civilian_f",
              "zombie_janitor", "zombie_cook", "zombie_gym", "hound", "boss_chef", "boss_bodybuilder", "stalker"]
UI_SPRITES = ["status_cole_fine", "status_cole_caution", "status_cole_danger", "textbox"]
UI_SCREENS = ["inventory_bg", "itembox_bg", "document_bg", "save_typewriter"]


# ============================================================
# 量化
# ============================================================

def quantize_rgb(im, n, dither=True):
    """RGB 圖 → (編號陣列, 調色盤 [(r,g,b)…])，編號 0 .. n-1。"""
    q = im.convert("RGB").quantize(colors=n, method=Image.Quantize.MEDIANCUT,
                                   dither=Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE)
    pal = q.getpalette()[: n * 3]
    pal += [0] * (n * 3 - len(pal))
    return np.asarray(q, dtype=np.uint8), [tuple(pal[i * 3: i * 3 + 3]) for i in range(n)]


def rgba_of(path):
    im = Image.open(path)
    return im.convert("RGBA")


def build_actor_palette(images):
    """所有角色、圖示的不透明像素放在一起，量化成 ACTOR_COLORS 色。"""
    pix = []
    for im in images:
        a = np.asarray(im)
        pix.append(a[a[..., 3] >= 128][:, :3])
    allpx = np.concatenate(pix)
    # 像素太多時取樣（不影響結果太多，速度快很多）
    if len(allpx) > 400000:
        allpx = allpx[:: len(allpx) // 400000 + 1]
    strip = Image.fromarray(allpx.reshape(1, -1, 3).astype(np.uint8), "RGB")
    q = strip.quantize(colors=ACTOR_COLORS, method=Image.Quantize.MEDIANCUT, kmeans=3)
    pal = q.getpalette()[: ACTOR_COLORS * 3]
    palimg = Image.new("P", (1, 1))
    palimg.putpalette(pal + [0] * (768 - len(pal)))
    return [tuple(pal[i * 3: i * 3 + 3]) for i in range(ACTOR_COLORS)], palimg


def map_actor(im, palimg, first=ACTOR_FIRST):
    """RGBA → 全域顏色編號（first + i），透明 = 0。不抖色：角色小，抖色只會變髒。"""
    q = im.convert("RGB").quantize(palette=palimg, dither=Image.Dither.NONE)
    idx = np.asarray(q, dtype=np.int32) + first
    idx[np.asarray(im)[..., 3] < 128] = 0
    return idx.astype(np.uint8)


# ============================================================
# 資源包的項目（和 comet/tools/pak.mjs 相同的格式）
# ============================================================

def bg_entry(pixels, palette, depth=None):
    out = bytearray(struct.pack("<HHH", 320, 240, len(palette)))
    for c in palette:
        out += bytes(c)
    out += pixels.astype(np.uint8).tobytes()
    if depth is None:
        out += struct.pack("<HH", 0, 0)
    else:
        out += struct.pack("<HH", 160, 120)
        flat = depth.astype(np.uint8).ravel()
        i = 0
        while i < len(flat):
            n = 1
            while i + n < len(flat) and n < 255 and flat[i + n] == flat[i]:
                n += 1
            out += bytes((n, int(flat[i])))
            i += n
    return PAK_BG, bytes(out)


def crop(frame):
    """裁掉透明的邊。回傳 (像素, 左, 上)；全透明回傳 1×1。"""
    ys, xs = np.nonzero(frame)
    if len(xs) == 0:
        return np.zeros((1, 1), np.uint8), 0, 0
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    return frame[y0:y1, x0:x1], int(x0), int(y0)


def encode_rows(px):
    """一格角色 → 一列一列壓縮（comet/core/gfx.h）：每列（透明幾點、有顏色幾點、顏色…），前面是每列的位置。"""
    h, w = px.shape
    rows = []
    for y in range(h):
        r = px[y]
        out = bytearray()
        x = 0
        while x < w:
            skip = 0
            while x + skip < w and r[x + skip] == 0 and skip < 255:
                skip += 1
            run = 0
            while x + skip + run < w and r[x + skip + run] != 0 and run < 255:
                run += 1
            out += bytes((skip, run)) + r[x + skip:x + skip + run].tobytes()
            x += skip + run
        rows.append(bytes(out))
    head = bytearray()
    off = h * 2
    for r in rows:
        head += struct.pack("<H", off)
        off += len(r)
    assert off < 65536
    return bytes(head) + b"".join(rows)


def sprites_entry(frames):
    """frames = [(像素 h×w, ox, oy)]"""
    head = 2 + len(frames) * 12
    enc = [encode_rows(px) for px, _, _ in frames]
    out = bytearray(struct.pack("<H", len(frames)))
    off = head
    for (px, ox, oy), e in zip(frames, enc):
        h, w = px.shape
        out += struct.pack("<HHhhI", w, h, ox, oy, off)
        off += len(e)
    for e in enc:
        out += e
    return PAK_SPRITES, bytes(out)


def pal_entry(first, palette):
    out = bytearray(struct.pack("<HH", first, len(palette)))
    for c in palette:
        out += bytes(c)
    return PAK_PAL, bytes(out)


def write_pak(path, entries):
    names = list(entries)
    dir_ = bytearray()
    off = 48 + 48 * len(names)
    for n in names:
        t, data = entries[n]
        nb = n.encode()
        assert 1 <= len(nb) <= 32, n
        dir_ += nb.ljust(32, b"\0") + struct.pack("<IIII", t, off, len(data), 0)
        off += len(data)
    body = bytes(dir_) + b"".join(entries[n][1] for n in names)
    head = b"CPAK" + struct.pack("<II", 1, len(names)) + hashlib.sha256(body).digest() + struct.pack("<I", 0)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(head + body)
    return len(head) + len(body)


# ============================================================
# 各類素材
# ============================================================

def half_depth(depth_cm):
    """320×240 公分 → 160×120（8 公分）。每 2×2 取最近（最小的非 0）的遮擋物：寧可多擋一點，不要漏擋。"""
    d = depth_cm.astype(np.int64)
    d[d == 0] = 1 << 30
    blk = d.reshape(120, 2, 160, 2).min(axis=(1, 3))
    out = np.clip((blk + DEPTH_UNIT // 2) // DEPTH_UNIT, 1, 255)
    out[blk >= 1 << 30] = 0
    return out.astype(np.uint8)


def room_entries(entries, lua_rooms):
    for rj_path in sorted(glob.glob(os.path.join(ART, "rooms", "*", "room.json"))):
        rdir = os.path.dirname(rj_path)
        rj = json.load(open(rj_path))
        rid = rj["id"]
        for cam in rj["cameras"]:
            px, pal = quantize_rgb(Image.open(os.path.join(rdir, cam["bg"])), BG_COLORS)
            depth = np.asarray(Image.open(os.path.join(rdir, cam["depth"]))).astype(np.int64)
            entries[f"{rid}.{cam['id']}"] = bg_entry(px, pal, half_depth(depth))
        lua_rooms.append(room_lua(rj, roomgeo.Room(rj, rdir)))


def mm(v):
    return int(round(v * 1000))


def poly_lua(poly):
    return "{" + ",".join(f"{mm(x)},{mm(y)}" for x, y in poly) + "}"


def door_arrival(room, poly, z):
    """穿過這扇門進來時站在哪裡：離門最近、站得住的格子（同一層），面向房間裡面。"""
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    best, bd = None, 1e9
    for (_i, _j, x, y, cz, _lv) in room.cells:
        if abs(cz - z) > 0.5:
            continue
        d = math.hypot(x - cx, y - cy)
        if 0.55 <= d < bd:
            best, bd = (x, y, cz), d
    if best is None:
        return None
    x, y, cz = best
    yaw = int(round(math.degrees(math.atan2(x - cx, y - cy)))) % 360    # 背對門（0 = +y，順時針）
    return x, y, cz, yaw


def prop_poly(dp):
    """擺在場景裡的門（kit.door）→ 門前的範圍：寬 w、往房間裡 0.4 公尺。門朝 +y 再轉 yaw 度（逆時針）。"""
    a = math.radians(dp["yaw"])
    ux, uy = math.cos(a), math.sin(a)          # 門的寬度方向
    nx, ny = -math.sin(a), math.cos(a)         # 門面向的方向（房間裡面）
    hw = dp["w"] / 2
    pts = []
    for (s, t) in ((-hw, 0.0), (hw, 0.0), (hw, 0.4), (-hw, 0.4)):
        pts.append((dp["x"] + ux * s + nx * t, dp["y"] + uy * s + ny * t))
    return pts


def room_doors(rj, room):
    """真的門＋場景裡看得到、但沒有通往任何地方的門（變成「鎖著」）。"""
    doors = [dict(d) for d in rj["doors"]]
    for dp in rj.get("door_props", []):
        matched = False
        for d in rj["doors"]:
            xs = [p[0] for p in d["poly"]]
            ys = [p[1] for p in d["poly"]]
            if (min(xs) - 0.6 <= dp["x"] <= max(xs) + 0.6 and min(ys) - 0.6 <= dp["y"] <= max(ys) + 0.6
                    and abs(d.get("z", 0) - dp.get("z", 0)) < 0.5):
                matched = True
        if not matched:
            doors.append({"id": f"prop{len(doors)}", "to": "_locked", "poly": prop_poly(dp), "z": dp.get("z", 0), "prop": True})
    out = []
    for d in doors:
        arr = door_arrival(room, d["poly"], d.get("z", 0))
        a = f',arrive={{{mm(arr[0])},{mm(arr[1])},{mm(arr[2])},{arr[3]}}}' if arr else ""
        out.append(f'{{id="{d["id"]}",to="{d["to"]}",z={mm(d.get("z", 0))},p={poly_lua(d["poly"])}{a}}}')
    return ",".join(out)


def camera_grid_lua(room):
    """鏡頭格子 → Lua：每一層一個字串，每格 2 個字元（看得到的鏡頭的位元遮罩、最好的鏡頭），字元 = 48 + 數值。"""
    grids, _cells = room.grid
    levels = []
    for lv, g in sorted(grids.items()):
        chars = []
        for j in range(room.ny):
            for i in range(room.nx):
                mask, best = g.get((i, j), (0, 0))
                assert mask < 79 and best < 79
                chars.append(chr(48 + mask) + chr(48 + best))
        # 長字串 [==[ … ]==]：裡面的 \ 和 " 不會被當成跳脫字元
        levels.append(f'[{lv}]=[==[{"".join(chars)}]==]')
    return (f'{{x0={mm(room.x0)},y0={mm(room.y0)},nx={room.nx},ny={room.ny},cell={mm(roomgeo.CELL)},'
            f'lv={{{",".join(levels)}}}}}')


def surfaces_lua(rj):
    """地面：{level, 多邊形, z0, z1, 軸, a0, a1}。平的地面 z0 = z1。"""
    out = []
    for p in rj["walk"]:
        out.append(f'{{lv=0,p={poly_lua(p)},z0=0,z1=0}}')
    for f in rj.get("floors", []):
        for p in f["walk"]:
            out.append(f'{{lv={f["level"]},p={poly_lua(p)},z0={mm(f["z"])},z1={mm(f["z"])}}}')
    for r in rj.get("ramps", []):
        out.append(f'{{lv={r["level"]},p={poly_lua(r["poly"])},z0={mm(r["z0"])},z1={mm(r["z1"])},'
                   f'ax="{r["axis"]}",a0={mm(r["a0"])},a1={mm(r["a1"])}}}')
    blocks = [f'{{lv=0,p={poly_lua(p)}}}' for p in rj.get("blocks", [])]
    for f in rj.get("floors", []):
        blocks += [f'{{lv={f["level"]},p={poly_lua(p)}}}' for p in f.get("blocks", [])]
    return ",".join(out), ",".join(blocks)


def room_lua(rj, room):
    """一個房間的資料 → Lua 表格（整數）。"""
    room.grid = room.camera_grid()
    room.cells = room.grid[1]
    cams = []
    for c in rj["cameras"]:
        f = 160 / math.tan(math.radians(c["fov"]) / 2)   # 焦距（像素），水平視角
        vec = lambda v: ",".join(str(int(round(a * VEC))) for a in v)  # noqa: E731
        cams.append(f'{c["id"]}={{x={mm(c["pos"][0])},y={mm(c["pos"][1])},z={mm(c["pos"][2])},'
                    f'r={{{vec(c["right"])}}},u={{{vec(c["up"])}}},f={{{vec(c["forward"])}}},foc={int(round(f))}}}')
    cam_ids = ",".join(f'"{c["id"]}"' for c in rj["cameras"])
    zones = ",".join(f'{{cam="{z["camera"]}",p={poly_lua(z["poly"])}}}' for z in rj["zones"])
    surf, blocks = surfaces_lua(rj)
    tint = ",".join(str(int(round(t * 256))) for t in rj.get("tint", (1, 1, 1)))
    sp = rj.get("spawn", {"x": 0, "y": 0, "yaw": 0})
    return (f'ROOMS["{rj["id"]}"]={{cams={{{",".join(cams)}}},cam_ids={{{cam_ids}}},zones={{{zones}}},'
            f'doors={{{room_doors(rj, room)}}},surf={{{surf}}},blocks={{{blocks}}},grid={camera_grid_lua(room)},'
            f'tint={{{tint}}},spawn={{x={mm(sp.get("x", 0))},y={mm(sp.get("y", 0))},yaw={int(sp.get("yaw", 0)) % 360}}}}}')


def character_entries(entries, palimg, lua_spr):
    for name in CHARACTERS:
        d = os.path.join(ART, "characters", name)
        meta = json.load(open(os.path.join(d, f"{name}_sheet.json")))
        sheet = map_actor(rgba_of(os.path.join(d, f"{name}_sheet.png")), palimg)
        fw, fh = meta["frame"]
        pvx, pvy = meta["pivot"]
        frames, anims = [], {}
        for r, row in enumerate(meta["rows"]):
            # 只存方向 0–4（正面、右前、右、右後、背面），5–7 用 1–3 左右翻轉，省下 3/8
            if row["dir"] > 4:
                continue
            if row["dir"] == 0:
                anims[row["anim"]] = (len(frames), row["frames"])
            for i in range(row["frames"]):
                px, x0, y0 = crop(sheet[r * fh:(r + 1) * fh, i * fw:(i + 1) * fw])
                frames.append((px, x0 - pvx, y0 - pvy))
        entries[f"chr.{name}"] = sprites_entry(frames)
        an = ",".join(f"{a}={{{s},{n}}}" for a, (s, n) in anims.items())
        # 第 d 個方向（0–4）的第 i 格 = start + d × n + i
        lua_spr.append(f'CHR["{name}"]={{ppm={meta["pixels_per_meter"]},anim={{{an}}}}}')


def icon_entries(entries, palimg, lua_spr):
    icons = sorted(p for p in glob.glob(os.path.join(ART, "icons", "*.png")) if not p.endswith("icons_sheet.png"))
    frames, names = [], []
    for p in icons:
        idx = map_actor(rgba_of(p), palimg)
        frames.append((idx, 0, 0))   # 圖示不裁切：32×32，左上角就是 (x, y)
        names.append(os.path.splitext(os.path.basename(p))[0])
    entries["icons"] = sprites_entry(frames)
    lua_spr.append("ICON={" + ",".join(f'{n}={i}' for i, n in enumerate(names)) + "}")
    # 介面小圖：狀態立繪、對話框
    frames = []
    for n in UI_SPRITES:
        frames.append((map_actor(rgba_of(os.path.join(ART, "ui", f"{n}.png")), palimg), 0, 0))
    entries["ui"] = sprites_entry(frames)
    lua_spr.append("UI={" + ",".join(f'{n}={i}' for i, n in enumerate(UI_SPRITES)) + "}")
    return names


def item_entries(entries):
    """道具檢查：每個道具自己的 128 色（放在 128–255），12 格轉一圈。"""
    for p in sorted(glob.glob(os.path.join(ART, "items", "*_turn.png"))):
        name = os.path.basename(p)[: -len("_turn.png")]
        im = rgba_of(p)
        a = np.asarray(im)
        opaque = a[a[..., 3] >= 128][:, :3]
        strip = Image.fromarray(opaque.reshape(1, -1, 3).astype(np.uint8), "RGB")
        q = strip.quantize(colors=BG_COLORS, method=Image.Quantize.MEDIANCUT)
        pal = q.getpalette()[: BG_COLORS * 3]
        palimg = Image.new("P", (1, 1))
        palimg.putpalette(pal + [0] * (768 - len(pal)))
        idx = map_actor(im, palimg, first=128)
        n = im.width // 96
        frames = []
        for i in range(n):
            px, x0, y0 = crop(idx[:, i * 96:(i + 1) * 96])
            frames.append((px, x0 - 48, y0 - 48))   # 以中心為基準

        entries[f"item.{name}"] = sprites_entry(frames)
        entries[f"item.{name}.pal"] = pal_entry(128, [tuple(pal[i * 3:i * 3 + 3]) for i in range(BG_COLORS)])


def screen_entries(entries, lua_spr):
    for n in UI_SCREENS:
        px, pal = quantize_rgb(Image.open(os.path.join(ART, "ui", f"{n}.png")), BG_COLORS)
        entries[f"scr.{n}"] = bg_entry(px, pal)
    # 開門動畫：整段共用一組 128 色
    doors = []
    for kind_dir in sorted(glob.glob(os.path.join(ART, "doors", "*"))):
        kind = os.path.basename(kind_dir)
        meta = json.load(open(os.path.join(kind_dir, "door.json")))
        frames = [Image.open(os.path.join(kind_dir, f"frame_{i:02d}.png")).convert("RGB") for i in range(meta["frames"])]
        strip = Image.new("RGB", (320, 240 * len(frames)))
        for i, f in enumerate(frames):
            strip.paste(f, (0, i * 240))
        px, pal = quantize_rgb(strip, BG_COLORS)
        for i in range(len(frames)):
            entries[f"door.{kind}.{i:02d}"] = bg_entry(px[i * 240:(i + 1) * 240], pal)
        doors.append(f'{kind}={{frames={meta["frames"]},fps={meta["fps"]},hold_start={meta["hold_start"]},hold_end={meta["hold_end"]}}}')
    lua_spr.append("DOORANIM={" + ",".join(doors) + "}")
    lay = json.load(open(os.path.join(ART, "ui", "inventory_layout.json")))
    lua_spr.append("INV_LAYOUT=" + lua_value(lay))


def lua_value(v):
    if isinstance(v, dict):
        return "{" + ",".join(f"{k}={lua_value(x)}" for k, x in v.items()) + "}"
    if isinstance(v, (list, tuple)):
        return "{" + ",".join(lua_value(x) for x in v) + "}"
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    return str(int(v))


def main():
    entries = {}
    lua_rooms, lua_spr = [], []

    # 角色共用調色盤：先把所有要用的圖收集起來
    actor_imgs = [rgba_of(os.path.join(ART, "characters", n, f"{n}_sheet.png")) for n in CHARACTERS]
    actor_imgs += [rgba_of(p) for p in glob.glob(os.path.join(ART, "icons", "*.png")) if not p.endswith("icons_sheet.png")]
    actor_imgs += [rgba_of(os.path.join(ART, "ui", f"{n}.png")) for n in UI_SPRITES]
    actor_pal, palimg = build_actor_palette(actor_imgs)
    entries["actors"] = pal_entry(ACTOR_FIRST, actor_pal)

    character_entries(entries, palimg, lua_spr)
    icon_entries(entries, palimg, lua_spr)
    item_entries(entries)
    screen_entries(entries, lua_spr)
    room_entries(entries, lua_rooms)

    size = write_pak(OUT_PAK, entries)
    os.makedirs(os.path.dirname(OUT_LUA), exist_ok=True)
    with open(OUT_LUA, "w") as f:
        f.write("-- gen_data.lua：由 tools/export_pak.py 自動產生，不要手動修改\n")
        f.write("-- 位置：公釐；方向向量：放大 4096 倍；tint：256 = 1.0\n\n")
        f.write("ROOMS = {}\nCHR = {}\n\n")
        # 正弦表：SIN[角度 + 1] = sin(角度) × 4096（角度 0–359）。遊戲裡不呼叫 math.sin：
        # 各平台的三角函數可能差最後一位，重播就會對不上；查表一定一樣
        f.write("SIN={" + ",".join(str(int(round(math.sin(math.radians(a)) * VEC))) for a in range(360)) + "}\n")
        for line in lua_rooms + lua_spr:
            f.write(line + "\n")
    print(f"{os.path.relpath(OUT_PAK, ROOT)}：{len(entries)} 項，{size / 1024 / 1024:.1f} MB")
    print(f"{os.path.relpath(OUT_LUA, ROOT)}：{len(lua_rooms)} 個房間")
    # 角色量化結果的預覽（檢查顏色有沒有跑掉）
    prev = Image.new("RGB", (ACTOR_COLORS * 4, 8))
    for i, c in enumerate(actor_pal):
        prev.paste(c, (i * 4, 0, i * 4 + 4, 8))
    prev.resize((ACTOR_COLORS * 8, 16), Image.NEAREST).save(os.path.join(ROOT, "build", "actor_palette.png"))


if __name__ == "__main__":
    main()
