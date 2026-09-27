# DST Mod 移植与兼容性适配指南

## 目录
1. [DS 单机版 → DST 联机版移植](#ds-单机版--dst-联机版移植)
2. [DST 旧版 → 新版 API 适配](#dst-旧版--新版-api-适配)
3. [网络同步改造](#网络同步改造)
4. [存档兼容性处理](#存档兼容性处理)
5. [Mod 间冲突兼容](#mod-间冲突兼容)
6. [移植检查清单](#移植检查清单)

---

## DS 单机版 → DST 联机版移植

### 核心差异总览

| 方面 | DS 单机版 | DST 联机版 |
|------|-----------|------------|
| 模拟模式 | 单一模拟 | 主机模拟 + 客机预测 |
| 组件 | 所有实体都有完整组件 | 客机只有网络同步的部分组件 |
| 玩家 | 单玩家 | 多玩家，每个玩家有独立 HUD |
| 世界 | 单世界 | 主世界 + 洞穴分片 |
| UI | 直接操作 | 通过 HUD 类后初始化 |

### 步骤 1：modinfo.lua 适配

```lua
-- DST 版
name = "My Mod (DST)"
description = "..."
author = "..."
version = "1.0.0"
api_version = 10
dst_compatible = true
all_clients_require_mod = true
client_only_mod = false
icon_atlas = "modicon.xml"
icon = "modicon.tex"
configuration_options = {}
```

### 步骤 2：modmain.lua 结构改造

```lua
local require = GLOBAL.require
local TheWorld = GLOBAL.TheWorld

-- 仅主机执行的逻辑
if TheWorld.ismastersim then
    -- 组件修改、预制物修改等
end

-- 客机也需要执行的逻辑（UI、纹理加载等）
```

### 步骤 3：预制物移植要点

```lua
local function fn()
    local inst = CreateEntity()
    inst.entity:AddTransform()
    inst.entity:AddAnimState()
    inst.entity:AddNetwork()  -- DST 必须添加

    MakeInventoryPhysics(inst)
    inst.AnimState:SetBank("myitem")
    inst.AnimState:SetBuild("myitem")
    inst.AnimState:PlayAnimation("idle")

    inst:AddTag("mytag")
    inst.entity:SetPristine()  -- 标记网络初始化完成

    if not TheWorld.ismastersim then
        return inst  -- 客机到此为止
    end

    -- 以下仅主机执行
    inst:AddComponent("inspectable")
    inst:AddComponent("inventoryitem")
    inst:AddComponent("stackable")
    MakeHauntableLaunch(inst)
    return inst
end
```

### 步骤 4：玩家相关代码移植

```lua
-- 错误（DS 写法）
local player = GetPlayer()
player.components.health:DoDelta(10)

-- 正确（DST 写法）
AddPrefabPostInit("player", function(inst)
    if not TheWorld.ismastersim then return end
    inst:DoTaskInTime(0, function()
        if inst.components.health then
            inst.components.health:DoDelta(10)
        end
    end)
end)
```

---

## DST 旧版 → 新版 API 适配

### 常见 API 变更对照

| 旧 API | 新 API |
|--------|--------|
| `GetPlayer()` | `ThePlayer` (客机) |
| `GetWorld()` | `TheWorld` |
| `GetClock()` | `TheWorld.state` |
| `GetSeasonManager()` | `TheWorld.state` |
| `GetClock():IsDay()` | `TheWorld.state.isday` |
| `GetSeasonManager():IsSummer()` | `TheWorld.state.issummer` |

### 状态访问适配

```lua
-- 旧版
if GetClock():IsDay() then ... end

-- 新版
if TheWorld.state.isday then ... end
if TheWorld.state.issummer then ... end
if TheWorld.state.phase == "day" then ... end
```

### 配方适配

```lua
local myrecipe = AddRecipe2("myitem", {
    Ingredient("twigs", 2),
    Ingredient("cutstone", 1),
}, TUNING.PROTOTYPER_TREES.SCIENCEMACHINE, {
    atlas = "images/inventoryimages/myitem.xml",
    image = "myitem.tex",
})
```

---

## 网络同步改造

### 网络变量完整示例

```lua
local function fn()
    local inst = CreateEntity()
    inst.entity:AddTransform()
    inst.entity:AddNetwork()

    -- 定义网络变量（在 SetPristine 之前）
    inst._myvalue = net_ushortint(inst.GUID, "myentity._myvalue", "myvaluedirty")
    inst._myname = net_string(inst.GUID, "myentity._myname", "mynamedirty")

    inst.entity:SetPristine()

    if not TheWorld.ismastersim then
        inst:ListenForEvent("myvaluedirty", function()
            local val = inst._myvalue:value()
        end)
        return inst
    end

    inst._myvalue:set(100)
    inst._myname:set("default")
    return inst
end
```

### Mod RPC 完整示例

```lua
-- 注册 RPC（主机端执行）
AddModRPCHandler("mymod", "useitem", function(player, inst, target)
    if not player or not player:IsValid() then return end
    if not inst or not inst:IsValid() then return end
    if player:GetDistanceSqToInst(inst) > 25 then return end
    if inst.components.mycomponent then
        inst.components.mycomponent:Use(player, target)
    end
end)

-- 客机端调用
local function UseItem(inst, target)
    SendModRPCToServer(MOD_RPC["mymod"]["useitem"], inst, target)
end
```

---

## 存档兼容性处理

### 版本化存档数据

```lua
local MyComponent = Class(function(self, inst)
    self.inst = inst
    self.version = 2
    self.data = {}
end)

function MyComponent:OnSave()
    return { version = self.version, data = self.data }
end

function MyComponent:OnLoad(data)
    if not data then return end
    if data.version == 1 then
        self.data = { count = data.value or 0 }
    elseif data.version == 2 then
        self.data = data.data or {}
    end
    self.data.count = self.data.count or 0
end
```

---

## Mod 间冲突兼容

### 安全修改已有预制物

```lua
AddPrefabPostInit("firepit", function(inst)
    if inst.components.fueled then
        local old_ignite = inst.components.fueled.ignite
        inst.components.fueled.ignite = function(self, doer)
            if old_ignite then old_ignite(self, doer) end
        end
    end
end)
```

### 检测其他 Mod 是否存在

```lua
local function IsModEnabled(modname)
    for i, mod in ipairs(ModManager:GetEnabledMods()) do
        if mod.modname == modname then return true end
    end
    return false
end
```

---

## 移植检查清单

### 文件结构
- [ ] `modinfo.lua` 已更新为 DST 格式
- [ ] `modmain.lua` 区分主机/客机逻辑
- [ ] 预制物添加了 `Network` 组件和 `SetPristine()`
- [ ] 组件添加了 `OnSave`/`OnLoad`

### 网络同步
- [ ] 所有需要客机显示的数据都有网络变量
- [ ] 客机请求主机的操作使用 Mod RPC
- [ ] RPC 处理函数有参数校验和防作弊检查
- [ ] 客机代码不直接访问 `components`

### 兼容性
- [ ] 旧存档可以正常加载
- [ ] 与常见 mod 无冲突（使用 PostInit）
- [ ] 洞穴分片正常工作
- [ ] 多玩家场景正常

### 测试
- [ ] 主机单独运行测试通过
- [ ] 客机加入测试通过
- [ ] 保存/加载测试通过
- [ ] 日志无 error/warning
