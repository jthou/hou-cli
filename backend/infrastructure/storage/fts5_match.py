"""
FTS5 MATCH 查询串构造（任务队列全文检索用）。

时间：2026-03-14；理由：用户要求用 SQLite FTS5 做已完成任务检索；方法：空白分词 + 非 ASCII 段用双引号短语，
多段用 OR 提高召回；避免注入 FTS 特殊语法（引号转义）。

无兜底：空或过短输入返回空串，由调用方回退关键词排序（见 completed_tasks_prompt）。
"""
from __future__ import annotations

import re
from typing import List


def build_fts5_match_query(raw: str) -> str:
    """
    生成 FTS5 MATCH 子句内容（不含 WHERE/MATCH 关键字）。

    - 英文/数字/下划线连续段（>=2）作为裸词；
    - 含中文或其它符号的连续非空段作为双引号短语（内部 \" 转义为 \"\"）；
    - 各段之间 OR。
    """
    q = (raw or "").strip()[:800]
    if len(q) < 2:
        return ""

    segments: List[str] = []
    for seg in re.split(r"\s+", q):
        if not seg:
            continue
        if re.match(r"^[a-zA-Z0-9_.-]{2,}$", seg):
            segments.append(seg)
        else:
            esc = seg.replace('"', '""')
            segments.append(f'"{esc}"')

    if not segments:
        return ""
    return " OR ".join(segments)
