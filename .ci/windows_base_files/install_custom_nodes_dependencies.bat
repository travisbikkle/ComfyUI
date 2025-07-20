chcp 65001 >nul

@echo off
echo ComfyUI Custom Nodes Dependencies Installer
echo.

REM 检测 Python 是否已安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未检测到 Python 安装
    echo.
    echo 请先安装 Python（任意版本均可）
    echo 下载地址: https://mirrors.aliyun.com/python-release/windows/python-3.12.9-amd64.exe
    echo.
    echo 安装完成后，请确保在命令行中运行 "python --version" 能正常显示版本信息
    echo.
    pause
    exit /b 1
)

echo Python 已安装，开始运行安装脚本...
echo.
python install_custom_nodes_dependencies.py
pause