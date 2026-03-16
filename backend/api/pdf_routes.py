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


def _extract_pdf_text(pdf_path: Path, page_numbers: list[int], layout: bool, columns: bool) -> str:
    """提取 PDF 文本。layout=True 用 pdfminer；columns=True 时按分栏优化 LAParams。"""
    from backend.utils.pdf_extract import extract_text_from_pdf
    return extract_text_from_pdf(pdf_path, page_numbers, use_layout=layout, fix_doubled=False, columns=columns)


@router.get("/pdf/page-text")
async def get_pdf_page_text(
    file_path: str = Query(
        ...,
        description="服务器上的 PDF 绝对路径（如上传、扩展获取后返回的 path）",
    ),
    page: int = Query(1, ge=1, description="要提取的页码，从 1 开始"),
    layout: bool = Query(True, description="保持原文缩进与排版（默认 True，使用 pdfminer）"),
):
    """读取指定 PDF 的某一页文本内容。layout=True 时用 pdfminer 保持缩进排版。"""
    try:
        pdf_path = _resolve_local_pdf(file_path)
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail=f"PDF 文件不存在: {file_path}")
        if pdf_path.suffix.lower() != ".pdf":
            raise HTTPException(status_code=400, detail="文件不是 PDF 格式")

        page_count = 0
        try:
            import pdfplumber  # type: ignore
            with pdfplumber.open(str(pdf_path)) as pdf:
                page_count = len(pdf.pages)
        except ImportError:
            pass
        if page_count == 0:
            try:
                from pdfminer.high_level import extract_pages
                page_count = sum(1 for _ in extract_pages(str(pdf_path)))
            except Exception:
                raise HTTPException(status_code=500, detail="无法读取 PDF 页数")

        if page < 1 or page > page_count:
            raise HTTPException(status_code=400, detail=f"页码超出范围: 1–{page_count}")

        page_numbers = [page - 1]
        text = _extract_pdf_text(pdf_path, page_numbers, layout, columns)

        return {
            "success": True,
            "file_path": str(pdf_path),
            "page": page,
            "page_count": page_count,
            "text": text or "",
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"get_pdf_page_text failed: {e}", level="error")
        raise HTTPException(status_code=500, detail=f"读取 PDF 失败: {e}")


def _parse_pages_spec(spec: str, page_count: int) -> list[int]:
    """解析页码规格：支持 1-8、1,3,5、1-3,5,7-9 等格式。返回 0-based 页码列表。"""
    if not spec or not spec.strip():
        return []
    seen: set[int] = set()
    for part in spec.replace("，", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            try:
                lo = max(1, int(a.strip()))
                hi = min(page_count, int(b.strip()))
                if lo <= hi:
                    for p in range(lo, hi + 1):
                        seen.add(p - 1)
            except ValueError:
                continue
        else:
            try:
                p = int(part.strip())
                if 1 <= p <= page_count:
                    seen.add(p - 1)
            except ValueError:
                continue
    return sorted(seen)


@router.get("/pdf/page-range-text")
async def get_pdf_page_range_text(
    file_path: str = Query(
        ...,
        description="服务器上的 PDF 绝对路径",
    ),
    page_from: int = Query(1, ge=1, description="起始页（含），pages 未传时使用"),
    page_to: int = Query(1, ge=1, description="结束页（含），pages 未传时使用"),
    pages: Optional[str] = Query(
        None,
        description="跳着抓取：如 1,3,5 或 1-3,5,7-9。传此参数时忽略 page_from/page_to",
    ),
    layout: bool = Query(True, description="保持原文缩进与排版"),
    columns: bool = Query(False, description="按分栏提取（改善多栏 PDF 阅读顺序，需 layout=True）"),
):
    """提取多页文本（含首尾），返回合并文本及每页明细。columns=True 时按分栏优化。"""
    try:
        pdf_path = _resolve_local_pdf(file_path)
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail=f"PDF 文件不存在: {file_path}")
        if pdf_path.suffix.lower() != ".pdf":
            raise HTTPException(status_code=400, detail="文件不是 PDF 格式")

        page_count = 0
        try:
            import pdfplumber  # type: ignore
            with pdfplumber.open(str(pdf_path)) as pdf:
                page_count = len(pdf.pages)
        except ImportError:
            try:
                from pdfminer.high_level import extract_pages
                page_count = sum(1 for _ in extract_pages(str(pdf_path)))
            except Exception:
                pass
        if page_count == 0:
            raise HTTPException(status_code=500, detail="无法读取 PDF 页数")

        if pages and pages.strip():
            page_numbers = _parse_pages_spec(pages, page_count)
            if not page_numbers:
                raise HTTPException(status_code=400, detail="pages 格式无效，示例：1-8 或 1,3,5 或 1-3,5,7-9")
        else:
            if page_from > page_to:
                page_from, page_to = page_to, page_from
            if page_to > page_count:
                page_to = page_count
            if page_from < 1:
                page_from = 1
            page_numbers = list(range(page_from - 1, page_to))

        pages_detail = []
        for pn in page_numbers:
            pg_num = pn + 1
            pg_text = _extract_pdf_text(pdf_path, [pn], layout, columns)
            pages_detail.append({"page": pg_num, "text": pg_text or ""})
        text = "\n\n".join(p["text"] for p in pages_detail if p["text"])
        pg_nums = [p["page"] for p in pages_detail]
        resp_page_from = min(pg_nums) if pg_nums else page_from
        resp_page_to = max(pg_nums) if pg_nums else page_to

        return {
            "success": True,
            "file_path": str(pdf_path),
            "page_from": resp_page_from,
            "page_to": resp_page_to,
            "page_count": page_count,
            "text": text,
            "pages": pages_detail,
        }
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"get_pdf_page_range_text failed: {e}", level="error")
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
        pdf_path = _resolve_local_pdf(file_path)
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
