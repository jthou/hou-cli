"""
LLM 对话审计：记录每次送入 LLM 的输入与 LLM 的输出，便于审计与排查。
日志按日写入 JSONL 文件，存于应用数据目录 llm_audit/ 下。
同一次调用的 request / response / response_error 通过 meta.audit_id 关联。

可通过环境变量关闭：LLM_AUDIT_DISABLED=1 或 true/yes 时不写入任何记录。
"""
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _is_audit_disabled() -> bool:
    """环境变量 LLM_AUDIT_DISABLED=1|true|yes 时关闭审计写入。"""
    v = os.environ.get("LLM_AUDIT_DISABLED", "").strip().lower()
    return v in ("1", "true", "yes")


def create_audit_id() -> str:
    """生成单次 LLM 调用的审计关联 ID，用于在日志中配对 request 与 response。"""
    return uuid.uuid4().hex[:16]


# 单条内容在审计中的最大长度（字符），超出截断并注明
MAX_CONTENT_LEN = 50000
# 单条消息预览最大长度
MAX_MESSAGE_PREVIEW_LEN = 8000


def _get_audit_dir() -> Path:
    try:
        from shared.platform_utils import get_app_data_dir
        d = get_app_data_dir() / "llm_audit"
        d.mkdir(parents=True, exist_ok=True)
        return d
    except Exception as e:
        logger.warning("LLM 审计目录不可用: %s", e)
        return None


def _today_file() -> Optional[Path]:
    d = _get_audit_dir()
    if d is None:
        return None
    return d / f"llm_audit_{datetime.utcnow().strftime('%Y-%m-%d')}.jsonl"


def _truncate(s: str, max_len: int = MAX_CONTENT_LEN) -> str:
    if not s or len(s) <= max_len:
        return s or ""
    return s[:max_len] + "\n...(已截断)"


def _messages_summary(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """将 messages 转为可序列化、长度受控的摘要，用于审计。"""
    out = []
    for m in messages:
        role = m.get("role", "")
        content = m.get("content") or m.get("text") or ""
        if isinstance(content, str):
            preview = _truncate(content, MAX_MESSAGE_PREVIEW_LEN)
        else:
            s = str(content)
            preview = s[:MAX_MESSAGE_PREVIEW_LEN] + ("...(已截断)" if len(s) > MAX_MESSAGE_PREVIEW_LEN else "")
        out.append({
            "role": role,
            "content_length": len(str(content)),
            "content_preview": preview,
        })
    return {"message_count": len(messages), "messages": out}


def _response_summary(content: Any, model: str) -> Dict[str, Any]:
    """将 LLM 返回内容转为可序列化的摘要。"""
    if content is None:
        return {"type": "null"}
    if isinstance(content, str):
        return {
            "type": "text",
            "content_length": len(content),
            "content_preview": _truncate(content, MAX_CONTENT_LEN),
        }
    # 可能是 message 对象（含 tool_calls）
    if hasattr(content, "content") and content.content:
        return {
            "type": "text",
            "content_length": len(content.content),
            "content_preview": _truncate(content.content, MAX_CONTENT_LEN),
        }
    if hasattr(content, "tool_calls") and content.tool_calls:
        names = [
            getattr(t, "function", None) and getattr(t.function, "name", None) or str(t)
            for t in content.tool_calls
        ]
        return {"type": "tool_calls", "count": len(content.tool_calls), "names": names}
    return {"type": "other", "repr": _truncate(repr(content), 2000)}


def append_audit(
    direction: str,
    model: str,
    payload: Dict[str, Any],
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    """
    追加一条 LLM 审计记录。失败仅打日志，不抛异常。
    LLM_AUDIT_DISABLED=1 时不写入。

    Args:
        direction: "request" | "response" | "response_error"
        model: 模型名
        payload: 请求时为 messages 摘要，响应时为 content 摘要
        meta: 可选，如 session_id, usage, error
    """
    if _is_audit_disabled():
        return
    path = _today_file()
    if path is None:
        return
    record = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "direction": direction,
        "model": model,
        "payload": payload,
        **(meta or {}),
    }
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("写入 LLM 审计日志失败: %s", e)
