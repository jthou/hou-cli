"""心跳监控相关路由"""
from fastapi import APIRouter
from shared.debug_utils import debug_log

router = APIRouter()

@router.get("/heartbeat/status")
async def get_heartbeat_status():
    """获取心跳监控状态"""
    try:
        from backend.infrastructure.monitoring.heartbeat import get_heartbeat_monitor
        monitor = get_heartbeat_monitor()
        status = monitor.get_status()
        return {
            "success": True,
            "status": status
        }
    except Exception as e:
        debug_log(f"Failed to get heartbeat status: {str(e)}", level="error")
        return {
            "success": False,
            "error": str(e)
        }
