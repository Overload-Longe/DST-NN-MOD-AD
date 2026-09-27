# DST-NN-MOD-AD — 柠娜版 DST Mod AI 适配技能库

使 AI（豆包等）能直接使用柠版（手机端）《饥荒联机版》Mod 适配技能与适配成果。

## 📦 技能包（供其他 AI 使用）

- `dst-mod-dev/SKILL.md` —— DST Mod 开发与排障技能主文件（触发边界/工作流/实战沉淀 §7.x）
- `dst-mod-dev/references/*.md` —— 参考知识库（Bug 模式/移植清单/DST API/UI 修改/柠版专项/角色专项）
- `dst-mod-dev/tools/` —— 柠版一键适配工具（dst_mobile_adapter.py 等，纹理转换/自动文件/兼容层注入/打包）

**AI 使用方式**：将 `dst-mod-dev/` 目录安装为技能，先读 SKILL.md 获得完整技能逻辑，再按需加载 references 与 tools。

## 🎮 已适配 mod 源码

- `传奇武器附魔强化/` —— 装备附魔/宝石/召唤/元素职业大 mod 的 PC→柠版适配源码（文本部分）。纹理/动画等二进制资源体积大不入库，完整可安装 zip 见本地交付。

## 适配规范（沉淀摘要）

- 纹理：ASTC 8x8（Mali GPU 只认 ASTC）；文件：UTF-8 BOM+CRLF
- 词法安全：尾 BOM 炸弹、endlocal 粘连、require pcall 包裹、worldgen 链 _G 别名
- UI：FW_RegisterModButton 柠版按钮、触摸管线、point 施法 target=nil 兜底
- 打包：zip 内套 mod 文件夹 + 全正斜杠 + compresslevel=6

详见 SKILL.md §7.x 与柠版适配API文档.md（本地完整版）。
