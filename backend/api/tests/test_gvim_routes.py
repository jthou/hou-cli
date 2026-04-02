"""gvim API：本机打开 MediaWiki（扩展调用）。"""

from unittest.mock import MagicMock, patch


def test_open_mediawiki_gvim_ok(client):
    inst = MagicMock()
    inst.open_mediawiki_page = MagicMock(
        return_value={
            "success": True,
            "message": "已打开",
            "page_title": "大模型微调/LLaMA-Factory_QuickStart",
            "file_path": "/tmp/x.mediawiki",
            "url": "http://example/wiki/x",
        }
    )
    with patch("backend.services.gvim_service.GvimService", return_value=inst):
        r = client.post(
            "/api/gvim/open-mediawiki-page",
            json={"page_title": "大模型微调/LLaMA-Factory_QuickStart"},
        )
    assert r.status_code == 200
    data = r.json()
    assert data.get("success") is True
    assert "LLaMA" in (data.get("page_title") or "")
    inst.open_mediawiki_page.assert_called_once_with("大模型微调/LLaMA-Factory_QuickStart")


def test_open_mediawiki_gvim_empty_title(client):
    r = client.post("/api/gvim/open-mediawiki-page", json={"page_title": ""})
    assert r.status_code == 422
