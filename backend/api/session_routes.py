"""会话管理相关路由"""
from fastapi import APIRouter
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

@router.get("/sessions/list")
async def list_sessions(limit: int = 10):
    """列出最近的会话"""
    try:
        orchestrator = get_orchestrator()
        sessions = orchestrator.context_manager.list_sessions(limit=limit)
        
        # 获取每个会话的预览信息
        result = []
        for session in sessions:
            try:
                preview = orchestrator.context_manager.get_session_preview(session.session_id)
                result.append(preview)
            except Exception as e:
                # 如果获取预览失败，使用基本信息
                result.append({
                    "session_id": session.session_id,
                    "preview": "",
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
    """删除指定会话"""
    try:
        orchestrator = get_orchestrator()
        result = orchestrator.context_manager.clear_session(session_id)
        
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

@router.post("/sessions/{session_id}/clear")
async def clear_session_messages(session_id: str):
    """清除会话的所有消息"""
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
async def create_session():
    """创建新会话"""
    try:
        orchestrator = get_orchestrator()
        session_id = orchestrator.context_manager.create_session()
        
        return {
            "success": True,
            "session_id": session_id
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

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

