# 人物（角色）Mod 适配指南

> 整理：神似 ｜ 来源：`C:\Users\Longe\下载\饥荒\人物mod` 下 20 个**已适配柠版**的人物 Mod（全带 early_prefab_auto.lua / mod_auto.lua / preload_assets_auto.lua，部分带 sound_banks_auto.lua / test.lua）
> 配套：`柠版适配API文档.md` §21

## 何时查阅

- 适配/分析**新角色 Mod**（自建 prefab 角色）或**原版角色增强 Mod**
- 遇到角色 Mod 在柠版：角色贴图空白、鬼魂形态空白、手持武器空白、技能按钮不显示、角色专属背包/UI 异常

## 人物 Mod 两大类

| 类 | 代表 | 挂载方式 |
|---|---|---|
| 新角色（17） | 不灵小姐、乌拉拉、千年狐、卡尼猫、小小格温、小红帽蕾克、幽幽子、晓美焰、橘雪莉、沃尔：破碎织者、米塔、蟾宫神使玉兔、诅咒遗骸威尔顿、边狱公司以斯拉、雪露、风幻龙瑟尔泽、魔法少女小樱 | PrefabFiles + 角色 prefab（MakePlayerCharacter） |
| 原版增强（3） | 更好的阿比盖尔、最好的女武神、永远强壮的沃尔夫冈 | AddPrefabPostInit / AddComponentPostInit / AddPlayerPostInit |

## 新角色 prefab 标准模板

```lua
-- scripts/prefabs/whorl.lua（骨架，沃尔实证）
local MakePlayerCharacter = require "prefabs/player_common"
TUNING.GAMEMODE_STARTING_ITEMS.DEFAULT.whorl = { "shadowheart" }   -- 初始物品

local common_postinit = function(inst)   -- 客户端+服务端都跑：tags/minimap
    inst.MiniMapEntity:SetIcon("whorl.tex")
    inst:AddTag("weaver")
end
local master_postinit = function(inst)   -- 仅服务端：属性/组件/语音
    inst.starting_inventory = start_inv[TheNet:GetServerGameMode()] or start_inv.default
    inst.soundsname = "webber"           -- 复用原版语音
    inst.components.health:SetMaxHealth(TUNING.WHORL_HEALTH)
    inst.components.hunger:SetMax(TUNING.WHORL_HUNGER)
    inst.components.sanity:SetMax(TUNING.WHORL_SANITY)
    inst.components.combat.damagemultiplier = 1
    inst.OnLoad = onload
    inst.OnNewSpawn = onload
end
return MakePlayerCharacter("whorl", prefabs, assets, common_postinit, master_postinit, prefabs)
```

**固定伴生**：
- 鬼魂形态 `<name>_none.lua`（死亡/幽灵换装；whorl_none、lake_none、carney_none、mad_mita_none 等 15+ 实证）
- 角色注册：`PrefabFiles = {...}` + `AddModCharacter("uuz", "FEMALE")`（幽幽子实证）
- 专属背包/装备：`<name>_backpack` / `<name>_pack` / `<name>_bag`（buling_backpack、wiltonmod_pack、setsuro_backpack、ccs_bag）

## 原版角色增强模板

```lua
-- ① 改 TUNING 数值（更好的阿比盖尔）
TUNING.ABIGAIL_HEALTH_LEVEL1 = 150 * GetModConfigData("health")
AddPrefabPostInit("abigail", function(inst) ... end)

-- ② 改组件方法（永远强壮的沃尔夫冈）
AddComponentPostInit("mightiness", function(self)
    self.DoDec = function() end
    local old_onload = self.OnLoad
    self.OnLoad = function(self, data) if old_onload then old_onload(self, data) end ... end
end)

-- ③ 综合（最好的女武神）：AddPlayerPostInit + AddPrefabPostInit + AddRecipe + SkillTree
```

## 技能树（DST 官方 skilltreeupdater，无需额外适配）

- 技能树 prefab：`skilltree_<角色>.lua`（skilltree_uuz / skilltree_yutu / skilltree_wiltonmod / setsuro_skilltree 实证）
- 检查激活（女武神实证）：
```lua
if owner.components.skilltreeupdater ~= nil and
   owner.components.skilltreeupdater:IsActivated("wathgrithr_arsenal_spear_4") then
    inst.components.aoetargeting:SetEnabled(true)
end
```
- 自建跨端组件：`AddReplicableComponent("uuz_springvalue")`

## env 环境接管（角色 mod 通用头，12+ 实证）

```lua
GLOBAL.setmetatable(env, { __index = function(t, k) return GLOBAL.rawget(GLOBAL, k) end })
-- 之后 modimport("uuzmain/xxx") 分模块挂载（幽幽子 8+ 个实证）
```

## 柠版适配要点（已适配实证）

1. **动画三件套全量注册**（early_prefab_auto.lua 或 FW_PreloadAssets）：
   - 角色本体 `<name>.zip`
   - 鬼魂形态 `ghost_<name>_build.zip`
   - 手持 `swap_<武器>.zip`
   - 小红帽蕾克手工版示例：`FW_PreloadAssets(modname, { "anim/lake.zip", "anim/ghost_lake_build.zip", "anim/swap_wuqi.zip", "anim/lake1.zip", "anim/lake2.zip", ... })`
2. **FW_LoadPrefabs 替代 PrefabFiles**（小红帽蕾克实证）：
   `GLOBAL.FW_LoadPrefabs(modname, { "lake", "lake_none", "book_shu", ... })`
3. **加密/分片加载**（蟾宫神使玉兔实证）：`kleiloadlua` + `setfenv`，RunModFile 依次跑 `modmain_decrypted.lua` / `modclientmain.lua`。
4. **专属 UI/技能按钮**（不灵小姐实证）：`AddPlayerPostInit` → `MobileUI.ScheduleButtonMount(player)`；HUD 元素 `MobileUI.RegisterUI(widget, key, w, h)`。
5. **声音**：10 个已带 sound_banks_auto.lua（千年狐/格温/晓美焰/橘/米塔/玉兔/威尔顿/以斯拉/雪露/小樱）。
6. **按键/键盘事件**走 ModRPC（千年狐实证）：`AddModRPCHandler("wharang", "keyhandler", ...)`。
7. **纯增强 mod**（无 anim）无需纹理/early_prefab，只需 mod_auto + preload_assets。

## 排障速查

| 现象 | 排查点 |
|---|---|
| 角色本体/鬼魂/手持空白 | early_prefab_auto.lua 是否含 `<name>.zip` / `ghost_<name>_build.zip` / `swap_<武器>.zip` 三条 |
| 角色可选但进图白名 | PrefabFiles 是否被 FW_LoadPrefabs 正确接管；mod_auto asset_case_aliases 是否含角色资源 |
| 技能按钮/专属 UI 不显示 | 是否走 FW_RegisterModButton / MobileUI 挂载；注册时机是否在 UI 实例化后 |
| 加密 mod 卡加载 | RunModFile 的 kleiloadlua 路径是否与 mods/<mod名>/ 实际一致 |
| 原版角色增强无效果 | 是否 AddComponentPostInit 覆盖了组件方法且保留旧函数 |


## 按键技能 → 柠版按钮（工具 v1.4.23 自动，§20.23）

PC 角色 Mod 的按键技能（键盘触发）在手机端无法触发。工具自动扫描两类实证模式，
modmain 尾部注入 `FW_RegisterModButton`（`onpress` 复用原始 `SendModRPCToServer`）：

| 模式 | 写法 | 实证 |
|---|---|---|
| a) 控制键转发 | `OnControlDown` 内 `SendModRPCToServer(<rpc>, KEY_X, true, nil)` | 千年狐（R 键） |
| b) 键盘钩子 | `function self:OnRawKey(key, down, ...)` 内 `key == X and down → SendModRPCToServer(<rpc>)` | 晓美焰（SKILLKEY→timepause） |

**去重**（图标按钮已有对应键盘常量 → 不重复注册）：
- 同 RPC 表达式只注册一次；
- Mod 已有 `FW_RegisterModButton` 且注册块含同 RPC（`["x"]`→`.x` 规范化比较）→ 跳过
  （晓美焰实证：时停/换弹已手工注册 HOMURA_TIMEPAUSE/HOMURA_RELOAD → 自动跳过去重）；
- 注入幂等标记 `__fw_keybutton`。

**跳过保护**：RPC 为纯局部变量名（无 `.`/`[` 前缀）→ 跳过；按键直接调本地函数
（如晓美焰 `DoAutoReload`）→ 不提取（该 mod 通常已手工注册按钮）。

**CLI**：`--no-key-buttons` 跳过；GUI 复选框「角色技能按钮」。