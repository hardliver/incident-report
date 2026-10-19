# 事故報告 INCIDENT REPORT

Nova One / Comet 引擎上的固定視角恐怖冒險遊戲（早期惡靈古堡式＋事件與對話上的黑色幽默）。

- 遊戲 ID：`hardliver/incident-report`
- 平台：Level 1（320×240，每張背景 256 色），網頁版同時可玩
- 企劃：`docs/content.md`；美術規格：`docs/art-style.md`；任務：`docs/tasks.md`

## 素材

**全部原創**，由 `tools/` 裡的 Python 腳本產生（貼圖、模型、場景、預渲染）。
itch.io 上的 PSX 素材包只當風格參考，沒有使用任何檔案（見 `CREDITS.md`）。

## 需要的工具

```sh
pip install bpy numpy pillow     # bpy = Blender 的 Python 模組，不需要打開 Blender
```

## 產生素材

```sh
python3 tools/psx_textures.py          # 貼圖 → art/textures/
python3 tools/bake_room.py foyer       # 房間 → build/rooms/foyer/
python3 tools/bake_room.py --all
python3 tools/character.py cole        # 角色 sprite → art/characters/cole/（角色定義在 characters/）
python3 tools/preview_composite.py     # 把角色放進房間測試遮擋 → build/composite_test.png
python3 tools/icons.py                 # 物品欄圖示 → art/icons/
python3 tools/icons.py --inspect       # 檢查道具的轉台大圖 → art/items/
python3 tools/door_anim.py             # 開門轉場 → art/doors/
python3 tools/ui.py                    # 介面底圖 → art/ui/
```

## 打包與試玩

遊戲程式在 `src/`（Lua），大圖放在資源包 `build/incident.pak`（格式見 comet 的 `core/pak.h`）。

```sh
python3 tools/export_pak.py            # art/ → build/incident.pak、src/gen_data.lua
node ../comet/tools/cart.mjs .         # src/ → build/incident.lua（遊戲檔）
python3 tests/check_doors.py           # 檢查每扇門都走得到（含二樓、樓梯）
python3 tests/check_cameras.py         # 檢查每個站得到的地方都有鏡頭看得到 → build/camera_maps/
```

- **在 Comet Studio 玩**：開啟資料夾，選這個資料夾（`comet.json` 裡有 `"pak"`，會自動載入資源包）
- **網頁版**：把 `build/incident.lua` 和 `build/incident.pak` 放在一起，用 `play.html?game=incident.lua` 打開
- **自動測試**：`python3 tests/shots.py tests/typewriter.txt 120,197 --start save_room,1400,2600,0`
  用按鍵腳本跑遊戲、在指定的幀存圖（需要 comet 的 `build/mac`）

操作（坦克式）：上＝前進、下＝後退、左右＝轉身、按住 B＋上＝跑、A＝調查／開門（要面向門）、
按住 L＝舉槍、R＝開槍（鍵盤：Q、E；沒有肩鍵的手把：按住 B 舉槍、A 開槍）、Start＝物品欄、Select＝除錯資訊。

## 資料夾

| 路徑 | 內容 |
|---|---|
| `src/` | 遊戲程式（Lua）；`gen_data.lua` 是 `export_pak.py` 自動產生的 |
| `tests/` | 自動測試：門的可達性、按鍵腳本截圖 |
| `tools/` | 素材產生流程（貼圖、模型套件、預渲染、打包） |
| `rooms/` | 房間定義（Python）：擺設、燈光、攝影機、可走區域 |
| `art/` | 產生出來、要進 repo 的素材 |
| `build/` | 中間產物與預覽（不進 repo） |
| `docs/` | 企劃、美術規格、任務清單 |
