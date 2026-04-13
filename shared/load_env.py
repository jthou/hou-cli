"""
统一 .env 加载逻辑。

所有入口（main、routes、frontend、脚本、测试）必须调用 load_env() 获取环境变量。
加载顺序：项目根 → 用户配置目录 → 当前目录。
override：全部 True，后续文件覆盖前面的，确保用户凭据（config_dir）覆盖项目根空占位。
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_CONFIG_DIR = Path.home() / ".config" / "hou-cli"


# 时间：2026-03-22；理由：Python 3.9 不支持 PEP604 内联 Union；方法：用 Optional[Path] 保持与 3.10+ 行为一致
def load_env(project_root: Optional[Path] = None) -> None:
    """
    加载 .env，统一逻辑。

    Args:
        project_root: 项目根目录；None 时从 shared 包位置推断
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent

    # 时间：2026-04-11；理由：cwd 与项目根相同时会二次加载同一 .env，把 ~/.config/hou-cli/.env 里已合并的凭据覆盖掉（MCP/后端表现为「明明配了却登录失败」）；方法：按路径去重后再 load，后者仍 override 前者
    env_paths = [
        project_root / ".env",
        _CONFIG_DIR / ".env",
        Path.cwd() / ".env",
    ]
    seen: set[Path] = set()
    for env_path in env_paths:
        try:
            key = env_path.resolve()
        except OSError:
            continue
        if key in seen:
            continue
        seen.add(key)
        if env_path.exists():
            load_dotenv(env_path, override=True)

    try:
        from shared.httpx_defaults import merge_hou_cli_no_proxy_hosts

        merge_hou_cli_no_proxy_hosts()
    except Exception:
        pass


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
