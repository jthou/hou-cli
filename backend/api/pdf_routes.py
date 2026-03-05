"""PDF 阅读/解析相关路由"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from shared.debug_utils import debug_log

router = APIRouter()


def _resolve_local_pdf(file_path: str) -> Path:
    """解析本地 PDF 路径。在线 PDF 统一由扩展获取，不再由后端下载。"""
    pdf_path = Path(file_path).expanduser().resolve()
    return pdf_path


class PdfResolveRequest(BaseModel):
    source: str


class PdfUploadFromExtensionRequest(BaseModel):
    """扩展获取的 PDF base64 数据"""
    base64: str
    original_url: Optional[str] = None


def _cleanup_old_pdf_temp_files(max_age_hours: int = 24):
    """清理超过指定小时的 PDF 临时文件"""
    import tempfile as _tempfile
    import time

    temp_dir = Path(_tempfile.gettempdir()) / "hou-cli-pdf"
    if not temp_dir.exists():
        return
    cutoff = time.time() - max_age_hours * 3600
    for f in temp_dir.glob("*.pdf"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink(missing_ok=True)
        except Exception:
            pass


@router.post("/pdf/upload-from-extension")
async def upload_pdf_from_extension(payload: PdfUploadFromExtensionRequest):
    """接收扩展获取的 PDF（base64），保存到临时文件并返回路径。统一方案：在线 PDF 仅通过扩展获取。"""
    import base64
    import tempfile

    temp_dir = Path(tempfile.gettempdir()) / "hou-cli-pdf"
    temp_dir.mkdir(parents=True, exist_ok=True)
    _cleanup_old_pdf_temp_files()

    b64 = (payload.base64 or "").strip()
    if not b64:
        raise HTTPException(status_code=400, detail="base64 不能为空")

    try:
        raw = base64.b64decode(b64, validate=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"base64 解码失败: {e}")

    max_bytes = 50 * 1024 * 1024  # 50MB
    if len(raw) > max_bytes:
        raise HTTPException(status_code=400, detail=f"PDF 超过 {max_bytes // (1024*1024)} MB 限制")

    if len(raw) < 4 or raw[:4] != b"%PDF":
        raise HTTPException(status_code=400, detail="不是有效的 PDF 文件")

    fd, path = tempfile.mkstemp(suffix=".pdf", dir=str(temp_dir))
    try:
        import os
        os.write(fd, raw)
        os.close(fd)
    except Exception:
        try:
            os.close(fd)
        except Exception:
            pass
        Path(path).unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="保存临时文件失败")

    return {
        "success": True,
        "file_path": path,
        "original_url": payload.original_url,
    }


@router.post("/pdf/resolve")
async def resolve_pdf_source(payload: PdfResolveRequest):
    """将本地路径解析为可用的 PDF 绝对路径。在线 PDF 统一由扩展获取。"""
    src = (payload.source or "").strip()
    if not src:
        raise HTTPException(status_code=400, detail="source 不能为空")
    if src.startswith("http://") or src.startswith("https://"):
        raise HTTPException(
            status_code=400,
            detail="在线 PDF 请使用扩展加载（需安装 Hou CLI 扩展）",
        )

    pdf_path = _resolve_local_pdf(src)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"PDF 文件不存在: {src}")
    if pdf_path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="文件不是 PDF 格式")

    return {
        "success": True,
        "file_path": str(pdf_path),
        "downloaded": False,
        "original": src,
    }


@router.get("/pdf/page-text")
async def get_pdf_page_text(
    file_path: str = Query(
        ...,
        description="服务器上的 PDF 绝对路径（如上传、扩展获取后返回的 path）",
    ),
    page: int = Query(1, ge=1, description="要提取的页码，从 1 开始"),
):
    """读取指定 PDF 的某一页文本内容。仅支持本地路径（扩展获取的 PDF 会先保存到临时文件）。"""
    try:
        pdf_path = _resolve_local_pdf(file_path)
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
