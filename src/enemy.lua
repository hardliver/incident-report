-- enemy.lua：殭屍
--
-- 每個房間的殭屍寫在 hotspots.lua 的 ENEMIES。殺掉的會記在 FLAGS（"dead_" .. id），
-- 屍體留在原地（早期惡靈古堡也是這樣：回到房間還看得到自己打倒的殭屍）。
--
-- 狀態：
--   feed   跪在地上啃食（序章第一隻）。主角靠近或開槍才會站起來
--   rise   站起來、轉頭
--   idle   站著，主角進入視線就走過來
--   walk   拖著腳走向主角，邊走邊轉向
--   grab   撲抓：撲到一半時主角還在面前就咬下去
--   hurt   中彈後往後踉蹌
--   down   倒下
--   dead   屍體

E = { list = {} }

local SPEED = 7          -- 走路速度（公釐／幀）：比主角走路慢很多
local TURN = 2           -- 轉向速度（度／幀）
local SIGHT = 9000       -- 看得到主角的距離
local REACH = 760        -- 撲抓距離

local function set(e, st, anim)
    e.state = st
    e.timer = 0
    if anim then A.play(e, anim, e.fps) end
end

-- 進入房間時呼叫：依照 ENEMIES 建立這個房間的殭屍
function E.spawn(room_id)
    E.list = {}
    for _, d in ipairs(ENEMIES[room_id] or {}) do
        local e = A.new(d.chr, d.x, d.y, d.yaw)
        e.id = d.id
        e.hp = d.hp or 60
        if FLAGS["dead_" .. d.id] then
            e.dead = true
            e.state = "dead"
            A.play(e, "down", 60, true)   -- 一開始就是最後一格（倒在地上）
            e.t = 600
        else
            e.fps = d.state == "feed" and 3 or 4
            set(e, d.state or "idle", d.state == "feed" and "feed" or "idle")
        end
        E.list[#E.list + 1] = e
    end
end

-- 被子彈打中
function E.hit(e, dmg)
    if e.dead then return end
    e.hp = e.hp - dmg
    if e.hp <= 0 then
        e.dead = true
        FLAGS["dead_" .. e.id] = true
        e.state = "down"
        e.timer = 0
        A.play(e, "down", 10, true)
    else
        e.alerted = true
        set(e, "hurt", "hurt")
    end
end

local function face_player(e, p)
    local dx, dy = p.x - e.x, p.y - e.y
    return G.yaw_to(dx, dy), W.dist(e.x, e.y, p.x, p.y)
end

-- 每一幀。p = 主角；回傳要對主角造成的傷害（0 = 沒有）
function E.update(e, p)
    e.t = e.t + 1
    e.timer = e.timer + 1
    local st = e.state
    if st == "dead" then
        return 0
    end
    if st == "down" then
        -- 6 格動畫播完就停在最後一格
        if e.timer >= 6 * 60 // e.fps then e.state = "dead" end   -- 動畫停在最後一格（A.play 的 once）
        return 0
    end
    local want, dist = face_player(e, p)
    if p.dead then
        if st ~= "idle" then set(e, "idle", "idle") end
        return 0
    end
    if st == "feed" then
        if dist < 2200 or e.alerted then
            set(e, "rise", "idle")
        end
    elseif st == "rise" then
        -- 站起來之後慢慢轉過來看著主角：這一秒是給玩家反應的時間
        e.yaw = G.turn_toward(e.yaw, want, 3)
        if e.timer > 50 then set(e, "walk", "walk") end
    elseif st == "idle" then
        if dist < SIGHT or e.alerted then set(e, "walk", "walk") end
    elseif st == "walk" then
        e.yaw = G.turn_toward(e.yaw, want, TURN)
        local dx = G.sin(e.yaw) * SPEED // 4096
        local dy = G.cos(e.yaw) * SPEED // 4096
        W.move(e, dx, dy)
        if dist < REACH and G.angle_diff(e.yaw, want) < 35 and p.state ~= "hurt" and (e.cool or 0) == 0 then
            e.fps = 6
            set(e, "grab", "grab")
        end
    elseif st == "grab" then
        -- 撲過去（4 格 × 10 幀）：第 26 幀判定有沒有咬到
        if e.timer == 26 and dist < REACH + 200 and p.state ~= "hurt" then
            return 18 + rnd(9)          -- 18–26
        end
        if e.timer >= 40 then
            e.fps = 4
            set(e, "walk", "walk")
            e.cool = 60                 -- 剛咬過：之後一秒不會再撲
        end
    elseif st == "hurt" then
        -- 往後退一點（被子彈的衝擊推開）
        local dx = -G.sin(e.yaw) * 6 // 4096
        local dy = -G.cos(e.yaw) * 6 // 4096
        W.move(e, dx, dy)
        if e.timer >= 18 then
            e.fps = 4
            set(e, "walk", "walk")
        end
    end
    if e.cool and e.cool > 0 then e.cool = e.cool - 1 end
    return 0
end
