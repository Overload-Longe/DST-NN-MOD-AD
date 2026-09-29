# 柠版（手机端 DST）Mod 适配 API 文档 · 精要版

> 完整版 341KB（5763 行）位于 C:\Users\Longe\下载\工具转换\柠版适配API文档.md；SKILL.md 与 references/ 已含核心要点。本精要版保留全部 ## 章节及其子节标题，供 AI 快速定位。

## 柠版（手机端 DST）Mod 适配 API 文档

## 1. 柠版与 FW_ 框架

## 2. 环境检测（每次排障/写代码第一步）

## 3. API 总览（快速索引）

## 4. 资源与预制物
> 子节：FW_PreloadAssets(modname, {路径...}) / FW_LoadPrefabs(modname, PrefabFiles)

## 5. 配方
> 子节：FW_RegisterRecipe(modname, {...})

## 6. Replica 网络组件
> 子节：FW_AddReplicableComponent(name)

## 7. 移动端 UI
> 子节：7.1 FW_RegisterModButton(modname, {...}) —— 按钮栏按钮 / 7.2 框架内部按钮 API（一般不直接调用） / 7.3 FW_RegisterModUI(modname, widget, {...}) —— 可编辑悬浮 UI / 7.4 FW_RegisterHUDWidget(widget, id, {...}) / 7.5 FW_RegisterEditable(modname, proxy_widget, key, {...}) / FW_FindEditable(target) / 7.6 HUD 编辑模式接口

## 8. 触摸与拖拽
> 子节：FW_BindWidgetTouch(modname, widget, {...}) / widget 约定字段（框架与 Mod 的隐式契约，改名即失效）

## 9. 任务调度
> 子节：FW_DoTaskInTime / FW_DoPeriodicTask(modname, inst, taskid, ...)

## 10. 方法钩子
> 子节：FW_WrapMethod(modname, object, method, hookname, wrapper)

## 11. 远程武器 / 通用瞄准轮盘（RANGED_AIM）
> 子节：FW_RegisterRangedWeapon(modname, {...})

## 12. 容器 widget 兼容
> 子节：FW_NormalizeContainerWidgetInfo(widget)

## 13. 内部注册表（排障读状态）

## 14. 客户端配置持久化

## 15. 大 Mod 适配架构（棱镜 & 能力勋章）
> 子节：15.1 棱镜（[DST] 棱镜 / Legion 7.6.5） / 15.2 能力勋章（Medal） / 15.3 通用适配套路

## 16. 柠版适配自动生成文件

## 17. 常见 Bug 速查表

## 18. 手机端适配验收清单

## 19. 实战适配模式（补充自 `个人适配柠版mod`）
> 子节：19.1 按钮延迟注册（等 Mod 资源加载完，避免进游戏卡住） / 19.2 全局桥接：rawset 挂 UI 实例供按钮回调使用 / 19.3 FW 按钮替代原生 UI 入口（隐藏原入口图标） / 19.4 AddSimPostInit 延迟注册 —— 替代失效的 `ModManager.RegisterPrefabs` hook / 19.5 FW_RegisterModUI 封装层 + IsMobile 守卫 + pcall 失败处理 / 19.6 FW_LoadPrefabs 条件调用（PC 端跳过） / 19.7 抑制原生方法报错（pcall 包装，防崩但不吞问题） / 19.8 UI 按屏幕尺寸动态缩放（手机端通用） / 19.9 功能裁剪式移植（大 Mod 的柠版精简版）

## 附录：框架运行日志标识

## 20. 一键适配柠版工具（dst_mobile_adapter.py）
> 子节：★ 20.0 最终结论速查（AIP 十四轮迭代后唯一有效的适配路线，2026-09-12 用户实测"完全正常"） / 20.1 用法 / 20.2 工具做的事（对应本手册各章） / 20.3 KTEX 解析关键实现（踩坑记录） / 20.4 AIP 大 Mod 适配模式（工具生成的兼容层结构） / 20.5 strict.lua 环境坑：RegisterFW 严禁读 GLOBAL.Assets（AIP 实战教训） / 20.5b 变种：AddRecipe2 不在 GLOBAL 上（modmain 环境注入 API）——modimport 兼容层裸读报错 / 20.6 Lua 5.1 隐式 arg 表在柠版为 nil → unpack(arg) 游戏内闪退（AIP 实战教训） / 20.6b 变种：vararg 函数**直接引用**隐式 arg（不经过 unpack）——进入世界后闪退 / 20.7 世界内动画空白（物品/装备/武器）——动画资源加载通道缺失（AIP 实战第六轮）

## 20.8 ★ 动画 build 注册 vs 预加载（动画空白最终根因，AIP 实战第七轮）

## 20.9 ★ FW_LoadPrefabs 接管破坏 build 收集链（动画空白最终结论，AIP 实战第八轮）

## 20.10 ★ 纯原生模式 --native（动画空白最终解决方案，AIP 实战第九轮）

## 20.11 ★ asset_case_aliases owner 校验（--native 必踩坑，AIP 第十轮）
> 子节：20.11b ★ modinfo 单引号 name → modname 回退目录名 → owner 错（英雄联盟武器 2026-09-13） / 20.11c ★★ modicon.xml 别名跨 mod 冲突 → ambiguous asset case alias（2026-09-13）

## 20.12 ⚠️ 已废弃（被 §20.14 推翻）：prefab 多 ANIM 原生收集不可靠 → Assets 全量提升（AIP 第十一轮）

## 20.13 ⚠️ 已废弃（被 §20.14 推翻）：Assets 表加载上限（~256 条）→ 智能补缺（AIP 第十二轮）

## 20.14 ★ early_prefab_auto.lua = 柠版动画唯一有效通道（AIP 第十四轮，手持/皮肤空白终解）

## 20.15 ★ 自定义 Scroller 柠版触摸滚动适配（AIP 书籍/图鉴 UI，AIP 第十五轮）
> 子节：20.15.1 ★ 工具 --touch-scroll 注入的卡加载坑（AIP 第十六轮实测，工具双括号 bug） / 20.15.2 ★★ modmain require 注入路线废弃 → 改滚动类文件注入（AIP 第十七轮实测） / 20.15.3 ★★★ 触摸只挂 black（命中垫层）→ 可交互子项区域无法滑动（AIP 第十八轮实测）

## 20.17 ★ 通用规则库（工具自动，不依赖 per-mod 补丁）
> 子节：20.17.1 按钮注册通用规则（替代手工 FW_RegisterModButton 写法）

## 20.18 ★ 通用防御性修复注入（工具自动，英雄联盟武器 nil 防护的通用化）
> 子节：20.18.1 fx 特效变量判空 / 20.18.2 target 判空 / 20.18.3 滚动条触屏崩溃（lastx nil）兜底 / 20.18.4 边界（工具做不了的，需人工处理） / 20.18.5 验证口径

## 20.16 AIP 书籍页面结构（元素/位置/大小/信息/滑动）——后续 UI 适配参考
> 子节：20.18.3b ★ ScrollableList 系跳过自定义触摸注入（v1.4.4，LOL 左侧滑动闪烁实证） / 20.18.3c ★ ScrollableList 系拖动重写（v1.4.5，LOL 图鉴左侧"拖动滑块无效"实证） / 20.18.3d ★ StartUpdating 关键点 + SetWhileDown 无守卫重写（v1.4.7，"根本划不动"实证） / 20.18.3e ★ content_root 整体平移渲染模型（v1.4.8，"滑动后一直闪烁"实证） / 20.18.3f ★ content_root 创建必须限定 ctor 范围（v1.4.9，"卡加载"实证）

## 1. 柠版与 FW_ 框架

## 2. 环境检测（每次排障/写代码第一步）

## 3. API 总览（快速索引）

## 4. 资源与预制物
> 子节：20.18.3g ★ 平移模型只对"分组式列表"注入（v1.4.10，"拖动滑块依旧闪烁"实证） / 20.18.3h ★ 拖动步进改浮点逼近（v1.4.11，"依旧闪烁"实证 + 手工版 ScrollingGrid 启示） / 20.18.3i ★ 平移直动 + 跨整步刷新（v1.4.12，最终性能修复） / 20.18.3j ★ 列表本体触摸拖动（v1.4.13，"左侧列表拖不动"实证） / 20.18.3k ★ OnTouch 原生触摸通道 + RefreshView 视口裁剪（v1.4.14，两问题实修） / 20.18.3l ★ 方向修正 + 滑块 marker OnTouch 跟手（v1.4.15，闪烁真正根因） / 20.18.3m ★ 首屏溢出修复 + 滑块方向修正 + DoDragScroll 固定基准（v1.4.16） / 20.18.3n ★ 列表/滑块语义分流（v1.4.17，滑块方向反真正根因） / 20.18.3o ★ 滑块跟手比例修复：除以 scroll_bar_container 竖向缩放（v1.4.18） / 20.19 GUI 流程可选化：适配流程全部可勾选（v1.4.19） / 20.18.3n ★ 滑块方向最终结论：坐标轴方向判定（v1.4.17） / FW_PreloadAssets(modname, {路径...})…

## 5. 配方
> 子节：FW_RegisterRecipe(modname, {...})

## 6. Replica 网络组件
> 子节：FW_AddReplicableComponent(name)

## 7. 移动端 UI
> 子节：7.1 FW_RegisterModButton(modname, {...}) —— 按钮栏按钮 / 7.2 框架内部按钮 API（一般不直接调用） / 7.3 FW_RegisterModUI(modname, widget, {...}) —— 可编辑悬浮 UI / 7.4 FW_RegisterHUDWidget(widget, id, {...}) / 7.5 FW_RegisterEditable(modname, proxy_widget, key, {...}) / FW_FindEditable(target) / 7.6 HUD 编辑模式接口

## 8. 触摸与拖拽
> 子节：FW_BindWidgetTouch(modname, widget, {...}) / widget 约定字段（框架与 Mod 的隐式契约，改名即失效）

## 9. 任务调度
> 子节：FW_DoTaskInTime / FW_DoPeriodicTask(modname, inst, taskid, ...)

## 10. 方法钩子
> 子节：FW_WrapMethod(modname, object, method, hookname, wrapper)

## 11. 远程武器 / 通用瞄准轮盘（RANGED_AIM）
> 子节：FW_RegisterRangedWeapon(modname, {...})

## 12. 容器 widget 兼容
> 子节：FW_NormalizeContainerWidgetInfo(widget)

## 13. 内部注册表（排障读状态）

## 14. 客户端配置持久化

## 15. 大 Mod 适配架构（棱镜 & 能力勋章）
> 子节：15.1 棱镜（[DST] 棱镜 / Legion 7.6.5） / 15.2 能力勋章（Medal） / 15.3 通用适配套路

## 16. 柠版适配自动生成文件

## 17. 常见 Bug 速查表

## 18. 手机端适配验收清单

## 19. 实战适配模式（补充自 `个人适配柠版mod`）
> 子节：19.1 按钮延迟注册（等 Mod 资源加载完，避免进游戏卡住） / 19.2 全局桥接：rawset 挂 UI 实例供按钮回调使用 / 19.3 FW 按钮替代原生 UI 入口（隐藏原入口图标） / 19.4 AddSimPostInit 延迟注册 —— 替代失效的 `ModManager.RegisterPrefabs` hook / 19.5 FW_RegisterModUI 封装层 + IsMobile 守卫 + pcall 失败处理 / 19.6 FW_LoadPrefabs 条件调用（PC 端跳过） / 19.7 抑制原生方法报错（pcall 包装，防崩但不吞问题） / 19.8 UI 按屏幕尺寸动态缩放（手机端通用） / 19.9 功能裁剪式移植（大 Mod 的柠版精简版）

## 附录：框架运行日志标识

## 20. 一键适配柠版工具（dst_mobile_adapter.py）
> 子节：★ 20.0 最终结论速查（AIP 十四轮迭代后唯一有效的适配路线，2026-09-12 用户实测"完全正常"） / 20.1 用法 / 20.2 工具做的事（对应本手册各章） / 20.3 KTEX 解析关键实现（踩坑记录） / 20.4 AIP 大 Mod 适配模式（工具生成的兼容层结构） / 20.5 strict.lua 环境坑：RegisterFW 严禁读 GLOBAL.Assets（AIP 实战教训） / 20.5b 变种：AddRecipe2 不在 GLOBAL 上（modmain 环境注入 API）——modimport 兼容层裸读报错 / 20.6 Lua 5.1 隐式 arg 表在柠版为 nil → unpack(arg) 游戏内闪退（AIP 实战教训） / 20.6b 变种：vararg 函数**直接引用**隐式 arg（不经过 unpack）——进入世界后闪退 / 20.7 世界内动画空白（物品/装备/武器）——动画资源加载通道缺失（AIP 实战第六轮）

## 20.8 ★ 动画 build 注册 vs 预加载（动画空白最终根因，AIP 实战第七轮）

## 20.9 ★ FW_LoadPrefabs 接管破坏 build 收集链（动画空白最终结论，AIP 实战第八轮）

## 20.10 ★ 纯原生模式 --native（动画空白最终解决方案，AIP 实战第九轮）

## 20.11 ★ asset_case_aliases owner 校验（--native 必踩坑，AIP 第十轮）
> 子节：20.11b ★ modinfo 单引号 name → modname 回退目录名 → owner 错（英雄联盟武器 2026-09-13） / 20.11c ★★ modicon.xml 别名跨 mod 冲突 → ambiguous asset case alias（2026-09-13）

## 20.12 ⚠️ 已废弃（被 §20.14 推翻）：prefab 多 ANIM 原生收集不可靠 → Assets 全量提升（AIP 第十一轮）

## 20.13 ⚠️ 已废弃（被 §20.14 推翻）：Assets 表加载上限（~256 条）→ 智能补缺（AIP 第十二轮）

## 20.14 ★ early_prefab_auto.lua = 柠版动画唯一有效通道（AIP 第十四轮，手持/皮肤空白终解）

## 20.15 ★ 自定义 Scroller 柠版触摸滚动适配（AIP 书籍/图鉴 UI，AIP 第十五轮）
> 子节：20.15.1 ★ 工具 --touch-scroll 注入的卡加载坑（AIP 第十六轮实测，工具双括号 bug） / 20.15.2 ★★ modmain require 注入路线废弃 → 改滚动类文件注入（AIP 第十七轮实测） / 20.15.3 ★★★ 触摸只挂 black（命中垫层）→ 可交互子项区域无法滑动（AIP 第十八轮实测）

## 20.17 ★ 通用规则库（工具自动，不依赖 per-mod 补丁）
> 子节：20.17.1 按钮注册通用规则（替代手工 FW_RegisterModButton 写法）

## 20.18 ★ 通用防御性修复注入（工具自动，英雄联盟武器 nil 防护的通用化）
> 子节：20.18.1 fx 特效变量判空 / 20.18.2 target 判空 / 20.18.3 滚动条触屏崩溃（lastx nil）兜底 / 20.18.4 边界（工具做不了的，需人工处理） / 20.18.5 验证口径

## 20.16 AIP 书籍页面结构（元素/位置/大小/信息/滑动）——后续 UI 适配参考
> 子节：20.20 pcall 多返回值错取崩溃：sf 缩放取数（v1.4.20） / 20.21 滑块拖远后比手慢：拖动中 1:1 跟手（v1.4.21） / 20.22 GUI 取消功能：真中断（v1.4.22）

## 21. 人物（角色）Mod 适配
> 子节：21.1 人物 Mod 两大类（20 个清单） / 21.2 新角色 prefab 标准模板（`MakePlayerCharacter`，沃尔 whorl 实证） / 21.3 原版角色增强模板（3 种实证） / 21.4 技能树模式（DST 官方 skilltreeupdater） / 21.5 env 环境接管模式（角色 mod 通用头） / 21.6 柠版适配要点（20 个已适配 mod 实证） / 21.7 资源规模参考表（适配工作量预估）

## 20.23 角色按键技能 → 柠版按钮（v1.4.23）
> 子节：两类实证模式（自动识别） / 去重（图标按钮已有对应键盘常量 → 不重复注册） / 注入产物（千年狐实证）

## 20.24 ★ v1.4.24：备份/恢复 + 按键四通道扫描 + KTEX flags 高位对齐 + FW_SimulateKey 可选（2026-09-14，APK 逆向借鉴落地）
> 子节：20.24.1 注入前备份 modmain —— ⚠️ 已移除（v1.4.25，用户决定"没什么用"） / 20.24.2 按键技能扫描补全四通道（借鉴 APK KeyScanner） / 20.24.3 KTEX flags 高位对齐（2878 tex 实证） / 20.24.4 FW_SimulateKey 可选模拟按键（`--simulate-key`，默认关闭） / 20.24.5 验证

## 20.25 ★ v1.4.26：tile_preload_auto.lua 生成（levels/ 自定义地形预加载，荔只只物语对比实证）
> 子节：20.25.1 这是什么 / 为什么必须 / 20.25.2 格式（与棱镜/永不妥协/荔只只物语手工版逐字一致） / 20.25.3 工具实现 / 20.25.4 验证 / 20.25.5 荔只只物语对比结论（本能力来源）

## 22. 新版柠版内置 mod 库 API 增量（v1.4，2026-09-15 全量扫描 124 mod）
> 子节：22.1 全新 FW_* API（9 个，v1.3 未记录） / 22.2 已知 API 字段扩展（跨 20+ mod 实证） / 22.3 非 FW_ 前缀的框架级新 API / 22.4 新全局表 / 常量 / 命名约定 / 22.5 机制沉淀（新模式总结） / 22.6 工具改进实施（dst_mobile_adapter.py v1.5.0，§20.26-20.28 已落地） / 22.7 已知坑补充 / 22.8 已知 mod 版本与改动清单（本批新发现，2026-09-15）

## 23. 更多料理 Heap of Foods 大 Mod 适配机制沉淀（2026-09-16~20 全程实测）
> 子节：23.0 总流程 / 23.1 ★ modimport 与 require 实例隔离 → GLOBAL 共享表 / 23.2 ★ AddCookerRecipe 第三参 / cookbook_atlas / no_cookbook / 23.3 ★ init_postinit.lua 改表必须整体重建 / 23.4 strict 环境 GLOBAL 字段裸读 → rawget / 23.5 大入口模块拆分恢复 / 23.6 汉化大表卡加载 → 精简表 / 23.7 postinit 分级恢复 + 审计脚本 / 23.8 编码统一 vs 真实改动（对比脚本） / 23.9 ★ 原版物品图标通道错乱（正确解 = 改数据指原版图集） / 23.10 遗漏审计必须追间接加载链 / 23.11 setfenv 全局接管文件 → 显式 GLOBAL 安全化改写…

## 24. 工具 v1.6.0 P0 四项（2026-09-17 实施，7.17-7.19）
> 子节：24.1 P0 四项 / 24.2 回归抓到的 2 个新 bug

## 25. ★ 自建 minimap 图集三件套（7.20，紫白乱码终解）

## 26. 手机端新坑速查（7.21-7.28）
> 子节：26.1 ★ 手机端"点选施法" target=nil（point 施法 pos 表） / 26.2 ★ 超宽屏容器格子偏左：对照 PC 原版源码（勿加位移补偿） / 26.3 ★ 弹射/法球伤害"时有时无"：绕过 combat:GetAttacked 直接 DoDelta / 26.4 ★ 柠版 CollectSpDamage 不工作：hook 手动补 planardamage / 26.5 ★ FROMNUM = 引擎 bank 解析失败哨兵（非 Lua 字面量） / 26.6 ★ 柠版无 components/soundemitter：modmain 顶层裸 require → 卡加载 / 26.7 ★ 原版动画补包黑块 → 直接引用 APK 原版（7.27 终解） / 26.8 ★ 尾 BOM（\ufeff）语法炸弹：禁止整文件重建 lua

## 27. ★ 头顶等级/Label 显示：直接抄原版实现（7.29 终解）
> 子节：27.1 已证伪四案（勿重试） / 27.2 正确解 = 原版实现（一字不改） / 27.3 铁律

## 28. 柠版 mod 打包规范（技能 §8，勿再错）

## 29. ★ 丰耘秘境全案：加密皮肤删除/全皮肤解锁/图鉴面板/Replica 时序（v26z-v27e，9 轮实测）
> 子节：29.1 背景 / 29.2 Klei DLC 加密皮肤（.dyn 0xC5949293）——删除变体保留默认（v26z） / 29.3 皮肤所有权全解锁（v27b） / 29.4 图鉴收集进度 0/0（v27c） / 29.5 图鉴皮肤网格图标空白（v27d） / 29.6 ★ Replica 同步时序崩溃（v27e） / 29.7 通用排查链（图鉴皮肤显示）

## 30. 《传奇武器附魔强化》PC→柠版实战沉淀（2026-09-27，长期维护）
> 子节：30.1 ★ endlocal 词法粘连 = mod 被禁用（同类词法坑，与 §28 尾 BOM 并列） / 30.2 ★ Insight/全能信息面板注入失效排查（dyc_panel_compat） / 30.3 召唤 boss prefab 缺失 → 明确提示（外部模组依赖） / 30.4 ★ mod 自定义 prefab 图标兜底（GetImageAsset 找不到 → custom_xml/custom_tex） / 30.5 BGM 删除优化体积（接口保留） / 30.6 外部模组 boss 贴图降级（use_text_display） / 30.7 ★ inventoryitem 组件时序：SetPristine 前加组件 = 前端 Spawn 即崩（v3.22 闪退全案） / 30.8 ★ prefab 文件内 AddInventoryItemAtlas → "prefab file is not callable"（加载失败 ≠ 语法错误） / 30.9 ★ 图标 fallback 空纹理 = 引擎级闪退（无 Lua error）+ 多 mod 扩展 player_classified 冲突 / 30.10 ★ 柠版跃迁/传送通道全案（丰耘凶险手杖/护甲，v14.52-v14.67 终解）：状态机组件链三级 nil→GoToState 不可行 / 通道选型表（DoTouchSpecialAction 限距≈150 / ExecuteConsoleCommand 仅主机 / SendRemoteExecute 仅客机管理员 / 普通 Mod RPC 单通道终选） / 消耗复用 hmrblinker:BlinkIn/BlinkOut（onblinkin=粘液+耐久+特效） / 客户端动画 AnimState+DoPeriodicTask 轮询 AnimDone（1.5s 超时兜底） / strict 局部变量自引用坑=先声明后赋值 / 兜底 return {} 卡全图交互铁律