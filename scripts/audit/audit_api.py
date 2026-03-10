#!/usr/bin/env python3
"""API 审计：扫描后端路由与前端 fetch 调用，比对并输出 API_PATH_AUDIT.md"""
import ast
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_API = PROJECT_ROOT / "backend" / "api"
FRONTEND_SRC = PROJECT_ROOT / "frontend" / "react-app" / "src"
OUTPUT_FILE = PROJECT_ROOT / "docs" / "audit" / "API_PATH_AUDIT.md"


def _extract_backend_routes() -> set:
    """从 backend/api/*.py 提取 @router.get/post/... 中的路径，考虑 router prefix"""
    routes = set()
    for py in BACKEND_API.glob("*.py"):
        if py.name in ("__init__.py", "routes.py", "web_routes.py"):
            continue
        text = py.read_text(encoding="utf-8")
        # 解析 router prefix
        prefix = ""
        pm = re.search(r'APIRouter\s*\(\s*prefix\s*=\s*["\']([^"\']+)["\']', text)
        if pm:
            prefix = pm.group(1).rstrip("/")
        # 匹配 @router.get("/path") 等
        for m in re.finditer(
            r'@router\.(get|post|put|patch|delete)\s*\(\s*["\']([^"\']+)["\']',
            text,
        ):
            method, path = m.group(1).upper(), m.group(2)
            full_path = (prefix + "/" + path.lstrip("/")) if prefix else path
            if not full_path.startswith("/api"):
                full_path = "/api" + full_path if full_path.startswith("/") else "/api/" + full_path
            routes.add(f"{method} {full_path}")
    return routes


def _extract_frontend_fetches() -> set:
    """从前端源码中提取 fetch('/api/...') 或 fetch(`/api/...`) 的路径"""
    fetches = set()
    for ext in ("*.js", "*.jsx", "*.ts", "*.tsx"):
        for p in FRONTEND_SRC.rglob(ext):
            try:
                text = p.read_text(encoding="utf-8")
            except Exception:
                continue
            # fetch('/api/xxx') 或 fetch(`/api/xxx`) 或 fetch(`/api/xxx${...}`)
            for m in re.finditer(
                r"fetch\s*\(\s*[`'\"](/api/[^`'\")\s]+)[`'\"]",
                text,
            ):
                path = m.group(1).split("?")[0].rstrip("/") or "/"
                fetches.add(f"GET {path}")  # 默认 GET，实际可能 POST 等，简化处理
            for m in re.finditer(
                r"fetch\s*\(\s*[`'\"](/api/[^`'\")\s]+)[`'\"]\s*,\s*\{\s*method:\s*['\"](\w+)['\"]",
                text,
            ):
                path = m.group(1).split("?")[0].rstrip("/") or "/"
                fetches.add(f"{m.group(2).upper()} {path}")
            # 模板字符串中的 /api/xxx
            for m in re.finditer(
                r"fetch\s*\(\s*`([^`]*)`\s*\)",
                text,
            ):
                s = m.group(1)
                if "/api/" in s:
                    base = re.sub(r"\$\{[^}]+\}", "", s)
                    base = re.sub(r"\?.*", "", base).strip()
                    if base.startswith("/api/"):
                        fetches.add(f"GET {base}")
    return fetches


def _normalize_path(p: str) -> str:
    """将 /api/task-queue/tasks/{task_id} 规范为可比较形式"""
    return re.sub(r"\{[^}]+\}", "{id}", p)


def run_api_audit(write_md: bool = True) -> dict:
    backend_routes = _extract_backend_routes()
    frontend_fetches = _extract_frontend_fetches()

    # 规范化后端路径用于匹配
    backend_normalized = {}
    for r in backend_routes:
        parts = r.split(" ", 1)
        method, path = parts[0], parts[1] if len(parts) > 1 else ""
        norm = _normalize_path(path)
        backend_normalized[norm] = backend_normalized.get(norm, set()) | {method}

    # 前端调用的路径（规范化）
    frontend_normalized = set()
    for f in frontend_fetches:
        parts = f.split(" ", 1)
        method, path = parts[0], parts[1] if len(parts) > 1 else ""
        norm = _normalize_path(path)
        frontend_normalized.add((norm, method))

    # 前端调用但后端可能未实现（简化：只检查路径存在）
    used_in_frontend = {p for p, _ in frontend_normalized}
    backend_paths = set(backend_normalized.keys())
    unused_by_frontend = backend_paths - used_in_frontend
    possibly_missing = used_in_frontend - backend_paths

    data = {
        "backend_routes": sorted(backend_routes),
        "frontend_fetches": sorted(frontend_fetches),
        "backend_path_count": len(backend_routes),
        "frontend_fetch_count": len(frontend_fetches),
        "unused_by_frontend": sorted(unused_by_frontend),
        "possibly_missing": sorted(possibly_missing),
    }
    if write_md:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_FILE.write_text(_render_md(data), encoding="utf-8")
    return data


def _render_md(data: dict) -> str:
    lines = [
        "# API 路径审计",
        "",
        f"- 后端路由数: {data['backend_path_count']}",
        f"- 前端 fetch 数: {data['frontend_fetch_count']}",
        "",
        "## 后端路由",
        "",
        "```",
    ]
    for r in data["backend_routes"]:
        lines.append(r)
    lines.extend(["```", "", "## 前端调用的 API", ""])
    for f in data["frontend_fetches"]:
        lines.append(f"- {f}")
    if data["unused_by_frontend"]:
        lines.extend(["", "## 后端有但前端未使用", ""])
        for p in data["unused_by_frontend"]:
            lines.append(f"- {p}")
    if data["possibly_missing"]:
        lines.extend(["", "## 前端调用但可能未实现（需人工核对）", ""])
        for p in data["possibly_missing"]:
            lines.append(f"- {p}")
    return "\n".join(lines)


def main():
    run_api_audit(write_md=True)
    print(f"API 审计已写入: {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
