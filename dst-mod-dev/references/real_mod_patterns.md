# 真实模组实现手法目录（摘自 100 个实装模组）

> 每个手法都来自柠版饥荒手机版内置的真实模组（标注来源模组名），可直接套用。
> 覆盖：网络同步、RPC、新动作、HUD、自定义界面、状态图、技能系统、存档、输入、相机、地形、安全加载。

## 1. 网络变量同步（客机可见的实体数据）

来源：牛牛信息面板。net 变量需在 `SetPristine` 前定义，用 `inst.GUID` 作所有者；
主机 set，客机监听 dirty 事件。

```lua
-- 主机侧（懒创建，避免重复定义）
if not inst.bihud_beefalo_netvar then
    inst.bihud_beefalo_netvar = net_entity(inst.GUID, "bihud_beefalo", "bihud_beefalo_dirty")
    inst.bihud_bell_info_netvar = net_string(inst.GUID, "bihud_bell_info", "bihud_bell_info_dirty")
    bell_client_listen(inst)   -- 注册 dirty 监听
end
```

## 2. RPC 双向通信

来源：不灵小姐正在绝赞遇险中。服务端用 `AddModRPCHandler` 注册，客机用 `SendModRPCToServer` 触发。

```lua
-- 服务端注册
AddModRPCHandler("Destiny", "DESTINY_SKILL_ECHO", function(player)
    if player:HasTag("buling") and not player.components.timer:TimerExists("destiny_echo") then
        if not player.sg:HasStateTag("busy") then
            -- 执行技能逻辑
        end
    end
end)

-- 客机/主机触发（任意地方）
SendModRPCToServer("Destiny", "DESTINY_SKILL_ECHO", player)
```

技巧：用 `player.sg:HasStateTag("busy")` 判断玩家是否处于可操作状态，是防连发的常见做法。

## 3. 新增动作（完整三件套：定义 + 触发条件 + fn）

来源：不灵小姐正在绝赞遇险中。

```lua
-- ① 定义动作（可带 fn，act 为 BufferedAction，含 doer/target/invobject/GetActionPoint()）
W_FISHING = AddAction("W_FISHING", "捞鱼", function(act)
    local owner = act.doer
    local target = act.target
    local inst = act.invobject
    if not owner then return false end
    -- ...执行逻辑...
    return true
end)

-- ② 挂触发条件：AddComponentAction 在指定组件/槽位条件下把动作加入候选列表
AddComponentAction("EQUIPPED", "equippable", function(inst, doer, target, actions, right)
    if right and doer ~= nil and doer:HasTag("player")
        and inst.prefab == "lighter" and target ~= nil
        and (target.prefab == "emberlight" or target.prefab == "stafflight") then
        table.insert(actions, ACTIONS.TRANSFORM_FIREBALL)
    end
end)

-- ③ 覆写已有动作 fn（如一键收获）
local old_pick = ACTIONS.PICK.fn
ACTIONS.PICK.fn = function(act)
    local r = old_pick(act)
    -- ...扩展逻辑...
    return r
end
```

## 4. HUD / Widget 挂载

来源：牛牛信息面板、成就。

```lua
-- 往玩家 HUD 根节点加自定义 Widget
AddClassPostConstruct("screens/playerhud", function(self)
    self.BIHUD = self.root:AddChild(BIHUD(self))
    self.BIHUD:AttachMobile()
end)

-- 往 controls（底部操作栏）加
AddClassPostConstruct("widgets/controls", function(self)
    self.BIHUD_CONFIG = self:AddChild(BIHUD_CONFIG(self))
end)

-- 往状态显示区加（血条等）
AddClassPostConstruct("widgets/statusdisplays", function(self)
    function self:RefreshPetHealth2() ... end
end)
```

## 5. 自定义 Screen（全屏界面）

来源：物品生成菜单。标准结构：require widget 基类 → 构造 Screen → 组件布局 → PushScreen。

```lua
local Screen = require "widgets/screen"
local Widget = require "widgets/widget"
local Text = require "widgets/text"
local Image = require "widgets/image"
local TextButton = require "widgets/textbutton"
local Menu = require "widgets/menu"

-- 打开（带淡入淡出）
_G.TheFrontEnd:Fade(_G.FADE_OUT, _G.SCREEN_FADE_TIME, function()
    _G.TheFrontEnd:PushScreen(DebugMenuScreen())
    _G.TheFrontEnd:Fade(_G.FADE_IN, _G.SCREEN_FADE_TIME)
end)
```

## 6. 状态图修改与驱动

来源：小小格温。

```lua
-- 给玩家加新状态
AddStategraphState("wilson", State {
    name = "corin_rush",
    -- tags/timeline/events 配置
})

-- 跳状态
act.doer.sg:GoToState("gwen_soul_jump")
```

## 7. 技能系统改造（重点：方法覆写 + 多阶段重放）

来源：无限技能（改 DST 官方技能树）。核心思路：`G.pcall(G.require, ...)` 安全加载 →
覆写表内数据 → 覆写类方法 → 在多个加载阶段重试，防止时机不对。

```lua
local G = GLOBAL or _G
local function ApplyInfiniteSkills()
    -- 安全 require，失败不崩溃
    local ok_defs, defs = G.pcall(G.require, "prefabs/skilltree_defs")
    if ok_defs and defs.SKILLTREE_DEFS then
        for _, prefab_defs in pairs(defs.SKILLTREE_DEFS) do
            for _, skill in pairs(prefab_defs) do
                if type(skill.lock_open) == "function" then
                    skill.lock_open = function() return true end  -- 强制解锁
                end
            end
        end
    end
    -- 覆写类方法（保存原函数再包装，不直接覆盖）
    local ok_data, SkillTreeData = G.pcall(G.require, "skilltreedata")
    if ok_data and type(SkillTreeData.GetPointsForSkillXP) == "function" then
        local old = SkillTreeData.ActivateSkill
        SkillTreeData.ActivateSkill = function(self, skill, characterprefab)
            if self.skillxp and self.skillxp[characterprefab] == nil then
                self.skillxp[characterprefab] = 0
            end
            return old(self, skill, characterprefab)
        end
    end
    G.rawset(G, "INFINITE_SKILL_ACTIVATION", true)
end
-- 多阶段重试，覆盖不同加载时机
Reapply("modmain")
AddGamePostInit(function() Reapply("game post init") end)
AddSimPostInit(function() Reapply("sim post init") end)
-- 非专用服上，再改 UI 显示
if not (G.TheNet and G.TheNet:IsDedicated()) then
    AddClassPostConstruct("widgets/redux/skilltreebuilder", function(builder)
        local old_refresh = builder.RefreshTree
        builder.RefreshTree = function(self, ...)
            local r = old_refresh and old_refresh(self, ...) or nil
            for _, g in pairs(self.skillgraphics or {}) do
                if g and g.status then g.status.activatable = true end
            end
            return r
        end
    end)
end
```

## 8. 大模组框架：Replica 组件分离 + 自定义 TUNING + 多语言

来源：能力勋章（195 种 API，1016 文件）。这是"如何组织大型模组"的标杆：

- **组件/副本分离**：每个需要跨端数据的组件写两个文件
  `scripts/components/medal_delivery.lua`（主机逻辑）+ `medal_delivery_replica.lua`（客机显示）。
  客机侧通过 `self.inst.replica.medal_delivery:SetDeliverier(...)` 同步。
- **自定义数值表**：`TUNING_MEDAL = {...}`，不用散落魔法数字。
- **自定义动作**：`ACTIONS.MEDAL_ORIGIN_POLLINATION`，配合 `AddComponentAction` 注册。
- **自定义状态图/大脑**：`SGmedal_xxx.lua`、`brains/medal_xxxbrain.lua`，独立命名空间避免冲突。
- **多语言**：`scripts/lang/medal_strings_ch.lua` + `medal_strings_eng.lua`，按 `TUNING.MEDAL_LANGUAGE` 切换。
- **世界级网络组件**：`TheWorld.net.components.medal_spacetimestorms._nodes:value()`。
- **新工具动作表**：`GLOBAL.TOOLACTIONS["MEDALTRANSPLANT"] = true`。

## 9. 存档（组件级 + 子实体）

来源：成就。

```lua
function achievementability:OnSave()
    local data = { coinamount = self.coinamount, killamount = self.killamount }
    if inst.questghost ~= nil then
        data.questghost = inst.questghost:GetSaveRecord()   -- 子实体存档
    end
    return data
end
function achievementability:OnLoad(data)
    self.coinamount = data.coinamount or 0
    self.killamount = data.killamount or 0
end
```

## 10. 输入处理

来源：拖拽丢弃（屏幕坐标 → 世界坐标）、不灵小姐（按键）。

```lua
-- 按键绑定
TheInput:AddKeyDownHandler(KEY_G, function()
    local player = ThePlayer
    -- ...
end)

-- 判断是否点在 HUD 上（避免误触 UI）
if _G.TheInput == nil or _G.TheInput.GetHUDEntityAtPoint == nil then return end
if _G.TheInput:GetHUDEntityAtPoint(x, y) ~= nil then return end
-- 屏幕坐标 → 世界坐标
local wx, wy, wz = _G.TheSim:ProjectScreenPos(x, y)
```

## 11. 相机与视野

来源：大视野。改视野用 `TheCamera`（客机），注意判空。

```lua
local camera = G.TheCamera
if not camera then return end
if type(camera.SetDefault) == "function" then
    -- camera.maxdist 为最大视野距离
    if tonumber(camera.maxdist) ~= 120 then
        -- 修改
    end
end
```

## 12. 地形/世界修改

来源：填海叉。

```lua
local map = TheWorld.Map
map:SetTile(tile_x, tile_y, target_tile)      -- 换 tile 类型
map:RebuildLayer(original_tile, tile_x, tile_y)  -- 重建图层
map:RebuildLayer(target_tile, tile_x, tile_y)
```

## 13. 周期任务与跨天刷新

来源：传奇武器附魔强化。

```lua
-- 周期恢复耐久
inst["restore_use_task"] = inst:DoPeriodicTask(3, function()
    AddEquipUse(inst, 1)
end)

-- 跨天监听（世界天数变化）
inst:WatchWorldState("cycles", UpdateDayEffect)
inst:WatchWorldState("cycles", function(data_inst, data) self:RefreshLimit() end)
```

## 14. 移动端（柠版）模组差异

手机版模组普遍比 PC 版多 4 个框架文件，且部分被原作者或他人**重移植**过：

- `mod_auto.lua`：声明入口与别名（`entrypoints = {["modmain.lua"]=true, ...}`）。
- `preload_assets_auto.lua`：预加载资源声明（通常为空表）。
- `early_prefab_auto.lua`：早期预制物注册。
- `test.lua`：自动化冒烟/行为测试（`contract_version = 3`、`capabilities = {"smoke","behavior"}`）。
- 移动端带 DST 官方技能树：`TheSkillTree`、`prefabs/skilltree_defs`、`skilltreedata`。
- 每个模组目录名就是中文名，`mods.lua` 用 `AddMods("中文名")` 按顺序加载，后加载覆写先加载的同钩子代码。