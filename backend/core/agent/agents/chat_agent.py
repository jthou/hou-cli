"""Chat Agent - 对话和问答"""
from typing import Dict, Any
from backend.core.agent.base_agent import BaseAgent

class ChatAgent(BaseAgent):
    """对话 Agent"""
    
    def __init__(self):
        super().__init__(
            name="对话Agent",
            description="专门处理对话和问答",
            capabilities=["对话", "问答", "信息查询"]
        )
    
    async def execute(self, task: Dict[str, Any]) -> Any:
        """执行对话任务"""
        message = task.get("message", "")
        response = await self.think(message)
        return {"response": response}

