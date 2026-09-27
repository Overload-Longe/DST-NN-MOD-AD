@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title 柠版 Mod 一键适配工具

if "%~1"=="" (
    echo.
    echo  请把 PC 端 Mod 的 .zip 压缩包或 Mod 文件夹【拖到这个文件上】再松开
    echo.
    echo  可选：拖完松手前按 Shift 可直接选择“打开方式”，也可先拖进来再按任意键
    echo.
    pause
    exit /b
)

set "SRC=%~1"
set "SRC_DIR=%~dp1"
set "SCRIPT=%~dp0dst_mobile_adapter.py"

echo.
echo  ============================================
echo   柠版（手机端 DST）Mod 一键适配
echo   src: %SRC%
echo  ============================================
echo.

python -X utf8 "%SCRIPT%" "%SRC%" --zip

echo.
echo  完成。适配版 zip 在：%SRC_DIR%（与源文件同目录）
echo  请把 zip 解压，将里面的 Mod 文件夹拷贝到雷电模拟器柠版的 mod 目录。
echo.
pause