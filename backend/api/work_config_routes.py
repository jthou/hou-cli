"""工作配置 API：读取与保存 rules、work_context、terms"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from backend.core.agent.work_config import (
    load_work_config,
    save_work_config,
    get_config_path,
    WorkConfig,
)

router = APIRouter()


class WorkConfigSchema(BaseModel):
    rules: List[str] = []
    work_context: str = ""
    terms: List[str] = []
    extra: dict = {}


def _config_to_schema(config: WorkConfig) -> WorkConfigSchema:
    return WorkConfigSchema(
        rules=list(config.rules),
        work_context=config.work_context,
        terms=list(config.terms),
        extra=dict(config.extra),
    )


def _schema_to_config(schema: WorkConfigSchema) -> WorkConfig:
    return WorkConfig(
        rules=list(schema.rules),
        work_context=schema.work_context,
        terms=list(schema.terms),
        extra=dict(schema.extra),
    )


@router.get("/settings/work-config")
async def get_work_config():
    """返回当前工作配置（rules、work_context、terms）"""
    try:
        config = load_work_config()
        return {
            "success": True,
            "config_path": str(get_config_path()),
            "config": _config_to_schema(config).model_dump(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings/work-config")
async def put_work_config(body: WorkConfigSchema):
    """保存工作配置"""
    try:
        config = _schema_to_config(body)
        path = save_work_config(config)
        return {
            "success": True,
            "config_path": str(path),
            "config": _config_to_schema(config).model_dump(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
