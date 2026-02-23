"""系统监控API路由"""
from fastapi import APIRouter, Query
import logging

from backend.externals.system_monitor import system_monitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["system-monitor"])


@router.get("/load")
async def get_system_load():
    """获取系统负载信息"""
    try:
        data = system_monitor.get_system_load()
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        logger.error(f"获取系统负载失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/cpu")
async def get_cpu_info():
    """获取CPU信息"""
    try:
        data = system_monitor._get_cpu_info()
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        logger.error(f"获取CPU信息失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/memory")
async def get_memory_info():
    """获取内存信息"""
    try:
        data = system_monitor._get_memory_info()
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        logger.error(f"获取内存信息失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/processes")
async def get_top_processes(
    limit: int = Query(20, ge=1, le=100, description="返回进程数量限制")
):
    """获取Top进程信息"""
    try:
        data = system_monitor._get_top_processes(limit=limit)
        return {
            "success": True,
            "data": data,
            "count": len(data)
        }
    except Exception as e:
        logger.error(f"获取进程信息失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/disk")
async def get_disk_info():
    """获取磁盘信息"""
    try:
        data = system_monitor._get_disk_info()
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        logger.error(f"获取磁盘信息失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/network")
async def get_network_info():
    """获取网络信息"""
    try:
        data = system_monitor._get_network_info()
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        logger.error(f"获取网络信息失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }