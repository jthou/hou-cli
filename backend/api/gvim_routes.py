"""本机 gvim：供浏览器扩展等从 127.0.0.1 调用，打开 MediaWiki 页面（走 GvimService API 拉取）。"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gvim", tags=["gvim"])


def _client_is_localhost(request: Request) -> bool:
    c = request.client
    if not c:
        return True
    host = (c.host or "").strip().lower()
    if host in ("127.0.0.1", "localhost", "::1", "testclient"):
        return True
    return host.startswith("::ffff:127.0.0.1")


class OpenMediaWikiBody(BaseModel):
    page_title: str = Field(..., min_length=1, max_length=800, description="MediaWiki 页面标题，可含子页面斜杠")


@router.post("/open-mediawiki-page")
async def open_mediawiki_in_gvim(request: Request, body: OpenMediaWikiBody) -> Dict[str, Any]:
    if not _client_is_localhost(request):
        raise HTTPException(status_code=403, detail="仅允许本机 127.0.0.1 调用")
    title = body.page_title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="page_title 不能为空")
    try:
        from backend.services.gvim_service import GvimService, GvimServiceError

        svc = GvimService()
        out = svc.open_mediawiki_page(title)
        return {"success": True, **out}
    except GvimServiceError as e:
        logger.warning("gvim open mediawiki: %s", e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("gvim open mediawiki failed")
        raise HTTPException(status_code=500, detail=str(e)) from e
