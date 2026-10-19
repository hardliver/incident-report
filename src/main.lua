-- main.lua：遊戲的主流程
--
-- 狀態（state）：
--   "title"   標題畫面
--   "report"  事故報告的開頭（黑底白字）
--   "play"    操作柯爾
--   "door"    開門轉場動畫（同時換房間）
--   "save"    打字機的特寫（選存檔欄位）
--   "inv"     物品欄
--   "over"    柯爾倒下（遊戲結束）
--
-- 操作見 player.lua。A：調查／開門　Start：物品欄　Select：除錯資訊

local BA, START, SELECT = 4, 6, 7

local state = "title"
local t = 0                -- 目前狀態經過幾幀
local player
local debug = false

-- 會存進存檔的東西（全域：hotspots.lua 也會用）
FLAGS = {}                 -- 劇情旗標，例如 FLAGS.prologue_lock = true
INV = {}                   -- 物品欄（見 items.lua）
local playtime = 0         -- 遊戲時間（幀）
local save_count = 0       -- 存了幾次（結局評價用）
local SLOTS = 3            -- 存檔欄位 1–3

-- 門的種類（開門動畫）：沒列出來的是單開木門
local DOOR_KIND = {
    ["exterior.front"] = "wood_double",
    ["foyer.front"] = "wood_double",
    ["dining.east"] = "wood_double",
    ["foyer.west"] = "wood_double",
    ["kitchen.freezer"] = "metal",
    ["freezer.east"] = "metal",
    ["pool.machine"] = "metal",
    ["pool_machine.south"] = "metal",
}

local function set_state(s)
    state = s
    t = 0
end

-- ============================================================
-- 換房間
-- ============================================================

local door_anim = nil    -- 開門動畫進行中：{ kind, to, from, door, frame }

local function enter_room(id, x, y, yaw, z)
    player.x, player.y, player.yaw = x, y, yaw
    W.load(id, x, y, z or 0)
    player.z, player.lv = W.ground(x, y, z or 0)
    player.z = player.z or 0
    E.spawn(id)
    -- 會擋路的角色：主角＋這個房間的殭屍
    W.actors = { player }
    for _, e in ipairs(E.list) do W.actors[#W.actors + 1] = e end
    P.fx = {}
    A.play(player, "idle")
end

-- 新遊戲：所有狀態回到開頭
local function new_game()
    FLAGS = {}
    INV = {}
    inv_add("handgun", 1)
    inv_has("handgun").n = 15          -- 彈匣是滿的
    playtime = 0
    save_count = 0
    player = P.new()
end

-- 試著開門。不能走的門顯示訊息
local function try_door(d)
    local key = W.id .. "." .. d.id
    if key == "foyer.front" then
        if not FLAGS.front_locked_seen then
            FLAGS.front_locked_seen = true
            U.say("門從外面被鎖住了。", "門把下方的鎖孔不是鑰匙孔，\n是四個圓形的凹槽，排成一個菱形。")
        else
            U.say("門鎖著。四個圓形的凹槽。")
        end
        return
    end
    if d.to == "_locked" then
        -- 有寫特別說明的門（hotspots.lua 的 LOCKED_TEXT）就用那一段，否則就是一般的「鎖著」
        U.say(LOCKED_TEXT[key] or "門鎖著。")
        return
    end
    if ROOMS[d.to] == nil then
        -- 還沒做好的房間：在遊戲裡也是一扇打不開的門
        U.say("門的另一邊好像被什麼東西頂住了，打不開。")
        return
    end
    local kind = DOOR_KIND[W.id .. "." .. d.id] or "wood_single"
    door_anim = { kind = kind, to = d.to, from = W.id, door = d.id, info = DOORANIM[kind] }
    set_state("door")
end

-- ============================================================
-- 存檔：打字機＋色帶
-- ============================================================
-- 每次存檔用掉一卷色帶。存檔的內容：在哪裡、劇情旗標、持有的東西、時間、存了幾次

local function fmt_time(frames)
    local m = frames // 3600
    return string.format("%d:%02d", m // 60, m % 60)
end

-- 欄位的說明，例如「1  前廳　0:12　第 2 次」；空的欄位是「1  －－－」
local function slot_label(i)
    local s = loadsave(i)
    if s == nil then return string.format("%d　－－－", i) end
    return string.format("%d　%s　%s　第 %d 次", i, ROOM_NAME[s.room] or s.room, fmt_time(s.time), s.saves)
end

local function write_save(i)
    save_count = save_count + 1
    inv_take("ink_ribbon", 1)
    save(i, {
        room = W.id, x = player.x, y = player.y, z = player.z, yaw = player.yaw, hp = player.hp,
        flags = FLAGS, inv = INV, time = playtime, saves = save_count,
    })
end

local function load_save(i)
    local s = loadsave(i)
    if s == nil then return false end
    new_game()
    FLAGS = s.flags or {}
    INV = s.inv or {}
    player.hp = s.hp or 100
    playtime = s.time or 0
    save_count = s.saves or 0
    enter_room(s.room, s.x, s.y, s.yaw, s.z)
    set_state("play")
    return true
end

-- 打字機：先問要不要用色帶，再到特寫畫面選欄位
local function use_typewriter()
    local n = inv_count("ink_ribbon")
    if n == 0 then
        U.say("一台老式打字機。", "沒有色帶，什麼也打不出來。")
        return
    end
    U.choose(string.format("要用一卷色帶，把到目前為止的經過打下來嗎？\n（色帶剩 %d 卷）", n), { "打字", "不要" }, function(c)
        if c ~= 1 then return end
        set_state("save")
        bgload("scr.save_typewriter")
        local labels = {}
        for i = 1, SLOTS do labels[i] = slot_label(i) end
        U.choose("打在哪一頁？", labels, function(slot)
            if slot then
                write_save(slot)
                U.say(string.format("……記錄完成。色帶還剩 %d 卷。", inv_count("ink_ribbon")))
            end
            W.refresh()
            set_state("play")
        end)
    end)
end

-- 調查面前的東西
function use_hotspot(h)
    if h.kind == "typewriter" then
        use_typewriter()
    elseif h.kind == "itembox" then
        U.say("物流箱。蓋子上印著「長青當日到貨：全美 48 州，當日送達。」", "（物流箱之後才會開放。）")
    elseif h.kind == "pickup" then
        local name = ITEMS[h.give].name
        local got = inv_add(h.give, h.count)
        if got == 0 then
            U.say(h.text, "東西太多了，拿不下。")
            return
        end
        if got < h.count then
            -- 只拿得下一部分：剩下的留在原地，下次再來拿
            h.count = h.count - got
            U.say(h.text, string.format("拿了%s ×%d（剩下的拿不下）。", name, got))
            return
        end
        FLAGS[h.flag] = true
        U.say(h.text, string.format("拿到了%s ×%d。", name, got))
    elseif h.kind == "look" then
        U.say(table.unpack(h.text))
    end
end

-- ============================================================
-- 操作柯爾
-- ============================================================

local function update_play()
    if U.update() then return end    -- 正在看訊息：其他都暫停

    if U.pressed(SELECT) then debug = not debug end
    if U.pressed(START) and player.state == "free" then
        IU.open()
        set_state("inv")
        return
    end

    local act = P.update(player)
    for _, e in ipairs(E.list) do
        local dmg, ev = E.update(e, player)
        if ev == "ankle" then
            P.hold(player, e)
        elseif dmg > 0 then
            if e.state == "ankle" then P.bite(player, dmg) else P.damage(player, dmg, e) end
        end
    end
    P.update_fx()
    W.update_camera(player.x, player.y, player.lv)

    if player.state == "dead" then
        set_state("over")
        return
    end
    if act == "act" then
        -- 先看面前有沒有東西可以調查，沒有才看是不是站在門前
        local p = player
        local h = find_hotspot(W.id, p.x, p.y, p.yaw)
        if h then
            use_hotspot(h)
        else
            local d = W.door_at(p.x, p.y, p.z, p.yaw)
            if d then try_door(d) end
        end
    end
end

-- ============================================================
-- 開門動畫
-- ============================================================
-- 時間軸（每一格動畫 = 60 / fps 幀）：
--   第一格停 hold_start 格 → 播完全部格 → 最後一格停 hold_end 格 → 進入新房間

local function door_step()
    local a = door_anim
    local per = 60 // a.info.fps
    local tick = t // per
    local f = tick - a.info.hold_start
    if f < 0 then f = 0 end
    if f > a.info.frames - 1 then f = a.info.frames - 1 end
    return f, tick >= a.info.hold_start + a.info.frames + a.info.hold_end
end

local function update_door()
    local f, done = door_step()
    if f ~= door_anim.frame then
        door_anim.frame = f
        bgload(string.format("door.%s.%02d", door_anim.kind, f))
    end
    if done then
        local a = door_anim
        door_anim = nil
        local x, y, z, yaw = W.arrival(a.to, a.from, a.door)
        enter_room(a.to, x, y, yaw, z)
        set_state("play")
        if a.to == "foyer" and a.from == "exterior" and not FLAGS.prologue_lock then
            FLAGS.prologue_lock = true
            U.say("身後傳來「喀」的一聲。", "門自己鎖上了。")
        end
    end
end

-- ============================================================
-- 引擎呼叫的三個函式
-- ============================================================

function _init()
    palload("actors")
    U.init()
    new_game()
end

local REPORT = {
    "事故報告　編號 0417",
    "撰寫人：副警長　柯爾．哈特利",
    "地點：長青生命股份有限公司　創辦人莊園",
    "",
    "以下依時間順序記錄。",
    "本人已盡力據實陳述。",
    "有些部分，本人自己讀起來也不太相信。",
}

function _update()
    U.read_buttons()
    t = t + 1
    if state == "title" then
        if U.update() then return end
        if t > 20 and (U.pressed(START) or U.pressed(BA)) then
            local any = false
            for i = 1, SLOTS do
                if loadsave(i) then any = true end
            end
            if not any then
                set_state("report")
            else
                U.choose(nil, { "從頭開始", "繼續" }, function(c)
                    if c == 1 then
                        new_game()
                        set_state("report")
                    elseif c == 2 then
                        local labels = {}
                        for i = 1, SLOTS do labels[i] = slot_label(i) end
                        U.choose("讀取哪一頁？", labels, function(slot)
                            if slot and not load_save(slot) then U.say("這一頁是空白的。") end
                        end)
                    end
                end)
            end
        end
    elseif state == "report" then
        if t > 30 and (U.pressed(BA) or U.pressed(START)) then
            -- DEV_START：測試用（tests/ 的腳本會在遊戲檔後面加上這個設定，直接從某個房間開始）
            if DEV_START then
                player.hp = DEV_START.hp or 100
                for id, n in pairs(DEV_START.give or {}) do inv_add(id, n) end
                for k, v in pairs(DEV_START.flags or {}) do FLAGS[k] = v end
                enter_room(DEV_START.room, DEV_START.x, DEV_START.y, DEV_START.yaw, DEV_START.z)
                set_state("play")
                return
            end
            local r = ROOMS.exterior.spawn
            enter_room("exterior", r.x, r.y, r.yaw % 360)
            set_state("play")
            U.say("晚上十一點四十分。", "報案內容：「莊園的派對，有人一直在尖叫。」", "……派對的音樂停了。")
        end
    elseif state == "play" then
        playtime = playtime + 1
        update_play()
    elseif state == "save" then
        U.update()
    elseif state == "inv" then
        if IU.update(player) then
            W.refresh()
            W.apply_tint()
            set_state("play")
        end
    elseif state == "door" then
        update_door()
    elseif state == "over" then
        if t > 120 and (U.pressed(BA) or U.pressed(START)) then
            new_game()
            set_state("title")
        end
    end
end

local function draw_center(s, y, c)
    text(s, (SCREEN_W - textw(s)) // 2, y, c)
end

function _draw()
    if state == "title" then
        cls(0)
        draw_center("事 故 報 告", 92, 7)
        draw_center("INCIDENT REPORT", 112, 6)
        if U.busy() then
            U.draw()
        elseif t % 60 < 40 then
            draw_center("按 A 開始", 180, 5)
        end
        return
    end
    if state == "report" then
        cls(0)
        for i, line in ipairs(REPORT) do
            if t > i * 20 then text(line, 24, 40 + (i - 1) * 20, i <= 3 and 7 or 6) end
        end
        return
    end
    if state == "door" then
        bg()
        return
    end
    if state == "save" then
        bg()
        U.draw()
        return
    end

    if state == "inv" then
        IU.draw(player)
        return
    end
    if state == "over" then
        cls(0)
        if t > 30 then draw_center("副警長　柯爾．哈特利", 90, 7) end
        if t > 70 then draw_center("本報告於此中斷。", 116, 6) end
        if t > 120 then draw_center("按 A 回到標題", 190, 5) end
        return
    end

    bg()
    A.draw_pools(E.list)
    A.draw_all(W.actors)
    P.draw_fx(player)
    U.draw()

    if debug then
        local s = player.scr
        text(string.format("%s / %s", W.id, W.cam_id), 4, 4, 10)
        text(string.format("x %d  y %d  z %d  lv %d  yaw %d", player.x, player.y, player.z, player.lv or -1, player.yaw), 4, 20, 10)
        if s then text(string.format("depth %d cm  scale %d", s.depth, s.scale), 4, 36, 10) end
        local gun = inv_has("handgun")
        text(string.format("hp %d  %s  ammo %d+%d", player.hp, player.state, gun and gun.n or 0, inv_count("handgun_ammo")), 4, 52, 10)
        for i, e in ipairs(E.list) do
            text(string.format("%s %s hp %d", e.id, e.state, e.hp), 4, 52 + i * 16, 10)
        end
    end
end
