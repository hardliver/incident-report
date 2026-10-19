-- world.lua：房間、固定鏡頭、投影、地面與碰撞、門
--
-- 每個房間有好幾個鏡頭（ROOMS[id].cams）。打包工具把房間切成 25 公分的格子，
-- 算好每一格「哪些鏡頭看得到角色」和「哪個鏡頭最好」（ROOMS[id].grid，見 tools/roomgeo.py）。
-- 換鏡頭的規則：目前的鏡頭還看得到角色就不換；看不到才換成那一格最好的鏡頭。
-- 這樣不會在兩個鏡頭的交界來回跳，也不會出現「人走出畫面」的鏡頭。

W = {
    id = nil,        -- 目前房間的 id
    room = nil,      -- ROOMS[id]
    cam_id = nil,    -- 目前鏡頭
    cam = nil,
}

local PLAYER_R = 280   -- 角色的半徑（公釐）：離牆、家具至少這麼遠
local STEP_Z = 350     -- 走一步最多上下多少（樓梯一階 300）

-- 換鏡頭：載入那個鏡頭的背景（像素、顏色、深度）
local function set_camera(id)
    W.cam_id = id
    W.cam = W.room.cams[id]
    bgload(W.id .. "." .. id)
end

-- 重新載入目前鏡頭的背景（從打字機、物品欄這些全螢幕畫面回來時）
function W.refresh()
    bgload(W.id .. "." .. W.cam_id)
end

-- 依位置選鏡頭。lv：角色在哪一層（0 = 一樓，1 = 二樓，10 以上 = 樓梯）
function W.update_camera(x, y, lv)
    local g = W.room.grid
    local i, j = (x - g.x0) // g.cell, (y - g.y0) // g.cell
    local s = g.lv[lv or 0]
    if s == nil or i < 0 or j < 0 or i >= g.nx or j >= g.ny then return false end
    local k = (j * g.nx + i) * 2 + 1
    local mask, best = s:byte(k) - 48, s:byte(k + 1) - 48
    if best == 0 then return false end
    -- 目前的鏡頭還看得到：不換
    for n, id in ipairs(W.room.cam_ids) do
        if id == W.cam_id and (mask >> (n - 1)) & 1 == 1 then return false end
    end
    local id = W.room.cam_ids[best]
    if id == W.cam_id then return false end
    set_camera(id)
    return true
end

-- 角色的顏色依房間的光線染色（從物品欄這種不染色的畫面回來時也要呼叫）
function W.apply_tint()
    local t = W.room.tint
    paltint(16, 112, t[1], t[2], t[3])
end

-- 進入房間
function W.load(id, x, y, z)
    W.id = id
    W.room = ROOMS[id]
    W.cam_id = nil
    W.apply_tint()
    local _, lv = W.ground(x, y, z or 0)
    if not W.update_camera(x, y, lv) then set_camera(W.room.cam_ids[1]) end
end

-- ============================================================
-- 投影：世界座標（公釐）→ 畫面座標
-- ============================================================
-- 鏡頭的三個方向（右 r、上 u、前 f）都放大了 4096 倍。
-- 一個點相對鏡頭的位移 (dx, dy, dz) 和三個方向各做內積，就得到它在鏡頭眼中的
-- 「往右多少、往上多少、往前多遠」。往前越遠，畫在畫面上就越靠近中心、越小：
--   畫面 x = 160 + 焦距 × 往右 / 往前
--   畫面 y = 120 − 焦距 × 往上 / 往前
-- 回傳：畫面 x、y，離鏡頭的深度（公分），以及 zf（往前的距離 × 4096，算縮放用）。
-- 在鏡頭後面回傳 nil
function W.project(x, y, z)
    local c = W.cam
    local dx, dy, dz = x - c.x, y - c.y, z - c.z
    local zf = dx * c.f[1] + dy * c.f[2] + dz * c.f[3]
    if zf < 200 * 4096 then return nil end   -- 太近或在鏡頭後面
    local xr = dx * c.r[1] + dy * c.r[2] + dz * c.r[3]
    local yu = dx * c.u[1] + dy * c.u[2] + dz * c.u[3]
    return 160 + c.foc * xr // zf, 120 - c.foc * yu // zf, zf // 40960, zf
end

-- 角色要放大幾倍（256 = 原尺寸）。角色圖是「每公尺 ppm 像素」畫的，
-- 在 zf 這麼遠的地方，每公尺佔畫面 焦距 / 距離（公尺）像素
function W.scale(zf, ppm)
    return 256 * W.cam.foc * 4096000 // (zf * ppm)
end

-- 角色在鏡頭眼中面向哪個方向。角色圖的方向：0 = 面向鏡頭，2 = 面向畫面左邊，
-- 4 = 背對鏡頭，6 = 面向畫面右邊（每 45° 一格）。
-- 回傳（圖的方向 0–4，要不要左右翻轉）：5–7 沒有存，用 3–1 翻轉
function W.view_dir(yaw)
    local fx, fy = G.sin(yaw), G.cos(yaw)                 -- 角色面向的方向（世界）
    local c = W.cam
    local left = -(fx * c.r[1] + fy * c.r[2]) // 4096     -- 往畫面左邊的分量
    local toward = -(fx * c.f[1] + fy * c.f[2]) // 4096   -- 往鏡頭（面向觀眾）的分量
    local d = G.angle8(left, toward) // 45                -- angle8：0 = 面向鏡頭，90 = 面向左
    if d > 4 then return 8 - d, true end
    return d, false
end

-- ============================================================
-- 地面與碰撞
-- ============================================================
-- 地面（ROOMS[id].surf）有三種：一樓（level 0，高度 0）、樓上的地板（level 1…）、
-- 樓梯（level 10…，高度沿著 x 或 y 從 z0 升到 z1）。障礙物（blocks）只擋同一層。
-- 一樓和二樓的範圍在地圖上可以重疊（迴廊就在一樓的正上方），靠「高度差」分辨角色在哪一層。

-- 地面 s 在 (x, y) 的高度
local function surf_z(s, x, y)
    if s.ax == nil then return s.z0 end
    local a = s.ax == "x" and x or y
    if a <= s.a0 then return s.z0 end
    if a >= s.a1 then return s.z1 end
    return s.z0 + (s.z1 - s.z0) * (a - s.a0) // (s.a1 - s.a0)
end

-- (x, y) 在高度 z 附近站得住的地面：回傳 高度, level；沒有回傳 nil
function W.ground(x, y, z)
    local best_z, best_lv, best_d
    for _, s in ipairs(W.room.surf) do
        if G.inpoly(s.p, x, y) then
            local sz = surf_z(s, x, y)
            local d = math.abs(sz - z)
            if d <= STEP_Z and (best_d == nil or d < best_d) then
                local blocked = false
                for _, b in ipairs(W.room.blocks) do
                    if b.lv == s.lv and G.inpoly(b.p, x, y) then blocked = true break end
                end
                if not blocked then best_z, best_lv, best_d = sz, s.lv, d end
            end
        end
    end
    return best_z, best_lv
end

-- 角色站在 (x, y)、腳在高度 z 附近可不可以：中心和前後左右四個點都要站得住。
-- 可以的話回傳新的高度和 level
function W.can_stand(x, y, z)
    local cz, lv = W.ground(x, y, z)
    if cz == nil then return nil end
    local r = PLAYER_R
    if W.ground(x + r, y, cz) and W.ground(x - r, y, cz) and W.ground(x, y + r, cz) and W.ground(x, y - r, cz) then
        return cz, lv
    end
    return nil
end

-- 會擋路的角色（主角、活著的殭屍）。由主程式每次換房間時設定
W.actors = {}
local BODY = 560   -- 兩個角色中心至少相隔多遠（公釐）

-- 從 (x, y) 走到 (nx, ny) 會不會撞到別的角色。已經貼在一起時，只要是「離開」就可以走（不然會卡住）。
-- 不同樓層的角色不會相撞
local function bump(self, x, y, nx, ny)
    for _, a in ipairs(W.actors) do
        if a ~= self and not a.dead and math.abs((a.z or 0) - (self.z or 0)) < 1000 then
            local ox, oy = nx - a.x, ny - a.y
            local d2 = ox * ox + oy * oy
            if d2 < BODY * BODY then
                local px, py = x - a.x, y - a.y
                if d2 <= px * px + py * py then return true end
            end
        end
    end
    return false
end

local function try(self, nx, ny)
    local z, lv = W.can_stand(nx, ny, self.z or 0)
    if z == nil or bump(self, self.x, self.y, nx, ny) then return false end
    self.x, self.y, self.z, self.lv = nx, ny, z, lv
    return true
end

-- 角色 self 往 (dx, dy) 移動（會更新 self.x、y、z、lv）。撞到東西時試著只走 x 或只走 y，
-- 貼著牆斜走時才會「滑」過去，而不是整個卡住。回傳有沒有動
function W.move(self, dx, dy)
    if try(self, self.x + dx, self.y + dy) then return true end
    if dx ~= 0 and try(self, self.x + dx, self.y) then return true end
    if dy ~= 0 and try(self, self.x, self.y + dy) then return true end
    return false
end

-- 兩點的距離（公釐）。整數開根號：先用浮點數算，再取整數（只用在比較遠近，不影響重播）
function W.dist(ax, ay, bx, by)
    local dx, dy = ax - bx, ay - by
    return math.floor(math.sqrt(dx * dx + dy * dy))
end

-- ============================================================
-- 門
-- ============================================================

-- 面前的門：門的範圍（牆邊的一塊矩形）往外擴大 60 公分，角色的中心在裡面、
-- 和門在同一層，而且面向門所在的那面牆（左右 60° 以內）。背對著門打不開
function W.door_at(x, y, z, yaw)
    local r = 600
    local fx, fy = G.sin(yaw), G.cos(yaw)
    for _, d in ipairs(W.room.doors) do
        local p = d.p
        local x0, y0, x1, y1 = p[1], p[2], p[1], p[2]
        for i = 1, #p // 2 do
            x0 = math.min(x0, p[i * 2 - 1]); x1 = math.max(x1, p[i * 2 - 1])
            y0 = math.min(y0, p[i * 2]);     y1 = math.max(y1, p[i * 2])
        end
        if x >= x0 - r and x <= x1 + r and y >= y0 - r and y <= y1 + r and math.abs(z - d.z) < 1000 then
            -- 面向判斷：要面向「門所在的那面牆」。門的進入點（arrive，打包工具算的，在門前、房間裡面）
            -- 指向門中心的方向，就是「朝著門」的方向；和角色面向的夾角要小於 60°（cos 60° = 0.5）
            local cx, cy = G.center(p)
            local nx, ny = cx - x, cy - y
            if d.arrive then nx, ny = cx - d.arrive[1], cy - d.arrive[2] end
            local len = W.dist(0, 0, nx, ny)
            if len == 0 or (nx * fx + ny * fy) * 2 > len * 4096 then return d end
        end
    end
    return nil
end

-- 穿過門之後站在哪裡：新房間裡「通往舊房間」的那扇門前面（打包工具算好的 arrive）。
-- 回傳 x, y, z, 面向的角度
function W.arrival(room_id, from_id, door_id)
    local room = ROOMS[room_id]
    local door
    for _, d in ipairs(room.doors) do
        if d.to == from_id and d.arrive then door = d break end
    end
    if door == nil then
        for _, d in ipairs(room.doors) do
            if d.id == door_id and d.arrive then door = d break end
        end
    end
    if door == nil then
        return room.spawn.x, room.spawn.y, 0, room.spawn.yaw
    end
    local a = door.arrive
    return a[1], a[2], a[3], a[4]
end
