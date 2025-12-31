"""平台工具函数"""
import platform
from pathlib import Path

def get_app_data_dir() -> Path:
    """获取应用数据目录（跨平台）"""
    system = platform.system()
    
    if system == "Windows":
        return Path.home() / "AppData" / "Local" / "hou-cli"
    elif system == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "hou-cli"
    else:  # Linux
        return Path.home() / ".local" / "share" / "hou-cli"

def get_port_file() -> Path:
    """获取端口文件路径"""
    data_dir = get_app_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "port.txt"

def save_port(port: int):
    """保存端口号"""
    port_file = get_port_file()
    port_file.write_text(str(port))

def load_port() -> int:
    """加载端口号"""
    port_file = get_port_file()
    if port_file.exists():
        return int(port_file.read_text().strip())
    return 8000  # 默认端口

