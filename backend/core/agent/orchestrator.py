"""Agent 编排器"""
from typing import Optional, Dict, Any, AsyncIterator
from backend.core.agent.coordinator import AgentCoordinator
from backend.services.llm.llm_service import LLMService
# from backend.core.workflow.workflow_identifier import WorkflowIdentifier
# from backend.core.workflow.workflow_engine import WorkflowEngine

class Orchestrator:
    """Agent 编排器，负责任务分解和 Agent 协调"""
    
    def __init__(self):
        self.coordinator = AgentCoordinator()
        self.llm_service = LLMService()
        # self.workflow_identifier = WorkflowIdentifier()
        # self.workflow_engine = WorkflowEngine(self)
    
    async def process(self, task: str, context: Optional[Dict] = None) -> str:
        """处理任务，支持 SOP 和动态编排"""
        # TODO: 实现流程识别和 SOP 执行
        # 暂时使用动态编排
        return await self.process_dynamic(task, context)
    
    async def process_dynamic(self, task: str, context: Optional[Dict] = None) -> str:
        """动态编排执行"""
        # TODO: 实现动态编排逻辑
        # 暂时直接调用 LLM
        system_prompt = "你是一个智能助手，能够帮助用户解决各种问题。"
        response = await self.llm_service.chat(
            system_prompt=system_prompt,
            user_prompt=task
        )
        return response
    
    async def stream_process(self, task: str, context: Optional[Dict] = None) -> AsyncIterator[str]:
        """流式处理任务"""
        # TODO: 实现流式编排逻辑
        # 暂时直接调用 LLM 流式接口
        system_prompt = "你是一个智能助手，能够帮助用户解决各种问题。"
        async for chunk in self.llm_service.stream_chat(
            system_prompt=system_prompt,
            user_prompt=task
        ):
            yield chunk

