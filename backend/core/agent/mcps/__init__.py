"""MCP (Model Context Protocol) 服务器集成

支持多个 MCP 服务器的连接、工具发现和注册。
"""
from backend.core.agent.mcps.manager import MCPManager
from backend.core.agent.mcps.client import MCPClient
from backend.core.agent.mcps.adapter import MCPToolAdapter
from backend.core.agent.mcps.config import MCPConfig, load_mcp_configs
from backend.core.agent.mcps.models import MCPServerConfig, MCPTool, MCPResource

__all__ = [
    "MCPManager",
    "MCPClient",
    "MCPToolAdapter",
    "MCPConfig",
    "load_mcp_configs",
    "MCPServerConfig",
    "MCPTool",
    "MCPResource",
]

