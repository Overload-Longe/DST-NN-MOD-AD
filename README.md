# DST-NN-MOD-AD

**NN DST MOD 适配库**：使 AI（豆包等智能助手）更便捷地适配柠版（手机端）《饥荒联机版》Mod 的技能与成果仓库。

## 仓库内容

| 目录 | 说明 |
|---|---|
| `dst-mod-dev/` | **AI 可加载的 Mod 适配技能包**（SKILL.md + references 知识库 + tools 一键适配工具），其他 AI 安装后即可复用柠版适配全流程 |
| `docs/` | 适配 API 文档（柠版 FW_* 框架全量手册 + 实战沉淀） |
| `传奇武器附魔强化/` | 已适配 mod 文本源码存档（PC→柠版：装备附魔/召唤/元素职业） |

## 让其他 AI 使用本技能

1. 将 `dst-mod-dev/` 整个目录放入 AI 助手的 skills 目录（如豆包 `用户数据/.user_skills/`）；
2. AI 读取 `dst-mod-dev/SKILL.md` 即获得：柠版适配触发边界、工作流程、铁律沉淀（ASTC 纹理/BOM+CRLF/FW_* 框架/词法安全等）；
3. 配套 `docs/柠版适配API文档.md` 为 FW_* API 全量手册，`dst-mod-dev/references/` 为分主题知识库，`dst-mod-dev/tools/dst_mobile_adapter.py` 为一键适配工具（纹理转换/自动文件/打包）。

## 安装已适配 Mod（柠版）

1. 下载对应 mod 完整 zip（本仓库仅存文本源码，纹理/动画等二进制资源体积大不入库）；
2. 解压后拷贝内层 mod 文件夹到柠版 mods 目录；
3. 游戏内启用，重启进入世界。

## 适配规范要点（沉淀自实战）

- 纹理：KTEX ASTC 8x8（RGBA 在柠版 Mali 管线解压失败）；
- 编码：.lua 统一 UTF-8 BOM + CRLF；
- 动画：`early_prefab_auto.lua` 全量注册每个 anim zip；
- 框架：柠版 FW_RegisterModButton/FW_RegisterAction/FW_LoadPrefabs 等（见 docs）；
- 词法安全：尾 BOM、endlocal 粘连等坑已规避（见 docs §28/§30）。