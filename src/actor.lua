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
    return { chr = chr, spr = loaded[chr], x = x, y = y, yaw = yaw, anim = "idle", t = 0, fps = 10 }
end

-- 換動畫（同一個動畫不重來）
function A.play(a, anim, fps)
    if a.anim ~= anim then
        a.anim = anim
        a.t = 0
    end
    a.fps = fps or 10
end

-- 目前要畫第幾格：動畫在資源包裡的起點 + 方向 × 格數 + 第幾格
local function frame_of(a, dir)
    local an = CHR[a.chr].anim[a.anim] or CHR[a.chr].anim.idle
    local start, n = an[1], an[2]
    local i = (a.t * a.fps // 60) % n
    return start + dir * n + i
end

-- 算出畫面上的位置、大小、深度，存在 a.scr（畫的時候、排序時用）。看不到回傳 false
function A.place(a)
    local sx, sy, depth, zf = W.project(a.x, a.y, 0)
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
    sprdraw(a.spr, frame_of(a, dir), s.x, s.y, s.scale, flip, s.depth)
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
