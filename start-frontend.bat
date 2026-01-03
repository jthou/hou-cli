@echo off
REM Windows 启动前端 CLI - 自动激活虚拟环境

cd /d "%~dp0"

REM 检查虚拟环境
if not exist "venv\Scripts\activate.bat" (
    echo ❌ 虚拟环境不存在
    pause
    exit /b 1
)

REM 激活虚拟环境并启动前端
call venv\Scripts\activate.bat
python -m frontend.main chat

pause


