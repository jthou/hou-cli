"""Agent 编排器"""
import os
from pathlib import Path
from typing import Optional, Dict, Any, AsyncIterator
from dotenv import load_dotenv

# 加载 .env 文件（在导入 LLMService 之前）
env_path = Path(__file__).parent.parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # 尝试从当前目录加载
    load_dotenv()

from backend.core.agent.coordinator import AgentCoordinator
from backend.core.context.manager import ContextManager as FullContextManager
from backend.core.context.models import MessageRole
from backend.services.llm.llm_service import LLMService
from shared.debug_utils import DebugOutput
# from backend.core.workflow.workflow_identifier import WorkflowIdentifier
# from backend.core.workflow.workflow_engine import WorkflowEngine

class Orchestrator:
    """Agent 编排器，负责任务分解和 Agent 协调"""
    
    def __init__(self):
        self.coordinator = AgentCoordinator()
        self.llm_service = LLMService()
        self.context_manager = FullContextManager()
        self.debug = DebugOutput()  # 调试输出
        # self.workflow_identifier = WorkflowIdentifier()
        # self.workflow_engine = WorkflowEngine(self)
    
    async def process(self, task: str, context: Optional[Dict] = None) -> str:
        """处理任务，支持 SOP 和动态编排"""
        # TODO: 实现流程识别和 SOP 执行
        # 暂时使用动态编排
        return await self.process_dynamic(task, context)
    
    async def process_dynamic(self, task: str, context: Optional[Dict] = None) -> str:
        """
        动态编排执行
        
        Args:
            task: 用户任务/消息
            context: 上下文信息（可选，包含 session_id）
            
        Returns:
            LLM 生成的回复
        """
        self.debug.log_orchestrator_step("开始处理任务", {"task": task[:50] + "..." if len(task) > 50 else task})
        
        # 获取会话 ID（如果提供）
        session_id = context.get("session_id") if context else None
        self.debug.log_context_operation("获取会话ID", session_id or "new", {"provided": session_id is not None})
        
        # 如果没有会话 ID，创建新会话
        if not session_id:
            session_id = self.context_manager.create_session()
            self.debug.log_context_operation("创建新会话", session_id)
        
        # 获取历史消息
        history = self.context_manager.get_messages_for_llm(session_id)
        self.debug.log_context_operation("获取历史消息", session_id, {"count": len(history)})
        
        # 构建消息列表
        system_prompt = "你是一个智能助手，能够帮助用户解决各种问题。"
        
        # 构建 user_prompt（包含历史上下文）
        user_prompt = task
        if history:
            # 将历史消息格式化为对话形式
            history_text = "\n".join([
                f"{'用户' if msg['role'] == 'user' else '助手'}: {msg['content']}"
                for msg in history
            ])
            user_prompt = f"{history_text}\n用户: {task}"
        else:
            user_prompt = task
        
        # LLM 调用
        self.debug.log_llm_request(system_prompt, user_prompt, "deepseek-chat")
        response = await self.llm_service.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        self.debug.log_llm_response(response, "deepseek-chat")
        
        # 保存消息到历史
        self.context_manager.add_message(session_id, MessageRole.USER, task)
        self.context_manager.add_message(session_id, MessageRole.ASSISTANT, response)
        self.debug.log_context_operation("保存消息", session_id, {"user": True, "assistant": True})
        
        self.debug.log_orchestrator_step("任务处理完成", {"response_length": len(response)})
        return response
    
    async def stream_process(self, task: str, context: Optional[Dict] = None) -> AsyncIterator[str]:
        """
        流式处理任务
        
        Args:
            task: 用户任务/消息
            context: 上下文信息（可选，包含 session_id）
            
        Yields:
            流式数据块
        """
        self.debug.log_orchestrator_step("开始流式处理任务", {"task": task[:50] + "..." if len(task) > 50 else task})
        
        # 获取会话 ID（如果提供）
        session_id = context.get("session_id") if context else None
        self.debug.log_context_operation("获取会话ID", session_id or "new", {"provided": session_id is not None})
        
        # 如果没有会话 ID，创建新会话
        if not session_id:
            session_id = self.context_manager.create_session()
            self.debug.log_context_operation("创建新会话", session_id)
        
        # 获取历史消息
        history = self.context_manager.get_messages_for_llm(session_id)
        self.debug.log_context_operation("获取历史消息", session_id, {"count": len(history)})
        
        # 构建消息
        system_prompt = "你是一个智能助手，能够帮助用户解决各种问题。"
        
        # 构建 user_prompt（包含历史上下文）
        if history:
            # 将历史消息格式化为对话形式
            history_text = "\n".join([
                f"{'用户' if msg['role'] == 'user' else '助手'}: {msg['content']}"
                for msg in history
            ])
            user_prompt = f"{history_text}\n用户: {task}"
        else:
            user_prompt = task
        
        # 流式调用 LLM
        self.debug.log_llm_request(system_prompt, user_prompt, "deepseek-chat")
        full_response = ""
        
        async for chunk in self.llm_service.stream_chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        ):
            full_response += chunk
            yield chunk
        
        self.debug.log_llm_response(full_response, "deepseek-chat")
        
        # 保存消息到历史
        self.context_manager.add_message(session_id, MessageRole.USER, task)
        self.context_manager.add_message(session_id, MessageRole.ASSISTANT, full_response)
        self.debug.log_context_operation("保存消息", session_id, {"user": True, "assistant": True})
        
        self.debug.log_orchestrator_step("流式任务处理完成", {"response_length": len(full_response)})

