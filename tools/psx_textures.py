"""PSX 風格貼圖產生器。

每張貼圖都是程式畫出來的：
  1. 用雜訊（noise）做出材質的底色變化
  2. 畫上圖案（木紋、壁紙花紋、磁磚縫……）
  3. 加上舊化（髒污、水漬、裂痕）
  4. 量化成 16–32 色，保留 PSX 的色階感

所有貼圖都可以無縫重複（tile）：雜訊用「環繞」的方式產生。

用法：python3 tools/psx_textures.py        → 輸出到 art/textures/
"""
import os
import sys
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "art", "textures")


# ---------------------------------------------------------------- 基本工具

def rng(seed):
    return np.random.default_rng(seed)


def tile_noise(size, cells, seed, octaves=3):
    """可無縫重複的雜訊，值在 0..1。

    做法：在 cells×cells 的小格子放亂數，用雙線性內插放大到 size。
    格子在邊界「環繞」（最右邊接回最左邊），所以貼圖可以無縫重複。
    """
    r = rng(seed)
    total = np.zeros((size, size))
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        c = cells * (2 ** o)
        if c > size:
            break
        g = r.random((c, c))
        # 環繞內插
        x = np.arange(size) * c / size
        x0 = np.floor(x).astype(int) % c
        x1 = (x0 + 1) % c
        fx = x - np.floor(x)
        fx = fx * fx * (3 - 2 * fx)            # smoothstep，比較柔和
        a = g[x0][:, x0] * (1 - fx)[None, :] + g[x0][:, x1] * fx[None, :]
        b = g[x1][:, x0] * (1 - fx)[None, :] + g[x1][:, x1] * fx[None, :]
        layer = a * (1 - fx)[:, None] + b * fx[:, None]
        total += layer * amp
        norm += amp
        amp *= 0.5
    return total / norm


def stretch_noise(size, cells_x, cells_y, seed):
    """拉長的雜訊（木紋用）：x 方向變化慢、y 方向變化快。"""
    r = rng(seed)
    g = r.random((cells_y, cells_x))
    img = Image.fromarray((g * 255).astype(np.uint8)).resize((size, size), Image.BICUBIC)
    return np.asarray(img) / 255.0


def hexc(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)


def ramp(t, colors):
    """把 0..1 的值對應到一串顏色（漸層）。"""
    t = np.clip(t, 0, 1)
    cs = [hexc(c) for c in colors]
    n = len(cs) - 1
    idx = np.minimum((t * n).astype(int), n - 1)
    f = (t * n - idx)[..., None]
    a = np.stack(cs)[idx]
    b = np.stack(cs)[idx + 1]
    return a * (1 - f) + b * f


def grime(img, seed, amount=0.35, size=None):
    """舊化：低頻的髒污斑塊，讓顏色變暗、偏黃褐。"""
    s = img.shape[0]
    n = tile_noise(s, 3, seed, 3)
    m = np.clip((n - 0.55) * 3, 0, 1)[..., None] * amount
    dirt = np.array([60, 48, 32], float)
    return img * (1 - m) + dirt * m


def water_stain(img, seed, top=True, amount=0.4):
    """水漬：從上方往下流的深色痕跡（牆面用）。"""
    s = img.shape[0]
    r = rng(seed)
    out = img.copy()
    for _ in range(r.integers(2, 5)):
        x = r.integers(0, s)
        w = r.integers(3, 10)
        length = r.integers(s // 4, s // 1)
        for y in range(length):
            k = (1 - y / length) * amount
            for dx in range(-w, w + 1):
                xx = (x + dx + int(3 * np.sin(y / 9))) % s
                fall = 1 - abs(dx) / (w + 1)
                yy = y if top else s - 1 - y
                out[yy, xx] = out[yy, xx] * (1 - k * fall) + np.array([50, 42, 30]) * k * fall
    return out


def quantize(arr, colors):
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    q = img.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    return q.convert("RGB")


def save(arr, name, colors=24):
    os.makedirs(OUT, exist_ok=True)
    im = quantize(arr, colors)
    im.save(os.path.join(OUT, name + ".png"))
    return im


# ---------------------------------------------------------------- 材質

def wood_floor(name, base, seed, size=128, planks=8):
    """木地板：橫向的木條，每條顏色略有不同，接縫是深色線。"""
    r = rng(seed)
    h = size // planks
    out = np.zeros((size, size, 3))
    grain = stretch_noise(size, 4, 48, seed)
    fine = tile_noise(size, 16, seed + 1, 2)
    for i in range(planks):
        tone = 0.75 + r.random() * 0.35
        y0, y1 = i * h, (i + 1) * h
        g = grain[y0:y1] * 0.6 + fine[y0:y1] * 0.4
        out[y0:y1] = ramp(g, base)[...] * tone
        # 木條的端縫（每條位置不同）
        cut = r.integers(0, size)
        out[y0:y1, cut:cut + 1] *= 0.45
        out[y0:y0 + 1] *= 0.4          # 長邊接縫
    out = grime(out, seed + 2, 0.3)
    return save(out, name, 24)


def wallpaper_damask(name, bg, fg, seed, size=128):
    """大馬士革花紋壁紙：菱形排列的花飾，加上褪色與水漬。"""
    img = Image.new("RGB", (size, size), tuple(int(v) for v in hexc(bg)))
    d = ImageDraw.Draw(img)
    c = tuple(int(v) for v in hexc(fg))
    cell = size // 2
    for cy in range(0, size + cell, cell):
        for cx in range(0, size + cell, cell):
            for (ox, oy) in ((0, 0), (cell // 2, cell // 2)):
                x, y = cx + ox, cy + oy
                # 花飾：上下兩片葉子＋中間的菱形
                d.polygon([(x, y - 22), (x + 9, y - 6), (x, y + 2), (x - 9, y - 6)], fill=c)
                d.polygon([(x, y + 22), (x + 9, y + 6), (x, y - 2), (x - 9, y + 6)], fill=c)
                d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=tuple(int(v * 0.8) for v in c))
                d.line([(x - 14, y), (x + 14, y)], fill=c, width=2)
    # 讓圖案環繞（左上角補畫已經涵蓋）
    arr = np.asarray(img).astype(float)
    n = tile_noise(size, 6, seed, 3)[..., None]
    arr = arr * (0.82 + 0.3 * n)
    arr = water_stain(arr, seed + 3, top=True, amount=0.35)
    arr = grime(arr, seed + 4, 0.25)
    return save(arr, name, 20)


def wainscot(name, base, seed, size=128):
    """護牆板：木頭外框＋凹進去的面板。"""
    grain = stretch_noise(size, 3, 32, seed).T          # 直紋
    arr = ramp(grain * 0.7 + 0.15, base)
    img = Image.fromarray(arr.astype(np.uint8))
    d = ImageDraw.Draw(img)
    hi = tuple(int(v) for v in hexc(base[-1]))
    lo = tuple(int(v * 0.5) for v in hexc(base[0]))
    for x0 in (8, 72):
        d.rectangle([x0, 14, x0 + 48, 110], outline=lo, width=2)
        d.line([(x0 + 2, 16), (x0 + 46, 16)], fill=hi)
        d.line([(x0 + 2, 16), (x0 + 2, 108)], fill=hi)
    d.rectangle([0, 0, size - 1, 6], fill=tuple(int(v * 0.8) for v in hexc(base[1])))
    d.line([(0, 6), (size, 6)], fill=lo, width=1)
    d.rectangle([0, size - 8, size - 1, size - 1], fill=lo)
    arr = np.asarray(img).astype(float)
    arr = grime(arr, seed + 1, 0.3)
    return save(arr, name, 20)


def plaster(name, base, seed, size=128, cracks=3):
    """灰泥牆：淡色、斑駁、有裂痕。"""
    n = tile_noise(size, 4, seed, 4)
    arr = ramp(n, base)
    img = Image.fromarray(arr.astype(np.uint8))
    d = ImageDraw.Draw(img)
    r = rng(seed)
    dark = tuple(int(v * 0.55) for v in hexc(base[0]))
    for _ in range(cracks):
        x, y = r.integers(0, size), r.integers(0, size)
        for _ in range(r.integers(8, 20)):
            nx, ny = x + r.integers(-6, 7), y + r.integers(2, 8)
            d.line([(x, y), (nx, ny)], fill=dark)
            x, y = nx % size, ny % size
    arr = np.asarray(img).astype(float)
    arr = water_stain(arr, seed + 2, True, 0.3)
    arr = grime(arr, seed + 3, 0.3)
    return save(arr, name, 20)


def marble_checker(name, a, b, seed, size=128, tiles=2):
    """黑白大理石棋盤格：每格有紋理（vein），格線是灰縫。"""
    vein = tile_noise(size, 5, seed, 4)
    v = np.abs(np.sin(vein * 18)) ** 0.25                  # 細細的紋路
    out = np.zeros((size, size, 3))
    t = size // tiles
    for i in range(tiles):
        for j in range(tiles):
            cols = a if (i + j) % 2 == 0 else b
            sl = (slice(i * t, (i + 1) * t), slice(j * t, (j + 1) * t))
            out[sl] = ramp(v[sl] * 0.8 + vein[sl] * 0.2, cols)
            out[i * t, j * t:(j + 1) * t] = 70
            out[i * t:(i + 1) * t, j * t] = 70
    out = grime(out, seed + 1, 0.25)
    return save(out, name, 24)


def marble(name, base, seed, size=128):
    """大理石（柱子、台座、樓梯）：細紋路＋淡淡的髒污。"""
    vein = tile_noise(size, 4, seed, 4)
    v = np.abs(np.sin(vein * 14 + tile_noise(size, 8, seed + 5, 2) * 3)) ** 0.3
    arr = ramp(v * 0.75 + vein * 0.25, base)
    arr = grime(arr, seed + 1, 0.3)
    return save(arr, name, 20)


def carpet(name, field, border, seed, size=128):
    """地毯：底色＋小花紋＋磨損。可以重複鋪在走廊。"""
    n = tile_noise(size, 32, seed, 2)
    arr = ramp(n * 0.5 + 0.25, field)
    img = Image.fromarray(arr.astype(np.uint8))
    d = ImageDraw.Draw(img)
    bc = tuple(int(v) for v in hexc(border))
    for y in range(8, size, 32):
        for x in range(8, size, 32):
            d.polygon([(x + 8, y), (x + 16, y + 8), (x + 8, y + 16), (x, y + 8)], outline=bc)
            d.point([(x + 8, y + 8)], fill=bc)
    arr = np.asarray(img).astype(float)
    wear = tile_noise(size, 2, seed + 1, 2)[..., None]
    arr = arr * (0.75 + 0.35 * wear)
    arr = grime(arr, seed + 2, 0.3)
    return save(arr, name, 20)


def stone_blocks(name, base, seed, size=128, rows=4):
    """石塊牆：錯位排列的石塊，縫是深色。"""
    n = tile_noise(size, 8, seed, 4)
    arr = ramp(n, base)
    img = Image.fromarray(arr.astype(np.uint8))
    d = ImageDraw.Draw(img)
    h = size // rows
    dark = tuple(int(v * 0.4) for v in hexc(base[0]))
    for i in range(rows):
        y = i * h
        d.line([(0, y), (size, y)], fill=dark, width=2)
        off = (h if i % 2 else 0)
        for x in range(off, size + h * 2, h * 2):
            d.line([(x % size, y), (x % size, y + h)], fill=dark, width=2)
    arr = np.asarray(img).astype(float)
    arr = grime(arr, seed + 1, 0.4)
    return save(arr, name, 20)


def metal_plate(name, base, seed, size=64, rust=0.5):
    """金屬板：刷紋＋鉚釘＋鏽斑。"""
    brush = stretch_noise(size, 2, 32, seed)
    arr = ramp(brush * 0.6 + 0.2, base)
    img = Image.fromarray(arr.astype(np.uint8))
    d = ImageDraw.Draw(img)
    for x in (4, size - 6):
        for y in (4, size - 6):
            d.ellipse([x, y, x + 2, y + 2], fill=tuple(int(v) for v in hexc(base[-1])))
    arr = np.asarray(img).astype(float)
    rn = tile_noise(size, 4, seed + 1, 3)
    m = np.clip((rn - (1 - rust * 0.6)) * 4, 0, 1)[..., None]
    arr = arr * (1 - m) + hexc("#6a3a1c") * m
    return save(arr, name, 16)


def tiles_bath(name, base, seed, size=128, n=8):
    """浴室／研究所的小方磚：磚縫、少數裂掉或髒掉的磚。"""
    r = rng(seed)
    t = size // n
    out = np.zeros((size, size, 3))
    noise = tile_noise(size, 16, seed, 2)
    for i in range(n):
        for j in range(n):
            tone = 0.9 + r.random() * 0.15
            if r.random() < 0.06:
                tone *= 0.7
            sl = (slice(i * t, (i + 1) * t), slice(j * t, (j + 1) * t))
            out[sl] = ramp(noise[sl] * 0.4 + 0.5, base) * tone
            out[i * t, j * t:(j + 1) * t] = hexc(base[0]) * 0.6
            out[i * t:(i + 1) * t, j * t] = hexc(base[0]) * 0.6
    out = water_stain(out, seed + 2, True, 0.25)
    out = grime(out, seed + 3, 0.35)
    return save(out, name, 16)


def fabric(name, base, seed, size=64):
    """布料（沙發、窗簾、床單）：細的織紋＋皺褶。"""
    weave = (np.add.outer(np.arange(size), np.arange(size)) % 2) * 0.08
    n = tile_noise(size, 4, seed, 3)
    arr = ramp(n * 0.7 + 0.15 + weave, base)
    arr = grime(arr, seed + 1, 0.2)
    return save(arr, name, 16)


def leather(name, base, seed, size=64):
    n = tile_noise(size, 12, seed, 3)
    cr = tile_noise(size, 24, seed + 1, 1)
    arr = ramp(n * 0.6 + 0.2 - (cr > 0.8) * 0.2, base)
    return save(arr, name, 16)


def brass(name, seed, size=32):
    n = tile_noise(size, 4, seed, 2)
    arr = ramp(n, ["#4a3410", "#9a7424", "#d8b050", "#f0d890"])
    arr = grime(arr, seed + 1, 0.4)
    return save(arr, name, 12)


def books(name, seed, size=128):
    """書架上的書背：高度、顏色、寬度都不一樣的直條。"""
    r = rng(seed)
    out = np.zeros((size, size, 3)) + hexc("#1a120c")
    cols = ["#5a1a1a", "#1e3a2a", "#2a2a4a", "#6a4a20", "#3a2a1a", "#4a4a40", "#702a1a"]
    rows = 2
    rh = size // rows
    for row in range(rows):
        x = 0
        while x < size:
            w = int(r.integers(4, 11))
            hgt = int(r.integers(int(rh * 0.65), rh - 4))
            c = hexc(cols[r.integers(0, len(cols))]) * (0.7 + 0.5 * r.random())
            y1 = (row + 1) * rh - 3
            out[y1 - hgt:y1, x:min(x + w, size)] = c
            out[y1 - hgt + 4:y1 - hgt + 6, x + 1:min(x + w - 1, size)] = c * 1.5   # 書背上的燙金線
            out[y1 - 12:y1 - 10, x + 1:min(x + w - 1, size)] = c * 1.5
            out[y1 - hgt:y1, x:x + 1] *= 0.5
            x += w
        out[(row + 1) * rh - 3:(row + 1) * rh] = hexc("#3a2414")   # 層板
    out = grime(out, seed + 1, 0.25)
    return save(out, name, 24)


def paper(name, seed, size=64, lines=True):
    n = tile_noise(size, 4, seed, 3)
    arr = ramp(n * 0.5 + 0.4, ["#8a8068", "#c8bea0", "#e8e0c8"])
    if lines:
        for y in range(10, size, 6):
            arr[y, 6:size - 6] *= 0.75
    arr = grime(arr, seed + 1, 0.3)
    return save(arr, name, 12)


def painting(name, seed, size=64, dark=True):
    """油畫：暗色的風景／肖像（看不清楚的筆觸）。"""
    n = tile_noise(size, 3, seed, 4)
    n2 = tile_noise(size, 8, seed + 1, 2)
    y = np.linspace(0, 1, size)[:, None]
    arr = ramp(np.clip(n * 0.5 + y * 0.5, 0, 1),
               ["#0e0c0a", "#2a2418", "#4a3a24", "#6a5a3a"] if dark else ["#1a2a3a", "#4a5a5a", "#8a7a5a", "#c8a870"])
    arr = arr * (0.85 + 0.3 * n2[..., None])
    return save(arr, name, 16)


def ceiling_wood(name, seed, size=128):
    grain = stretch_noise(size, 4, 40, seed)
    arr = ramp(grain * 0.6 + 0.2, ["#1a110a", "#2e1e12", "#4a3020"])
    for x in range(0, size, 32):
        arr[:, x:x + 2] *= 0.4
    arr = grime(arr, seed + 1, 0.3)
    return save(arr, name, 16)


# ---------------------------------------------------------------- 清單

def build_all():
    made = []
    def m(fn, *a, **k):
        made.append(a[0]); fn(*a, **k)

    # 地板
    m(wood_floor, "floor_wood_dark", ["#2a1a0e", "#4a2e18", "#6a4426", "#7e5430"], 11)
    m(wood_floor, "floor_wood_worn", ["#3a2818", "#5a4028", "#7a5a38", "#9a7850"], 12)
    m(marble_checker, "floor_marble_checker", ["#b8b0a0", "#d8d0c0", "#ece6d8"], ["#141210", "#2a2622", "#3e3832"], 13)
    m(marble, "marble_white", ["#5a564e", "#9a948a", "#bcb6aa", "#d0cabe"], 19)
    m(marble, "marble_dark", ["#141210", "#2a2622", "#3e3832", "#5a524a"], 20)
    m(carpet, "carpet_red", ["#2a0806", "#4a1210", "#6a1c18"], "#8a6a2a", 14)
    m(carpet, "carpet_green", ["#0a1a10", "#14301e", "#204a2e"], "#7a6a3a", 15)
    m(tiles_bath, "tiles_white", ["#8a8a80", "#c8c8bc", "#e0e0d4"], 16)
    m(tiles_bath, "tiles_lab_green", ["#3a4a40", "#6a8070", "#8aa090"], 17)
    m(stone_blocks, "floor_stone", ["#2a2824", "#4a4640", "#6a6458"], 18)
    # 牆
    m(wallpaper_damask, "wallpaper_damask_green", "#1e3426", "#2e4a36", 21)
    m(wallpaper_damask, "wallpaper_damask_red", "#3a1214", "#521c1e", 22)
    m(wallpaper_damask, "wallpaper_damask_cream", "#8a7a5a", "#a0906a", 23)
    m(wainscot, "wainscot_dark", ["#1e120a", "#3a2414", "#5a3a20"], 24)
    m(plaster, "plaster_cream", ["#6a6250", "#9a9078", "#b8ae94"], 25)
    m(plaster, "plaster_grey", ["#3e3c38", "#5e5a54", "#7a7670"], 26, cracks=6)
    m(stone_blocks, "wall_stone", ["#2a2620", "#46403a", "#625a50"], 27, rows=6)
    m(ceiling_wood, "ceiling_wood", 28)
    # 道具用
    m(wood_floor, "wood_furniture", ["#1e120a", "#3a2214", "#58361e", "#6a4428"], 31, size=64, planks=1)
    m(wood_floor, "wood_crate", ["#4a3a22", "#6a5434", "#8a7048", "#a08458"], 32, size=64, planks=4)
    m(metal_plate, "metal_steel", ["#2a2c2e", "#4a4e52", "#6a6e72", "#8a8e92"], 33, rust=0.3)
    m(metal_plate, "metal_rusty", ["#2a2420", "#4a3e36", "#6a5a4e"], 34, rust=1.0)
    m(metal_plate, "metal_typewriter", ["#0e1210", "#1e2620", "#2e3a32", "#46564a"], 35, rust=0.1)
    m(fabric, "fabric_velvet_red", ["#200606", "#3e0e0e", "#5a1616", "#701e1e"], 36)
    m(fabric, "fabric_linen", ["#6a6658", "#9a9482", "#b8b29e"], 37)
    m(fabric, "fabric_curtain_green", ["#0a1a10", "#16301e", "#22462c"], 38)
    m(leather, "leather_brown", ["#1a0e08", "#3a2214", "#5a3820"], 39)
    m(brass, "brass", 40)
    m(books, "books", 41)
    m(paper, "paper", 42)
    m(painting, "painting_dark", 43)
    m(painting, "painting_portrait", 44, dark=False)
    print(f"{len(made)} textures → {OUT}")
    return made


def contact_sheet(made, path):
    """所有貼圖排成一張總覽圖（放大 2 倍）。"""
    from PIL import ImageFont
    cols = 6
    cell = 128 * 2 + 8
    rows = (len(made) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + 18)), (16, 14, 18))
    d = ImageDraw.Draw(sheet)
    for i, n in enumerate(made):
        im = Image.open(os.path.join(OUT, n + ".png"))
        im = im.resize((im.width * 2 * (128 // im.width), im.height * 2 * (128 // im.height)), Image.NEAREST)
        x, y = (i % cols) * cell, (i // cols) * (cell + 18)
        sheet.paste(im, (x + 4, y + 4))
        d.text((x + 4, y + cell - 2), n, fill=(220, 210, 180))
    sheet.save(path)


if __name__ == "__main__":
    made = build_all()
    if "--sheet" in sys.argv:
        os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
        contact_sheet(made, os.path.join(ROOT, "build", "textures_sheet.png"))
