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
    # 如果是通过 PyInstaller 打包的，跳过虚拟环境检查
    if getattr(sys, 'frozen', False):
        # 打包后的可执行文件，不需要虚拟环境
        return
    
    # 开发环境才检查虚拟环境
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
    """根据端口号查找进程 PID（优先 LISTEN 进程）"""
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if f":{port}" in line and "LISTENING" in line:
                        parts = line.split()
                        if parts:
                            try:
                                return int(parts[-1])
                            except ValueError:
                                continue
        else:
            # 优先查找 LISTEN 进程（服务端），避免误杀客户端
            result = subprocess.run(
                ["lsof", "-i", f":{port}", "-P", "-n"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.strip().split('\n')[1:]:
                    if "LISTEN" in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                return int(parts[1])
                            except ValueError:
                                pass
            # 无 LISTEN 时退回用 -ti 取第一个
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
    
    # 5. 等待端口完全释放（OS 需要时间回收）
    time.sleep(2)
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
            # 将 stderr 重定向到日志文件，以便调试
            log_dir = get_app_data_dir() / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "backend_startup.log"
            
            # 写入启动标记
            with open(log_file, 'a') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"后端启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*60}\n")
            
            # 打开日志文件用于 stderr 重定向
            stderr_file = open(log_file, 'a')
            process = subprocess.Popen(
                [sys.executable, "-m", "backend.main"],
                stdout=subprocess.DEVNULL,
                stderr=stderr_file,  # 将 stderr 写入日志文件
                start_new_session=True
            )
            # 不关闭文件，让进程继续使用
        
        save_pid(process.pid)
        
        # 检查进程是否立即退出（启动失败）
        # 增加等待时间，因为后端启动需要初始化任务处理器等
        time.sleep(2)
        if process.poll() is not None:
            # 进程已退出，说明启动失败
            error_msg = f"后端启动失败 (退出码: {process.returncode})"
            # 读取日志文件的最后几行
            log_file = get_app_data_dir() / "logs" / "backend_startup.log"
            if log_file.exists():
                try:
                    with open(log_file, 'r') as f:
                        lines = f.readlines()
                        if lines:
                            last_lines = ''.join(lines[-20:])  # 最后20行
                            error_msg += f"\n错误信息（最后20行）:\n{last_lines}"
                except Exception:
                    pass
            # 关闭 stderr 文件（如果存在）
            if 'stderr_file' in locals():
                try:
                    stderr_file.close()
                except Exception:
                    pass
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

def stop_backend(cleanup=False):
    """停止后端服务
    
    Args:
        cleanup: 是否清除运行环境（默认 False）
    """
    if cleanup:
        # 清除运行环境（包括停止进程、清理 PID 文件等）
        cleanup_environment()
        return True
    
    # 简单停止（保留 PID 文件）
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
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="停止时清除运行环境（仅用于 stop 命令）"
    )
    
    args = parser.parse_args()
    
    if args.command == "stop":
        stop_backend(cleanup=args.cleanup)
        return
    
    if args.command == "restart":
        # 重启时总是先清理环境
        cleanup_environment()
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
        
        if args.wait:
            # 如果使用了 --wait，等待后端启动后启动前端
            if not backend_was_running:
                # 等待后端启动完成
                print("⏳ 等待后端服务启动...")
                # 先等待一下，让后端有时间启动
                time.sleep(3)
                
                max_retries = 40  # 增加重试次数到40次（总共约20秒）
                retry_count = 0
                port_file_found = False
                
                while retry_count < max_retries:
                    try:
                        # 先检查端口文件是否存在
                        port_file = get_port_file()
                        if not port_file.exists():
                            time.sleep(0.5)
                            retry_count += 1
                            continue
                        
                        port_file_found = True
                        port = load_port()
                        # 检查端口是否为有效值（大于1024，允许8000）
                        if port and port > 1024:
                            # 使用 httpx 进行健康检查，配置 trust_env=False 跳过代理
                            try:
                                response = httpx.get(
                                    f"http://127.0.0.1:{port}/health", 
                                    timeout=3.0,  # 增加超时时间
                                    trust_env=False  # 跳过代理，避免 502 错误
                                )
                                if response.status_code == 200:
                                    # 验证响应内容
                                    try:
                                        data = response.json()
                                        if data.get("status") == "ok":
                                            print("✅ 后端服务已就绪")
                                            break
                                    except Exception:
                                        # JSON解析失败，但HTTP状态码是200，也算成功
                                        print("✅ 后端服务已就绪")
                                        break
                            except httpx.ConnectError:
                                # 连接错误，继续重试
                                pass
                            except httpx.TimeoutException:
                                # 超时，继续重试
                                pass
                            except httpx.RequestError:
                                # 其他请求错误，继续重试
                                pass
                            except Exception as e:
                                # 其他错误，继续重试
                                pass
                    except Exception:
                        # 其他错误，继续重试
                        pass
                    
                    time.sleep(0.5)
                    retry_count += 1
                
                if retry_count >= max_retries:
                    if not port_file_found:
                        print("⚠️  后端服务启动超时：未找到端口文件")
                        print("   请检查后端服务是否正常启动")
                    else:
                        port = load_port()
                        print(f"⚠️  后端服务启动超时：端口文件存在（端口: {port}），但健康检查失败")
                        print("   请检查后端服务是否正常启动，或手动检查后端日志")
                    print("   继续启动前端...")
                    print("   如果前端无法连接，请手动检查后端状态")
            else:
                print("✅ 后端服务已在运行")
            
            # 无论后端是新启动还是已运行，都启动前端
            if not args.foreground:
                print("\n🚀 启动前端交互式界面...")
                try:
                    # 不设置 check=True，允许前端正常退出（如配置检查失败）
                    result = subprocess.run(
                        [sys.executable, "-m", "frontend.main", "chat"]
                    )
                    # 如果前端退出码不为 0，说明可能是配置错误
                    if result.returncode != 0:
                        print(f"\n⚠️  前端退出（退出码: {result.returncode}）")
                        print("   可能是配置未完成，请检查 ~/.config/hou-cli/.env")
                except KeyboardInterrupt:
                    print("\n⏹️  前端已停止")
                    stop_backend()
                except Exception as e:
                    print(f"❌ 前端启动失败: {e}")
                    stop_backend()
                    sys.exit(1)
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
