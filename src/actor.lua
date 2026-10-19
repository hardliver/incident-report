-- actor.lua：角色（主角、殭屍……）的狀態、動畫、畫法
--
-- 每個角色是一個表格：
--   x, y        位置（公釐）
--   yaw         面向（0–359 度，0 = +y，順時針）
--   chr         CHR 裡的名字（決定用哪一組圖、每公尺幾像素、有哪些動畫）
--   spr         sprload 回傳的編號
--   anim, t     目前的動畫、播了幾幀

A = {}

local loaded = {}   -- chr 名稱 → sprload 編號（同一種角色只載入一次）

function A.new(chr, x, y, yaw)
    if loaded[chr] == nil then loaded[chr] = sprload("chr." .. chr) end
    return { chr = chr, spr = loaded[chr], x = x, y = y, z = 0, lv = 0, yaw = yaw, anim = "idle", t = 0, fps = 10 }
end

-- 換動畫（同一個動畫不重來）。once = true：播完停在最後一格（倒下），否則一直循環
function A.play(a, anim, fps, once)
    if a.anim ~= anim then
        a.anim = anim
        a.t = 0
    end
    a.fps = fps or a.fps or 10
    a.once = once
end

-- 目前要畫第幾格：動畫在資源包裡的起點 + 方向 × 格數 + 第幾格
local function frame_of(a, dir)
    local an = CHR[a.chr].anim[a.anim] or CHR[a.chr].anim.idle
    local start, n = an[1], an[2]
    local i = a.t * a.fps // 60
    if a.once then i = math.min(i, n - 1) else i = i % n end
    if a.rev then i = n - 1 - i end          -- 倒著播（殭屍從地上爬起來＝倒下的動畫倒過來）
    return start + dir * n + i
end

-- 算出畫面上的位置、大小、深度，存在 a.scr（畫的時候、排序時用）。看不到回傳 false
function A.place(a)
    local sx, sy, depth, zf = W.project(a.x, a.y, a.z or 0)
    if sx == nil then
        a.scr = nil
        return false
    end
    a.scr = { x = sx, y = sy, depth = depth, scale = W.scale(zf, CHR[a.chr].ppm) }
    return true
end

function A.draw(a)
    local s = a.scr
    if s == nil then return end
    local dir, flip = W.view_dir(a.yaw)
    -- 深度留一點餘裕：腳邊的地板比腳的中心近一點點，不能把腳擋掉。
    -- 趴在地上的身體往鏡頭這邊延伸將近 1 公尺，餘裕要更大
    sprdraw(a.spr, frame_of(a, dir), s.x, s.y, s.scale, flip, s.depth - (a.prone and 110 or 25))
end

-- 地上的一灘血：屍體下面慢慢擴大（4 格，越來越大）。在角色之前畫（貼在地上）
local fx = nil
function A.draw_pools(list)
    fx = fx or sprload("fx")
    for _, a in ipairs(list) do
        if a.pool then
            local sx, sy, depth, zf = W.project(a.x, a.y, a.z or 0)
            if sx then
                local f = math.min(3, a.pool // 45)
                sprdraw(fx, FX.blood + f, sx, sy, W.scale(zf, 62), false, depth - 120)
            end
        end
    end
end

-- 一群角色：由遠到近畫（近的蓋住遠的）
function A.draw_all(list)
    local vis = {}
    for _, a in ipairs(list) do
        if A.place(a) then vis[#vis + 1] = a end
    end
    table.sort(vis, function(p, q) return p.scr.depth > q.scr.depth end)
    for _, a in ipairs(vis) do A.draw(a) end
end
