"""PDF 阅读/解析相关路由"""

from pathlib import Path
from typing import Optional, Tuple

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from shared.debug_utils import debug_log

router = APIRouter()


def _download_pdf_if_url(file_path: str) -> Tuple[Path, bool]:
    """若 file_path 为 http/https URL，则下载到临时文件并返回 (路径, True)，否则按本地路径解析并返回 (路径, False)。"""
    if file_path.startswith("http://") or file_path.startswith("https://"):
        try:
            # 复用 pdf_to_wiki 的下载逻辑和大小限制
            from backend.infrastructure.execution.task_handlers import _download_pdf_to_temp
        except Exception as e:  # pragma: no cover - 极端情况
            raise HTTPException(
                status_code=500,
                detail=f"当前后端未启用 PDF 下载能力: {e}",
            )

        try:
            temp_path_str, _size = _download_pdf_to_temp(file_path)
        except ValueError as ve:
            # 大小超限等业务性错误
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"下载 PDF 失败: {e}")

        temp_path = Path(temp_path_str).resolve()
        return temp_path, True

    # 本地文件路径
    pdf_path = Path(file_path).expanduser().resolve()
    return pdf_path, False


class PdfResolveRequest(BaseModel):
  source: str


@router.post("/pdf/resolve")
async def resolve_pdf_source(payload: PdfResolveRequest):
    """将 URL 或本地路径解析为可用的 PDF 本地文件路径。

    - 对于 http/https URL，会下载到临时文件并返回该路径
    - 对于本地路径，会返回规范化后的绝对路径
    """
    src = (payload.source or "").strip()
    if not src:
        raise HTTPException(status_code=400, detail="source 不能为空")

    pdf_path, downloaded = _download_pdf_if_url(src)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"PDF 文件不存在: {src}")
    if pdf_path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="文件不是 PDF 格式")

    return {
        "success": True,
        "file_path": str(pdf_path),
        "downloaded": downloaded,
        "original": src,
    }


@router.get("/pdf/page-text")
async def get_pdf_page_text(
    file_path: str = Query(
        ...,
        description="服务器上的 PDF 绝对路径（如上传后返回的 path），或 http(s) 在线 PDF URL",
    ),
    page: int = Query(1, ge=1, description="要提取的页码，从 1 开始"),
):
    """读取指定 PDF 的某一页文本内容。

    - 支持本地绝对路径（如 /task-queue/upload-input-file 返回的 path）
    - 也支持 http/https 在线 PDF，会自动下载到临时文件后再解析
    """
    temp_downloaded = False
    try:
        pdf_path, temp_downloaded = _download_pdf_if_url(file_path)
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail=f"PDF 文件不存在: {file_path}")
        if pdf_path.suffix.lower() != ".pdf":
            raise HTTPException(status_code=400, detail="文件不是 PDF 格式")

        try:
            import pdfplumber  # type: ignore
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="pdfplumber 未安装，请确认后端已安装依赖: pip install pdfplumber",
            )

        text: Optional[str] = ""
        page_count = 0
        with pdfplumber.open(str(pdf_path)) as pdf:
            page_count = len(pdf.pages)
            if page < 1 or page > page_count:
                raise HTTPException(
                    status_code=400,
                    detail=f"页码超出范围: 1–{page_count}",
                )
            pg = pdf.pages[page - 1]
            text = pg.extract_text() or ""

        return {
            "success": True,
            "file_path": str(pdf_path),
            "page": page,
            "page_count": page_count,
            "text": text,
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"get_pdf_page_text failed: {e}", level="error")
        raise HTTPException(status_code=500, detail=f"读取 PDF 失败: {e}")
    finally:
        # 对于在线 PDF，解析完后删除临时文件
        if temp_downloaded:
            try:
                pdf_path.unlink(missing_ok=True)  # type: ignore[name-defined]
            except Exception:
                debug_log("删除临时 PDF 文件失败", level="warning")


@router.get("/pdf/view")
async def view_pdf(
    file_path: str = Query(
        ...,
        description="服务器上的 PDF 绝对路径（如上传后返回的 path）或本机路径（需在用户主目录下）",
    ),
):
    """直接返回 PDF 文件本身，供浏览器原生 PDF 查看器使用。仅支持本地文件路径。"""
    try:
        pdf_path = Path(file_path).expanduser().resolve()
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail=f"PDF 文件不存在: {file_path}")
        if pdf_path.suffix.lower() != ".pdf":
            raise HTTPException(status_code=400, detail="文件不是 PDF 格式")

        return FileResponse(str(pdf_path), media_type="application/pdf")
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"view_pdf failed: {e}", level="error")
        raise HTTPException(status_code=500, detail=f"读取 PDF 失败: {e}")
