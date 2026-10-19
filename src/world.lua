-- world.lua：房間、固定鏡頭、投影、碰撞、門
--
-- 每個房間有好幾個鏡頭（ROOMS[id].cams），地上畫了好幾塊「鏡頭區」（zones）：
-- 主角走進哪一塊，就切到那一塊指定的鏡頭，換上那個鏡頭預先算好的背景。
-- 這就是早期惡靈古堡的固定視角。

W = {
    id = nil,        -- 目前房間的 id
    room = nil,      -- ROOMS[id]
    cam_id = nil,    -- 目前鏡頭
    cam = nil,
}

local PLAYER_R = 280   -- 角色的半徑（公釐）：離牆、家具至少這麼遠

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

-- 依位置選鏡頭：第一個包含這一點的鏡頭區。都不包含就維持原本的鏡頭
function W.update_camera(x, y)
    for _, z in ipairs(W.room.zones) do
        if G.inpoly(z.p, x, y) then
            if z.cam ~= W.cam_id then
                set_camera(z.cam)
                return true
            end
            return false
        end
    end
    return false
end

-- 角色的顏色依房間的光線染色（從物品欄這種不染色的畫面回來時也要呼叫）
function W.apply_tint()
    local t = W.room.tint
    paltint(16, 112, t[1], t[2], t[3])
end

-- 進入房間。角色的顏色依房間的光線染色（暖色的燈、冷色的月光）
function W.load(id, x, y)
    W.id = id
    W.room = ROOMS[id]
    W.cam_id = nil
    W.apply_tint()
    if not W.update_camera(x, y) then
        -- 不在任何鏡頭區裡（不該發生）：用第一個鏡頭
        local first = W.room.zones[1].cam
        set_camera(first)
    end
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
-- 碰撞
-- ============================================================

-- 這一點能不能站：在可走範圍裡，而且不在任何障礙物（家具）裡
local function free_point(x, y)
    local ok = false
    for _, p in ipairs(W.room.walk) do
        if G.inpoly(p, x, y) then ok = true break end
    end
    if not ok then return false end
    for _, p in ipairs(W.room.blocks) do
        if G.inpoly(p, x, y) then return false end
    end
    return true
end

-- 角色站在 (x, y) 可不可以：中心和前後左右四個點都要能站
function W.can_stand(x, y)
    local r = PLAYER_R
    return free_point(x, y) and free_point(x + r, y) and free_point(x - r, y)
        and free_point(x, y + r) and free_point(x, y - r)
end

-- 會擋路的角色（主角、活著的殭屍）。由主程式每次換房間時設定
W.actors = {}
local BODY = 560   -- 兩個角色中心至少相隔多遠（公釐）

-- 從 (x, y) 走到 (nx, ny) 會不會撞到別的角色。已經貼在一起時，只要是「離開」就可以走（不然會卡住）
local function bump(self, x, y, nx, ny)
    for _, a in ipairs(W.actors) do
        if a ~= self and not a.dead then
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

local function ok(self, x, y, nx, ny)
    return W.can_stand(nx, ny) and not bump(self, x, y, nx, ny)
end

-- 從 (x, y) 往 (dx, dy) 移動。撞到東西時試著只走 x 或只走 y，
-- 貼著牆斜走時才會「滑」過去，而不是整個卡住。self：誰在走（不和自己相撞）
function W.move(x, y, dx, dy, self)
    if ok(self, x, y, x + dx, y + dy) then return x + dx, y + dy end
    if dx ~= 0 and ok(self, x, y, x + dx, y) then return x + dx, y end
    if dy ~= 0 and ok(self, x, y, x, y + dy) then return x, y + dy end
    return x, y
end

-- 兩點的距離（公釐）。整數開根號：先用浮點數算，再取整數（只用在比較遠近，不影響重播）
function W.dist(ax, ay, bx, by)
    local dx, dy = ax - bx, ay - by
    return math.floor(math.sqrt(dx * dx + dy * dy))
end

-- ============================================================
-- 門
-- ============================================================

-- 站在哪扇門前面：門的範圍（牆邊的一塊矩形）往外擴大 60 公分，角色的中心在裡面就算。
-- 角色碰不到牆（離牆至少一個半徑），所以一定要擴大，否則永遠走不進門的範圍
function W.door_at(x, y)
    local r = 600
    for _, d in ipairs(W.room.doors) do
        local p = d.p
        local x0, y0, x1, y1 = p[1], p[2], p[1], p[2]
        for i = 1, #p // 2 do
            x0 = math.min(x0, p[i * 2 - 1]); x1 = math.max(x1, p[i * 2 - 1])
            y0 = math.min(y0, p[i * 2]);     y1 = math.max(y1, p[i * 2])
        end
        if x >= x0 - r and x <= x1 + r and y >= y0 - r and y <= y1 + r then return d end
    end
    return nil
end

-- 穿過門之後站在哪裡：新房間裡「通往舊房間」的那扇門，往房間裡面走一步。
-- 回傳 x, y, 面向的角度
function W.arrival(room_id, from_id, door_id)
    local room = ROOMS[room_id]
    local door
    for _, d in ipairs(room.doors) do
        if d.to == from_id then door = d break end
    end
    if door == nil then
        for _, d in ipairs(room.doors) do
            if d.id == door_id then door = d break end
        end
    end
    if door == nil then
        return room.spawn.x, room.spawn.y, room.spawn.yaw % 360
    end
    -- 門的中心往四個方向試：走 900 公釐後站得住的那個方向就是房間裡面
    local cx, cy = G.center(door.p)
    local saved = W.room
    W.room = room                       -- can_stand 看的是 W.room，暫時換一下
    local best
    for _, dir in ipairs({ { 0, 1, 0 }, { 1, 0, 90 }, { 0, -1, 180 }, { -1, 0, 270 } }) do
        for step = 700, 1500, 200 do
            local x, y = cx + dir[1] * step, cy + dir[2] * step
            if W.can_stand(x, y) then
                best = { x, y, dir[3] }
                break
            end
        end
        if best then break end
    end
    W.room = saved
    if best then return best[1], best[2], best[3] end
    return room.spawn.x, room.spawn.y, room.spawn.yaw % 360
end
