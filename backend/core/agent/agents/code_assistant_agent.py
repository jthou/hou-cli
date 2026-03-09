"""
代码助手 Agent - 独立的编程 Agent，拥有明确的工具注册与执行逻辑。

与通用 orchestrator 不同，本 Agent 专门负责「写代码并执行代码」场景，
配备 execute_code、exec、process、file_search 工具，具备独立的工具注册机制。
"""
import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from backend.core.context.models import MessageRole
from backend.core.agent.tools.registry import ToolRegistry
from backend.core.agent.agent_tools_registry import (
    CODE_ASSISTANT_TOOLS,
    get_tools_for_llm_by_agent,
)
from backend.core.agent.system_prompt_templates import CODE_ASSISTANT_SYSTEM_PROMPT
from backend.core.agent.agents.base_context_agent import BaseContextAgent

logger = logging.getLogger(__name__)


class CodeAssistantAgent(BaseContextAgent):
    """代码助手 Agent：专注写代码、执行代码解决问题。

    工具注册机制：
    - 工具名称在 agent_tools_registry.CODE_ASSISTANT_TOOLS 中定义
    - 工具实例从 ToolRegistry 获取（由 orchestrator 在启动时注册）
    - 若工具未注册，本 Agent 会尝试补充注册，并记录诊断日志
    """

    AGENT_ID = "code_assistant"
    TOOL_NAMES = CODE_ASSISTANT_TOOLS

    def __init__(
        self,
        tool_registry: ToolRegistry,
        llm_service: Any,
        context_manager: Any,
    ):
        super().__init__(tool_registry, llm_service, context_manager)
        self._tools_registered = False

    def _ensure_tools_registered(self) -> None:
        """确保代码助手所需工具已注册；若缺失则尝试补充注册。"""
        if self._tools_registered:
            return
        missing = [
            name
            for name in self.TOOL_NAMES
            if self.tool_registry.get_tool(name) is None
        ]
        if not missing:
            self._tools_registered = True
            return

        logger.info(
            "CodeAssistantAgent: 部分工具未注册，尝试补充注册: %s",
            missing,
        )
        for name in missing:
            try:
                if name == "execute_code":
                    from backend.core.agent.tools.builtin.code_executor_tool import (
                        CodeExecutorTool,
                    )
                    self.tool_registry.register(CodeExecutorTool())
                elif name == "exec":
                    from backend.core.agent.tools.builtin.exec_tool import ExecTool
                    self.tool_registry.register(ExecTool())
                elif name == "process":
                    from backend.core.agent.tools.builtin.process_tool import (
                        ProcessTool,
                    )
                    self.tool_registry.register(ProcessTool())
                elif name == "file_search":
                    from backend.core.agent.tools.builtin.file_search_tool import (
                        FileSearchTool,
                    )
                    self.tool_registry.register(FileSearchTool())
            except Exception as e:
                logger.warning(
                    "CodeAssistantAgent: 无法注册工具 %s: %s",
                    name,
                    e,
                )
        self._tools_registered = True

    def get_tools_for_llm(self) -> List[dict]:
        """获取供 LLM Function Calling 使用的工具定义列表。"""
        self._ensure_tools_registered()
        all_tools = self.tool_registry.get_tools_for_llm()
        tools = get_tools_for_llm_by_agent(self.AGENT_ID, all_tools)
        if not tools:
            registered = self.tool_registry.list_tools()
            logger.warning(
                "CodeAssistantAgent: 工具列表为空！期望: %s，已注册: %s",
                self.TOOL_NAMES,
                registered,
            )
        return tools

    def _format_tool_results_markdown(
        self, tool_results: List[Dict[str, Any]]
    ) -> str:
        """将工具执行结果格式化为 Markdown，追加到消息内容以便持久化。"""
        if not tool_results:
            return ""
        lines = ["\n\n## 执行结果\n"]
        for i, tc in enumerate(tool_results, 1):
            name = tc.get("name", "tool")
            args = tc.get("args") or {}
            result = tc.get("result") or {}
            err = tc.get("error")
            success = tc.get("success", False)
            lines.append(f"\n### {i}. {name}\n")
            if name == "execute_code":
                code = args.get("code", "")
                lang = args.get("language", "python")
                if code:
                    lines.append(f"```{lang}\n{code}\n```\n")
                if success and result:
                    out = result.get("output", "")
                    if out:
                        lines.append(f"**输出：**\n```\n{out}\n```\n")
                if err or result.get("error"):
                    lines.append(f"**错误：**\n```\n{err or result.get('error', '')}\n```\n")
            elif name == "exec":
                cmd = args.get("command", "")
                if cmd:
                    lines.append(f"`$ {cmd}`\n")
                if success and result:
                    out = result.get("output", "")
                    if out:
                        lines.append(f"**输出：**\n```\n{out}\n```\n")
                if err or result.get("error"):
                    lines.append(f"**错误：**\n```\n{err or result.get('error', '')}\n```\n")
            else:
                if success:
                    lines.append(f"```\n{json.dumps(result, ensure_ascii=False, indent=2)}\n```\n")
                if err:
                    lines.append(f"**错误：** {err}\n")
        return "".join(lines)

    async def stream_process(
        self,
        task: str,
        context: Optional[Dict[str, Any]],
        delegate: Any,
    ) -> AsyncIterator[str]:
        session_id = context.get("session_id") if context else None
        if not session_id:
            session_id = self.context_manager.create_session(
                metadata={"type": "code_assistant"}
            )

        history = self.context_manager.get_messages_for_llm(
            session_id, max_messages=None, max_tokens=None
        )
        system_prompt = CODE_ASSISTANT_SYSTEM_PROMPT
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

        # 用户明确要求「执行」或消息含代码块时，追加强制执行提示
        exec_keywords = ("执行", "运行", "执行看看", "运行看看", "跑一下", "试试")
        has_code_block = "```" in (task or "")
        if any(kw in (task or "") for kw in exec_keywords) or has_code_block:
            user_prompt = (
                user_prompt
                + "\n\n【重要】用户要求执行代码。你必须立即调用 execute_code 或 exec 工具执行，"
                "不要只给文档、步骤或示例。直接调用工具并返回执行结果。"
            )

        tools = self.get_tools_for_llm()

        selected_model = await delegate._select_model(task, context=context)
        if selected_model != self.llm_service.model:
            self.llm_service.set_model(selected_model)

        full_response = ""
        tool_results: List[Dict[str, Any]] = []
        try:
            if tools:
                async for chunk in delegate._chat_with_tools_stream(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    tools=tools,
                    planning_files=None,
                    session_id=session_id,
                    context=context,
                ):
                    if chunk.startswith("__TOOL__:"):
                        try:
                            data = json.loads(chunk[9:].strip())
                            if data.get("name"):
                                tool_results.append(data)
                        except (json.JSONDecodeError, TypeError):
                            pass
                        yield chunk
                    elif (
                        chunk.startswith("__DEBUG__:")
                        or chunk.startswith("__STATUS__:")
                        or chunk.startswith("__PROGRESS__:")
                    ):
                        yield chunk
                    else:
                        full_response = (full_response or "") + chunk
                        yield chunk
            else:
                audit_meta = {"session_id": session_id} if session_id else None
                async for chunk in self.llm_service.stream_chat(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    audit_meta=audit_meta,
                ):
                    full_response += chunk
                    yield chunk

            self.context_manager.add_message(session_id, MessageRole.USER, task)
            content_to_save = full_response or ""
            if tool_results:
                content_to_save += self._format_tool_results_markdown(tool_results)
            self.context_manager.add_message(
                session_id, MessageRole.ASSISTANT, content_to_save
            )
        finally:
            self.llm_service.reset_model()
