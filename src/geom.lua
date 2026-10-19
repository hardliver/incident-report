-- geom.lua：幾何小工具（全部用整數）
--
-- 世界座標：x 向右、y 向前、z 向上，單位公釐（mm）。地面 z = 0。
-- 角度：0–359 度，0 = 面向 +y，順時針增加（90 = 面向 +x）。

G = {}

-- sin、cos × 4096（查 gen_data.lua 的 SIN 表，不用 math.sin：各平台結果才會完全一樣）
function G.sin(a) return SIN[a % 360 + 1] end
function G.cos(a) return SIN[(a + 90) % 360 + 1] end

-- 點 (x, y) 在不在多邊形 p 裡（p = {x1, y1, x2, y2, …}）。
-- 「射線法」：從點往右畫一條線，數它穿過幾條邊；奇數次就在裡面
function G.inpoly(p, x, y)
    local inside = false
    local n = #p // 2
    local jx, jy = p[n * 2 - 1], p[n * 2]
    for i = 1, n do
        local ix, iy = p[i * 2 - 1], p[i * 2]
        if (iy > y) ~= (jy > y) then
            -- 這條邊在 y 這個高度的 x 位置；用乘法比較，避免除法的小數
            -- x < ix + (y - iy) * (jx - ix) / (jy - iy)
            local lhs = (x - ix) * (jy - iy)
            local rhs = (y - iy) * (jx - ix)
            if (jy - iy > 0 and lhs < rhs) or (jy - iy < 0 and lhs > rhs) then
                inside = not inside
            end
        end
        jx, jy = ix, iy
    end
    return inside
end

-- 多邊形的中心（各頂點平均，房間裡的矩形夠用了）
function G.center(p)
    local sx, sy, n = 0, 0, #p // 2
    for i = 1, n do
        sx = sx + p[i * 2 - 1]
        sy = sy + p[i * 2]
    end
    return sx // n, sy // n
end

-- 從 (dx, dy) 的方向算出角度（0 = +y，90 = +x），只分 8 個方向就夠的地方用
function G.angle8(dx, dy)
    -- tan(22.5°) ≈ 106 / 256：比較兩軸的大小決定落在哪一個 45° 扇形
    local ax, ay = math.abs(dx), math.abs(dy)
    local a
    if ax * 256 < ay * 106 then
        a = dy >= 0 and 0 or 180
    elseif ay * 256 < ax * 106 then
        a = dx >= 0 and 90 or 270
    elseif dx >= 0 then
        a = dy >= 0 and 45 or 135
    else
        a = dy >= 0 and 315 or 225
    end
    return a
end

function G.clamp(v, lo, hi)
    if v < lo then return lo end
    if v > hi then return hi end
    return v
end
