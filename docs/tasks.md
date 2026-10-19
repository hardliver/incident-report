# 任務清單

最後更新：2026-10-19。完成一項就打勾並 commit（只 commit，不 push）。

## R0：素材與流程

- [x] A1 專案骨架：README、CREDITS、docs、tools
- [x] A2 PSX 貼圖庫（`tools/psx_textures.py`，32 張）
- [x] A3 場景與道具套件（`tools/kit.py`）
- [x] A4 房間預渲染流程（`tools/bake_room.py`）：背景、前景深度、room.json、預覽
- [x] A5 前廳（3 機位）、安全房（2 機位）
- [x] A6 柯爾：分段剛體模型、骨架、待機／走路／瞄準，8 方向 sprite（`tools/character.py`）
- [x] A7 合成測試（`tools/preview_composite.py`）：投影、縮放、深度遮擋，與引擎同一套數學
- [ ] A8 柯爾 v2：臉部細節、手的形狀、肩膀線條；跑步、受傷、轉身、開門動作
- [ ] A9 sprite 依房間燈光調色（暖色房間 vs. 冷色房間）
- [ ] A10 諾拉（同一套 `character.py`，參數化成角色定義檔）
- [ ] A11 殭屍：宴會賓客、莊園員工；拖行步伐、抓人動作
- [ ] A12 序章的其他房間：大門外、衣帽間
- [ ] A13 道具圖示（32×32，從 3D 模型渲染）

## R1：垂直切片（之後）

見 content.md 第 14 節。
