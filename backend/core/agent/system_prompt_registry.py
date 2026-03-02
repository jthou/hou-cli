"""
系统提示词审计：按 agent 汇总当前使用的系统提示与配备工具，供设置页「系统提示词审计」展示。
唯一数据源为 system_prompt_templates（提示）与 agent_tools_registry（工具），
与 orchestrator 引用同一配置。
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
from backend.core.agent.agent_tools_registry import get_tool_names_for_agent


def get_all_system_prompts() -> List[Dict[str, Any]]:
    """返回按 agent 划分的系统提示与工具列表，每项为 { "id", "name", "prompt", "tools" }。"""
    return [
        {
            "id": "chat",
            "name": "通用对话",
            "prompt": CHAT_SYSTEM_PROMPT,
            "tools": get_tool_names_for_agent("chat"),
        },
        {
            "id": "article_writing",
            "name": "写文章",
            "prompt": ARTICLE_WRITING_SYSTEM_PROMPT + ARTICLE_WRITING_NOTE,
            "tools": get_tool_names_for_agent("article_writing"),
        },
        {
            "id": "orchestrator_selector",
            "name": "智能编排选择器",
            "prompt": ORCHESTRATOR_SELECTOR_AUDIT_PROMPT,
            "tools": get_tool_names_for_agent("orchestrator_selector"),
        },
        {
            "id": "skill_matching",
            "name": "技能匹配",
            "prompt": SKILL_MATCHING_AUDIT_PROMPT,
            "tools": get_tool_names_for_agent("skill_matching"),
        },
        {
            "id": "model_selector",
            "name": "模型选择",
            "prompt": MODEL_SELECTOR_PROMPT,
            "tools": get_tool_names_for_agent("model_selector"),
        },
    ]
