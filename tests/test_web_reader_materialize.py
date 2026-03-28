"""网页阅读：materialize-inline-images 落盘与静态路由（轻量 FastAPI，不导入 backend.main）"""
# 时间：2026-03-14；理由：微信配图防盗链；方法：小图 base64 写入 tmp 后 GET 可读

import base64

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def web_reader_client(tmp_path, monkeypatch):
    from backend.api import web_reader_routes

    monkeypatch.setattr(web_reader_routes, "_INLINE_IMG_DIR", tmp_path)
    app = FastAPI()
    app.include_router(web_reader_routes.router)
    return TestClient(app)


def test_materialize_inline_images_and_serve(web_reader_client: TestClient):
    one_px_png = base64.b64encode(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
    ).decode("ascii")
    data_url = f"data:image/png;base64,{one_px_png}"
    r = web_reader_client.post(
        "/web-reader/materialize-inline-images",
        json={
            "images": [
                {"original_url": "https://mmbiz.qpic.cn/fake/1.png", "data_url": data_url},
            ]
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True
    m = body.get("mapping") or {}
    assert len(m) == 1
    path = list(m.values())[0]
    assert path.startswith("/api/web-reader/inline-static/")
    fname = path.split("/")[-1]

    r2 = web_reader_client.get(f"/web-reader/inline-static/{fname}")
    assert r2.status_code == 200
    assert r2.content[:8] == b"\x89PNG\r\n\x1a\n"

    r404 = web_reader_client.get("/web-reader/inline-static/../../../etc/passwd")
    assert r404.status_code == 404


def test_fetch_weread_inline_image_rejects_non_weread_host(web_reader_client: TestClient):
    r = web_reader_client.post(
        "/web-reader/fetch-weread-inline-image",
        json={
            "original_url": "https://evil.example.com/x.jpg",
            "page_url": "https://weread.qq.com/web/reader/xxx",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is False


def test_fetch_weread_inline_image_ok_with_mock_httpx(web_reader_client: TestClient, monkeypatch):
    from backend.api import web_reader_routes

    one_px_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    class _MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, headers=None):
            req = httpx.Request("GET", url)
            return httpx.Response(
                200,
                request=req,
                content=one_px_png,
                headers={"content-type": "image/png"},
            )

    monkeypatch.setattr(web_reader_routes.httpx, "AsyncClient", _MockAsyncClient)

    r = web_reader_client.post(
        "/web-reader/fetch-weread-inline-image",
        json={
            "original_url": "https://res.weread.qq.com/wrepub/epub_test",
            "page_url": "https://weread.qq.com/web/reader/foo",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True
    m = body.get("mapping") or {}
    assert len(m) == 1
    path = list(m.values())[0]
    assert path.startswith("/api/web-reader/inline-static/")
    fname = path.split("/")[-1]

    r2 = web_reader_client.get(f"/web-reader/inline-static/{fname}")
    assert r2.status_code == 200
    assert r2.content[:8] == b"\x89PNG\r\n\x1a\n"
