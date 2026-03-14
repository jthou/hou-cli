#!/usr/bin/env python3
"""
测试 MediaWiki 看板 API 读写。
用法（项目根目录）：python scripts/test_kanban_api.py [board_id]
默认测试看板「石头科技-AI4SE」(ID: 15)。
"""
import os
import sys
import json

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from pathlib import Path
from shared.load_env import load_env
load_env(Path(_root))


def main():
    from backend.services.mediawiki_client_service.client import (
        MediaWikiClientService,
        MediaWikiClientError,
    )

    board_id = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    print(f"测试看板 ID={board_id}（石头科技-AI4SE）")
    print("-" * 50)

    client = MediaWikiClientService()
    try:
        client.connect()
    except MediaWikiClientError as e:
        print(f"连接失败: {e}")
        sys.exit(1)

    # 使用哪个账号
    user = client.bot_name or client.username or "匿名"
    print(f"当前 API 用户: {user}")
    print()

    # 1. 获取看板列表（含 raw 响应便于调试）
    print("1. 获取看板列表 (getboards filter_status=all)")
    try:
        raw = client.site.api("kanban", kanban_action="getboards", filter_status="all")
        if "error" in raw:
            print(f"   ❌ API 返回错误: {raw}")
        else:
            boards = raw.get("boards", [])
            print(f"   ✅ 共 {len(boards)} 个看板")
            for b in boards:
                bid = b.get("board_id")
                name = b.get("board_name", "")
                if bid == board_id or "石头" in name or "AI4SE" in name:
                    print(f"      [*] ID={bid} 名称={name}")
                elif len(boards) <= 10:
                    print(f"      - ID={bid} 名称={name}")
    except Exception as e:
        print(f"   ❌ 异常: {e}")
        import traceback
        traceback.print_exc()

    # 2. 获取单个看板详情（含 raw 响应）
    print()
    print(f"2. 获取看板详情 (getboard board_id={board_id})")
    try:
        raw = client.site.api("kanban", kanban_action="getboard", board_id=board_id)
        if "error" in raw:
            err = raw.get("error", {})
            print(f"   ❌ API 返回错误:")
            print(f"      code: {err.get('code')}")
            print(f"      info: {err.get('info')}")
            print(f"      完整: {json.dumps(raw, ensure_ascii=False, indent=2)}")
        else:
            board = raw.get("board")
            if not board:
                print(f"   ❌ 无 board 字段，完整响应: {json.dumps(raw, ensure_ascii=False)[:500]}")
            else:
                cols = board.get("columns", [])
                print(f"   ✅ 看板: {board.get('board_name', board_id)}")
                print(f"      列数: {len(cols)}")
                for c in cols:
                    print(f"         - column_id={c.get('column_id')} 名称={c.get('column_name')} 卡片数={len(c.get('cards', []))}")
    except Exception as e:
        print(f"   ❌ 异常: {e}")
        import traceback
        traceback.print_exc()

    # 3. 尝试创建任务（需要有效的 column_id）
    print()
    print("3. 尝试创建任务 (createtask)")
    try:
        board = client.kanban_get_board(board_id)
        columns = board.get("columns", [])
        if not columns:
            print("   ⚠ 看板无列，跳过创建任务")
        else:
            col = columns[0]
            col_id = col.get("column_id")
            col_name = col.get("column_name", "")
            title = "hou-cli 测试任务（可删除）"
            print(f"   使用列: column_id={col_id} ({col_name})")
            task_id = client.kanban_create_task(
                board_id=board_id,
                column_id=col_id,
                title=title,
                description="脚本 test_kanban_api.py 写入测试",
                priority="low",
            )
            print(f"   ✅ 创建成功 task_id={task_id}")
            print(f"   可在 MediaWiki 看板中删除该测试任务")
    except MediaWikiClientError as e:
        print(f"   ❌ MediaWikiClientError: {e}")
    except Exception as e:
        print(f"   ❌ 异常: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("测试完成")


if __name__ == "__main__":
    main()
