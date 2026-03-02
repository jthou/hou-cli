"""Tool 注册器"""
from typing import Dict, Optional, List
from backend.core.agent.tools.base import Tool, ToolResult
from backend.core.agent.tools.metadata import tool_metadata_registry


class ToolRegistry:
    """工具注册器（单例模式）"""
    
    _instance: Optional['ToolRegistry'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: Dict[str, Tool] = {}
        return cls._instance
    
    def register(self, tool: Tool) -> None:
        """
        注册工具
        
        Args:
            tool: 要注册的工具
            
        Raises:
            ValueError: 如果工具名称已存在
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool
        
        # 如果工具有元数据属性，同步到元数据注册表
        # 优先使用工具实例的元数据，如果没有则使用默认元数据
        metadata = tool_metadata_registry.get_metadata(tool.name)
        if metadata:
            # 如果工具实例有元数据，更新元数据注册表
            # 注意：只更新工具实例明确提供的属性，不要覆盖默认元数据
            if hasattr(tool, 'metadata') and tool.metadata:
                # 如果工具实例有 metadata 属性，使用它
                if hasattr(tool.metadata, 'requires_reasoning'):
                    metadata.requires_reasoning = tool.metadata.requires_reasoning
                if hasattr(tool.metadata, 'requires_code'):
                    metadata.requires_code = tool.metadata.requires_code
                if hasattr(tool.metadata, 'recommended_model'):
                    metadata.recommended_model = tool.metadata.recommended_model
                if hasattr(tool.metadata, 'can_parallel'):
                    metadata.can_parallel = tool.metadata.can_parallel
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """
        获取工具
        
        Args:
            name: 工具名称
            
        Returns:
            Tool 对象，如果不存在返回 None
        """
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """
        列出所有已注册的工具名称
        
        Returns:
            工具名称列表
        """
        return list(self._tools.keys())

    def get_all_tools(self) -> List[Tool]:
        """
        获取所有已注册的工具实例
        
        Returns:
            Tool 实例列表
        """
        return list(self._tools.values())
    
    def get_tools_for_llm(self) -> List[dict]:
        """
        获取 LLM 格式的工具定义（用于 Function Calling）
        
        Returns:
            OpenAI Function Calling 格式的工具定义列表
        """
        return [tool.to_dict() for tool in self._tools.values()]
    
    def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """
        执行工具（同步）
        
        Args:
            tool_name: 工具名称
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        tool = self.get_tool(tool_name)
        if tool is None:
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' not found"
            )
        
        # 验证参数
        validation_error = tool.validate_parameters(**kwargs)
        if validation_error:
            return ToolResult(
                success=False,
                error=validation_error
            )
        
        # 执行工具
        try:
            return tool.execute(**kwargs)
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error executing tool '{tool_name}': {str(e)}"
            )
    
    async def execute_async(self, tool_name: str, **kwargs) -> ToolResult:
        """
        异步执行工具（如果在异步上下文中，优先使用此方法）
        
        Args:
            tool_name: 工具名称
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        tool = self.get_tool(tool_name)
        if tool is None:
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' not found"
            )
        
        # 验证参数
        validation_error = tool.validate_parameters(**kwargs)
        if validation_error:
            return ToolResult(
                success=False,
                error=validation_error
            )
        
        # 如果工具有异步执行方法，直接调用
        if hasattr(tool, '_execute_async'):
            try:
                return await tool._execute_async(**kwargs)
            except Exception as e:
                return ToolResult(
                    success=False,
                    error=f"Error executing tool '{tool_name}': {str(e)}"
                )
        
        # 否则使用同步方法（在线程池中执行）
        import asyncio
        import concurrent.futures
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(tool.execute, **kwargs)
            return await loop.run_in_executor(None, future.result)
    
    def clear(self) -> None:
        """清空注册表（主要用于测试）"""
        self._tools.clear()

