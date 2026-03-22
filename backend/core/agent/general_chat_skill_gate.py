# 时间：2026-03-22；理由：通用对话误匹配视频技能缺 input_file；方法：独立模块供 Orchestrator 与单测引用，避免 tests 导入 orchestrator 触发 load_env（Py3.9 兼容问题）
from __future__ import annotations

import os
import re


def general_chat_allows_skill_prematch(task: str) -> bool:
    """
    general_chat 是否允许走 skill_registry.match（音视频/下载类流水线）。

    - 默认 auto：无 URL、无本地路径倾向、无明确音视频关键词 → False，避免新闻/闲聊误命中。
    - GENERAL_CHAT_SKILL_PREMATCH: on/always/off/never/auto
    """
    mode = (os.getenv("GENERAL_CHAT_SKILL_PREMATCH") or "auto").strip().lower()
    if mode in ("1", "true", "on", "all", "always", "yes"):
        return True
    if mode in ("0", "false", "off", "never", "no"):
        return False
    t = (task or "").strip()
    if not t:
        return False
    tl = t.lower()
    if re.search(r"https?://", tl):
        return True
    if re.search(
        r"(?:^|[\s\"'`])(?:~/|/Users/|/home/|[a-z]:\\)",
        tl,
        re.IGNORECASE,
    ):
        return True
    if re.search(
        r"\.(?:mp4|mkv|mov|avi|m4v|webm|flv|mp3|wav|m4a|aac|srt|vtt)\b",
        tl,
        re.IGNORECASE,
    ):
        return True
    phrases = (
        "下载",
        "视频下载",
        "bilibili",
        "b站",
        "youtube",
        "字幕",
        "subtitles",
        "提取字幕",
        "提取音频",
        "提取视频",
        "提取片段",
        "语音转文字",
        "剪辑",
        "裁剪",
        "截取",
        "合并视频",
        "ffmpeg",
        "whisper",
        "压制",
        "嵌入字幕",
    )
    if any(p in t for p in phrases):
        return True
    en = ("download", "subtitle", "transcribe", "ffmpeg", "whisper")
    if any(p in tl for p in en):
        return True
    return False
