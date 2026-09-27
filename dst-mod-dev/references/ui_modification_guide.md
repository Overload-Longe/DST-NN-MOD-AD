# DST Mod UI 修改指南

## UI 架构

```
TheFrontEnd
└── Screen (PlayerHUD, MainScreen)
    └── Widget (可嵌套)
        ├── Image / Text / Button / UIAnim
        └── Widget (子组件)
```

### 核心类
- `Widget` - 所有 UI 基类 (`widgets/widget`)
- `Image` - 图片 (`widgets/image`)
- `Text` - 文字 (`widgets/text`)
- `ImageButton` - 图片按钮 (`widgets/imagebutton`)
- `UIAnim` - 动画 (`widgets/uianim`)
- `Screen` - 屏幕 (`widgets/screen`)

## HUD 修改

### 添加 Widget 到 HUD

```lua
AddClassPostConstruct("screens/playerhud", function(self)
    self:DoTaskInTime(0, function()
        if self.mywidget then return end
        self.mywidget = self:AddChild(require("widgets/mywidget")(self.owner))
        self.mywidget:SetVAnchor(ANCHOR_TOP)
        self.mywidget:SetHAnchor(ANCHOR_RIGHT)
        self.mywidget:SetPosition(-100, -150, 0)
        self.mywidget:Show()
    end)
end)
```

### 修改已有 HUD 元素

```lua
AddClassPostConstruct("screens/playerhud", function(self)
    self:DoTaskInTime(0, function()
        if self.controls then
            -- self.controls.health 生命徽章
            -- self.controls.hunger 饥饿徽章
            -- self.controls.sanity 精神徽章
            -- self.controls.inv 背包栏
            -- self.controls.craftingmenu 制作菜单
        end
    end)
end)
```

## 自定义 Widget

```lua
local Widget = require "widgets/widget"
local Image = require "widgets/image"
local Text = require "widgets/text"
local ImageButton = require "widgets/imagebutton"

local MyWidget = Class(Widget, function(self, owner)
    Widget._ctor(self, "MyWidget")
    self.owner = owner
    self.is_open = false

    self:SetScaleMode(SCALEMODE_PROPORTIONAL)
    self:SetMaxPropUpscale(MAX_HUD_SCALE)

    -- 背景
    self.panel = self:AddChild(Image("images/ui.xml", "black_frame.tex"))
    self.panel:SetSize(300, 200)
    self.panel:SetTint(0, 0, 0, 0.8)

    -- 标题
    self.title = self:AddChild(Text(UIFONT, 28))
    self.title:SetString("我的面板")
    self.title:SetPosition(0, 75, 0)
    self.title:SetColour(1, 0.85, 0.5, 1)

    -- 数值
    self.value_text = self:AddChild(Text(NUMBERFONT, 32))
    self.value_text:SetString("0")
    self.value_text:SetPosition(0, 20, 0)

    -- 按钮
    self.use_btn = self:AddChild(ImageButton())
    self.use_btn:SetPosition(0, -40, 0)
    self.use_btn:SetText("使用")
    self.use_btn:SetFont(BUTTONFONT)
    self.use_btn:SetTextSize(24)
    self.use_btn:SetOnClick(function() self:OnUseClick() end)

    self:Hide()
end)

function MyWidget:Open()
    if self.is_open then return end
    self.is_open = true
    self:Show()
    self:MoveToFront()
    self:SetScale(0.8)
    self:ScaleTo(0.8, 1, 0.15)
end

function MyWidget:Close()
    if not self.is_open then return end
    self.is_open = false
    self:Hide()
end

function MyWidget:Toggle()
    if self.is_open then self:Close() else self:Open() end
end

function MyWidget:UpdateValue(val)
    self.value_text:SetString(tostring(val))
end

function MyWidget:OnUseClick()
    if self.owner and self.owner:IsValid() then
        -- SendModRPCToServer(...)
    end
end

function MyWidget:OnControl(control, down)
    if MyWidget._base.OnControl(self, control, down) then return true end
    if not down and control == CONTROL_CANCEL then
        self:Close()
        return true
    end
    return false
end

return MyWidget
```

## 自定义 Screen

```lua
local Screen = require "widgets/screen"
local Image = require "widgets/image"
local Text = require "widgets/text"
local ImageButton = require "widgets/imagebutton"
local Widget = require "widgets/widget"

local MyScreen = Class(Screen, function(self, owner)
    Screen._ctor(self, "MyScreen")
    self.owner = owner

    -- 半透明背景
    self.black = self:AddChild(Image("images/global.xml", "square.tex"))
    self.black:SetVAnchor(ANCHOR_MIDDLE)
    self.black:SetHAnchor(ANCHOR_MIDDLE)
    self.black:SetScaleMode(SCALEMODE_FILLSCREEN)
    self.black:SetTint(0, 0, 0, 0.6)

    -- 根面板
    self.root = self:AddChild(Widget("ROOT"))
    self.root:SetVAnchor(ANCHOR_MIDDLE)
    self.root:SetHAnchor(ANCHOR_MIDDLE)
    self.root:SetScaleMode(SCALEMODE_PROPORTIONAL)

    self.panel = self.root:AddChild(Image("images/ui.xml", "black_frame.tex"))
    self.panel:SetSize(500, 400)

    self.title = self.root:AddChild(Text(TITLEFONT, 40))
    self.title:SetString("我的屏幕")
    self.title:SetPosition(0, 160, 0)

    self.close_btn = self.root:AddChild(ImageButton())
    self.close_btn:SetPosition(0, -120, 0)
    self.close_btn:SetText("关闭")
    self.close_btn:SetOnClick(function() self:Close() end)

    self.default_focus = self.close_btn
end)

function MyScreen:OnControl(control, down)
    if MyScreen._base.OnControl(self, control, down) then return true end
    if not down and control == CONTROL_CANCEL then
        self:Close()
        return true
    end
    return false
end

function MyScreen:Close()
    TheFrontEnd:PopScreen(self)
end

return MyScreen
```

### 打开 Screen
```lua
local screen = require "screens/myscreen"(self.owner)
TheFrontEnd:PushScreen(screen)
```

## 常用 Widget 操作

### Image
```lua
img:SetSize(w, h)
img:SetPosition(x, y, z)
img:SetTint(r, g, b, a)
img:Show() / img:Hide()
img:SetScale(x, y, z)
img:MoveToFront() / img:MoveToBack()
```

### Text
```lua
txt:SetString("text")
txt:SetColour(r, g, b, a)
txt:SetSize(32)
txt:SetHAlign(ANCHOR_LEFT)
txt:SetVAlign(ANCHOR_MIDDLE)
txt:SetRegionSize(w, h)
```

### ImageButton
```lua
btn:SetText("Click")
btn:SetFont(BUTTONFONT)
btn:SetTextSize(24)
btn:SetTextColour(r, g, b, a)
btn:SetOnClick(function() end)
btn:SetHoverText("Tooltip")
btn:Enable() / btn:Disable()
```

## 动画与特效

```lua
-- 位置移动
widget:MoveTo(x1, y1, z1, x2, y2, z2, time)
-- 缩放
widget:ScaleTo(start, end, time)

-- UIAnim
local UIAnim = require "widgets/uianim"
local anim = self:AddChild(UIAnim())
anim:GetAnimState():SetBank("myanim")
anim:GetAnimState():SetBuild("myanim")
anim:GetAnimState():PlayAnimation("open")
anim:GetAnimState():PushAnimation("idle", true)
```

## 输入处理

```lua
function MyWidget:OnControl(control, down)
    if MyWidget._base.OnControl(self, control, down) then return true end
    if down then
        if control == CONTROL_ACCEPT then return true end
    else
        if control == CONTROL_CANCEL then self:Close() return true end
    end
    return false
end
```

### 常用控件常量
```lua
CONTROL_CANCEL (Esc) / CONTROL_ACCEPT (Enter) / CONTROL_ACTION (空格)
CONTROL_ATTACK (F) / CONTROL_MAP (Tab) / CONTROL_PAUSE (P)
CONTROL_PRIMARY (鼠标左键) / CONTROL_SECONDARY (鼠标右键)
CONTROL_SCROLLUP / CONTROL_SCROLLDOWN
```

### 全局快捷键
```lua
TheInput:AddKeyHandler(function(key, down)
    if down and key == KEY_F1 then
        -- F1 按下
    end
end)
```

## 分辨率适配

```lua
-- 锚点
ANCHOR_LEFT / ANCHOR_MIDDLE / ANCHOR_RIGHT
ANCHOR_TOP / ANCHOR_MIDDLE / ANCHOR_BOTTOM
widget:SetVAnchor(ANCHOR_TOP)
widget:SetHAnchor(ANCHOR_RIGHT)
widget:SetPosition(-50, -50, 0)  -- 相对锚点偏移

-- 缩放模式
SCALEMODE_PROPORTIONAL  -- 比例缩放（推荐 HUD）
SCALEMODE_FILLSCREEN    -- 填充屏幕
widget:SetScaleMode(SCALEMODE_PROPORTIONAL)
widget:SetMaxPropUpscale(MAX_HUD_SCALE)
```

## 常见场景

### 添加快捷栏按钮
```lua
AddClassPostConstruct("screens/playerhud", function(self)
    self:DoTaskInTime(0, function()
        if not self.controls then return end
        self.mod_btn = self.controls:AddChild(ImageButton())
        self.mod_btn:SetVAnchor(ANCHOR_BOTTOM)
        self.mod_btn:SetHAnchor(ANCHOR_LEFT)
        self.mod_btn:SetPosition(300, 200, 0)
        self.mod_btn:SetText("Mod")
        self.mod_btn:SetOnClick(function()
            if self.mymod_panel then self.mymod_panel:Toggle() end
        end)
    end)
end)
```

### 自定义状态指示器
```lua
-- 参考 widget 模板，创建一个带图标+数值的小徽章
-- 挂载到 HUD，通过网络变量事件更新显示
```
