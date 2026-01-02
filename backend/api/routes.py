"""路由定义"""
import os
import json
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# 加载 .env 文件（在导入 Orchestrator 之前）
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # 尝试从当前目录加载
    load_dotenv()

from backend.core.agent.orchestrator import Orchestrator

router = APIRouter()

# 延迟创建 orchestrator，确保 .env 已加载
_orchestrator = None

def get_orchestrator():
    """获取 Orchestrator 实例（单例模式）"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None  # 会话 ID（可选）

@router.post("/chat")
async def chat(request: ChatRequest):
    """处理聊天请求（非流式）"""
    try:
        orchestrator = get_orchestrator()
        context = {}
        if request.session_id:
            context["session_id"] = request.session_id
        
        response = await orchestrator.process(request.message, context=context)
        
        # 返回响应和会话 ID（如果是新会话）
        result = {
            "response": response,
            "status": "success"
        }
        if not request.session_id:
            # 如果是新会话，返回会话 ID（需要从 orchestrator 获取）
            # 简化处理：前端可以自己管理会话 ID
            pass
        
        return result
    except Exception as e:
        return {
            "response": None,
            "status": "error",
            "error": str(e)
        }

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """处理聊天请求（流式 SSE）"""
    async def generate():
        try:
            orchestrator = get_orchestrator()
            context = {}
            if request.session_id:
                context["session_id"] = request.session_id
            
            async for chunk in orchestrator.stream_process(request.message, context=context):
                # SSE 格式：data: {json}\n\n
                yield f"data: {json.dumps({'content': chunk, 'status': 'streaming'})}\n\n"
            # 发送完成信号
            yield f"data: {json.dumps({'content': '', 'status': 'done'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'content': '', 'status': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用 Nginx 缓冲
        }
    )

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

@router.post("/sessions/{session_id}/clear")
async def clear_session_messages(session_id: str):
    """清除会话的所有消息"""
    try:
        orchestrator = get_orchestrator()
        result = orchestrator.context_manager.clear_session(session_id)
        
        if result:
            return {"success": True, "message": f"会话 {session_id} 的消息已清除"}
        else:
            return {"success": False, "error": f"会话不存在或清除失败: {session_id}"}
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/sessions/{session_id}")
async def get_session_detail(session_id: str):
    """获取会话详情（包含消息列表）"""
    try:
        orchestrator = get_orchestrator()
        session = orchestrator.context_manager.get_session(session_id)
        
        if not session:
            return {"success": False, "error": f"会话不存在: {session_id}"}
        
        # 获取消息列表（不压缩，用于显示）
        messages = orchestrator.context_manager.get_messages(
            session_id,
            compressed=False
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
        
        return {
            "success": True,
            "session": {
                "session_id": session.session_id,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "metadata": session.metadata
            },
            "messages": messages_data
        }
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

@router.post("/sessions")
async def create_session():
    """创建新会话"""
    try:
        orchestrator = get_orchestrator()
        session_id = orchestrator.context_manager.create_session()
        
        return {
            "success": True,
            "session_id": session_id,
            "message": f"新会话已创建: {session_id}"
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
        orchestrator = get_orchestrator()
        session = orchestrator.context_manager.get_session(session_id)
        
        if not session:
            return {"success": False, "error": f"会话不存在: {session_id}"}
        
        # 获取消息列表
        messages = orchestrator.context_manager.get_messages(session_id, compressed=False)
        
        if not messages:
            return {"success": False, "error": "会话中没有消息"}
        
        # 构建对话内容用于摘要生成
        conversation_text = "\n".join([
            f"{msg.role.value}: {msg.content}"
            for msg in messages
        ])
        
        # 使用 LLM 生成摘要
        system_prompt = "你是一个专业的对话摘要生成器。请为以下对话生成一个简洁、准确的摘要，包括主要话题、关键信息和结论。"
        user_prompt = f"请为以下对话生成摘要：\n\n{conversation_text}"
        
        summary = await orchestrator.llm_service.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        return {
            "success": True,
            "summary": summary,
            "session_id": session_id,
            "message_count": len(messages)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

