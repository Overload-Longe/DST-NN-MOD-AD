# 柠版（手机端 DST）Mod 适配指南

> 本文档沉淀自「趣味食物（食趣）」Mod 在柠版（手机端/雷电模拟器）的实战适配经验，
> 覆盖贴图/动画空白、纯黑块、闪退、配方失效等高频问题。所有结论均经实际验证。

## 适用场景

把 PC 端 Mod 装到手机端「柠版」（雷电模拟器等）后出现以下任一现象：

- 食物/物品贴图空白或纯黑块
- 物品图标右下角出现黑色 ■
- 进游戏卡在加载页面
- 自定义厨具/调味站点击闪退
- 调味品用后产出失败食物（潮湿黏糊）
- 右键道具点击无反应

---

## 1. 贴图/动画空白（纯黑块）诊断速查表

| 现象 | 根因 | 修复 |
|------|------|------|
| 背包/物品栏图标正常，动画贴图全黑 | `anim/*.zip` 内 atlas 纹理为 DXT5，Mali GPU 不支持 | 转 RGBA |
| 物品图标右下角黑色 ■ | 角标动画包（如品质角标）同为 DXT5 | 同上 |
| 地上/锅里食物纯黑块 | 食物动画包 DXT5 | 同上 |
| 背包图标也空白 | 物品栏图集未预加载 | 补 preload 清单 |
| 动画完全不显示 | anim zip 未预加载 | 补 early_prefab 清单 |

**快速判断**：背包图标来自独立 `.tex`（物品栏图集，通常已是 RGBA），动画贴图来自
`anim/*.zip` 内的 atlas 纹理（可能 DXT5）。如果图标正常但动画黑，几乎必然是 DXT5 问题。

---

## 2. KTEX 纹理格式与 DXT5→RGBA 转换

### KTEX 格式（逆向确认）

- 8 字节头：`"KTEX"` + 4 字节 header（uint32 LE）
- header 位域：
  - `compression`：bit 4-8（**2 = DXT5**，**4 = RGBA**）
  - `mipmap_count`：bit 13-17
  - `flags`：bit 18+（0 = RGBA 无压缩，3 = DXT5）
- 每 mip 10 字节 pre：`uint16 w, uint16 h, uint16 pitch, uint32 datasz`
- 随后按序排列各 mip 像素数据

### 根因

Android Mali GPU **不支持 DXT/BC 压缩纹理**，解码失败 → 渲染为纯黑。
桌面 GPU 正常显示，所以这类问题只在手机端出现。

### 修复

把 `anim/*.zip` 内所有 `atlas-0.tex` / `atlas-1.tex` 从 DXT5(compression=2) 转成
RGBA(compression=4)，`build.bin` / `anim.bin` 保持原样。独立 `.tex`
（物品栏图集 / modicon / 厨师图鉴 / minimap）通常已是 RGBA，无需转换。

**工具**：`tools/convert_dxt5_to_rgba.py`（纯 Python BC3 解压，不依赖 ktools）
用法：`python convert_dxt5_to_rgba.py <Mod根目录>`

### 2.1 ★ KTEX flags 位（动画全空白根因，AIP 实战第四轮）

**现象**：背包图标正常，但**世界内动画全空白**（地上物品、穿在身上装备、手持武器）。
不是 DXT5 问题（已转 ASTC 8x8），不是别名冲突（全量扫描 0 冲突）。

**根因**：转换工具生成 KTEX 头时只重写 compression(bit4-8)/mip(bit13-17) 位，
**保留了原 DXT5 头的 flags 位(bit18+)**（如 7）。引擎按 flags 判断纹理格式，
flags=7 解码失败 → 该 mod 所有动画空白。**正常柠版 mod（棱镜/馨食记实测）的
ASTC 头 = `comp=24, mip=1, flags=4`**。

**校验**（python 读 anim zip 内 atlas tex 头）：
```python
h = struct.unpack('<I', d[4:8])[0]
comp, mip, flags = (h>>4)&0x1F, (h>>13)&0x1F, (h>>18)&0x7
# 期望 ASTC: (24, 1, 4)   RGBA: (4, 1, 0)
```
任何 flags≠4 的 ASTC 头都必须重写：`hdr & ~(0x7<<18) | (4<<18)`。
`dst_mobile_adapter.py` 已修复（ASTC flags=4、RGBA flags=0），生成后全量校验通过。

> **后续更新（AIP 第六轮）**：flags 修复后仍空白——flags 只是必要条件，真正主因是
> **动画资源加载通道缺失**（见 §2.2）。两个问题叠加：flags 错 + 无预加载通道。

---

## 2.2 ★ 动画加载通道缺失（世界内物品/装备/武器空白，AIP 实战第六轮）

**现象**：背包图标正常，世界内物品/装备/武器动画全空白。纹理头已正确
（ASTC flags=4）、别名无冲突、资源副本完整、zip 无损。

**根因**：动画 zip 必须走**显式预加载通道**，柠版框架不会自动收集：
- PC 上 prefab 文件内部的 `Asset("ANIM","anim/xxx.zip")` 由 ModManager 自动收集；
- **柠版不收集 prefab 内 Asset**——而大物品包的 modmain `Assets` 往往只声明
  UI/驱动动画（AIP 仅 2 条 ANIM，298 个物品动画全在 prefab 里）→ 从未被加载 → 空白。
- 正常 mod 的两种显式通道：① modmain/子模块 `Assets={...}` **全量声明**（传奇武器/九格装备栏）；
  ② `early_prefab_auto.lua` 条目带 **`preload = true`**（棱镜/能力勋章）。

**修复（`dst_mobile_adapter.py` 已内置）**：双重通道——
① 兼容层 `RegisterFW` 把资源副本 `anim/` 全部 zip 硬编码进 preload 列表（生成期收集，
Lua 无法列目录），与 modmain Assets 合并后统一 `FW_PreloadAssets`；
② `early_prefab_auto.lua` 全部条目加 `preload = true`。
日志打印 `全量动画兜底预加载: N 个`。

**排查 SOP**：世界内动画空白 + 图标正常 →
1. 纹理头 flags（§2.1）→ 2. 别名冲突（§8）→ 3. **查 modmain Assets 的 ANIM 声明数**
   vs `anim/` 目录 zip 数；若远小于且 early_prefab 无 preload → 加载通道缺失 → 注入全量预加载。

> **后续更新（AIP 第七轮）**：双重预加载后仍空白——预加载 ≠ build 注册，见 §2.3。

---

## 2.3 ★ 动画 build 注册 vs 预加载（世界内空白最终根因，AIP 实战第七轮）

**现象**：§2.2 双重预加载（FW_PreloadAssets 全量 + early_prefab 全 preload）注入后**仍空白**。
对照永不妥协（modmain `Assets` ANIM=0、无 FW_PreloadAssets）却动画正常——机制差异只剩一处。

**根因**：**预加载（文件取到内存）≠ build 注册（引擎登记动画名，SetBuild 才能用）**。
柠版引擎只从 **modmain 级 `Assets = {...}` 表**收集注册 build；**prefab 定义第三参数的
assets 表（`Prefab("x", fn, assets)`）柠版不收集**（PC 端 ModManager 收集）。
AIP 动画全在 prefab 第三参数（267 条 ANIM）→ 298 个 build 未注册 → SetBuild 报无此 build → 空白。
图标正常：images 走 preload_assets_auto.lua 清单（另一路）。

**正常 mod 的 build 注册通道**：
| mod | 注册通道 | 形式 |
|-----|----------|------|
| 永不妥协 | modmain `Assets` 全量 | init/init_assets.lua 集中 `Assets={475 ANIM}` |
| 传奇武器 | modmain `Assets` 全量 | main/hh_assets.lua 集中 `Assets={13 ANIM}` |
| 棱镜 | early_prefab 注册 | early_prefab_auto.lua 405 条 preload=true |
| AIP(修复前) | 无 | prefab 第三参数（柠版不收集）→ 空白 |

**修复（`dst_mobile_adapter.py` 已内置，永不妥协模式）**：
1. `collect_all_assets()`：跨行扫描 modmain+scripts/ 全部 Lua 的静态 `Asset("TYPE","path")`
   （跳过注释、去重保序）；
2. `collect_anim_zips()`：把 `anim/` 目录**未被静态覆盖的 zip** 补为 `Asset("ANIM","anim/<f>.zip")`
   ——覆盖动态拼接声明（`Asset("ANIM","anim/"..name..".zip")`，prefab 局部变量在 Assets 模块无定义）；
3. `gen_assets_auto()`：生成 `scripts/<key>_assets_auto.lua`：`Assets = { <全部 Asset 行> }`；
4. `inject_modmain`：在 **modmain 原 Assets 表块结束后**注入
   `modimport("scripts/<key>_assets_auto.lua")`（覆盖为全量，原生引擎读 env.Assets 注册全部 build；
   必须在 RegisterFW(Assets,...) **之前**，兼容层拿到的才是全量）。

**校验**：assets_auto.lua 内 ANIM 数 ≥ `anim/` 目录 zip 数（AIP：315 ≥ 298，0 缺失）；
modmain 注入顺序 = Assets 块 → modimport(assets_auto) → PrefabFiles → RegisterFW。

**排查 SOP（三层）**：动画空白 + 图标正常 →
1. 纹理头 flags（§2.1）；2. 加载通道预加载清单（§2.2）；
3. **build 注册**：数 modmain `Assets` 的 ANIM 声明数 vs `anim/` zip 数，若 << → 生成全量 Assets 模块。

> **后续更新（AIP 第八轮，最终结论）**：§2.2+§2.3 双修复后仍空白——主因其实是
> **`FW_LoadPrefabs` 接管预制物注册**。对照 `个人适配柠版mod` 下手工适配成功的 mod
> （趣味食物/英雄联盟武器/传奇武器附魔强化）共性：**无 `scripts/mods/` 资源副本、
> 无 FW_LoadPrefabs 调用、无 preload 标记**，纯原生 PrefabFiles 注册 + prefab 第三参数
> assets 由原生引擎收集注册 build。修复：RegisterFW 改为原生 PrefabFiles 优先
> （`#prefabs_table > 0` 时跳过 FW_LoadPrefabs，仅空表兜底）。见 `柠版适配API文档.md` §20.9。

> **终极方案（AIP 第九轮，§20.10）**：连补丁都不需要——手工 mod 证明**柠版原生 mod 机制
> 与 PC 一致**（读 modmain env 的 Assets/PrefabFiles + 收集 prefab 第三参数 assets）。
> 早期 4 个 bug（Assets/AddRecipe2 not declared 等）全是"资源副本把 modmain 复制进
> scripts/mods/ 被框架重载"自造的。工具新增 **`--native` 纯原生模式**：解包 → ASTC →
> Lua 5.1 post-fix → 自动文件（根路径），**零注入**。AIP 从 17.68MB 降到 9.08MB 且结构
> 与手工 mod 逐项一致。动画空白 SOP 终局：**先对照手工适配 mod 结构，有副本/兼容层/FW_
> 注入直接 --native 重来**，不要逐层补丁。

> **§20.11 owner 坑（AIP 第十轮）**：--native 自动文件的**值**不能用"真实根路径自映射"
> （`anim/xxx.zip`），框架在 FrontendLoadMod 按 `scripts/mods/<mod名>/...` 前缀校验
> owner，否则报 `invalid asset alias owner: <mod>` 崩 ServerCreationScreen。三个自动文件
> 的值全部用 `scripts/mods/<mod名>/...` **死引用**（手工 mod 同款，文件不存在无害）。
> 键（短路径）不变，只改值。

> **§20.12 多 ANIM 收集不可靠（AIP 第十一轮，手持/装备/皮肤空白终解）**：地面正常但
> 手持/装备/皮肤空白 → 查 prefab ANIM 数：正常物品=1 个 ANIM，异常=2+ 个（swap/皮肤 zip）。
> 根因：① 柠版对 prefab 第三参数 assets 的收集，**第 2 个及以后 ANIM 不可靠**（主 zip 加载、
> swap 不加载）；② **不在 PrefabFiles 表的模板动态 prefab（马头等）完全不收集**。
> 修复：--native 模式内置 `inject_assets_append`——全部 ANIM（313 条，含 swap/皮肤/模板
> 动画/动态拼接动画）**追加**进 modmain Assets 表（原表保留去重）→ 原生引擎必然加载。
> **铁律：Assets 提升必须在无 FW_ 接管的纯原生环境做**（§20.8 覆盖式在兼容层环境失败过）。

> **§20.14 early_prefab_auto.lua = 柠版动画唯一有效通道（AIP 第十四轮，手持/皮肤空白终解）**：
> 手持/穿戴/皮肤空白根因 = early_prefab_auto.lua 只注册 prefab 主动画（0 swap 条目），
> swap/皮肤/模板 build zip 从不加载。对照英雄联盟武器（404 条含 109 swap）：
> **生成规则 = anim/ 目录每个 zip 一条**（name=zip 名去 .zip，anim=scripts/mods/<mod名>/anim/<zip>）。
> 框架按条目预注册 build → SetBuild/OverrideSymbol 时 build 已在内存 → 动画显示。
> **废弃**：modmain Assets 表补缺（柠版不读）、FW_PreloadAssets（未生效）、prefab swap 前置。

---

## 3. 柠版资源预加载机制

柠版**不自动扫描** Mod 资源，必须显式声明三个自动文件
（生成逻辑可从「柠版模组一键适配器-MT」.sh 逆向）：

| 文件 | 作用 |
|------|------|
| `preload_assets_auto.lua` | 预加载 XML / 图集 |
| `early_prefab_auto.lua` | 预加载 anim zip |
| `mod_auto.lua` | 资源路径别名 `"anim/xxx.zip"` → `"scripts/mods/<Mod文件夹名>/anim/xxx.zip"` |

路径前缀必须为 `scripts/mods/<Mod文件夹名>/...`（文件夹名须与 mod 实际文件夹一致）。
缺失时物品栏图集、动画、图鉴全部空白。

---

## 4. 文件编码格式（关键坑：进游戏卡加载页）

柠版文件加载器**对格式敏感**：

- Mod 内已有文件为 **UTF-8 BOM + CRLF**
- **新建 .lua 文件必须 UTF-8 BOM + CRLF**，否则进游戏卡在加载页面
- 修改已有文件保持其原格式

Python 统一写入：

```python
text = content.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')
open(path, 'wb').write(b'\xef\xbb\xbf' + text.encode('utf-8'))
```

---

## 5. ModManager.RegisterPrefabs hook 不触发

PC 端很多 Mod 用 hook `GLOBAL.ModManager.RegisterPrefabs` 在预制物注册前做初始化
（复制食谱、注册配方等）。**柠版不走标准流程**（用 `FW_LoadPrefabs` 加载预制物），
导致 hook 不触发 → 功能缺失或闪退。

| 现象 | 根因 |
|------|------|
| 调味品配方未注册，调味站产出 wetgoop（潮湿黏糊） | 调味配方注册逻辑在 hook 内 |
| 自定义烹饪锅点击闪退 | `cooking.recipes.<锅名>` 为 nil，stewer `pairs(nil)` 崩溃 |

**修复**：把 hook 内的逻辑改为在 modmain 直接执行（直接调用 `AddCookerRecipe`），
不依赖 hook。执行时机需在对应预制物文件加载前（保证生成表有数据、预制物能创建）。

---

## 6. 客户端实体标签缺失 → 动作/交互失效

**现象**：嫩肉粉（肉类品质道具）点击无反应，味精（素类）正常。

**根因**：食物预制物在 `SetPristine()` 之后、`ismastersim` 分支内才
`AddComponent("edible")` 和加标签 → **客户端实体没有 `edible_MEAT`/`edible_VEGGIE`
标签**。客户端判断 `isMeatFood` 依赖 `HasTag("edible_MEAT")` → 识别失败 → 动作不出现在菜单。

**修复**：标准食物标签 `edible_<foodtype>` 必须在 `SetPristine()` **之前**添加
（客户端可见），服务端分支再补 `edible.ismeat`：

```lua
inst:AddTag("preparedfood")
local tf_foodtype_tag = data.foodtype or FOODTYPE.GENERIC
inst:AddTag("edible_" .. tostring(tf_foodtype_tag))   -- SetPristine 前，客户端可见
...
inst.entity:SetPristine()
if not TheWorld.ismastersim then return inst end
inst:AddComponent("edible")
...
if inst.components.edible.foodtype == FOODTYPE.MEAT then
    inst.components.edible.ismeat = true
end
```

---

## 7. 参考案例：趣味食物 Mod 柠版适配全记录

| 版本 | 问题 | 根因 | 修复 |
|------|------|------|------|
| v1 | 食物在背包/地面贴图空白 | 仅预加载 modicon，背包图集/动画/图鉴未预加载 | 生成 3 个自动文件（96 XML / 51 anim / 241 别名） |
| v2 | 纯黑块、右下角黑色 ■ | anim 内 atlas 为 DXT5，Mali GPU 不支持 | 56 个纹理 DXT5→RGBA |
| v3 | 能力勋章厨师勋章不兼容 | 新文件非 BOM+CRLF 卡加载页 | 兼容补丁 + 统一文件格式 |
| v4 | 调味品变潮湿黏糊、大厨闪退 | ModManager.RegisterPrefabs hook 不触发 | 配方直接注册到调味站 |
| 最终 | 火锅灶台点击闪退 | `cooking.recipes.tf_cookpot` 为 nil | 复制 cookpot 食谱到火锅灶台 |
| 最终 | 嫩肉粉点击无反应 | 客户端缺 edible_MEAT 标签 | SetPristine 前补标签 |
---

## 8. 跨 Mod 动画别名冲突（动画全空白的最高优先级根因）

**现象**：Mod 的物品/武器/建筑/商店模型全部空白（地上模型、手持武器、自定义建筑），
但背包图标、UI 图集正常。改纹理格式（DXT5→RGBA/ASTC）、补 Assets 声明、加 preload
全部无效。

**根因**：多个 Mod 的 `mod_auto.lua` 里注册了**同名动画别名**（如 `anim/xxx.zip`），
且都指向各自 mod 内的文件。柠版引擎收集别名时发现同名别名指向多个目标 →
报 `[MODULE][ERR] resources.assets:setup ... err=ambiguous asset case alias: anim/xxx.zip`
→ 该模块 setup 失败 → 依赖它的 `prefabs.early`（动画预加载）与 `prefabs.world_preload`
连带被 disabled → **所有动画永不加载 → 模型空白**。

典型冲突场景：两个 Mod 都覆盖同一原版动画（如鱼叉动作 `player_actions_speargun.zip`、
`player_mount_actions_speargun.zip`），或都带同名的原版动画包。

**诊断**：
1. 日志找 `[FAIL] key=resources.assets:setup` 与 `err=ambiguous asset case alias: <资源名>`
2. 全局扫描所有 mod 的 `mod_auto.lua`（`scripts/mods/*/mod_auto.lua`），
   用大小写不敏感对比找出同名别名：
   ```python
   for m in sorted(os.listdir(mods_dir)):
       读 mod_auto.lua, 解析 asset_case_aliases 的 key 集合
       与目标 mod 取交集
   ```
3. 同查 `early_prefab_auto.lua` 的 `{name=..., anim=...}` 条目（同样会冲突）

**修复**：从**后加载方**（或功能次要方）的 `mod_auto.lua` 与 `early_prefab_auto.lua`
中**删除冲突别名条目**（保留 zip 文件与 modmain 的 Asset 声明——引擎按需加载时会
落到另一方的别名/原版资源）。修复后日志应看到 `resources.assets ... ready`（无 ERR）
且 `prefabs.early ... ready`。

**注意**：`player_actions_*` / `player_mount_actions_*` 这类是**原版动画的覆盖包**，
很多 Mod 会自带；判断"哪个该让位"看功能主次，删除别名只是不注册映射，不删文件。

---

## 9. 声音不加载：必须生成 sound_banks_auto.lua

**现象**：Mod 有 `sound/*.fev + *.fsb`，但游戏内无对应音效/BGM。

**根因**：柠版不自动扫描声音。凡 mod 带 `sound/` 目录，必须生成
`sound_banks_auto.lua`（与其它 `*_auto.lua` 同规则：**无 BOM + CRLF**）：

```lua
-- Generated by build_zip.py; do not edit by hand.
return {
    version = 2,
    modname = "英雄联盟武器",
    total_bytes = <所有 fev+fsb 字节和>,
    pairs = {
        { fev = "scripts/mods/<文件夹名>/sound/xxx.fev", fsb = "scripts/mods/<文件夹名>/sound/xxx.fsb" },
    },
}
```

参考正常 Mod（晓美焰/永不妥协/魔法少女小樱）的同名文件格式照抄。
modmain 里 `Asset("SOUNDPACKAGE"...)` 声明与 sound_banks_auto.lua 不冲突，可并存。

---

## 10. 触屏滑块/滚动条修复：自定义滚动条 → 内置 ScrollingGrid

**现象**：图鉴/列表页的滚动条手柄拖动失灵、点击滚动条翻页异常、拖动后手柄位置
错乱、触屏下 `attempt to perform arithmetic on field 'lastx'(a nil value)` 崩溃。

**根因**：PC 版自定义滚动条（从 `widgets/scrollablelist.lua` 复制改样式）在柠版触屏下：
- `TheFrontEnd.lastx/lasty` 可能为 nil（触屏未模拟鼠标事件）或固定在按下点不更新
- 拖动手柄的 `o_pos`（原始位置）在 SetOnDown 里丢失 → "远离滚动条"分支
  `SetPosition(o_pos)` 位置错乱
- `LockFocus` 劫持触屏、坐标换算（GetWorldPosition vs lastx）不一致

**首选修复**：**改用游戏内置 `TEMPLATES.ScrollingGrid`**（简易存储/种植计算器均为
此方案，触屏滑动/拖动/手柄全部原生支持）：

```lua
local TEMPLATES = require "widgets/redux/templates"
grid = TEMPLATES.ScrollingGrid({}, {
    context = { ... },             -- 回调上下文（如 pedia 实例）
    item_ctor_fn = function(ctx, index)  -- 创建每格 widget
        local w = Widget('item-'..index)
        w.content = w:AddChild(CreateItem())
        return w
    end,
    apply_fn = function(ctx, widget, data, index)  -- 按数据填充 + 设点击
        widget:Disable(); widget.content:Hide()
        if not data then return end
        widget:Enable()
        ... 填充内容 ...
        widget.content:Show()
    end,
    widget_width = 200, widget_height = 60,
    num_visible_rows = 7, num_columns = 1,   -- 单列列表 = num_columns=1
    scrollbar_offset = 10,                   -- 滚动条贴列表右侧
    scrollbar_height_offset = 0,
    peek_percent = 0,
    allow_bottom_empty_row = true,
    scroll_per_click = 1,
})
grid:SetItemsData(items_data)   -- 换组/换数据
```

**必须保留自定义滚动条时的最小修复**：
1. `SetOnDown` 里保存 `position_marker.o_pos = position_marker:GetPosition()`
2. 拖动/翻页处 `lastx/lasty` 加兜底：
   `local lastx = TheFrontEnd.lastx or self._drag_lastx or marker.x`
   （`_drag_lastx/_drag_lasty` 在 SetOnDown 记录）
3. 滚动条点击翻页的 `TheFrontEnd.lasty` 也加 `or 0` 兜底

---

## 11. UI 调整记忆模式（放大/缩小/上移/下移，借鉴成就轻松版）

**需求**：让页面（图鉴/成就/面板）可手动缩放与上下移动，并记忆位置（重启保留）。

**参考实现**（成就轻松版 uiachievement.lua）：
- 页面主体容器记 `self.size` / `self.ui_offset_y`
- 放大/缩小按钮：`size = clamp(size ± 0.02, 下限, 1.3)`；`container:SetScale(size,size,1)`
- 上移/下移按钮：`offset_y = clamp(offset_y ± 25, -250, 250)`；`container:SetPosition(0, offset_y, 0)`
- 持久化：`TheSim:GetPersistentString(key, cb, false)` 读取；
  `GLOBAL.pcall(SavePersistentString, key, size..","..offset, false)` 写入
  （键名全局唯一，如 `lol_wp_pedia_ui_config`）
- 编辑模式开关按钮：点击展开/收起这组按钮
- **注意**：若容器设了 `SetScaleMode(SCALEMODE_FIXEDPROPORTIONAL)`，显式 SetScale
  会被 ScaleMode 覆盖——缩放/移动应作用于**外层未设 ScaleMode 的 widget**
  （如页面根 widget 自身）

---

## 12. 参考案例：英雄联盟武器 Mod 柠版适配全记录

| 阶段 | 问题 | 根因 | 修复 |
|------|------|------|------|
| 1 | 动画全空白（物品/武器/建筑/商店） | **跨 mod 同名动画别名 → resources.assets FAIL → 动画预加载禁用** | 删除与"永不妥协"冲突的 2 个别名（mod_auto + early_prefab） |
| 2 | 动画纹理 | 曾怀疑 DXT5/ASTC/mip 链，**全部排除**（正常 mod 用 ASTC 8x8 单 mip 或 RGBA 全 mip 均可） | 纹理维持 ASTC 8x8（与正常 mod 一致） |
| 3 | 金锅配方失效/闪退 | RegisterPrefabs hook 不触发 | AddSimPostInit 直接注册食谱 |
| 4 | 图鉴/属性按钮 PC 位置不适配 | PC 左下角按钮 | FW_RegisterModButton 柠版按钮（pos/scale 可调，日志 `[ABTN]` 确认） |
| 5 | 图鉴滚轮报错 | 触屏 lastx/lasty nil | 滚动条拖动加兜底（后升级为 ScrollingGrid） |
| 6 | 声音缺失（链锯声/BGM） | 无 sound_banks_auto.lua | 生成 18 对 fev/fsb 清单 |
| 7 | 图鉴滑块异常 | 自定义滚动条触屏 bug（o_pos/lastx） | 左侧列表改 TEMPLATES.ScrollingGrid |
| 8 | 图鉴缩放/移动 | 用户要求 | 移植成就"UI 调整记忆"（放大/缩小/上移/下移 + 持久化） |

**关键教训**：
- 柠版对资源加载失败多静默或仅报 `[MODULE][ERR]/[FAIL]` 级日志，排查必须看这层
- "动画空白"先查 resources.assets 是否 FAIL（别名冲突），再查纹理格式
- 正常 mod 对比法（同结构 mod 的 mod_auto/sound_banks/纹理）是最高效的排障手段
- 用户环境常有上百个 mod，别名/资源名冲突是常态，必须全量对比

---

## 13. Lua 5.1 隐式 arg 表在柠版为 nil → 游戏内闪退（AIP 实战教训）

**现象**：AIP 适配后进游戏正常，使用飞行视角（flyWrapper）时闪退。日志尾部：

```
[instance_2][00:01:11]: [string "...flyW..."]:193: bad argument #1 to 'unpack' (table expected, got nil)
@scripts/mods/AIP-额外物品包/scripts/flyWrapper.lua:193 in (method) Update (Lua) <184-194>
```

**根因**：PC 老 Mod 的 vararg 函数里用 Lua 5.1 隐式 `arg` 表转发参数
（`return OriginUpdate(self, dt, _G.unpack(arg))`）。Lua 5.2+ 移除了隐式 `arg`，
柠版（DST 64010402 新版）里 `arg` 为 nil → `unpack(nil)` 崩溃。PC 端 DST 仍是
Lua 5.1 所以正常——"PC 正常、柠版闪退"的典型版本兼容 bug。

**修复**：`_G.unpack(arg)` → `_G.unpack({...})`（Lua 5.1 语义等价，5.2+ 正常）。
AIP 共 6 处（flyWrapper.lua:193、prefabsHooker.lua:408/445 等）。

**一键工具已内置**：`dst_mobile_adapter.py` 第 8 步自动全文替换
`unpack(arg)` → `unpack({...})`（保持 BOM/编码），日志打印
`== 兼容性 post-fix: unpack(arg)->unpack({...}) 共 N 处`。

### 13.1 变种：vararg 函数**直接引用**裸 arg → 进入世界后闪退（AIP 第二轮）

**现象**：unpack(arg) 修完后，AIP **进入世界即闪退**。日志：

```
aipUtils.lua:8: bad argument #1 to 'pairs' (table expected, got nil)
@aipUtils.lua:201 aipPrint → aipCommonStr → aipCountTable(arg)   -- arg=nil
@components/world_common_store.lua:393 (PERIODIC 5s 周期任务)
```

**根因**：`unpack(arg)` 只是隐式 arg 的一种用法；**任何 vararg 函数体内裸引用
`arg`** 在柠版新 Lua 都是 nil。aipUtils.lua 有 5 个：
`aipCommonStr`（`aipCountTable(arg)` + `arg[i]`）、`aipFindEnt/aipFindEnts/
aipCountEnts/aipIndexEnts`（`entMatchNames(arg,ent)` → `table.contains(nil)` 崩溃）。
这些实体查找函数被 AIP 全局逻辑高频调用，世界生成/运行时必然触发。

**修复**：函数体首行注入 `local arg={...}`（Lua 5.1 等价、5.2+ 修复）：
```lua
function _G.aipCommonStr(showType,split,...)
    local arg={...}      -- ← 注入
    local count=_G.aipCountTable(arg)
```

**一键工具已升级**：post-fix 现在自动扫描单行 vararg 函数声明（含 `...`），函数体有裸
`arg` 且无 `local arg` 时在首条语句前注入 `local arg={...}`；日志打印
`== 兼容性 post-fix: vararg 注入 local arg={...} 共 N 处`。

**排查 SOP**：堆栈帧在 mod 工具函数 + 报 `pairs/ipairs/#/table.contains 收到 nil` →
看函数声明是否含 `...`、体内是否引用 `arg` → 注入 `local arg={...}`。

**同类老 API 排查清单**（PC→柠版移植必扫）：裸 `arg`（注入 `local arg={...}`）、
`table.getn`→`#`、`math.mod`→`%`、`getfenv/setfenv`→`_ENV`、`loadstring`→`load`、
全局 `unpack`→`table.unpack`。详见 `柠版适配API文档.md` §20.6 / §20.6b。

---

## 14. strict.lua 环境坑：modmain 注入 API 不在 GLOBAL（AIP 第三轮实战）

**现象**：修完 RegisterFW 与 arg 后，modmain 加载又报：

```
mobile_compat_aip.lua:73: variable 'AddRecipe2' is not declared
strict.lua:23 in __index
modmain.lua:2 in main chunk
```

**根因**：`AddRecipe2` 等**挂载点 API 是 DST 注入 modmain env 的，不在 GLOBAL 表上**
（柠版新版移走了；PC 老版在）。modimport 的兼容层是独立 strict 环境，`G.AddRecipe2`
（G=GLOBAL）触发 strict `__index` → 字段不存在 → 抛 `variable 'AddRecipe2' is not
declared`（不是 nil）。modmain 里裸用 AddRecipe2 正常（env 注入），modimport 里裸用崩。

**修复**（工具模板已改，重新生成产物自动生效）：

```lua
local orig_AddRecipe2 = G.rawget(G, "AddRecipe2")   -- strict 安全
if type(orig_AddRecipe2) == "function" then
    G.rawset(G, "AddRecipe2", function(...) ... end)  -- 写入也 rawset
end
-- G.AllRecipes → G.rawget(G, "AllRecipes")
```

**挂载点 API 清单**（modimport 脚本一律 rawget 判存在）：`AddRecipe2` /
`AddPrefabPostInit` / `AddComponentPostInit` / `AddPlayerPostInit` / `AddSimPostInit` /
`AddClassPostConstruct` / `AddModRPCHandler` / `AddMinimapAtlas` / `AddInventoryItemAtlas`。

**排障 SOP**：`variable 'xxx' is not declared` + xxx 是 DST 挂载 API → 该 API 是
modmain env 注入（不在 GLOBAL）→ modimport 侧 rawget + 判存在，缺失静默跳过。
详见 `柠版适配API文档.md` §20.5b。

---

## 15. 自定义 Scroller 柠版触摸滚动（AIP 书籍/图鉴实战，§10 的延伸）

**场景**：书籍/图鉴页用了**自绘 Scroller**（`widgets/redux/aipScroller.lua` 这类，
非内置 ScrollableList/ScrollingGrid），原始只响应 `CONTROL_SCROLLBACK/FWD`
（鼠标滚轮/手柄键）且要求 `enabled and focused`。柠版无滚轮、无手柄 focus 导航
→ 章节菜单 + 长描述完全无法滚动。AIP 书籍 129 章节、菜单可视高仅 580
（scrollBound ≈ 7115）→ **必须滚动**。

**两个独立滚动区**（AIP 书籍布局）：左 `menuScroller`（章节菜单）+ 右 `descHolder`
（描述内容，每次选章节 Kill 重建）——各自是独立 Scroller 实例，构造里统一启用。

**适配（参照简易存储/种植计算器实装验证的触摸模式，三通道）**：

```lua
-- ① 命中层：black 用 ImageButton（有尺寸、可触摸命中），不设 SetOnClick
self.black = self:AddChild(ImageButton("images/global.xml","square.tex"))
-- ② 构造函数末尾 self:EnableTouchScroll()

function Scroller:EnableTouchScroll()
    if self.touchScrollEnabled then return end
    self.touchScrollEnabled = true
    local scroller, black = self, self.black
    -- 通道A 原生触摸事件（简易存储 terminal_invslot 式）
    local function install_touch(t)
        t._touch_id = nil; t._touch_last_y = nil
        function t:OnTouchStart(id, x, y)
            if self._touch_id == nil then
                self._touch_id = id; self._touch_last_y = y
                if GLOBAL.TheFrontEnd then GLOBAL.TheFrontEnd:LockFocus(true, id) end
                return true
            end
            return false
        end
        function t:OnTouchMove(id, x, y)
            if self._touch_id == id and self._touch_last_y ~= nil then
                local dy = y - self._touch_last_y
                self._touch_last_y = y
                if dy ~= 0 then scroller:Offset(dy) end
                return true
            end
            return false
        end
        function t:OnTouchEnd(id, x, y)
            if self._touch_id == id then
                self._touch_id = nil; self._touch_last_y = nil
                if GLOBAL.TheFrontEnd then GLOBAL.TheFrontEnd:LockFocus(false, id) end
                return true
            end
            return false
        end
        function t:OnTouchCancel(id)
            if self._touch_id == id then
                self._touch_id = nil; self._touch_last_y = nil
                if GLOBAL.TheFrontEnd then GLOBAL.TheFrontEnd:LockFocus(false, id) end
            end
        end
    end
    install_touch(black); install_touch(self)
    -- 通道B 原版 drag 系统（ScrollableList 式）
    if type(black.SetDragable) == "function" then
        black:SetDragable(true)
        black:SetDragUpdateFn(function(x, y, dx, dy)
            if dy ~= 0 then scroller:Offset(dy) end
        end)
    end
end
```

**要点**：
1. **触摸命中层必须有尺寸且可交互**：普通 Widget/Image 无尺寸接不住触摸；
   ImageButton 是通用命中层（不设 SetOnClick 即无点击动作）；
2. **菜单项（ImageButton）优先接住自己的触摸**（命中子项走点击、空白区走滚动），
   触摸分发从最上层 hit test，天然不冲突；
3. `OnTouchStart return true` 吞触摸防透传；`LockFocus(true/false,id)` 防滚动误触；
4. **首选仍是内置 `TEMPLATES.ScrollingGrid`**（§10，零代码自带触摸）；
   自绘 Scroller 是布局自定义度太高时的替代；
5. 保留滚轮/手柄通道，PC 行为不变。