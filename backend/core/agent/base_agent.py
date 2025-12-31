"""Agent 基类"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from backend.services.llm.llm_service import LLMService

class BaseAgent(ABC):
    """Agent 基类，所有专门化 Agent 继承此类"""
    
    def __init__(self, name: str, description: str, capabilities: list = None):
        self.name = name
        self.description = description
        self.capabilities = capabilities or []
        self.llm_service = LLMService()
    
    @abstractmethod
    async def execute(self, task: Dict[str, Any]) -> Any:
        """执行任务"""
        pass
    
    async def think(self, prompt: str, context: Optional[Dict] = None) -> str:
        """Agent 思考过程"""
        system_prompt = f"""你是 {self.name}，{self.description}
        
你的能力包括：
{chr(10).join(f"- {cap}" for cap in self.capabilities)}

请仔细思考并执行任务。"""
        
        if context:
            system_prompt += f"\n\n上下文信息：{context}"
        
        response = await self.llm_service.chat(
            system_prompt=system_prompt,
            user_prompt=prompt
        )
        return response

