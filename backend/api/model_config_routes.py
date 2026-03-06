"""模型配置审计 API：读取 .env 中配置的模型信息（不暴露密钥原文）"""
import os
from fastapi import APIRouter

router = APIRouter()

# Agent/组件 -> 模型映射（与 orchestrator、browser_tool 等实际使用一致）
# 每项: (agent_id, name, model_keys_or_expr, description)
AGENT_MODEL_MAPPING = [
    ("chat", "通用对话", ["CHAT_MODEL", "CODE_MODEL", "REASONING_MODEL"], "按任务智能选择"),
    ("work_assistant", "工作助手", ["CHAT_MODEL", "CODE_MODEL", "REASONING_MODEL"], "用户可选具体模型"),
    ("article_writing", "写文章", ["CHAT_MODEL", "CODE_MODEL", "REASONING_MODEL"], "按任务智能选择"),
    ("orchestrator_selector", "智能编排选择器", ["DEEPSEEK_MODEL", "BAILIAN_MODEL", "TURBOGATEWAY_MODEL"], "LLM_PROVIDER 决定"),
    ("skill_matching", "技能匹配", ["DEEPSEEK_MODEL", "BAILIAN_MODEL", "TURBOGATEWAY_MODEL"], "LLM_PROVIDER 决定"),
    ("model_selector", "模型选择", ["REASONING_MODEL"], "固定使用推理模型"),
    ("task_decomposer", "任务分解", ["REASONING_MODEL"], "固定使用推理模型"),
    ("autonomous_executor", "自主执行器", ["REASONING_MODEL"], "固定使用推理模型"),
    ("complexity_analyzer", "复杂度分析", ["CHAT_MODEL", "CODE_MODEL", "REASONING_MODEL"], "使用 orchestrator 当前模型"),
    ("research_manager", "研究管理", ["REASONING_MODEL", "CHAT_MODEL"], "推理+对话"),
    ("browser_tool", "Browser 工具", ["BROWSER_TOOL_VISION_MODEL", "BROWSER_TOOL_REASONING_MODEL", "BROWSER_TOOL_CHAT_MODEL"], "按任务类型选择"),
]

# API Key 类变量：仅显示「已设置」/「未设置」及长度，不暴露原文
API_KEY_KEYS = {
    "DEEPSEEK_API_KEY",
    "BAILIAN_API_KEY",
    "DASHSCOPE_API_KEY",
    "TURBOGATEWAY_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
}

# 模型/配置类变量：可安全展示
MODEL_CONFIG_KEYS = [
    ("LLM_PROVIDER", "LLM 提供商", "deepseek"),
    ("DEEPSEEK_MODEL", "DeepSeek 模型", "deepseek-chat"),
    ("BAILIAN_MODEL", "百炼平台模型", "qwen-turbo"),
    ("TURBOGATEWAY_MODEL", "TheTurbo.ai 网关模型", "gpt-5"),
    ("CHAT_MODEL", "对话模型", "deepseek-chat"),
    ("CODE_MODEL", "编码模型", "deepseek-coder"),
    ("REASONING_MODEL", "推理模型", "deepseek-reasoner"),
    ("BROWSER_TOOL_VISION_MODEL", "Browser 视觉模型", "qwen-vl-max-2025-08-13"),
    ("BROWSER_TOOL_REASONING_MODEL", "Browser 推理模型", "deepseek-reasoner"),
    ("BROWSER_TOOL_CHAT_MODEL", "Browser 对话模型", "deepseek-chat"),
    ("LLM_TEMPERATURE", "LLM 温度", "0.7"),
    ("LLM_MAX_TOKENS", "LLM 最大 Token", "2000"),
    ("DISABLE_SMART_MODEL_SELECTION", "禁用智能模型选择", "false"),
    ("BAILIAN_BASE_URL", "百炼 Base URL", ""),
    ("TURBOGATEWAY_BASE_URL", "TheTurbo Base URL", ""),
    ("DEEPSEEK_BASE_URL", "DeepSeek Base URL", ""),
]


def _mask_api_key(val: str) -> dict:
    """API Key 脱敏：仅返回是否设置及长度"""
    v = (val or "").strip()
    if not v:
        return {"set": False, "display": "未设置", "length": 0}
    return {"set": True, "display": f"已设置（{len(v)} 字符）", "length": len(v)}


def _get_default_llm_model() -> str:
    """获取 LLMService 默认模型（与 llm_service.py 逻辑一致）"""
    provider = (os.getenv("LLM_PROVIDER") or "deepseek").strip().lower()
    if provider == "bailian":
        return os.getenv("BAILIAN_MODEL", "qwen-turbo")
    if provider == "theturbogateway":
        return os.getenv("TURBOGATEWAY_MODEL", "gpt-5")
    return os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


def _resolve_agent_models() -> list:
    """解析每个 agent 实际使用的模型"""
    default_llm = _get_default_llm_model()
    key_to_model = {
        "CHAT_MODEL": os.getenv("CHAT_MODEL", "deepseek-chat"),
        "CODE_MODEL": os.getenv("CODE_MODEL", "deepseek-coder"),
        "REASONING_MODEL": os.getenv("REASONING_MODEL", "deepseek-reasoner"),
        "DEEPSEEK_MODEL": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "BAILIAN_MODEL": os.getenv("BAILIAN_MODEL", "qwen-turbo"),
        "TURBOGATEWAY_MODEL": os.getenv("TURBOGATEWAY_MODEL", "gpt-5"),
        "BROWSER_TOOL_VISION_MODEL": os.getenv("BROWSER_TOOL_VISION_MODEL", "qwen-vl-max-2025-08-13"),
        "BROWSER_TOOL_REASONING_MODEL": os.getenv("BROWSER_TOOL_REASONING_MODEL", "deepseek-reasoner"),
        "BROWSER_TOOL_CHAT_MODEL": os.getenv("BROWSER_TOOL_CHAT_MODEL", "deepseek-chat"),
    }
    out = []
    for agent_id, name, keys, desc in AGENT_MODEL_MAPPING:
        if keys == ["DEEPSEEK_MODEL", "BAILIAN_MODEL", "TURBOGATEWAY_MODEL"]:
            models_display = default_llm
        else:
            models_display = ", ".join(key_to_model.get(k, "?") for k in keys)
        out.append({
            "agent_id": agent_id,
            "name": name,
            "model_keys": keys,
            "models_resolved": models_display,
            "description": desc,
        })
    return out


@router.get("/settings/model-config-audit")
async def get_model_config_audit():
    """
    返回 .env 中配置的模型相关信息。
    - API Key 类：仅显示「已设置」/「未设置」及长度，不暴露原文
    - 模型名、Base URL 等：显示实际值
    """
    result = {"success": True, "api_keys": {}, "model_config": []}

    for key in API_KEY_KEYS:
        val = os.environ.get(key, "").strip()
        if not val and key == "DASHSCOPE_API_KEY":
            val = os.environ.get("BAILIAN_API_KEY", "").strip()
        result["api_keys"][key] = _mask_api_key(val)

    for key, label, default in MODEL_CONFIG_KEYS:
        val = os.environ.get(key, "")
        if val is None:
            val = ""
        val = str(val).strip()
        display = val if val else f"（默认: {default}）" if default else "未设置"
        result["model_config"].append({
            "key": key,
            "label": label,
            "value": val or None,
            "display": display,
        })

    result["agent_model_mapping"] = _resolve_agent_models()

    # 用户可选模型（模型选择下拉使用的配置）
    result["model_selection"] = [
        {"key": "CHAT_MODEL", "label": "对话模型", "value": os.getenv("CHAT_MODEL", "deepseek-chat")},
        {"key": "CODE_MODEL", "label": "编码模型", "value": os.getenv("CODE_MODEL", "deepseek-coder")},
        {"key": "REASONING_MODEL", "label": "推理模型", "value": os.getenv("REASONING_MODEL", "deepseek-reasoner")},
    ]

    return result


@router.get("/models/selectable")
async def get_selectable_models():
    """
    返回前端可选的模型列表（具体模型名）。
    - auto: 智能选择
    - 其余为配置的 chat/code/reasoning 模型名
    """
    chat_model = os.getenv("CHAT_MODEL", "deepseek-chat")
    code_model = os.getenv("CODE_MODEL", "deepseek-coder")
    reasoning_model = os.getenv("REASONING_MODEL", "deepseek-reasoner")

    models = [
        {"value": "auto", "label": "智能选择"},
        {"value": chat_model, "label": chat_model},
        {"value": code_model, "label": code_model},
        {"value": reasoning_model, "label": reasoning_model},
    ]
    # 去重：若 chat/code/reasoning 配置了相同模型，只保留一个
    seen = set()
    unique = []
    for m in models:
        if m["value"] not in seen:
            seen.add(m["value"])
            unique.append(m)
    return {"success": True, "models": unique}
