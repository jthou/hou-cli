"""版本信息 API：从 pyproject.toml 读取，作为单一事实来源"""
import re
from pathlib import Path

from fastapi import APIRouter

router = APIRouter()


def _get_version_from_pyproject() -> str:
    """从 pyproject.toml 读取 version，作为项目唯一版本源"""
    root = Path(__file__).resolve().parent.parent.parent
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return "0.1.0"
    try:
        text = pyproject.read_text(encoding="utf-8")
        m = re.search(r'version\s*=\s*["\']([^"\']+)["\']', text)
        return m.group(1) if m else "0.1.0"
    except Exception:
        return "0.1.0"


@router.get("/version")
async def get_version():
    """获取系统版本（从 pyproject.toml 读取）"""
    return {"version": _get_version_from_pyproject()}
