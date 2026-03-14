#!/usr/bin/env python3
"""
MediaWiki parse API 测试脚本。
用法：python scripts/test_mediawiki_parse_api.py [--payload FILE]
默认使用 scripts/test_mediawiki_parse_payload.json（完整表格），不存在则用内置简化版。
"""
import argparse
import json
import sys
from pathlib import Path

# 添加项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 默认完整 payload 路径（与脚本同目录）
DEFAULT_PAYLOAD_FILE = Path(__file__).resolve().parent / "test_mediawiki_parse_payload.json"

# 内置简化版（payload 文件不存在时使用）
FALLBACK_WIKITEXT = """{| class="wikitable"
|+
!项目
!事项
!点（辅助工具）
!线（自动化系统）
!面（自主工具）
|-
|AI辅助软件流程
|
* 通过mcp、tools、agents、skills等技术深入到'''研发流程'''中，从点到面，完成AI4SE的智能化软件'''研发体系'''。
** 点：
*** 产品需求分解
*** 详细设计review
*** 代码review
** 线
** 面
|
*产品需求分析阶段
** 产品需求输入信息
** AI 辅助需求分析
|
* 产品数据系统打通
** 社交媒体、商城产品评论抓取与维护
|
* 建立统一的产品数据平台
|-
|AI辅助培训与落地
|
* 建立AI赋能中台
** 对各部门AI应用能力进行系统培训
|
* 基础培训材料准备
** AI辅助生成 AI 工具使用指南
|
* 系统化培训体系
|
|}"""


def main():
    parser = argparse.ArgumentParser(description="Test MediaWiki parse API")
    parser.add_argument(
        "--payload",
        type=Path,
        help="JSON file with {wikitext: '...', title?: '...'}",
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000",
        help="Backend base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--testclient",
        action="store_true",
        help="Use FastAPI TestClient (no server needed, connects to real MediaWiki)",
    )
    args = parser.parse_args()

    payload_path = args.payload or (DEFAULT_PAYLOAD_FILE if DEFAULT_PAYLOAD_FILE.exists() else None)
    if payload_path and Path(payload_path).exists():
        with open(payload_path) as f:
            payload = json.load(f)
        wikitext = payload.get("wikitext", "")
        if not args.payload and payload_path:
            print(f"(使用默认 payload: {payload_path.name})")
    else:
        wikitext = FALLBACK_WIKITEXT
        payload = {"wikitext": wikitext}
        print("(使用内置简化版，指定 --payload 可测完整内容)")

    input_rows = wikitext.count("|-")  # MediaWiki 表格行分隔符
    print(f"wikitext length: {len(wikitext)} chars, 表格行数: {input_rows}")
    print()

    if args.testclient:
        # 使用 TestClient，无需启动服务，会真实调用 MediaWiki
        from fastapi.testclient import TestClient
        from backend.main import app
        client = TestClient(app)
        r = client.post("/api/mediawiki/parse", json=payload)
        data = r.json()
    else:
        try:
            import httpx
        except ImportError:
            print("需要安装 httpx: pip install httpx")
            sys.exit(1)
        url = f"{args.url.rstrip('/')}/api/mediawiki/parse"
        print(f"POST {url}")
        try:
            r = httpx.post(url, json=payload, timeout=30.0)
            data = r.json()
        except Exception as e:
            print(f"请求失败: {e}")
            sys.exit(1)

    print(f"Status: {r.status_code}")
    print(f"Success: {data.get('success')}")

    if data.get("html"):
        html = data["html"]
        output_rows = html.count("<tr>")  # HTML 表格行数
        print(f"HTML length: {len(html)} chars, 表格行数: {output_rows}")
        # 表头 1 行 + 数据行，input_rows 不含表头
        expected_rows = 1 + input_rows  # <tr> 包含表头行
        if output_rows != expected_rows:
            print(f"  ⚠ 行数不一致: 预期 {expected_rows} 行, 实际 {output_rows} 行")
        checks = [
            ("产品需求分解", "产品需求分解" in html),
            ("AI辅助培训与落地", "AI辅助培训与落地" in html),
            ("AI知识体系流程搭建", "AI知识体系流程搭建" in html),
            ("AI问题分析", "AI问题分析" in html),
            ("AI基础设施建设", "AI基础设施建设" in html),
        ]
        for label, found in checks:
            print(f"  {label}: {'✓' if found else '✗'}")
        print()
        print("HTML 输出:")
        print("-" * 40)
        print(html)
    else:
        print("Error:", data.get("detail", data))
        sys.exit(1)


if __name__ == "__main__":
    main()
