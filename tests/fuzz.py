"""隨機按鍵測試：從好幾個房間出發，亂按一通（走路、轉身、開門、開槍、物品欄），看遊戲會不會出錯（紅畫面）。

用法：python3 tests/fuzz.py [次數]
出錯時印出房間、種子和 Lua 的錯誤訊息；同一個種子每次都一樣，可以重現。
"""
import os
import random
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMET = os.environ.get("COMET", os.path.join(ROOT, "..", "comet", "build", "mac"))
STARTS = [
    'room="foyer",x=-6200,y=3000,yaw=270',
    'room="foyer",x=-5600,y=4000,yaw=0',
    'room="dining",x=4100,y=2000,yaw=270',
    'room="dining",x=4100,y=2000,yaw=270,flags={dead_dining_guest=true,dead_dining_maid=true}',
    'room="cloakroom",x=1200,y=800,yaw=0',
    'room="hall_west",x=1200,y=6000,yaw=0',
    'room="hall_east",x=1200,y=1000,yaw=0',
    'room="gym",x=800,y=2900,yaw=90',
]
KEYS = ["U", "U", "U B", "L", "R", "A", "A", "D", "LB", "LB RB", "LB D RB", "X", "START", "", "U X"]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    base = open(os.path.join(ROOT, "build", "incident.lua"), encoding="utf-8").read()
    cart = os.path.join(ROOT, "build", "fuzz.lua")
    script = os.path.join(ROOT, "build", "fuzz.txt")
    bad = 0
    for st in STARTS:
        open(cart, "w", encoding="utf-8").write(base + f"\nDEV_START={{{st},give={{handgun_ammo=30}}}}\n")
        for seed in range(n):
            rng = random.Random(seed)
            lines = ["30", "2 A", "40", "2 A", "10"]
            lines += [f"{rng.randint(3, 40)} {rng.choice(KEYS)}" for _ in range(200)]
            open(script, "w").write("\n".join(lines) + "\n")
            r = subprocess.run([COMET, cart, os.path.join(ROOT, "build", "fuzz.ppm"), "--pak",
                                os.path.join(ROOT, "build", "incident.pak"), "--input", script],
                               capture_output=True, text=True)
            errs = [l for l in r.stdout.splitlines() if "跑了" not in l]
            if errs or r.returncode:
                bad += 1
                print(f"✗ {st} 種子 {seed}：{errs[:2]}")
    print("全部通過" if bad == 0 else f"{bad} 次出錯")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
