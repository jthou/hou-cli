"""
统一 .env 加载逻辑。

所有入口（main、routes、frontend、脚本、测试）必须调用 load_env() 获取环境变量。
加载顺序：项目根 → 用户配置目录 → 当前目录。
override：全部 True，后续文件覆盖前面的，确保用户凭据（config_dir）覆盖项目根空占位。
"""
from pathlib import Path

from dotenv import load_dotenv

_CONFIG_DIR = Path.home() / ".config" / "hou-cli"


def load_env(project_root: Path | None = None) -> None:
    """
    加载 .env，统一逻辑。

    Args:
        project_root: 项目根目录；None 时从 shared 包位置推断
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent

    env_paths = [
        (project_root / ".env", True),
        (_CONFIG_DIR / ".env", True),
        (Path.cwd() / ".env", True),
    ]
    for env_path, override in env_paths:
        if env_path.exists():
            load_dotenv(env_path, override=override)


def load_env_for_file(file_path: str) -> None:
    """
    从任意文件路径推断项目根并加载。供脚本、测试使用。

    Args:
        file_path: 通常传 __file__
    """
    p = Path(file_path).resolve()
    for _ in range(8):
        if (p / "backend").is_dir() or (p / "frontend").is_dir() or (p / "scripts").is_dir():
            load_env(project_root=p)
            return
        parent = p.parent
        if parent == p:
            break
        p = parent
    load_env(project_root=Path.cwd())
