-- player.lua：柯爾的操作、狀態、開槍
--
-- 操作（坦克式）：
--   上：往前走　下：後退　左右：轉身　按住 B＋上：跑
--   X：按一下開始跑，再按一下變回走路；方向鍵全部放開也會變回走路
--     （下次再按方向鍵是走路，要跑再按一次 X）
--   按住 L：舉槍瞄準（自動轉向最近的殭屍），瞄準時按 R 開槍、左右微調方向、
--     按住下＝往地上瞄準（打趴在地上的殭屍、打腳），按住上＝往上瞄準（打頭，比較容易打中要害）
--     （和新版惡靈古堡一樣；鍵盤是 Q 舉槍、E 開槍）
--   沒有肩鍵的手把（紅白機）：按住 B（不按上）舉槍，A 開槍
--
-- 體力 100，狀態分三階段（不用數字顯示，物品欄裡看立繪）：
--   良好 60 以上　負傷 25–59　危急 24 以下：按著傷口、走得慢、不能跑

P = {}

local LEFT, RIGHT, UP, DOWN, BA, BB, BX, BL, BR = 0, 1, 2, 3, 4, 5, 8, 10, 11
local SHAKE = 10             -- 被抓住腳時，左右來回甩幾次才掙脫
local WALK, RUN, BACK, LIMP = 24, 52, 14, 15
local TURN, AIM_TURN = 4, 3
local FIRE_COOL = 22         -- 兩發之間至少隔幾幀
local RELOAD_TIME = 54       -- 換彈匣幾幀

P.fx = {}                    -- 畫面上的特效（血花、槍口火光）
P.hint = nil                 -- 畫面上方的小提示（例如「沒有子彈」），不會暫停遊戲
P.hint_t = 0

function P.new()
    local p = A.new("cole", 0, 0, 0)
    p.hp = 100
    p.aim_lv = 0
    p.state = "free"
    p.timer = 0
    p.cool = 0
    return p
end

function P.status(p)
    if p.hp >= 60 then return "fine" end
    if p.hp >= 25 then return "caution" end
    return "danger"
end

local function set(p, st)
    p.state = st
    p.timer = 0
end

local function show_hint(s)
    P.hint = s
    P.hint_t = 90
end

-- 被趴在地上的殭屍抓住腳
function P.hold(p, e)
    if p.state == "down" or p.state == "dead" then return end
    set(p, "held")
    p.holder = e
    p.shake = 0
    p.last_dir = nil
    A.play(p, "struggle", 4)
    show_hint("被抓住腳了！左右來回甩開它！")
end

-- 抓著腳的殭屍咬下去：只扣體力，不會被推開（腳還被抓著）
function P.bite(p, dmg)
    p.hp = p.hp - dmg
    if p.scr then P.blood(p.scr.x, p.scr.y - 20 * p.scr.scale // 256, 8) end
    if p.hp <= 0 then
        p.hp = 0
        E.release(p.holder)
        set(p, "down")
        A.play(p, "down", 10, true)
    end
end

-- 被咬：扣體力、往後退、硬直一下。體力歸零就倒下
function P.damage(p, dmg, from)
    if p.state == "down" or p.state == "dead" then return end
    p.hp = p.hp - dmg
    p.push_x = G.sin(from.yaw) * 10 // 4096    -- 往殭屍面向的方向被推開
    p.push_y = G.cos(from.yaw) * 10 // 4096
    if p.hp <= 0 then
        p.hp = 0
        set(p, "down")
        A.play(p, "down", 10, true)
    else
        set(p, "hurt")
        A.play(p, "hurt")
    end
    -- 血花
    if p.scr then P.blood(p.scr.x, p.scr.y - 70 * p.scr.scale // 256, 10) end
end

-- 在畫面 (x, y) 噴 n 點血（只是畫面效果，不影響遊戲）
function P.blood(x, y, n)
    for _ = 1, n do
        P.fx[#P.fx + 1] = { x = x * 16, y = y * 16, vx = rnd(49) - 24, vy = -rnd(32) - 8, life = 14 + rnd(10), c = 8 }
    end
end

-- 瞄準時自動轉向最近的殭屍（前方左右 50° 以內、14 公尺以內）。
-- 最近的是趴在地上的，就自動往下瞄準
local function auto_aim(p)
    local best, best_d, prone = nil, 14000, false
    for _, e in ipairs(E.list) do
        if not e.dead then
            local want = G.yaw_to(e.x - p.x, e.y - p.y)
            local d = W.dist(p.x, p.y, e.x, e.y)
            if G.angle_diff(want, p.yaw) <= 50 and d < best_d then best, best_d, prone = want, d, e.prone end
        end
    end
    if best then p.yaw = best end
    p.auto_low = prone
end

-- 開一槍：打中槍口方向左右 10° 以內最近的殭屍
local function fire(p)
    local gun = inv_has("handgun")
    if gun.n == 0 then
        if inv_count("handgun_ammo") > 0 then
            set(p, "reload")
            A.play(p, "idle")
        else
            show_hint("沒有子彈了。")
            p.cool = FIRE_COOL
        end
        return
    end
    gun.n = gun.n - 1
    p.cool = FIRE_COOL
    p.flash = 3
    A.play(p, p.aim_lv < 0 and "shoot_down" or "shoot", 12, true)
    p.t = 0
    -- 打得到誰：往下瞄準＝地上的、和站著的腳；平舉或往上＝只有站著的（子彈從趴著的殭屍頭上飛過去）
    local target, best = nil, 15000
    for _, e in ipairs(E.list) do
        e.alerted = true              -- 槍聲：整個房間的殭屍都會過來
        if not e.dead and (p.aim_lv < 0 or not e.prone) then
            local want = G.yaw_to(e.x - p.x, e.y - p.y)
            local d = W.dist(p.x, p.y, e.x, e.y)
            if G.angle_diff(want, p.yaw) <= 10 and d < best then target, best = e, d end
        end
    end
    if target then
        local dmg = 9 + rnd(6)                     -- 9–14
        local crit = p.aim_lv > 0 and 5 or 12      -- 往上瞄準（頭）比較容易打中要害
        if rnd(crit) == 0 then dmg = dmg * 4 end
        E.hit(target, dmg, p.aim_lv < 0)
        if target.scr then
            local h = target.prone and 15 or (p.aim_lv < 0 and 40 or 80)
            P.blood(target.scr.x, target.scr.y - h * target.scr.scale // 256, dmg > 20 and 16 or 7)
        end
    end
end

-- 每一幀。回傳 "act"：按了 A（調查／開門，由主程式處理）
function P.update(p)
    p.t = p.t + 1
    p.timer = p.timer + 1
    if p.cool > 0 then p.cool = p.cool - 1 end
    if p.flash and p.flash > 0 then p.flash = p.flash - 1 end
    if P.hint_t > 0 then P.hint_t = P.hint_t - 1 end

    local st = p.state
    if st == "down" then
        if p.timer > 120 then set(p, "dead") end
        return nil
    elseif st == "dead" then
        return nil
    elseif st == "hurt" then
        W.move(p, p.push_x, p.push_y)
        if p.timer >= 36 then set(p, "free") end
        return nil
    elseif st == "reload" then
        if p.timer >= RELOAD_TIME then
            inv_reload("handgun")
            set(p, "free")
        end
        return nil
    elseif st == "held" then
        -- 腳被抓住：左、右輪流按（同一邊連按不算）
        local dir = U.pressed(LEFT) and 0 or (U.pressed(RIGHT) and 1 or nil)
        if dir ~= nil and dir ~= p.last_dir then
            p.shake = p.shake + 1
            p.last_dir = dir
            p.t = p.t + 8             -- 甩腳的動畫跟著動
        end
        if p.shake >= SHAKE then
            E.release(p.holder)
            p.holder = nil
            set(p, "free")
            P.hint_t = 0
        end
        return nil
    end

    -- X：跑步開關。方向鍵全部放開（停下來）就自動變回走路
    if U.pressed(BX) then p.running = not p.running end
    if not (U.held(UP) or U.held(DOWN) or U.held(LEFT) or U.held(RIGHT)) then p.running = false end

    local has_gun = inv_has("handgun") ~= nil
    local danger = P.status(p) == "danger"
    local aim_btn = U.held(BL) or (U.held(BB) and (st == "aim" or not U.held(UP)))

    if has_gun and aim_btn then
        if st ~= "aim" then
            set(p, "aim")
            auto_aim(p)
        end
        if U.held(LEFT) then p.yaw = (p.yaw - AIM_TURN) % 360 end
        if U.held(RIGHT) then p.yaw = (p.yaw + AIM_TURN) % 360 end
        -- 瞄準的高度：按住下＝往下，按住上＝往上，都沒按＝平舉（自動瞄準到趴著的殭屍時是往下）
        if U.held(DOWN) then p.aim_lv = -1
        elseif U.held(UP) and U.held(BL) then p.aim_lv = 1
        elseif p.auto_low then p.aim_lv = -1
        else p.aim_lv = 0 end
        if U.held(UP) then p.auto_low = false end
        if (U.pressed(BR) or U.pressed(BA)) and p.cool == 0 then fire(p) end
        if (p.anim ~= "shoot" and p.anim ~= "shoot_down") or p.t > 12 then
            A.play(p, p.aim_lv < 0 and "aim_down" or "aim")
        end
        return nil
    end
    if st == "aim" then set(p, "free") end

    local speed = 0
    if U.held(LEFT) then p.yaw = (p.yaw - TURN) % 360 end
    if U.held(RIGHT) then p.yaw = (p.yaw + TURN) % 360 end
    if U.held(UP) then
        if danger then speed = LIMP
        elseif U.held(BB) or p.running then speed = RUN
        else speed = WALK end
    elseif U.held(DOWN) then
        speed = -BACK
    end
    if speed ~= 0 then
        local dx = G.sin(p.yaw) * speed // 4096
        local dy = G.cos(p.yaw) * speed // 4096
        W.move(p, dx, dy)
        if speed == RUN then A.play(p, "run", 12)
        elseif danger then A.play(p, "limp", 8)
        else A.play(p, "walk", speed < 0 and 6 or 10) end
    else
        A.play(p, danger and "hurt" or "idle")
    end
    if U.pressed(BA) then return "act" end
    return nil
end

-- 特效：每幀移動、變短，最後消失
function P.update_fx()
    for i = #P.fx, 1, -1 do
        local f = P.fx[i]
        f.x = f.x + f.vx
        f.y = f.y + f.vy
        f.vy = f.vy + 4               -- 重力
        f.life = f.life - 1
        if f.life <= 0 then table.remove(P.fx, i) end
    end
end

function P.draw_fx(p)
    for _, f in ipairs(P.fx) do
        rect(f.x // 16, f.y // 16, 2, 2, f.c)
    end
    -- 槍口火光：角色面前、胸口高度的一團黃白色
    if p.flash and p.flash > 0 and p.scr then
        local s = p.scr
        local gx, gy = W.project(p.x + G.sin(p.yaw) * 650 // 4096, p.y + G.cos(p.yaw) * 650 // 4096, p.z + 1350)
        if gx then
            -- 十字形的小火光：大小跟著角色的遠近，最多 5 像素
            local r = G.clamp(3 * s.scale // 256, 1, 5)
            rect(gx - r, gy, r * 2 + 1, 1, 10)
            rect(gx, gy - r, 1, r * 2 + 1, 10)
            rect(gx - 1, gy - 1, 3, 3, 7)
        end
    end
    if P.hint_t > 0 then
        local w = textw(P.hint)
        U.box((SCREEN_W - w) // 2 - 8, 8, w + 16, 24)
        text(P.hint, (SCREEN_W - w) // 2, 13, 7)
    end
end
