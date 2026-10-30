# 柠版 Mod 适配工具

此目录提供适配器 v1.6.7 完整源码、GUI、Windows 拖拽入口和两份原版图集表。

## 使用

需要可用的 Python 3。先执行 `py -V`，再执行：

```powershell
py -X utf8 dst_mobile_adapter.py --help
py -X utf8 dst_mobile_adapter.py "D:/Mods/我的Mod" --out "D:/Converted/我的Mod" --zip
```

也可把 Mod 目录或 ZIP 拖到 `柠版一键适配.bat`，或通过 `py 柠版适配工具GUI.pyw` 启动图形界面。请使用新输出目录，保留输入。

## ASTC 编码器

本次源码分发未附带二进制编码器。可从 [Arm astc-encoder](https://github.com/ARM-software/astc-encoder/releases) 获取适合 Windows 的版本，将可执行文件放为 `astcenc/astcenc.exe`，或使用 `--astcenc` 指定完整路径。缺少编码器时适配器会回退 RGBA，此结果需要按目标设备验证。处理部分纹理的路径可选依赖 Pillow；遇到相关提示时执行 `py -m pip install Pillow`。

## 构建与检查

安装 PyInstaller 并准备 `astcenc/` 后，在此目录执行 `py -m PyInstaller 柠版适配工具.spec --noconfirm`。配置会携带两份图集表。源码更新不会自动更新已发布 exe。

资源增删后先执行 `--verify-auto`；需要刷新时在产物副本上执行 `--sync-auto`（默认原地处理）。多个 Mod 联用前执行 `--audit-aliases`，具体参数见 `--help`。

拖拽入口会检测可用解释器、保留转换退出码，并在失败时显示错误提示。工具完成转换后仍需目标手机端验证。
