"""process 工具：管理 exec 启动的后台进程"""
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from backend.infrastructure.execution.process_registry import get_process_registry


class ProcessTool(Tool):
    """process 工具

    管理 exec 启动的后台进程：list/poll/log/kill/remove。
    """

    def __init__(self):
        parameters = [
            ToolParameter(
                name="action",
                type="string",
                description="list|poll|log|kill|remove",
                required=True,
                enum=["list", "poll", "log", "kill", "remove"]
            ),
            ToolParameter(
                name="session_id",
                type="string",
                description="会话 ID（list 时可选）",
                required=False
            ),
            ToolParameter(name="offset", type="integer", description="log 分页偏移", required=False),
            ToolParameter(name="limit", type="integer", description="log 行数", required=False),
        ]
        super().__init__(
            name="process",
            description=(
                "管理 exec 启动的后台进程。"
                "list/poll/log/kill/remove。"
            ),
            parameters=parameters
        )
        self.registry = get_process_registry()

    def execute(self, **kwargs) -> ToolResult:
        action = kwargs.get("action", "")
        session_id = kwargs.get("session_id", "")
        offset = kwargs.get("offset", 0) or 0
        limit = kwargs.get("limit", 100) or 100

        if not action:
            return ToolResult(success=False, error="action 参数必需")

        if action != "list" and not session_id:
            return ToolResult(
                success=False,
                error="session_id 在 list 以外操作时必需"
            )

        if action == "list":
            sessions = self.registry.list_running()
            items = [
                {
                    "session_id": s.id,
                    "command": (
                        s.command[:80] + "..." if len(s.command) > 80
                        else s.command
                    ),
                    "pid": s.pid,
                    "cwd": s.cwd,
                    "exited": s.exited,
                    "exit_code": s.exit_code,
                    "backgrounded": s.backgrounded
                }
                for s in sessions
            ]
            return ToolResult(
                success=True,
                data={"sessions": items, "count": len(items)}
            )

        session = self.registry.get(session_id)
        if not session:
            return ToolResult(success=False, error=f"会话不存在: {session_id}")

        if action == "poll":
            tail = self.registry.tail_output(session_id)
            return ToolResult(
                success=True,
                data={
                    "session_id": session_id,
                    "exited": session.exited,
                    "exit_code": session.exit_code,
                    "tail": tail
                }
            )

        if action == "log":
            lines = session.aggregated.splitlines()
            total = len(lines)
            start = max(0, offset)
            end = min(start + limit, total)
            chunk = "\n".join(lines[start:end])
            return ToolResult(
                success=True,
                data={
                    "session_id": session_id,
                    "output": chunk,
                    "offset": start,
                    "limit": limit,
                    "total_lines": total
                }
            )

        if action == "kill":
            if session.exited:
                return ToolResult(
                    success=False,
                    error="进程已退出，无需 kill"
                )
            if session.pid:
                try:
                    import os
                    import signal
                    os.kill(session.pid, signal.SIGTERM)
                    session.exited = True
                    session.exit_code = -15
                    return ToolResult(
                        success=True,
                        data={"session_id": session_id, "message": "已发送 SIGTERM"}
                    )
                except ProcessLookupError:
                    session.exited = True
                    session.exit_code = -1
                    return ToolResult(
                        success=True,
                        data={"session_id": session_id, "message": "进程已不存在"}
                    )
                except Exception as e:
                    return ToolResult(success=False, error=str(e))
            return ToolResult(success=False, error="无 pid 信息")

        if action == "remove":
            if not session.exited:
                return ToolResult(
                    success=False,
                    error="仅可移除已退出的会话"
                )
            ok = self.registry.remove(session_id)
            return ToolResult(
                success=ok,
                data={"session_id": session_id, "removed": ok}
            )

        return ToolResult(success=False, error=f"未知 action: {action}")
