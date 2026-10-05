---
name: dst-mod-dev
description: >
  饥荒联机版（Don't Starve Together）Mod 开发与排障技能。覆盖 Bug 排查与修复、
  Mod 移植/兼容性适配（DS→DST、旧版→新版、PC→柠版/手机端）、Mod 代码结构分析
  与功能解读、新 Mod 开发（Lua 脚本、DST API、预制物/组件/状态图）、UI 界面修改
  （HUD/Widget/Screen）。
  当用户咨询《饥荒》联机版 Mod 制作、Mod 崩溃报错、Mod 移植、Mod 代码分析、
  Mod 功能修改、UI 改动、Lua 脚本问题、DST API 使用，或遇到柠版/手机端贴图空白、
  纯黑块、卡加载页等适配问题时使用。
  人物/角色 Mod（新角色、原版角色增强、技能树、角色专属 UI）适配与分析也进入本技能。
  不使用：纯游戏玩法/攻略咨询（与 Mod 无关）、非 Mod 向的通用 Lua 教学、
  其他游戏（非 DST）的 Mod 问题。
version: 1.12.0
---

# DST Mod 开发与排障

> 整理：神似 ｜ 版本：1.12.2（v1.12.2 增量：★v1.10.1 的 bit9 优化**真正落地到代码**（2026-10-05）——此前 SKILL.md 已实证"ASTC 单 mip 必须 0xFFF02380（bit9=1）是柠版 2.1.1 Mali 管线必需位"，但主工具 `convert_bytes` 实际写头仍为 0xFFF02180（bit9=0）；v1.6.3 修复为 `| (1 << 9)`，py 级（fm.tex/esctemplate.tex→0xFFF02380 PASS）+ **exe 级双重实测**（临时 console 版 exe 转换 fm.tex → 0xFFF02380 bit9=1 PASS）；**exe 重建**：顶层 `柠版适配工具.exe` 从 9/15 的 v1.6.0 旧快照重建为 v1.6.3（PyInstaller 6.22.2，内嵌最新主工具）。v1.12.1 增量：★柠版适配工具整理（2026-10-05）——工具包唯一权威目录 `C:\Users\Longe\下载\工具转换\`（主工具 `柠版mod转换工具/dst_mobile_adapter.py` **v1.6.2**），技能副本 `tools/dst_mobile_adapter.py` 已同步 v1.6.2（206416B，曾落后 18KB 教训：改工具后必须双端同步）；**原版图集静态表自动选新：默认加载 `vanilla_atlas_jh210.json`（2.1.0 APK，6622 region）优先，jh142（1.4.2，6187 region）兜底，新增 `--atlas <json>` 显式指定**（此前写死 jh142，更新 APK 图集/region 位置差异会漏修）；新增 `工具转换/README.md` 工具包索引。v1.12 增量：★虚空回廊（Void Corridor）模式适配全案 §7.37——出生状态机靠齐端游（选角信号→全员就绪→6 秒倒计时→统一放行）、手机端服务器"不 tick"铁律（DoPeriodicTask/DoTaskInTime 不执行 → 实时锚点+客户端 run_start RPC 周期驱动三段推进）、客户端 sync handler 必须写回 client_state（v7.22 投票不显示根因）、PC 自定义全局缺失 → modmain 补 GLOBAL.FindPlayer（v7.25 客机投票后主机闪退）、皮肤恢复校验角色 prefab（v7.23 选机器人误套艾莉西亚）、AddClassPostConstruct self 作用域坑（v7.24 加载即崩）、luaparser BOM/括号误报 → LuaJIT loadfile 权威校验、SendModRPCToClient 必须带 userid+剔除 performance、跨 instance 不共享 GLOBAL、三面板 FW_RegisterEditable 适配层（非按钮注册）；详见 `柠版适配API文档.md` §32.11。v1.11 增量：★虚空异界（泰拉）整包适配好版全案 §7.36——轮盘施法三型统一模板（A 拖动持续施法/B 拖动选点松开施法/投掷周期索敌）、mod 角色皮肤选择三件套（ValidateSpawnPrefabRequest hook + SendSpawnRequestToServer 持久化 + CheckOwnership 放行，修正"引擎层校验不可注入"错误结论）、背包注入物品栏下方终解（删除独立注入文件整合进 tr_inventory_bar + 底板不拉伸铁律 + FeiyingStateKey 状态签名闸门）、modmain Prefab 包装自动补 ATLAS_BUILD、worldgen 专属游戏模式注入；详见 `柠版适配API文档.md` §32。v1.10.2 增量：柠版声音「全静音」清单格式全案——`sound_banks_auto.lua`/`mod_auto.lua` 必须 LF 无 BOM（手机端 31/31 正常发声 mod 全 LF 实证），CRLF 致框架按需声音加载器解析失败 → 全装备无声，见 §7.35；柠版适配API文档 v1.7 去重合并（5854→4057 行，新增 §31 声音清单格式规范）。v1.10.1 增量：①泰拉（虚空异界·泰拉 2526778484）DaxSg Lua 解密流程沉淀——算法=整文件倒序+固定替换表（非 VM 字节码/XOR），工具 `tools/terra_daxsg_decode.py`（单文件/批量，内置 BYTE_MAP）+ `tools/mapping_best_effort.csv`（完整映射表）+ `tools/README-daxsg-terra.md`（解密+重组+9bit+路径修正全流程，2026-09 群友逆向实证，方便下次解密复用）；②dst_mobile_adapter.py 纹理头 9bit 优化：ASTC 单 mip flags 默认改 0xFFF02380（bit9=1，原 0xFFF02180）——柠版 2.1.1 成功 mod 更多料理 v3.44/AIP v3.40 全部 tex（含 anim zip 内部）逐字节实证 bit9=1 是 Mali 管线必需位（minimap §7.20 同标准），顶层 tex 与 zip 内 tex 同一 convert_bytes 自动覆盖。v1.10 增量：融入 skills-手机版.zip 46 份契约技能，新增 `references/api_contract_map.md`——46 领域契约要点 + 精确 file:line 源码锚点（Android/Playdigious 树）+ 关联 dst-mod-creater api-* 笔记；dst_api_quickref.md 顶部补平台前提速查与锚点定位入口。v1.9.9 已融入 dst-mod-creater v1.2 配套知识库：官方源码 API 笔记 13 篇/8+7 模板/15 工具/11 mod 笔记，见『配套知识库 dst-mod-creater』；丰耘秘境实战沉淀见 §7.30：Klei 加密皮肤删除/皮肤全解锁/图鉴收集与图标/Replica 时序；猪镇房子柠版 nil 防护全景见 §7.31：GLOBAL strict 无自引用/setfenv 前补环境/ToolUtil 缺失/构造 nil 参数/Replica 时序/221 处扫描评估法；柠版打包规范实证沉淀：zip 内套 mod 名文件夹 + 全正斜杠 + compresslevel=6，见 §8；工具 v1.5.2：防御规则新增 SpawnPrefab 链式调用判空——行首 SpawnPrefab('x').Method 单行链式拆两行 + if __sp then 判空，注释/赋值/已判空跳过、__sp 幂等；心之钢 lavaarena_firebomb_explosion（Forge 专属 prefab 柠版缺失）→ nil 索引崩溃实证；v1.5.1 rmtree 安全守卫与 §22.6 七项改进保留；传奇武器附魔强化闪退全案见 §7.33：inventoryitem SetPristine 时序（前置组件=前端 Spawn 即崩）/AddInventoryItemAtlas 在 prefab 文件内=not callable/图标 fallback 空纹理=引擎级闪退（无 Lua error）/多 mod 扩展 player_classified 冲突；**柠版跃迁/传送通道全案见 §7.34（v14.52-v14.67 终解）：ThePlayer 状态机组件链三级全 nil→GoToState 不可行；传送通道选型=普通 Mod RPC 单通道终选（DoTouchSpecialAction 内置限距≈150/ExecuteConsoleCommand 仅主机/SendRemoteExecute 仅客机管理员）；消耗复用 hmrblinker:BlinkIn/BlinkOut（onblinkin 回调=恐怖粘液+耐久+特效）；客户端动画 AnimState+DoPeriodicTask 轮询 AnimDone；strict 局部变量自引用坑=先声明后赋值；兜底 return {} 卡全图交互铁律**）

## 何时使用 / 何时不用（触发边界）

| ✅ 命中任一即进入本技能 | ❌ 回退通用回答或其他技能 |
|---|---|
| 咨询/报错涉及 DST Mod：制作、崩溃报错、移植、代码分析、功能修改、UI 改动、Lua/DST API | 纯游戏玩法、攻略、剧情咨询（与 Mod 无关） |
| 柠版/手机端适配：贴图空白、纯黑块、卡加载页、闪退、配方失效、触摸/拖拽失灵 | 通用 Lua 编程教学（与 DST 无关） |
| Mod 间兼容/冲突排查、多 Mod 同开异常 | 其他游戏（非 DST）的 Mod 问题 |

## 工作流程

### 1. Bug 排查与修复（主要）

按以下顺序推进：

1. **定位错误**：让用户提供 `client_log.txt` / `server_log.txt` 中的报错堆栈，或从用户描述中提取崩溃场景
2. **匹配模式**：查阅 `references/common_bug_patterns.md`，找到对应错误类型的根因和修复方案
3. **定位代码**：在用户提供的 Mod 代码中搜索报错涉及的函数/组件/预制物
4. **给出修复**：提供具体的代码修改（替换哪段、改成什么），并说明原因
5. **验证建议**：告知用户如何验证修复（查看日志、控制台测试、多人测试）

**常见错误速查**：
- `attempt to index a nil value` → 空引用，加组件存在性检查
- `attempt to call method` → API 变更或方法不存在，查版本差异
- `stack overflow` → 事件循环/递归，加守卫标记
- 客机看不到变化 → 缺少网络同步，改用 net 变量或 Mod RPC
- 旧存档崩溃 → OnLoad 未处理旧格式，加版本迁移

### 2. Mod 移植 / 兼容性适配（主要）

1. **确认源和目标**：DS→DST？旧版 DST→新版？PC→柠版/手机端？某个 Mod 适配另一个 Mod？
2. **一键工具优先**：PC→柠版/手机端适配，先用 `tools/dst_mobile_adapter.py`（纹理转换 + 资源副本 + 自动文件[含 tile_preload_auto.lua，levels/ 地形预加载] + 兼容层注入 + 打包，详见 `柠版适配API文档.md` §20）。工具无法覆盖的个性化问题再走下述手工清单。
3. **按清单检查**：使用 `references/mod_porting_guide.md` 中的移植检查清单逐项核对
4. **柠版/手机端适配**：遇到贴图空白/纯黑块/卡加载页/闪退/配方失效，先查
   `references/mobile_porting_guide.md`（KTEX DXT5→RGBA、文件编码、hook 失效、客户端标签）；
   **动画空白（手持/装备/皮肤/地面）第一排查点 = `early_prefab_auto.lua` 是否全量注册
   所有 build**（anim/ 每个 zip 一条；只注册 prefab 主动画必然 swap/皮肤空白且静默无报错）。
   大 Mod 用 `--native` 模式，工具自动生成全量 early_prefab（见 `柠版适配API文档.md` §20.0/§20.14）；
   **人物/角色 Mod** 额外查 `references/character_mod_guide.md`（角色本体+鬼魂+手持三件套动画、
   FW_LoadPrefabs、技能树、专属 UI/按钮，见 `柠版适配API文档.md` §21）
5. **重点改造**：
   - 所有预制物添加 `Network` 组件 + `SetPristine()`
   - 区分主机/客机逻辑（`TheWorld.ismastersim`）
   - 需要客机显示的数据加网络变量
   - 玩家操作改用 Mod RPC
   - OnSave/OnLoad 加版本号处理旧存档
6. **冲突兼容**：使用 `AddPrefabPostInit` 而非覆盖预制物，保存原函数再扩展

### 3. Mod 代码结构分析与功能解读（次要）

1. **先看整体结构**：查阅 `references/mod_structure.md` 理解标准目录结构
2. **入口分析**：从 `modinfo.lua`（配置/兼容性）→ `modmain.lua`（挂载点）开始
3. **逐层深入**：预制物（prefabs/）→ 组件（components/）→ UI（widgets/）→ 状态图（stategraphs/）
4. **功能总结**：按"实现了什么功能 → 通过什么机制 → 关键文件和函数"的结构输出

### 4. 新 Mod 开发（次要）

1. **确定需求**：明确要添加的物品/生物/功能/UI
2. **搭建结构**：参考 `references/mod_structure.md` 创建标准目录和 `modinfo.lua` / `modmain.lua`
3. **编写代码**：
   - 预制物/组件模板参考 `references/mod_structure.md`
   - API 调用参考 `references/dst_api_quickref.md`；拿不准"某个功能该用什么 API"时，
     先查 `references/api_usage_statistics.md`（100 个实装模组的 API 使用排行）和
     `references/real_mod_patterns.md`（真实模组实现手法 + 可直接套用的代码样例）；
     API 的**契约与精确源码锚点（file:line）**查 `references/api_contract_map.md`
   - 需要网络同步时参考 `references/mod_porting_guide.md` 的网络同步章节
4. **配置与字符串**：添加配方、字符串、配置选项

### 5. UI 界面修改（次要）

1. **确定修改类型**：添加 HUD 元素？修改已有 HUD？创建新 Screen？自定义 Widget？
2. **查阅指南**：`references/ui_modification_guide.md` 中有完整模板和场景示例
3. **挂载方式**：HUD 用 `AddClassPostConstruct("screens/playerhud", ...)`，新 Screen 用 `TheFrontEnd:PushScreen()`
4. **数据绑定**：UI 只从网络变量读取数据，不直接访问组件

### 6. 新版柠版内置 mod 库已验证 API（v1.5 增量速查）

> 来源：新版柠版（jh联机模组版 1.4.2）APK 内置 124 个已适配 mod 全量扫描，详见 `柠版适配API文档.md` §22。
> 适用：新 Mod 适配时优先用这些**已验证实装**写法，减少试错。

- **FW_RegisterAction(mod, id, {keycode, keyboard_phase, character, onpress(player,source), ondown/onup})** —— 按键动作注册，`source=='touch'` 区分触屏；与 `FW_RegisterModButton({key=同id, reuse_action=true})` 成对 = 按键技能→触屏按钮标准模式（橘雪莉/卡尼猫/风幻龙/行为学实证，13 处调用）
- **FW_RegisterCharacter(mod, {prefab, register=AddModCharacter, gender, name, title, health, hunger, sanity, skins})** —— 角色入列三件套之一（+ FW_LoadPrefabs + FW_PreloadAssets），自动写 TUNING + MODCHARACTERLIST（小红帽蕾克/橘雪莉实证）
- **FW_CancelLifecycle(mod, player, task_id) / FW_DiagnoseLifecycle(mod)** —— 生命周期任务取消/诊断；配合生命周期重载 `FW_DoTaskInTime(mod, player, 'task_id', delay, cb)`（常用智能锅分帧配方生成实证）
- **FW_UnregisterEditable(widget)** —— 反注册旧 editable root（Rebuild 前必调，防重复注册；艾莉娅/小地图面板实证）
- **FW_IsActionButtonPoint(x,y)** —— 自定义世界触摸时排除框架按钮区（触屏交互加强版实证）
- **触摸管线四件套**：`controller.OnTouchStart/End/Cancel` hook + 原生长按 `OnTouchLong(id)` + 双指手势 `OnGesture(theta,dist,state)` + `wasLongTouch`/`IsVirtualStickTouched()`；全局用 `TheInput:AddTouchStart/Move/EndHandler`；屏幕坐标用 `TheSim:GetEntitiesAtScreenPoint`/`ProjectScreenPos`（触屏交互加强版/快捷宣告/基地投影实证）
- **mod 自报能力表**：`rawset(G, '<MOD>_MOBILE_V140'/'<MOD>_MOBILE_COMPAT', {...})` 上报移动端能力/容器几何，框架 autotest 读表断言（连锁采集/储藏室/可升级箱子等实证）
- **FW_RegisterModButton 必传 `character` 字段**（防跨角色按钮泄漏）；`onrelease`/`show_in_edit_mode`/`reuse_action` 两段式技能必用；返回 `ok, detail`
- **FW_RegisterRangedWeapon 扩展**：`require_equipped=false`（坐骑/非手持技能）+ `reticule_directional`（方向线）+ `deadzone` + `resolve_target`/`validate_target`（驯服考拉象/绯/科加斯实证）

## 参考文件导航

| 文件 | 内容 | 何时查阅 |
|------|------|----------|
| `references/common_bug_patterns.md` | 常见 Bug 模式、根因、修复代码、排查流程 | 任何报错/崩溃/异常行为 |
| `references/mod_porting_guide.md` | DS→DST 移植步骤、API 变更对照、网络同步改造、存档兼容、检查清单 | Mod 移植、版本适配、冲突兼容 |
| `references/dst_api_quickref.md` | 全局对象、实体方法、常用组件、事件、任务、网络 API、配方、UI 基础、挂载点 | 写代码时查 API 用法 |
| `references/api_contract_map.md` | **API 契约索引（v1.10 新增）**：46 领域契约要点 + 精确到 file:line 的源码锚点（Android/Playdigious 手机版树）+ 关联 dst-mod-creater api-* 笔记；含平台前提速查 | 拿不准 API 契约/源码锚点、平台门禁、版本差异定位 |
| `references/mod_structure.md` | Mod 目录结构、modinfo/modmain 详解、预制物/组件/Widget 模板、资源组织、配置系统 | 新建 Mod、分析代码结构、理解文件组织 |
| `references/ui_modification_guide.md` | UI 架构、HUD 修改、Widget/Screen 模板、常见场景、动画、输入、分辨率适配 | 任何 UI 相关修改 |
| `references/api_usage_statistics.md` | 100 个实装模组的 API 使用统计（挂载点/网络/组件/进阶手法按使用率排序） | 选 API、判断可行性、评估兼容性 |
| `references/real_mod_patterns.md` | 真实模组实现手法：网络同步、RPC、新动作、HUD/Screen、技能树改造、Replica 组件、存档、输入、相机、地形、移动端框架 | 实现复杂功能、大模组架构、移动端（柠版）模组适配 |
| `references/mobile_porting_guide.md` | 柠版/手机端适配专项：KTEX 格式与 DXT5→RGBA 转换、资源预加载清单、文件编码(BOM+CRLF)、ModManager.RegisterPrefabs hook 失效、客户端标签缺失等 | PC→柠版/手机端适配、贴图空白/纯黑块/卡加载页/闪退排查 |
| `references/character_mod_guide.md` | **人物/角色 Mod 适配专项**：新角色 MakePlayerCharacter 模板、鬼魂形态/手持动画三件套、原版增强（AddComponentPostInit/TUNING）、技能树 skilltreeupdater、env 接管、加密分片、20 个已适配人物 Mod 实证 | 新角色/原版角色增强 Mod 适配、角色贴图空白/技能按钮不显示排查 |
| `tools/dst_mobile_adapter.py` | 柠版一键适配工具（**v1.6.3**，2026-10-05 已同步主工具包；权威版本在 `C:\Users\Longe\下载\工具转换\柠版mod转换工具\dst_mobile_adapter.py`——**改工具先改主包，再同步本副本**）：**ASTC 头 bit9=1（0xFFF02380）已落地**（v1.6.3，py+exe 双实测 PASS）+ 默认 native 纯原生模式 + 全量编码统一 + worldgen 链 _G 别名 + 原版图集修正静态表（**v1.6.2：jh210/2.1.0 自动优先、jh142 兜底、`--atlas` 显式指定**，见 §7.17）：纹理转换（DXT5/RGBA→ASTC 8x8，**并发** min(CPU,6) 可调 `--workers`）、资源副本、自动文件生成（**early_prefab_auto.lua 全量 build 注册 = 柠版动画唯一有效通道**，anim/ 每个 zip 一条，英雄联盟武器 404 条含 109 swap 式；native 模式默认不注入已废弃的 Assets 补缺 / FW_PreloadAssets，`--with-legacy-injects` 才保留）、strict 安全兼容层注入（Assets/AddRecipe2 等一律 rawget/传参）、Lua 5.1 兼容 post-fix（unpack(arg)→unpack({...}) + vararg 函数注入 local arg={...}）、**通用规则库（不依赖 per-mod 补丁，自动执行：①nil 防御 fx/target 判空 + SpawnPrefab 链式调用判空（v1.5.2，e) 段：行首 `SpawnPrefab('x').Method...` 单行链式 → 拆两行 + `if __sp then ... end`，注释/赋值/已有判空跳过，`__sp` 幂等；心之钢 Forge 专属 prefab `lavaarena_firebomb_explosion` 缺失→nil 索引崩溃实证） ②滚动条 `TheFrontEnd.lastx/lasty` 兜底+SetOnDown 按下点记录 ③playerhud 面板型自定义 widget → FW_RegisterModButton 柠版按钮自动注册，**带 icon/pos/scale 样式转移 + 原版 logo 隐藏（`__fw_logo_hide`）+ 面板内 back/logo 互切归一（`__fw_back_hide`）**，§20.17.1 ④`ModManager.RegisterPrefabs` hook → AddSimPostInit 延迟执行转换，§20.17.2）**、**`--touch-scroll`（扫描自定义滚动类并在类文件内注入柠版触摸滚动，触摸双处挂载 black+Scroller 自身 + SetDragable，**滚动调用链兜底 `Scroll` 方法**——ScrollableList 系只有 Scroll(步数)，§20.17.4**，AIP §20.15/§20.15.3）**、**ScrollableList 系拖动重写（v1.4.5 自动执行无开关：标准 ScrollableList 原版 DoDragScroll 嵌套深坐标换算错乱→拖动滑块无效，LOL 图鉴左侧实证；注入手工版同构——SetOnDown 立即 LockFocus(true)+dragging + Scroll 开头 `_target_offset=nil` 打断残留插值 + DoDragScroll 重写（手指 y→滑轨比例→ScrollToRatio）+ ScrollToRatio/OnUpdate 方法（每帧 ±1 步平滑逼近），`__fw_drag_rewrite` 幂等，§20.18.3c）**、**角色按键技能 → 柠版按钮（v1.4.23，独立可选项 `--no-key-buttons` 跳过；扫描控制键转发/键盘钩子两类按键技能 → modmain 注入 FW_RegisterModButton，onpress 复用原始 SendModRPCToServer；去重：同 RPC 只注册一次 + 已有图标按钮注册块含同 RPC 跳过去重，`__fw_keybutton` 幂等，§20.23）**、**v1.4.24/25：按键技能扫描补全四通道；按键技能扫描补全四通道（c) OnRawKey 反序 KEY_X==key / d) AddKeyDown/UpHandler 直连 / e) 别名回填 local X="KEY_Y" / f) 鼠标键 MOUSEBUTTON_* / g) 配置键 GetModConfigData→modinfo default，统一 add_found 去重）**、**KTEX flags 高位对齐（2878 tex 实证：ASTC 单 mip=0xFFF02380（v1.6.3 bit9=1）、RGBA=0xFFF02040，bit20-31=0xFFF 工具链前缀）**、**tile_preload_auto.lua 生成（v1.4.26：检测 levels/ 目录 → `.tex`=IMAGE / `.xml`=FILE 全量预加载清单，无 BOM + CRLF，同 sound_banks；棱镜/永不妥协/荔只只物语手工版同款，缺失→自定义地形贴图空白/紫块，§20.25）**、**v1.5.0 七项改进（§22.6 已实施）：①FW_RegisterAction 成对注入（按键技能四通道 → `FW_RegisterAction(keycode/keyboard_phase/character/onpress(player,source))` + `FW_RegisterModButton(reuse_action=true)`，`_has_action` 判空回退纯按钮，幂等 `__fw_keyaction`，§20.26）②生命周期任务重写（`X:DoTaskInTime/DoPeriodicTask` + 成对 `task:Cancel()` → `__FW_LIFE_TASK/PERIOD/CANCEL` 框架托管 + pcall 回退原生；词边界回调式替换防子串误伤，`--no-lifecycle` 跳过，§20.27）③触摸管线 hook（`__FW_TOUCH_GUARD/__FW_TOUCH_ENTITIES` + playercontroller 补 OnTouchLong/OnGesture 只补 nil，`--no-touch-pipeline` 跳过，§20.28）④FW_RegisterCharacter 自动生成（AddModCharacter 未 FW_RegisterCharacter( 时注入，stats 读 TUNING 缺省 150，幂等 `__fw_registerchar`）⑤tile_preload_extra.lua 合并（levels/ 手写清单去重并入）⑥按钮 character 字段补全（find_character 三模式扫描防跨角色泄漏）⑦去重收集只取注册块内部 + AddClassPostConstruct 双引号 playerhud 识别（冒烟 24/24 PASS）**、**v1.5.1 输出目录安全守卫（严重事故修复，2026-09-15：保存位置误指 Downloads 根导致全目录被 rmtree 清空）：`rmtree` 仅允许"本工具输出特征名"目录（`*-柠版适配版` 后缀）；`--out` 已存在且非本工具输出 → 改在其下新建 `<modname>-柠版适配版` 子目录输出，绝不整目录删除；即使匹配特征名仍校验不得等于源目录/源父目录/磁盘根（三场景冒烟验证：哨兵保留/子目录输出/特征名覆盖重建全 PASS）**、**`--simulate-key` 可选：onpress 优先 FW_SimulateKey（判空+pcall，不可用回退 RPC；FW_AutoAimFromKey 未实装不可用）**、打包（用法见 `柠版适配API文档.md` §20/§20.0） | PC→柠版/手机端适配的批量化第一步 |
| `tools/astcenc/astcenc.exe` | ASTC 编码器（v5.7.0），`dst_mobile_adapter.py` 自动调用 | 纹理转 ASTC 8x8 |
| `柠版适配API文档.md`（v1.8，位于 `C:\\Users\\Longe\\下载\\工具转换\\`） | 全量 API 手册 + 工具章节；**§22 = 新版柠版 124 mod API 增量**（新 API/字段扩展/机制模式/工具改进规划 §20.26-28）；**§32 = 虚空异界（泰拉）整包适配好版全案**（轮盘施法三型模板/皮肤选择三件套/背包注入终解/Prefab ATLAS_BUILD 包装/worldgen 游戏模式注入，2026-10-03） | 查 FW_* API 用法、新 API 与已验证实装写法、机制沉淀、泰拉整包模式复用 |

| `dst-mod-creater/`（配套技能包，v1.2 全量融入） | 官方源码 API 笔记 13 篇（带 file:line 引用）、8 可运行模板 + 7 官方模板（含人物 esctemplate 标准）、KTEX/SCML/混淆解密工具 15 个（tools/）、10 个大型 mod 设计笔记（mod-notes/ 含丰耘秘境 mod-fengyun.md）、美术参考样本（assets/ 70+ 张） | 查 API 源码依据、拿模板起步、逆向/纹理工具、参考大型 mod 设计 |

## 配套知识库 dst-mod-creater（v1.2 全量融入）

本技能已内置完整 dst-mod-creater 技能包（子目录 `dst-mod-creater/`，MIT 许可，离线可用，635 文件 / 36MB）：

- **API 笔记**：`dst-mod-creater/references/api-*.md`（13 篇：组件/prefab/AI/世界生成/UI，全部带官方源码 file:line 引用）——写代码查 API 的首选依据
- **快速入门**：`dst-mod-creater/references/00-quickstart.md`（30 分钟从零跑通一个 mod）
- **美术管线**：`dst-mod-creater/references/art.md`（KTEX 格式破解 DXT5/RGBA8、色板、XML atlas、动画规范）+ `tools/`（dst_tex_analyze.py 等 15 个工具）
- **人物开发标准**：`dst-mod-creater/references/character-esc.md` + `official-templates.md`（20 部位规范表、SCML/anim.bin 逆向、皮肤、生成工作流）
- **可运行模板**：`dst-mod-creater/templates/`（modinfo/modmain/turf/building/creature/item/worldgen/ui 8 个 + official/ 7 个 Klei 官方模板 verbatim 副本）
- **大型 mod 实战笔记**：`dst-mod-creater/references/mod-notes/`（11 篇：棱镜/热带体验/神话书说/Uncompromising/道诡异仙/登仙/丰耘秘境/山海秘藏/万物书/地府，含 mod-fengyun.md 丰耘秘境笔记）
- **混淆逆向工具**：`dst-mod-creater/tools/daogui_*.py`、`lol_dump.py`、`probe_require.py`（道诡异仙三层加密实战验证）；**泰拉 DaxSg 倒序+替换解码**：`tools/terra_daxsg_decode.py`（单文件/批量 `--dir`）+ `tools/mapping_best_effort.csv`（完整字节映射表，cipher→plain+置信度）+ `tools/README-daxsg-terra.md`（全流程：算法真相/61 模块加密分布/明文清单/重组+9bit+路径修正/判据速查——2026-09 泰拉 2526778484 实战，区别于 VM 字节码/XOR，勿混用）

用法：做新 Mod → 00-quickstart + 选模板；查 API → api-*.md；美术/纹理 → art.md + tools/；参考大型 mod 设计 → mod-notes/。

## 关键原则

1. **主机/客机分离**：所有修改组件数据的代码必须在 `TheWorld.ismastersim` 守卫内；客机只读网络变量
2. **安全访问**：访问 `inst.components.xxx` 前必须检查组件是否存在；`FindEntity` 等返回值必须判空
3. **PostInit 优于覆盖**：用 `AddPrefabPostInit` / `AddComponentPostInit` 修改已有内容，不覆盖整个文件，避免与其他 Mod 冲突
4. **网络同步**：任何需要客机看到的数据变化必须通过 `net_xxx` 变量或 `Mod RPC` 同步，不能直接改客机状态
5. **存档兼容**：OnSave 带版本号，OnLoad 处理旧格式迁移；移除组件时清理旧数据
6. **给可操作的代码**：用户偏好直接可操作的技术指导，给出具体文件、具体行、替换前后的代码，而非泛泛而谈
7. **先复现再修复**：让用户提供报错日志和复现步骤，不要凭猜测改代码
8. **不要反复加 print 让用户来回测**：用户在手机上测一次成本极高（打包→装→进游戏→操作→回传日志）。
   定位 bug 时先静态分析代码+原版源码+APK 源码，把所有假设一次性想清楚，再改代码。
   **最多加一轮调试 print**；一轮没定位到就停下来重新分析代码逻辑，而不是加更多 print 让用户再测一轮。
   用户明确说"不要调试了"时立刻停止 print，基于已有证据直接给修复方案。

## 排查时需要向用户索取的信息

- 完整的报错日志（`client_log.txt` 中 error 附近的堆栈）
- Mod 版本和 DST 游戏版本
- 复现步骤（做了什么操作后出现问题）
- 是否只在主机/客机/多人时出现
- 是否与其他 Mod 同时启用（二分法确认冲突）
- 相关代码文件（如果用户能提供）

## 8. 柠版 mod 打包规范（v1.9.1 实证沉淀，勿再错）

> 依据：dst_mobile_adapter.py 打包逻辑（L3907-3918）+ 使用说明.txt「四、安装到柠版」+ 更多料理/英雄联盟武器/成就三包实测（2026-09-20）。

**格式铁律（交付前逐条核对）**：
1. **zip 内套一层 mod 文件夹**：顶层目录名 = modinfo 解析的 mod 名（**不带** "-柠版适配版" 后缀——英雄联盟武器/更多料理实证；成就 zip 带后缀是其 modinfo name 本身带后缀的特例）。柠版按文件夹内 modinfo.lua 识别 mod，文件夹名不影响安装。
2. **zip 文件名**：`<mod名>-柠版适配版.zip`（输出到 mod 目录同级或用户指定目录）。
3. **路径全正斜杠**（zip 规范要求；反斜杠条目安卓解压有风险）。
4. **压缩级别**：DEFLATED `compresslevel=6`（与工具一致；Fastest 约大 1.3MB）。
5. **安装方式**：解压 zip → 拷贝内层 mod 文件夹到柠版 mods 目录。

**推荐实现（Python，与工具输出 100% 一致，条目自动正斜杠）**：
```python
import zipfile, os
target = r"<mod源目录>"; modname = "<mod名>"          # 顶层目录名 = mod 名
outzip = os.path.join(os.path.dirname(target.rstrip('/\\')), modname + '-柠版适配版.zip')
if os.path.exists(outzip): os.remove(outzip)
with zipfile.ZipFile(outzip, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for r, dirs, files in os.walk(target):
        for f in files:
            p = os.path.join(r, f)
            z.write(p, os.path.join(modname, os.path.relpath(p, target)))  # ZipInfo 自动 replace(os.sep,'/')
```

**PowerShell 替代（两坑已实测踩过，勿用 `[ZipFile]::CreateFromDirectory`）**：
- ❌ `CreateFromDirectory`：Windows .NET 生成**反斜杠**条目 + 自动丢外层文件夹名。
- ✅ ZipArchive 逐文件 CreateEntry：`rel = folderName + "/" + $file.FullName.Substring($tmpDir.Length + 1).Replace('\\','/')`——**必须手动补 `folderName + "/"` 前缀**，否则丢顶层目录。

**体积预期**：源 75.9MB → compresslevel=6 约 47.1MB（anim/zip + fsb 音频 + tex 纹理本身已压缩，外层压不动；可压缩仅 .lua/.xml 文本）。**压缩率 60-65% 正常，不是打包遗漏**。

**验证清单（交付前必查）**：①条目数 = 源文件数 ②首条 = `<mod名>/...` ③含反斜杠条目 = 0 ④修复内容在 zip 内读回确认（如 `HOF_DEBUG_MODE = false`、挂载语句）。

## 7. 大 Mod 适配沉淀（更多料理 Heap of Foods 实战，v3.25 实测能进）

> 适配对象：创意工坊 2334209327（~1220 文件/~500 prefabs/85 食谱/酿造+腌制/钓鱼/岛屿）。
> 全程用户实测：图标黑 → 闪退 → 卡加载 → 能进；以下为**可复用机制**，细节见 `柠版适配API文档.md` §23。

### 7.1 ★ modimport 与 require 实例隔离 → GLOBAL 共享表

**现象**：大 Mod 的"每日推荐菜谱固定不变 / 配方计数 0/N / 手册打开 pairs(nil)"系列 bug 同源。
**根因**：柠版 modimport 通道与 require 通道**不共享文件缓存** → 两个独立文件实例 → 数据表 nil。
**修复**：共享数据表挂 `rawset(GLOBAL, "__<MOD>_<TABLE>", ...)`，读取方 `rawget(GLOBAL, ...) or {}`（strict 安全）。
**特征**：报错在 UI 打开时（非启动）+ 表 nil + 多文件互 require/modimport。

### 7.2 ★ AddCookerRecipe 第三参 / cookbook_atlas / no_cookbook

- 第三参 true → `cookbook_category="mod"`；false/缺省 → 强制覆盖 `recipe.cookbook_atlas="images/cookbook_<锅>.xml"`（柠版无此资源 → 开菜谱书崩溃）；
- `recipe.no_cookbook=true` → 跳过菜谱书但照常进锅具烹饪表；
- 适配：modmain 注入防御 hook 自动补 true；自制锅具菜谱用 no_cookbook + 不带第三参（原版食物不混入模组页）。

### 7.3 ★ init_postinit.lua 改表必须整体重建

正则替换单表（非贪婪 `{...}`）会**吞掉后续 MAP/PREFABS 表** → pairs(nil) 刷屏 → 卡加载（三连实测教训）。
铁律：多表串联文件任何单表修改 = 拼接全部表整体重建；每条目 pcall + 失败打印，单文件失败不卡加载。

### 7.4 strict 环境 GLOBAL 字段裸读 → rawget

柠版 strict.lua 对**不存在的 GLOBAL 字段**报 `variable 'xxx' is not declared`（不是 nil）。
`local x = TheFishRegistry` 直接抛错 → `local x = rawget(GLOBAL, "TheFishRegistry")` + 判空。
区分：**存在**的 GLOBAL 成员（TUNING/TheWorld/SpawnPrefab）可裸读；**不确定存在**的（mod 注入全局/跨文件单例）一律 rawget。

### 7.5 大入口模块拆分恢复

主模块 require 8 个子模块 → 柠版整块 require 有 not declared 风险 → **禁用整个入口模块 + 子模块逐个 pcall(require) 恢复**（崩溃风险低→功能价值高排序）；util_luck 这类有纯概率兜底的优先。

### 7.6 汉化大表卡加载 → 精简表

639KB 全量汉化表实测卡加载 → 98KB/1330 键精简表正常。保留玩家可见键（物品/配方/UI/台词/地皮）+ 手工补新内容键；角色个性梗可留原文。

### 7.7 postinit 分级恢复 + 审计脚本

100-200 个 postinit 文件：已加载（pcall 全量）→ 遗漏（brains/components 存在但未进清单，按核心玩法>岛屿>跨 mod 兼容分级补）→ 暂缓（map/terrain 世界生成、setfenv 全局接管，记录原因不硬上）。
**审计脚本要点**：差集比较时**去掉 .lua 后缀**、**注意 MISC 前缀拼接（hof_xxx → 加载名 xxx）**，否则误报（本次 36 项里 7 个误报）。

### 7.8 编码统一 vs 真实改动（对比脚本）

559 个"修改"中 476 个只是 BOM+CRLF 统一（忽略换行后 diff=0），真实改动仅 83 个。
**对比必须忽略 BOM/CRLF**：`t[3:] if t.startswith(b'\xef\xbb\xbf')` + 换行归一，否则工作量高估 6 倍。

### 7.9 大 Mod 适配总流程

资源层（ASTC 全量 + 5 自动文件）→ 编码层（BOM+CRLF）→ 入口层（加载链重排 + AddInventoryItemAtlas 补菜谱图集）→ 数据层（GLOBAL 共享表）→ 配方层（AddCookerRecipe 机制）→ postinit（整体重建 + pcall 分级）→ 汉化（精简表）→ 实测（删净→解压→日志唯一判据）。
### 7.10 ★ 原版物品图标通道错乱（hook 证伪 + 正确解 = 改数据指原版图集，v3.36-3.37 终解）

**现象**：制作栏/UI 里原版物品图标复制其他贴图/白图/无，**背包可能正常**（原版 prefab 无 atlasname 走自动解析）。
**日志**：`WARNING! Could not find region 'X.tex' from atlas 'images/inventoryimages2.xml'` 或
`Could not find an asset matching images/inventoryimages/inventoryimagesX.xml in any of the search paths`。
**根因**：mod recipe 写死 PC 版图集（DefaultAtlas2 = inventoryimages2 等）→ 柠版原版图集**路径格式**和 **region 分布**都与 PC 不同（见 §7.16）。
**已证伪方案**：①hook GetInventoryItemAtlas——对**已构造的 recipe.atlas** 无效（recipetile L90 直接读 `recipe:GetAtlas()`，不走 GetInventoryItemAtlas）；②AddInventoryItemAtlas 池——只对 GetInventoryItemAtlas **裸查**生效，显式 atlas 跳过。
**正确解**：遍历 AllRecipes 改 `recipe.atlas` 指向柠版原版正确图集（§7.16 路径 + region 归属）。
**排查要点**：图标类 bug ①搜日志 region/asset 报错 ②解包柠版 APK images.zip 查真实归属 ③改 recipe.atlas。

### 7.11 遗漏审计必须追间接加载链

"postinit 文件存在但不在 init_postinit 清单" ≠ 未加载——可能被其他文件 modimport（本案例 mods/ 6 个
经 hof_modcompatibility 间接加载，属误报）。审计三步：①直连清单差集 ②搜全 mod 对该文件名的 modimport/require
③守卫型文件（`if TUNING.HOF_IS_XXX`）确认守卫值再定论。
### 7.12 setfenv 全局接管文件 → 显式 GLOBAL 安全化改写

`GLOBAL.setfenv(1, GLOBAL)`（全局接管）在柠版 strict 环境有风险。**安全化三步**：
1. 源版所有裸用名 → `_G.rawget(_G, "X")` 局部引用，逐个判存在（缺则 return，不崩）；
2. 被 hook 的原函数存 local 再覆盖；3. 注释保留源版语义。
适用 postinit 数据/逻辑层；**worldgen 不适用**（需原生加载顺序）。
另：向已有 if 块后插代码，anchor 若选块内行会把新块并进 then 分支（逻辑错）——插入前确认 anchor 后紧跟 end。

### 7.13 ★ 自建图集必须 ASTC 8x8（RGBA KTEX 在柠版解压失败 0x500，v3.29→v3.31 实证）

**现象**：自建小图集（从 PC 原版提取原版物品 region）用 **RGBA（comp=4）** 打包，mod 里其他图集全 ASTC——日志
`HWTexture::DeserializeTexture failed on .../xxx.tex. glGetError returned 0x500`，图集纹理加载失败 → 图标黑/异常。
**根因**：柠版（Mali GPU 管线）对该 mod 环境只认 **ASTC**；RGBA 单独 .tex 解压失败（早期 RGBA 可用经验不适用当前引擎）。
**修复**：RGBA 数据经 astcenc 转 **ASTC 8x8 单 mip**：KTEX 头 `comp=24, mip=1, flags=4 → 0xFFF02380`，mip pre `pitch=0, datasz=块数据字节数`（256x256 = 16384B，文件总大小 16402B 与正常 mod 同规格图集完全一致）。
**校验**：`comp=(hdr>>4)&0x1F == 24`；与 mod 内正常图集（hof_hudimages.tex 等）头字节完全一致才交付。
**教训**：自建任何 .tex 一律 ASTC 8x8（同工具转换规则），不要用 RGBA——即使 RGBA 头"理论上正确"。

### 7.14 ★ 原版物品图标第二条路：AddInventoryItemAtlas 池（v3.31 实证）

**现象**：hook GetInventoryItemAtlas 对 4 鱼图标返回自建图集，但日志仍报 `Could not find region 'fishmeat.tex' from atlas 'images/inventoryimages2.xml'`——hook 未拦截到请求。
**机制**：柠版 GetInventoryItemAtlas **会遍历 AddInventoryItemAtlas 注册的图集池**（v2.27 菜谱书修复实证：注册菜谱图集后 GetInventoryItemAtlas 直接命中）。
**修复**：`AddInventoryItemAtlas("images/inventoryimages/hof_vanillafish.xml")`（短路径，与 modmain 菜谱图集注册同表）→ 池命中（AtlasContains 检查 region）→ 返回正确图集；hook 保留双保险。
**适用范围修正（v3.34-3.37 日志实证）**：池注册**只对 GetInventoryItemAtlas 裸查生效**（原版 prefab 无 atlasname 走自动解析时）；**对已构造的 recipe.atlas / 显式 atlas 无效**——制作栏 recipetile L90 直接读 `recipe:GetAtlas()`、mod recipe 显式传 DefaultAtlas2，均跳过池。**正确解见 §7.16（改 recipe.atlas 指柠版原版图集）**；自建图集仅当柠版原版**确无 region** 时才用（如 spice 图标从 PC 提取失败场景）。
**排查要点**：原版物品图标在柠版"该图集不含 region"时，两条路：①**解包 APK images.zip 查真实归属 → 改 recipe.atlas 指原版正确图集**（首选）；②仅当原版确无 region 才自建图集（ASTC 8x8，§7.13）。
**诊断**：hook 内加 `print("[ATLASFIX] GetInventoryItemAtlas type:", type(orig))` 区分"没装"与"没拦截"。

### 7.15 ★ worldgen 隔离 env 无裸 Lua 内置（pcall/type 为 nil，v3.32 实证）

**现象**：modworldgenmain 里 `modimport("postinit/map/terrain")` 报 `[MOD-LOAD-ERROR] ...:29: attempt to call global 'pcall' (a nil value)` → 世界生成失败重试 5 次 give up（卡生成世界）。
**根因**：柠版 modworldgenmain 隔离 env **没有裸 Lua 内置**（pcall/type 为 nil；pairs/ipairs/table 部分可用——本案例 hof_worldgen 裸 ipairs 未崩、terrain 裸 pcall 崩）——**凡 worldgen 链 modimport 文件，裸内置一律不依赖**。
**修复**：文件顶部统一 `local pcall = _G.pcall / local type = _G.type / local pairs = _G.pairs / local ipairs = _G.ipairs / local tostring = _G.tostring`（同 hof_worldtiledefs v2.20 模式）；声明后裸用走局部遮蔽，安全。
**排查要点**：世界生成报 MOD-LOAD-ERROR + `attempt to call global 'X' (a nil value)` → X 是 Lua 内置 → worldgen 隔离 env 坑 → 顶部 _G 别名；**modworldgenmain 链上所有 modimport 文件写完后必须扫裸内置**。

### 7.16 ★ 柠版原版图集路径与 region 分布（原版通道终解，v3.37 APK 源码实证）

**路径差异**：PC 版 `images/inventoryimages/inventoryimages1.xml`（带 `inventoryimages/` 子目录）；
**柠版 `images/inventoryimages1.xml`（无子目录）**——simutil.lua `GetInventoryItemAtlas_Internal` 源码实证
（images1-4 = `"images/inventoryimages1.xml"` 等，与 APK `assets/databundles/images.zip` 条目一致）。
写错带子目录路径 → `resolvefilepath` 报 `Could not find an asset matching ... in any of the search paths`。

**region 分布差异（4 鱼实证）**：PC 版 fishmeat/fishmeat_small/oceanfish_small_7/8_inv 全在 inventoryimages2；
**柠版 fishmeat/fishmeat_small/oceanfish_small_8_inv → inventoryimages1、oceanfish_small_7_inv → inventoryimages3**
（APK images.zip 精确 region 匹配）。spice 同理：chili_over→2、salt/sugar_over→1（柠版独有，PC 图集无）。

**配套机制（原版源码）**：①原版 prefab **从不显式设 atlasname**（scripts/prefabs/ 全量扫描 0 显式设置）——
物品图标全走 `GetInventoryItemAtlas(image)` 自动解析；②recipetile.lua L90 **无 fallback**：
`im:SetTexture(recipe:GetAtlas(), image, ...)`——recipe.atlas 必须能 resolve（不能 nil、不能写死错图集）。

**修复模式（v3.37 实装）**：
```lua
local ATLAS1 = "images/inventoryimages1.xml"   -- 柠版路径（无子目录）
local ATLAS3 = "images/inventoryimages3.xml"
local FIX = { ["fishmeat.tex"]=ATLAS1, ["fishmeat_small.tex"]=ATLAS1,
              ["oceanfish_small_7_inv.tex"]=ATLAS3, ["oceanfish_small_8_inv.tex"]=ATLAS1 }
local AllRecipes = rawget(_G, "AllRecipes")
if type(AllRecipes) == "table" then
    for _, r in pairs(AllRecipes) do
        if type(r) == "table" and FIX[r.image] then r.atlas = FIX[r.image] end
    end
end
```
挂载点：modmain `modimport("postinit/xxx")`（init_postinit 之后）；文件 BOM+CRLF；rawget 判 AllRecipes。

**最优排查 = 解包柠版 APK**（D:\BaiduNetdiskDownload 等）：`assets/databundles/images.zip`（原版图集 711 条 xml/tex）
查 region 归属；`scripts.zip`（811MB）查原版源码（simutil.lua/recipetile.lua/prefabs/）。比逐版本试错高效一个数量级。

**教训链**：原版通道"无 region" ≠ 柠版没有 → 解包 APK 查归属 → **位置变了**（1/3 不是 2）+ **路径格式变了**（无子目录）
→ 改 recipe.atlas 指原版正确图集 = 终解。图标类 bug 三步：①搜日志 ②解包 APK 查归属 ③改数据指原版图集。

### 7.17 ★ 转换工具 v1.6.0 P0（默认 native + 编码统一 + worldgen 别名 + 原版图集静态表）

**背景**：用户要求优化 dst_mobile_adapter.py，解决"转换后用不了"。P0 四项已实施并干跑验证
（测试产物：zip 全部 .lua BOM+CRLF；worldgen 注入 1 文件；图集命中 1 recipe 全 PASS）。

1. **默认 native 纯原生模式**：v1.6.0 起 `--native` 默认开启（`--legacy-compat` 显式切回旧兼容层）。
   依据：AIP 兼容层 17.68MB 全问题 → native 9.08MB 全好；手工适配成功 mod 均无副本无 FW_。
2. **全量编码统一 normalize_encoding**：所有 .lua 统一 UTF-8 BOM + CRLF（幂等；跳过二进制/异常）。
   **坑：utf-8-sig 解码会剥 BOM——解码后必须无条件重加 BOM**（否则有 BOM 文件被误剥，
   干跑 zip 9 文件 8 个丢 BOM 实证）。白名单跳过工具特意无 BOM 的清单
   （sound_banks_auto.lua / tile_preload_auto.lua）。**流程末尾有收尾统一**——后续注入
   （触摸管线等）写回可能 LF，收尾再跑一次 normalize_encoding 兜底。
3. **worldgen 链 _G 别名 inject_worldgen_globals**：解析 modworldgenmain.lua 的
   `modimport("...")` → 对每个链文件顶部注入 `local pcall/type/pairs/ipairs/tostring = _G.x`。
   **路径拼接用 `rel.split('/')` 不是 `rel.replace('.', os.sep)`**（后者把 .lua 的 . 也替换）。
4. **原版图集修正（静态表方案）**：**v1.6.2 自动选新**——`vanilla_atlas_jh210.json`（2.1.0 APK，6622 region）优先，
   jh142（1.4.2，6187 region）兜底（`_ATLAS_TABLE_CANDIDATES` 顺序），也支持 `--atlas <json>` 显式指定；
   表从 APK images.zip 一次性解析（region → 柠版图集路径无子目录）——工具直接读表，**无需每次解包 APK**；
   `--rebuild-atlas --apk <APK>` 仅 APK 更新时重建（文件名带版本标识）。扫描 .lua 的
   `image="xxx.tex"` → 表命中 → 生成 `postinit/<modkey>_vanilla_atlas.lua`
   （遍历 AllRecipes 改 recipe.atlas，rawget 判 AllRecipes）→ modmain 末尾挂载 modimport。
   **坑：旧版写死 jh142——更新版 APK 的图集/region 位置差异会漏修**（2026-10-05 泰拉明文版冒烟：jh210 命中 14 recipe）。
5. **bytes/str 混用坑**：`('%s_xxx' % mk) not in raw`（raw 是 bytes）→ TypeError——必须
   `(str).encode('utf-8') not in raw`。

**要点**：大改工具后必须 py_compile + 构造最小测试 mod 干跑 + 回读产物（zip 内逐文件查 BOM/CRLF、
worldgen 注入内容、atlas FIX 表）——日志说"成功"不等于产物正确（本次两个 bug 都是干跑+回读抓到的）。

### 7.18 ★ 工具 v1.6.0 三件套真实 mod 回归（2026-09-17 用户实测要求）

**英雄联盟武器**：工具 1442 文件 vs 手工 1451。仅手工多 9 个 UI 素材（config_act/bigger/dact/
smaller 4 组 8 个 + lol_wp_inv_slot 2 个）——**源 zip 无这些文件**（手工后期追加，非转换遗漏）。
early_prefab 工具 406 vs 手工 404（工具全量兜底多 2）；sound_banks 18=18。**结论：一致**。

**AIP**：工具 1280 vs 手工 1279。仅工具多 postinit/aip_vanilla_atlas.lua（v1.6.0 新规则）。
early_prefab 298=298 完全一致；mod_auto 931 vs 933。**结论：一致**。

**更多料理**：工具 1178 vs 手工 1221。源 zip 100% 覆盖（anim 351 zip = early_prefab 351 条、
mod_auto 398=398、纹理 383/0）。差异 = 手工版后期补充的 **42 个官方 quagmire 动画 + lavaarena_beetletaur_fx**
（源 zip 只有 2 个 quagmire zip——更多料理脚本引用 quagmire 锅/食材但源未带动画，手工从原版补）
+ postinit/hof_fishicons（工具版用 heap_of_foods_vanilla_atlas.lua 等价替代，命中 37 recipe 含 4 鱼）
+ 安装说明。**手工深度定制（§7.1 共享表/§7.2 菜谱书/§7.6 汉化精简/§7.5 入口拆分）工具 P0 未含**
——更多料理要完全等价需 P1 规则化或手工补。**结论：基础转换完整，深度定制需人工**。

### 7.19 ★ 工具 v1.6.0 回归抓到的 2 个新 bug（已在真实 mod 修复）

1. **parse_modinfo 配置项误匹配（更多料理 name=LANGUAGE 实证）**：modinfo 用多语言表
   `name = ChooseTranslationTable(STRINGS.NAME)`——双引号正则 `name\s*=\s*"..."` 兜底命中
   `configuration_options` 的 `{ name = "LANGUAGE", ... }` → modname=LANGUAGE → 输出文件夹名/
   modkey 全错。**修复**：①正则改**行首锚定** `(?m)^\s*name\s*=\s*"..."`（配置项前有 `{` 排除）；
   ②加多语言表分支 `STRINGS\s*=\s*\{[^}]*?NAME\s*=\s*\{[^}]*?zh\s*=\s*"..."`
   （zh 优先，无 zh 回退首个字符串=英文）——注意 STRINGS 与 NAME **跨行**，不能写 `STRINGS\.NAME`。
2. **LDR RGB（KTEX comp=5）不识别（更多料理 4 个 colourcube 失败实证）**：
   `images/colourcubesimages/*.tex` comp=5，pitch=w*3、datasz=w*h*3（未压缩 RGB）——
   parse_mip0_rgba 不认 → convert_bytes 返回 None → failed 计数无明细。**修复**：加 comp==5 分支
   RGB→RGBA 补 A=255。**另修**：convert_file 对 convert_bytes=None 也 append failed（带原因），
   否则 failed 计数有但 FAIL 明细空。

### 7.20 ★ 自建 minimap 图集三件套：ASTC 数据 + 头 bit9=1 + preload 清单（v3.40-3.44 紫白乱码终解）

**现象**：更多料理斑点灌木（k_spotbush）小地图图标紫白乱码块。四轮修复失败路径：
v3.40 63×63 RGBA 数据错 → v3.41 64×64 尺寸对齐仍乱码 → v3.42 按工具标准重做 ASTC
（`-cs`+PNG+`-medium`+`body[16:]` 去头、解码回读色差 5.63% 内容正确）**仍乱码** → v3.43 头改
0xFFF02380（bit9=1）**仍乱码**——数据、头全对还乱码。

**真正根因（v3.44 APK 源码实证）**：**minimap 图集必须进 preload_assets_auto.lua 清单**。
AddMinimapAtlas 只注册图集元数据；**纹理对象由 preload 清单预加载创建**（日志
`preload loaded ... xml holder=FW_STATIC_ATLAS_N`）。漏清单 → AddAtlas 注册成功（日志有
`MiniMapComponent::AddAtlas`）、无 0x500、无 region 报错，但 tex 从未加载 → 渲染紫白占位。
正常 mod（储藏室/千年狐/景熹/能力勋章等）preload 清单**显式含 minimap xml**（
`"scripts/mods/储藏室（新地窖）/minimap/storeroom.xml"`）实证。

**完整修复三件套（缺一不可）**：
1. **ASTC 数据**：`astcenc -cs png out.astc 8x8 -medium -silent`，块数据取 `body[16:]`（去 16B 文件头，不是去尾）；
2. **KTEX 头 bit9=1**：0xFFF02380（comp=24/mip=1/flags=4/bit9=1）——44 个正常 mod minimap 图集逐字节一致；
   （普通 UI 图集用工具标准 0xFFF02180 即可，bit9 是 **minimap 管线**必需位）
3. **preload 清单**：`preload_assets_auto.lua` 必须含该图集 xml（ATLAS_PAIR，自动带同目录 tex）。

**排查顺序（minimap 图标异常）**：①日志 `MiniMapComponent::AddAtlas` 确认注册 ②`Could not
find region` 搜 region 名（原版 minimap_data1/2.xml 精简了 quagmire 等 region → 自建正确）
③无 0x500 无 region 报错仍乱码 → **查 preload 清单是否含该 xml**（最优先，终因）→ 再查
KTEX 头 bit9 → 再查 ASTC 数据。
**APK 位置**：原版 minimap 不在 databundles/images.zip，在 APK 根 `assets/minimap/`
（minimap_data1.xml=17 region / minimap_data2.xml=524 region / minimap_atlas1.tex / minimap_atlas2.tex）。
**工具规则化（v1.6.1）**：gen_preload_assets 增加 `minimap/` 顶层目录扫描；
新增 ensure_minimap_preload 收尾步骤——扫描全部 minimap 图集目录（minimap/ + images 下含
minimap 的目录）的 xml（有同目录 tex）→ 与清单求并集自动补全（幂等；条目插到结尾 `}` 前）。


### 7.21 ★ 手机端"点选施法" target=nil 坑（point 施法 pos={x,y,z} 表）——拆解法杖全套修复实证

**现象**：同一把法杖/任意"右键点选目标"的 spell，PC 端右键点装备正常（`CastSpell(target=装备实体,pos,doer)`），
手机端点装备却**静默用不了**，提示"右键装备操作/请点选装备"——无 Lua 报错。

**根因**：手机端触摸点实体走的是 **point 施法**而非 target 施法：`target=nil`，`pos={x,y,z}` 普通表
（**不是 userdata**，没有 `:Get()`）。函数里 `if target and target.components.hh_equip then ... else 提示 end`
直接落 else，功能根本没进。拆解法杖 5 类"点装备"函数**全军覆没**：附魔石、洗蕴石、13 种宝石操作、卷轴 AoE。
（卷轴/空槽拆解本来就读 pos，反而正常——反证就是这个坑。）

**排查信号**：PC/模拟器正常 → 手机不行；白字提示"右键XX操作"；日志无 Lua error。
→ **第一反应：这是 point 施法 target=nil，不是功能没实现。**

**通用修法（所有需要"点选目标实体"的施法函数必做）**：
1. spellcaster 双开：`canuseontargets=true` + `canuseonpoint=true`（PC 点实体走 target，手机点地面/点实体走 pos）。
2. 函数开头把"目标实体"统一解析成 `target_equip`，target/pos 两路：
```lua
local target_equip = nil
if HH_UTILS:HasComponents(target, "hh_equip") then
    target_equip = target                      -- PC/点实体
end
if not target_equip and HH_UTILS:IsHHType(pos,"table") and pos.x and pos.y and pos.z then
    local near = TheSim:FindEntities(pos.x,pos.y,pos.z, 3, {"hh_equip"}, BLACK_TAG, {"_inventoryitem","pickable"})
    if near then
        for i,v in ipairs(near) do
            if HH_UTILS:HasComponents(v,"hh_equip") and checkOwner(v)
               and HH_UTILS:HasComponents(v,"equippable")
               and not v.components.equippable:IsEquipped() then
                target_equip = v; break
            end
        end
    end
end
if not target_equip then HHSay(caster,"请点选要操作的装备"); return end
```
3. 半径按交互意图取：单个目标 3 格，AoE/批量按原意（拆解 8 格）。
4. **pos 判定用 `pos.x and pos.y and pos.z`（普通表）**；注意区分——CanCast 校验里的 pos 是另一处，
   那走 `pos:Get()`。别混用。

**配套坑（白名单 vs 附魔范围不一致）**：staff 能对**任意**地面 hh_equip 附魔（FindEntities 不限 prefab），
但拆解若写死 `hh_check_list[v.prefab]`（掉落白名单）就会"能附不能拆"。
修法：拆解放行改成 `(hh_check_list[v.prefab] or effect_num > 0)`——带词条的装备无论是否白名单都能拆、把石头吐回。

**一句话**：手机端任何"右键点选某实体施法"的 mod 功能，target 必为 nil 兜底到 pos；这是柠版触屏施法的标准形态，
不是偶发 bug。

### 7.22 ★ 超宽屏容器格子偏左：PC原版对照法（v3.45 终解，此前 self.root 位移方案证伪）

**现象**：手机超宽屏（2670×1200，aspect≈2.22 > 16:9）上，自定义容器打开后格子整体偏左；平板正常。

**弯路（v3.25-v3.44 全错，勿再试）**：SetPosition(0,0,0) 强制居中、self.root 位移补偿、分辨率缓存调参、定时器自愈循环——全部基于错误前提（原版 containerwidget 自己管理位置），白费功夫。
此前在 `AddClassPostConstruct("widgets/containerwidget")` 里加了：
- `self:SetPosition(0,0,0)` 强制面板居中 → **这是根因**：原版 containerwidget 自己管理位置，
  强制 SetPosition(0,0,0) 把面板拉到屏幕中心，干扰原版定位 → 超宽屏格子偏左。
- `self.root:SetPosition(base + comp)` 水平补偿位移 → 在错误位置上再叠加，客机时序不同必失效。
- `HH_ComputeWideBase()` 分辨率缓存 + 各种 FACTOR 调参 → 全部基于错误前提，白费功夫。
- 定时器挂 self.inst / ThePlayer 延迟重施 / 自愈循环 → 全是治标，勿再试。

**★ 终解（v3.45，对照PC原版源码）**：解压PC原版mod zip，看原版 `handleContainer` 的 Open 写法。
PC原版只做三件事：
```lua
self:SetVAnchor(ANCHOR_MIDDLE)
self:SetHAnchor(ANCHOR_MIDDLE)
self:SetScaleMode(SCALEMODE_PROPORTIONAL)
self[ui_name] = self:AddChild(ui_father(self["owner"], self["container"]))
```
**不设 SetPosition(0,0,0)，不动 self.root**。让原版 containerwidget 自己定位。
柠版直接复用这段，房主客机都正常。

**★ 通用原则**：自定义容器UI位置不对时，**第一步永远是解压PC原版mod对照源码**，看原版怎么写。
不要凭猜测加位移补偿——你以为的"定位bug"可能只是适配版多改了一行 SetPosition 导致的。

**★ 客机UI不生效排查（避免重蹈）**：
- 补偿/位移函数如果在 `AddChild(ui_father(...))` **之前**调用，此时格子层 self.root 还没创建，
  `if not self.root then return end` 直接跳过 → 客机时序更晚必落空。**必须在 AddChild 之后调**。
- containerwidget 的 `self.inst` 是容器实体不是本地玩家，客机端 DoTaskInTime 不一定触发；
  要做延迟定时器必须用 ThePlayer。
- 客机端格子数据异步同步窗口长，一次性延迟重施会落空；盲目加自愈循环只是治标。

**编码**：改 .lua 必须 UTF-8 BOM+CRLF（PowerShell `[IO.File]::WriteAllText($p,$text,(New-Object Text.UTF8Encoding($true)))`）。

### 7.23 ★ 弹射/法球伤害"时有时无"：绕过 combat:GetAttacked 中间环节直接 DoDelta

**现象**：divine法球/弹射物命中后，伤害有时0有时正常（打死鸟/打不死鸟）。无Lua报错。

**根因**：`combat:GetAttacked(attacker, 0, weapon, nil, {planar=25})` 中间有多个环节会把 spdamage 清零：
- L607 attackdodger: `if self.inst.components.attackdodger:CanDodge(attacker) then damage, spdamage = 0, nil`
- L616 inventory: `self.inst.components.inventory:ApplyDamage(...)` 返回 damage=0, spdamage=nil
- L647 SpDefense: `SpDamageUtil.ApplySpDefense(target, spdamage)` 可能清零
这些组件在柠版某些生物上存在，导致 spdamage 被吞 → 伤害0。

**修法**：弹射/法球命中后直接 `health:DoDelta(-dmg)`，绕过整个 combat:GetAttacked：
```lua
if target and target:IsValid() and target.components.health and not target.components.health:IsDead() then
    local dmg = 25
    target.components.health:DoDelta(-dmg, nil, attacker.prefab)
    target:PushEvent("attacked", { attacker = attacker, damage = dmg, damageresolved = dmg, original_damage = dmg })
end
```
DoDelta 只检查 invincible/absorb，普通生物不挡，稳定扣血。

**适用场景**：任何"法球命中后额外伤害"（弹射/连锁/溅射）——不要走 GetAttacked 的 spdamage 通道。
本体武器伤害走 GetAttacked 正常（dmgsys hook 手动补 planardamage 见 §7.24）。

### 7.24 ★ 柠版 CollectSpDamage 不工作：dmgsys hook 手动补 planardamage

**现象**：武器有 `AddComponent("planardamage"):SetBaseDamage(50)`，但攻击时位面伤害为0。

**根因**：柠版 `SpDamageUtil.CollectSpDamage` 运行时不从 weapon 实体收集 planardamage
（虽 APK scripts.zip 确认组件存在且 DefineSpType("planar") 已注册）。PC原版会自动收集，柠版不工作。

**修法**：在 combat:GetAttacked hook 开头手动补：
```lua
if weapon and weapon.components and weapon.components.planardamage then
    local _pd = weapon.components.planardamage:GetDamage()
    if _pd and _pd > 0 then
        spdamage = spdamage or {}
        if not spdamage.planar then
            spdamage.planar = _pd
        end
    end
end
```
放在 orig_dmg 计算之后、old_GetAttacked 调用之前。已存在的 spdamage.planar 不覆盖（弹射类自带25保留）。

**适用范围**：77处 AddComponent("planardamage") 的武器全部走这个通用修复，不用逐个改 prefab。

### 7.25 ★ FROMNUM = 引擎 bank 解析失败哨兵（非 Lua 字面量，v3.49 实证）

**现象**：日志持续刷 `Could not find anim [run_loop] in bank [FROMNUM]`（152 次/83 分钟，
instance_2/3/4 多实例），缺失动画全是 run_loop/run_pre/hit/run_pst/idle_loop/dial_loop/
item_out/spawn（玩家/NPC 标准动画）。**不是卡顿源**（1.8 次/分钟），但对应实体动画全空白。

**FROMNUM 本质**：柠版引擎 **SetBank(原版bank) 时该 bank 未注册 → 引擎把 bank 占位成
"FROMNUM" 哨兵** → 之后播放任何动画都报 `Could not find anim X in bank [FROMNUM]`。
**FROMNUM 不是任何 Lua 字面量赋值**——全量扫描 PC 原版 scripts.zip（56MB）与 APK
scripts.zip（1.28GB，含 124 内置 mod）：字面量仅 1 处注释（redeemdialog.lua）+
19 处防御检查（`bank:find('FROMNUM')`，橘雪莉/魔法少女小樱/物品生成菜单/烹饪锅助手/
绳索桥等），**零赋值/零返回**。所以 grep 字面量永远找不到"产生者"。

**排查铁律（两条误判教训）**：
1. **不能靠日志时间相邻归属**（快速整理背包箱子误判实例）：[ABTN] 快速整理按钮
   Active=true 与 FROMNUM 首现相邻 ≠ 因果——该 mod 纯 replica 物品整理（modmain 25KB
   全读，无 AnimState/SetBank/动画路径），不产生 FROMNUM。
2. **正确路径 = 反查缺失动画名**：run_loop/hit/dial_loop/item_out = **pigman bank 动画**
   → 搜代码 `SetBank("pigman")` → 更多料理岛民（k_meadowisland_trader/
k_deciduousforest_trader/k_meadowisland_fishermerm）→ 适配版 anim/ **缺原版动画
   ds_pig_basic.zip**（bank=pigman 定义所在）→ 引擎 bank 解析失败 → FROMNUM。

**修复（此方法已被 §7.27 推翻，勿用）**：补原版动画 zip + 三处注册是错误路径（未验证 APK 原版资源存在性 + 未转 ASTC，实测黑块）。正确解：原版资源直接引用 APK，见 §7.27 四步。
**同类 bank 缺失统计法**：日志 `Could not find anim [X] in bank [Y]` 按 Y 分组统计，
可一次列全所有 bank 级缺失（本案例：explode 371=鲸鱼尸体缺 explode 动画 v3.48 已修 /
FROMNUM 152=岛民 pigman / collapse 10=低频噪音暂不修）。
### 7.26 ★ 柠版无 components/soundemitter：modmain 顶层裸 require 原版组件 → mod 禁用 → 卡加载（v3.51 实证）

**现象**：装新包后卡加载（世界生成重试 5 次 give up）。日志三段链：
`[MOD-LOAD-ERROR] modmain.lua:22: module 'components/soundemitter' not found` → `Disabling <mod> because it had an error` → `An error occured during world gen and we give up! [was 5 of 5]`。
**根因**：柠版 scripts.zip **无 components/soundemitter**（SoundEmitter 为引擎内置，APK 全量扫描零命中）。modmain 顶层裸 `_G.require("components/soundemitter")`（适配早期加的 quagmire 静默 hook）抛错 → modmain 加载失败 → mod 被禁用 → modworldgenmain 世界生成引用缺失 → 重试 5 次 give up → 卡加载界面。
**修复**：对原版组件/模块的 require 一律 pcall 包裹：
```lua
local _se_ok, _se_cls = _G.pcall(_G.require, "components/soundemitter")
if _se_ok and _se_cls ~= nil and type(_se_cls.PlaySound) == "function" and _se_cls.__hof_quagmire_silenced == nil then
```
**通用规则**：①modmain/modclientmain 顶层 require **原版组件**必须 pcall——柠版组件面比 PC 原版窄（引擎内置化，components/ 下无 sound*）；②排查 require 缺失前先排除 `--[[ ]]--` 注释块内的引用（本案例 modclientmain achievementsmain、k_newbrews hof_brewrecipes_warly 均注释块，误报）；③"卡加载"日志按 `MOD-LOAD-ERROR` → `Disabling` → `world gen we give up` 三段定位；④DEBUG_MODE print 刷屏修好后，二次卡加载必查 MOD-LOAD-ERROR（print=0 但 MOD-LOAD-ERROR>0 时）。
### 7.27 ★ 原版动画补包黑块 → 直接引用 APK 原版（v3.52 终解，§7.25 方案修正）

**现象**：手工补入原版动画 zip（butterfly_basic/rock/rock2/rock_flintless 等 13 个）后，蝴蝶/石头/金矿全变黑色块。
**根因**：手工从 PC 原版复制的 zip 内部 tex 是 **PC 格式 comp=2（DXT1，hdr FFFD4220/FFFD6220）**，柠版 Mali GPU 只认 **ASTC comp=24（FFF02380）** → 纹理加载失败黑块（§7.13 同族）。同时这些资源**柠版 APK 原版全有**（`assets/anim/`），mod 重复打包纯属冗余 + 抢占原版 bank。
**终解**：原版资源直接引用 APK，不打包进 mod。四步：
1. 删 mod `anim/` 副本 zip（13 个：ds_pig_basic/actions/attacks + tree_leaf_short/normal/tall + butterfly_basic + lobster_den/lobster_den_build + rock/rock2/rock_flintless + splash）；
2. 删 `early_prefab_auto.lua` 对应注册（13 条）；
3. 删 `mod_auto.lua` 对应 alias（注意这些别名可能被工具生成在 **entrypoints 表内**而非 asset_case_aliases，按行删即可）；
4. 删 prefab 的 `Asset("ANIM","anim/xxx.zip")` 声明（8 个 prefab 共 11 条）——**SetBank/SetBuild/PlayAnimation 运行时调用保留**，引擎自动解析 APK 原版 bank。
**验证**：①APK namelist 确认 `assets/anim/xxx.zip` 存在；②anim/ 全量扫描 tex comp==24 才交付；③打包后包内无残留 zip 名、无 Asset 声明、无 alias。
**体积**：13 个 zip 省 ~1.7MB（zip 包 47.06→45.39MB）。
**铁律**：**凡要"补原版动画"，第一步查 APK `assets/anim/` 是否有同名 zip——有则删 mod 副本+撤销三处注册（直接引用）；无才补且必须转 ASTC**。§7.25 的"补+三处注册"是错误路径（未验证 APK 原版资源存在性 + 未转纹理），保留为反面教材。
### 7.28 ★ 尾 BOM（\ufeff）语法炸弹：整文件重写 lua → modimport 失败 → 卡生成世界（v3.53 实证，自己引入的坑）

**现象**：装包后卡在生成世界。日志链：
`[MOD-LOAD-ERROR] ...:369: Error in modimport: ... importing main/map/hof_worldtiledefs.lua!` →
`[string "scripts/mods/.../main/map/hof_worldt..."]:116: '=' expected near '<eof>'` → `Disabling ... because it had an error` → 世界生成失败。
**根因**：适配时用 Python `open(p).read().decode("utf-8-sig")` → `split/join/replace("\n","\r\n")` → `write(out.encode("utf-8"))` **整文件重建**的方式改 lua，5 个文件（4 个 worldgen + mod_auto.lua）**全部被写入文件尾 EF BB BF（U+FEFF）**。Lua 词法器遇 `end\ufeff` 报 `'=' expected near '<eof>'` → 该文件加载即崩 → modimport 失败 → mod Disabling → 卡世界生成。
**排查要点**：卡加载时先搜日志 `'=' expected near`（语法错误）→ 定位文件 → **检查文件尾部字节**（`b.endswith(b"\xef\xbb\xbf")`）→ 头 BOM 正常不等于文件干净（**尾 BOM 不显示在头**）。
**修复**：字节级删尾：`open(p,"wb").write(b[:-3]) if b.endswith(b"\xef\xbb\xbf")`。改完全 mod 扫描 `tail or mid BOM`，状态机括号验证（**先字符串后注释**——简单正则 strip 会把字符串里的 `--` 当注释导致误报）。
**铁律**：①改 lua **禁止 decode+join+encode 整文件重建**（本次 5/5 中招）——用 Edit 工具或字节级替换；必须重建时写回后立即检查头 BOM 保持 + 尾无 EF BB BF + 括号；②验证语法错误用**状态机词法**（字符串/注释/块注释顺序处理），不用简单正则；③交付前 zip 内全 lua 扫 `\ufeff`（0 才放行）——本次打包后 zip 内 0 异常才算过。
### 7.29 ★ 头顶等级/Label 显示：直接抄原版实现（自创网络同步四案全败，v3.54 终解）

**现象**：成就 mod 头顶等级显示，重进 0 级 → 重进不显示 → 完全不显示 → 进世界卡死（自创方案一路恶化）。

**已证伪四案（勿重试）**：net_smallbyte 存等级（定长装不下数百级）、title 纯本地化（客户端无网络同步）、服务器网络实体+客户端轮询（柠版网络实体链路不可靠）、玩家 net_string+本地渲染（进世界卡死）——全部失败，勿重试。
**正确解 = 原版实现（成就轻松版.zip 实证，一字不改）**：
- modmain SHOW_TITLE 块：**两端无守卫** updateTitle：`inst.title = GLOBAL.SpawnPrefab("title")` + `SetParent(inst.entity)` + SetText；`DoPeriodicTask(2, updateTitle)` + **立即调用一次**；无事件监听、无 ismastersim 判断。
- title.lua：`net_string(inst.GUID,"texttitle","title")` + **监听在 SetPristine() 之前注册** + OnSetText 文本解析颜色（`string.find(txt,"EXP")` → `gsub("%D+","",1)` → tonumber → ColorTitle[floor(color/10)+1]）——颜色不走 net_smallbyte。
- 客户端本地实体渲染链路（SetText → net:set → 本地 dirty → OnSetText → AddLabel）**一定通**；"显示 0 级"是原版固有行为（客户端组件无存档数据），杀怪/轮询后刷正——**用户接受原版行为即算修复完成**。

**铁律**：①柠版**头顶 Label/文字渲染只抄原版实现，不自创网络同步**；②服务器网络实体→客户端副本渲染链路在柠版不可靠（收不到/无初始 dirty）；③玩家实体加 net_string 有卡死风险（v5.4 实测）；④**用户点名"用原版实现"时 = 逐字复制用户给的基准 zip 对应文件，不做任何"改进"**（本次 v5.4 违背此点自作主张加 net 同步 → 卡死 → 用户发怒）。

### 7.30 ★ 丰耘秘境实战：加密皮肤删除/皮肤全解锁/图鉴面板/Replica 时序（v26z-v27e，9 轮实测）

**背景**：PC 版丰耘秘境（皮肤图鉴/综合面板/小房间/加密皮肤大 Mod）→ 柠版全手动适配；用户禁用一键工具。

**1. Klei DLC 加密皮肤包识别与处理**：部分皮肤变体的 `.dyn` 源文件是 Klei DLC 加密格式（魔数 **0xC5949293**，社区确认不可解压）→ 专属纹理无法提取 → 降级（内容=基础）在图鉴/放置仍空白错乱（用户否决）→ 终解 = **删除变体皮肤、保留默认模型**。**删除必须四联动**：①anim/ zip ②early_prefab_auto.lua 注册行（漏删实测 8 条残留，v27d 才补清）③mod_auto.lua asset 别名 ④皮肤注册表（AddItemSkin）/图鉴条目/文本表。

**2. 皮肤所有权全解锁（所有人全皮肤）**：`SkinCheckFn`/`SkinCheckClientFn`（客户端/服务器双函数）直接 `return true`——停用 FREE_USERS 白名单/CDK/合集/服务器四条路径。**一次改两函数全覆盖**：物品皮肤（itemskins checkfn）/角色皮肤（characterskins）/cherry 服装（fallback 同一 API）/图鉴收集（HasSkin）。

**3. 图鉴收集进度 0/0 → 1/1**：`GetCollectProgress` 读 `PREFAB_SKINS_IDS[base]`——**删光 AddItemSkin 的条目该表为 nil → 返回 0,0**（图鉴有默认模型却显示"已拥有 0/0"）——兜底 `return 1, 1`（有图鉴条目就有默认基础外观）。

**4. 图鉴皮肤网格图标空白（"看起来删了"）**：皮肤项无 `atlas/tex` 字段 → 格子什么都不显示（用户误判"模型图标被删"）——补 `atlas = "images/inventoryimages/<name>.xml", tex = "<name>.tex"`（region 名=文件名.tex，图集文件在即可直接 SetTexture）。

**5. ★ Replica 同步时序崩溃（面板 SetValue(nil) 算术崩）**：组件 `_ctor` 时 `inst.replica.<comp>` 可能未就绪 → `PushReplicaData` 判空跳过 → 客户端 replica `_data` 空 → `Get*()` 返回 nil → UI `RefreshFromStaff` 读值**覆盖默认** → `SetValue(nil)` → `math.floor(nil/step+0.5)` 崩。**三层防御**：①读值 `or 旧值`（不覆盖默认）②调用处 `or 默认`（scale=1/白/0）③函数内部 `value = value or 0`；**根因补**：`_ctor` 末尾 `self.inst:DoTaskInTime(0, function() ... PushReplicaData() end)`（判空幂等）。

**铁律**：①皮肤类"删除"必须四联动（anim/注册/别名/注册表）；②图鉴皮肤显示问题先查数据字段（atlas/tex/skins）再怀疑资源缺失；③Replica 读值一律 or 兜底，组件 _ctor 一律延迟补推。

### 7.31 ★ 柠版 nil 防护全景（猪镇房子实战，v1-v9 全手动迭代）

**背景**：PC 工坊 3562141537（住房系统）→ 柠版全手动适配。逐轮实测日志：进世界 targetindicator nil 崩 → 全面扫描 221 处链式/方法调用 → 12 处防护 + 2 处禁用。以下为**可复用机制**。

**1. 柠版 GLOBAL 是 strict 表且无 GLOBAL 自引用**（最核心）：
- 读**不存在**的 GLOBAL 字段报 `variable 'xxx' is not declared`（不是 nil）；GLOBAL 表本身也被 strict 包裹，`GLOBAL.env` 读不存在的字段同样被拦；
- `setfenv(1, GLOBAL)` **生效后环境 = GLOBAL 表本身**，该表无 `GLOBAL` 字段 → 之后任何 `GLOBAL.xxx` 裸读都报 `variable 'GLOBAL' is not declared`（v4/v5 两轮踩坑实证）；
- **正确修复（setfenv 前补环境，setfenv 后不碰 GLOBAL 字段）**：
```lua
local modimport = modimport
-- 柠版修复：setfenv 前补当前环境 __index=GLOBAL
local _cur_env = GLOBAL.getfenv(1)
if GLOBAL.getmetatable(_cur_env) == nil then
    GLOBAL.setmetatable(_cur_env, {__index = GLOBAL})
end
GLOBAL.setfenv(1, GLOBAL)
```
- 注意：modworldgenmain 前端（instance_0）与进世界（instance_2/3）的 setfenv 生效行为**不同**——前端可能不生效（环境=strict mod env）、进世界生效（环境=GLOBAL 表）——**两个环境都要能过**，修复块放 setfenv 前即可两端兼容。

**2. 柠版无全局 ToolUtil**（PC 原版有 scripts/toolutil.lua）：strings.lua 等文件裸读 `ToolUtil.MergeTable` 崩 → **加载前 pcall 判断 + modimport 兜底**：
```lua
local _tt_ok = pcall(function() return ToolUtil ~= nil end)
if not _tt_ok then
    modimport("main/toolutil")   -- mod 自带 toolutil 时
end
```

**3. 柠版构造函数允许 nil 参数，mod 覆盖函数裸读必崩**：targetindicator 原版 `self.target ~= nil and ... or 0` 全程 nil 安全（L41/L47/L308），mod 覆盖版直接 `self.target.prefab` → target 为 nil（复活指示器等场景不传 target）崩溃。**覆盖函数/PostConstruct 入口统一 `self.xxx == nil or` 防护，nil 时回退原版函数**：
```lua
function TargetIndicator:GetAvatarAtlas(...)
    if self.target == nil or self.target.prefab ~= "target_indicator_marker" then
        return get_avatar_atlas(self, ...)
    end
```

**4. 柠版 UI 元素缺失 → FindChild nil 崩**：MakeFilterPanel 柠版无 `line_horizontal_white.tex` 定位线 → `FindChild(...)` 返回 nil → `:GetPosition()` 崩。**找到才用，找不到置 nil 并跳过相关逻辑**；若 mod 的整个 widget 修改依赖 PC 专属元素 → **直接禁用该 postinit**（postinit.lua 注册清单注释该行），用柠版原版 UI（本案例 craftingmenu 禁用，室内家具制作栏正常）。

**5. Replica/组件未同步 nil**：`owner.replica.interiorvisitor`（mod 自己 AddReplicableComponent 注册，客户端同步未就绪时 nil）、`TheWorld.components.interiorspawner`（室外不存在）→ **全链路 `a and a.b and a.b:c()` 防护**：
```lua
local iv = self.owner.replica and self.owner.replica.interiorvisitor
if iv == nil then return end
```

**6. 全局 nil 扫描法（221 处命中评估流程）**：
- 正则：`self\.[A-Za-z_]\w*(\.[A-Za-z_]\w*)+`（链式索引）+ `self\.[A-Za-z_]\w*:`（方法调用），postinit 全目录批量扫；
- 逐条评估优先级：**进世界即触发**（targetindicator/containerwidget/HUD）> 室内触发（mapwidget interiorvisitor）> 低优先（mapscreen 打开地图才构造）；
- **确认安全不用改**：原版字段存在（bottomright_root/minimap 原版构造就有；`self.inst` 由 Widget 基类 L7 `CreateEntity()` 注入）、已有 nil 检查（`self.locomotor ~= nil`）、AddComponent 兜底（widget.lua uianim）；
- 附带教训：**APK 内置 mods/<同名>/ 可能是自己之前打包的快照**（diff 确认=同版本），不是独立官方适配——别浪费时间对比。

**7. 排查顺序（nil 崩溃）**：报错堆栈定位文件行 → 从 APK `assets/databundles/scripts.zip` 提取柠版原版同文件（`scripts/widgets/xxx.lua`）对比字段差异 → 判断三类（字段缺失/时序未同步/UI 元素缺失）→ 对应上述防护 → **改完打包前用正则重扫确认无新增裸读**。
### 7.32 ★ endlocal 词法粘连 = mod 被禁用（传奇武器附魔强化 v3.21 实证）+ Insight 注入失效排查

**endlocal 词法粘连**：endlocal HH_EQUIP = {（end 与 local 无空格）→ Lua 词法器最长匹配读成标识符 → '=' expected near 'HH_EQUIP' → require 失败 → LoadPrefabFile 失败 → **整个 mod Disabling**（日志 MOD FAILED + Disabling <mod> + 存档 sim prefab restore failed）。修复：拆 end+换行+local。**全 mod 词法自查**：正则 end(?=[a-z]) + (return|break)(local|function)，注意字符串键 [endonenter]/注释 ending 误报。

**Insight/全能信息面板注入失效排查（dyc_panel_compat）**：验证链路 = DYCInfoPanel 全局 → objectDetailWindow → SetObjectDetail(data) → data.lines。**铁律：词条注册成功日志（modmain 阶段）≠ mod 存活；prefab 加载（LoadPrefabFile 更晚）失败会整体禁 mod → 注入必失效。先搜 Disabling <mod> 排除上游，再查 hook 链路。**

**同族沉淀**：①召唤依赖外部模组的 boss（prefab 缺失）→ Spawn 内显式 Say 提示 content 最后一行，勿静默；②UI GetImageAsset 自动解析的 mod 自定义 prefab 图标 → 显式补 custom_xml/custom_tex（图集 region 名=文件名.tex）；③删音频优化体积 = 删 fev/fsb 文件 + 删 Asset 声明 + **代码 PlaySound 保留**（接口保留，静默不播不崩）。
### 7.33 ★ 柠版 inventoryitem 组件时序 + prefab 加载失败（传奇武器附魔强化闪退全案，v3.22 实证）

**背景**：传奇武器附魔强化（柠版 64020101）点击稀有宝石（hh_gem_item）闪退，无 Lua error；连续两版补丁证伪后终解。四坑按排查顺序沉淀。

**① 补丁 A 证伪：inventoryitem 移到 SetPristine 前 = 前端 Spawn 即崩**
- 现象：`[string "scripts/components/inventoryitem.lua"]:10: attempt to index field 'inventoryitem' (a nil value)`，堆栈 `class.lua:43 __newindex(k=owner,v=nil)` → `inventoryitem.lua:61 _ctor` → `entityscript.lua:610 AddComponent` → prefab fn → `b2x-...`（柠版加载壳，非具体 mod）。
- 根因：**柠版前端（instance_0）也会执行 prefab fn**——物品预览/图鉴类 mod 会 `SpawnPrefab` 物品实体；SetPristine **前**实例化 inventoryitem 组件 → `_ctor` 内 `self.owner = nil` 触发柠版 strict class `__newindex`（字段未就绪）→ 崩。
- 铁律：**mod 原版"inventoryitem 在 SetPristine 后添加、客户端 return"是柠版唯一安全写法**；不要为"客户端槽位图标"把组件前置。客户端图标问题另走图标通道（见③）。

**② AddInventoryItemAtlas 在 prefab 文件内调用 → 整文件 "prefab file is not callable"**
- 现象：日志 `[62508ms][PREFAB][3][ERR] prefab file is not callable: .../scripts/prefabs/hh_prefabs.lua`（多实例多时段）→ 该文件所有 prefab 未注册 → 物品消失。
- 根因：`AddInventoryItemAtlas` 触发图集纹理加载，prefab 注册阶段时序下执行中断 → 文件未返回函数 → 加载失败。语法 loadfile 仍 OK（**语法通过 ≠ 加载成功**）。
- 修复：prefab 文件内只保留**原版同款** `RegisterInventoryItemAtlas(atlas, "name.tex")`（纯元数据注册，makeItems 实证安全）；AddInventoryItemAtlas 如需用，放 modmain 时机或 pcall 包裹。

**③ 无 inventoryitem 实体的图标 fallback 渲染 → 空纹理 → 引擎级闪退（无 Lua error）**
- 现象：`Could not find region 'hh_gem_item.tex' from atlas 'images/inventoryimages4.xml'`（渲染不崩，点击拿起/预览详情时崩，进程无收尾即终止）。
- 机制：无 inventoryitem 组件的实体（前端预览/图鉴/槽位 fallback）渲染图标 → 引擎按 **prefab 名**（`hh_gem_item.tex`）自动解析 → 原版图集无 region → 空纹理 → 引擎渲染路径崩溃（**无 Lua error ≠ 无问题，先搜 region 缺失**）。
- 修复：mod 图集（hh_items.xml）补同名 region（复制同物品 UV）+ `RegisterInventoryItemAtlas(mod_atlas, "hh_gem_item.tex")`。§7.14 的 AddInventoryItemAtlas 池在本案**不可在 prefab 文件内用**（见②）。

**④ 多 mod 扩展 player_classified 冲突（能力勋章）**
- 现象：`scripts/prefabs/player_classified.lua:456: attempt to call method 'Startbell' (a nil value)` → `Error deserializing lua state for entity player_classified ... Failed to read net var data` → recipesdirty/bufferedbuildsdirty 刷屏 → 游戏异常终止。
- 归因链：另一 mod（能力勋章）`FW_LoadPrefabs requested=113 added=0`（prefab 全未注册）→ 它给 player_classified 加的 Startbell 方法/net 变量（medal_*/gym_bell_start）缺失 → 事件触发 nil 崩 + net 反序列化失败。
- 排查法：**实体字段归属判断**——player_classified 上 `txk_light_shield_*`=本 mod、`medal_*/gym_bell`=勋章 mod；搜本 mod 全目录引用确认无关；`[PREFAB][ERR]` 只报某 mod 文件 = 该 mod 自己的加载失败，勿归因邻居 mod。

**方法论沉淀**：①改 prefab 文件后必查 `[PREFAB][ERR] prefab file is not callable`（加载失败 ≠ 语法错误，LuaJIT loadfile 通过也无效）；②"无 Lua error 闪退"先搜 region/asset 缺失（引擎渲染路径）；③前端/客户端也会执行 prefab fn（预览 Spawn）——prefab 里任何"非服务端安全"的组件/调用都会被前端触发；④本地 stub（LuaJIT + package.path）无法复现柠版 require 链（柠版走 modimport 隔离实例），中文路径在 stub 文件还有编码坑——静态归因优先，不反复让用户测。

### 7.34 ★ 柠版跃迁/传送通道全案（丰耘秘境凶险手杖/护甲地图跳跃，v14.52-v14.67，15 轮实测终解）

**背景**：PC 原版跃迁走 `playercontroller:DoAction(BufferedAction(HMR_BLINK_MAP_CONFIRM))` → mapscreen 动作 → 状态图 `hmr_blinkin_pre → hmr_blinkin(11帧) → hmr_blinkout(14帧)` 传送+动画。柠版手机端"地图跳跃无效/轮盘限距"系列 bug 15 轮实测，以下为**可复用终解**。

**1. ★ 柠版 ThePlayer 状态机组件链三级全 nil（决定性事实）**
- 日志实证：`player.sg=nil`、`player.components.stategraph=nil`、`player:GetComponent("stategraph")=nil`（三级全拿不到）。
- **推论**：任何"手动 GoToState"方案（含丰耘状态图 `hmr_blinkin/hmr_blinkin_pre/hmr_blinkout`、hmrblinker:BlinkTo 内部 GoToState）在柠版必然失败——**GoToState 类方案全部不可行**。
- 传送必须直接改坐标：`player.Physics:Teleport(x,y,z)` + `player.Transform:SetPosition(x,y,z)` 兜底（pcall 包裹）。

**2. ★ 传送通道选型结论表（按实测可靠性排序）**

| 通道 | 单机/主机 | 客机管理员 | 客机非管理员 | 距离限制 | 依据 |
|---|---|---|---|---|---|
| `DoTouchSpecialAction`（轮盘框架） | ✅ | ✅ | ✅ | **≈150 内置上限**（APK 魔改源码不可见） | v14.54 实测轮盘+地图均限距 |
| `ExecuteConsoleCommand`（引擎控制台） | ✅ | ❌（本地副本无效） | ❌ | 无 | TMIR 单机通道 |
| `TheNet:SendRemoteExecute` | — | ✅ | ❌ | 无 | TMIR 客机管理员通道 |
| **`SendModRPCToServer(MOD_RPC[mod][rpc])` 普通 RPC** | ✅ | ✅ | ✅ | 无 | **复活与传送按钮实证，终选** |

- **终解 = 普通 Mod RPC 单通道**（主机/客机统一、无管理员/控制台依赖）；RPC handler 在服务器做 `BlinkIn() → Teleport → BlinkOut()`（见下）。
- **DoTouchSpecialAction 内置限距**（≈150）来自移动端框架（GetGroundUseSpecialAction 等），Lua 层无法解除；轮盘短跳 150 合理，地图全图跳跃必须绕开它走 RPC。

**3. ★ 消耗复用组件模式（勿重写消耗逻辑）**
- 恐怖粘液/耐久消耗在凶险手杖 `terror_staff.lua` 的 `onblinkin` 回调（container slot 1 粘液 stackable 减 1 + `finiteuses:Use(1)` + `OnItemChanged`），由 `player.components.hmrblinker:BlinkIn()` 触发（hmrblinker 组件按 current_source 回调）。
- **RPC handler 标准形态**（对齐 PC 原版状态图语义）：
```lua
AddModRPCHandler("HMR", "HMR_BLINK_JUMP", function(player, px, py, pz)
    if player ~= nil and player:IsValid() then
        local x, y, z = px or 0, py or 0, pz or 0
        if player.components.hmrblinker ~= nil then
            pcall(function() player.components.hmrblinker:BlinkIn() end)  -- 消耗粘液+耐久+fx_in 特效
        end
        pcall(function() player.Physics:Teleport(x, y, z) end)
        pcall(function() player.Transform:SetPosition(x, y, z) end)
        if player.components.hmrblinker ~= nil then
            pcall(function() player.components.hmrblinker:BlinkOut() end) -- fx_out 特效（目标点）
        end
    end
end)
```
- **没粘液也照常传送**（PC 原版行为：onblinkin 内 item==nil 跳过消耗），不卡跳。护甲逃生跃迁（OnMinHealth→BlinkTo）无 onblinkin（不消耗粘液，只扣护甲耐久）。

**4. ★ 客户端动画序列（无状态机方案）**
- 状态机 nil → 直接 `AnimState:PlayAnimation` + `DoPeriodicTask(FRAMES)` 轮询 `AnimDone()` 推进；每段**超时兜底 tick>45（1.5s）**自动跳过（动画缺失/被玩家循环覆盖时不卡死）；全部播完恢复 `idle`。
- 动画名：`wortox_portal_jumpin_pre → wortox_portal_jumpin → wortox_portal_jumpout`（骑乘换 `boat_jump_pre/loop/pst`）；**特效主体 = BlinkIn/BlinkOut 生成的 fx prefab**（服务器生成广播，客户端可见）。

**5. ★ 柠版 strict 局部变量自引用坑（v14.66 实测闪退）**
- `local task = player:DoPeriodicTask(x, function() ... task:Cancel() ... end)` → 初始化表达式求值时 `task` 未进入作用域 → 闭包引用 → 柠版 strict 报 `variable 'task' is not declared`（进世界即崩）。
- 修复：**先声明后赋值**：
```lua
local task
task = player:DoPeriodicTask(x, function()
    ...
    if task ~= nil then task:Cancel() end
end)
```

**6. 动画缺失判断（低频非崩溃，勿过度修）**
- `Could not find anim [ground_idle] in bank [honor_cookpot]` = **PC 原版固有**（原版动画 zip 就没做 ground_idle/ground_place 放置段），引擎静默忽略，非适配遗漏、不崩溃——**修需要美术资源，不修**。
- 丰耘云端代理 `CURL ERROR [7] Failed to connect`（nnqq.com.cn/fymj/proxy）= 用户网络环境项，本地功能有失败兜底，不影响。

**7. 交互铁律再强调**：任何"兜底 return {}"注入（如大炮 GetCannonAimActions）都会**卡全图交互**（角色无交互按钮/物品无法拾取）——**宁可不兜底，删除兜底恢复交互**（v14.52 实证）。

### 7.35 ★ 柠版声音"全静音"：框架消费清单必须 LF（英雄联盟武器 v43 全案，2026-10-01）

**症状**：mod 所有带音效装备集体无声（BGM/武器音效全无），但 mod 功能正常、无 Lua 报错。

**根因**：适配工具把 `sound_banks_auto.lua` / `mod_auto.lua` 写成了 **CRLF**；手机端已装正常发声 mod 的这两个文件 **31/31、151/152 全部为 LF 无 BOM**。框架按需声音加载器（`per-mod sound bank manifest lazy loader`）解析 CRLF 清单失败 → 全部 bank 静默不加载 → 全装备无声。

**修复**：字节级仅移除 CR（CRLF→LF、无 BOM），内容零改动；改后从打包 zip 内**按字节**回读确认（StreamReader 读文本会误报 BOM，必须按字节查 EF BB BF）。

**排查三步（静态层全对时不要停在"文件没丢"）**：①sound/ 文件齐全且 fev/fsb 头有效（FSB5/FEV 与正常 mod 一致）②清单/别名/Asset 声明/PlaySound 事件名逐一核对 ③★**全样本格式比对**——sound_banks_auto 必须与正常 mod 同格式（LF），这是决定性一步。

**铁律**：①"全静音"优先怀疑清单格式，不是文件缺失；②框架消费清单（sound_banks_auto/mod_auto）=LF、引擎加载文件（preload_assets/early_prefab）=CRLF 是各自规范，勿一刀切；③改清单前先扫描全部已装正常 mod 的同文件格式作基准。详见 `柠版适配API文档.md` §31。

### 7.36 ★ 虚空异界（泰拉）整包适配全案：轮盘施法/皮肤选择/背包注入三大终解（2026-10-03，用户交付适配好版实证）

> 依据：用户提供的"适配好的泰拉"目录（`C:\Users\Longe\下载\饥荒\个人适配柠版mod\虚空异界（泰拉）`，3810 文件）全量扫描。该目录与工作目录唯一差异 = **删除了 `main\tr_backpack_bar.lua` 与 `main\tr_feiyng_inventorybar.lua` 两个独立背包注入文件**（背包注入逻辑已整合进 `main\tr_inventory_bar.lua` 内嵌 PATCH）。以下模式均为**可复用终解**，细节与完整代码模板见 `柠版适配API文档.md` §32。

**1. ★ 轮盘施法统一模板（FW_RegisterRangedWeapon 三型）**——泰拉所有武器技能在柠版统一走触摸轮盘：
- **A 类（天顶剑/终极棱镜/彩虹猫）：拖动持续施法**——`onaim` 按武器 cd 节流 `aoespell:CastSpell(doer, pos)`（`_last_attack_time` 闸门）+ `onfire` 补一次；只保留轮盘（装备时 `aoetargeting:SetEnabled(false)` 隐藏原版技能按钮）。
- **B 类（囚龙山/星衍巨镰/投掷类）：拖动选点、松开施法**——`onaim` 只更新标点，`onfire` 才 FindEntities 找目标 → `SpawnPrefab("tornado")` 或 `combat:DoAttack(target)`；投掷类用 `DoPeriodicTask(0.1)` 周期索敌（`FIND_RADIUS=15`，排除 playerghost/INLIMBO/player/companion/wall/abigail/shadowminion）+ `combat:DoAttack(target)` 触发原版投掷。
- **统一骨架**：`FW_RegisterRangedWeapon(mod, {priority, range=9999, action_side="right", reticule_directional=true, reticule_prefab="reticule", ...})` + `unpack_pos(position)`（**Vector3 userdata 与普通表两路兼容**：`type(position.Get)=="function"` 走 `:Get()`，否则 `position.x/.z`）+ 客户端 `SendModRPCToServer` / 服务器 `AddModRPCHandler`（`checknumber(x/z)` + 武器 prefab 白名单校验）。
- **★ 星衍巨镰"暂时做不到"根因（用户多轮未解的终解）**：客户端 `spellbook.spell_id` 只是**客户端本地状态**；PC 靠 playercontroller 把 (spellbook, spell_id) 塞进 LeftClick RPC，柠版无此通道 → 服务器 `aoespell:CastSpell` 静默空放。修复：① 客户端每次 `SelectSpell` 立即发 `select` RPC 同步服务器（`onselect → if TheWorld.ismastersim then aoespell:SetSpellFn(fn)`）；② 服务器记 `weapon._tr_spell_id` 兜底；③ 从未选过技能默认选第 1 个，保证不空放。**星衍巨镰按用户要求保留原版技能按钮 + spellbook 选技能流程**，轮盘仅"拖拽选点+松开施法"。

**2. ★ mod 角色皮肤选择三件套（tr_skins_api + tr_skin_choice + tr_skin_ownership）**——"选人大厅能选、进游戏回退原皮肤"的终解：
- **① hook `ValidateSpawnPrefabRequest`**（定义在 `scripts/networking.lua`，是 **Lua 层全局函数，可 hook**——修正此前"引擎层校验不可注入"的错误结论）：返回 rt 数组，把 `rt[2]=base` 放行 mod 皮肤；
- **② hook `TheNet.SendSpawnRequestToServer`** 记录选人大厅选择的皮肤 → `SetPersistentString("tr_ygsts_skin_choice_v1", ...)` 持久化 → 进游戏 tr_uis.lua 读取恢复；
- **③ `CheckOwnership`/`CheckClientOwnership` 放行**（isskin 匹配 "ygsts" 前缀）。三层缺一不可：校验放行 + 选择持久化 + 所有权放行。

**3. ★ 背包注入物品栏下方（integrated backpack）终解 = 删除独立文件 + 整合进 tr_inventory_bar.lua**：
- **"禁用导致物品栏左右拉伸的代码"的最终实现**：直接删 `tr_backpack_bar.lua` / `tr_feiyng_inventorybar.lua`（用户适配好版实证），全部逻辑收进 `tr_inventory_bar.lua` 内嵌 `TR_FEIYING_INVENTORYBAR_PATCH`；
- **关键设计（防拉伸铁律）**：装备底板 `bar.bg` 保持原版位置不动（`EQUIP_PLATE_UP=0`）；`ResizePanel` 只**纵向增高** `bgcover`、**绝不改 X 缩放/宽度**（`bar.bgcover:SetScale(sx, sy, ...)` 中 sx 按 16 列背包宽度算、不动原版 20 列 X scale——"60-slot mod stretches bg and bgcover with the same 20-column X scale"是拉伸根因）；
- **状态签名闸门**：`FeiyingStateKey` 签名防重复重排（丢弃再拾取后不再被旧几何改坏）；
- **容器面板隐藏**：`containerwidget Open` 后 `bganim/bgimage/inv` 全 Hide（独立面板不再弹出）；
- **Lua 5.1 local 前置声明坑**：helper 若定义在使用点之后会被当全局查找 → nil 崩溃（`attempt to call global 'X' (a nil value)`），需**先声明后赋值**（v8.5 注释实证）。
- 参考实现：丰耘秘境 `scripts\hmrmain\hmr_init.lua` L788-949 辉煌背包（bg=Image 无 Flow 死代码、integrated 布局 bg 本来就盖两行、**底板不做任何 SetPosition/SetScale**）。

**4. ★ modmain.lua 头部 Prefab 包装（ATLAS_BUILD 自动补）**：
```lua
local TrOriginalPrefab = Prefab
Prefab = function(name, fn, assets, deps, force_path_search)
    -- 遍历 assets：凡 "images/inventoryimages/*.xml" 的 ATLAS 且未登记 ATLAS_BUILD → 自动补 Asset("ATLAS_BUILD", file, 256)
    -- 原因：inventory atlases 也必须先成为 animation builds，minisign 皮肤符号才能引用
    return TrOriginalPrefab(name, fn, assets, deps, force_path_search)
end
```
**5. ★ worldgen 专属游戏模式注入（modworldgenmain.lua）**：`TR_VOID_CORRIDOR` level type / `tr_void_corridor` game mode / `exclusive` 或混合配置；hook `ServerSettingsTab`/`ServerCreationScreen` + `SelectGameModeWithoutCallback`（spinner 找不到选项时先 `SetOptions(GetGameModesSpinnerData(...))` 再选）+ `IsNewWorldTab`（`slot==nil or slot<0 or ShardSaveGameIndex:IsSlotEmpty(slot)`）判定新世界标签。

**6. 大文件 hook 组织模式（8 个 30-86KB hook 文件）**：`tr_world_prefab_hooks.lua`（86KB：AddPrefabPostInit 批量 + 老手战双胞胎 + PlayerHud UI）、`tr_component_ui_hooks.lua`（weapon GetProjectile / playercontroller OnLeftClick / combat / health SetVal·DoDelta·SetMaxHealth·SetPercent / containerwidget Open·Close·OnMouseWheel + 滚动容器）、`tr_character_actions.lua`（temperature/freezable/pinnable/grogginess/childspawner/combat/growable/cursable + CHARGE_ATTACK 动作 + baiyu RPC + FIX_FENSHEN 动作）——**组件方法 hook 统一 `local old_X = Component.X` 再覆盖**，动作统一 `AddAction + AddStategraphActionHandler("wilson"/"wilson_client")` 双端注册。详见 API 文档 §32。


### 7.37 ★ 虚空回廊（Void Corridor）模式适配全案：出生/倒计时/投票/三面板（2026-10-04，双人实测全流程走通）

> 用户实测链路：combat→returning→countdown→contract（投票）→role_select（选职业）→shop→combat 全走通，主客机不闪退。核心文件见 `柠版适配API文档.md` §32.11。以下为可复用终解（均有多轮实测/闪退实证）。

**1. ★ 手机端服务器"不 tick"铁律**——服务器 `DoPeriodicTask` 倒计时、`DoTaskInTime(0.35/5)` 投票推进在手机端服务器**全部不执行**。终解 = **实时锚点 + 客户端 RPC 周期驱动**：服务器设 `_contract_vote_at = TheSim:GetRealTime()/1000 + 5`，客户端出生后每 2 秒发 `run_start` RPC，服务器 handler 做**三段推进**（countdown→StartContractVote / contract→票齐 ResolveContractVote / role_select→下一 phase）。

**2. ★ 客户端 sync handler 必须写回 client_state**——`AddClientModRPCHandler("sync", ...)` 第一行必须 `client_state = DecodeState(encoded)`，漏写则所有 widget（投票/金块/波次/敌怪/选职业/小游戏）拿不到 state 全不显示（服务器 phase=contract 正常但主客机投票页都不弹 = 此根因，v7.22）。分发：controls postconstruct 统一 `ListenForEvent("tr_void_corridor_sync")` 逐个 `SetState`（6 个 widget 全实现 SetState）。

**3. ★ PC 自定义全局缺失 → modmain 补全局**——泰拉 PC 版在某 modimport 文件定义全局 `FindPlayer`（引擎无此全局，柠版缺失）→ `attempt to call global 'FindPlayer' (a nil value)` 崩溃（客机投票后主机闪退 = 此因，v7.25）。修复：modmain 顶部 `GLOBAL.FindPlayer = function(userid) ... 遍历 AllPlayers ... end`，一处定义全 mod 生效（system/events 裸调用全覆盖）。

**4. ★ 皮肤恢复必须校验角色 prefab**——"进游戏恢复上次皮肤"逻辑若只校验皮肤名（IsValidYgstsSkin）、不校验角色 → 任意角色（wathgrithr/wx78）出生 2 秒后被强制 `SetBuild(艾莉西亚)` 误套（v7.23）。修复：`if player.prefab ~= "ygsts" then return end`。

**5. ★ AddClassPostConstruct 回调 self 作用域坑（v7.24 加载即崩）**——追加逻辑必须写在 `function(self) ... end` **函数体内**；写在 `end)` 之后 = 顶层孤儿代码，`self` 为全局 nil → `attempt to index global 'self' (a nil value)`。移动代码时勿吞掉包裹它的顶层 `if not TheNet:IsDedicated()` 的收尾 `end`。

**6. ★ luaparser 对 BOM/括号误报 → LuaJIT 权威校验**——luaparser 对 UTF-8 BOM 报 `token recognition error at: ''`（文件实际可运行）；对括号不平衡报 `syntax errors: None`（误报 OK）。权威校验 = `luajit -e "local f,e=loadfile([[path]]); if f then print('OK') else print(e) end"`。

**7. ★ 出生状态机与倒计时链路**——服务器不挂 native `worldcharacterselectlobby`；客户端装扮页点"选择"用 `TheNet:SendSpawnRequestToServer`，服务器 hook `VerifySpawnNewPlayerOnServerRequest` 做 Lua 状态机（SpawnRequest=就绪、全员就绪→6 秒倒计时→放行；`IsUserSpawned` 已出生玩家自动就绪）。倒计时广播 `SendModRPCToClient(rpc, userid, ...)` **必须带 userid**（否则 Invalid RPC sender list）、**剔除 performance 条目**（客户端托管主机收不到服务器→客户端 RPC）；主机本地近似 `TR_SPAWN_LOCAL_START = GetTimeRealSeconds()`（跨 instance 不共享 GLOBAL）。

**8. ★ 三面板柠版适配层 = FW_RegisterEditable（非按钮注册）**——金块/敌怪海克斯/回廊状态面板 → `FW_RegisterEditable("虚空异界（泰拉）", proxy, key, {...})`（用户明确"不是注册成按钮，只是添加柠版适配层"）；proxy 挂 controls 同级 + 同锚定 + `SetPosition` 绝对同步（手机端 Widget 无 SetOffset，直接崩）；持久化名 `tr_gold_panel_pos_v1`/`tr_affixes_panel_pos_v1`/`tr_status_panel_pos_v1`。

**9. 版本回溯锚点**：v7.13 PushEvent 纯本地不跨网络 → v7.14 Mod RPC → v7.16 带 userid → v7.18 run_start 通道+剔除 performance（SendServerRPC 须 GLOBAL API 转发）→ v7.19 GLOBAL 锚点跨 instance 不共享 → v7.20 主机本地近似+诊断打印 → v7.21 DoTaskInTime 不 tick 实证+实时锚点 → v7.22 client_state 写回根因 → v7.23 皮肤守卫 → v7.24 self 作用域+补 end → v7.25 FindPlayer 补全局。详见 `柠版适配API文档.md` §32.11。
