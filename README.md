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
```

## 資料夾

| 路徑 | 內容 |
|---|---|
| `tools/` | 素材產生流程（貼圖、模型套件、預渲染） |
| `rooms/` | 房間定義（Python）：擺設、燈光、攝影機、可走區域 |
| `art/` | 產生出來、要進 repo 的素材 |
| `build/` | 中間產物與預覽（不進 repo） |
| `docs/` | 企劃、美術規格、任務清單 |
