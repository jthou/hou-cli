#!/usr/bin/env python3
"""开发审计主入口：依次执行代码统计、开发历史、API 审计，输出 AUDIT_REPORT.json"""
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "docs" / "audit"
OUTPUT_FILE = OUTPUT_DIR / "AUDIT_REPORT.json"
AUDIT_DIR = Path(__file__).resolve().parent / "audit"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "code_stats": None,
        "dev_history": None,
        "api_audit": None,
    }

    # 1. 代码统计
    try:
        mod = _load_module("code_stats", AUDIT_DIR / "code_stats.py")
        report["code_stats"] = mod.run_code_stats()
        (OUTPUT_DIR / "code_stats.json").write_text(
            json.dumps(report["code_stats"], ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("✓ 代码统计完成")
    except Exception as e:
        report["code_stats"] = {"error": str(e)}
        print(f"✗ 代码统计失败: {e}")

    # 2. 开发历史
    try:
        mod = _load_module("dev_history", AUDIT_DIR / "dev_history.py")
        report["dev_history"] = mod.run_dev_history()
        (OUTPUT_DIR / "dev_history.json").write_text(
            json.dumps(report["dev_history"], ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("✓ 开发历史完成")
    except Exception as e:
        report["dev_history"] = {"error": str(e)}
        print(f"✗ 开发历史失败: {e}")

    # 3. API 审计
    try:
        mod = _load_module("audit_api", AUDIT_DIR / "audit_api.py")
        report["api_audit"] = mod.run_api_audit()
        print("✓ API 审计完成")
    except Exception as e:
        report["api_audit"] = {"error": str(e)}
        print(f"✗ API 审计失败: {e}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n审计报告已写入: {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
