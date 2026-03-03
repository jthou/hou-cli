"""MediaWiki KanbanBoard 看板工具

提供对 MediaWiki KanbanBoard 扩展的常用操作封装：
- 列出当前用户可见的看板
- 获取单个看板详情（列、任务、里程碑）
- 在看板上创建 / 更新 / 删除任务
"""

from typing import Optional, Dict, Any, List

from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from backend.services.mediawiki_client_service import MediaWikiClientService
from backend.services.mediawiki_client_service.client import (
    MediaWikiClientError,
)


class KanbanBoardTool(Tool):
    """KanbanBoard 看板操作工具"""

    def __init__(self) -> None:
        parameters = [
            ToolParameter(
                name="operation",
                type="string",
                description=(
                    "操作类型："
                    "'list_boards'（看板列表）、"
                    "'get_board'（获取看板详情）、"
                    "'create_task'（创建任务）、"
                    "'update_task'（更新任务）、"
                    "'delete_task'（删除任务）、"
                    "'add_column'（新增列）、"
                    "'update_column'（更新列）、"
                    "'delete_column'（删除列）、"
                    "'reorder_columns'（列排序）、"
                    "'reorder_cards'（卡片排序）、"
                    "'get_milestones'（获取里程碑）、"
                    "'create_milestone'（创建里程碑）、"
                    "'update_milestone'（更新里程碑）、"
                    "'delete_milestone'（删除里程碑）、"
                    "'hide_board'（隐藏看板）、"
                    "'archive_board'（归档看板）、"
                    "'delete_board'（删除看板）、"
                    "'restore_board'（恢复看板）、"
                    "'get_stats'（统计）、"
                    "'get_history'（任务历史）"
                ),
                required=True,
                enum=[
                    "list_boards",
                    "get_board",
                    "create_task",
                    "update_task",
                    "delete_task",
                    "add_column",
                    "update_column",
                    "delete_column",
                    "reorder_columns",
                    "reorder_cards",
                    "get_milestones",
                    "create_milestone",
                    "update_milestone",
                    "delete_milestone",
                    "hide_board",
                    "archive_board",
                    "delete_board",
                    "restore_board",
                    "get_stats",
                    "get_history",
                ],
            ),
            ToolParameter(
                name="board_id",
                type="integer",
                description="看板 ID（get_board / create_task / delete_task 必需）",
                required=False,
            ),
            ToolParameter(
                name="filter_status",
                type="string",
                description=(
                    "看板筛选状态，仅 list_boards 使用："
                    "active|hidden|archived|deleted|all，默认 active"
                ),
                required=False,
                default="active",
            ),
            ToolParameter(
                name="column_id",
                type="integer",
                description="列 ID（create_task 必需）",
                required=False,
            ),
            ToolParameter(
                name="task_id",
                type="integer",
                description="任务 ID（update_task / delete_task 必需）",
                required=False,
            ),
            ToolParameter(
                name="title",
                type="string",
                description="任务标题（create_task 必需，update_task 可选）",
                required=False,
            ),
            ToolParameter(
                name="description",
                type="string",
                description="任务描述（可选）",
                required=False,
            ),
            ToolParameter(
                name="priority",
                type="string",
                description=(
                    "任务优先级：low|medium|high|urgent，"
                    "默认 medium"
                ),
                required=False,
                default="medium",
                enum=["low", "medium", "high", "urgent"],
            ),
            ToolParameter(
                name="due_date",
                type="string",
                description="任务截止日期，字符串形式（可选，例如 2026-03-10）",
                required=False,
            ),
            ToolParameter(
                name="status_id",
                type="integer",
                description="列 ID，update_task 时传入可移动任务到该列",
                required=False,
            ),
            # 列操作相关
            ToolParameter(
                name="column_name",
                type="string",
                description="列名称（add_column 必需，update_column 可选）",
                required=False,
            ),
            ToolParameter(
                name="column_description",
                type="string",
                description="列描述（可选，仅后端记录）",
                required=False,
            ),
            ToolParameter(
                name="column_color",
                type="string",
                description="列颜色，形如 #3498db（可选）",
                required=False,
            ),
            ToolParameter(
                name="column_width",
                type="integer",
                description="列宽度（像素，可选，默认 300）",
                required=False,
            ),
            ToolParameter(
                name="column_max_cards",
                type="integer",
                description="列最大卡片数（可选，0 表示无限制）",
                required=False,
            ),
            ToolParameter(
                name="column_wip_limit",
                type="integer",
                description="列 WIP 限制（可选，0 表示无限制）",
                required=False,
            ),
            ToolParameter(
                name="column_position",
                type="integer",
                description="列插入位置（add_column 可选，-1 表示末尾）",
                required=False,
            ),
            ToolParameter(
                name="move_cards_to",
                type="integer",
                description="删除列时卡片移动到的列 ID（0 表示一并删除）",
                required=False,
            ),
            ToolParameter(
                name="column_orders",
                type="string",
                description=(
                    "列排序 JSON（reorder_columns 使用），"
                    "例如: "
                    "[{\"column_id\":1,\"order\":1},{\"column_id\":2,\"order\":2}]"
                ),
                required=False,
            ),
            ToolParameter(
                name="card_orders",
                type="string",
                description=(
                    "卡片排序 JSON（reorder_cards 使用），"
                    "例如: "
                    "[{\"card_id\":1,\"column_id\":2,\"order\":1}]"
                ),
                required=False,
            ),
            # 里程碑
            ToolParameter(
                name="milestone_id",
                type="integer",
                description="里程碑 ID（update_milestone / delete_milestone 必需）",
                required=False,
            ),
            ToolParameter(
                name="milestone_name",
                type="string",
                description="里程碑名称（create_milestone 必需，update 可选）",
                required=False,
            ),
            ToolParameter(
                name="milestone_description",
                type="string",
                description="里程碑描述（可选）",
                required=False,
            ),
            ToolParameter(
                name="start_date",
                type="string",
                description="开始日期（可选，YYYY-MM-DD）",
                required=False,
            ),
            ToolParameter(
                name="end_date",
                type="string",
                description="结束日期（可选，YYYY-MM-DD）",
                required=False,
            ),
            ToolParameter(
                name="milestone_color",
                type="string",
                description="里程碑颜色（可选）",
                required=False,
            ),
            ToolParameter(
                name="time_range",
                type="string",
                description="统计时间范围（get_stats），如 week 或 month",
                required=False,
            ),
            # 任务历史
            ToolParameter(
                name="history_limit",
                type="integer",
                description="任务历史条数限制（get_history，可选）",
                required=False,
            ),
            ToolParameter(
                name="history_offset",
                type="integer",
                description="任务历史偏移量（get_history，可选）",
                required=False,
            ),
        ]

        super().__init__(
            name="kanban_board",
            description=(
                "管理 MediaWiki KanbanBoard 看板与任务："
                "列出看板、读取看板详情、创建/更新/删除任务。"
                "依赖已配置好的 MediaWiki 连接与 KanbanBoard 扩展。"
            ),
            parameters=parameters,
            requires_reasoning=False,
            requires_code=False,
            recommended_model="chat",
            can_parallel=True,
        )

        self._client: Optional[MediaWikiClientService] = None

    def _get_client(self) -> MediaWikiClientService:
        """获取 MediaWiki 客户端实例（延迟初始化）"""
        if self._client is None:
            try:
                self._client = MediaWikiClientService()
                self._client.connect()
            except Exception as exc:
                raise RuntimeError(
                    "MediaWiki Kanban 客户端初始化失败: "
                    f"{exc}. 请检查 MEDIAWIKI_* 环境变量配置。"
                )
        return self._client

    def execute(self, **kwargs: Any) -> ToolResult:
        """执行看板相关操作"""
        operation = kwargs.get("operation")
        if not operation:
            return ToolResult(success=False, error="operation 参数是必需的")

        try:
            client = self._get_client()
        except RuntimeError as exc:
            return ToolResult(success=False, error=str(exc))

        try:
            if operation == "list_boards":
                return self._handle_list_boards(client, kwargs)
            if operation == "get_board":
                return self._handle_get_board(client, kwargs)
            if operation == "create_task":
                return self._handle_create_task(client, kwargs)
            if operation == "update_task":
                return self._handle_update_task(client, kwargs)
            if operation == "delete_task":
                return self._handle_delete_task(client, kwargs)
            if operation == "add_column":
                return self._handle_add_column(client, kwargs)
            if operation == "update_column":
                return self._handle_update_column(client, kwargs)
            if operation == "delete_column":
                return self._handle_delete_column(client, kwargs)
            if operation == "reorder_columns":
                return self._handle_reorder_columns(client, kwargs)
            if operation == "reorder_cards":
                return self._handle_reorder_cards(client, kwargs)
            if operation == "get_milestones":
                return self._handle_get_milestones(client, kwargs)
            if operation == "create_milestone":
                return self._handle_create_milestone(client, kwargs)
            if operation == "update_milestone":
                return self._handle_update_milestone(client, kwargs)
            if operation == "delete_milestone":
                return self._handle_delete_milestone(client, kwargs)
            if operation == "hide_board":
                return self._handle_change_board_status(
                    client, kwargs, "hideboard", "隐藏"
                )
            if operation == "archive_board":
                return self._handle_change_board_status(
                    client, kwargs, "archiveboard", "归档"
                )
            if operation == "delete_board":
                return self._handle_change_board_status(
                    client, kwargs, "deleteboard", "删除"
                )
            if operation == "restore_board":
                return self._handle_change_board_status(
                    client, kwargs, "restoreboard", "恢复"
                )
            if operation == "get_stats":
                return self._handle_get_stats(client, kwargs)
            if operation == "get_history":
                return self._handle_get_history(client, kwargs)

            return ToolResult(
                success=False,
                error=f"未知 operation：{operation}",
            )
        except MediaWikiClientError as exc:
            return ToolResult(success=False, error=f"看板操作失败: {exc}")
        except Exception as exc:
            return ToolResult(success=False, error=f"看板操作异常: {exc}")

    # ------------------------------------------------------------------
    # 具体操作实现
    # ------------------------------------------------------------------

    def _call_api(
        self,
        client: MediaWikiClientService,
        kanban_action: str,
        **params: Any,
    ) -> Dict[str, Any]:
        """直接调用 MediaWiki kanban API。"""
        client._ensure_connected()  # type: ignore[attr-defined]
        result = client.site.api("kanban", kanban_action=kanban_action, **params)
        if "error" in result:
            err = result.get("error", {}).get("info", str(result))
            raise MediaWikiClientError(err)
        return result

    def _handle_list_boards(
        self,
        client: MediaWikiClientService,
        kwargs: Dict[str, Any],
    ) -> ToolResult:
        filter_status = kwargs.get("filter_status") or "active"
        boards = client.kanban_get_boards(filter_status=filter_status)
        summary = f"共 {len(boards)} 个看板（状态过滤：{filter_status}）。"
        return ToolResult(
            success=True,
            data={
                "operation": "list_boards",
                "filter_status": filter_status,
                "count": len(boards),
                "boards": boards,
                "summary": summary,
            },
        )

    def _handle_get_board(
        self,
        client: MediaWikiClientService,
        kwargs: Dict[str, Any],
    ) -> ToolResult:
        board_id = kwargs.get("board_id")
        if not board_id:
            return ToolResult(
                success=False,
                error="get_board 操作需要 board_id 参数",
            )
        board = client.kanban_get_board(int(board_id))
        columns: List[Dict[str, Any]] = board.get("columns", [])  # type: ignore[assignment]
        task_count = sum(
            len(col.get("cards", []) or []) for col in columns
        )
        summary = (
            f"看板「{board.get('board_name', board_id)}」"
            f"包含 {len(columns)} 列、{task_count} 个任务。"
        )
        return ToolResult(
            success=True,
            data={
                "operation": "get_board",
                "board_id": board_id,
                "board": board,
                "summary": summary,
            },
        )

    def _handle_create_task(
        self,
        client: MediaWikiClientService,
        kwargs: Dict[str, Any],
    ) -> ToolResult:
        board_id = kwargs.get("board_id")
        column_id = kwargs.get("column_id")
        title = (kwargs.get("title") or "").strip()

        if not board_id:
            return ToolResult(
                success=False,
                error="create_task 操作需要 board_id 参数",
            )
        if not column_id:
            return ToolResult(
                success=False,
                error="create_task 操作需要 column_id 参数",
            )
        if not title:
            return ToolResult(
                success=False,
                error="create_task 操作需要 title 参数",
            )

        description = (kwargs.get("description") or "").strip()
        priority = kwargs.get("priority") or "medium"
        due_date = (kwargs.get("due_date") or "").strip() or None

        task_id = client.kanban_create_task(
            board_id=int(board_id),
            column_id=int(column_id),
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
        )
        summary = f"已在看板 {board_id} 的列 {column_id} 中创建任务 #{task_id}「{title}」。"
        return ToolResult(
            success=True,
            data={
                "operation": "create_task",
                "board_id": board_id,
                "column_id": column_id,
                "task_id": task_id,
                "title": title,
                "priority": priority,
                "due_date": due_date,
                "summary": summary,
            },
        )
    def _handle_update_task(
        self,
        client: MediaWikiClientService,
        kwargs: Dict[str, Any],
    ) -> ToolResult:
        task_id = kwargs.get("task_id")
        if not task_id:
            return ToolResult(
                success=False,
                error="update_task 操作需要 task_id 参数",
            )

        title = kwargs.get("title")
        description = kwargs.get("description")
        priority = kwargs.get("priority")
        status_id = kwargs.get("status_id")
        due_date = kwargs.get("due_date")

        client.kanban_update_task(
            task_id=int(task_id),
            title=title,
            description=description,
            priority=priority,
            status_id=int(status_id) if status_id is not None else None,
            due_date=due_date,
        )
        summary = f"已更新任务 #{task_id}。"
        return ToolResult(
            success=True,
            data={
                "operation": "update_task",
                "task_id": task_id,
                "summary": summary,
            },
        )

    def _handle_delete_task(
        self,
        client: MediaWikiClientService,
        kwargs: Dict[str, Any],
    ) -> ToolResult:
        board_id = kwargs.get("board_id")
        task_id = kwargs.get("task_id")
        if not board_id:
            return ToolResult(
                success=False,
                error="delete_task 操作需要 board_id 参数",
            )
        if not task_id:
            return ToolResult(
                success=False,
                error="delete_task 操作需要 task_id 参数",
            )

        client.kanban_delete_task(
            board_id=int(board_id),
            task_id=int(task_id),
        )
        summary = f"已在看板 {board_id} 中删除任务 #{task_id}。"
        return ToolResult(
            success=True,
            data={
                "operation": "delete_task",
                "board_id": board_id,
                "task_id": task_id,
                "summary": summary,
            },
        )

    # ---------------- 列操作 ----------------

    def _handle_add_column(
        self,
        client: MediaWikiClientService,
        kwargs: Dict[str, Any],
    ) -> ToolResult:
        board_id = kwargs.get("board_id")
        name = (kwargs.get("column_name") or "").strip()
        if not board_id:
            return ToolResult(
                success=False,
                error="add_column 操作需要 board_id 参数",
            )
        if not name:
            return ToolResult(
                success=False,
                error="add_column 操作需要 column_name 参数",
            )
        params: Dict[str, Any] = {
            "board_id": int(board_id),
            "name": name,
        }
        desc = kwargs.get("column_description")
        if desc:
            params["description"] = desc
        color = kwargs.get("column_color")
        if color:
            params["color"] = color
        pos = kwargs.get("column_position")
        if pos is not None:
            params["position"] = int(pos)
        width = kwargs.get("column_width")
        if width is not None:
            params["width"] = int(width)
        max_cards = kwargs.get("column_max_cards")
        if max_cards is not None:
            params["max_cards"] = int(max_cards)
        wip = kwargs.get("column_wip_limit")
        if wip is not None:
            params["wip_limit"] = int(wip)

        data = self._call_api(client, "addcolumn", **params)
        column = data.get("column")
        summary = f"已在看板 {board_id} 中新增列「{name}」。"
        return ToolResult(
            success=True,
            data={
                "operation": "add_column",
                "board_id": board_id,
                "column": column,
                "summary": summary,
            },
        )

    def _handle_update_column(
        self,
        client: MediaWikiClientService,
        kwargs: Dict[str, Any],
    ) -> ToolResult:
        board_id = kwargs.get("board_id")
        column_id = kwargs.get("column_id")
        if not board_id or not column_id:
            return ToolResult(
                success=False,
                error="update_column 操作需要 board_id 和 column_id 参数",
            )
        params: Dict[str, Any] = {
            "board_id": int(board_id),
            "column_id": int(column_id),
        }
        if kwargs.get("column_name") is not None:
            params["name"] = kwargs["column_name"]
        if kwargs.get("column_description") is not None:
            params["description"] = kwargs["column_description"]
        if kwargs.get("column_color") is not None:
            params["color"] = kwargs["column_color"]
        if kwargs.get("column_width") is not None:
            params["width"] = int(kwargs["column_width"])
        if kwargs.get("column_max_cards") is not None:
            params["max_cards"] = int(kwargs["column_max_cards"])
        if kwargs.get("column_wip_limit") is not None:
            params["wip_limit"] = int(kwargs["column_wip_limit"])

        self._call_api(client, "updatecolumn", **params)
        summary = f"已更新看板 {board_id} 的列 {column_id}。"
        return ToolResult(
            success=True,
            data={
                "operation": "update_column",
                "board_id": board_id,
                "column_id": column_id,
                "summary": summary,
            },
        )

    def _handle_delete_column(
        self,
        client: MediaWikiClientService,
        kwargs: Dict[str, Any],
    ) -> ToolResult:
        board_id = kwargs.get("board_id")
        column_id = kwargs.get("column_id")
        if not board_id or not column_id:
            return ToolResult(
                success=False,
                error="delete_column 操作需要 board_id 和 column_id 参数",
            )
        params: Dict[str, Any] = {
            "board_id": int(board_id),
            "column_id": int(column_id),
        }
        if kwargs.get("move_cards_to") is not None:
            params["move_cards_to"] = int(kwargs["move_cards_to"])
        self._call_api(client, "deletecolumn", **params)
        summary = f"已删除看板 {board_id} 的列 {column_id}。"
        return ToolResult(
            success=True,
            data={
                "operation": "delete_column",
                "board_id": board_id,
                "column_id": column_id,
                "summary": summary,
            },
        )

    def _handle_reorder_columns(
        self,
        client: MediaWikiClientService,
        kwargs: Dict[str, Any],
    ) -> ToolResult:
        board_id = kwargs.get("board_id")
        orders = kwargs.get("column_orders")
        if not board_id or not orders:
            return ToolResult(
                success=False,
                error="reorder_columns 操作需要 board_id 和 column_orders 参数",
            )
        self._call_api(
            client,
            "reordercolumns",
            board_id=int(board_id),
            column_orders=str(orders),
        )
        summary = f"已更新看板 {board_id} 的列顺序。"
        return ToolResult(
            success=True,
            data={
                "operation": "reorder_columns",
                "board_id": board_id,
                "summary": summary,
            },
        )

    def _handle_reorder_cards(
        self,
        client: MediaWikiClientService,
        kwargs: Dict[str, Any],
    ) -> ToolResult:
        board_id = kwargs.get("board_id")
        orders = kwargs.get("card_orders")
        if not board_id or not orders:
            return ToolResult(
                success=False,
                error="reorder_cards 操作需要 board_id 和 card_orders 参数",
            )
        self._call_api(
            client,
            "reordercards",
            board_id=int(board_id),
            card_orders=str(orders),
        )
        summary = f"已更新看板 {board_id} 的卡片顺序。"
        return ToolResult(
            success=True,
            data={
                "operation": "reorder_cards",
                "board_id": board_id,
                "summary": summary,
            },
        )

    # ---------------- 里程碑 ----------------

    def _handle_get_milestones(
        self,
        client: MediaWikiClientService,
        kwargs: Dict[str, Any],
    ) -> ToolResult:
        board_id = kwargs.get("board_id")
        if not board_id:
            return ToolResult(
                success=False,
                error="get_milestones 操作需要 board_id 参数",
            )
        data = self._call_api(
            client,
            "getmilestones",
            board_id=int(board_id),
        )
        milestones = data.get("milestones", [])
        summary = f"看板 {board_id} 有 {len(milestones)} 个里程碑。"
        return ToolResult(
            success=True,
            data={
                "operation": "get_milestones",
                "board_id": board_id,
                "milestones": milestones,
                "summary": summary,
            },
        )

    def _handle_create_milestone(
        self,
        client: MediaWikiClientService,
        kwargs: Dict[str, Any],
    ) -> ToolResult:
        board_id = kwargs.get("board_id")
        name = (kwargs.get("milestone_name") or "").strip()
        if not board_id:
            return ToolResult(
                success=False,
                error="create_milestone 操作需要 board_id 参数",
            )
        if not name:
            return ToolResult(
                success=False,
                error="create_milestone 操作需要 milestone_name 参数",
            )
        params: Dict[str, Any] = {
            "board_id": int(board_id),
            "name": name,
        }
        if kwargs.get("milestone_description"):
            params["description"] = kwargs["milestone_description"]
        if kwargs.get("start_date"):
            params["start_date"] = kwargs["start_date"]
        if kwargs.get("end_date"):
            params["end_date"] = kwargs["end_date"]
        if kwargs.get("milestone_color"):
            params["color"] = kwargs["milestone_color"]

        data = self._call_api(client, "createmilestone", **params)
        milestone = data.get("milestone")
        summary = f"已在看板 {board_id} 创建里程碑「{name}」。"
        return ToolResult(
            success=True,
            data={
                "operation": "create_milestone",
                "board_id": board_id,
                "milestone": milestone,
                "summary": summary,
            },
        )

    def _handle_update_milestone(
        self,
        client: MediaWikiClientService,
        kwargs: Dict[str, Any],
    ) -> ToolResult:
        board_id = kwargs.get("board_id")
        milestone_id = kwargs.get("milestone_id")
        if not board_id or not milestone_id:
            return ToolResult(
                success=False,
                error=(
                    "update_milestone 操作需要 "
                    "board_id 和 milestone_id 参数"
                ),
            )
        params: Dict[str, Any] = {
            "board_id": int(board_id),
            "milestone_id": int(milestone_id),
        }
        if kwargs.get("milestone_name") is not None:
            params["name"] = kwargs["milestone_name"]
        if kwargs.get("milestone_description") is not None:
            params["description"] = kwargs["milestone_description"]
        if kwargs.get("start_date") is not None:
            params["start_date"] = kwargs["start_date"]
        if kwargs.get("end_date") is not None:
            params["end_date"] = kwargs["end_date"]
        if kwargs.get("milestone_color") is not None:
            params["color"] = kwargs["milestone_color"]
        if kwargs.get("status") is not None:
            params["status"] = kwargs["status"]

        self._call_api(client, "updatemilestone", **params)
        summary = (
            f"已更新看板 {board_id} 的里程碑 {milestone_id}。"
        )
        return ToolResult(
            success=True,
            data={
                "operation": "update_milestone",
                "board_id": board_id,
                "milestone_id": milestone_id,
                "summary": summary,
            },
        )

    def _handle_delete_milestone(
        self,
        client: MediaWikiClientService,
        kwargs: Dict[str, Any],
    ) -> ToolResult:
        board_id = kwargs.get("board_id")
        milestone_id = kwargs.get("milestone_id")
        if not board_id or not milestone_id:
            return ToolResult(
                success=False,
                error=(
                    "delete_milestone 操作需要 "
                    "board_id 和 milestone_id 参数"
                ),
            )
        self._call_api(
            client,
            "deletemilestone",
            board_id=int(board_id),
            milestone_id=int(milestone_id),
        )
        summary = (
            f"已删除看板 {board_id} 的里程碑 {milestone_id}。"
        )
        return ToolResult(
            success=True,
            data={
                "operation": "delete_milestone",
                "board_id": board_id,
                "milestone_id": milestone_id,
                "summary": summary,
            },
        )

    # ---------------- 看板状态 / 统计 / 历史 ----------------

    def _handle_change_board_status(
        self,
        client: MediaWikiClientService,
        kwargs: Dict[str, Any],
        action: str,
        action_label: str,
    ) -> ToolResult:
        board_id = kwargs.get("board_id")
        if not board_id:
            return ToolResult(
                success=False,
                error=f"{action_label} 看板需要 board_id 参数",
            )
        self._call_api(
            client,
            action,
            board_id=int(board_id),
        )
        summary = f"已{action_label}看板 {board_id}。"
        return ToolResult(
            success=True,
            data={
                "operation": action,
                "board_id": board_id,
                "summary": summary,
            },
        )

    def _handle_get_stats(
        self,
        client: MediaWikiClientService,
        kwargs: Dict[str, Any],
    ) -> ToolResult:
        board_id = kwargs.get("board_id")
        params: Dict[str, Any] = {}
        if board_id:
            params["board_id"] = int(board_id)
        if kwargs.get("time_range"):
            params["time_range"] = kwargs["time_range"]
        if kwargs.get("start_date"):
            params["start_date"] = kwargs["start_date"]
        if kwargs.get("end_date"):
            params["end_date"] = kwargs["end_date"]
        data = self._call_api(client, "getstats", **params)
        summary = (
            f"统计范围 {data.get('start_date')} ~ "
            f"{data.get('end_date')}，包含 {len(data.get('days', []))} 天数据。"
        )
        return ToolResult(
            success=True,
            data={
                "operation": "get_stats",
                "board_id": board_id,
                "stats": data,
                "summary": summary,
            },
        )

    def _handle_get_history(
        self,
        client: MediaWikiClientService,
        kwargs: Dict[str, Any],
    ) -> ToolResult:
        task_id = kwargs.get("task_id")
        if not task_id:
            return ToolResult(
                success=False,
                error="get_history 操作需要 task_id 参数",
            )
        params: Dict[str, Any] = {
            "task_id": int(task_id),
        }
        if kwargs.get("history_limit") is not None:
            params["limit"] = int(kwargs["history_limit"])
        if kwargs.get("history_offset") is not None:
            params["offset"] = int(kwargs["history_offset"])
        data = self._call_api(client, "gethistory", **params)
        history = data.get("history", [])
        summary = f"任务 {task_id} 有 {len(history)} 条历史记录。"
        return ToolResult(
            success=True,
            data={
                "operation": "get_history",
                "task_id": task_id,
                "history": history,
                "summary": summary,
            },
        )

