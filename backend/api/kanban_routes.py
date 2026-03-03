"""KanbanBoard 看板只读 API：列出看板、获取单个看板详情（列与卡片）。

前端用于展示 MediaWiki KanbanBoard 扩展中的看板数据。
写操作（创建/更新/删除任务、列等）目前由工具/后续接口负责。
"""

from typing import Optional

from fastapi import APIRouter

router = APIRouter()


def _get_client():
    """延迟导入 MediaWiki 客户端，避免启动时强依赖。"""
    from backend.services.mediawiki_client_service import MediaWikiClientService

    client = MediaWikiClientService()
    client.connect()
    return client


@router.get("/settings/kanban/boards")
async def list_kanban_boards(filter_status: str = "active"):
    """返回当前用户可见的看板列表。"""
    try:
        client = _get_client()
        boards = client.kanban_get_boards(filter_status=filter_status)
        return {
            "success": True,
            "filter_status": filter_status,
            "boards": boards,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "success": False,
            "error": str(e),
            "filter_status": filter_status,
            "boards": [],
        }


@router.get("/settings/kanban/board")
async def get_kanban_board(
    board_id: int,
    with_milestones: Optional[bool] = True,
):
    """返回单个看板的详细信息（列与卡片、里程碑等）。"""
    try:
        client = _get_client()
        board = client.kanban_get_board(board_id)
        if not with_milestones:
            board = dict(board)
            board.pop("milestones", None)
        return {
            "success": True,
            "board_id": board_id,
            "board": board,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "success": False,
            "error": str(e),
            "board_id": board_id,
            "board": None,
        }
