"""
工作助手 Agent - 面向软件架构师，管理学规范，支持看板与 MediaWiki 工具。
"""
from typing import Any, AsyncIterator, Dict, Optional

from backend.core.context.models import MessageRole
from backend.core.agent.system_prompt_templates import WORK_ASSISTANT_SYSTEM_PROMPT
from backend.core.agent.agent_tools_registry import (
    get_tool_names_for_agent,
    get_tools_for_llm_by_agent,
)
from backend.core.agent.agents.base_context_agent import BaseContextAgent


class WorkAssistantAgent(BaseContextAgent):
    """工作助手 Agent：软件架构师身份、管理学规范，支持 kanban_board、mediawiki 工具。"""

    AGENT_ID = "work_assistant"

    def get_tools_for_llm(self) -> list:
        """获取工作助手配备的工具列表。"""
        return get_tools_for_llm_by_agent(
            self.AGENT_ID,
            self.tool_registry.get_tools_for_llm(),
        )

    async def stream_process(
        self,
        task: str,
        context: Optional[Dict[str, Any]],
        delegate: Any,
    ) -> AsyncIterator[str]:
        regenerate_msg_id = (context or {}).get("regenerate_from_message_id")
        session_id = context.get("session_id") if context else None

        if regenerate_msg_id and session_id:
            msg = self.context_manager.get_message_by_id(
                session_id, regenerate_msg_id
            )
            if not msg or msg.role != MessageRole.USER:
                yield "错误：无法重新回答，未找到对应用户消息。"
                return
            task = msg.content or ""
            ok = self.context_manager.truncate_after_message(
                session_id, regenerate_msg_id
            )
            if not ok:
                yield "错误：截断对话失败。"
                return

        if not session_id:
            session_id = self.context_manager.create_session(
                metadata={"type": "work_assistant"}
            )

        session_obj = self.context_manager.get_session(session_id)
        session_meta = (session_obj.metadata or {}) if session_obj else {}
        persona = (session_meta.get("persona") or "").strip()

        system_prompt = WORK_ASSISTANT_SYSTEM_PROMPT
        if persona:
            system_prompt = f"【身份】{persona}\n\n{system_prompt}"

        history = self.context_manager.get_messages_for_llm(
            session_id, max_messages=None, max_tokens=None
        )
        filtered_history = [
            msg for msg in history if msg["role"] in ["user", "assistant"]
        ]
        if filtered_history:
            history_text = "\n".join([
                f"{'用户' if msg['role'] == 'user' else '助手'}: {msg['content']}"
                for msg in filtered_history
            ])
            user_prompt = f"【历史对话】\n{history_text}\n\n【当前用户问题】\n{task}"
        else:
            user_prompt = task

        tools = self.get_tools_for_llm()
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
                    if (
                        chunk.startswith("__DEBUG__:")
                        or chunk.startswith("__TOOL__:")
                        or chunk.startswith("__STATUS__:")
                        or chunk.startswith("__PROGRESS__:")
                        or chunk.startswith("__EVALUATION__:")
                    ):
                        yield chunk
                    else:
                        full_response = (full_response or "") + chunk
                        yield chunk
            else:
                audit_meta = {"session_id": session_id} if session_id else None
                response = await self.llm_service.chat(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    audit_meta=audit_meta,
                )
                full_response = response or ""

            if not regenerate_msg_id:
                self.context_manager.add_message(session_id, MessageRole.USER, task)
            self.context_manager.add_message(
                session_id, MessageRole.ASSISTANT, full_response or ""
            )
        finally:
            self.llm_service.reset_model()
