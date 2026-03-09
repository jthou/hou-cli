"""字节预算与单条大小限制

借鉴 OpenClaw：capArrayByJsonBytes、单条消息大小上限、超大消息占位符。
防止 context 溢出、单条超大消息拖垮内存/网络。
"""
import json
from typing import List, Tuple, Any

# 默认单条消息最大字节数（128KB）
DEFAULT_MAX_SINGLE_MESSAGE_BYTES = 128 * 1024

# 默认总历史最大字节数（约 512KB，安全余量）
DEFAULT_MAX_HISTORY_BYTES = 512 * 1024

# 超大消息占位符
OVERSIZED_PLACEHOLDER = "[message omitted: too large]"


def _json_utf8_bytes(obj: Any) -> int:
    """计算对象 JSON 序列化后的 UTF-8 字节数。"""
    return len(json.dumps(obj, ensure_ascii=False).encode("utf-8"))


def replace_oversized_messages(
    messages: List[dict],
    max_single_message_bytes: int = DEFAULT_MAX_SINGLE_MESSAGE_BYTES,
) -> Tuple[List[dict], int]:
    """
    将超大消息替换为占位符。

    Args:
        messages: LLM 格式消息列表 [{"role": "...", "content": "..."}]
        max_single_message_bytes: 单条消息最大字节数

    Returns:
        (替换后的消息列表, 被替换的数量)
    """
    result: List[dict] = []
    replaced_count = 0
    for msg in messages:
        size = _json_utf8_bytes(msg)
        if size > max_single_message_bytes:
            result.append({
                "role": msg.get("role", "user"),
                "content": OVERSIZED_PLACEHOLDER,
            })
            replaced_count += 1
        else:
            result.append(msg)
    return result, replaced_count


def cap_array_by_json_bytes(
    items: List[dict],
    max_bytes: int,
) -> Tuple[List[dict], int]:
    """
    按 JSON 字节数从头部截断，保留尾部（最近的消息）。

    Args:
        items: 消息列表
        max_bytes: 最大总字节数

    Returns:
        (截断后的消息列表, 实际字节数)
    """
    if not items:
        return [], 2  # 空数组 "[]" 约 2 字节

    parts = [_json_utf8_bytes(item) for item in items]
    # 总字节 ≈ 2 + sum(parts) + (len-1) 个逗号
    total = 2 + sum(parts) + max(0, len(parts) - 1)
    start = 0
    while total > max_bytes and start < len(items) - 1:
        total -= parts[start] + 1
        start += 1
    return items[start:], total


def enforce_history_budget(
    messages: List[dict],
    max_bytes: int = DEFAULT_MAX_HISTORY_BYTES,
    max_single_message_bytes: int = DEFAULT_MAX_SINGLE_MESSAGE_BYTES,
) -> List[dict]:
    """
    对 LLM 消息列表应用字节预算：先替换超大单条，再按总字节截断。

    Args:
        messages: LLM 格式消息列表
        max_bytes: 总历史最大字节数
        max_single_message_bytes: 单条消息最大字节数

    Returns:
        处理后的消息列表
    """
    replaced, _ = replace_oversized_messages(messages, max_single_message_bytes)
    capped, _ = cap_array_by_json_bytes(replaced, max_bytes)
    return capped
