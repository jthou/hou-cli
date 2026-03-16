"""写作画像 API：读取与保存 preferences、style_notes、sample_articles；接受记录抽样与打分"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from backend.core.agent.writing_profile import (
    load_writing_profile,
    save_writing_profile,
    get_profile_path,
    WritingProfile,
    SampleArticle,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# 接受记录与打分（时间：2025-03-15；理由：从接受的修改中抽样章节请用户打分，据此改进写作画像）
# ---------------------------------------------------------------------------

@router.get("/settings/writing-profile/acceptance-records")
async def list_acceptance_records_for_rating(limit: int = 20):
    """获取可打分的接受记录列表（用于抽样）。"""
    try:
        from backend.services.writing_acceptance import list_records_for_rating
        records = list_records_for_rating(limit=limit)
        return {"success": True, "records": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings/writing-profile/acceptance-records/{record_id}/sections")
async def get_sections_for_rating(record_id: int, max_sections: int = 5):
    """获取某条记录的章节列表，供用户打分。"""
    try:
        from backend.services.writing_acceptance import get_sections_for_rating
        sections = get_sections_for_rating(record_id, max_sections=max_sections)
        return {"success": True, "record_id": record_id, "sections": sections}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class RateSectionRequest(BaseModel):
    record_id: int
    section_index: int
    score: int  # 1-5
    section_text: Optional[str] = None


@router.post("/settings/writing-profile/rate-section")
async def submit_section_rating(body: RateSectionRequest):
    """提交章节打分。"""
    try:
        from backend.services.writing_acceptance import submit_section_rating
        ok = submit_section_rating(
            record_id=body.record_id,
            section_index=body.section_index,
            score=body.score,
            section_text=body.section_text,
        )
        return {"success": ok}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class LearnFromRatingsRequest(BaseModel):
    min_score: int = 4
    limit: int = 10


@router.post("/settings/writing-profile/learn-from-ratings")
async def learn_from_ratings(body: LearnFromRatingsRequest):
    """根据高分章节更新写作画像。"""
    try:
        from backend.services.writing_acceptance import get_high_rated_content
        from backend.core.agent.writing_profile import load_writing_profile, save_writing_profile

        contents = get_high_rated_content(min_score=body.min_score, limit=body.limit)
        if not contents:
            return {"success": True, "message": "暂无高分章节可学习", "updated": False}

        from backend.services.llm.llm_service import LLMService
        llm = LLMService()
        prompt = f"""
请分析以下用户打高分的文章章节，提炼其写作偏好与表述习惯。输出 JSON：
{{"preferences": ["偏好1", "偏好2", ...], "style_notes": "表述习惯描述（200字内）"}}

高分章节：
{chr(10).join(f"--- 章节 {i+1} ---{chr(10)}{c[:800]}" for i, c in enumerate(contents))}
"""
        import json
        import re
        resp = await llm.chat([{"role": "user", "content": prompt}])
        text = (resp or "").strip()
        # 兼容 ```json ... ``` 包裹
        if "```" in text:
            m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
        else:
            m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return {"success": False, "error": "LLM 未返回有效 JSON"}

        json_str = m.group(1) if m.lastindex and m.lastindex >= 1 else m.group()
        parsed = json.loads(json_str)
        prefs = parsed.get("preferences") or []
        style_notes = parsed.get("style_notes") or ""

        profile = load_writing_profile()
        existing_prefs = set(profile.preferences)
        added = 0
        for p in prefs:
            if isinstance(p, str) and p.strip() and p.strip() not in existing_prefs:
                profile.preferences.append(p.strip())
                existing_prefs.add(p.strip())
                added += 1
        if style_notes and style_notes.strip():
            profile.style_notes = (profile.style_notes or "").strip() + "\n\n" + style_notes.strip()
        save_writing_profile(profile)
        return {"success": True, "updated": True, "preferences_added": added}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SampleArticleSchema(BaseModel):
    title: str
    content: Optional[str] = None
    path: Optional[str] = None


class WritingProfileSchema(BaseModel):
    preferences: List[str] = []
    style_notes: str = ""
    sample_articles: List[SampleArticleSchema] = []
    extra: dict = {}


def _profile_to_schema(profile: WritingProfile) -> WritingProfileSchema:
    samples = [
        SampleArticleSchema(title=s.title, content=s.content, path=s.path)
        for s in profile.sample_articles
    ]
    return WritingProfileSchema(
        preferences=list(profile.preferences),
        style_notes=profile.style_notes,
        sample_articles=samples,
        extra=dict(profile.extra),
    )


def _schema_to_profile(schema: WritingProfileSchema) -> WritingProfile:
    samples = [
        SampleArticle(title=s.title, content=s.content, path=s.path)
        for s in schema.sample_articles
    ]
    return WritingProfile(
        preferences=list(schema.preferences),
        style_notes=schema.style_notes,
        sample_articles=samples,
        extra=dict(schema.extra),
    )


@router.get("/settings/writing-profile")
async def get_writing_profile():
    """返回当前写作画像（preferences、style_notes、sample_articles）"""
    try:
        profile = load_writing_profile()
        return {
            "success": True,
            "profile_path": str(get_profile_path()),
            "profile": _profile_to_schema(profile).model_dump(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings/writing-profile")
async def put_writing_profile(body: WritingProfileSchema):
    """保存写作画像"""
    try:
        profile = _schema_to_profile(body)
        path = save_writing_profile(profile)
        return {
            "success": True,
            "profile_path": str(path),
            "profile": _profile_to_schema(profile).model_dump(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
