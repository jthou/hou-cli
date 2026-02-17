"""后台启动 Web 前端服务"""
import subprocess
import sys
import os
from pathlib import Path

def start_web_background():
    """在后台启动 Web 前端服务"""
    # 获取项目根目录
    project_root = Path(__file__).parent.parent.parent
    
    # 构建命令
    python_exe = sys.executable
    web_main = str(project_root / "frontend" / "web" / "main.py")
    
    # 在后台启动（不阻塞）
    if sys.platform == "win32":
        # Windows
        subprocess.Popen(
            [python_exe, web_main],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            cwd=str(project_root)
        )
    else:
        # macOS/Linux
        subprocess.Popen(
            [python_exe, web_main],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            cwd=str(project_root)
        )

if __name__ == "__main__":
    start_web_background()

