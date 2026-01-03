#!/usr/bin/env python3
"""统一启动脚本 - 后端后台运行，前端交互式"""
import subprocess
import sys
import time
import os
import re
from pathlib import Path
import signal
import atexit
import argparse
import httpx
from typing import Optional
from shared.platform_utils import get_app_data_dir, load_port, get_port_file

# 确保在项目根目录
project_root = Path(__file__).parent
os.chdir(project_root)

# PID 文件路径
PID_FILE = project_root / ".backend.pid"

def check_venv():
    """检查是否在虚拟环境中"""
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  警告: 未检测到虚拟环境")
        print("   建议先运行: source venv/bin/activate")
        response = input("   是否继续? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)

def save_pid(pid):
    """保存进程 PID"""
    PID_FILE.write_text(str(pid))

def get_backend_pid():
    """获取后端进程 PID"""
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text().strip())
        except:
            return None
    return None

def is_backend_running():
    """检查后端是否在运行"""
    pid = get_backend_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, 0)  # 检查进程是否存在
        return True
    except OSError:
        return False

def find_process_by_port(port: int) -> Optional[int]:
    """根据端口号查找进程 PID（跨平台）"""
    try:
        if sys.platform == "win32":
            # Windows: 使用 netstat 和 findstr
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if f":{port}" in line and "LISTENING" in line:
                        # 提取 PID（最后一列）
                        parts = line.split()
                        if parts:
                            try:
                                return int(parts[-1])
                            except ValueError:
                                continue
        else:
            # macOS/Linux: 使用 lsof
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                try:
                    return int(result.stdout.strip().split('\n')[0])
                except ValueError:
                    pass
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    return None

def kill_process_by_port(port: int) -> bool:
    """杀死占用指定端口的进程"""
    pid = find_process_by_port(port)
    if pid is None:
        return False
    
    try:
        # 先尝试优雅退出
        os.kill(pid, signal.SIGTERM)
        time.sleep(1)
        
        # 检查是否还在运行
        try:
            os.kill(pid, 0)
            # 还在运行，强制杀死
            os.kill(pid, signal.SIGKILL)
            time.sleep(0.5)
        except ProcessLookupError:
            # 进程已退出
            pass
        
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False

def cleanup_environment():
    """完全清理运行环境"""
    print("🧹 清理运行环境...")
    
    # 1. 停止 PID 文件中的后端进程
    pid = get_backend_pid()
    if pid is not None:
        try:
            if is_backend_running():
                print(f"   🛑 停止后端进程 (PID: {pid})...")
                os.kill(pid, signal.SIGTERM)
                time.sleep(1)
                if is_backend_running():
                    os.kill(pid, signal.SIGKILL)
                    time.sleep(0.5)
        except (ProcessLookupError, OSError):
            pass
    
    # 2. 读取端口文件，杀死占用该端口的进程
    port_file = get_port_file()
    if port_file.exists():
        try:
            port = int(port_file.read_text().strip())
            pid_by_port = find_process_by_port(port)
            if pid_by_port is not None:
                # 如果端口进程和 PID 文件中的不同，杀死端口进程
                if pid_by_port != pid:
                    print(f"   🛑 停止占用端口 {port} 的进程 (PID: {pid_by_port})...")
                    kill_process_by_port(port)
        except (ValueError, Exception):
            pass
    
    # 3. 清理 PID 文件
    if PID_FILE.exists():
        PID_FILE.unlink(missing_ok=True)
        print("   ✅ 已清理 PID 文件")
    
    # 4. 不清理端口文件，保留以便下次启动时复用端口
    # 如果端口被占用，会在启动时自动检测并分配新端口
    # if port_file.exists():
    #     port_file.unlink(missing_ok=True)
    #     print("   ✅ 已清理端口文件")
    
    # 5. 等待一小段时间确保进程完全退出
    time.sleep(0.5)
    print("✅ 环境清理完成")

def start_backend(background=True):
    """启动后端进程"""
    # 先完全清理环境（强制重启）
    cleanup_environment()
    
    if background:
        print("🚀 启动后端服务（后台）...")
    else:
        print("🚀 启动后端服务...")
    
    if background:
        # 后台运行
        if sys.platform == "win32":
            # Windows
            process = subprocess.Popen(
                [sys.executable, "-m", "backend.main"],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            # Unix/Linux/macOS
            # 暂时保留 stderr 以便调试，生产环境可以改为 DEVNULL
            process = subprocess.Popen(
                [sys.executable, "-m", "backend.main"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,  # 保留 stderr 以便调试
                start_new_session=True
            )
        
        save_pid(process.pid)
        
        # 检查进程是否立即退出（启动失败）
        time.sleep(0.5)
        if process.poll() is not None:
            # 进程已退出，说明启动失败
            stderr = process.stderr.read().decode('utf-8', errors='ignore') if process.stderr else ""
            error_msg = f"后端启动失败 (退出码: {process.returncode})"
            if stderr:
                error_msg += f"\n错误信息: {stderr[:200]}"
            raise RuntimeError(error_msg)
        
        if not background:  # 只在非后台模式下显示详细信息
            print(f"✅ 后端服务已在后台启动 (PID: {process.pid})")
            print("   日志请查看后端输出")
        # 不在这里等待，让调用者决定等待时间
        return process.pid
    else:
        # 前台运行（阻塞）
        try:
            subprocess.run(
                [sys.executable, "-m", "backend.main"],
                check=True
            )
        except KeyboardInterrupt:
            print("\n⏹️  后端服务已停止")
        except Exception as e:
            print(f"❌ 后端启动失败: {e}")
            sys.exit(1)
        return None

def stop_backend():
    """停止后端服务"""
    pid = get_backend_pid()
    if pid is None:
        print("❌ 未找到后端进程 PID")
        return False
    
    if not is_backend_running():
        print("✅ 后端服务未运行")
        PID_FILE.unlink(missing_ok=True)
        return True
    
    try:
        print(f"🛑 正在停止后端服务 (PID: {pid})...")
        os.kill(pid, signal.SIGTERM)
        time.sleep(1)
        
        # 检查是否还在运行
        if is_backend_running():
            print("⚠️  强制停止...")
            os.kill(pid, signal.SIGKILL)
        
        PID_FILE.unlink(missing_ok=True)
        print("✅ 后端服务已停止")
        return True
    except ProcessLookupError:
        print("✅ 后端服务已停止")
        PID_FILE.unlink(missing_ok=True)
        return True
    except Exception as e:
        print(f"❌ 停止失败: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="LLM Agent CLI 启动脚本")
    parser.add_argument(
        "command",
        nargs="?",
        choices=["start", "stop", "status", "restart"],
        default="start",
        help="命令: start(启动), stop(停止), status(状态), restart(重启)"
    )
    parser.add_argument(
        "--foreground",
        "-f",
        action="store_true",
        help="前台运行后端（用于调试）"
    )
    parser.add_argument(
        "--wait",
        "-w",
        action="store_true",
        help="等待后端启动完成（用于后续启动前端）"
    )
    
    args = parser.parse_args()
    
    if args.command == "stop":
        stop_backend()
        return
    
    if args.command == "status":
        if is_backend_running():
            pid = get_backend_pid()
            print(f"✅ 后端服务正在运行 (PID: {pid})")
        else:
            print("❌ 后端服务未运行")
        return
    
    if args.command == "restart":
        stop_backend()
        time.sleep(1)
        args.command = "start"
    
    if args.command == "start":
        if not args.wait:
            print("=" * 60)
            print("🎯 LLM Agent CLI - 启动后端服务")
            print("=" * 60)
        
        check_venv()
        
        # 启动后端
        backend_was_running = is_backend_running()
        pid = start_backend(background=not args.foreground)
        
        if args.wait and pid:
            # 等待后端启动完成
            if not backend_was_running:
                print("⏳ 等待后端服务启动...")
                # 先等待一下，让后端有时间启动
                time.sleep(2)
            else:
                print("✅ 后端服务已在运行，跳过等待")
                return
            
            max_retries = 20  # 增加重试次数
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # 先检查端口文件是否存在
                    port_file = get_app_data_dir() / "port.txt"
                    if not port_file.exists():
                        time.sleep(0.5)
                        retry_count += 1
                        continue
                    
                    port = load_port()
                    # 检查端口是否为有效值（不是默认值8000，且大于1024）
                    if port and port != 8000 and port > 1024:
                        # 使用 httpx 进行健康检查，配置 trust_env=False 跳过代理
                        try:
                            response = httpx.get(
                                f"http://127.0.0.1:{port}/health", 
                                timeout=2.0,
                                trust_env=False  # 跳过代理，避免 502 错误
                            )
                            if response.status_code == 200:
                                print("✅ 后端服务已就绪")
                                return
                        except httpx.RequestError:
                            # 连接错误，继续重试
                            pass
                except Exception:
                    # 其他错误，继续重试
                    pass
                except Exception:
                    # 其他错误，继续重试
                    pass
                
                time.sleep(0.5)
                retry_count += 1
            
            print("⚠️  后端服务启动超时，但继续启动前端...")
            print("   如果前端无法连接，请手动检查后端状态: make status-backend")
        elif not args.foreground:
            print("\n💡 提示:")
            print("   - 后端已在后台运行")
            print("   - 启动前端: python -m frontend.main chat")
            print("   - 停止后端: python cli.py stop")
            print("   - 查看状态: python cli.py status")

if __name__ == "__main__":
    # 注册退出处理
    def cleanup():
        pass  # 不自动停止，让用户手动控制
    
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))
    
    main()
