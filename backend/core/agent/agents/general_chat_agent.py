"""
通用对话 Agent - 使用 CHAT_SYSTEM_PROMPT，支持全量工具与会话级 enabled_tools、persona。
"""
from typing import Any, AsyncIterator, Dict, Optional

from backend.api.stream_sender import should_persist_stream_chunk_in_assistant_message
from backend.core.context.models import MessageRole
from backend.core.agent.system_prompt_templates import CHAT_SYSTEM_PROMPT
from backend.core.agent.agent_tools_registry import (
    get_tool_names_for_agent,
    get_tools_for_llm_by_agent,
)
from backend.core.agent.agents.base_context_agent import BaseContextAgent


class GeneralChatAgent(BaseContextAgent):
    """通用对话 Agent：CHAT_SYSTEM_PROMPT，支持 enabled_tools、persona。"""

    AGENT_ID = "general_chat"

    def get_tools_for_llm(
        self,
        session_id: Optional[str],
        task: str,
    ) -> list:
        """获取工具列表，考虑 enabled_tools 与「工具询问」特殊逻辑。"""
        tools = get_tools_for_llm_by_agent(
            self.AGENT_ID,
            self.tool_registry.get_tools_for_llm(),
        )
        t = (task or "").strip()
        if any(
            k in t
            for k in (
                "你有什么工具",
                "你能做什么",
                "有哪些工具",
                "你能调用哪些工具",
                "你会用哪些工具",
            )
        ):
            return []

        session_obj = self.context_manager.get_session(session_id) if session_id else None
        session_meta = (session_obj.metadata or {}) if session_obj else {}
        enabled = session_meta.get("enabled_tools")
        if isinstance(enabled, list) and len(enabled) > 0 and tools:
            name_set = set(enabled)
            tools = [
                t for t in tools
                if (t.get("function") or {}).get("name") in name_set
            ]
        return tools

    async def stream_process(
        self,
        task: str,
        context: Optional[Dict[str, Any]],
        delegate: Any,
    ) -> AsyncIterator[str]:
        session_id = context.get("session_id") if context else None
        if not session_id:
            session_id = self.context_manager.create_session(
                metadata={"type": "general_chat"}
            )

        history = self.context_manager.get_messages_for_llm(
            session_id, max_messages=None, max_tokens=None
        )
        system_prompt = CHAT_SYSTEM_PROMPT

        session_obj = self.context_manager.get_session(session_id)
        session_meta = (session_obj.metadata or {}) if session_obj else {}
        tool_names = get_tool_names_for_agent("general_chat")
        enabled = session_meta.get("enabled_tools")
        if isinstance(enabled, list) and len(enabled) > 0:
            tool_names = [t for t in tool_names if t in set(enabled)]
        tools_list_str = "、".join(tool_names) if tool_names else "（无）"
        system_prompt = (
            system_prompt
            + f"\n\n【可用工具列表】当用户问「你有什么工具」「你能做什么」时，"
            f"直接以文字回答，不要调用任何工具。可用工具：{tools_list_str}"
        )
        persona = (session_meta.get("persona") or "").strip()
        if persona:
            system_prompt = f"【身份】{persona}\n\n{system_prompt}"

        filtered_history = [
            msg for msg in history if msg["role"] in ["user", "assistant"]
        ]
        if filtered_history:
            history_text = "\n".join([
                f"{'用户' if msg['role'] == 'user' else '助手'}: {msg['content']}"
                for msg in filtered_history
            ])
            user_prompt = (
                f"以下是历史对话记录：\n{history_text}\n\n当前用户问题：{task}"
            )
        else:
            user_prompt = task

        tools = self.get_tools_for_llm(session_id, task)

        selected_model = await delegate._select_model(task, context=context)
        if selected_model != self.llm_service.model:
            self.llm_service.set_model(selected_model)

        try:
            full_response = ""
            if tools:
                async for chunk in delegate._chat_with_tools_stream(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    tools=tools,
                    planning_files=None,
                    session_id=session_id,
                    context=context,
                ):
                    if should_persist_stream_chunk_in_assistant_message(chunk):
                        full_response = (full_response or "") + chunk
                    yield chunk
            else:
                audit_meta = {"session_id": session_id} if session_id else None
                async for chunk in self.llm_service.stream_chat(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    audit_meta=audit_meta,
                    stream_reasoning_chunks=True,
                ):
                    if should_persist_stream_chunk_in_assistant_message(chunk):
                        full_response += chunk
                    yield chunk

            self.context_manager.add_message(session_id, MessageRole.USER, task)
            self.context_manager.add_message(
                session_id, MessageRole.ASSISTANT, full_response or ""
            )
        finally:
            self.llm_service.reset_model()
