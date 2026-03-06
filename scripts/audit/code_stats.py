#!/usr/bin/env python3
"""代码统计脚本：扫描仓库行数、文件数、语言分布，输出 stats/code_stats.json"""
import json
import os
import sys
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_FILE = PROJECT_ROOT / "docs" / "audit" / "code_stats.json"

# 单文件最大行数，超过则跳过（避免大数据文件拉高统计）
MAX_LINES_PER_FILE = 50000

# 排除的目录
EXCLUDE_DIRS = {
    ".git", "node_modules", "venv", "__pycache__", ".venv",
    "dist", "build", ".next", ".cache", "coverage", ".pytest_cache",
    "externals", "*.egg-info", ".mypy_cache", "mcps",
}

# 语言扩展名映射
LANG_EXT = {
    "python": (".py", ".pyi"),
    "javascript": (".js", ".mjs", ".cjs"),
    "typescript": (".ts", ".tsx"),
    "jsx": (".jsx",),
    "json": (".json",),
    "html": (".html", ".htm"),
    "css": (".css", ".scss", ".less"),
    "shell": (".sh", ".bash", ".zsh"),
    "markdown": (".md", ".mdx"),
    "yaml": (".yml", ".yaml"),
    "sql": (".sql",),
    "other": (),
}


def _should_exclude(p: Path) -> bool:
    for part in p.parts:
        if part in EXCLUDE_DIRS or part.startswith(".") and part != ".env":
            return True
        if "externals" in part or "node_modules" in part:
            return True
    return False


def _get_lang(ext: str) -> str:
    for lang, exts in LANG_EXT.items():
        if ext in exts:
            return lang
    return "other"


def count_lines(path: Path) -> int:
    try:
        with open(path, "rb") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def run_code_stats() -> dict:
    stats = {
        "total_files": 0,
        "total_lines": 0,
        "by_language": {},
        "by_directory": {},
        "generated_at": None,
    }
    by_lang = stats["by_language"]
    by_dir = stats["by_directory"]

    for root, dirs, files in os.walk(PROJECT_ROOT, topdown=True):
        root_path = Path(root)
        # 跳过排除目录
        dirs[:] = [d for d in dirs if not _should_exclude(root_path / d)]

        rel_root = root_path.relative_to(PROJECT_ROOT)
        rel_parts = rel_root.parts
        top_dir = rel_parts[0] if rel_parts else "."

        for f in files:
            fp = root_path / f
            if _should_exclude(fp):
                continue
            ext = fp.suffix.lower()
            if not ext and f != "Makefile":
                continue
            if ext == "" and f == "Makefile":
                ext = ".mk"
            lang = _get_lang(ext) if ext else "other"
            lines = count_lines(fp)
            if lines == 0 and lang == "other":
                continue
            if lines > MAX_LINES_PER_FILE:
                continue

            stats["total_files"] += 1
            stats["total_lines"] += lines
            by_lang[lang] = by_lang.get(lang, {"files": 0, "lines": 0})
            by_lang[lang]["files"] += 1
            by_lang[lang]["lines"] += lines
            by_dir[top_dir] = by_dir.get(top_dir, {"files": 0, "lines": 0})
            by_dir[top_dir]["files"] += 1
            by_dir[top_dir]["lines"] += lines

    from datetime import datetime, timezone
    stats["generated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return stats


def main():
    stats = run_code_stats()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"代码统计已写入: {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
