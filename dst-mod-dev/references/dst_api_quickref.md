# DST Mod 开发 API 速查表

## 全局对象

```lua
local TheWorld = GLOBAL.TheWorld
local ThePlayer = GLOBAL.ThePlayer  -- 仅客机
local TheSim = GLOBAL.TheSim
local TheFrontEnd = GLOBAL.TheFrontEnd
local TUNING = GLOBAL.TUNING
local STRINGS = GLOBAL.STRINGS
```

### 世界状态
```lua
TheWorld.state.isday / isdusk / isnight
TheWorld.state.phase  -- "day"/"dusk"/"night"
TheWorld.state.issummer / iswinter / isspring / isautumn
TheWorld.state.season
TheWorld.state.cycles
TheWorld.state.ismastersim
```

## 实体与预制物

### Prefab() 函数

```lua
Prefab(name, fn, assets, deps, force_path_search)
-- name  : 预制物名（控制台 c_give() 用的名字）
-- fn    : 初始化函数，定义属性、组件、方法等
-- assets: 用到的动画、贴图、音效等资源
-- deps  : 依赖的预制物，直接传 prefabs 变量即可
-- force_path_search: 强制路径搜索（一般不用）

-- 返回示例
return Prefab("myitem", fn, assets, prefabs)
```

### CreateEntity() 初始组件

通过 `CreateEntity()` 创建的实体，可按需添加：
- `Transform` — 位置、方向、缩放
- `AnimState` — 材质(Build)、动画集合(Bank)、动画播放
- `Physics` — 物理行为、碰撞
- `Light` — 光源
- `Network` — 网络组件（DST 必须，决定客机能否看到）
- `MapEntity` / `MiniMapEntity` — 小地图图标
- `SoundEmitter` — 声音

```lua
local inst = CreateEntity()
inst.entity:AddTransform()
inst.entity:AddAnimState()
inst.entity:AddNetwork()       -- DST 必须
inst.entity:AddSoundEmitter()
inst.entity:AddDynamicShadow()
inst.entity:AddLight()
inst.entity:AddMiniMapEntity()
MakeInventoryPhysics(inst)
MakeCharacterPhysics(inst, mass, radius)
MakeObstaclePhysics(inst, radius)
inst:AddTag("tag") / inst:RemoveTag("tag") / inst:HasTag("tag")
inst.entity:SetPristine()      -- 网络初始化完成标记
if not TheWorld.ismastersim then return inst end
```

### EntityScript 完整方法

**生命周期与状态**
```lua
inst:IsValid() / inst:IsInLimbo() / inst:IsAsleep()
inst:IsOnValidGround() / inst:IsOnPassablePoint() / inst:IsOnOcean()
inst:IsInLight() / inst:IsLightGreaterThan(threshold)
inst:GetIsWet() / inst:GetTimeAlive()
inst:Remove() / inst:Hide() / inst:Show()
inst:RemoveFromScene() / inst:ReturnToScene()
inst:ForceOutOfLimbo()
inst:GetCurrentPlatform() / inst:GetCurrentTileType()
```

**位置与距离**
```lua
inst:GetPosition() / inst.Transform:GetWorldPosition()
inst.Transform:SetPosition(x, y, z)
inst:GetRotation() / inst:GetAngleToPoint(x, y, z)
inst:FacePoint(x, y, z) / inst:ForceFacePoint(x, y, z)
inst:FaceAwayFromPoint(x, y, z)
inst:GetDistanceSqToInst(other) / inst:GetDistanceSqToPoint(x, y, z)
inst:IsNear(other, range) / inst:IsNearPlayer(range)
inst:GetNearestPlayer() / inst:GetDistanceSqToClosestPlayer()
inst:GetPositionAdjacentTo(other, min_dist, max_dist)
```

**组件与标签**
```lua
inst:AddComponent(name) / inst:RemoveComponent(name)
inst:AddTag(tag) / inst:RemoveTag(tag) / inst:HasTag(tag)
inst:GetComponentName()
```

**名称与显示**
```lua
inst:GetDisplayName() / inst:GetBasicDisplayName() / inst:GetAdjectivedName()
inst:SetPrefabName(name) / inst:SetPrefabNameOverride(name)
inst:GetSkinBuild() / inst:GetSkinName()
inst:GetAdjective()
```

**事件系统**
```lua
inst:ListenForEvent(event, fn, source)
inst:RemoveListener(event, fn, source) / inst:RemoveEventCallback(event, fn, source)
inst:RemoveAllEventCallbacks()
inst:PushEvent(event, data)
inst:WatchWorldState(state, fn) / inst:StopWatchingWorldState(state, fn)
inst:StopAllWatchingWorldStates()
```

**任务与线程**
```lua
inst:DoTaskInTime(time, fn) / inst:DoPeriodicTask(period, fn, initial_delay)
inst:CancelAllPendingTasks() / inst:KillTasks()
inst:GetTaskInfo() / inst:TimeRemainingInTask(task) / inst:ResumeTask(task)
inst:StartThread(fn) / inst:RunScript(fn)
```

**大脑与状态图**
```lua
inst:SetBrain(brainname) / inst:RestartBrain() / inst:StopBrain() / inst:GetBrainString()
inst:SetStateGraph(sgname) / inst:ClearStateGraph()
```

**子实体**
```lua
inst:AddChild(child) / inst:RemoveChild(child) / inst:SpawnChild(prefabname)
```

**动作**
```lua
inst:AddInherentAction(action) / inst:RemoveInherentAction(action)
inst:SetInherentSceneAction(action) / inst:SetInherentSceneAltAction(action)
inst:ClearBufferedAction() / inst:PushBufferedAction(action) / inst:PerformBufferedAction()
inst:GetBufferedAction() / inst:PreviewBufferedAction()
inst:CanDoAction(action) / inst:OnBuilt(builder, pt) / inst:OnUsedAsItem()
```

**物理**
```lua
inst:GetPhysicsRadius() / inst:SetPhysicsRadiusOverride(radius)
inst:SetDeployExtraSpacing(spacing) / inst:SetTerraformExtraSpacing(spacing)
inst:SetGroundTargetBlockerRadius(radius)
```

**存档**
```lua
inst:GetSaveRecord() / inst:GetPersistData() / inst:SetPersistData(data)
inst:LoadPostPass(newents, data) / inst:LongUpdate(dt)
inst:GetDebugString()
```

**生成预制物**
```lua
SpawnPrefab("prefabname")
```

### standardcomponents 常用 Make* 函数

定义在 `standardcomponents.lua`，用于快速设置物理、燃烧、冻结、作祟等性质。

**物理**
```lua
MakeInventoryPhysics(inst)          -- 物品物理
MakeProjectilePhysics(inst)         -- 投射物物理
MakeCharacterPhysics(inst, mass, radius)   -- 角色物理
MakeFlyingCharacterPhysics(inst, mass, radius)
MakeTinyFlyingCharacterPhysics(inst, mass, radius)
MakeGiantCharacterPhysics(inst, mass, radius)
MakeFlyingGiantCharacterPhysics(inst, mass, radius)
MakeGhostPhysics(inst, mass, radius)
MakeTinyGhostPhysics(inst, mass, radius)
MakeObstaclePhysics(inst, radius)   -- 障碍物物理
MakeSmallObstaclePhysics(inst, radius)
MakeHeavyObstaclePhysics(inst, radius)
MakeSmallHeavyObstaclePhysics(inst, radius)
MakeWaterObstaclePhysics(inst, radius, depth)
RemovePhysicsColliders(inst)
ChangeToObstaclePhysics(inst) / ChangeToCharacterPhysics(inst)
ChangeToGhostPhysics(inst) / ChangeToInventoryPhysics(inst)
ChangeToWaterObstaclePhysics(inst)
ToggleOffCharacterCollisions(inst) / ToggleOnCharacterCollisions(inst)
ToggleOffAllObjectCollisions(inst)
PreventCharacterCollisionsWithPlacedObjects(inst)
PreventTargetingOnAttacked(inst)
```

**燃烧**
```lua
MakeSmallBurnable(inst, burntime) / MakeMediumBurnable(inst, burntime)
MakeLargeBurnable(inst, burntime)
MakeSmallPropagator(inst) / MakeMediumPropagator(inst) / MakeLargePropagator(inst)
MakeSmallBurnableCharacter(inst, symbol) / MakeMediumBurnableCharacter(inst, symbol)
MakeLargeBurnableCharacter(inst, symbol)
```

**冻结**
```lua
MakeTinyFreezableCharacter(inst, symbol)
MakeSmallFreezableCharacter(inst, symbol)
MakeMediumFreezableCharacter(inst, symbol)
MakeLargeFreezableCharacter(inst, symbol)
MakeHugeFreezableCharacter(inst, symbol)
```

**作祟（haunt）**
```lua
MakeHauntable(inst)
MakeHauntableLaunch(inst)                    -- 作祟后弹飞
MakeHauntableLaunchAndSmash(inst)
MakeHauntableWork(inst)                       -- 作祟后被工作
MakeHauntableWorkAndIgnite(inst)
MakeHauntableFreeze(inst)                     -- 作祟后冻结
MakeHauntableIgnite(inst)                     -- 作祟后点燃
MakeHauntableLaunchAndIgnite(inst)
MakeHauntableChangePrefab(inst, prefab)
MakeHauntableLaunchOrChangePrefab(inst)
MakeHauntablePerish(inst)                     -- 作祟后腐烂
MakeHauntableLaunchAndPerish(inst)
MakeHauntablePanic(inst)                      -- 作祟后恐慌
MakeHauntablePanicAndIgnite(inst)
MakeHauntablePlayAnim(inst, anim)
MakeHauntableGoToState(inst, state)
MakeHauntableDropFirstItem(inst)
MakeHauntableLaunchAndDropFirstItem(inst)
AddHauntableCustomReaction(inst, fn, check_fn)
AddHauntableDropItemOrWork(inst)
```

**其他**
```lua
MakeInventoryFloatable(inst)                  -- 水上漂浮
MakeSnowCoveredPristine(inst) / MakeSnowCovered(inst)  -- 积雪覆盖
MakeNoGrowInWinter(inst)                      -- 冬天不生长
MakeFeedableSmallLivestockPristine(inst) / MakeFeedableSmallLivestock(inst)
MakeDeployableFertilizerPristine(inst) / MakeDeployableFertilizer(inst)
AddDefaultRippleSymbols(inst)                 -- 水波纹
```

## 常用组件

### 生命与战斗
```lua
inst.components.health:SetMaxHealth(n) / :DoDelta(n) / :IsDead() / :Kill()
inst.components.combat:SetTarget(t) / :GetTarget() / :DoAttack(t)
inst.components.combat:SetDefaultDamage(n) / :SetAttackRange(n)
```

### 物品与库存
```lua
inst.components.inventoryitem.imagename / .atlasname
inst.components.inventory:GiveItem(item) / :RemoveItem(item) / :Has(prefab, n)
inst.components.stackable:SetMaxSize(n) / :StackSize() / :IsFull()
```

### 燃料与燃烧
```lua
inst.components.fueled:SetMaxFuel(n) / :AddFuel(n) / :SetPercent(p) / :Ignite() / :Extinguish()
inst.components.burnable:Ignite() / :Extinguish() / :IsBurning()
```

### 可食用与腐烂
```lua
inst.components.edible:SetFoodType(type) / :SetHealthValue(n) / :SetHungerValue(n) / :SetSanityValue(n)
inst.components.edible.foodtype = FOODTYPE.MEAT / VEGGIE / GENERIC / etc.
inst.components.perishable:SetPerishTime(TUNING.PERISH_SUPERSLOW)
inst.components.perishable:StartPerishing()
inst.components.perishable.onperishreplacement = "spoiled_food"
```

### 存储容器
```lua
inst.components.container:GiveItem(item, slot) / :RemoveItem(item) / :Open(doer) / :Close(doer) / :Has(prefab, n)
```

### 可工作（砍伐/挖掘）
```lua
inst.components.workable:SetWorkAction(ACTIONS.CHOP) / :SetWorkLeft(n) / :GetWorkLeft()
```

## 事件系统

### 常用事件
```lua
"onremove" / "onbuilt" / "onspawned"
"healthdelta" / "attacked" / "death" / "respawnfromghost"
"onpickup" / "ondropped" / "equip" / "unequip"
"oninspect" / "onworked" / "onfinished"
"playeractivated" / "playerdeactivated" (TheWorld 事件)
"cycleschanged" / "phasechanged" / "seasonchanged"
```

## 网络同步 API

### 网络变量类型
```lua
net_bool(guid, name, dirtyevent)
net_byte / net_ushortint / net_shortint / net_int / net_float
net_string(guid, name, dirtyevent)
net_entity(guid, name, dirtyevent)
```

### 使用模式
```lua
-- 定义（SetPristine 之前）
inst._mydata = net_ushortint(inst.GUID, "mymod._mydata", "mydatadirty")
-- 主机设置
inst._mydata:set(42)
-- 客机读取
local val = inst._mydata:value()
-- 客机监听变化
inst:ListenForEvent("mydatadirty", function() end)
```

### Mod RPC
```lua
AddModRPCHandler("mymod", "action", function(player, inst, param) end)
SendModRPCToServer(MOD_RPC["mymod"]["action"], inst, param)
AddShardModRPCHandler("mymod", "sync", function(shardid, data) end)
SendModRPCToShard(SHARD_RPC["mymod"]["sync"], nil, data)
```

## 配方与科技

```lua
AddRecipe2("myitem", {
    Ingredient("twigs", 2),
    Ingredient("flint", 1),
}, TUNING.PROTOTYPER_TREES.SCIENCEMACHINE, {
    atlas = "images/inventoryimages/myitem.xml",
    image = "myitem.tex",
})
-- 科技树
TUNING.PROTOTYPER_TREES.SCIENCEMACHINE / ALCHEMYENGINE / PRESTIHATITATOR / SHADOWMANIPULATOR
```

## UI Widget 基础

```lua
local Widget = require "widgets/widget"
local Image = require "widgets/image"
local Text = require "widgets/text"
local ImageButton = require "widgets/imagebutton"
-- 挂载到 HUD
AddClassPostConstruct("screens/playerhud", function(self)
    self:DoTaskInTime(0, function()
        self.mywidget = self:AddChild(require("widgets/mywidget")(self.owner))
        self.mywidget:SetVAnchor(ANCHOR_TOP)
        self.mywidget:SetHAnchor(ANCHOR_RIGHT)
        self.mywidget:SetPosition(-150, -100, 0)
    end)
end)
-- 锚点
ANCHOR_LEFT / ANCHOR_MIDDLE / ANCHOR_RIGHT
ANCHOR_TOP / ANCHOR_MIDDLE / ANCHOR_BOTTOM
```

## Mod 挂载点

```lua
AddPrefabPostInit("name", function(inst) end)
AddComponentPostInit("name", function(self) end)
AddClassPostConstruct("screens/playerhud", function(self) end)
AddPlayerPostInit(function(inst) end)
AddWorldPostInit(function(world) end)
AddGamePostInit(function() end)
AddSimPostInit(function() end)
AddPrefabPostInitAny(function(inst) end)
AddModRPCHandler(ns, name, fn)
AddRecipe2(name, ingredients, level, options)
AddStategraphState("wilson", State{...})
AddStategraphEvent("wilson", EventHandler(...))
AddStategraphPostInit("wilson", function(sg) end)
```

## 配置读取

```lua
local val = GetModConfigData("option_name")
-- 带默认值
local function GetConfig(name, default)
    local v = GetModConfigData(name)
    return v ~= nil and v or default
end
```


## 实测补充（来自 100 个实装模组，见 api_usage_statistics.md / real_mod_patterns.md）

### 新增动作三件套（AddAction / AddComponentAction / 覆写 fn）

```lua
-- ① 定义动作（fn 的 act 是 BufferedAction：act.doer / act.target / act.invobject / act:GetActionPoint()）
W_FISHING = AddAction("W_FISHING", "捞鱼", function(act)
    local owner, target, inst = act.doer, act.target, act.invobject
    if not owner then return false end
    -- ...
    return true
end)

-- ② 挂触发条件（组件+槽位条件下把动作加入候选）
AddComponentAction("EQUIPPED", "equippable", function(inst, doer, target, actions, right)
    if right and doer and doer:HasTag("player") and inst.prefab == "lighter" then
        table.insert(actions, ACTIONS.TRANSFORM_FIREBALL)
    end
end)

-- ③ 覆写已有动作
local old = ACTIONS.PICK.fn
ACTIONS.PICK.fn = function(act)
    local r = old(act)
    -- 扩展
    return r
end
```

### 按键绑定与输入

```lua
TheInput:AddKeyDownHandler(KEY_G, function() local p = ThePlayer end)
TheInput:GetHUDEntityAtPoint(x, y)        -- 判断是否点在 HUD 上
local wx, wy, wz = TheSim:ProjectScreenPos(x, y)  -- 屏幕坐标->世界坐标
```

### 安全 require（模组内 require 游戏数据，失败不崩溃）

```lua
local ok, mod = pcall(require, "prefabs/skilltree_defs")  -- 或 G.pcall(G.require, ...)
if ok and type(mod) == "table" then
    -- ...
end
```

### 方法覆写保底（保存原函数再包装 + 多阶段重放）

```lua
local old = SkillTreeData.ActivateSkill
SkillTreeData.ActivateSkill = function(self, skill, char)
    if self.skillxp and self.skillxp[char] == nil then self.skillxp[char] = 0 end
    return old(self, skill, char)
end
-- 加载时机不确定时，在 modmain / AddGamePostInit / AddSimPostInit 各重放一次
```

### 地形修改

```lua
local map = TheWorld.Map
map:SetTile(tx, ty, WORLD_TILES.FARMING_SOIL)
map:RebuildLayer(original_tile, tx, ty)
map:RebuildLayer(target_tile, tx, ty)
```

### 世界状态监听

```lua
inst:WatchWorldState("cycles", UpdateDayEffect)  -- 跨天刷新
inst:WatchWorldState("season", fn)
```

### 技能树（DST 官方技能树，移动端/新版本）

```lua
TheSkillTree                              -- 全局技能树
pcall(require, "prefabs/skilltree_defs")  -- SKILLTREE_DEFS
pcall(require, "skilltreedata")           -- GetPointsForSkillXP / GetAvailableSkillPoints / ActivateSkill
```

### Replica 组件（主机/客机数据分离，大模组规范）

```
scripts/components/medal_delivery.lua           -- 主机逻辑
scripts/components/medal_delivery_replica.lua   -- 客机副本，self.inst.replica.medal_delivery:SetXxx()
```

### 其他实用

```lua
inst:WatchWorldState("cycles", fn)
inst.sg:HasStateTag("busy")                -- 状态图条件判断
inst.AnimState:OverrideSymbol(region, build, symbol)  -- 换部件符号/皮肤
inst:StartUpdatingComponent() / :StopUpdatingComponent()
inst:GetSaveRecord()                       -- 子实体存档（配合 OnSave）
GLOBAL.TOOLACTIONS["MYTOOL"] = true        -- 新工具动作表
local mediam = require("widgets/screen")   -- 自定义 Screen 基类
TheFrontEnd:Fade(FADE_OUT, SCREEN_FADE_TIME, function() TheFrontEnd:PushScreen(s) TheFrontEnd:Fade(FADE_IN, SCREEN_FADE_TIME) end)
```

### 移动端（柠版）模组框架文件

`mod_auto.lua`（入口声明）、`preload_assets_auto.lua`（资源）、`early_prefab_auto.lua`（早期预制物）、
`test.lua`（自动测试）。模组目录名=中文名，mods.lua 用 `AddMods("中文名")` 按序加载。
