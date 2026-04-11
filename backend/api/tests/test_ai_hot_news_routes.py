"""POST /api/ai-hot-news/run：直跑不入队。"""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_ai_hot_news_run_success(client):
    fake = {
        "status": "success",
        "summary": "测试标题",
        "result": {
            "digest": {
                "schema_version": "1",
                "meta": {"title": "测试标题"},
                "markdown": "# 测试\n",
                "source_refs": [],
                "search_log": [],
            }
        },
    }
    with patch(
        "backend.api.ai_hot_news_routes.run_ai_hot_news_digest",
        new_callable=AsyncMock,
        return_value=fake,
    ):
        r = client.post("/api/ai-hot-news/run", json={"metadata": {}})
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["result"]["status"] == "success"
    assert "digest" in data["result"]["result"]


def test_ai_hot_news_run_propagates_non_success(client):
    fake = {"status": "error", "summary": "bad", "error": {"code": "X", "message": "m"}}
    with patch(
        "backend.api.ai_hot_news_routes.run_ai_hot_news_digest",
        new_callable=AsyncMock,
        return_value=fake,
    ):
        r = client.post("/api/ai-hot-news/run", json={"metadata": {}})
    assert r.status_code == 500
