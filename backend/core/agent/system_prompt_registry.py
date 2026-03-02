"""
系统提示词审计：按 agent 汇总当前使用的系统提示，供设置页「系统提示词审计」展示。
唯一数据源为 system_prompt_templates，与 orchestrator 引用同一模版。
"""
from typing import List, Dict, Any

from backend.core.agent.system_prompt_templates import (
    CHAT_SYSTEM_PROMPT,
    ARTICLE_WRITING_SYSTEM_PROMPT,
    ARTICLE_WRITING_NOTE,
    ORCHESTRATOR_SELECTOR_AUDIT_PROMPT,
    SKILL_MATCHING_AUDIT_PROMPT,
    MODEL_SELECTOR_PROMPT,
)


def get_all_system_prompts() -> List[Dict[str, Any]]:
    """返回按 agent 划分的系统提示列表，每项为 { "id", "name", "prompt" }。"""
    return [
        {"id": "chat", "name": "通用对话", "prompt": CHAT_SYSTEM_PROMPT},
        {
            "id": "article_writing",
            "name": "写文章",
            "prompt": ARTICLE_WRITING_SYSTEM_PROMPT + ARTICLE_WRITING_NOTE,
        },
        {
            "id": "orchestrator_selector",
            "name": "智能编排选择器",
            "prompt": ORCHESTRATOR_SELECTOR_AUDIT_PROMPT,
        },
        {"id": "skill_matching", "name": "技能匹配", "prompt": SKILL_MATCHING_AUDIT_PROMPT},
        {"id": "model_selector", "name": "模型选择", "prompt": MODEL_SELECTOR_PROMPT},
    ]
