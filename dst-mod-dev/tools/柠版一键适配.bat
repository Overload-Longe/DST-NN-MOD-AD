@echo off
chcp 65001 >nul
setlocal DisableDelayedExpansion
title 柠版 Mod 一键适配工具
if "%~1"=="" (
    echo 请把 Mod 目录或 ZIP 拖到此文件上。
    pause
    exit /b 2
)
set "SCRIPT=%~dp0dst_mobile_adapter.py"
if not exist "%SCRIPT%" (
    echo 找不到适配器源码：%SCRIPT%
    pause
    exit /b 2
)
py -V >nul 2>&1
if not errorlevel 1 (
    py -X utf8 "%SCRIPT%" "%~1" --zip
    goto result
)
python -V >nul 2>&1
if errorlevel 1 (
    echo 未找到可用的 Python，请先安装 Python。
    pause
    exit /b 2
)
python -X utf8 "%SCRIPT%" "%~1" --zip
:result
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" (
    echo 转换失败，退出码：%RESULT%。请查看上方错误信息。
    pause
    exit /b %RESULT%
)
echo 转换完成，输出位置请查看上方日志。仍需在目标手机端验证。
pause
exit /b 0
