"""同时启动 CLI 和 Web 前端"""
import subprocess
import sys
import time
import os
from pathlib import Path

def start_all_frontends():
    """同时启动 CLI 和 Web 前端"""
    project_root = Path(__file__).parent.parent
    python_exe = sys.executable
    
    # 1. 启动 Web 前端（后台）
    print("🌐 启动 Web 前端服务...")
    web_main = project_root / "frontend" / "web" / "main.py"
    
    if sys.platform == "win32":
        # Windows
        web_process = subprocess.Popen(
            [python_exe, str(web_main)],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            cwd=str(project_root)
        )
    else:
        # macOS/Linux
        web_process = subprocess.Popen(
            [python_exe, str(web_main)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            cwd=str(project_root)
        )
    
    # 等待 Web 前端启动
    time.sleep(2)
    print("✅ Web 前端已启动（后台运行）")
    print("   🌐 访问: http://127.0.0.1:8081")
    print("   （如果 8081 被占用，会自动使用其他可用端口）")
    print()
    
    # 2. 启动 CLI 前端（前台，交互式）
    print("🖥️  启动 CLI 前端...")
    print()
    
    # 运行 CLI 前端（通过 click 命令）
    # 这会阻塞，直到用户退出
    from frontend.main import cli
    cli(['chat'])

if __name__ == "__main__":
    try:
        start_all_frontends()
    except KeyboardInterrupt:
        print("\n⏹️  已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

