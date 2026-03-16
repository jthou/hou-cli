"""写作建议 API：根据光标位置上下文，返回 1–5 条写作建议"""
import json
import logging
import re
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/writing-suggestions", tags=["writing-suggestions"])


class WritingSuggestionsRequest(BaseModel):
    """写作建议请求"""
    text_before: str  # 光标前文本，建议 200–500 字
    text_after: str = ""  # 光标后文本，建议 50–100 字
    format: str = "markdown"  # markdown | wikitext
    max_suggestions: int = 5


class WritingSuggestionsResponse(BaseModel):
    """写作建议响应"""
    suggestions: List[str]


async def _call_writing_suggestions_llm(
    text_before: str,
    text_after: str,
    fmt: str,
    max_suggestions: int,
) -> List[str]:
    """调用 LLM 生成写作建议"""
    from backend.services.llm.llm_service import LLMService

    from backend.core.agent.system_prompt_templates import WRITING_SUGGESTIONS_PROMPT_TEMPLATE

    prompt = WRITING_SUGGESTIONS_PROMPT_TEMPLATE.format(
        text_before=(text_before or "")[-500:] if text_before else "",
        text_after=(text_after or "")[:100] if text_after else "",
        format=fmt,
    )
    llm = LLMService(temperature=0.4, max_tokens=200)
    response = await llm.chat(
        messages=[{"role": "user", "content": prompt}],
        audit_meta={"source": "writing_suggestions"},
    )
    if not response or not isinstance(response, str):
        return []
    return parse_suggestions_from_llm_response(response, max_suggestions)


def parse_suggestions_from_llm_response(response: str, max_suggestions: int = 5) -> List[str]:
    """
    从 LLM 响应文本中解析 suggestions 列表。
    支持 JSON 格式及回退按行解析。供单元测试复用。
    """
    text = (response or "").strip()
    # 尝试提取 {"suggestions": [...]} 结构
    for pattern in [
        r'\{[^{}]*"suggestions"\s*:\s*\[[^\]]*\][^{}]*\}',
        r'\{[^{}]*"suggestions"\s*:\s*\[.*?\]\s*\}',
    ]:
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group())
                suggestions = data.get("suggestions") or []
                if isinstance(suggestions, list):
                    return [str(s).strip() for s in suggestions[:max_suggestions] if s]
            except json.JSONDecodeError:
                pass
    # 回退：按行解析，跳过 JSON 和代码块
    lines = [
        ln.strip()
        for ln in text.split("\n")
        if ln.strip() and not ln.strip().startswith("{") and not ln.strip().startswith("```")
    ]
    return lines[:max_suggestions] if lines else []


@router.post("", response_model=WritingSuggestionsResponse)
async def get_writing_suggestions(req: WritingSuggestionsRequest):
    """
    根据光标前后文本，返回 1–5 条写作建议。
    触发方式：编辑器中按 Ctrl+Space。
    """
    text_before = (req.text_before or "").strip()
    if not text_before:
        return WritingSuggestionsResponse(suggestions=[])

    fmt = (req.format or "markdown").lower()
    if fmt not in ("markdown", "wikitext"):
        fmt = "markdown"
    max_suggestions = max(1, min(5, req.max_suggestions or 5))

    try:
        suggestions = await _call_writing_suggestions_llm(
            text_before=text_before,
            text_after=(req.text_after or "").strip(),
            fmt=fmt,
            max_suggestions=max_suggestions,
        )
        return WritingSuggestionsResponse(suggestions=suggestions)
    except Exception as e:
        logger.exception("写作建议生成失败: %s", e)
        raise HTTPException(status_code=500, detail=f"写作建议生成失败: {e}")
