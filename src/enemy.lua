-- enemy.lua：殭屍
--
-- 每個房間的殭屍寫在 hotspots.lua 的 ENEMIES。真的死了才記在 FLAGS（"dead_" .. id），
-- 屍體和地上的一灘血留在原地（早期惡靈古堡也是這樣：回到房間還看得到自己打倒的殭屍）。
--
-- 站著的狀態：
--   feed    跪在地上啃食（序章第一隻）。主角靠近或開槍才會站起來
--   rise    站起來、轉頭
--   idle    站著，主角進入視線就走過來
--   walk    拖著腳走向主角，邊走邊轉向
--   grab    撲抓：撲到一半時主角還在面前就咬下去
--   hurt    中彈後往後踉蹌
-- 倒在地上的狀態（站著瞄準打不到，要往下瞄準）：
--   fall    倒下中（動畫播完之後依情況變成 dead、feign 或 crawl）
--   dead    真的死了：屍體，身體下面慢慢流出一灘血
--   feign   裝死：看起來和屍體一樣，但主角靠近就抓腳，或過一陣子自己爬起來
--   getup   從地上爬起來（倒下的動畫倒著播）
--   crawl   腳被打斷了：趴在地上用手爬過來
--   ankle   趴著抓住主角的腳，每隔一段時間咬一口；主角左右來回甩可以掙脫

E = { list = {} }

local SPEED = 7          -- 走路速度（公釐／幀）：比主角走路慢很多
local CRAWL = 3          -- 爬的速度
local TURN = 2           -- 轉向速度（度／幀）
local SIGHT = 9000       -- 看得到主角的距離
local REACH = 760        -- 撲抓距離
local ANKLE = 850        -- 趴著抓腳的距離

local PRONE = { fall = true, dead = true, feign = true, getup = true, crawl = true, ankle = true }

local function set(e, st, anim, fps, once)
    e.state = st
    e.timer = 0
    if anim then
        A.play(e, anim, fps or e.fps, once)
        e.t = 0
    end
    e.prone = PRONE[st] or false
end

-- 進入房間時呼叫：依照 ENEMIES 建立這個房間的殭屍
function E.spawn(room_id)
    E.list = {}
    for _, d in ipairs(ENEMIES[room_id] or {}) do
        local e = A.new(d.chr, d.x, d.y, d.yaw)
        e.id = d.id
        e.hp = d.hp or 60
        e.fps = 4
        e.timer = 0
        e.cool = 0
        -- 會不會裝死：資料有寫就照寫的，沒寫就三成機率（同一個存檔每次都一樣：rnd 的種子固定在重播裡）
        if d.feign ~= nil then e.can_feign = d.feign else e.can_feign = rnd(10) < 3 end
        if FLAGS["dead_" .. d.id] then
            e.dead = true
            set(e, "dead", "down", 60, true)
            e.t = 600                     -- 一開始就是最後一格（倒在地上）
            e.pool = 600                  -- 血已經流完了
        elseif d.state == "feed" then
            e.fps = 3
            set(e, "feed", "feed")
        elseif d.state == "crawl" then
            set(e, "crawl", "crawl", 6)
        else
            set(e, "idle", "idle")
        end
        E.list[#E.list + 1] = e
    end
end

-- 被子彈打中。low = 往下瞄準打中的（打腳：有機會把站著的殭屍打倒成爬行）
function E.hit(e, dmg, low)
    if e.dead then return end
    e.hp = e.hp - dmg
    e.alerted = true
    if e.hp <= 0 then
        if e.can_feign and not e.prone then
            -- 裝死：倒下去、看起來死了，其實還有一口氣
            e.can_feign = false
            e.hp = 25
            e.after_fall = "feign"
        else
            e.dead = true
            FLAGS["dead_" .. e.id] = true
            e.after_fall = "dead"
            e.pool = 0
        end
        if not e.prone then
            set(e, "fall", "down", 10, true)
        elseif e.dead then
            set(e, "dead")                -- 已經在地上：直接死
            e.pool = 0
        end
        return
    end
    if e.prone then return end           -- 趴著的被打中只扣血
    if low and rnd(4) == 0 then
        -- 腳被打斷：倒下來，之後用爬的
        e.after_fall = "crawl"
        set(e, "fall", "down", 10, true)
        return
    end
    set(e, "hurt", "hurt")
end

local function face_player(e, p)
    local dx, dy = p.x - e.x, p.y - e.y
    return G.yaw_to(dx, dy), W.dist(e.x, e.y, p.x, p.y)
end

local function start_walk(e)
    e.fps = 4
    e.rev = false
    set(e, "walk", "walk")
end

-- 每一幀。p = 主角。回傳兩個值：對主角造成的傷害（0 = 沒有）、"ankle"（剛抓住主角的腳）
function E.update(e, p)
    e.t = e.t + 1
    e.timer = e.timer + 1
    if e.cool > 0 then e.cool = e.cool - 1 end
    if e.pool and e.pool < 600 then e.pool = e.pool + 1 end
    local st = e.state
    if st == "dead" then return 0 end
    if st == "fall" then
        -- 倒下的 6 格動畫播完（10 fps → 36 幀）
        if e.timer >= 36 then
            local nxt = e.after_fall
            if nxt == "dead" then
                set(e, "dead")
            elseif nxt == "feign" then
                set(e, "feign")
                e.wake = 240 + rnd(300)   -- 4–9 秒後自己爬起來
            else
                set(e, "crawl", "crawl", 6)
            end
            e.prone = true
        end
        return 0
    end
    local want, dist = face_player(e, p)
    local p_free = p.state ~= "down" and p.state ~= "dead" and p.state ~= "held" and p.state ~= "hurt"

    if st == "feed" then
        if dist < 2200 or e.alerted then
            e.fps = 4
            set(e, "rise", "idle")
        end
    elseif st == "rise" then
        -- 站起來之後慢慢轉過來看著主角：這一秒是給玩家反應的時間
        e.yaw = G.turn_toward(e.yaw, want, 3)
        if e.timer > 50 then start_walk(e) end
    elseif st == "idle" then
        if dist < SIGHT or e.alerted then start_walk(e) end
    elseif st == "walk" then
        e.yaw = G.turn_toward(e.yaw, want, TURN)
        W.move(e, G.sin(e.yaw) * SPEED // 4096, G.cos(e.yaw) * SPEED // 4096)
        if dist < REACH and G.angle_diff(e.yaw, want) < 35 and p_free and e.cool == 0 then
            e.fps = 6
            set(e, "grab", "grab")
        end
    elseif st == "grab" then
        -- 撲過去（4 格 × 10 幀）：第 26 幀判定有沒有咬到
        if e.timer == 26 and dist < REACH + 200 and p_free then
            e.cool = 60
            return 18 + rnd(9)          -- 18–26
        end
        if e.timer >= 40 then
            e.cool = 60                 -- 剛撲過：之後一秒不會再撲
            start_walk(e)
        end
    elseif st == "hurt" then
        -- 往後退一點（被子彈的衝擊推開）
        W.move(e, -G.sin(e.yaw) * 6 // 4096, -G.cos(e.yaw) * 6 // 4096)
        if e.timer >= 18 then start_walk(e) end
    elseif st == "feign" then
        -- 裝死：主角走到旁邊就突然抓腳；不然時間到了自己爬起來
        if dist < ANKLE and p_free and e.cool == 0 then
            e.yaw = want
            set(e, "ankle", "reach", 4)
            return 0, "ankle"
        end
        if e.timer >= e.wake then set(e, "getup", "down", 8, true) e.rev = true end
    elseif st == "getup" then
        if e.timer >= 45 then
            e.rev = false
            start_walk(e)
        end
    elseif st == "crawl" then
        e.yaw = G.turn_toward(e.yaw, want, 1)
        W.move(e, G.sin(e.yaw) * CRAWL // 4096, G.cos(e.yaw) * CRAWL // 4096)
        if dist < ANKLE and p_free and e.cool == 0 and G.angle_diff(e.yaw, want) < 40 then
            set(e, "ankle", "reach", 4)
            return 0, "ankle"
        end
    elseif st == "ankle" then
        -- 抓著腳：每 70 幀咬一口（主角掙脫了就放手）
        if p.state ~= "held" then
            e.cool = 120
            set(e, "crawl", "crawl", 6)
        elseif e.timer % 70 == 50 then
            return 10 + rnd(6)
        end
    end
    return 0
end

-- 殭屍被主角甩開
function E.release(e)
    if e.state == "ankle" then
        e.cool = 180                      -- 被甩開之後三秒內不會再抓
        set(e, "crawl", "crawl", 6)
        W.move(e, -G.sin(e.yaw) * 300 // 4096, -G.cos(e.yaw) * 300 // 4096)
    end
end
