-- hotspots.lua：房間裡可以調查的東西（手寫的資料，不是自動產生的）
--
-- 站在附近、面向它、按 A 就會觸發。位置是公釐（和 rooms/*.py 的公尺 × 1000）。
-- kind：
--   "typewriter"  打字機（存檔）
--   "itembox"     物流箱（之後做）
--   "pickup"      撿東西：give = 拿到什麼，flag = 撿過了就不再出現
--   "look"        只是看看：text = 要說的話（好幾段用表格）

ROOM_NAME = {
    exterior = "莊園前庭", foyer = "前廳", cloakroom = "衣帽間", dining = "餐廳",
    hall_west = "一樓西側走廊", library = "圖書室", kitchen = "廚房", freezer = "冷凍庫",
    save_room = "安全房（一樓）", pantry_2f = "二樓配膳室", hall_east = "一樓東側走廊",
    gym = "健身房", locker_room = "更衣室", pool = "室內泳池", pool_full = "室內泳池",
    pool_machine = "泳池機房", guest_corridor = "客房走廊", guest_room = "客房 306",
    save_room_east = "安全房（東翼）",
}

HOT = {
    save_room = {
        { kind = "typewriter", x = 1350, y = 4450 },
        { kind = "itembox", x = 3500, y = 3400 },
        { kind = "pickup", x = 1900, y = 4300, give = "ink_ribbon", count = 3, flag = "ribbon_save1",
          text = "打字機旁邊有一盒色帶，還沒拆封。" },
    },
    save_room_east = {
        { kind = "typewriter", x = 550, y = 2800 },
        { kind = "itembox", x = 2900, y = 3500 },
    },
    foyer = {
        { kind = "look", x = 0, y = 13900, text = {
            "榮譽之牆。歷年經銷商的照片排得密密麻麻，每個人都笑得很用力。",
            "正中央有一扇沒有把手的門，門上嵌著四個圓形的凹槽。",
        } },
    },
    exterior = {
        { kind = "pickup", x = 3400, y = 7500, give = "handgun_ammo", count = 15, flag = "car_ammo",
          text = "巡邏車的後車廂。備用子彈還在原本的位置。" },
        { kind = "look", x = 3400, y = 7500, text = {
            "我的巡邏車。無線電只剩下雜訊。",
        } },
    },
    cloakroom = {
        { kind = "pickup", x = 1500, y = 2400, give = "painkillers", count = 1, flag = "cloak_pills",
          text = "大衣口袋裡有一盒止痛藥。" },
    },
}

-- 房間裡的殭屍。id 不能重複（殺掉之後記在 FLAGS["dead_" .. id]）。
-- state 省略 = 站著（idle）；"feed" = 跪著啃食，靠近才會站起來
ENEMIES = {
    cloakroom = {
        { id = "cloak_first", chr = "zombie_guest", x = 2700, y = 1500, yaw = 90, state = "feed", hp = 55 },
    },
    dining = {
        { id = "dining_guest", chr = "zombie_guest", x = -3000, y = 9000, yaw = 180, hp = 60 },
        { id = "dining_maid", chr = "zombie_maid", x = 3000, y = 8200, yaw = 200, hp = 50 },
    },
}

-- 找面前可以調查的東西：距離 1.6 公尺以內（桌子有深度，站在桌前也要碰得到）、大致在面前（左右 60° 以內）
function find_hotspot(room_id, x, y, yaw)
    local list = HOT[room_id]
    if list == nil then return nil end
    local fx, fy = G.sin(yaw), G.cos(yaw)
    local best, best_d = nil, 1600 * 1600
    for _, h in ipairs(list) do
        if not (h.kind == "pickup" and FLAGS[h.flag]) then
            local dx, dy = h.x - x, h.y - y
            local d2 = dx * dx + dy * dy
            -- 面向判斷：(dx, dy) 和面向的內積 > 距離 × cos60°（= 一半）
            local dot = (dx * fx + dy * fy) // 4096
            if d2 < best_d and dot * dot * 4 > d2 and dot > 0 then
                best, best_d = h, d2
            end
        end
    end
    return best
end
