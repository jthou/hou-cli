"""平台工具函数"""
import platform
from pathlib import Path
from typing import Optional

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

def get_default_download_dir() -> Path:
    """获取系统默认下载目录（跨平台）"""
    system = platform.system()
    if system == "Windows":
        # Windows: C:\Users\Username\Downloads\hou-cli-videos
        return Path.home() / "Downloads" / "hou-cli-videos"
    elif system == "Darwin":  # macOS
        # macOS: /Users/Username/Downloads/hou-cli-videos
        return Path.home() / "Downloads" / "hou-cli-videos"
    else:  # Linux
        # Linux: /home/username/Downloads/hou-cli-videos
        return Path.home() / "Downloads" / "hou-cli-videos"

def normalize_output_dir(output_dir: Optional[str] = None, restrict_to_home: bool = False) -> Path:
    """规范化输出目录路径，未指定则使用默认下载目录。

    Args:
        output_dir: 用户指定的输出目录，可为 None。
        restrict_to_home: 为 True 时路径须在用户主目录下，
            否则回退到默认下载目录（用于任务/API 等不可信输入）。
    """
    if output_dir:
        path = Path(output_dir).expanduser().resolve()
        if restrict_to_home:
            try:
                path.relative_to(Path.home().resolve())
            except ValueError:
                path = get_default_download_dir()
    else:
        path = get_default_download_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path

