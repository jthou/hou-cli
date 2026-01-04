"""MCP 客户端（单个服务器连接）"""
import asyncio
import json
import logging
import subprocess
from typing import Dict, Any, Optional, List, AsyncIterator
from backend.core.agent.mcps.models import MCPServerConfig, MCPTool, MCPResource

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP 客户端，负责连接单个 MCP 服务器"""
    
    def __init__(self, config: MCPServerConfig):
        """
        初始化 MCP 客户端
        
        Args:
            config: MCP 服务器配置
        """
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.connected = False
        self.tools: List[MCPTool] = []
        self.resources: List[MCPResource] = []
    
    async def connect(self) -> bool:
        """
        连接到 MCP 服务器
        
        Returns:
            是否连接成功
        """
        try:
            if self.config.type == "stdio":
                return await self._connect_stdio()
            elif self.config.type in ("http", "sse"):
                return await self._connect_http()
            else:
                logger.error(f"不支持的 MCP 连接类型: {self.config.type}")
                return False
        except Exception as e:
            logger.error(f"连接 MCP 服务器 {self.config.name} 失败: {e}", exc_info=True)
            return False
    
    async def _connect_stdio(self) -> bool:
        """通过 stdio 连接 MCP 服务器"""
        try:
            # 构建命令
            cmd = [self.config.command]
            if self.config.args:
                cmd.extend(self.config.args)
            
            # 启动进程
            env = os.environ.copy()
            if self.config.env:
                env.update(self.config.env)
            
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                bufsize=0
            )
            
            # 发送初始化请求
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "hou-cli",
                        "version": "1.0.0"
                    }
                }
            }
            
            # 发送请求并等待响应
            request_str = json.dumps(init_request) + "\n"
            self.process.stdin.write(request_str)
            self.process.stdin.flush()
            
            # 读取响应（简化实现，实际需要更复杂的协议处理）
            # TODO: 实现完整的 MCP 协议处理
            
            self.connected = True
            logger.info(f"MCP 服务器 {self.config.name} 连接成功 (stdio)")
            return True
            
        except Exception as e:
            logger.error(f"连接 MCP 服务器 {self.config.name} (stdio) 失败: {e}", exc_info=True)
            return False
    
    async def _connect_http(self) -> bool:
        """通过 HTTP/SSE 连接 MCP 服务器"""
        # TODO: 实现 HTTP/SSE 连接
        logger.warning(f"HTTP/SSE 连接模式尚未实现: {self.config.name}")
        return False
    
    async def list_tools(self) -> List[MCPTool]:
        """
        获取 MCP 服务器提供的工具列表
        
        Returns:
            工具列表
        """
        if not self.connected:
            logger.warning(f"MCP 服务器 {self.config.name} 未连接，无法获取工具列表")
            return []
        
        # TODO: 实现工具列表获取
        # 发送 tools/list 请求并解析响应
        
        return self.tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用 MCP 工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        if not self.connected:
            raise RuntimeError(f"MCP 服务器 {self.config.name} 未连接")
        
        # TODO: 实现工具调用
        # 发送 tools/call 请求并解析响应
        
        return {}
    
    async def disconnect(self):
        """断开连接"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"断开 MCP 服务器 {self.config.name} 连接时出错: {e}")
                if self.process:
                    self.process.kill()
            finally:
                self.process = None
        
        self.connected = False
        logger.info(f"MCP 服务器 {self.config.name} 已断开连接")

