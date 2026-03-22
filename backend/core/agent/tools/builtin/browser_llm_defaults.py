"""
Browser 相关工具选用的默认模型名（与 LLMService 默认走百炼 Qwen 一致）。

时间：2026-03-21；理由：项目默认不再使用 DeepSeek 作为回退；方法：环境变量优先级链 + qwen3-max。
"""
from __future__ import annotations

import os


def browser_default_chat_model() -> str:
    """非视觉 browser-use 任务默认对话模型。"""
    return (
        (os.getenv("BROWSER_TOOL_CHAT_MODEL") or "").strip()
        or (os.getenv("CHAT_MODEL") or "").strip()
        or (os.getenv("BAILIAN_MODEL") or "").strip()
        or (os.getenv("DEEPSEEK_MODEL") or "").strip()
        or "qwen3-max"
    )


def browser_default_reasoning_model() -> str:
    """Browser 任务分析中「复杂任务」推荐的推理向模型。"""
    return (
        (os.getenv("BROWSER_TOOL_REASONING_MODEL") or "").strip()
        or (os.getenv("REASONING_MODEL") or "").strip()
        or (os.getenv("BAILIAN_MODEL") or "").strip()
        or (os.getenv("DEEPSEEK_MODEL") or "").strip()
        or "qwen3-max"
    )
