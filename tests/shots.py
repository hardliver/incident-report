"""跑一段按鍵腳本，在指定的幀存圖（自動測試、檢查畫面用）。

用法：python3 tests/shots.py 腳本.txt 幀,幀,… [輸出資料夾] [--start 房間,x,y,角度]
--keep-saves：不清空存檔（接著上一次的測試，例如先存檔、再測讀檔）
--start：不從序章開始，報告畫面之後直接站在那個房間（測試用，見 main.lua 的 DEV_START）
腳本格式見 comet/platform/mac/main.c 的 --input：一行一段「幀數 按鍵…」。
需要 Comet 的 Mac 版播放器（環境變數 COMET，預設 ../comet/build/mac）。
存檔放在 build/test_saves（每次執行前清空），所以每次都是從沒有存檔開始。
最後把所有截圖拼成一張 sheet.png。
"""
import os
import shutil
import subprocess
import sys

from PIL import Image

COMET = os.environ.get("COMET", os.path.join("..", "comet", "build", "mac"))


def main():
    args = sys.argv[1:]
    keep = "--keep-saves" in args
    args = [a for a in args if a != "--keep-saves"]
    cart = "build/incident.lua"
    if "--start" in args:
        k = args.index("--start")
        room, x, y, yaw = args[k + 1].split(",")
        args = args[:k] + args[k + 2:]
        cart = "build/incident_test.lua"
        src = open("build/incident.lua", encoding="utf-8").read()
        open(cart, "w", encoding="utf-8").write(
            src + f'\nDEV_START = {{ room = "{room}", x = {int(x)}, y = {int(y)}, yaw = {int(yaw)} }}\n')
    script = args[0]
    frames = [int(f) for f in args[1].split(",")]
    outdir = args[2] if len(args) > 2 else "build/shots"
    os.makedirs(outdir, exist_ok=True)
    saves = "build/test_saves"
    if not keep:
        shutil.rmtree(saves, ignore_errors=True)
    os.makedirs(saves, exist_ok=True)
    out = os.path.join(outdir, "last.ppm")
    r = subprocess.run([COMET, cart, out, "--pak", "build/incident.pak", "--saves", saves,
                        "--input", script, "--shots", ",".join(map(str, frames))], capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode:
        raise SystemExit(r.returncode)
    imgs = []
    for f in frames:
        ppm = os.path.join(outdir, f"last_{f}.ppm")
        im = Image.open(ppm).convert("RGB")
        im.save(os.path.join(outdir, f"{f}.png"))
        os.remove(ppm)
        imgs.append(im)
    cols = min(4, len(imgs))
    sheet = Image.new("RGB", (320 * cols, 240 * ((len(imgs) + cols - 1) // cols)))
    for i, im in enumerate(imgs):
        sheet.paste(im, ((i % cols) * 320, (i // cols) * 240))
    sheet.save(os.path.join(outdir, "sheet.png"))


if __name__ == "__main__":
    main()
