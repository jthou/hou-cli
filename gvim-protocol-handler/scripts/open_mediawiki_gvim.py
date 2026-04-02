#!/usr/bin/env python3
"""从命令行打开 MediaWiki 词条到 gvim，与 HTTP /api/gvim 使用同一套 GvimService 逻辑。"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

_SCRIPT_DIR = Path(__file__).resolve().parent
_ROOT_FILE = _SCRIPT_DIR / "hou_cli_root.txt"
if _ROOT_FILE.is_file():
    _REPO_ROOT = Path(_ROOT_FILE.read_text(encoding="utf-8").strip())
elif os.environ.get("HOU_CLI_ROOT", "").strip():
    _REPO_ROOT = Path(os.environ["HOU_CLI_ROOT"].strip()).resolve()
else:
    # gvim-protocol-handler/scripts/*.py -> 仓库根为 scripts 上两级
    _REPO_ROOT = _SCRIPT_DIR.parent.parent.resolve()
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.services.gvim_service import GvimService, GvimServiceError
from shared.load_env import load_env


def title_from_hou_gvim_url(url: str) -> str:
    u = urlparse(url.strip())
    if u.scheme != "hou-gvim":
        raise ValueError(f"期望 hou-gvim 协议，收到: {u.scheme!r}")
    qs = parse_qs(u.query, keep_blank_values=False)
    for key in ("title", "page_title", "pageTitle"):
        if key in qs and qs[key]:
            return unquote(qs[key][0]).replace("+", " ")
    raise ValueError("URL 缺少查询参数 title / page_title / pageTitle")


def main() -> int:
    parser = argparse.ArgumentParser(description="用 gvim 打开 MediaWiki 词条（Hou CLI / GvimService）")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--title", help="词条标题（原始文本，无需编码）")
    g.add_argument("--url", help="hou-gvim://mediawiki?title=... 完整 URL")
    args = parser.parse_args()

    load_env(project_root=_REPO_ROOT)

    try:
        title = title_from_hou_gvim_url(args.url) if args.url else (args.title or "").strip()
        if not title:
            print("标题为空", file=sys.stderr)
            return 1
        svc = GvimService()
        svc.open_mediawiki_page(title)
    except GvimServiceError as e:
        print(str(e), file=sys.stderr)
        return 1
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
