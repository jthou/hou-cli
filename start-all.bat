@echo off
REM Windows 一键启动前后端（后端后台，前端交互式）

cd /d "%~dp0"

REM 检查虚拟环境
if not exist "venv\Scripts\activate.bat" (
    echo ❌ 虚拟环境不存在，请先运行: python -m venv venv
    pause
    exit /b 1
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

echo 🚀 启动后端服务（后台）...
python cli.py start

echo.
echo 🚀 启动前端 CLI...
echo.

REM 启动前端（交互式）
python -m frontend.main chat

pause






