-- invui.lua：物品欄畫面（按 Start 打開）
--
-- 左邊：柯爾的立繪（良好／負傷／危急三種）和狀態。右邊：8 格道具，下面是指令。
-- 方向鍵選格子 → A 叫出指令（使用、檢查）→ A 執行。B 返回，Start 關閉。
-- 「檢查」會切到全黑的畫面，道具在中間慢慢轉（道具自己的 128 色，借用背景的 128–255）。

IU = { sel = 1, mode = "slots", cmd = 1, t = 0 }

local LAY = INV_LAYOUT
local CMDS = { "使用", "檢查", "組合", "返回" }
local STATUS_TEXT = { fine = "良好", caution = "負傷", danger = "危急" }
local STATUS_COLOR = { fine = 11, caution = 10, danger = 8 }
local icons, ui, turn

function IU.open()
    icons = icons or sprload("icons")
    ui = ui or sprload("ui")
    IU.mode = "slots"
    IU.msg = nil
    IU.t = 0
    if IU.sel > INV_SIZE then IU.sel = 1 end
    paltint(16, 112, 256, 256, 256)    -- 物品欄不受房間光線影響
    bgload("scr.inventory_bg")
end

-- 使用道具。回傳要顯示的訊息
local function use(p, slot)
    local def = ITEMS[slot.id]
    if def.heal then
        if p.hp >= 100 then return "現在不需要。" end
        p.hp = math.min(100, p.hp + def.heal)
        inv_take(slot.id, 1)
        return def.name .. "。好多了。"
    elseif def.ammo_for then
        if not inv_has(def.ammo_for) then return "沒有可以用這個的東西。" end
        local k = inv_reload(def.ammo_for)
        if k == 0 then return "彈匣已經是滿的。" end
        return string.format("裝填了 %d 發。", k)
    elseif def.weapon then
        return "已經拿在手上了。"
    end
    return "現在用不到。"
end

-- 回傳 true = 關閉物品欄
function IU.update(p)
    IU.t = IU.t + 1
    if IU.mode == "inspect" then
        if U.pressed(4) or U.pressed(5) or U.pressed(6) then
            IU.mode = "slots"
            sprfree(turn)
            turn = nil
            bgload("scr.inventory_bg")   -- 背景的顏色被道具借走了，重新載入
        end
        return false
    end
    if U.pressed(6) then return true end
    if IU.mode == "slots" then
        local s = IU.sel
        if U.pressed(0) and (s - 1) % 4 > 0 then s = s - 1 end
        if U.pressed(1) and (s - 1) % 4 < 3 then s = s + 1 end
        if U.pressed(2) and s > 4 then s = s - 4 end
        if U.pressed(3) and s <= 4 then s = s + 4 end
        if s ~= IU.sel then IU.msg = nil end
        IU.sel = s
        if U.pressed(5) then return true end
        if U.pressed(4) and INV[s] then
            IU.mode = "cmd"
            IU.cmd = 1
        end
    elseif IU.mode == "cmd" then
        if U.pressed(0) and IU.cmd > 1 then IU.cmd = IU.cmd - 1 end
        if U.pressed(1) and IU.cmd < #CMDS then IU.cmd = IU.cmd + 1 end
        if U.pressed(5) then IU.mode = "slots" end
        if U.pressed(4) then
            local slot = INV[IU.sel]
            local c = CMDS[IU.cmd]
            IU.mode = "slots"
            if c == "使用" then
                IU.msg = use(p, slot)
            elseif c == "檢查" then
                local name = "item." .. slot.id
                if pakhas(name) then
                    IU.mode = "inspect"
                    IU.t = 0
                    turn = sprload(name)
                    palload(name .. ".pal")
                else
                    IU.msg = ITEMS[slot.id].desc
                end
            elseif c == "組合" then
                IU.msg = "（組合之後才會開放。）"
            end
        end
    end
    return false
end

local function draw_desc(s)
    local d = LAY.description
    text(s, d[1] + 6, d[2] + 6, 7)
end

function IU.draw(p)
    if IU.mode == "inspect" then
        cls(0)
        local slot = INV[IU.sel]
        local def = ITEMS[slot.id]
        -- 12 格轉一圈，每 8 幀換一格；放大兩倍（96 → 192）
        sprdraw(turn, (IU.t // 8) % sprcount(turn), 160, 100, 512)
        local w = textw(def.name)
        text(def.name, (SCREEN_W - w) // 2, 8, 7)
        U.box(6, 192, 308, 42)
        text(def.desc, 14, 198, 7)
        return
    end
    bg()
    local st = P.status(p)
    local pr = LAY.portrait
    sprdraw(ui, UI["status_cole_" .. st], pr[1], pr[2])
    local stt = LAY.status_text
    text(STATUS_TEXT[st], stt[1] + 6, stt[2] + 3, STATUS_COLOR[st])
    for i, pos in ipairs(LAY.slots) do
        local slot = INV[i]
        if slot then
            sprdraw(icons, ICON[slot.id], pos[1], pos[2])
            if ITEMS[slot.id].stack or ITEMS[slot.id].weapon then
                local s = tostring(slot.n)
                text(s, pos[1] + 34 - textw(s), pos[2] + 22, 7)
            end
        end
        if i == IU.sel then
            -- 選到的格子：外框（每 30 幀閃一下）
            local c = (IU.t // 15) % 2 == 0 and 10 or 9
            local x, y, z = pos[1] - 4, pos[2] - 4, LAY.slot_size + 8
            rect(x, y, z, 1, c); rect(x, y + z - 1, z, 1, c)
            rect(x, y, 1, z, c); rect(x + z - 1, y, 1, z, c)
        end
    end
    for i, b in ipairs(LAY.commands) do
        local on = IU.mode == "cmd" and i == IU.cmd
        local s = CMDS[i]
        text(s, b[1] + (b[3] - textw(s)) // 2, b[2] + 1, on and 10 or 5)
    end
    local slot = INV[IU.sel]
    if IU.msg then
        draw_desc(IU.msg)
    elseif slot then
        draw_desc(ITEMS[slot.id].name)
    end
end
