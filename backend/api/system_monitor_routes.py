"""系统监控API路由"""
import json
import logging
import re
from pathlib import Path

from fastapi import APIRouter, Query

from backend.externals.system_monitor import system_monitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["system-monitor"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DISK_REPORT_JSON = PROJECT_ROOT / "docs" / "disk_report.json"
DISK_REPORT_TXT_CANDIDATES = [
    PROJECT_ROOT / "docs" / "disk_report.txt",
    PROJECT_ROOT / "report.txt",
]


def _parse_disk_report_txt(content: str) -> dict | None:
    """解析 make disk-scan 输出的 txt 报告，提取 df 已用、items"""
    total_used = 0.0
    items = []
    # df 已用: 809.1 GB
    m = re.search(r"df\s*已用:\s*([\d.]+)\s*GB", content)
    if m:
        total_used = float(m.group(1))
    # 行格式: "    147.67 GB ( 18.3%)  /System/Volumes/Data/opt"
    pattern = re.compile(r"^\s*([\d.]+)\s+GB\s+\(\s*[\d.]+%\s*\)\s+(.+)$", re.MULTILINE)
    for match in pattern.finditer(content):
        size_gb = float(match.group(1))
        path = match.group(2).strip()
        if path and not path.startswith("="):
            items.append({"path": path, "category": path.split("/")[-1] or path, "size_gb": round(size_gb, 2)})
    if not items:
        return None
    large_items = [x for x in items if x["size_gb"] >= 1]
    scanned_total = sum(x["size_gb"] for x in items)
    return {
        "total_used_gb": round(total_used, 2),
        "scanned_total_gb": round(scanned_total, 2),
        "user_only": False,
        "items": items,
        "large_items": large_items,
        "source": "make disk-scan (txt)",
    }


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


def _add_partitions(data: dict) -> None:
    """为报告数据补充分区信息"""
    try:
        partitions = system_monitor._get_disk_info()
        data["partitions"] = [
            {
                "device": p.get("device"),
                "mountpoint": p.get("mountpoint"),
                "total_gb": round(p.get("total", 0) / (1024**3), 2),
                "used_gb": round(p.get("used", 0) / (1024**3), 2),
                "free_gb": round(p.get("free", 0) / (1024**3), 2),
                "percent": p.get("percent", 0),
            }
            for p in (partitions or [])
        ]
    except Exception:
        data.setdefault("partitions", [])


@router.get("/disk-scan-report")
async def get_disk_scan_report():
    """获取 make disk-scan 生成的报告（优先 JSON，否则解析 txt）"""
    try:
        if DISK_REPORT_JSON.exists():
            raw = DISK_REPORT_JSON.read_text(encoding="utf-8")
            data = json.loads(raw)
            _add_partitions(data)
            data["source"] = "make disk-scan"
            return {"success": True, "data": data}
        if DISK_REPORT_TXT.exists():
            content = DISK_REPORT_TXT.read_text(encoding="utf-8")
            data = _parse_disk_report_txt(content)
            if data:
                _add_partitions(data)
                return {"success": True, "data": data}
        return {"success": True, "data": None, "message": "暂无全盘扫描报告，请执行 make disk-scan"}
    except Exception as e:
        logger.warning(f"读取磁盘扫描报告失败: {e}")
        return {"success": False, "error": str(e), "data": None}


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