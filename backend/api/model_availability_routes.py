"""模型可用性审计 API：解析 .env 模型列表，对模型发起探测"""
import os
import re
from collections import defaultdict
from fastapi import APIRouter, Body
from pydantic import BaseModel
from typing import List, Optional

from backend.utils.env_models_parser import parse_env_models
from backend.services.llm.llm_service import probe_model
from backend.services.llm.model_registry import ModelRegistry

router = APIRouter()

# 百炼平台模型分类（按匹配顺序，先匹配先归属）
BAILIAN_CATEGORIES = [
    (r"^qwen3-coder-", "通义千问3 代码"),
    (r"^qwen3-vl-", "通义千问3 视觉理解"),
    (r"^qwen-vl-", "通义千问 VL"),
    (r"^qwen3-omni-", "通义千问3 全模态"),
    (r"^qwen-omni-", "通义千问 Omni"),
    (r"^qwen3-asr-", "通义千问3 语音识别"),
    (r"^qwen3-tts-", "通义千问3 语音合成"),
    (r"^qwen-tts-", "通义千问 TTS"),
    (r"^qwen3-livetranslate-", "通义千问3 翻译"),
    (r"^qwen-mt-", "通义千问 MT"),
    (r"^qwen-image-", "通义千问 图像生成"),
    (r"^wan2\.6-", "通义万相"),
    (r"^qwq-", "通义千问 推理"),
    (r"^qvq-", "通义千问 推理"),
    (r"^qwen2\.5-", "通义千问2.5 开源"),
    (r"^deepseek", "DeepSeek（百炼）"),
    (r"^glm-", "GLM 系列"),
    (r"^kimi-", "Kimi 系列"),
    (r"^fun-asr", "Fun-ASR 系列"),
    (r"^baichuan", "百川系列"),
    (r"^chatglm", "ChatGLM 系列"),
    (r"^llama", "LLaMA 系列"),
    (r"^qwen3\.6-plus$", "通义千问3 深度思考"),
    (r"^qwen3-max$", "通义千问3 文本生成"),
    (r"^qwen-plus-2025", "通义千问3 文本生成"),
    (r"^qwen-flash$", "通义千问3 文本生成"),
    (r"^qwen-max-2025", "通义千问3 文本生成"),
    (r"^qwen-turbo-latest$", "通义千问3 文本生成"),
    (r"^qwen-deep-research$", "通义千问3 文本生成"),
    (r"^qwen-turbo$", "通义千问 传统"),
    (r"^qwen-plus$", "通义千问 传统"),
    (r"^qwen-max", "通义千问 传统"),
    (r"^qwen-\d", "通义千问 传统"),
    (r"^qwen", "通义千问 其他"),
    (r".*", "其他百炼平台"),
]


def _get_bailian_category(model_name: str) -> str:
    """根据模型名返回百炼平台分类"""
    m = (model_name or "").lower().strip()
    # 支持 "bailian-模型" 格式，先去掉前缀再匹配
    if m.startswith("bailian-"):
        m = m[len("bailian-"):]
    for pattern, cat in BAILIAN_CATEGORIES:
        if re.match(pattern, m):
            return cat
    return "其他百炼平台"


PROVIDER_LABELS = {
    "deepseek": "DeepSeek",
    "bailian": "百炼平台",
    "theturbogateway": "TheTurbo.ai 网关",
    "other": "其他",
}
PROVIDER_ORDER = ["deepseek", "bailian", "theturbogateway"]

# 配置 key -> 提供商（配置行明确指定平台）
KEY_TO_PROVIDER = {
    "DEEPSEEK_MODEL": "deepseek",
    "BAILIAN_MODEL": "bailian",
    "TURBOGATEWAY_MODEL": "theturbogateway",
    "BROWSER_TOOL_VISION_MODEL": "bailian",  # 多为百炼 qwen-vl
    "BROWSER_TOOL_REASONING_MODEL": "deepseek",
    "BROWSER_TOOL_CHAT_MODEL": "deepseek",
}


class ProbeRequest(BaseModel):
    """探测请求体"""
    models: Optional[List[str]] = None  # 不传或空则使用 unique_models


def _get_provider(model_name: str, config_key: Optional[str] = None) -> str:
    """
    根据配置 key 或模型名推断提供商。
    配置 key 优先：DEEPSEEK_MODEL/BAILIAN_MODEL 等明确指定平台；
    CHAT_MODEL/CODE_MODEL/REASONING_MODEL 使用 LLM_PROVIDER。
    """
    model_lower = (model_name or "").lower().strip()
    # 模型名显式前缀优先（用户明确指定平台）
    if model_lower.startswith("bailian-"):
        return "bailian"
    if model_lower.startswith("theturbogateway-"):
        return "theturbogateway"
    if model_lower.startswith("deepseek-") and any(
        model_lower.startswith(f"deepseek-{x}")
        for x in ("deepseek", "qwen", "baichuan", "chatglm", "llama", "gpt")
    ):
        return "deepseek"
    # 配置 key 指定（.env 中从哪个变量解析出的，决定平台）
    if config_key and config_key in KEY_TO_PROVIDER:
        return KEY_TO_PROVIDER[config_key]
    if config_key in ("CHAT_MODEL", "CODE_MODEL", "REASONING_MODEL"):
        p = (os.getenv("LLM_PROVIDER") or "deepseek").strip().lower()
        if p in ("deepseek", "bailian", "theturbogateway"):
            return p
    # 兜底：按模型名推断
    provider, _ = ModelRegistry.parse_model_name(model_name)
    return provider


@router.get("/settings/model-availability-audit/models")
async def get_models():
    """
    返回 .env 中解析出的模型列表，按提供商分组。
    - models: 每项含 key, label, model, source, provider
    - unique_models: 去重后的模型名列表，用于探测
    - models_by_provider: 按提供商分组的模型 { provider: [models...] }
    """
    models, unique_models = parse_env_models()
    for m in models:
        m["provider"] = _get_provider(m["model"], m.get("key"))
    # 按提供商分组，且按模型名去重，合并同一模型的多个来源
    by_provider = defaultdict(dict)  # provider -> { model: { keys, sources } }
    for m in models:
        p, name = m["provider"], m["model"]
        if name not in by_provider[p]:
            by_provider[p][name] = {
                "model": name,
                "provider": p,
                "keys": [],
                "sources": set(),
            }
        entry = by_provider[p][name]
        if m.get("key"):
            entry["keys"].append(m["key"])
        entry["sources"].add(m["source"])
    # 转为列表，配置项合并显示；百炼平台按分类分组
    models_by_provider = {}
    bailian_category_order = []  # 用于前端展示顺序

    for p in PROVIDER_ORDER + [k for k in by_provider if k not in PROVIDER_ORDER]:
        if p not in by_provider:
            continue
        items = []
        for name, entry in by_provider[p].items():
            keys = list(dict.fromkeys(entry["keys"]))  # 去重保序
            item = {
                "model": name,
                "provider": p,
                "key": keys[0] if keys else None,
                "keys": keys,
                "source": "配置" if "config" in entry["sources"] else "注释",
            }
            if p == "bailian":
                item["category"] = _get_bailian_category(name)
                if item["category"] not in bailian_category_order:
                    bailian_category_order.append(item["category"])
            items.append(item)
        models_by_provider[p] = items

    return {
        "success": True,
        "models": models,
        "unique_models": unique_models,
        "models_by_provider": models_by_provider,
        "provider_labels": PROVIDER_LABELS,
        "bailian_category_order": bailian_category_order,
    }


@router.post("/settings/model-availability-audit/probe")
async def post_probe(body: Optional[ProbeRequest] = Body(default=None)):
    """
    对指定或全部模型发起探测。
    - 不传或 models 为空：使用 GET /models 的 unique_models
    - 传 models：按指定列表探测
    """
    models_to_probe = None
    if body and body.models:
        models_to_probe = body.models

    if not models_to_probe:
        _, unique_models = parse_env_models()
        models_to_probe = unique_models

    if not models_to_probe:
        return {"success": True, "results": []}

    models_list, _ = parse_env_models()
    models_with_key = {}
    for x in models_list:
        if x.get("key") and x["model"] not in models_with_key:
            models_with_key[x["model"]] = x["key"]
    results = []
    for model in models_to_probe:
        r = await probe_model(model)
        results.append({
            "model": model,
            "provider": _get_provider(model, models_with_key.get(model)),
            **r,
        })

    return {"success": True, "results": results}
