# DST Mod 标准结构与文件组织

## Mod 目录结构

```
mymod/
├── modinfo.lua              # 元信息（必需）
├── modmain.lua              # 入口脚本（必需）
├── modicon.xml / modicon.tex # 图标
├── scripts/
│   ├── prefabs/             # 预制物定义
│   ├── components/          # 自定义组件
│   ├── widgets/             # 自定义 UI
│   ├── screens/             # 自定义屏幕
│   ├── stategraphs/         # 状态图
│   └── actions/             # 自定义动作
├── anim/                    # 动画资源 (.zip)
├── images/
│   ├── inventoryimages/     # 物品图标
│   └── hud/                 # HUD 图片
└── sounds/                  # 音效 (.fsb)
```

## modinfo.lua

```lua
name = "My Mod"
description = "描述"
author = "作者"
version = "1.0.0"
api_version = 10
dst_compatible = true
all_clients_require_mod = true   -- 影响游戏逻辑时设 true
client_only_mod = false           -- 纯 UI mod 设 true
icon_atlas = "modicon.xml"
icon = "modicon.tex"
server_filter_tags = {"mymod"}

configuration_options = {
    {
        name = "enable",
        label = "启用",
        hover = "说明",
        options = {
            {description = "开", data = true},
            {description = "关", data = false},
        },
        default = true,
    },
}
```

## modmain.lua 标准结构

```lua
local GLOBAL = _G
local TheWorld = GLOBAL.TheWorld

-- 读取配置
local enable = GetModConfigData("enable")

-- 客机也执行（UI、字符串）
AddSimPostInit(function()
    GLOBAL.STRINGS.NAMES.MYITEM = "我的物品"
end)

AddClassPostConstruct("screens/playerhud", function(self)
    self:DoTaskInTime(0, function() end)
end)

-- 仅主机执行
if TheWorld.ismastersim then
    AddPrefabPostInit("firepit", function(inst) end)
    AddComponentPostInit("health", function(self) end)
    AddPlayerPostInit(function(inst) end)
end

AddWorldPostInit(function(world) end)
AddGamePostInit(function() end)
```

## 预制物模板（可食用物品，含腐烂）

```lua
local assets = {
    Asset("ANIM", "anim/pidan.zip"),
    Asset("IMAGE", "images/pidan.tex"),
    Asset("ATLAS", "images/pidan.xml"),
}

local prefabs = {
    "spoiled_food",
}

local function fn()
    local assetname = "pidan"
    local inst = CreateEntity()

    -- ===== 客机/主机共有部分 =====
    inst.entity:AddTransform()
    inst.entity:AddAnimState()
    MakeInventoryPhysics(inst)

    inst.AnimState:SetBank(assetname)
    inst.AnimState:SetBuild(assetname)
    inst.AnimState:PlayAnimation("idle")

    MakeInventoryFloatable(inst)  -- 水上漂浮

    inst.entity:SetPristine()

    if not TheWorld.ismastersim then
        return inst
    end

    -- ===== 仅主机部分 =====
    inst:AddComponent("inspectable")

    inst:AddComponent("inventoryitem")
    inst.components.inventoryitem.atlasname = "images/pidan.xml"

    -- 可食用
    inst:AddComponent("edible")
    inst.components.edible.foodtype = FOODTYPE.MEAT
    inst.components.edible.hungervalue = TUNING.CALORIES_SMALL
    inst.components.edible.healthvalue = TUNING.CALORIES_TINY
    inst.components.edible.sanityvalue = TUNING.SANITY_HUGE

    -- 可腐烂
    inst:AddComponent("perishable")
    inst.components.perishable:SetPerishTime(TUNING.PERISH_SUPERSLOW)
    inst.components.perishable:StartPerishing()
    inst.components.perishable.onperishreplacement = "spoiled_food"

    -- 可堆叠
    inst:AddComponent("stackable")
    inst.components.stackable.maxsize = TUNING.STACK_SIZE_SMALLITEM

    MakeHauntableLaunch(inst)

    return inst
end

return Prefab("pidan", fn, assets, prefabs)
```

### 预制物模板（基础物品）

```lua
local assets = {
    Asset("ANIM", "anim/myitem.zip"),
    Asset("ATLAS", "images/inventoryimages/myitem.xml"),
    Asset("IMAGE", "images/inventoryimages/myitem.tex"),
}

local function fn()
    local inst = CreateEntity()
    inst.entity:AddTransform()
    inst.entity:AddAnimState()
    inst.entity:AddNetwork()
    MakeInventoryPhysics(inst)
    inst.AnimState:SetBank("myitem")
    inst.AnimState:SetBuild("myitem")
    inst.AnimState:PlayAnimation("idle")
    inst:AddTag("mytag")
    inst.entity:SetPristine()

    if not TheWorld.ismastersim then return inst end

    inst:AddComponent("inspectable")
    inst:AddComponent("inventoryitem")
    inst.components.inventoryitem.imagename = "myitem"
    inst.components.inventoryitem.atlasname = "images/inventoryimages/myitem.xml"
    inst:AddComponent("stackable")
    inst.components.stackable.maxsize = TUNING.STACK_SIZE_SMALLITEM
    MakeHauntableLaunch(inst)
    return inst
end

return Prefab("myitem", fn, assets)
```

## 组件模板

```lua
local MyComponent = Class(function(self, inst)
    self.inst = inst
    self.value = 0
end)

function MyComponent:SetValue(val)
    self.value = val
    self.inst:PushEvent("mycomponentvaluechanged", {value = self.value})
end

function MyComponent:OnSave()
    return { value = self.value }
end

function MyComponent:OnLoad(data)
    if data then self.value = data.value or 0 end
end

function MyComponent:OnRemoveFromEntity() end

return MyComponent
```

## Widget 模板

```lua
local Widget = require "widgets/widget"
local Image = require "widgets/image"
local Text = require "widgets/text"
local ImageButton = require "widgets/imagebutton"

local MyWidget = Class(Widget, function(self, owner)
    Widget._ctor(self, "MyWidget")
    self.owner = owner
    self.bg = self:AddChild(Image("images/hud.xml", "crafting_menu.tex"))
    self.bg:SetSize(200, 150)
    self.label = self:AddChild(Text(UIFONT, 28))
    self.label:SetString("Hello")
    self.btn = self:AddChild(ImageButton())
    self.btn:SetText("Click")
    self.btn:SetOnClick(function() end)
end)

function MyWidget:UpdateData(val)
    self.label:SetString(tostring(val))
end

return MyWidget
```

## 资源文件

- **动画**：Spriter 导出 `.scml` + 图片，打包为 `.zip` 放 `anim/`
- **物品图标**：64x64 或 128x128 PNG，用 autocompiler 转 `.xml`+`.tex` 放 `images/inventoryimages/`
- **音效**：FMOD Studio 导出 `.fsb` 放 `sounds/`

## 配置选项

```lua
-- 读取（带默认值）
local function GetConfig(name, default)
    local v = GetModConfigData(name)
    return v ~= nil and v or default
end
local enable = GetConfig("enable", true)
```

## 字符串定义

```lua
AddSimPostInit(function()
    STRINGS.NAMES.MYITEM = "我的物品"
    STRINGS.RECIPE_DESC.MYITEM = "配方描述"
    STRINGS.CHARACTERS.GENERIC.DESCRIBE.MYITEM = "检查台词"
    STRINGS.ACTIONS.MYACTION = "动作名"
end)
```