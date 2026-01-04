@echo off
REM Windows 一键启动脚本 - 自动激活虚拟环境并启动后端（后台）

cd /d "%~dp0"

REM 检查虚拟环境
if not exist "venv\Scripts\activate.bat" (
    echo ❌ 虚拟环境不存在，请先运行: python -m venv venv
    pause
    exit /b 1
)

REM 激活虚拟环境并启动后端（后台）
call venv\Scripts\activate.bat
python cli.py start

echo.
echo 💡 提示:
echo    - 后端已在后台运行
echo    - 启动前端: start-frontend.bat
echo    - 停止后端: stop.bat
echo    - 查看状态: python cli.py status

pause
