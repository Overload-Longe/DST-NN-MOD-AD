# 泰拉（虚空异界·泰拉）DaxSg Lua 解密流程记录

> 工坊 ID：**2526778484** ｜ Mod 名：虚空异界（泰拉）/Void Realm ｜ version 2.2.5
> 记录时间：2026-09-30 ｜ 来源：群友逆向交付（第一批 895 scripts 明文 + 第二批三件套）+ 本方重组验证
> 状态：**全部受保护 Lua 已解出明文并完成柠版适配**（962 个 Lua 全明文、纹理 9bit、自动文件路径修正）

---

## 一、加密算法真相（取代一切密钥流猜测）

泰拉这批受保护 Lua（main/ 61 个、scripts/ 若干、modmain0/modworldgenmain0 等）的保护
**不是 Lua VM 字节码、不是 XOR 流密码**，而是：

```
保护 = ① 整个文件字节流【倒序】
      ② 再按固定字节替换表 BYTE_MAP（cipher_byte → plain_byte）逐字节替换
```

- **长度完全不变**（倒序+单字节替换都不改变长度）
- **首字节**（0x83 / 0xa3 / 0x18 / 0xd0 等）= 原文件**末尾字节**经替换后的值，**不是**流密钥标志
- 同一 BYTE_MAP 同时解 `main/` 与 `scripts/` 下同格式文件
- 早期做过的 LCG/周期/移位/会话密钥/文件名哈希/0xE1 与 0x83 同源等密钥流分析**全部反证，方向本身错了，勿重试**

## 二、工具

| 文件 | 用途 |
|---|---|
| `terra_daxsg_decode.py` | 解码器：单文件/批量（`--dir`），内置 BYTE_MAP |
| `mapping_best_effort.csv` | 完整字节映射表（cipher_hex, plain_hex, plain_repr, confidence） |

### 用法
```bash
# 单文件
python terra_daxsg_decode.py 加密文件.lua 输出.lua
# 批量（保留相对路径，自动加 .decoded.lua 后缀）
python terra_daxsg_decode.py --dir 加密目录 --out 输出目录
```

### 置信度分级
- **confirmed_ascii**：ASCII/代码语法映射，高置信——英文标识符/控制流/API/路径/数字全部可读
- **statistical_utf8**：中文 UTF-8 多字节统计映射——中文注释/字符串可能仍乱码（**未唯一确定**）
- **unmapped_identity**：恒等——未见/未映射字节原样保留

## 三、main/ 61 模块加密分布（原始清单）

| 首字节 | 数量 | 说明 |
|---|---|---|
| 0x83 | 52 | 常规受保护模块 |
| 0xa3 | 6 | haixingmozunmap / hh_api / lastprism_facetomouse / lastprism_recipe / zenith_facetomouse / zenith_repair |
| 0x18 | 1 | hh_function（1969B） |
| 0xd0 | 1 | hh_tunning（26B） |
| 空 | 1 | tr_buffui.lua（0B，需手工补空文件） |

大文件：tr_world_prefab_hooks 85162B / tr_hex_system 44452B / tr_magic_weapon_actions 47982B /
tr_character_actions 32303B / tr_hermit_fish_task 32067B / tr_dynamic_cave_island 40090B /
tr_component_ui_hooks 34641B / tr_skins_api 37922B

## 四、已解出的明文（群友第二批 source/）

- **main/ 60 个非空明文**
- **scripts/prefabs/ 2 个明文**：snake_scales_fx、tr_stars
- **modmain.lua（34855B）= modmain1 真身**——入口 = `GLOBAL.setmetatable(env, {__index=...})` env 回退 GLOBAL
  + 54 条 modimport 挂载链（scripts/magic_ui.lua、tr_hook、tr_hook_builder、containers_tr、
  tr_tanceqi_init、tr_globalfn、modinit/baiyu_sg 等）
- **modworldgenmain.lua（22625B）= modworldgenmain1**（GLOBAL. 前缀安全化）
- **modservercreationmain.lua（7856B）**
- **modinfo.lua（31436B）**
- 另有 `protected_originals/`（modmain.lua 39660B VM 解码器、modmain0.lua 100724B、
  modworldgenmain0.lua 95738B 等未解原件）、`known_readable_originals/`（存档）、tools/、mapping、
  syntax_check.tsv（62 脚本全过 Lua 5.4 语法）、反混淆说明.txt

### 关于 0xE1 DaxSg 包装层（modmain0 / modworldgenmain0）
群友说明："没必要继续反编译，包内已有可读入口"。**重组明文 mod 时直接删除这两个 0xE1 文件**
（真身 modmain.lua 加载链 0 次引用 VM 解码器全局——2K7lHntxTJMZs/S9DB0XMEzAjX/eyUfdkpLNibIYx/
DaxSg_mod/daxsg_ 全 0），以真身 modmain.lua 为准。用户实测诊断包崩溃根因（柠版 VM 解码器
`arithmetic on local 'C'/'N'`）在移除解码器后消除。

## 五、重组 + 柠版适配流程（已验证，可复现）

1. **解压工坊原版包** → 全资源（tex/anim/images/levels/sound/...）
2. **明文覆盖**：modmain/modworldgenmain/modservercreationmain + main/60 + scripts/895
   + 补 tr_buffui.lua 空文件 + modmain1/modworldgenmain1 覆盖为明文
   → **删除 modmain0/modworldgenmain0**（0xE1，不再需要）→ 962 Lua 全明文
3. **一键工具适配**：`dst_mobile_adapter.py 源目录 --native --zip`（2023 纹理转 ASTC 8x8、
   自动文件 early_prefab_auto 1024 条/mod_auto/preload_assets 含 minimap 11 条/sound_banks/
   tile_preload 103 条/test、防御修复、打包 3803 文件 100.6MB）
4. **9bit 修复**（柠版标准 = KTEX flags bit9=1，0xFFF02380）：顶层 908 tex + anim zip 内部
   1004 个 zip 逐一解压改头重压（`fix_9bit2.py`）
5. **路径修正**：自动文件前缀 `scripts/mods/虚空异界（泰拉）/Void Realm/` → `scripts/mods/虚空异界（泰拉）/`
   （单层安装，去 /Void Realm/；泰拉源码里 Void Realm 引用均为 mod 标识/日志/文本，非路径，不需改）
6. **验证**：908 tex 9bit 全过 / anim zip 内部 9bit 全过 / minimap 14 tex 全过 / levels 86 tex 全过 /
   路径前缀 0 残留 / BOM 保持 / 单层顶层 3803 文件

## 六、关键判据速查

- **柠版纹理标准**：`0xFFF02380`（KTEX 头字节 `80 23 f0 ff`——ASTC 8x8 单 mip + bit9=1）。
  更多料理 v3.44 / AIP v3.40 全部 tex 逐字节一致。bit9=0（0xFFF02180）→ 纹理加载异常/动画空白类问题。
- **minimap 图集三件套**（§7.20）：ASTC 数据 + 头 bit9=1 + **必须进 preload_assets_auto.lua 清单**
  （泰拉 images/minimap/ 11 个 xml 已在清单）
- **保护文件识别启发式**：首字节在 BYTE_MAP 表内（0x83/0xa3/0x18/0xd0...）+ 长度不变 → 可试本解码器

## 七、遗留（已知限制）

- 中文 UTF-8 替换表未唯一确定——如需逐字节中文原文需另解（当前统计映射 → 中文注释/字符串乱码，
  但英文标识符/控制流/API/路径/数字全部可读）
- 语法过 ≠ 游戏运行时行为验证过（重组包功能由用户手机实测验收）
- modmain0/modworldgenmain0（0xE1）未解但明文入口可用——仅当需还原 VM 原逻辑才涉及
