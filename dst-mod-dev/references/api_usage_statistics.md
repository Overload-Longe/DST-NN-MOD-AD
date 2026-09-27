# 真实模组 API 使用统计（基于 100 个实装模组实测）

> **数据来源**：柠版饥荒联机手机版内置的 100 个模组、共 4485 个 Lua 文件（明文脚本），
> 由脚本对全部 Lua 文件做词法扫描统计而来。这些是**真实在运行、被验证可用**的 API 用法，
> 是判断"某个 API 是否值得用、怎么用"的最可靠依据。

## 1. 用法速查：写功能时优先用这些（按使用模组数排序）

### 挂载钩子（Mod 入口，几乎每个模组都用）

| API | 使用模组数 | 说明 |
|---|---|---|
| `GetModConfigData` | 77 | 读配置，标配 |
| `AddPrefabPostInit` | 62 | 给已有预制物追加逻辑，首选（不覆盖） |
| `AddClassPostConstruct` | 59 | 改已有 class（HUD/Widget/组件构造后） |
| `AddComponentPostInit` | 44 | 改已有组件 |
| `AddPlayerPostInit` | 43 | 玩家出生时挂逻辑 |
| `AddSimPostInit` | 33 | 模拟层初始化后 |
| `AddStategraphPostInit` | 23 | 改已有状态图 |
| `AddRecipe2` | 30 | 新配方（新版 API） |
| `AddGamePostInit` | 9 | 游戏层初始化后 |
| `AddAction` | 33 | 新动作 |
| `AddModRPCHandler` | 39 | 网络 RPC 服务端 |
| `AddMinimapAtlas`/`AddMinimapIcon` | 32 | 小地图图标 |
| `AddPrefabPostInitAny` | 25 | 任意预制物 |
| `AddStategraphState` | 19 | 新增状态 |

### 网络同步（多人可见的必选）

| API | 使用模组数 | 说明 |
|---|---|---|
| `TheWorld.ismastersim` | 60 | 主机/客机分支守卫 |
| `SetPristine` | 47 | 网络实体就绪标记 |
| `AddNetwork` | 47 | 实体加网络组件 |
| `net_` 系列 | 44 | net_bool/string/entity/float/byte 等网络变量 |
| `SendModRPCToServer` | 40 | 客机→主机请求 |
| `SendModRPCToClient` | 17 | 主机→客机 |
| `AddShardModRPCHandler` | 6 | 跨服务器（洞穴等）RPC |

### 实体与组件（写逻辑的主体）

| API | 使用模组数 | 说明 |
|---|---|---|
| `SpawnPrefab` | 75 | 生成实体 |
| `HasTag` | 74 | 判标签 |
| `ListenForEvent` | 71 | 监听事件 |
| `IsValid` | 69 | 判空/存活，**访问实体前必查** |
| `DoTaskInTime` | 66 | 延迟任务 |
| `AddComponent` | 65 | 加组件 |
| `GetWorldPosition`/`GetPosition` | 63/61 | 取坐标 |
| `AddTag`/`RemoveTag` | 63/44 | 标签管理 |
| `FindEntities` | 57 | 范围内找实体 |
| `PushEvent` | 47 | 发事件 |
| `DoPeriodicTask` | 46 | 周期任务 |
| `OnSave`/`OnLoad` | 49/47 | 存档 |
| `WatchWorldState` | 28 | 监听世界状态（季节/天数） |
| `StartUpdatingComponent` | 23 | 手动开关组件更新 |
| `SetPrefabNameOverride` | 17 | 改名显示 |
| `StartThread` | 19 | 协程线程 |

### 高频组件（components.X）

`inventory`(62) `inventoryitem`(59) `health`(52) `container`(48) `talker`(47) `locomotor`(44) `stackable`(43) `inspectable`(42) `combat`(41) `workable`(40) `sanity`(39) `playercontroller`(37) `burnable`(36) `weapon`(33) `timer`(31) `fueled`(31) `perishable`(31) `builder`(29) `temperature`(29) `leader`(28) `moisture`(28) `edible`(27) `seed`(27) `tool`(26) `deployable`(26) `follower`(24) `rechargeable`(24) `sleeper`(21) `growable`(19) `cooker`(19) `stewer`(19) `preserver`(19) `soil`(20) `crop`(15) `boat`(30) `fishingrod`(15) `saddle`(10) `teleporter`(9) `terraformer`(8)

## 2. 进阶/罕见手法（出现模组少，但值得掌握）

| 手法 | 出现模组数 | 典型用途 |
|---|---|---|
| 覆写 ACTIONS.PICK 等动作 fn | 多 | 一键收获/改交互（萌新快乐种地等） |
| `AddComponentAction("EQUIPPED","equippable",...)` | 少 | 给装备加右键动作（不灵小姐） |
| `TheInput:AddKeyDownHandler(KEY_G,...)` | 少 | 按键绑定 |
| `map:SetTile` + `RebuildLayer` | 少 | 地形改造（填海叉） |
| `TheSim:ProjectScreenPos` | 少 | 屏幕坐标→世界坐标（拖拽丢弃） |
| `TheCamera:SetDefault/maxdist` | 少 | 改视野（大视野） |
| `GetSaveRecord`/`SetPersistData` | 20/5 | 子实体存档 |
| `inst.sg:HasStateTag("busy")` | 多 | 状态图条件判断 |
| `G.pcall(G.require, ...)` | 少 | 安全 require（不崩溃） |
| `inst:WatchWorldState("cycles", fn)` | 28 | 跨天刷新 |
| `AnimState:OverrideSymbol` | 少 | 换皮肤/部件符号 |
| Replica 组件（xxx.lua + xxx_replica.lua） | 少 | 大模组主机/客机数据分离（能力勋章） |
| `TheWorld.net.components.xxx` | 少 | 世界级网络组件 |
| `GLOBAL.TOOLACTIONS["X"] = true` | 少 | 定义新工具动作 |
| 多语言 STRINGS（xxx_ch.lua/xxx_en.lua） | 少 | 中英双语 |

## 3. 用途

- **优先采用高使用率 API**：这些在大量实装模组中验证过，行为可预期、兼容性好。
- **学习进阶手法**：低使用率但高价值的 API 往往是大模组的核心，遇到复杂需求（跨端同步、
  自定义 UI、技能树、新生物 AI）时参照 `real_mod_patterns.md`。
- **手机版（柠版）差异**：移动端模组普遍带 `mod_auto.lua`、`preload_assets_auto.lua`、
  `test.lua`、`early_prefab_auto.lua` 四个框架文件，且很多模组被重新移植过（如技能树系统）。
  移动端自带 DST 技能树 API（`TheSkillTree`、`prefabs/skilltree_defs`、`skilltreedata`）。