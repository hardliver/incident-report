-- main.lua：遊戲的主流程
--
-- 狀態（state）：
--   "title"   標題畫面
--   "report"  事故報告的開頭（黑底白字）
--   "play"    操作柯爾
--   "door"    開門轉場動畫（同時換房間）
--   "save"    打字機的特寫（選存檔欄位）
--
-- 操作（坦克式，和早期惡靈古堡一樣：方向是「相對角色」的，不是相對畫面）：
--   上：往前走　下：後退　左右：原地轉身　按住 B：跑　A：調查／開門
--   Select：顯示除錯資訊（房間、鏡頭、座標）

local LEFT, RIGHT, UP, DOWN = 0, 1, 2, 3
local BA, BB, START, SELECT = 4, 5, 6, 7

local state = "title"
local t = 0                -- 目前狀態經過幾幀
local player
local debug = false

-- 會存進存檔的東西（全域：hotspots.lua 也會用）
FLAGS = {}                 -- 劇情旗標，例如 FLAGS.prologue_lock = true
INV = {}                   -- 持有的東西：INV.ink_ribbon = 3
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

-- 速度（公釐／幀）與轉身速度（度／幀）
local WALK, RUN, BACK, TURN = 24, 52, 14, 4

local function set_state(s)
    state = s
    t = 0
end

-- ============================================================
-- 換房間
-- ============================================================

local door_anim = nil    -- 開門動畫進行中：{ kind, to, from, door, frame }

local function enter_room(id, x, y, yaw)
    player.x, player.y, player.yaw = x, y, yaw
    W.load(id, x, y)
    A.play(player, "idle")
end

-- 試著開門。不能走的門顯示訊息
local function try_door(d)
    if d.to == "_locked" then
        if not FLAGS.front_locked_seen then
            FLAGS.front_locked_seen = true
            U.say("門從外面被鎖住了。", "門把下方的鎖孔不是鑰匙孔，\n是四個圓形的凹槽，排成一個菱形。")
        else
            U.say("門鎖著。四個圓形的凹槽。")
        end
        return
    end
    if ROOMS[d.to] == nil then
        U.say("（這扇門後面的部分還沒有做好。）")
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
    INV.ink_ribbon = INV.ink_ribbon - 1
    save(i, {
        room = W.id, x = player.x, y = player.y, yaw = player.yaw,
        flags = FLAGS, inv = INV, time = playtime, saves = save_count,
    })
end

local function load_save(i)
    local s = loadsave(i)
    if s == nil then return false end
    FLAGS = s.flags or {}
    INV = s.inv or {}
    playtime = s.time or 0
    save_count = s.saves or 0
    enter_room(s.room, s.x, s.y, s.yaw)
    set_state("play")
    return true
end

-- 打字機：先問要不要用色帶，再到特寫畫面選欄位
local function use_typewriter()
    local n = INV.ink_ribbon or 0
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
                U.say(string.format("……記錄完成。色帶還剩 %d 卷。", INV.ink_ribbon))
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
        U.say("物流箱。蓋子上印著「常青生活　安心配送」。", "（物流箱之後才會開放。）")
    elseif h.kind == "pickup" then
        INV[h.give] = (INV[h.give] or 0) + h.count
        FLAGS[h.flag] = true
        U.say(h.text, string.format("拿到了色帶 ×%d。", h.count))
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

    local p = player
    local moving, speed = false, 0
    if U.held(LEFT) then p.yaw = (p.yaw - TURN) % 360 end
    if U.held(RIGHT) then p.yaw = (p.yaw + TURN) % 360 end
    if U.held(UP) then
        speed = U.held(BB) and RUN or WALK
        moving = true
    elseif U.held(DOWN) then
        speed = -BACK
        moving = true
    end
    if moving then
        local dx = G.sin(p.yaw) * speed // 4096
        local dy = G.cos(p.yaw) * speed // 4096
        p.x, p.y = W.move(p.x, p.y, dx, dy)
        if speed == RUN then
            A.play(p, "run", 12)
        else
            A.play(p, "walk", speed < 0 and 6 or 10)
        end
    else
        A.play(p, "idle")
    end
    p.t = p.t + 1

    W.update_camera(p.x, p.y)

    if U.pressed(BA) then
        -- 先看面前有沒有東西可以調查，沒有才看是不是站在門前
        local h = find_hotspot(W.id, p.x, p.y, p.yaw)
        if h then
            use_hotspot(h)
        else
            local d = W.door_at(p.x, p.y)
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
        local x, y, yaw = W.arrival(a.to, a.from, a.door)
        enter_room(a.to, x, y, yaw)
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
    player = A.new("cole", 0, 0, 0)
end

local REPORT = {
    "事故報告　編號 0417",
    "撰寫人：副警長　柯爾．哈特利",
    "地點：永春莊園（常青生活股份有限公司 招待所）",
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
                enter_room(DEV_START.room, DEV_START.x, DEV_START.y, DEV_START.yaw)
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
    elseif state == "door" then
        update_door()
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

    bg()
    A.draw_all({ player })
    U.draw()

    if debug then
        local s = player.scr
        text(string.format("%s / %s", W.id, W.cam_id), 4, 4, 10)
        text(string.format("x %d  y %d  yaw %d", player.x, player.y, player.yaw), 4, 20, 10)
        if s then text(string.format("depth %d cm  scale %d", s.depth, s.scale), 4, 36, 10) end
    end
end
