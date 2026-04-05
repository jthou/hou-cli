"""模型配置审计 API：读取 .env 中配置的模型信息（不暴露密钥原文）"""
import os
from fastapi import APIRouter

from backend.services.llm.model_config import get_model_config_manager

router = APIRouter()

# Agent/组件 -> 模型映射（与 orchestrator、browser_tool 等实际使用一致）
# 每项: (agent_id, name, model_keys_or_expr, description)
AGENT_MODEL_MAPPING = [
    ("chat", "通用对话", ["CHAT_MODEL", "CODE_MODEL", "REASONING_MODEL"], "用户可选具体模型"),
    ("work_assistant", "工作助手", ["CHAT_MODEL", "CODE_MODEL", "REASONING_MODEL"], "用户可选具体模型"),
    ("article_writing", "写作助手", ["CHAT_MODEL", "CODE_MODEL", "REASONING_MODEL"], "用户可选具体模型"),
    ("ppt_assistant", "PPT 助手", ["CHAT_MODEL", "CODE_MODEL", "REASONING_MODEL"], "用户可选具体模型"),
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
    ("LLM_PROVIDER", "LLM 提供商", "bailian"),
    ("DEEPSEEK_MODEL", "DeepSeek 模型", "deepseek-chat"),
    ("BAILIAN_MODEL", "百炼平台模型", "qwen3-max"),
    ("TURBOGATEWAY_MODEL", "TheTurbo.ai 网关模型", "gpt-5"),
    ("CHAT_MODEL", "对话模型", "qwen3-max"),
    ("CODE_MODEL", "编码模型", "qwen3-coder-plus-2025-09-23"),
    ("REASONING_MODEL", "推理模型", "qwen3-max"),
    ("BROWSER_TOOL_VISION_MODEL", "Browser 视觉模型", "qwen-vl-max-2025-08-13"),
    ("BROWSER_TOOL_REASONING_MODEL", "Browser 推理模型", "qwen3-max"),
    ("BROWSER_TOOL_CHAT_MODEL", "Browser 对话模型", "qwen3-max"),
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
    provider = (os.getenv("LLM_PROVIDER") or "bailian").strip().lower()
    if provider == "bailian":
        return os.getenv("BAILIAN_MODEL", "qwen3-max")
    if provider == "theturbogateway":
        return os.getenv("TURBOGATEWAY_MODEL", "gpt-5")
    return os.getenv("DEEPSEEK_MODEL", "deepseek-chat")  # 仅 LLM_PROVIDER=deepseek 时


def _resolve_agent_models() -> list:
    """解析每个 agent 实际使用的模型"""
    default_llm = _get_default_llm_model()
    _m = get_model_config_manager()
    # 时间：2026-03-13；理由：与 ModelConfigManager 一致（含 REASONING_MODEL 空串→qwen3-max）；方法：统一走 get_*_model
    key_to_model = {
        "CHAT_MODEL": _m.get_chat_model(),
        "CODE_MODEL": _m.get_code_model(),
        "REASONING_MODEL": _m.get_reasoning_model(),
        "DEEPSEEK_MODEL": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "BAILIAN_MODEL": os.getenv("BAILIAN_MODEL", "qwen3-max"),
        "TURBOGATEWAY_MODEL": os.getenv("TURBOGATEWAY_MODEL", "gpt-5"),
        "BROWSER_TOOL_VISION_MODEL": os.getenv("BROWSER_TOOL_VISION_MODEL", "qwen-vl-max-2025-08-13"),
        "BROWSER_TOOL_REASONING_MODEL": os.getenv("BROWSER_TOOL_REASONING_MODEL", "qwen3-max"),
        "BROWSER_TOOL_CHAT_MODEL": os.getenv("BROWSER_TOOL_CHAT_MODEL", "qwen3-max"),
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
    _sel = get_model_config_manager()
    result["model_selection"] = [
        {"key": "CHAT_MODEL", "label": "对话模型", "value": _sel.get_chat_model()},
        {"key": "CODE_MODEL", "label": "编码模型", "value": _sel.get_code_model()},
        {"key": "REASONING_MODEL", "label": "推理模型", "value": _sel.get_reasoning_model()},
    ]

    return result


PROVIDER_LABELS = {
    "deepseek": "DeepSeek",
    "bailian": "百炼平台",
    "theturbogateway": "TheTurbo.ai 网关",
}

# 对话/编码/推理模型（写作助手、工作助手等）按供应商分组
# DeepSeek 平台：仅无版本号模型（chat/coder/reasoner）
# 百炼平台：带版本号的 deepseek-* 及 qwen 等
CHAT_MODELS_BY_PROVIDER = {
    "deepseek": [
        ("deepseek-chat", "DeepSeek Chat"),
        ("deepseek-coder", "DeepSeek Coder"),
        ("deepseek-reasoner", "DeepSeek Reasoner"),
    ],
    "bailian": [
        ("qwen3.6-plus", "Qwen3.6 Plus）"),
        ("qwen3-max", "Qwen3 Max"),
        ("qwen-plus-2025-12-01", "Qwen Plus"),
        ("qwen-flash", "Qwen Flash"),
        ("qwen-max-2025-01-25", "Qwen Max"),
        ("qwen-turbo-latest", "Qwen Turbo"),
        ("qwen3-coder-plus-2025-09-23", "Qwen3 Coder Plus"),
        ("qwen3-coder-flash", "Qwen3 Coder Flash"),
        ("qwen3-vl-plus-2025-12-19", "Qwen3-VL Plus"),
        ("qwen3-vl-flash-2025-10-15", "Qwen3-VL Flash"),
        ("qwen-vl-max-2025-08-13", "Qwen-VL Max"),
        ("qwq-plus", "QWQ Plus"),
        ("qvq-max-latest", "QVQ Max"),
        ("qvq-plus-latest", "QVQ Plus"),
        ("deepseek-r1", "DeepSeek R1（百炼）"),
        ("deepseek-v2", "DeepSeek V2（百炼）"),
        ("deepseek-v2.5", "DeepSeek V2.5（百炼）"),
        ("deepseek-v3", "DeepSeek V3（百炼）"),
        ("deepseek-v3.2", "DeepSeek V3.2（百炼）"),
        ("deepseek-chat", "DeepSeek Chat（百炼）"),
        ("deepseek-coder", "DeepSeek Coder（百炼）"),
        ("deepseek-reasoner", "DeepSeek Reasoner（百炼）"),
    ],
    "theturbogateway": [
        ("gpt-4o", "GPT-4o"),
        ("gpt-4o-mini", "GPT-4o Mini"),
        ("gpt-5", "GPT-5"),
        ("gpt-5-mini", "GPT-5 Mini"),
        ("o3", "O3"),
        ("o3-mini", "O3 Mini"),
        ("claude-opus-4-20250514", "Claude Opus 4"),
        ("claude-sonnet-4-20250514", "Claude Sonnet 4"),
        ("claude-sonnet-4-5-20250929", "Claude Sonnet 4.5"),
        ("gemini-2.5-pro", "Gemini 2.5 Pro"),
        ("gemini-2.5-flash", "Gemini 2.5 Flash"),
        ("sonar", "Sonar"),
        ("sonar-pro", "Sonar Pro"),
    ],
}

# 视觉模型（OCR/截图识别）按供应商分组
VISION_MODELS_BY_PROVIDER = {
    "bailian": [
        ("qwen3-vl-plus-2025-12-19", "Qwen3-VL Plus"),
        ("qwen3-vl-flash-2025-10-15", "Qwen3-VL Flash"),
        ("qwen-vl-max-2025-08-13", "Qwen-VL Max"),
        ("qwen-vl-plus-latest", "Qwen-VL Plus"),
        ("qwen3-vl-32b-thinking", "Qwen3-VL 32B Thinking"),
    ],
    "theturbogateway": [
        ("gpt-4o", "GPT-4o"),
        ("gpt-4o-mini", "GPT-4o Mini"),
        ("gemini-2.5-pro", "Gemini 2.5 Pro"),
        ("gemini-2.5-flash", "Gemini 2.5 Flash"),
        ("claude-opus-4-20250514", "Claude Opus 4"),
        ("claude-sonnet-4-20250514", "Claude Sonnet 4"),
    ],
}


def _get_vision_providers():
    """返回视觉模型按供应商分组，用于前端选择"""
    env_default = os.getenv(
        "WEB_READER_OCR_MODEL",
        os.getenv("BROWSER_TOOL_VISION_MODEL", "qwen3-vl-plus-2025-12-19"),
    )
    from backend.services.llm.model_registry import ModelRegistry

    provider, _ = ModelRegistry.parse_model_name(env_default)
    providers = []
    for p in ["bailian", "theturbogateway"]:
        models = VISION_MODELS_BY_PROVIDER.get(p, [])
        if not models:
            continue
        providers.append({
            "id": p,
            "label": PROVIDER_LABELS.get(p, p),
            "models": [{"value": v, "label": lbl} for v, lbl in models],
        })
    return {"providers": providers, "default": env_default}


@router.get("/models/selectable")
async def get_selectable_models():
    """
    返回前端可选的模型列表，按供应商分组。
    - providers: [{ id, label, models: [{value, label}] }]，含各供应商可选模型列表
    - models: 扁平列表（向后兼容）
    """
    from backend.services.llm.model_registry import ModelRegistry

    _m = get_model_config_manager()
    chat_model = _m.get_chat_model()
    code_model = _m.get_code_model()
    reasoning_model = _m.get_reasoning_model()
    configured_vals = {chat_model, code_model, reasoning_model} - {""}

    # 使用完整模型列表，确保配置的模型在列表中（若不在则追加）
    by_provider = {}
    for p in ["deepseek", "bailian", "theturbogateway"]:
        models = CHAT_MODELS_BY_PROVIDER.get(p, [])
        items = [{"value": v, "label": lbl} for v, lbl in models]
        by_provider[p] = items

    # 确保 .env 中配置的模型在列表中
    for val in configured_vals:
        if not val:
            continue
        provider, _ = ModelRegistry.parse_model_name(val)
        if provider in by_provider:
            seen = {m["value"] for m in by_provider[provider]}
            if val not in seen:
                by_provider[provider].append({"value": val, "label": val})

    # 时间：2026-03-21；理由：默认栈为百炼 Qwen；方法：下拉顺序百炼优先
    provider_order = ["bailian", "deepseek", "theturbogateway"]
    providers = []
    for p in provider_order:
        if p in by_provider and by_provider[p]:
            providers.append({
                "id": p,
                "label": PROVIDER_LABELS.get(p, p),
                "models": by_provider[p],
            })

    flat = []
    for p in provider_order:
        if p in by_provider:
            flat.extend(by_provider[p])
    # 已移除「智能选择」，用户需显式选择模型
    models = flat
    # 视觉模型（OCR/截图识别）：按供应商分组，供网页阅读等使用
    vision_providers = _get_vision_providers()
    return {
        "success": True,
        "models": models,
        "providers": providers,
        "vision_providers": vision_providers,
        "default_model": chat_model,
        # 时间：2026-04-04；理由：写作助手优先深度思考与改稿精度；方法：默认 qwen3.6-plus（与百炼模型 id 一致）
        "article_writing_default_model": "qwen3.6-plus",
        "ppt_assistant_default_model": "qwen3-max",  # PPT 助手固定默认（与写作助手同策略）
        # 时间：2026-03-13；理由：通用对话「深度思考」禁选下拉时需展示实际 REASONING_MODEL；方法与 get_reasoning_model() 一致
        "reasoning_model": reasoning_model,
    }


@router.get("/settings/model-stats")
async def get_model_stats(days: int = 30):
    """
    模型使用统计：响应时间、接受次数，按综合得分排名。
    - call_count: 调用次数
    - avg_response_ms: 平均响应时间（毫秒）
    - accepted_count: 被接受修改次数（写作助手场景点击「接受修改」）
    - score: 综合得分（接受次数权重高，响应越快越好）
    """
    try:
        from backend.services.llm.model_stats import get_model_stats as _get_stats
        stats = _get_stats(days=min(max(1, days), 90))
        return {"success": True, "stats": stats}
    except Exception as e:
        return {"success": False, "error": str(e), "stats": []}
