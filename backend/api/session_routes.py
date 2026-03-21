"""会话管理相关路由"""
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel
from backend.core.agent.orchestrator import Orchestrator
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

class CreateSessionRequest(BaseModel):
    metadata: Optional[dict] = None


class UpdateSessionRequest(BaseModel):
    title: Optional[str] = None
    metadata: Optional[dict] = None


@router.get("/sessions/list")
async def list_sessions(
    limit: int = 10,
    type: Optional[str] = None,
    sort: Optional[str] = None,
    order: Optional[str] = None,
    offset: int = 0,
):
    """列出会话；type= 时过滤类型；sort=updated_at|created_at，order=asc|desc，offset/limit 分页，limit 最大 100。"""
    limit = min(max(1, limit), 100)
    offset = max(0, offset)
    sort = sort if sort in ("updated_at", "created_at") else "updated_at"
    order = order if order in ("asc", "desc") else "desc"
    try:
        orchestrator = get_orchestrator()
        if type:
            fetch_limit = 200  # 先多取再按 type 过滤、再分页
            sessions = orchestrator.context_manager.list_sessions(
                limit=fetch_limit, sort=sort, order=order, offset=0
            )
            # type=article_writing 时同时包含未设置 type 的会话（兼容旧会话，避免“前面的会话没了”）
            if type == "article_writing":
                sessions = [
                    s for s in sessions
                    if (s.metadata or {}).get("type") == type or not (s.metadata or {}).get("type")
                ]
            else:
                sessions = [s for s in sessions if (s.metadata or {}).get("type") == type]
            sessions = sessions[offset : offset + limit]
        else:
            sessions = orchestrator.context_manager.list_sessions(
                limit=limit, sort=sort, order=order, offset=offset
            )

        # 获取每个会话的预览信息，并补充 title（metadata.title 或 fallback preview）
        result = []
        for session in sessions:
            try:
                preview = orchestrator.context_manager.get_session_preview(session.session_id)
                meta = preview.get("metadata") or {}
                preview["title"] = (meta.get("title") or preview.get("preview") or "").strip() or None
                result.append(preview)
            except Exception as e:
                meta = session.metadata or {}
                result.append({
                    "session_id": session.session_id,
                    "preview": "",
                    "title": (meta.get("title") or "").strip() or None,
                    "message_count": 0,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "metadata": session.metadata
                })
        
        return {"sessions": result}
    except Exception as e:
        return {
            "sessions": [],
            "error": str(e)
        }

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除指定会话（移除会话记录与目录，不可恢复）。"""
    try:
        orchestrator = get_orchestrator()
        result = orchestrator.context_manager.delete_session(session_id)
        
        if result:
            return {"success": True, "message": f"会话 {session_id} 已删除"}
        else:
            return {"success": False, "error": f"会话不存在或删除失败: {session_id}"}
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/sessions/search")
async def search_sessions(keyword: str, limit: int = 10):
    """搜索包含关键词的会话"""
    try:
        orchestrator = get_orchestrator()
        all_sessions = orchestrator.context_manager.list_sessions(limit=1000)
        
        # 搜索匹配的会话
        matching_sessions = []
        for session in all_sessions:
            # 获取会话预览
            try:
                preview = orchestrator.context_manager.get_session_preview(session.session_id)
                # 检查预览文本、会话 ID 或元数据中是否包含关键词
                if (keyword.lower() in preview.get("preview", "").lower() or
                    keyword.lower() in session.session_id.lower() or
                    any(keyword.lower() in str(v).lower() for v in session.metadata.values() if v)):
                    matching_sessions.append(preview)
            except:
                continue
            
            if len(matching_sessions) >= limit:
                break
        
        return {"sessions": matching_sessions}
    except Exception as e:
        return {
            "sessions": [],
            "error": str(e)
        }

@router.delete("/sessions/{session_id}/messages/{message_id}")
async def delete_message(session_id: str, message_id: str):
    """删除会话中的单条消息。前端删除后需同步到后端。"""
    debug_log(
        "收到删除消息请求",
        data={"session_id": session_id, "message_id": message_id}
    )
    try:
        if not message_id or not message_id.strip():
            return {"success": False, "error": "message_id 不能为空"}
        message_id = message_id.strip()
        orchestrator = get_orchestrator()
        result = orchestrator.context_manager.delete_message(session_id, message_id)
        if result:
            return {"success": True, "message": "消息已删除"}
        debug_log(
            "删除消息失败：未找到匹配的 message_id",
            level="warning",
            data={"session_id": session_id, "message_id": message_id}
        )
        return {"success": False, "error": "消息不存在或删除失败"}
    except Exception as e:
        debug_log(
            f"删除消息异常: {str(e)}",
            level="error",
            data={"session_id": session_id, "message_id": message_id}
        )
        return {"success": False, "error": str(e)}


class BatchDeleteMessagesRequest(BaseModel):
    message_ids: list[str]


class BatchDeleteSessionsRequest(BaseModel):
    session_ids: list[str]
    # 2026-03-21：与 list_sessions(type=…) 一致；article_writing 时允许 metadata 无 type（旧会话）
    expected_type: Optional[str] = None


def _session_metadata_type_matches_expected(session, expected_type: str) -> bool:
    """批量删会话前校验类型。expected_type=article_writing 时与 GET list 过滤规则一致。"""
    actual = (session.metadata or {}).get("type")
    if expected_type == "article_writing":
        return actual == "article_writing" or not actual
    return actual == expected_type


@router.post("/sessions/{session_id}/messages/batch-delete")
async def batch_delete_messages(session_id: str, request: BatchDeleteMessagesRequest):
    """批量删除会话中的消息（设计见 docs/design/01-batch-delete-sessions-and-messages-design.md）。"""
    debug_log(
        "收到批量删除消息请求",
        data={"session_id": session_id, "message_ids": request.message_ids}
    )
    try:
        message_ids = [mid.strip() for mid in request.message_ids if mid and mid.strip()]
        if not message_ids:
            return {"success": False, "error": "message_ids 不能为空"}
        if len(message_ids) > 100:
            return {"success": False, "error": "每次最多删除100条消息"}

        orchestrator = get_orchestrator()
        result = orchestrator.context_manager.delete_messages(session_id, message_ids)

        debug_log(
            "批量删除消息完成",
            data={"session_id": session_id, "result": result}
        )
        return result
    except Exception as e:
        debug_log(
            f"批量删除消息异常: {str(e)}",
            level="error",
            data={"session_id": session_id, "message_ids": request.message_ids}
        )
        return {"success": False, "error": str(e)}


@router.post("/sessions/batch-delete")
async def batch_delete_sessions(request: BatchDeleteSessionsRequest):
    """批量删除会话。可选 expected_type 防止跨助手误删（article_writing 兼容无 type 的旧会话）。"""
    debug_log(
        "收到批量删除会话请求",
        data={"session_ids": request.session_ids, "expected_type": request.expected_type}
    )
    try:
        session_ids = [sid.strip() for sid in request.session_ids if sid and sid.strip()]
        if not session_ids:
            return {"success": False, "error": "session_ids 不能为空"}
        if len(session_ids) > 50:
            return {"success": False, "error": "每次最多删除50个会话"}

        orchestrator = get_orchestrator()

        if request.expected_type:
            exp = request.expected_type.strip()
            for sid in session_ids:
                session = orchestrator.context_manager.get_session(sid)
                # 2026-03-21：expected_type 下必须能对每个 id 做类型判断；跳过「无索引会话」会留下与 list 不一致的删盘路径（终端审查）
                if session is None:
                    return {
                        "success": False,
                        "error": (
                            f"会话 {sid} 不存在或未在索引中，无法在 expected_type={exp!r} 下校验；请刷新列表后重试"
                        ),
                    }
                if not _session_metadata_type_matches_expected(session, exp):
                    actual = (session.metadata or {}).get("type")
                    return {
                        "success": False,
                        "error": (
                            f"会话 {sid} 类型为 {actual!r}，与期望的类型 {exp!r} 不符"
                        ),
                    }

        result = orchestrator.context_manager.delete_sessions(session_ids)

        debug_log(
            "批量删除会话完成",
            data={"result": result}
        )
        return result
    except Exception as e:
        debug_log(
            f"批量删除会话异常: {str(e)}",
            level="error",
            data={"session_ids": request.session_ids}
        )
        return {"success": False, "error": str(e)}


@router.post("/sessions/{session_id}/clear")
async def clear_session_messages(session_id: str):
    """清除会话的所有消息与当前文章草稿（含 current_article.md），会话本身保留。"""
    try:
        debug_log(
            "清除会话消息",
            data={"session_id": session_id}
        )
        orchestrator = get_orchestrator()
        result = orchestrator.context_manager.clear_session(session_id)
        
        if result:
            debug_log(
                "成功清除会话消息",
                data={"session_id": session_id}
            )
            return {"success": True, "message": f"会话 {session_id} 的消息已清除"}
        else:
            debug_log(
                "清除会话消息失败",
                level="warning",
                data={"session_id": session_id}
            )
            return {"success": False, "error": f"会话不存在或清除失败: {session_id}"}
    except Exception as e:
        debug_log(
            f"清除会话消息异常: {str(e)}",
            level="error",
            data={"session_id": session_id}
        )
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/sessions/{session_id}")
async def get_session_detail(session_id: str):
    """获取会话详情（包含消息列表）"""
    try:
        debug_log(
            "获取会话详情",
            data={"session_id": session_id}
        )
        orchestrator = get_orchestrator()
        session = orchestrator.context_manager.get_session(session_id)
        
        if not session:
            debug_log(
                "会话不存在",
                level="warning",
                data={"session_id": session_id}
            )
            return {"success": False, "error": f"会话不存在: {session_id}"}
        
        # 获取消息列表（不压缩，用于显示）
        debug_log(
            "获取消息列表",
            data={"session_id": session_id, "compressed": False}
        )
        messages = orchestrator.context_manager.get_messages(
            session_id,
            compressed=False
        )
        debug_log(
            f"获取到 {len(messages)} 条消息",
            data={"count": len(messages)}
        )
        
        # 转换为字典格式
        messages_data = [
            {
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "message_id": msg.message_id
            }
            for msg in messages
        ]
        
        result = {
            "success": True,
            "session": {
                "session_id": session.session_id,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "metadata": session.metadata
            },
            "messages": messages_data
        }
        debug_log(
            "成功获取会话详情",
            data={"session_id": session_id, "messages_count": len(messages_data)}
        )
        return result
    except Exception as e:
        debug_log(
            f"获取会话详情失败: {str(e)}",
            level="error",
            data={"session_id": session_id}
        )
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/sessions")
async def create_session(request: Optional[CreateSessionRequest] = None):
    """创建新会话；可传 metadata，如 { \"type\": \"article_writing\" } 标记写作助手会话"""
    try:
        orchestrator = get_orchestrator()
        metadata = getattr(request, "metadata", None) if request else None
        session_id = orchestrator.context_manager.create_session(metadata=metadata)
        return {"success": True, "session_id": session_id}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.patch("/sessions/{session_id}")
async def update_session(session_id: str, request: UpdateSessionRequest):
    """更新会话元数据（如 title）；body 中 title 会写入 metadata.title。"""
    try:
        orchestrator = get_orchestrator()
        session = orchestrator.context_manager.get_session(session_id)
        if not session:
            return {"success": False, "error": f"会话不存在: {session_id}"}
        updates = dict(request.metadata) if request.metadata else {}
        if request.title is not None:
            updates["title"] = request.title
        if not updates:
            return {"success": True, "session_id": session_id}
        ok = orchestrator.context_manager.update_session_metadata(session_id, updates)
        return {"success": ok, "session_id": session_id} if ok else {"success": False, "error": "更新失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/sessions/{session_id}/summary")
async def generate_session_summary(session_id: str):
    """生成会话摘要"""
    try:
        debug_log(
            "生成会话摘要",
            data={"session_id": session_id}
        )
        orchestrator = get_orchestrator()
        session = orchestrator.context_manager.get_session(session_id)
        
        if not session:
            return {"success": False, "error": f"会话不存在: {session_id}"}
        
        # 获取消息列表
        messages = orchestrator.context_manager.get_messages(
            session_id,
            compressed=False
        )
        
        if not messages:
            return {"success": False, "error": "会话中没有消息"}
        
        # 生成摘要（这里简化处理，实际应该调用 LLM）
        # TODO: 实现真正的摘要生成逻辑
        summary = f"会话包含 {len(messages)} 条消息"
        
        return {
            "success": True,
            "session_id": session_id,
            "summary": summary
        }
    except Exception as e:
        debug_log(
            f"生成会话摘要失败: {str(e)}",
            level="error",
            data={"session_id": session_id}
        )
        return {
            "success": False,
            "error": str(e)
        }

