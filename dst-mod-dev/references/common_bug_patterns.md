# DST Mod 常见 Bug 模式与修复方案

## 目录
1. [崩溃类错误](#崩溃类错误)
2. [逻辑类错误](#逻辑类错误)
3. [网络同步问题](#网络同步问题)
4. [存档兼容性问题](#存档兼容性问题)
5. [性能与内存问题](#性能与内存问题)
6. [UI 相关 Bug](#ui-相关-bug)

---

## 崩溃类错误

### 1. attempt to index a nil value (field 'xxx')

**症状**：日志报 `attempt to index a nil value (field 'components')` 或类似。

**根因**：访问了不存在的组件/字段，常见于：
- 预制物未添加对应组件就调用其方法
- 客机上访问仅主机存在的组件（如 `components.worldstate`）
- 实体已被移除但仍在回调中引用

**修复模式**：
```lua
-- 错误写法
inst.components.fueled:SetPercent(1)

-- 安全写法
if inst.components.fueled then
    inst.components.fueled:SetPercent(1)
end

-- 或用辅助函数
local function GetComponentSafe(inst, name)
    return inst and inst:IsValid() and inst.components and inst.components[name] or nil
end
```

### 2. attempt to call method 'xxx' (a nil value)

**症状**：调用了实体上不存在的方法。

**根因**：
- API 版本变更，方法被重命名或移除
- 在错误的实体类型上调用方法
- mod 加载顺序问题，函数尚未定义

**排查步骤**：
1. 在 `scripts/` 目录下搜索该方法名，确认是否存在
2. 检查调用对象的实际类型（`print(tostring(inst))`）
3. 对比 DST 版本更新日志中的 API 变更

### 3. stack overflow (too many recursive calls)

**症状**：日志报 `stack overflow`。

**根因**：
- 事件监听形成循环（A 触发 B，B 又触发 A）
- `onbuilt` / `onremove` 等回调中触发自身
- 无限递归的函数调用

**修复**：
```lua
-- 错误：事件循环
inst:ListenForEvent("onremove", function()
    SpawnPrefab("collapse_small")
end)

-- 正确：加守卫标记
local is_removing = false
inst:ListenForEvent("onremove", function()
    if is_removing then return end
    is_removing = true
end)
```

### 4. bad argument #x to 'xxx' (xxx expected, got nil)

**症状**：函数参数类型错误。

**根因**：
- 传入了 nil 而非预期的实体/字符串/数字
- `FindEntity` 等查找函数返回 nil 未检查

**修复**：所有可能返回 nil 的函数调用后必须检查：
```lua
local target = FindEntity(inst, 10, function(guy)
    return guy.components.health and not guy.components.health:IsDead()
end)
if target then
    -- 安全使用 target
end
```

---

## 逻辑类错误

### 1. 预制物注册冲突 / 重复定义

**症状**：两个 mod 都修改同一预制物，后加载的覆盖先加载的。

**排查**：
- 检查 `modmain.lua` 中 `AddPrefabPostInit` 的预制物名是否正确
- 用 `c_find("prefabname")` 控制台测试预制物是否存在
- 检查 `modinfo.lua` 中的 `priority` 配置加载顺序

**修复**：使用 `AddPrefabPostInit` 而非覆盖整个预制物定义：
```lua
AddPrefabPostInit("firepit", function(inst)
    if not GLOBAL.TheWorld.ismastersim then return end
end)
```

### 2. 组件未正确添加到预制物

**症状**：自定义组件在游戏中不生效，报 `component not found`。

**根因**：
- 只在 `modmain.lua` 中 `AddComponentPostInit` 但未在预制物中 `AddComponent`
- 组件文件名与类名不匹配
- 组件文件未放在 `scripts/components/` 目录

**修复**：
```lua
-- 在预制物定义中
inst:AddComponent("mycomponent")

-- 组件文件: scripts/components/mycomponent.lua
local MyComponent = Class(function(self, inst)
    self.inst = inst
    self.value = 0
end)
return MyComponent
```

### 3. 任务（task）未正确清理

**症状**：实体移除后任务仍在运行，导致访问已销毁实体。

**修复**：
```lua
inst:ListenForEvent("onremove", function()
    if inst._mytask then
        inst._mytask:Cancel()
        inst._mytask = nil
    end
end)

-- 或使用 inst:DoTaskInTime 自动绑定
inst._mytask = inst:DoTaskInTime(5, function() end)
```

---

## 网络同步问题

### 1. 客机看不到变化 / 只有主机生效

**症状**：主机上功能正常，客机上物品不更新、状态不同步。

**根因**：
- 直接修改了客机上的组件数据（应通过网络变量同步）
- 使用了仅主机存在的组件
- 未正确使用 Mod RPC

**修复模式**：
```lua
-- 方式1：使用网络变量
inst._mydata = net_ushortint(inst.GUID, "mymod._mydata", "mydatadirty")
inst:ListenForEvent("mydatadirty", function()
    local val = inst._mydata:value()
end)
inst._mydata:set(42)

-- 方式2：Mod RPC
AddModRPCHandler("mymod", "dosomething", function(player, inst, param) end)
SendModRPCToServer(MOD_RPC["mymod"]["dosomething"], inst, param)
```

### 2. 客机上访问 components 为 nil

**症状**：客机上 `inst.components.xxx` 为 nil。

**说明**：DST 中许多组件仅在主机模拟中存在，客机只有实体的网络表示。

**修复**：
```lua
if not GLOBAL.TheWorld.ismastersim then
    return
end
```

### 3. 分片（shard）间数据不同步

**修复**：使用分片 RPC：
```lua
AddShardModRPCHandler("mymod", "syncdata", function(shardid, data) end)
SendModRPCToShard(SHARD_RPC["mymod"]["syncdata"], nil, data)
```

---

## 存档兼容性问题

### 1. 旧存档加载崩溃

**症状**：更新 mod 后加载旧存档崩溃。

**根因**：
- 移除了旧版本中保存的字段，加载时 OnLoad 访问不存在的数据
- 组件被移除但存档中仍有其数据
- 数据格式变更未做迁移

**修复**：
```lua
function MyComponent:OnSave()
    return { version = 2, value = self.value }
end

function MyComponent:OnLoad(data)
    if data then
        if data.version == 1 then
            self.value = data.oldfield or 0
        elseif data.version == 2 then
            self.value = data.value or 0
        end
    end
end
```

### 2. 存档后自定义数据丢失

**修复**：
```lua
function MyComponent:OnSave()
    return { mydata = self.mydata }
end

function MyComponent:OnLoad(data)
    if data then
        self.mydata = data.mydata or 0
    end
end
```

---

## 性能与内存问题

### 1. 内存泄漏（监听器未移除）

**症状**：游戏时间越长越卡，最终崩溃。

**根因**：
- `ListenForEvent` 后未在实体移除时移除监听器
- 全局表中存储了已移除实体的引用
- `DoPeriodicTask` 未取消

**修复**：
```lua
-- 用 inst:ListenForEvent 而非全局监听，实体移除时自动清理
-- 全局监听器必须手动清理
```

### 2. 每帧执行导致卡顿

**优化**：
```lua
function MyComponent:OnUpdate(dt)
    self._updatetime = (self._updatetime or 0) + dt
    if self._updatetime < 0.5 then return end
    self._updatetime = 0
end
```

---

## UI 相关 Bug

### 1. UI 不显示 / 显示空白

**排查**：
- 检查 widget 是否添加到正确的父级
- 检查位置坐标是否在屏幕范围内
- 检查纹理是否正确加载

```lua
AddClassPostConstruct("screens/playerhud", function(self)
    self.mywidget = self:AddChild(require("widgets/mywidget")())
    self.mywidget:SetVAnchor(ANCHOR_TOP)
    self.mywidget:SetHAnchor(ANCHOR_RIGHT)
    self.mywidget:SetPosition(-100, -100, 0)
end)
```

### 2. 客机上 UI 不更新

**修复**：UI 只从网络变量读取数据：
```lua
inst:ListenForEvent("mydatadirty", function()
    self.label:SetString(tostring(inst._mydata:value()))
end, owner)
```

---

## 通用排查流程

1. **查看日志**：`Documents/Klei/DoNotStarveTogether/client_log.txt`，搜索 `error` 定位崩溃行
2. **二分法禁用**：逐个禁用 mod 确认冲突来源
3. **控制台调试**：按 `~` 打开控制台，用 `c_find()`、`print()` 检查实体状态
4. **打印堆栈**：在可疑函数中加 `print(debug.traceback())`
5. **检查版本**：确认 mod 支持的 DST 版本与当前游戏版本一致
