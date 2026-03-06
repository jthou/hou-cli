#!/usr/bin/env python3
"""开发历史统计：解析 git log，输出提交频率、作者、变更文件到 stats/dev_history.json"""
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_FILE = PROJECT_ROOT / "docs" / "audit" / "dev_history.json"


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(PROJECT_ROOT)] + list(args),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout.strip()


def run_dev_history() -> dict:
    data = {
        "total_commits": 0,
        "authors": {},
        "commits_by_week": {},
        "files_changed": {},
        "generated_at": None,
    }

    # 总提交数
    try:
        data["total_commits"] = int(_run_git("rev-list", "--count", "HEAD"))
    except Exception:
        data["total_commits"] = 0

    # 作者统计
    try:
        out = _run_git("shortlog", "-sn", "--all")
        for line in out.splitlines():
            parts = line.strip().split("\t", 1)
            if len(parts) == 2:
                count, author = int(parts[0]), parts[1].strip()
                data["authors"][author] = count
    except Exception:
        pass

    # 按周提交数（最近 52 周）
    try:
        out = _run_git("log", "--format=%ad", "--date=format:%Y-W%W", "-52")
        for line in out.splitlines():
            week = line.strip()
            if week:
                data["commits_by_week"][week] = data["commits_by_week"].get(week, 0) + 1
    except Exception:
        pass

    # 变更最多的文件（最近 500 次提交）
    try:
        out = _run_git("log", "--name-only", "--pretty=format:", "-500")
        for line in out.splitlines():
            f = line.strip()
            if f and not f.startswith("."):
                data["files_changed"][f] = data["files_changed"].get(f, 0) + 1
        # 取前 50
        sorted_files = sorted(
            data["files_changed"].items(),
            key=lambda x: -x[1],
        )[:50]
        data["files_changed"] = dict(sorted_files)
    except Exception:
        pass

    from datetime import datetime, timezone
    data["generated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return data


def main():
    data = run_dev_history()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"开发历史已写入: {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
