"""消息清洗

借鉴 OpenClaw：stripEnvelope、sanitizeChatHistoryMessages。
去除 envelope 包装、截断过长内容、脱敏敏感字段。
"""
import re
from typing import List, Dict, Any

# 敏感字段（不传给 LLM，避免泄露）
SENSITIVE_KEYS = frozenset({
    "api_key", "apikey", "api-key",
    "secret", "token", "password", "passwd",
    "authorization", "auth",
})

# 默认单条 content 最大字符数（防止超长）
DEFAULT_MAX_CONTENT_CHARS = 50_000

# 常见 envelope 模式（如 ```json ... ``` 包裹）
_ENVELOPE_PAT = re.compile(
    r"^```(?:json|text)?\s*\n?(.*?)\n?```\s*$", re.DOTALL | re.IGNORECASE
)
_ENVELOPE_PRE = re.compile(
    r"^<\s*pre\s*>?(.*?)<\s*/\s*pre\s*>?\s*$", re.DOTALL | re.IGNORECASE
)
ENVELOPE_PATTERNS = [_ENVELOPE_PAT, _ENVELOPE_PRE]


def strip_envelope(text: str) -> str:
    """
    去除常见的 envelope 包装（如 markdown 代码块）。

    Args:
        text: 原始文本

    Returns:
        去除包装后的文本
    """
    if not text or not isinstance(text, str):
        return text
    t = text.strip()
    for pat in ENVELOPE_PATTERNS:
        m = pat.match(t)
        if m:
            return m.group(1).strip()
    return t


def _truncate_content(content: str, max_chars: int) -> str:
    """截断过长 content。"""
    if not content or len(content) <= max_chars:
        return content
    return content[: max_chars - 20] + "\n...[truncated]"


def _sanitize_metadata(metadata: dict) -> dict:
    """脱敏 metadata，移除敏感字段。"""
    if not metadata or not isinstance(metadata, dict):
        return {}
    return {
        k: v for k, v in metadata.items()
        if k.lower() not in SENSITIVE_KEYS
    }


def sanitize_message_for_llm(
    msg: Dict[str, Any],
    max_content_chars: int = DEFAULT_MAX_CONTENT_CHARS,
) -> Dict[str, str]:
    """
    清洗单条消息，供 LLM 使用。

    Args:
        msg: 消息 dict，可能含 role, content, metadata 等
        max_content_chars: content 最大字符数

    Returns:
        仅含 role, content 的 LLM 格式消息
    """
    role = str(msg.get("role", "user")).strip().lower()
    if role not in ("system", "user", "assistant", "tool"):
        role = "user"

    content = msg.get("content")
    if content is None:
        content = ""
    if isinstance(content, list):
        # 兼容 [{type: "text", text: "..."}] 格式
        parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
            elif isinstance(item, str):
                parts.append(item)
        content = "\n".join(parts)
    else:
        content = str(content)

    content = strip_envelope(content)
    content = _truncate_content(content, max_content_chars)

    return {"role": role, "content": content}


def sanitize_messages_for_llm(
    messages: List[Dict[str, Any]],
    max_content_chars: int = DEFAULT_MAX_CONTENT_CHARS,
) -> List[Dict[str, str]]:
    """
    批量清洗消息列表。

    Args:
        messages: 原始消息列表
        max_content_chars: 单条 content 最大字符数

    Returns:
        清洗后的 LLM 格式消息列表
    """
    return [
        sanitize_message_for_llm(m, max_content_chars)
        for m in messages
    ]
