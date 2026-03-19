#!/usr/bin/env python3
"""启动 LiteLLM 代理供百炼漫画使用。时间：2025-03-19；理由：Makefile 的 set -a 在 .env 含引号时易出错；方法：Python 加载 env 再 exec litellm"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in [ROOT / ".env", ROOT / ".baoyu-skills" / ".env", Path.home() / ".baoyu-skills" / ".env"]:
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and v and not os.environ.get(k):
                    os.environ[k] = v
if not os.environ.get("DASHSCOPE_API_KEY") and os.environ.get("BAILIAN_API_KEY"):
    os.environ["DASHSCOPE_API_KEY"] = os.environ["BAILIAN_API_KEY"]

cfg = ROOT / "config" / "litellm_comic_bailian.yaml"
os.chdir(ROOT)
sys.exit(subprocess.call(["litellm", "--config", str(cfg), "--port", "4000"]))
