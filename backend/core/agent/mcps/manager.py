"""MCP 管理器（管理多个 MCP 服务器）"""
import asyncio
import logging
from typing import List, Dict, Optional
from backend.core.agent.mcps.config import load_mcp_configs
from backend.core.agent.mcps.client import MCPClient
from backend.core.agent.mcps.adapter import MCPToolAdapter
from backend.core.agent.mcps.models import MCPServerConfig
from backend.core.agent.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class MCPManager:
    """MCP 管理器，负责管理多个 MCP 服务器"""
    
    def __init__(self, tool_registry: Optional[ToolRegistry] = None):
        """
        初始化 MCP 管理器
        
        Args:
            tool_registry: 工具注册器（可选，如果提供则自动注册工具）
        """
        self.configs: List[MCPServerConfig] = []
        self.clients: Dict[str, MCPClient] = {}  # name -> client
        self.tool_registry = tool_registry
        self.initialized = False
    
    async def initialize(self) -> bool:
        """
        初始化 MCP 管理器（加载配置并连接服务器）
        
        Returns:
            是否初始化成功
        """
        if self.initialized:
            return True
        
        try:
            # 加载配置
            self.configs = load_mcp_configs()
            if not self.configs:
                logger.info("未配置 MCP 服务器，跳过初始化")
                self.initialized = True
                return True
            
            # 连接所有服务器
            connected_count = 0
            for config in self.configs:
                try:
                    client = MCPClient(config)
                    if await client.connect():
                        self.clients[config.name] = client
                        connected_count += 1
                        
                        # 发现并注册工具
                        await self._register_tools_from_client(client)
                    else:
                        logger.warning(f"MCP 服务器 {config.name} 连接失败")
                except Exception as e:
                    logger.error(f"初始化 MCP 服务器 {config.name} 失败: {e}", exc_info=True)
            
            logger.info(f"MCP 管理器初始化完成: {connected_count}/{len(self.configs)} 个服务器连接成功")
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"MCP 管理器初始化失败: {e}", exc_info=True)
            return False
    
    async def _register_tools_from_client(self, client: MCPClient):
        """
        从 MCP 客户端发现并注册工具
        
        Args:
            client: MCP 客户端
        """
        if not self.tool_registry:
            return
        
        try:
            # 获取工具列表
            mcp_tools = await client.list_tools()
            
            # 为每个工具创建适配器并注册
            for mcp_tool in mcp_tools:
                try:
                    adapter = MCPToolAdapter(mcp_tool=mcp_tools, mcp_client=client)
                    self.tool_registry.register(adapter)
                    logger.debug(f"注册 MCP 工具: {adapter.name} (来自 {client.config.name})")
                except Exception as e:
                    logger.warning(f"注册 MCP 工具失败 {mcp_tool.name}: {e}")
            
            logger.info(f"从 MCP 服务器 {client.config.name} 注册了 {len(mcp_tools)} 个工具")
            
        except Exception as e:
            logger.error(f"从 MCP 服务器 {client.config.name} 注册工具失败: {e}", exc_info=True)
    
    def get_client(self, server_name: str) -> Optional[MCPClient]:
        """
        获取指定名称的 MCP 客户端
        
        Args:
            server_name: 服务器名称
            
        Returns:
            MCPClient 或 None
        """
        return self.clients.get(server_name)
    
    def list_servers(self) -> List[str]:
        """
        列出所有已连接的 MCP 服务器名称
        
        Returns:
            服务器名称列表
        """
        return list(self.clients.keys())
    
    async def shutdown(self):
        """关闭所有 MCP 连接"""
        for name, client in self.clients.items():
            try:
                await client.disconnect()
            except Exception as e:
                logger.warning(f"关闭 MCP 服务器 {name} 连接时出错: {e}")
        
        self.clients.clear()
        self.initialized = False
        logger.info("MCP 管理器已关闭")

