"""写作画像 API：读取与保存 preferences、style_notes、sample_articles"""

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
