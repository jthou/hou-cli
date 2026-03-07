"""
Agent 配备工具唯一配置：各 agent 使用的 tool 名称均在此定义，orchestrator 与审计页仅引用本模块，保证唯一性和准确性。
- 新增/修改工具时只改此处，orchestrator 按 agent 过滤工具、审计 API 返回 tools 列表均基于此配置。
"""
from typing import Dict, List

# ---------------------------------------------------------------------------
# 各 agent 配备的工具名称（与 ToolRegistry 中注册的 tool.name 一致）
# ---------------------------------------------------------------------------
AGENT_TOOLS: Dict[str, List[str]] = {
    "chat": [
        "browser",
        "browser_navigate",
        "browser_click",
        "browser_fill",
        "browser_search",
        "browser_extract",
        "google_search",
        "wikipedia",
        "mediawiki",
        "web_fetch",
        "video_downloader",
        "execute_code",
        "whisper",
        "ffmpeg",
        "get_weather",
        "file_search",
        "file_organizer",
        "pdf_parser",
        "zhihu_zhida",
        "kanban_board",
        "image_generation",
        "text_to_image_prompt",
    ],
    "article_writing": [],  # 写文章仅依据参考信息+用户提问，不调用工具
    "work_assistant": [],   # 工作助手不调用工具，仅基于知识作答
    # 以下 agent 在审计页有系统提示但无 LLM 工具调用，tools 为空
    "orchestrator_selector": [],
    "skill_matching": [],
    "model_selector": [],
}


def get_tool_names_for_agent(agent_id: str) -> List[str]:
    """
    返回指定 agent 配备的工具名称列表。
    若 agent_id 不在配置中则返回空列表
    （调用方可按需回退为「全部工具」）。
    """
    return list(AGENT_TOOLS.get(agent_id, []))


def get_tools_for_llm_by_agent(
    agent_id: str, tools_for_llm: List[dict]
) -> List[dict]:
    """
    从 LLM 格式的工具定义列表中筛出该 agent 配备的工具。
    tools_for_llm: ToolRegistry.get_tools_for_llm() 的返回值。
    若 agent 配置为空（如 work_assistant、article_writing），返回空列表。
    """
    names = get_tool_names_for_agent(agent_id)
    if not names:
        return []
    name_set = set(names)
    return [
        t
        for t in tools_for_llm
        if (t.get("function") or {}).get("name") in name_set
    ]
