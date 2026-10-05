# API 契约映射索引（dst-mod-dev × skills-手机版）

> 用途：dst_api_quickref.md 是"API 怎么用"；本文件是"API 的契约与源码锚点"——遇到拿不准的 API，
> 先按领域查契约要点，再对照精确到 `file:line` 的源码锚点（来源：Android/Playdigious 手机版 DST 工程树，
> 即 `skills-手机版.zip` 的 46 份契约技能），最后回 dst-mod-creater 的 api-*.md 笔记看官方源码依据。
> 适用：新 Mod 开发、原版行为核验、API 变更后兼容评估。

## 0. 平台前提（Android 内置模组树，先于一切判断）

- `main.lua:52` `IsAndroid()`、`:61` `IsMobile()`；`main.lua:70` 主进程 `MODS_ROOT="mods/"` + `MODS_ENABLED=true`。
- `worldgen_main.lua:102` `IsAndroid()`、`:116-149` 世界生成进程单独开启内置模组（**与主进程是两个独立 Lua 实例，全局互不继承**）；赋值必须在 `IsAndroid()` 定义之后、`require("mods")` 之前，否则门禁早退。
- `mods.lua:10` `MOD_API_VERSION = 10`；`:474`/`:689` 两处 `if not MODS_ENABLED then return end` 门禁（模组"菜单能启用但完全不生效"第一嫌疑）。
- `modindex.lua:19` `LoadApkAssetModDirectoryNames` 读 `mods/modsettings.lua`（沙箱只提供 `Add`，其余调试开关是 no-op）；`:98` `RegisterApkModAssetPath` 登记 `package.assetpath`；`:479` 加载前预热。
- `mods.lua:1023-1027` `StartVersionChecking` 在 Android 直接 return（不做 Workshop 版本校验）；`DoVerifyModVersions`→`TheSim:VerifyModVersions`（`:1015-1017`）C API 在设备上不存在。

## 1. Mod 工程与运行时

| 技能（新包） | 契约要点 | 核心源码锚点 | 关联 dst-mod-creater |
|---|---|---|---|
| **dst-lua-runtime** | 柠版/安卓环境：`GLOBAL` 访问、require vs modimport、Class/metaclass 继承、模块环境边界；strict 环境读不存在字段报 not declared 而非 nil | class.lua、metaclass.lua、strict.lua、mods.lua、modutil.lua、main.lua:52/61/65-71、worldgen_main.lua:116-149 | api-core.md |
| **dst-mod-scaffolding** | modinfo/modmain/modworldgenmain/modservercreationmain 四入口；modsettings `Add("<id>")` 声明；客户端标签 client_only_mod / all_clients_require_mod | mods.lua、modindex.lua、modutil.lua、modindex.lua:19/98/479 | api-core.md |
| **dst-mod-review-refactoring** | 审查清单：master 权威、存档兼容、事件/任务清理、钩子冲突、废弃 API、性能 | modutil.lua、networkclientrpc.lua、netvars.lua | api-core.md + 全部 api-* |
| **dst-debugging-testing** | 保留第一条有效错误与最小复现；完整错误必须先看 print（`mods.lua:617` 非 debug 丢第二参）；"菜单启用但无效"查 `:474`/`:689` 门禁；错误 UI 被遮罩查 gamelogic | stacktrace.lua、debugprint.lua、consolecommands.lua、mods.lua:617/474/689 | common_bug_patterns.md |
| **dst-performance-profiling** | 服务器 tick 延迟/客户端掉帧：FindEntities 过量、OnUpdate/周期任务、Brain/SG 抖动、实体泄漏、UI 更新开销 | profiler.lua、perfutil.lua、entityscript.lua、simutil.lua、widget.lua | api-core.md + api-ai.md |
| **dst-api-update-diff** | 游戏更新改 scripts 树后的兼容评估：新旧源码快照对比、删除/变更的函数组件/动作/netvar/worldgen/UI、迁移报告 | snapshot/compare 脚本、modutil.lua、mods.lua、entityscript.lua、stategraph.lua、brain.lua、actions.lua、netvars.lua | 全部 api-* |
| **dst-source-research** | 以安装树为 ground truth 查原版实现：定位原生调用点、验证 mod 设计契约 | 源码根 scripts/、modutil.lua、entityscript.lua、scan 脚本 | 全部 api-*（file:line 依据） |
| **dst-workshop-release** | 上架/分发：元数据、语义化版本与兼容区间、依赖、manifest、预览、专服安装、发布前检查 | modindex.lua、mods.lua、modinfo.lua | api-core.md |
| **dst-client-frontend-mods** | 纯客户端 mod：client_only_mod、modservercreationmain 扩展建服前端、本地 HUD、读 replica、保证不要求服务器安装 | mods.lua、modindex.lua、frontend.lua、screens/playerhud.lua、entityreplica.lua | api-ui.md |

## 2. 实体·组件·钩子

| 技能 | 契约要点 | 核心源码锚点 | 关联 |
|---|---|---|---|
| **dst-prefab-authoring** | Prefab 实体构造：Entity 子系统、SetPristine 与 master 模拟顺序、placer、注册 PrefabFiles/Assets | prefabutil.lua、standardcomponents.lua、physics.lua、entityscript.lua、entityreplica.lua | api-prefabs-*.md |
| **dst-component-authoring** | 组件生命周期：Class 定义、OnSave/OnLoad/LoadPostPass/LongUpdate、更新、事件、AddComponentAction、Replica 双文件（`_replica.lua`） | entityscript.lua、entityreplica.lua、components/*_replica.lua、modutil.lua | api-components-*.md |
| **dst-hooking-compatibility** | 钩子安全：AddPrefabPostInit/AddComponentPostInit/AddBrainPostInit/AddStategraphPostInit/AddClassPostConstruct；包装原函数；多 mod 协调；Android 树本地标记处"原版顺序"假设不成立（mods.lua 11 处） | modutil.lua、mods.lua、entityscript.lua | api-core.md |
| **dst-events-tasks-lifecycle** | 事件/任务生命周期：ListenForEvent/RemoveEventCallback、WatchWorldState、DoTaskInTime/DoPeriodicTask、组件更新、睡眠唤醒、回调泄漏与实体移除 | entityscript.lua、scheduler.lua、widgets/widget.lua | api-core.md |

## 3. 网络·分片·存档

| 技能 | 契约要点 | 核心源码锚点 | 关联 |
|---|---|---|---|
| **dst-networking-rpc** | 主机权威 vs 客户端：netvar + dirty 事件、Replica、SetPristine 顺序、AddModRPCHandler/AddClientModRPCHandler、请求校验、防 desync | netvars.lua、networkclientrpc.lua、entityreplica.lua、SGwilson.lua（预测范例） | api-core.md + mod_porting_guide.md |
| **dst-shards-caves-portals** | 分片协调：洞穴/地表传送、玩家迁移、跨 shard 状态、AddShardModRPCHandler、migrationpetsoverrider | shardnetworking.lua、shardindex.lua、networkclientrpc.lua、components/shard_*.lua | api-core.md |
| **dst-persistence-migration** | 存档契约：OnSave/OnLoad/LoadPostPass/LongUpdate、GetPersistData/SetPersistData、版本化数据、实体引用、回滚/卸载/世界迁移不丢状态 | entityscript.lua、savefileupgrades.lua（内置升级，非公开钩子）、map/retrofit_savedata.lua | api-core.md + mod_porting_guide.md |

## 4. 角色·生物·AI

| 技能 | 契约要点 | 核心源码锚点 | 关联 |
|---|---|---|---|
| **dst-character-authoring** | 可玩角色：AddModCharacter（显式 gender）、属性/初始物品/台词/立绘/小地图、SG hook、技能树、多人出生 | player_common.lua、characterutil.lua、speech_*.lua、SGwilson.lua、modutil.lua | character_mod_guide.md + api-prefabs-*.md |
| **dst-creature-boss-authoring** | 完整生物/Boss 编排：prefab+组件+脑+SG+战斗+阶段+小兵+掉落+网络+存档+世界集成 | combat.lua、health.lua、lootdropper.lua、entitytracker.lua、timer.lua、netvars.lua | api-ai.md + api-components-*.md |
| **dst-brain-authoring** | 行为树：Brain/BrainWrangler、PriorityNode/SequenceNode/WhileNode/IfNode、DoAction、自定义节点、AI 目标选择 | brain.lua、behaviourtree.lua、entityscript.lua | api-ai.md |
| **dst-stategraph-authoring** | 状态图：State/EventHandler/TimeEvent/ActionHandler、state tag、超时、动画时间线、服务端与客户端玩家状态 | stategraph.lua、commonstates.lua、SGwilson.lua | api-ai.md |
| **dst-skilltree-authoring** | 技能树：skilltree_defs 数据、节点与前置、激活/停用回调、锁定与亲和、skilltreeupdater、选择持久化、UI 图集 | skilltreedata.lua、prefabs/skilltree_defs.lua、components/skilltreeupdater.lua、widgets/redux/skilltreewidget.lua、modutil.lua（RegisterSkilltreeBGForCharacter/RegisterSkilltreeIconsAtlas） | api-core.md |
| **dst-followers-mounts-pets** | 随从/宠物/坐骑：leader/follower、follower_replica、rideable/rider、domesticatable、忠诚与跨洞穴迁移 | leader.lua、follower.lua、follower_replica.lua、rideable.lua、rider.lua、migrationpetsoverrider.lua | api-components-*.md |

## 5. 物品·战斗·生存

| 技能 | 契约要点 | 核心源码锚点 | 关联 |
|---|---|---|---|
| **dst-inventory-equipment-containers** | 物品/容器：inventoryitem/equippable/stackable/finiteuses/fueled/perishable、container + container_replica、装备符号、物品所有权 | inventoryitem.lua、inventory.lua、stackable.lua、equippable.lua、container.lua、container_replica.lua、containers.lua | api-components-*.md |
| **dst-combat-weapons-projectiles** | 战斗：combat/health/weapon/armor、攻击周期与距离、伤害计算、位面伤害与防御、投射物/AoE、complexprojectile | combat.lua、health.lua、weapon.lua、armor.lua、planardamage.lua、planardefense.lua、projectile.lua、complexprojectile.lua | api-components-*.md |
| **dst-status-buffs-survival** | 属性/Buff：health/hunger/sanity/temperature/moisture/speed、持续伤害、debuffable + Debuff prefab、状态 UI 同步 | debuff.lua、debuffable.lua、health.lua、hunger.lua、sanity.lua、temperature.lua、locomotor.lua | api-components-*.md |
| **dst-food-cooking** | 食物/烹饪：AddIngredientValues/AddCookerRecipe、预制食物数值与腐坏、锅配方优先级、香料/晾晒/食谱书 | cooking.lua、preparedfoods.lua、spicedfoods.lua、edible.lua、stewer.lua、cookable.lua、dryable.lua、perishable.lua | api-components-*.md + 柠版 §7.2 |
| **dst-plants-farming-regrowth** | 植物/农场：growable/pickable/harvestable、farmsoil 交互、farmplantstress、plantregrowth/regrowthmanager、季节生长、存档 | growable.lua、pickable.lua、farming_manager.lua、farmplantstress.lua、plantregrowth.lua、regrowthmanager.lua | api-components-*.md |
| **dst-building-deployment-physics** | 建筑/部署：MakePlacer、deployable candeployfn/ondeploy、workable、碰撞物理（MakeObstaclePhysics）、燃烧/拆除 | prefabutil.lua（MakePlacer/MakeDeployableKitItem）、standardcomponents.lua、deployable.lua、workable.lua、burnable.lua | api-prefabs-*.md |
| **dst-crafting-tech-prototypers** | 配方/科技：AddRecipe2/AddCharacterRecipe/AddRecipeFilter、Ingredient 成本、TechTree/prototyper、图集 | recipe.lua、recipes.lua、techtree.lua、builder.lua、builder_replica.lua、prototyper.lua、modutil.lua | api-core.md |

## 6. 动作·交互·UI

| 技能 | 契约要点 | 核心源码锚点 | 关联 |
|---|---|---|---|
| **dst-action-authoring** | 动作契约：AddAction/AddComponentAction、BufferedAction 流（doer/target/invobject/GetActionPoint）、距离检查、右键/点选动作、SG ActionHandler、客户端预测 | actions.lua、componentactions.lua、bufferedaction.lua、SGwilson.lua、modutil.lua | dst_api_quickref.md「新增动作三件套」 |
| **dst-hud-screens-input** | HUD/屏幕/输入：扩展 PlayerHud/Controls、打开/关闭屏幕弹窗、键盘/手柄、焦点与暂停、重连与玩家替换后 UI 不坏 | screens/playerhud.lua、widgets/screen.lua、controls.lua、badge.lua、input.lua、frontend.lua、modutil.lua | api-ui.md + ui_modification_guide.md |
| **dst-ui-widget-authoring** | 可复用 Widget：继承 Widget/Image/Text/UIAnim/按钮/列表/网格、锚点与缩放模式、焦点导航、手柄、清理回调 | widgets/widget.lua、image.lua、text.lua、uianim.lua、button.lua、grid.lua、pagedlist.lua、controls.lua | api-ui.md + ui_modification_guide.md |

## 7. 世界·地图·生成

| 技能 | 契约要点 | 核心源码锚点 | 关联 |
|---|---|---|---|
| **dst-worldgen-authoring** | 世界生成：modworldgenmain、AddTaskSet/AddTask/AddRoom/AddLevel、拓扑 lock/key、自定义选项、生成失败与断图排查 | worldgen_main.lua、map/levels.lua、tasksets.lua、tasks.lua、rooms.lua、lockandkey.lua、storygen.lua、modutil.lua | api-worldgen.md |
| **dst-worldgen-layouts-retrofit** | 静态布局/Setpiece/旧档补丁：static_layout 内容、注入 setpiece、旧档加内容、防止重复生成 | map/static_layout.lua、object_layout.lua、layout.lua、protected_resources.lua、retrofit_savedata.lua | api-worldgen.md |
| **dst-world-systems-events-weather** | 世界系统：TheWorld 组件、季节/天气/气温、昼夜、全局事件、生成器、世界状态监听 | prefabs/world.lua、world_network.lua、seasons.lua、weather.lua、worldtemperature.lua、entityscript.lua | api-worldgen.md |
| **dst-tiles-map-minimap** | 地皮/地图/小地图：RegisterTileRange/AddTile、tile 与小地图属性、地皮物品、图集、渲染顺序；注册在 modworldgenmain | tilemanager.lua、tiledefs.lua、worldtiledefs.lua、modutil.lua（RegisterTileRange/AddTile/SetTileProperty）、MiniMapEntity | api-worldgen.md + 柠版 §7.20 |
| **dst-ocean-boats-fishing** | 海洋玩法：船/boatphysics/SGboat、划船航行、海钓、平台相对坐标、水上放置、海洋世界生成 | boatphysics.lua、boatcrew.lua、boatleak.lua、SGboat.lua、oceanfishingrod.lua、map/ocean_gen.lua | api-components-*.md + api-worldgen.md |
| **dst-scenarios-setpieces-cutscenes** | 场景/布景/过场：scripts/scenarios、static_layouts、scenario 回调、NIS 序列、一次性事件清理 | map/static_layouts/、map/object_layout.lua | api-worldgen.md |
| **dst-shards-caves-portals** | 见 §3 网络·分片（跨 shard 世界数据同步） | shardnetworking.lua、shardindex.lua | api-core.md |

## 8. 资产·表现·内容

| 技能 | 契约要点 | 核心源码锚点 | 关联 |
|---|---|---|---|
| **dst-assets-animation-atlas** | 动画/纹理资产：Asset 声明、SCML/Mod Tools 编译、SetBank/SetBuild/PlayAnimation、OverrideSymbol、库存图标/立绘/小地图图集 | prefabs.lua、prefabutil.lua、modutil.lua、widgets/image.lua、uianim.lua、itemimage.lua | art.md + mobile_porting_guide.md |
| **dst-audio-camera-effects** | 音效/相机表现：PlaySound/KillSound、循环音、RemapSoundEvent、CameraShake、镜头控制、多人重复排查 | camerashake.lua、cameras/、frontend.lua、modutil.lua（RemapSoundEvent）、mixes.lua、mixer.lua | api-core.md |
| **dst-fx-vfx-authoring** | 特效：FX prefab、AnimState 特效、跟随特效、拖尾/光/Bloom、colouradder、VFXEffect 粒子、本地视觉与复制状态分离 | fx.lua、prefabs/*_fx、emitters.lua、bloomer.lua、colouradder.lua | api-prefabs-*.md |
| **dst-shader-authoring** | 着色器：.vs/.ps/.ksh、ShaderCompiler.exe、bloom-pass、PostProcessor 多通道、AddModShadersInit/AddModShadersSortAndEnable | ShaderCompiler.exe、PostProcessor、SetBloomEffectHandle | api-ui.md |
| **dst-skins-symbol-overrides** | 外观变体：SetBuild、OverrideSymbol/ClearOverrideSymbol、mod 自有"类皮肤"本地变体、避免与官方皮肤/权益/交易系统冲突 | prefabskin.lua、prefabswaps.lua、skinsutils.lua、clothing.lua | dst_api_quickref.md + 柠版 §7.30 |
| **dst-localization-speech** | 本地化/角色台词：STRINGS 名称/描述/配方/动作/UI、speech_*.lua、PO 翻译、性别感知文本、键缺失/覆盖 | strings.lua、translator.lua、speech_wilson.lua、createstringspo.lua、languages/、modutil.lua（LoadPOFile） | api-core.md |

## 9. 专项工具与脚本（新包自带，可直接复用）

- `dst-api-update-diff/scripts/`：`snapshot_dst_source.py` / `snapshot-dst-source.ps1`（抓源码快照）、`compare_dst_snapshots.py` / `compare-dst-snapshots.ps1`（新旧差异→迁移报告）。
- `dst-source-research/scripts/`：`scan_dst_source.py` / `scan-dst-source.ps1`（按关键字扫安装树定位 API 调用点）。
- `dst-assets-animation-atlas/assets/scripts/`：`dst_tex_analyze.py`（KTEX 分析）、`ktex_lib.py`/`ktex_decode.py`/`ktex_ascii.py`/`ktex_batch.py`（KTEX 解码与批量）、`scml_analyze.py`（SCML 分析）、`char_sheet_gen.py`（角色表生成）——与 dst-mod-creater/tools/ 的 15 个工具互补。

## 使用顺序建议

1. 报错/行为异常 → `common_bug_patterns.md`（dst-mod-dev）定位模式；
2. 确认领域契约 → 查本文件对应技能行（契约要点 + 锚点）；
3. 需要源码级依据 → 去 dst-mod-creater/references/api-*.md（13 篇，带官方源码 file:line）；
4. 需要真实模组写法 → `real_mod_patterns.md` / `api_usage_statistics.md`；
5. 柠版特有坑 → `mobile_porting_guide.md` / `character_mod_guide.md` / 柠版适配API文档.md。
