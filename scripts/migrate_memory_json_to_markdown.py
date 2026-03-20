#!/usr/bin/env python3
"""将 FileLongTermMemory (JSON) 迁移到 MarkdownLongTermMemory (MEMORY.md)

设计文档：docs/design/01-three-level-memory-and-context-design.md
用法：python scripts/migrate_memory_json_to_markdown.py [--dry-run]
"""
import argparse
import json
import sys
from pathlib import Path

# 确保项目根在 path 中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared.platform_utils import get_app_data_dir
from backend.core.context.long_term_memory.models import Memory, MemoryType
from backend.core.memory.long_term.markdown_memory import MarkdownLongTermMemory


def load_json_memories(storage_dir: Path) -> list[Memory]:
    """从 FileLongTermMemory 目录加载所有记忆"""
    index_file = storage_dir / "index.json"
    memories_dir = storage_dir / "memories"
    memories = []
    if not index_file.exists():
        return memories
    try:
        data = json.loads(index_file.read_text(encoding="utf-8"))
        for mem_id, m in data.get("memories", {}).items():
            if not isinstance(m, dict):
                continue
            try:
                memories.append(Memory.from_dict(m))
            except Exception:
                pass
    except Exception as e:
        print(f"警告: 读取 index.json 失败: {e}", file=sys.stderr)
    return memories


def main():
    parser = argparse.ArgumentParser(description="JSON 长期记忆 → MEMORY.md 迁移")
    parser.add_argument("--dry-run", action="store_true", help="仅打印，不写入")
    parser.add_argument("--json-dir", type=Path, default=None, help="JSON 存储目录，默认 get_app_data_dir()/long_term_memory")
    args = parser.parse_args()

    json_dir = args.json_dir
    if not json_dir:
        for d in [get_app_data_dir() / "long_term_memory", PROJECT_ROOT / "data" / "long_term_memory"]:
            if d.exists():
                json_dir = d
                break
        json_dir = json_dir or (get_app_data_dir() / "long_term_memory")
    if not json_dir.exists():
        print(f"JSON 目录不存在: {json_dir}，无需迁移")
        return 0

    memories = load_json_memories(json_dir)
    if not memories:
        print("未找到可迁移的记忆")
        return 0

    print(f"找到 {len(memories)} 条记忆")
    md_memory = MarkdownLongTermMemory()
    if args.dry_run:
        for m in memories:
            print(f"  - [{m.memory_type.value}] {m.content[:50]}...")
        print("(dry-run，未写入)")
        return 0

    for m in memories:
        if md_memory.save_memory(m):
            print(f"  已迁移: {m.memory_id[:8]}...")
        else:
            print(f"  迁移失败: {m.memory_id}", file=sys.stderr)
    print(f"完成，已写入 {md_memory.memory_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
