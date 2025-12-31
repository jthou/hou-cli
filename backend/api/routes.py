"""路由定义"""
from fastapi import APIRouter
from pydantic import BaseModel
from backend.core.agent.orchestrator import Orchestrator

router = APIRouter()
orchestrator = Orchestrator()

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
async def chat(request: ChatRequest):
    """处理聊天请求"""
    try:
        response = await orchestrator.process(request.message)
        return {"response": response, "status": "success"}
    except Exception as e:
        return {
            "response": None,
            "status": "error",
            "error": str(e)
        }

