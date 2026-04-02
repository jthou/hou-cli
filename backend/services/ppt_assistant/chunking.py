"""长文分块：固定窗口 + overlap，供功能一多轮抽取。"""

from __future__ import annotations

from typing import List


def chunk_text(text: str, max_chars: int, overlap: int) -> List[str]:
    """
    将文本切成多段，每段最长 max_chars，相邻段重叠 overlap 字符。
    overlap 避免论点在边界被截断。
    """
    t = text or ""
    if not t.strip():
        return []
    if max_chars <= 0:
        return [t]
    if len(t) <= max_chars:
        return [t]

    chunks: List[str] = []
    start = 0
    step = max(1, max_chars - max(0, overlap))
    while start < len(t):
        end = min(start + max_chars, len(t))
        chunk = t[start:end]
        chunks.append(chunk)
        if end >= len(t):
            break
        start += step
    return chunks
