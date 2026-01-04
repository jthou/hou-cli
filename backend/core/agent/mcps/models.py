"""MCP 数据模型"""
from dataclasses import dataclass
from typing import Dict, Any, Optional, List


@dataclass
class MCPServerConfig:
    """MCP 服务器配置"""
    name: str  # 服务器名称（用于标识）
    type: str  # 连接类型：stdio, http, sse
    command: Optional[str] = None  # stdio 模式：命令（如 "node", "python"）
    args: Optional[List[str]] = None  # stdio 模式：命令参数
    url: Optional[str] = None  # http/sse 模式：服务器 URL
    env: Optional[Dict[str, str]] = None  # 环境变量
    timeout: int = 30  # 连接超时（秒）
    enabled: bool = True  # 是否启用


@dataclass
class MCPTool:
    """MCP 工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]  # JSON Schema
    server_name: str  # 所属的 MCP 服务器名称


@dataclass
class MCPResource:
    """MCP 资源定义"""
    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None
    server_name: str  # 所属的 MCP 服务器名称

