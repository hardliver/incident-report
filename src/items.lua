-- items.lua：道具的資料、物品欄（8 格）
--
-- INV 是一個陣列，每一格 { id = 道具, n = 數量 }。
-- 手槍的 n 是「彈匣裡還有幾發」；子彈、色帶的 n 是幾個。
-- 物品欄滿了就撿不起來（早期惡靈古堡的取捨：要帶什麼出門）。

INV_SIZE = 8

ITEMS = {
    handgun = { name = "配槍", weapon = true, clip = 15,
        desc = "松脊郡警局配發的 9mm 手槍。\n今天早上才領到，說明書還在口袋裡。" },
    handgun_ammo = { name = "手槍子彈", stack = 60, ammo_for = "handgun",
        desc = "9mm 子彈。盒子上寫著「僅供訓練使用」。" },
    ink_ribbon = { name = "色帶", stack = 10,
        desc = "打字機用的色帶。\n一卷可以打一次記錄。" },
    painkillers = { name = "止痛藥", stack = 3, heal = 35,
        desc = "一般的止痛藥。標籤上的經銷商貼紙被撕掉了。" },
    bandage = { name = "繃帶", stack = 3, heal = 20,
        desc = "乾淨的繃帶。至少能把傷口包起來。" },
}

function inv_count(id)
    local n = 0
    for _, s in ipairs(INV) do
        if s.id == id then n = n + s.n end
    end
    return n
end

function inv_has(id)
    for _, s in ipairs(INV) do
        if s.id == id then return s end
    end
    return nil
end

-- 放進物品欄：能疊的先疊到同一格，疊不下才佔新的格子。
-- 回傳實際放進去幾個（物品欄滿了可能少於 n）
function inv_add(id, n)
    local def = ITEMS[id]
    local left = n
    if def.stack then
        for _, s in ipairs(INV) do
            if s.id == id and s.n < def.stack then
                local k = math.min(left, def.stack - s.n)
                s.n = s.n + k
                left = left - k
            end
        end
    end
    while left > 0 and #INV < INV_SIZE do
        local k = def.stack and math.min(left, def.stack) or left
        INV[#INV + 1] = { id = id, n = k }
        left = left - k
    end
    return n - left
end

-- 拿走 n 個（數量到 0 的格子會移除）。不夠就不拿，回傳 false
function inv_take(id, n)
    if inv_count(id) < n then return false end
    for i = #INV, 1, -1 do
        local s = INV[i]
        if s.id == id and n > 0 then
            local k = math.min(n, s.n)
            s.n = s.n - k
            n = n - k
            if s.n == 0 and not ITEMS[id].weapon then table.remove(INV, i) end
        end
    end
    return true
end

-- 換彈匣：從子彈補到滿。回傳補了幾發
function inv_reload(weapon)
    local w = inv_has(weapon)
    if w == nil then return 0 end
    local need = ITEMS[weapon].clip - w.n
    local have = inv_count(weapon .. "_ammo")
    local k = math.min(need, have)
    if k > 0 then
        inv_take(weapon .. "_ammo", k)
        w.n = w.n + k
    end
    return k
end
