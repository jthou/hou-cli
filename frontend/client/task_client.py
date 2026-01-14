"""任务管理客户端 - 用于查询和管理异步任务"""
import httpx
from typing import Optional, List, Dict, Any
from frontend.client.ipc_client import IPCClient


class TaskClient:
    """任务管理客户端"""
    
    def __init__(self, ipc_client: IPCClient):
        """
        初始化任务客户端
        
        Args:
            ipc_client: IPC 客户端实例
        """
        self.ipc_client = ipc_client
        self.base_url = ipc_client.base_url
    
    def get_task(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态
        
        Args:
            task_id: 任务 ID
            
        Returns:
            任务信息字典
        """
        try:
            response = self.ipc_client.client.get(
                f"{self.base_url}/api/tasks/{task_id}",
                timeout=10.0
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                return result.get("task", {})
            else:
                raise Exception(result.get("error", "获取任务失败"))
        except httpx.RequestError as e:
            raise ConnectionError(f"连接错误：{str(e)}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise Exception(f"任务不存在: {task_id}")
            raise Exception(f"HTTP 错误：{e.response.status_code}")
    
    def list_tasks(self, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        列出任务
        
        Args:
            status: 任务状态过滤（可选）
            limit: 返回数量限制
            
        Returns:
            任务列表
        """
        try:
            params = {"limit": limit}
            if status:
                params["status"] = status
            
            response = self.ipc_client.client.get(
                f"{self.base_url}/api/tasks",
                params=params,
                timeout=10.0
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                return result.get("tasks", [])
            else:
                raise Exception(result.get("error", "获取任务列表失败"))
        except httpx.RequestError as e:
            raise ConnectionError(f"连接错误：{str(e)}")
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP 错误：{e.response.status_code}")
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            是否取消成功
        """
        try:
            response = self.ipc_client.client.post(
                f"{self.base_url}/api/tasks/{task_id}/cancel",
                timeout=10.0
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("success"):
                return True
            else:
                raise Exception(result.get("error", "取消任务失败"))
        except httpx.RequestError as e:
            raise ConnectionError(f"连接错误：{str(e)}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise Exception(f"任务不存在: {task_id}")
            raise Exception(f"HTTP 错误：{e.response.status_code}")

