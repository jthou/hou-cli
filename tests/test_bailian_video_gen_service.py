# 时间：2026-04-05；理由：文生视频 MCP 依赖 task_id 解析；方法：纯字典单测
from __future__ import annotations

import pytest

from backend.services.llm.bailian_video_gen_service import _task_id_from_submit, _video_url_from_task


def test_task_id_from_submit():
    assert _task_id_from_submit({"output": {"task_id": "abc-123"}}) == "abc-123"


def test_task_id_from_submit_missing():
    with pytest.raises(RuntimeError, match="task_id"):
        _task_id_from_submit({"output": {}})


def test_video_url_from_task():
    assert _video_url_from_task(
        {"output": {"task_status": "SUCCEEDED", "video_url": "https://x/v.mp4"}}
    ) == ("SUCCEEDED", "https://x/v.mp4")
