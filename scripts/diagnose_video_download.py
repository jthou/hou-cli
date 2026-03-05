#!/usr/bin/env python3
"""诊断视频下载失败任务：查询任务队列中的失败记录，并可选执行真实下载测试"""
import sys
import os

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from backend.infrastructure.storage.task_queue_db import (
    get_task_queue_db,
    TaskStatus,
)


def main():
    db = get_task_queue_db()
    print(f"任务队列数据库: {db.db_path}")
    print()

    # 1. 查询失败的 video_download 任务
    failed = db.list_tasks(
        status=TaskStatus.FAILED,
        limit=50,
        task_types=["video_download"],
        include_result=True,
    )
    print(f"=== 失败的视频下载任务 ({len(failed)} 个) ===\n")
    for t in failed:
        meta = t.get("metadata") or {}
        url = meta.get("url", "")
        err = t.get("error", "")
        created = t.get("created_at", "")
        task_id = t.get("task_id", "")
        print(f"任务 ID: {task_id}")
        print(f"  URL: {url}")
        print(f"  创建时间: {created}")
        print(f"  错误: {err[:500]}{'...' if len(err) > 500 else ''}")
        print()

    # 2. 最近所有 video_download 任务（含成功/失败）
    all_vd = db.list_tasks(
        limit=20,
        task_types=["video_download"],
        include_result=True,
    )
    print(f"=== 最近 20 个视频下载任务 ===\n")
    for t in all_vd:
        meta = t.get("metadata") or {}
        url = meta.get("url", "")
        status = t.get("status", "")
        err = t.get("error", "")
        created = t.get("created_at", "")
        task_id = t.get("task_id", "")
        print(f"[{status}] {task_id[:8]}... | {url}")
        if err:
            print(f"  错误: {err[:200]}...")
        print()


if __name__ == "__main__":
    main()
