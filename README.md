# DST-NN-MOD-AD —— 柠版（手机端 DST）Mod 适配技能库

> 由《传奇武器附魔强化》PC→柠版长期适配实战沉淀。供其他 AI / 开发者直接加载使用。
> 仓库：Overload-Longe/DST-NN-MOD-AD

## 三块内容

| 目录 | 内容 | 说明 |
|---|---|---|
| `dst-mod-dev/` | **技能包**（SKILL.md + references 知识库 + tools 工具） | AI 加载 `dst-mod-dev/SKILL.md` 即获得完整适配方法论 |
| `docs/` | 柠版适配 API 文档 | 完整版 341KB 超单文件推送上限，仓库收录**精要版**（章节导航） |
| `传奇武器附魔强化/` | 实战 mod 文本源码（测试占位） | 完整源码 zip 交付（见交付记录），仓库放代表文件供结构参考 |

## dst-mod-dev/ 技能包结构

```
dst-mod-dev/
├── SKILL.md                        # 主技能（v1.9.8 压缩版，AI 加载入口）
├── references/
│   ├── common_bug_patterns.md      # 常见 Bug 模式与修复
│   ├── mod_porting_guide.md        # 移植/兼容性适配指南
│   ├── mod_structure.md            # 标准结构/模板
│   ├── dst_api_quickref.md         # DST API 速查
│   ├── ui_modification_guide.md    # UI 修改指南
│   ├── api_usage_statistics.md     # 100 模组 API 使用统计
│   ├── real_mod_patterns.md        # 真实模组实现手法
│   ├── mobile_porting_guide.md     # 柠版移动端适配专项（核心）
│   └── character_mod_guide.md      # 人物 Mod 适配专项
└── tools/
    ├── convert_dxt5_to_rgba.py     # DXT5→RGBA 纹理修复（可运行）
    ├── 柠版一键适配.bat            # 拖拽一键适配入口
    └── dst_mobile_adapter.py       # 全功能一键适配器（187KB，超单文件上限未入库，见下）
```

## 未入库的大文件（本地完整版位置）

| 文件 | 大小 | 未入库原因 | 本地位置 |
|---|---|---|---|
| `dst_mobile_adapter.py`（完整源码） | 187KB | 超单文件推送上限 | `C:\Users\Longe\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\dst-mod-dev\tools\` |
| `柠版适配API文档.md`（完整版） | 341KB | 同上（仓库已收录精要版） | `C:\Users\Longe\下载\工具转换\` |
| `dst-mod-creater/`（第三方配套知识库） | 36MB / 635 文件 | 二进制+体积（MIT 许可独立包） | 同上 skills 目录内 |
| mod 完整源码（326 文件） | 4.3MB zip | 二进制+数量 | 交付包：`C:\Users\Longe\下载\传奇武器附魔强化-柠版适配版.zip` |

需要以上完整文件时，直接向作者（Overload-Longe）索取即可。

## 核心适配规范摘要（详见 SKILL.md / mobile_porting_guide.md）

1. **纹理**：全部转 ASTC 8x8 单 mip（KTEX comp=24, flags=4）；自建图集一律 ASTC，禁用 RGBA（Mali GPU 0x500 实测）
2. **编码**：`.lua` 必须 UTF-8 BOM + CRLF；禁止 decode+join+encode 整文件重建（尾 BOM 语法炸弹）；`sound_banks_auto/tile_preload_auto` 无 BOM
3. **动画**：`early_prefab_auto.lua` = 柠版动画唯一有效通道——anim/ 目录**每个 zip 一条**（含 swap/皮肤）
4. **图标**：原版物品图标改 `recipe.atlas` 指柠版原版图集（无子目录路径）；mod 自定义 prefab 补 `custom_xml/custom_tex`
5. **strict 环境**：`GLOBAL` 字段裸读报 not declared → `rawget`；挂载点 API（AddRecipe2 等）在 modmain env 不在 GLOBAL
6. **Lua 5.1→5.2**：裸 `arg` → 注入 `local arg={...}`；`unpack(arg)` → `unpack({...})`
7. **手机端施法**：右键点实体 = point 施法 target=nil + pos 表 → 两路解析
8. **打包**：zip 内套 mod 文件夹 + 全正斜杠 + compresslevel=6
9. **按钮/触摸**：FW_RegisterModButton（必传 character）；自定义滚动条 → TEMPLATES.ScrollingGrid
10. **词法坑**：`endlocal` 粘连、尾 BOM（\ufeff）→ mod 被禁用/卡加载；先搜 `Disabling <mod>` 排除上游

## 实战沉淀索引（SKILL.md §7 / docs §20-§30）

- §7.21 手机端点选施法 target=nil
- §7.22 超宽屏容器格子偏左（对照 PC 原版源码）
- §7.23 弹射伤害时有时无（绕过 GetAttacked 直接 DoDelta）
- §7.24 CollectSpDamage 不工作（hook 手动补 planardamage）
- §7.25/§7.27 FROMNUM 哨兵 / 原版动画直接引用 APK
- §7.28 尾 BOM 语法炸弹
- §7.29 头顶等级显示（直接抄原版实现）
- §7.30 丰耘秘境（加密皮肤/全解锁/图鉴/Replica 时序）
- §7.31 柠版 nil 防护全景（strict/setfenv/ToolUtil）
- §7.32 endlocal 词法粘连 + Insight 注入排查
- §30 传奇武器实战六条沉淀（endlocal/Insight/召唤提示/图标兜底/BGM 删除/贴图降级）

## 使用方式（给其他 AI）

1. 读取 `dst-mod-dev/SKILL.md` 获得完整工作流与触发边界
2. 排障/适配时按需读取 `references/` 对应文件
3. 需要执行适配时：本地安装 `dst_mobile_adapter.py` 完整版（向作者索取），或用 `convert_dxt5_to_rgba.py`（已入库可直接运行）
4. 深度知识查 `docs/柠版适配API文档-精要版.md` 章节导航，细节回查完整版