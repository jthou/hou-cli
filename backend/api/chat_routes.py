"""聊天相关路由"""
import subprocess
import tempfile
import traceback
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from backend.core.agent.orchestrator import Orchestrator
from backend.api.stream_sender import SSEFormatter
from backend.core.article_patch import apply_unified_diff
from shared.debug_utils import debug_log

router = APIRouter()

# 延迟创建 orchestrator
_orchestrator = None

def get_orchestrator():
    """获取 Orchestrator 实例（单例模式）"""
    global _orchestrator
    if _orchestrator is None:
        try:
            _orchestrator = Orchestrator()
        except Exception as e:
            debug_log(
                f"Failed to initialize Orchestrator: {str(e)}",
                level="error"
            )
            raise
    return _orchestrator

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None  # 会话 ID（可选）
    current_article: Optional[str] = None  # 写文章时右侧草稿，会注入对话上下文并持久化
    context_type: Optional[str] = None  # 建新会话时的类型，如 article_writing；无 session_id 时生效
    model: Optional[str] = None  # 用户指定模型：chat/code/reasoning 或具体模型名；不传则智能选择
    regenerate_from_message_id: Optional[str] = None  # 重新回答：指定用户消息 ID，删除其后内容并重新生成

@router.post("/chat")
async def chat(request: ChatRequest):
    """处理聊天请求（非流式）"""
    try:
        debug_log(
            "收到聊天请求",
            data={
                "message_preview": request.message[:50] if request.message else None,
                "session_id": request.session_id,
                "has_current_article": request.current_article is not None,
            }
        )
        orchestrator = get_orchestrator()
        context = {}
        if request.session_id:
            context["session_id"] = request.session_id
        if request.context_type:
            context["context_type"] = request.context_type
        if request.model and request.model.strip():
            context["model"] = request.model.strip()
        # 写文章：保存右侧草稿，供本次及后续轮次注入上下文
        if request.session_id and request.current_article is not None:
            orchestrator.context_manager.set_current_article(
                request.session_id, request.current_article
            )

        debug_log("开始处理请求...")
        response = await orchestrator.process(request.message, context=context)
        debug_log(
            "请求处理成功",
            data={"response_length": len(response) if response else 0}
        )

        # 文章更新由用户点击「接受修改」控制，此处不再自动写入

        # 返回响应与当前文章（右侧预览用）
        result = {
            "response": response,
            "status": "success",
        }
        if request.session_id:
            article = orchestrator.context_manager.get_current_article(
                request.session_id
            )
            if article is not None:
                result["article"] = article
        return result
    except Exception as e:
        error_trace = traceback.format_exc()
        debug_log(
            f"Chat request failed: {str(e)}",
            level="error",
            data={"error_trace": error_trace}
        )
        # 返回 200 状态码，但在响应中包含错误信息
        # 这样前端可以正常处理，而不是收到 502
        return {
            "response": None,
            "status": "error",
            "error": str(e)
        }

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """处理聊天请求（流式 SSE）"""
    import traceback
    from fastapi.responses import StreamingResponse
    
    debug_log(
        "chat_stream路由被调用",
        data={
            "message_preview": request.message[:50] if request.message else None,
            "session_id": request.session_id
        }
    )
    
    async def generate():
        try:
            orchestrator = get_orchestrator()
            context = {}
            if request.session_id:
                context["session_id"] = request.session_id
            if request.context_type:
                context["context_type"] = request.context_type
            if request.model and request.model.strip():
                context["model"] = request.model.strip()
            if request.regenerate_from_message_id:
                context["regenerate_from_message_id"] = request.regenerate_from_message_id
            # 写文章：保存右侧草稿供流式分支注入上下文（与 POST /chat 一致）
            if request.session_id and request.current_article is not None:
                orchestrator.context_manager.set_current_article(
                    request.session_id, request.current_article
                )
            
            debug_log("开始流式处理请求...")
            
            formatter = SSEFormatter()
            async for chunk in orchestrator.stream_process(request.message, context=context):
                if chunk:
                    yield formatter.format_chunk(chunk, "streaming")
            
            yield formatter.format_done()
            debug_log("流式响应完成")
        except Exception as e:
            error_trace = traceback.format_exc()
            debug_log(
                f"Stream chat request failed: {str(e)}",
                level="error",
                data={"error_trace": error_trace}
            )
            # 发送错误信息
            formatter = SSEFormatter()
            yield formatter.format_error(str(e))
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
            "Transfer-Encoding": "chunked"
        }
    )


@router.get("/chat/article")
async def get_chat_article(session_id: Optional[str] = None):
    """获取写文章会话的当前文章草稿（右侧预览），用于恢复页面时加载。"""
    if not session_id:
        return {"article": None, "status": "success"}
    try:
        orchestrator = get_orchestrator()
        article = orchestrator.context_manager.get_current_article(session_id)
        return {"article": article, "status": "success"}
    except Exception as e:
        debug_log(f"get_chat_article failed: {e}", level="error")
        return {"article": None, "status": "error", "error": str(e)}


class MwSourcesRequest(BaseModel):
    session_id: str
    titles: List[str] = []


@router.get("/chat/mw-sources")
async def get_chat_mw_sources(session_id: Optional[str] = None):
    """获取写文章会话的参考 MediaWiki 页面标题列表。"""
    if not session_id:
        return {"titles": [], "status": "success"}
    try:
        orchestrator = get_orchestrator()
        titles = orchestrator.context_manager.get_mw_source_titles(session_id)
        return {"titles": titles, "status": "success"}
    except Exception as e:
        debug_log(f"get_chat_mw_sources failed: {e}", level="error")
        return {"titles": [], "status": "error", "error": str(e)}


@router.put("/chat/mw-sources")
async def put_chat_mw_sources(request: MwSourcesRequest):
    """设置写文章会话的参考 MediaWiki 页面标题列表（覆盖）。"""
    try:
        orchestrator = get_orchestrator()
        ok = orchestrator.context_manager.set_mw_source_titles(
            request.session_id, request.titles or []
        )
        return {"status": "success" if ok else "error", "success": ok}
    except Exception as e:
        debug_log(f"put_chat_mw_sources failed: {e}", level="error")
        return {"status": "error", "success": False, "error": str(e)}


class SetArticleRequest(BaseModel):
    session_id: str
    content: str


@router.put("/chat/article")
async def set_chat_article(request: SetArticleRequest):
    """将指定内容设为当前会话的文章草稿（用于「写入右侧预览」），并记入版本历史。"""
    if not request.session_id:
        return {"article": None, "status": "error", "error": "缺少 session_id"}
    try:
        orchestrator = get_orchestrator()
        ok = orchestrator.context_manager.set_current_article(
            request.session_id, request.content or "", source="user"
        )
        article = orchestrator.context_manager.get_current_article(request.session_id) if ok else None
        return {"article": article, "status": "success" if ok else "error", "success": ok}
    except Exception as e:
        debug_log(f"set_chat_article failed: {e}", level="error")
        return {"article": None, "status": "error", "success": False, "error": str(e)}


@router.get("/chat/article/metadata")
async def get_article_metadata(session_id: Optional[str] = None):
    """获取会话的公众号文章元数据（标题、摘要、作者、封面 media_id）。"""
    if not session_id:
        return {"metadata": None, "status": "success"}
    try:
        orchestrator = get_orchestrator()
        meta = orchestrator.context_manager.get_article_wechat_metadata(session_id)
        return {"metadata": meta, "status": "success"}
    except Exception as e:
        debug_log(f"get_article_metadata failed: {e}", level="error")
        return {"metadata": None, "status": "error", "error": str(e)}


class GenerateMetadataRequest(BaseModel):
    session_id: str
    fields: Optional[List[str]] = None  # ["title","digest","author","cover"] 子集，空则全部


@router.post("/chat/article/generate-metadata")
async def generate_article_metadata_endpoint(request: GenerateMetadataRequest):
    """根据当前文章内容生成公众号元数据（可选：标题、摘要、作者、封面图）并保存。"""
    if not request.session_id:
        return {"status": "error", "error": "缺少 session_id", "metadata": None}
    try:
        from backend.services.article_metadata_service import (
            generate_article_metadata,
            generate_cover_image_from_content,
        )

        orchestrator = get_orchestrator()
        content = orchestrator.context_manager.get_current_article(request.session_id)
        if not content or not content.strip():
            return {"status": "error", "error": "当前文章为空", "metadata": None}

        fields = request.fields or ["title", "digest", "author", "cover"]
        meta = {}
        existing = orchestrator.context_manager.get_article_wechat_metadata(
            request.session_id
        ) or {}

        if "title" in fields or "digest" in fields or "author" in fields:
            text_fields = [f for f in ["title", "digest", "author"] if f in fields]
            if not text_fields:
                text_fields = ["title", "digest", "author"]
            parsed = await generate_article_metadata(content, fields=text_fields)
            meta.update({k: parsed.get(k, "") for k in ["title", "digest", "author"]})
            if parsed.get("error"):
                meta["metadata_error"] = parsed["error"]

        if "cover" in fields:
            cover_out = await generate_cover_image_from_content(content)
            meta["thumb_media_id"] = cover_out.get("thumb_media_id", "")
            meta["cover_prompt"] = cover_out.get("prompt", "")
            cover_err = cover_out.get("error")
            if cover_err:
                meta["cover_error"] = cover_err
                debug_log("封面生成失败", level="warning", data={"cover_error": cover_err})

        title = meta.get("title") or existing.get("title", "")
        digest = meta.get("digest") or existing.get("digest", "")
        author = meta.get("author") or existing.get("author", "")
        thumb = meta.get("thumb_media_id") or existing.get("thumb_media_id", "")

        ok = orchestrator.context_manager.set_article_wechat_metadata(
            request.session_id,
            title=title,
            digest=digest,
            author=author,
            thumb_media_id=thumb,
        )
        return {
            "status": "success" if ok else "error",
            "metadata": meta,
            "success": ok,
        }
    except Exception as e:
        import traceback

        debug_log(f"generate_article_metadata failed: {e}", level="error", data={"trace": traceback.format_exc()})
        err_msg = (str(e) or getattr(e, "message", None) or type(e).__name__ or "未知错误").strip()
        return {"status": "error", "error": err_msg or "生成失败", "metadata": None, "success": False}


@router.get("/chat/article/revisions")
async def get_article_revisions(session_id: Optional[str] = None, limit: int = 50, offset: int = 0):
    """列出写文章会话的文章修改历史（版本列表）。"""
    if not session_id:
        return {"revisions": [], "status": "success"}
    try:
        orchestrator = get_orchestrator()
        rows = orchestrator.context_manager.list_article_revisions(
            session_id, limit=max(1, min(limit, 100)), offset=max(0, offset)
        )
        revisions = [
            {"id": r[0], "content": r[1], "source": r[2], "created_at": r[3]}
            for r in rows
        ]
        return {"revisions": revisions, "status": "success"}
    except Exception as e:
        debug_log(f"get_article_revisions failed: {e}", level="error")
        return {"revisions": [], "status": "error", "error": str(e)}


class RestoreArticleRequest(BaseModel):
    session_id: str
    revision_id: int


class ApplyPatchArticleRequest(BaseModel):
    """应用 unified diff 到当前文章（LLM 输出 patch 时使用）。"""
    session_id: str
    patch: str  # unified diff 字符串


class PatchArticleRequest(BaseModel):
    """局部编辑：在锚点后插入内容。"""
    session_id: str
    op: str = "insert_after"  # 目前仅支持 insert_after
    anchor: str  # 当前文章中首次出现的锚点文本
    content: str  # 要插入的段落（支持多行 Markdown）


@router.post("/chat/article/apply-patch")
async def apply_patch_article(request: ApplyPatchArticleRequest):
    """对当前文章应用 unified diff（patch）。用于「LLM 输出 patch」后的精确合并。"""
    if not request.session_id:
        return {"article": None, "status": "error", "error": "缺少 session_id"}
    if not (request.patch or "").strip():
        return {"article": None, "status": "error", "error": "patch 不能为空"}
    try:
        orchestrator = get_orchestrator()
        current = orchestrator.context_manager.get_current_article(request.session_id)
        if current is None:
            current = ""
        new_content = apply_unified_diff(current, request.patch.strip())
        ok = orchestrator.context_manager.set_current_article(
            request.session_id, new_content, source="user"
        )
        article = orchestrator.context_manager.get_current_article(request.session_id) if ok else None
        if ok:
            try:
                from backend.services.llm.model_stats import get_last_model_for_session, record_acceptance
                model = get_last_model_for_session(request.session_id)
                if model:
                    record_acceptance(model, request.session_id)
            except Exception:
                pass
        return {"article": article, "status": "success" if ok else "error", "success": ok}
    except ValueError as e:
        return {"article": None, "status": "error", "success": False, "error": str(e)}
    except Exception as e:
        debug_log(f"apply_patch_article failed: {e}", level="error")
        return {"article": None, "status": "error", "success": False, "error": str(e)}


@router.post("/chat/article/patch")
async def patch_article(request: PatchArticleRequest):
    """在文章锚点首次出现位置之后插入一段内容，其余不变，并作为新版本入库。"""
    if not request.session_id:
        return {"article": None, "status": "error", "error": "缺少 session_id"}
    if (request.anchor or "").strip() == "":
        return {"article": None, "status": "error", "error": "锚点不能为空"}
    if request.op != "insert_after":
        return {"article": None, "status": "error", "error": f"不支持的操作: {request.op}"}
    try:
        orchestrator = get_orchestrator()
        current = orchestrator.context_manager.get_current_article(request.session_id)
        if current is None:
            current = ""
        idx = current.find(request.anchor)
        if idx < 0:
            return {"article": None, "status": "error", "error": "未在文章中找到该锚点，请检查锚点文本是否与文中一致"}
        next_idx = current.find(request.anchor, idx + len(request.anchor))
        if next_idx >= 0:
            return {"article": None, "status": "error", "error": "该锚点在文中出现多处，请使用更长的唯一文本作为锚点"}
        insert_pos = idx + len(request.anchor)
        new_content = (
            current[:insert_pos]
            + "\n\n"
            + (request.content or "").strip()
            + "\n\n"
            + current[insert_pos:]
        )
        ok = orchestrator.context_manager.set_current_article(
            request.session_id, new_content, source="user"
        )
        article = orchestrator.context_manager.get_current_article(request.session_id) if ok else None
        return {"article": article, "status": "success" if ok else "error", "success": ok}
    except Exception as e:
        debug_log(f"patch_article failed: {e}", level="error")
        return {"article": None, "status": "error", "success": False, "error": str(e)}


class MergeArticleRequest(BaseModel):
    """3-way 合并：base 为共同祖先，ours 为当前版本，theirs 为待合并版本。"""
    session_id: str
    base: str
    ours: str
    theirs: str


@router.post("/chat/article/merge")
async def merge_article(request: MergeArticleRequest):
    """对文章做 Git 风格 3-way 合并，返回合并结果（可能含冲突标记）。"""
    if not request.session_id:
        return {"content": None, "status": "error", "error": "缺少 session_id", "has_conflicts": False}
    try:
        with tempfile.TemporaryDirectory() as tmp:
            base_f = Path(tmp) / "base.md"
            ours_f = Path(tmp) / "ours.md"
            theirs_f = Path(tmp) / "theirs.md"
            base_f.write_text(request.base or "", encoding="utf-8")
            ours_f.write_text(request.ours or "", encoding="utf-8")
            theirs_f.write_text(request.theirs or "", encoding="utf-8")
            proc = subprocess.run(
                ["git", "merge-file", "-p", str(ours_f), str(base_f), str(theirs_f)],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmp,
            )
            merged = proc.stdout or ""
            has_conflicts = proc.returncode == 1
            return {
                "content": merged,
                "status": "success",
                "has_conflicts": has_conflicts,
            }
    except FileNotFoundError:
        return {"content": None, "status": "error", "error": "未找到 git，无法执行合并", "has_conflicts": False}
    except subprocess.TimeoutExpired:
        return {"content": None, "status": "error", "error": "合并超时", "has_conflicts": False}
    except Exception as e:
        debug_log(f"merge_article failed: {e}", level="error")
        return {"content": None, "status": "error", "error": str(e), "has_conflicts": False}


@router.post("/chat/article/restore")
async def restore_article_revision(request: RestoreArticleRequest):
    """将指定版本恢复为当前文章。"""
    if not request.session_id:
        return {"article": None, "status": "error", "error": "缺少 session_id"}
    try:
        orchestrator = get_orchestrator()
        content = orchestrator.context_manager.restore_article_revision(
            request.revision_id, request.session_id
        )
        if content is None:
            return {"article": None, "status": "error", "error": "版本不存在或不属于本会话"}
        return {"article": content, "status": "success"}
    except Exception as e:
        debug_log(f"restore_article_revision failed: {e}", level="error")
        return {"article": None, "status": "error", "error": str(e)}

