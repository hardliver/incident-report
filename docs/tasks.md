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
- [x] A8 柯爾 v2：鼻樑、拇指、肩膀線條；跑步、受傷動作（轉身、開門之後再做）
- [x] A9 sprite 依房間燈光調色：room.json 的 `tint`
- [x] A10 角色定義檔（`characters/*.py`）＋共用的手臂、腿；諾拉
- [x] A11 殭屍：宴會賓客、女僕；待機、拖行、撲抓
- [x] A12 序章與第 1 章的房間：大門外（巡邏車、路燈、莊園正面）、衣帽間、餐廳
- [x] A13 道具圖示（`tools/icons.py`，17 個，32×32，從 3D 模型渲染）
- [ ] A14 小頭目模型：主廚、年度體態冠軍、上線（追擊者）
- [ ] A15 第 1 章其他房間：廚房（主廚戰）、圖書室、一樓走廊
- [ ] A16 開門轉場動畫（門的 3D 模型慢慢打開，預渲染成幾格）
- [ ] A17 道具的 3D 檢查畫面（物品欄裡可以轉動看的大圖）

## R1：垂直切片（之後）

見 content.md 第 14 節。
