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
version: 1.9.9
---

# DST Mod 开发与排障

> 整理：神似 ｜ 版本：1.9.9（已融入 dst-mod-creater v1.2 配套知识库；丰耘秘境实战沉淀见 §7.30；猪镇房子柠版 nil 防护全景见 §7.31；柠版打包规范实证沉淀见 §8；工具 v1.5.2 防御规则 SpawnPrefab 链式判空；v1.5.1 rmtree 安全守卫；传奇武器附魔强化闪退全案见 §7.33：inventoryitem SetPristine 时序/prefab 文件内 AddInventoryItemAtlas/图标 fallback 空纹理/多 mod player_classified 冲突；柠版跃迁/传送通道全案见 §7.34：状态机组件链三级 nil→GoToState 不可行、普通 Mod RPC 单通道终选、消耗复用 BlinkIn/BlinkOut、strict 局部变量自引用坑、兜底 return {} 卡交互铁律）

## 何时使用 / 何时不用（触发边界）

| ✅ 命中任一即进入本技能 | ❌ 回退通用回答或其他技能 |
|---|---|
| 咨询/报错涉及 DST Mod：制作、崩溃报错、移植、代码分析、功能修改、UI 改动、Lua/DST API | 纯游戏玩法、攻略、剧情咨询（与 Mod 无关） |
| 柠版/手机端适配：贴图空白、纯黑块、卡加载页、闪退、配方失效、触摸/拖拽失灵 | 通用 Lua 编程教学（与 DST 无关） |
| Mod 间兼容/冲突排查、多 Mod 同开异常 | 其他游戏（非 DST）的 Mod 问题 |

## 工作流程

### 1. Bug 排查与修复（主要）

按以下顺序推进：
1. **定位错误**：让用户提供 client_log.txt / server_log.txt 报错堆栈，或从描述提取崩溃场景
2. **匹配模式**：查阅 references/common_bug_patterns.md 找对应根因和修复方案
3. **定位代码**：在 Mod 代码中搜索报错涉及的函数/组件/预制物
4. **给出修复**：提供具体代码修改并说明原因
5. **验证建议**：告知用户如何验证（查看日志、控制台测试、多人测试）

**常见错误速查**：attempt to index a nil value → 空引用加存在性检查；attempt to call method → API 变更；stack overflow → 递归加守卫；客机看不到变化 → 缺网络同步；旧存档崩溃 → OnLoad 版本迁移。

### 2. Mod 移植 / 兼容性适配（主要）

1. **确认源和目标**：DS→DST？旧版→新版？PC→柠版/手机端？
2. **一键工具优先**：先用 tools/dst_mobile_adapter.py（纹理转换+资源副本+自动文件+兼容层注入+打包，详见柠版适配API文档.md §20）
3. **按清单检查**：references/mod_porting_guide.md 移植检查清单逐项核对
4. **柠版/手机端适配**：贴图空白/纯黑块/卡加载/闪退/配方失效，先查 references/mobile_porting_guide.md（KTEX 转换、文件编码、hook 失效、客户端标签）；动画空白第一排查点 = early_prefab_auto.lua 是否全量注册所有 build；人物/角色 Mod 查 references/character_mod_guide.md
5. **重点改造**：预制物加 Network 组件+SetPristine()；区分主机/客机；网络变量同步；Mod RPC；OnSave/OnLoad 版本号
6. **冲突兼容**：AddPrefabPostInit 而非覆盖，保存原函数再扩展

### 3. Mod 代码结构分析与功能解读（次要）

modinfo.lua → modmain.lua → prefabs/ → components/ → widgets/ → stategraphs/，按「功能→机制→关键文件函数」输出。

### 4. 新 Mod 开发（次要）

参考 references/mod_structure.md 模板与 dst_api_quickref.md API；网络同步参考 mod_porting_guide.md。

### 5. UI 界面修改（次要）

HUD 用 AddClassPostConstruct("screens/playerhud")；新 Screen 用 TheFrontEnd:PushScreen()；UI 只读网络变量。

### 6. 新版柠版内置 mod 库已验证 API（v1.5 增量速查）

> 来源：新版柠版（jh联机模组版 1.4.2）APK 内置 124 个已适配 mod 全量扫描，详见柠版适配API文档.md §22。

- FW_RegisterAction(mod, id, {keycode, keyboard_phase, character, onpress(player,source), ondown/onup})：按键动作注册，source=='touch' 区分触屏；与 FW_RegisterModButton({key=同id, reuse_action=true}) 成对 = 按键技能→触屏按钮标准模式
- FW_RegisterCharacter(mod, {prefab, register=AddModCharacter, gender, name, title, health, hunger, sanity, skins})：角色入列三件套之一，自动写 TUNING + MODCHARACTERLIST
- FW_CancelLifecycle / FW_DiagnoseLifecycle / FW_DoTaskInTime(mod, player, 'task_id', delay, cb)：生命周期任务管理
- FW_UnregisterEditable(widget)：反注册旧 editable root（Rebuild 前必调）
- FW_IsActionButtonPoint(x,y)：自定义世界触摸时排除框架按钮区
- 触摸管线四件套：controller.OnTouchStart/End/Cancel hook + 原生长按 OnTouchLong(id) + 双指手势 OnGesture(theta,dist,state) + wasLongTouch/IsVirtualStickTouched()；全局 TheInput:AddTouchStart/Move/EndHandler；屏幕坐标 TheSim:GetEntitiesAtScreenPoint/ProjectScreenPos
- mod 自报能力表：rawset(G, '<MOD>_MOBILE_V140'/'<MOD>_MOBILE_COMPAT', {...})
- FW_RegisterModButton 必传 character 字段（防跨角色泄漏）；onrelease/show_in_edit_mode/reuse_action 两段式技能必用
- FW_RegisterRangedWeapon 扩展：require_equipped=false（坐骑/非手持）+ reticule_directional + deadzone + resolve_target/validate_target

## 参考文件导航

| 文件 | 内容 | 何时查阅 |
|------|------|----------|
| references/common_bug_patterns.md | 常见 Bug 模式、根因、修复代码、排查流程 | 任何报错/崩溃 |
| references/mod_porting_guide.md | DS→DST 移植步骤、API 变更对照、网络同步、存档兼容 | Mod 移植/版本适配 |
| references/dst_api_quickref.md | 全局对象、实体方法、常用组件、事件、网络 API、配方、UI | 写代码查 API |
| references/mod_structure.md | 目录结构、modinfo/modmain 详解、预制物/组件/Widget 模板 | 新建 Mod/结构分析 |
| references/ui_modification_guide.md | UI 架构、HUD 修改、Widget/Screen 模板 | 任何 UI 修改 |
| references/api_usage_statistics.md | 100 个实装模组 API 使用统计 | 选 API/判断可行性 |
| references/real_mod_patterns.md | 真实模组实现手法（网络同步/RPC/技能树/移动端框架） | 实现复杂功能 |
| references/mobile_porting_guide.md | 柠版专项：KTEX、预加载清单、文件编码、hook 失效、客户端标签 | PC→柠版适配排查 |
| references/character_mod_guide.md | 人物 Mod 专项：三件套动画、技能树、专属 UI/按钮 | 角色适配 |
| tools/dst_mobile_adapter.py | 柠版一键适配工具（v1.6.0 native 模式）：纹理转换 ASTC 8x8、自动文件、strict 兼容层、通用规则库、触摸滚动、按键技能转按钮、打包 | PC→柠版批量化第一步 |
| 柠版适配API文档.md（v1.5.2） | 全量 API 手册+工具章节；§22 = 124 mod API 增量 | 查 FW_* API/机制沉淀 |

## 配套知识库 dst-mod-creater（v1.2 全量融入）

本技能已内置完整 dst-mod-creater 技能包（子目录 dst-mod-creater/，MIT 许可，离线可用，635 文件 / 36MB）：
- API 笔记：dst-mod-creater/references/api-*.md（13 篇，带官方源码 file:line 引用）
- 快速入门：dst-mod-creater/references/00-quickstart.md
- 美术管线：dst-mod-creater/references/art.md + tools/（KTEX/SCML/混淆工具 15 个）
- 人物开发标准：character-esc.md + official-templates.md
- 可运行模板：dst-mod-creater/templates/（8 个 + official/ 7 个 Klei 官方模板）
- 大型 mod 实战笔记：dst-mod-creater/references/mod-notes/（11 篇）
- 混淆逆向工具：daogui_*.py、lol_dump.py、probe_require.py

用法：做新 Mod → 00-quickstart + 选模板；查 API → api-*.md；美术/纹理 → art.md + tools/；参考大型 mod → mod-notes/。

## 关键原则

1. 主机/客机分离：改组件数据必须在 TheWorld.ismastersim 守卫内
2. 安全访问：访问 inst.components.xxx 前必须判存在；FindEntity 等返回值判空
3. PostInit 优于覆盖：AddPrefabPostInit/AddComponentPostInit，避免冲突
4. 网络同步：客机可见数据必须 net 变量或 Mod RPC
5. 存档兼容：OnSave 带版本号，OnLoad 迁移旧格式
6. 给可操作的代码：具体文件、具体行、替换前后代码
7. 先复现再修复：要报错日志和复现步骤，不凭猜测
8. 不要反复加 print 让用户来回测（手机测试成本极高）：先静态分析+原版源码+APK 源码，最多一轮调试 print，一轮没定位就重新分析

## 排查时需要向用户索取的信息

- 完整报错日志（client_log.txt 中 error 附近堆栈）；Mod 版本和 DST 版本；复现步骤；主机/客机/多人；是否与其他 Mod 冲突；相关代码文件

## 8. 柠版 mod 打包规范（v1.9.1 实证沉淀，勿再错）

**格式铁律**：
1. zip 内套一层 mod 文件夹：顶层目录名 = modinfo 解析的 mod 名（不带 -柠版适配版 后缀）
2. zip 文件名：<mod名>-柠版适配版.zip
3. 路径全正斜杠（安卓解压反斜杠有风险）
4. 压缩级别 DEFLATED compresslevel=6
5. 安装：解压 zip → 拷贝内层 mod 文件夹到柠版 mods 目录

**推荐实现（Python）**：
import zipfile, os
target = r"<mod源目录>"; modname = "<mod名>"
outzip = os.path.join(os.path.dirname(target.rstrip('/\\')), modname + '-柠版适配版.zip')
if os.path.exists(outzip): os.remove(outzip)
with zipfile.ZipFile(outzip, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for r, dirs, files in os.walk(target):
        for f in files:
            p = os.path.join(r, f)
            z.write(p, os.path.join(modname, os.path.relpath(p, target)))

**PowerShell 替代**：勿用 [ZipFile]::CreateFromDirectory（反斜杠+丢外层文件夹）；用 ZipArchive 逐文件 CreateEntry 并手动补 folderName + "/" 前缀。

**体积预期**：源 75.9MB → compresslevel=6 约 47.1MB；压缩率 60-65% 正常，不是打包遗漏。

**验证清单**：①条目数=源文件数 ②首条=<mod名>/... ③含反斜杠条目=0 ④修复内容在 zip 内读回确认。

## 7. 大 Mod 适配沉淀（更多料理 Heap of Foods 实战，v3.25 实测能进）

### 7.1 ★ modimport 与 require 实例隔离 → GLOBAL 共享表

现象：大 Mod 的「每日推荐菜谱固定不变/配方计数 0/N/手册打开 pairs(nil)」同源。根因：柠版 modimport 与 require 通道不共享文件缓存 → 独立实例 → 数据表 nil。修复：共享表挂 rawset(GLOBAL, "__<MOD>_<TABLE>", ...)，读取方 rawget(GLOBAL, ...) or {}。特征：UI 打开时报错+表 nil+多文件互 require/modimport。

### 7.2 ★ AddCookerRecipe 第三参 / cookbook_atlas / no_cookbook

第三参 true → cookbook_category="mod"；false/缺省 → 覆盖 recipe.cookbook_atlas（柠版无资源→开菜谱书崩溃）；recipe.no_cookbook=true 跳过菜谱书但照常进烹饪表。适配：modmain 注入防御 hook 自动补 true。

### 7.3 ★ init_postinit.lua 改表必须整体重建

正则替换单表会吞掉后续表 → pairs(nil) 刷屏 → 卡加载。铁律：多表串联文件任何单表修改 = 拼接全部表整体重建；每条目 pcall。

### 7.4 strict 环境 GLOBAL 字段裸读 → rawget

柠版 strict.lua 对不存在的 GLOBAL 字段报 not declared（不是 nil）。不确定存在的字段一律 rawget(GLOBAL, "x") 判空。存在成员（TUNING/TheWorld）可裸读。

### 7.5 大入口模块拆分恢复

主模块 require 8 子模块 → 禁用整个入口 + 子模块逐个 pcall(require) 恢复（崩溃风险低→价值高排序）。

### 7.6 汉化大表卡加载 → 精简表

639KB 全量汉化表卡加载 → 98KB/1330 键精简表正常。保留玩家可见键。

### 7.7 postinit 分级恢复 + 审计脚本

已加载（pcall 全量）→ 遗漏（按核心玩法>岛屿>跨 mod 分级补）→ 暂缓（worldgen/setfenv 记录不硬上）。审计差集去掉 .lua 后缀、注意 MISC 前缀拼接，否则误报。

### 7.8 编码统一 vs 真实改动（对比脚本）

对比必须忽略 BOM/CRLF（t[3:] if startswith BOM + 换行归一），否则工作量高估 6 倍。

### 7.9 大 Mod 适配总流程

资源层（ASTC 全量+5 自动文件）→ 编码层（BOM+CRLF）→ 入口层（加载链重排+AddInventoryItemAtlas）→ 数据层（GLOBAL 共享表）→ 配方层（AddCookerRecipe）→ postinit（整体重建+pcall 分级）→ 汉化（精简表）→ 实测（删净→解压→日志唯一判据）。

### 7.10 ★ 原版物品图标通道错乱（正确解 = 改数据指原版图集，v3.36-3.37 终解）

现象：制作栏原版物品图标复制其他贴图/白图/无，背包可能正常。根因：mod recipe 写死 PC 版图集路径/region 与柠版不同。已证伪：hook GetInventoryItemAtlas（对已构造 recipe.atlas 无效）、AddInventoryItemAtlas 池（只对裸查生效）。正确解：遍历 AllRecipes 改 recipe.atlas 指向柠版原版正确图集（§7.16 路径+region）。排查：①搜日志 region 报错 ②解包 APK images.zip 查归属 ③改 recipe.atlas。

### 7.11 遗漏审计必须追间接加载链

postinit 文件存在但不在清单 ≠ 未加载——可能被其他文件 modimport。审计三步：直连差集 → 搜 modimport/require → 守卫型文件确认守卫值。

### 7.12 setfenv 全局接管文件 → 显式 GLOBAL 安全化改写

裸用名 → _G.rawget(_G, "X") 局部引用判存在；被 hook 原函数存 local 再覆盖；注释保留语义。worldgen 不适用。插入前确认 anchor 后紧跟 end。

### 7.13 ★ 自建图集必须 ASTC 8x8（RGBA KTEX 柠版解压失败 0x500）

柠版 Mali GPU 只认 ASTC：KTEX 头 comp=24, mip=1, flags=4 → 0xFFF02380，pitch=0, datasz=块数据字节数。自建任何 .tex 一律 ASTC 8x8。

### 7.14 ★ 原版物品图标第二条路：AddInventoryItemAtlas 池（v3.31）

池注册只对 GetInventoryItemAtlas 裸查生效；对显式 recipe.atlas 无效（正确解 §7.16）。排查：图标类 bug ①搜日志 ②解包 APK 查归属 ③改数据指原版图集。

### 7.15 ★ worldgen 隔离 env 无裸 Lua 内置（pcall/type 为 nil）

凡 worldgen 链 modimport 文件，顶部统一 local pcall/type/pairs/ipairs/tostring = _G.x。报 MOD-LOAD-ERROR + attempt to call global 'X' → X 是 Lua 内置 → worldgen 隔离 env 坑。

### 7.16 ★ 柠版原版图集路径与 region 分布（终解）

PC 版 images/inventoryimages/inventoryimages1.xml（带子目录）；柠版 images/inventoryimages1.xml（无子目录）。region 分布不同（4 鱼实证：柠版 1/3 不是 2）。修复：遍历 AllRecipes 改 recipe.atlas 指柠版正确图集。最优排查 = 解包柠版 APK 查 region 归属。

### 7.17 ★ 转换工具 v1.6.0 P0（默认 native + 编码统一 + worldgen 别名 + 图集静态表）

1. --native 默认开启；2. normalize_encoding 全量 BOM+CRLF（utf-8-sig 解码会剥 BOM——解码后无条件重加）；3. worldgen 链顶部 _G 别名（路径用 rel.split('/')）；4. 原版图集修正静态表 vanilla_atlas_jh142.json；5. bytes/str 混用坑（str.encode('utf-8') not in raw）。要点：大改工具后必须 py_compile + 最小测试 mod 干跑 + 回读产物。

### 7.18 ★ 工具 v1.6.0 三件套回归（英雄联盟武器/AIP/更多料理）

结论：基础转换完整一致；深度定制（共享表/菜谱书/汉化精简/入口拆分）需人工。

### 7.19 ★ 工具 v1.6.0 回归 2 个新 bug

1. parse_modinfo 配置项误匹配（name=LANGUAGE）：正则改行首锚定+多语言表分支；2. LDR RGB（comp=5）不识别：加 comp==5 分支 RGB→RGBA 补 A=255；convert_file 对 None 也 append failed。

### 7.20 ★ 自建 minimap 图集三件套：ASTC 数据 + 头 bit9=1 + preload 清单（v3.40-3.44 终解）

minimap 图集必须进 preload_assets_auto.lua 清单（AddMinimapAtlas 只注册元数据；纹理由 preload 预加载创建）。三件套缺一不可：①ASTC 数据（astcenc -cs png out.astc 8x8 -medium，body[16:] 去头）②KTEX 头 bit9=1（0xFFF02380）③preload 清单含 xml。排查顺序：日志 AddAtlas → region 报错 → preload 清单（最优先）→ 头 bit9 → ASTC 数据。

### 7.21 ★ 手机端"点选施法" target=nil 坑（point 施法 pos={x,y,z} 表）

手机触摸点实体走 point 施法：target=nil，pos={x,y,z} 普通表。函数内 if target and target.components.xxx 直接落 else。修法：spellcaster 双开（canuseontargets+canuseonpoint），函数开头 target/pos 两路解析目标实体（pos.x and pos.y and pos.z 判定），半径按交互意图取。信号：PC 正常手机不行+白字提示右键+无 Lua error → 第一反应 point 施法 target=nil。

### 7.22 ★ 超宽屏容器格子偏左：PC原版对照法（v3.45 终解）

弯路（勿再试）：SetPosition(0,0,0) 强制居中、self.root 位移补偿、分辨率缓存调参、定时器自愈循环——全部基于错误前提。终解：对照 PC 原版源码，只做 SetVAnchor/HAnchor(ANCHOR_MIDDLE)+SetScaleMode(SCALEMODE_PROPORTIONAL)+AddChild(ui_father)，不设 SetPosition 不动 root。通用原则：UI 位置不对第一步解压 PC 原版对照源码。客机：补偿函数必须在 AddChild 之后调；延迟定时器用 ThePlayer。

### 7.23 ★ 弹射/法球伤害"时有时无"：绕过 combat:GetAttacked 直接 DoDelta

GetAttacked 中间环节（attackdodger/inventory/SpDefense）会把 spdamage 清零。修法：弹射/法球命中后直接 health:DoDelta(-dmg) + PushEvent("attacked")。本体武器伤害走 GetAttacked 正常。

### 7.24 ★ 柠版 CollectSpDamage 不工作：dmgsys hook 手动补 planardamage

柠版 SpDamageUtil.CollectSpDamage 运行时不从 weapon 收集 planardamage。修法：combat:GetAttacked hook 开头手动补 spdamage.planar = weapon.components.planardamage:GetDamage()（已存在不覆盖）。77 处 AddComponent("planardamage") 通用修复。

### 7.25 ★ FROMNUM = 引擎 bank 解析失败哨兵（v3.49）

柠版引擎 SetBank 时 bank 未注册 → 占位 FROMNUM 哨兵 → 之后所有动画报 Could not find anim X in bank [FROMNUM]。FROMNUM 不是任何 Lua 字面量。排查铁律：不能靠日志时间相邻归属；正确路径 = 反查缺失动画名（run_loop/hit = pigman bank）→ 搜 SetBank → 缺原版动画 zip。修复（已被 §7.27 推翻勿用）：补原版动画+三处注册是错误路径（黑块实证）。同类 bank 缺失统计法：按 Y 分组统计可列全所有 bank 级缺失。

### 7.26 ★ 柠版无 components/soundemitter：modmain 顶层裸 require → mod 禁用 → 卡加载

日志三段链：MOD-LOAD-ERROR module not found → Disabling → world gen give up。修复：对原版组件 require 一律 pcall 包裹。通用规则：①modmain 顶层 require 原版组件必须 pcall ②排除注释块内引用误报 ③卡加载按三段定位 ④二次卡加载必查 MOD-LOAD-ERROR。

### 7.27 ★ 原版动画补包黑块 → 直接引用 APK 原版（v3.52 终解）

手工补 PC 原版动画 zip 内部 tex 是 DXT1（comp=2），柠版只认 ASTC → 黑块；且柠版 APK 原版全有。终解四步：删 anim/ 副本 zip + 删 early_prefab 注册 + 删 mod_auto alias + 删 Asset 声明（运行时 SetBank/PlayAnimation 保留，引擎自动解析 APK 原版）。铁律：凡要补原版动画，第一步查 APK assets/anim/ 是否有同名 zip——有则删副本直接引用；无才补且必须转 ASTC。

### 7.28 ★ 尾 BOM（\ufeff）语法炸弹：整文件重写 lua → modimport 失败 → 卡生成世界

整文件重建会把尾 BOM 写入文件尾 → Lua 词法器遇 end\ufeff 报 '=' expected near '<eof>'。排查：卡加载先搜 '=' expected near → 检查文件尾部字节 endswith(\xef\xbb\xbf)（头 BOM 正常不等于干净）。修复：字节级删尾。铁律：①改 lua 禁止 decode+join+encode 整文件重建 ②语法验证用状态机词法（先字符串后注释）③交付前 zip 内全 lua 扫 \ufeff=0 才放行。

### 7.29 ★ 头顶等级/Label 显示：直接抄原版实现（自创网络同步四案全败）

已证伪四案（勿重试）：net_smallbyte 存等级（定长装不下数百级）、title 纯本地化（客户端无网络同步）、服务器网络实体+客户端轮询（链路不可靠）、玩家 net_string+本地渲染（进世界卡死）。正确解 = 原版实现：modmain 两端无守卫 DoPeriodicTask(2, updateTitle)+立即调用；title.lua net_string 监听在 SetPristine 前注册；颜色不走 net_smallbyte。铁律：头顶 Label 只抄原版实现不自创网络同步；用户点名用原版实现时逐字复制基准 zip。

### 7.30 ★ 丰耘秘境实战：加密皮肤删除/皮肤全解锁/图鉴面板/Replica 时序（9 轮实测）

1. Klei DLC 加密皮肤包（魔数 0xC5949293）→ 删除变体皮肤保留默认模型。删除必须四联动：anim/ zip + early_prefab 注册 + mod_auto 别名 + 皮肤注册表/图鉴/文本。
2. 皮肤所有权全解锁：SkinCheckFn/SkinCheckClientFn 直接 return true（一次改两函数全覆盖）。
3. 图鉴收集进度 0/0 → 1/1：GetCollectProgress 读 PREFAB_SKINS_IDS 该表 nil → 兜底 return 1, 1。
4. 图鉴皮肤网格图标空白：补 atlas/tex 字段（region 名=文件名.tex）。
5. Replica 同步时序崩溃：三层防御（读值 or 旧值 / 调用处 or 默认 / 函数内 value or 0）+ _ctor 末尾 DoTaskInTime(0) 延迟补推。

铁律：皮肤删除四联动；图鉴显示先查数据字段再怀疑资源；Replica 读值一律 or 兜底。

### 7.31 ★ 柠版 nil 防护全景（猪镇房子实战，v1-v9 全手动迭代）

1. GLOBAL 是 strict 表且无自引用：读不存在字段报 not declared；setfenv 生效后 GLOBAL 表无 GLOBAL 字段 → 之后 GLOBAL.xxx 裸读报错。正确修复：setfenv 前补当前环境 __index=GLOBAL，setfenv 后不碰 GLOBAL 字段。
2. 柠版无全局 ToolUtil：pcall 判断 + modimport 兜底。
3. 构造函数允许 nil 参数，覆盖函数入口统一 self.xxx == nil or 防护，nil 回退原版函数。
4. 柠版 UI 元素缺失 → FindChild nil 崩：找到才用，否则置 nil 跳过；整个 widget 依赖 PC 专属元素 → 直接禁用该 postinit。
5. Replica/组件未同步 nil：全链路 a and a.b and a.b:c() 防护。
6. 全局 nil 扫描法：正则 self\.[A-Za-z_]\w*(\.[A-Za-z_]\w*)+ 链式 + 方法调用，逐条评估优先级。
7. 排查顺序：堆栈定位 → APK scripts.zip 提取原版同文件对比 → 判断三类（字段缺失/时序/UI 元素）→ 防护 → 重扫。

### 7.32 ★ endlocal 词法粘连 = mod 被禁用（传奇武器附魔强化 v3.21 实证）+ Insight 注入失效排查

**endlocal 词法粘连**：endlocal HH_EQUIP = {（end 与 local 无空格）→ Lua 词法器最长匹配读成标识符 → '=' expected near 'HH_EQUIP' → require 失败 → LoadPrefabFile 失败 → 整个 mod Disabling（日志 MOD FAILED + Disabling <mod> + 存档 sim prefab restore failed）。修复：拆 end+换行+local。全 mod 词法自查：正则 end(?=[a-z]) + (return|break)(local|function)，注意字符串键 [endonenter]/注释 ending 误报。

**Insight/全能信息面板注入失效排查（dyc_panel_compat）**：验证链路 = DYCInfoPanel 全局 → objectDetailWindow → SetObjectDetail(data) → data.lines。铁律：词条注册成功日志（modmain 阶段）≠ mod 存活；prefab 加载（LoadPrefabFile 更晚）失败会整体禁 mod → 注入必失效。先搜 Disabling <mod> 排除上游，再查 hook 链路。

**同族沉淀**：①召唤依赖外部模组的 boss（prefab 缺失）→ Spawn 内显式 Say 提示 content 最后一行，勿静默；②UI GetImageAsset 自动解析的 mod 自定义 prefab 图标 → 显式补 custom_xml/custom_tex（图集 region 名=文件名.tex）；③删音频优化体积 = 删 fev/fsb 文件 + 删 Asset 声明 + 代码 PlaySound 保留（接口保留，静默不播不崩）。

### 7.33 ★ inventoryitem 组件时序 + prefab 加载失败（传奇武器附魔强化闪退全案，v3.22 实证）

**① SetPristine 前加 inventoryitem = 前端 Spawn 即崩（instance_0 报 inventoryitem.lua:10 attempt to index field 'inventoryitem'）**
- 机制：柠版前端（instance_0 加载/物品预览/图鉴）也会执行 prefab fn（Spawn 预览）；SetPristine 前 AddComponent("inventoryitem") → _ctor 里 self.owner=nil 触发 strict class __newindex（字段未就绪）→ 崩。
- 修复：inventoryitem 必须 **SetPristine 后添加**（客机 fn 提前 return，不实例化组件）。

**② prefab 文件内 AddInventoryItemAtlas → "prefab file is not callable"（加载失败 ≠ 语法错误）**
- 现象：`[PREFAB][ERR] prefab file is not callable` → 文件所有 prefab 未注册 → 物品消失；LuaJIT loadfile 语法仍通过。
- 机制：AddInventoryItemAtlas 触发图集纹理加载，prefab 注册阶段时序中断 → 文件未返回函数。
- 修复：prefab 文件内只保留 **RegisterInventoryItemAtlas**（纯元数据注册）；AddInventoryItemAtlas 放 modmain 时机或 pcall 包裹。改完必查 [PREFAB][ERR]。

**③ 无 inventoryitem 实体的图标 fallback 渲染 → 空纹理 → 引擎级闪退（无 Lua error）**
- 机制：前端预览/图鉴/槽位 fallback 渲染图标 → 引擎按 prefab 名自动解析 → 原版图集无 region → 空纹理 → 引擎渲染路径崩溃。
- 修复：mod 图集补同名 region（复制同物品 UV）+ RegisterInventoryItemAtlas；**"无 Lua error 闪退"先搜 region 缺失**。

**④ 多 mod 扩展 player_classified 冲突（能力勋章）**：另一 mod `FW_LoadPrefabs requested=113 added=0`（prefab 全未注册）→ 它加的 Startbell 方法/net 变量缺失 → nil 崩 + net 反序列化失败。排查：**实体字段归属判断**（txk_light_shield=本 mod / medal_*=勋章 mod）；[PREFAB][ERR] 只报某 mod 文件 = 该 mod 自身加载失败，勿归因邻居。

### 7.34 ★ 柠版跃迁/传送通道全案（丰耘秘境凶险手杖/护甲地图跳跃，v14.52-v14.67，15 轮实测终解）

**1. ★ 柠版 ThePlayer 状态机组件链三级全 nil（决定性事实）**
- 日志实证：player.sg=nil / player.components.stategraph=nil / player:GetComponent("stategraph")=nil。
- 推论：**任何 GoToState 类方案（含丰耘状态图 hmr_blinkin/hmr_blinkout、hmrblinker:BlinkTo 内部 GoToState）在柠版必然失败**。
- 传送必须直接改坐标：player.Physics:Teleport(x,y,z) + Transform:SetPosition 兜底（pcall）。

**2. ★ 传送通道选型结论表（实测排序）**

| 通道 | 单机/主机 | 客机管理员 | 客机非管理员 | 距离限制 | 依据 |
|---|---|---|---|---|---|
| DoTouchSpecialAction（轮盘框架） | ✅ | ✅ | ✅ | ≈150 内置上限 | v14.54 实测 |
| ExecuteConsoleCommand（引擎控制台） | ✅ | ❌ | ❌ | 无 | TMIR 单机 |
| TheNet:SendRemoteExecute | — | ✅ | ❌ | 无 | TMIR 客机管理员 |
| **SendModRPCToServer 普通 Mod RPC** | ✅ | ✅ | ✅ | 无 | **复活与传送按钮实证，终选** |

- 终解 = **普通 Mod RPC 单通道**（主机/客机统一、无管理员/控制台依赖）；服务器 handler 内 BlinkIn() → Teleport → BlinkOut()。DoTouchSpecialAction 内置限距来自移动端框架，Lua 层无法解除；全图跳跃必须绕开它走 RPC。

**3. ★ 消耗复用组件模式（勿重写消耗逻辑）**
- 恐怖粘液/耐久消耗在 terror_staff.lua 的 onblinkin 回调（slot1 粘液 stackable 减 1 + finiteuses:Use(1)），由 player.components.hmrblinker:BlinkIn() 触发（按 current_source 回调）。
- RPC handler 标准形态：
```lua
AddModRPCHandler("HMR", "HMR_BLINK_JUMP", function(player, px, py, pz)
    if player ~= nil and player:IsValid() then
        local x, y, z = px or 0, py or 0, pz or 0
        if player.components.hmrblinker ~= nil then
            pcall(function() player.components.hmrblinker:BlinkIn() end)  -- 消耗粘液+耐久+fx_in
        end
        pcall(function() player.Physics:Teleport(x, y, z) end)
        pcall(function() player.Transform:SetPosition(x, y, z) end)
        if player.components.hmrblinker ~= nil then
            pcall(function() player.components.hmrblinker:BlinkOut() end) -- fx_out（目标点）
        end
    end
end)
```
- 没粘液也照常传送（PC 原版行为），不卡跳。护甲逃生跃迁（OnMinHealth→BlinkTo）无 onblinkin（只扣护甲耐久）。

**4. ★ 客户端动画序列（无状态机方案）**
- AnimState:PlayAnimation + DoPeriodicTask(FRAMES) 轮询 AnimDone() 推进；每段**超时兜底 tick>45（1.5s）**自动跳过（动画缺失/被玩家循环覆盖不卡死）；播完恢复 idle。
- 动画：wortox_portal_jumpin_pre → jumpin → jumpout（骑乘换 boat_jump_pre/loop/pst）；**特效主体 = BlinkIn/BlinkOut 生成的 fx prefab**（服务器生成广播，客户端可见）。

**5. ★ 柠版 strict 局部变量自引用坑（v14.66 实测闪退）**
- `local task = player:DoPeriodicTask(x, function() ... task:Cancel() ... end)` → 初始化表达式求值时 task 未进入作用域 → strict 报 `variable 'task' is not declared`。修复：**先声明后赋值**（local task; task = ...，闭包内判空）。

**6. 动画缺失判断（低频非崩溃，勿过度修）**
- Could not find anim [ground_idle/ground_place] in bank [honor_cookpot] = PC 原版固有（原版 zip 没做放置段），引擎静默忽略，不修（需美术资源）。
- 丰耘云端代理 CURL ERROR [7] Failed to connect（nnqq.com.cn/fymj/proxy）= 网络环境项，本地功能有兜底，不影响。

**7. 交互铁律**：兜底 return {} 注入（如大炮 GetCannonAimActions）会**卡全图交互**（无交互按钮/物品无法拾取）——宁可不兜底，删除兜底恢复交互（v14.52 实证）。