"""MCP 工具适配器（将 MCP 工具转换为 Tool 接口）"""
import logging
from typing import Dict, Any, Optional
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from backend.core.agent.mcps.models import MCPTool
from backend.core.agent.mcps.client import MCPClient

logger = logging.getLogger(__name__)


class MCPToolAdapter(Tool):
    """MCP 工具适配器，将 MCP 工具包装为 Tool 接口"""
    
    def __init__(self, mcp_tool: MCPTool, mcp_client: MCPClient):
        """
        初始化 MCP 工具适配器
        
        Args:
            mcp_tool: MCP 工具定义
            mcp_client: MCP 客户端
        """
        # 将 MCP 工具的 input_schema 转换为 ToolParameter 列表
        parameters = self._convert_parameters(mcp_tool.input_schema)
        
        # 工具名称添加服务器前缀，避免冲突
        tool_name = f"mcp_{mcp_tool.server_name}_{mcp_tool.name}"
        
        super().__init__(
            name=tool_name,
            description=f"[MCP: {mcp_tool.server_name}] {mcp_tool.description}",
            parameters=parameters
        )
        
        self.mcp_tool = mcp_tool
        self.mcp_client = mcp_client
    
    def _convert_parameters(self, input_schema: Dict[str, Any]) -> list[ToolParameter]:
        """
        将 JSON Schema 转换为 ToolParameter 列表
        
        Args:
            input_schema: JSON Schema 格式的参数定义
            
        Returns:
            ToolParameter 列表
        """
        parameters = []
        
        # 提取 properties 和 required
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])
        
        for param_name, param_schema in properties.items():
            param_type = param_schema.get("type", "string")
            param_desc = param_schema.get("description", "")
            param_required = param_name in required
            param_default = param_schema.get("default")
            param_enum = param_schema.get("enum")
            
            # 类型映射（JSON Schema -> ToolParameter type）
            type_mapping = {
                "string": "string",
                "integer": "integer",
                "number": "number",
                "boolean": "boolean",
                "object": "object",
                "array": "array",
            }
            
            tool_param_type = type_mapping.get(param_type, "string")
            
            parameters.append(ToolParameter(
                name=param_name,
                type=tool_param_type,
                description=param_desc,
                required=param_required,
                default=param_default,
                enum=param_enum
            ))
        
        return parameters
    
    def execute(self, **kwargs) -> ToolResult:
        """
        执行 MCP 工具
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        try:
            # 调用 MCP 客户端执行工具
            result = asyncio.run(self.mcp_client.call_tool(
                tool_name=self.mcp_tool.name,
                arguments=kwargs
            ))
            
            return ToolResult(
                success=True,
                data=result
            )
        except Exception as e:
            logger.error(f"执行 MCP 工具 {self.name} 失败: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=str(e)
            )

