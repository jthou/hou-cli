"""系统负载监控工具"""
import subprocess
import re
import psutil
import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class SystemMonitor:
    """系统监控工具类"""
    
    @staticmethod
    def get_system_load() -> Dict[str, Any]:
        """获取系统负载信息"""
        try:
            # 获取基础系统信息
            load_avg = SystemMonitor._get_load_average()
            cpu_info = SystemMonitor._get_cpu_info()
            memory_info = SystemMonitor._get_memory_info()
            disk_info = SystemMonitor._get_disk_info()
            network_info = SystemMonitor._get_network_info()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "load_average": load_avg,
                "cpu": cpu_info,
                "memory": memory_info,
                "disk": disk_info,
                "network": network_info,
                "processes": SystemMonitor._get_top_processes()
            }
        except Exception as e:
            logger.error(f"获取系统负载信息失败: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def _get_load_average() -> Dict[str, float]:
        """获取系统负载平均值"""
        try:
            # 使用 uptime 命令获取负载平均值
            cmd = ['uptime']
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                output = result.stdout.strip()
                # 解析 "load averages: 1.23, 2.34, 3.45" 格式
                pattern = r'load averages?: ([\d.]+), ([\d.]+), ([\d.]+)'
                match = re.search(pattern, output)
                if match:
                    return {
                        "1min": float(match.group(1)),
                        "5min": float(match.group(2)),
                        "15min": float(match.group(3))
                    }
            # 备用方案：使用 psutil
            load_avg = psutil.getloadavg()
            return {
                "1min": load_avg[0],
                "5min": load_avg[1],
                "15min": load_avg[2]
            }
        except Exception as e:
            logger.error(f"获取负载平均值失败: {e}")
            return {"1min": 0.0, "5min": 0.0, "15min": 0.0}
    
    @staticmethod
    def _get_cpu_info() -> Dict[str, Any]:
        """获取CPU信息"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1, percpu=False)
            
            # CPU逻辑核心数
            cpu_count_logical = psutil.cpu_count(logical=True)
            cpu_count_physical = psutil.cpu_count(logical=False)
            
            # CPU频率信息
            try:
                cpu_freq = psutil.cpu_freq()
                cpu_freq_info = {
                    "current": cpu_freq.current if cpu_freq else 0,
                    "min": cpu_freq.min if cpu_freq else 0,
                    "max": cpu_freq.max if cpu_freq else 0
                }
            except Exception:
                cpu_freq_info = {"current": 0, "min": 0, "max": 0}
            
            return {
                "percent": cpu_percent,
                "count_logical": cpu_count_logical,
                "count_physical": cpu_count_physical,
                "frequency": cpu_freq_info
            }
        except Exception as e:
            logger.error(f"获取CPU信息失败: {e}")
            return {
                "percent": 0.0,
                "count_logical": 0,
                "count_physical": 0,
                "frequency": {"current": 0, "min": 0, "max": 0}
            }
    
    @staticmethod
    def _get_memory_info() -> Dict[str, Any]:
        """获取内存信息"""
        try:
            virtual_mem = psutil.virtual_memory()
            swap_mem = psutil.swap_memory()
            
            return {
                "virtual": {
                    "total": virtual_mem.total,
                    "available": virtual_mem.available,
                    "used": virtual_mem.used,
                    "free": virtual_mem.free,
                    "percent": virtual_mem.percent,
                    "buffers": getattr(virtual_mem, 'buffers', 0),
                    "cached": getattr(virtual_mem, 'cached', 0)
                },
                "swap": {
                    "total": swap_mem.total,
                    "used": swap_mem.used,
                    "free": swap_mem.free,
                    "percent": swap_mem.percent
                }
            }
        except Exception as e:
            logger.error(f"获取内存信息失败: {e}")
            virtual_empty = {
                "total": 0, "available": 0, 
                "used": 0, "percent": 0
            }
            swap_empty = {"total": 0, "used": 0, "percent": 0}
            return {"virtual": virtual_empty, "swap": swap_empty}
    
    @staticmethod
    def _get_disk_info() -> List[Dict[str, Any]]:
        """获取磁盘信息"""
        try:
            partitions = psutil.disk_partitions()
            disk_info = []
            
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_info.append({
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent
                    })
                except Exception as e:
                    logger.warning(f"获取分区 {partition.mountpoint} 信息失败: {e}")
                    continue
            
            return disk_info
        except Exception as e:
            logger.error(f"获取磁盘信息失败: {e}")
            return []
    
    @staticmethod
    def _get_network_info() -> Dict[str, Any]:
        """获取网络信息"""
        try:
            net_io = psutil.net_io_counters()
            net_connections = len(psutil.net_connections())
            
            return {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "connections": net_connections
            }
        except Exception as e:
            logger.error(f"获取网络信息失败: {e}")
            return {
                "bytes_sent": 0,
                "bytes_recv": 0,
                "packets_sent": 0,
                "packets_recv": 0,
                "connections": 0
            }
    
    @staticmethod
    def _get_top_processes(limit: int = 20) -> List[Dict[str, Any]]:
        """获取Top进程信息（模拟top命令）"""
        try:
            processes = []
            
            # 获取所有进程
            attrs = [
                'pid', 'name', 'cpu_percent', 
                'memory_percent', 'memory_info', 'status'
            ]
            for proc in psutil.process_iter(attrs):
                try:
                    proc_info = proc.info
                    cpu_pct = proc_info['cpu_percent']
                    mem_pct = proc_info['memory_percent']
                    if cpu_pct is not None and mem_pct is not None:
                        mem_info = proc_info['memory_info']
                        mem_mb = (
                            round(mem_info.rss / (1024 * 1024), 1)
                            if mem_info else 0
                        )
                        processes.append({
                            "pid": proc_info['pid'],
                            "name": proc_info['name'][:50],
                            "cpu_percent": round(cpu_pct, 1),
                            "memory_percent": round(mem_pct, 1),
                            "memory_mb": mem_mb,
                            "status": proc_info['status']
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied, 
                        psutil.ZombieProcess):
                    continue
            
            # 按CPU使用率排序，取前N个
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            return processes[:limit]
        except Exception as e:
            logger.error(f"获取进程信息失败: {e}")
            return []


# 全局实例
system_monitor = SystemMonitor()