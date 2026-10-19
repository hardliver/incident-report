-- ui.lua：對話框、按鍵的「剛按下」
--
-- 訊息一次一段，畫在畫面下方的對話框裡；按 A 看下一段。
-- 有訊息的時候遊戲暫停（早期惡靈古堡也是這樣：看東西的時候殭屍不會動）

U = {
    queue = {},       -- 還沒看的訊息
    ui = nil,         -- 介面圖（sprload 編號）
}

-- 按鍵：剛按下的那一幀才算（按住不會連續觸發）
local BTN_COUNT = 12
local prev, now = {}, {}

function U.read_buttons()
    for b = 0, BTN_COUNT - 1 do
        prev[b] = now[b]
        now[b] = btn(0, b)
    end
end

function U.pressed(b) return now[b] and not prev[b] end
function U.held(b) return now[b] end

function U.init()
    U.ui = sprload("ui")
end

-- 加一段（或好幾段）訊息
function U.say(...)
    for _, s in ipairs({ ... }) do U.queue[#U.queue + 1] = s end
end

function U.busy() return #U.queue > 0 or U.menu ~= nil end

-- 選單：U.choose(標題, {選項…}, 選好之後呼叫 done(第幾個))；按 B 取消時 done(nil)。
-- 標題可以是 nil。訊息還沒看完的話，看完才出現選單
function U.choose(title, items, done, sel)
    U.menu = { title = title, items = items, done = done, sel = sel or 1 }
end

-- 有訊息或選單時：處理按鍵。回傳 true = 這一幀被佔用了（遊戲暫停）
function U.update()
    if #U.queue > 0 then
        if U.pressed(4) or U.pressed(5) then table.remove(U.queue, 1) end
        return true
    end
    local m = U.menu
    if m == nil then return false end
    if U.pressed(2) then m.sel = (m.sel - 2) % #m.items + 1 end   -- 上（到頂了就跳到最下面）
    if U.pressed(3) then m.sel = m.sel % #m.items + 1 end         -- 下
    if U.pressed(4) then
        U.menu = nil
        m.done(m.sel)
    elseif U.pressed(5) then
        U.menu = nil
        m.done(nil)
    end
    return true
end

-- 畫一個框（引擎預設的顏色，不受房間染色影響）
function U.box(x, y, w, h)
    rect(x, y, w, h, 0)
    rect(x, y, w, 1, 5)
    rect(x, y + h - 1, w, 1, 5)
    rect(x, y, 1, h, 5)
    rect(x + w - 1, y, 1, h, 5)
end

function U.draw()
    if #U.queue == 0 then
        if U.menu then U.draw_menu() end
        return
    end
    -- 對話框用引擎預設的顏色畫（0–15 號不受房間染色影響；角色的 16–127 號會被染色）
    U.box(6, 182, 308, 52)
    text(U.queue[1], 16, 190, 7)
    -- 還有下一段：右下角閃一個小三角形
    if #U.queue > 1 and frame() % 40 < 26 then
        rect(300, 228, 6, 2, 7)
        rect(301, 230, 4, 2, 7)
        rect(302, 232, 2, 2, 7)
    end
end

-- 選單：畫在畫面下方，選到的那一項前面有一個三角形
function U.draw_menu()
    local m = U.menu
    local title_lines = 0
    if m.title then
        title_lines = 1
        for _ in m.title:gmatch("\n") do title_lines = title_lines + 1 end
    end
    local h = 16 + #m.items * 18 + title_lines * 16 + (m.title and 4 or 0)
    local y = 234 - h
    U.box(6, y, 308, h)
    local ty = y + 8
    if m.title then
        text(m.title, 16, ty, 6)
        ty = ty + title_lines * 16 + 4
    end
    for i, it in ipairs(m.items) do
        local on = i == m.sel
        if on then   -- 游標：一個小三角形（字型裡沒有 ▶）
            for k = 0, 4 do rect(18 + k, ty + 3 + k, 1, 9 - k * 2, 10) end
        end
        text(it, 32, ty, on and 7 or 5)
        ty = ty + 18
    end
end
