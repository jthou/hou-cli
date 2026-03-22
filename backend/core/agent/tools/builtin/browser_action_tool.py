"""Browser Action Tool 基类 - 为 browser-use 的细粒度操作提供统一接口"""
import logging

from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from backend.services.llm.llm_service import LLMService
from backend.core.agent.tools.builtin.browser_llm_defaults import browser_default_chat_model


logger = logging.getLogger(__name__)


class BrowserActionTool(Tool):
    """Browser Action Tool 基类，为 browser-use 的细粒度操作提供统一接口
    
    这个基类封装了 browser-use 的底层操作，提供统一的工具接口，
    支持各种细粒度的浏览器操作，如点击、填写、导航等。
    """
    
    def __init__(self, name: str, description: str, parameters: list = None):
        """初始化 BrowserActionTool
        
        Args:
            name: 工具名称
            description: 工具描述
            parameters: 参数列表
        """
        super().__init__(
            name=name,
            description=description,
            parameters=parameters or [],
        )
        self.llm_service = LLMService()
        
    def execute(self, **kwargs) -> ToolResult:
        """执行浏览器操作（同步）
        
        子类应实现 _execute_action 方法来执行具体的浏览器操作
        """
        try:
            # 验证参数
            validation_error = self.validate_parameters(**kwargs)
            if validation_error:
                return ToolResult(
                    success=False,
                    error=validation_error
                )
            
            # 执行具体的浏览器操作
            result = self._execute_action(**kwargs)
            return result
            
        except Exception as e:
            logger.error(f"执行浏览器操作失败: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"执行浏览器操作失败: {str(e)}"
            )
    
    async def _execute_async(self, **kwargs) -> ToolResult:
        """执行浏览器操作（异步）
        
        子类应实现 _execute_action_async 方法来执行具体的浏览器操作
        """
        try:
            # 验证参数
            validation_error = self.validate_parameters(**kwargs)
            if validation_error:
                return ToolResult(
                    success=False,
                    error=validation_error
                )
            
            # 执行具体的浏览器操作
            result = await self._execute_action_async(**kwargs)
            return result
            
        except Exception as e:
            logger.error(f"执行浏览器操作失败: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"执行浏览器操作失败: {str(e)}"
            )
    
    def _execute_action(self, **kwargs) -> ToolResult:
        """执行具体的浏览器操作（同步）- 子类需要实现
        
        Args:
            **kwargs: 操作参数
            
        Returns:
            ToolResult: 执行结果
        """
        raise NotImplementedError("_execute_action 方法必须在子类中实现")
    
    async def _execute_action_async(self, **kwargs) -> ToolResult:
        """执行具体的浏览器操作（异步）- 子类需要实现
        
        Args:
            **kwargs: 操作参数
            
        Returns:
            ToolResult: 执行结果
        """
        raise NotImplementedError("_execute_action_async 方法必须在子类中实现")


class BrowserNavigateTool(BrowserActionTool):
    """浏览器导航工具"""
    
    def __init__(self):
        parameters = [
            ToolParameter(
                name="url",
                type="string",
                description="要导航到的URL地址",
                required=True
            ),
            ToolParameter(
                name="new_tab",
                type="boolean",
                description="是否在新标签页中打开，默认为false",
                required=False,
                default=False
            )
        ]
        
        super().__init__(
            name="browser_navigate",
            description="浏览器导航到指定URL",
            parameters=parameters
        )
    
    def _execute_action(self, **kwargs) -> ToolResult:
        """执行导航操作"""
        # 同步版本，我们调用异步版本
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        async def run_async():
            return await self._execute_action_async(**kwargs)
        
        return loop.run_until_complete(run_async())
    
    async def _execute_action_async(self, **kwargs) -> ToolResult:
        """执行导航操作（异步）"""
        from browser_use import Agent
        
        url = kwargs.get("url")
        new_tab = kwargs.get("new_tab", False)
        
        try:
            # 获取适配后的LLM
            llm = self.llm_service.get_browser_use_llm_with_adaptation(
                model=browser_default_chat_model()
            )
            
            # 创建 agent 执行导航
            agent = Agent(
                task=f"{'在新标签页' if new_tab else '在当前标签页'}导航到 {url}",
                llm=llm,
            )
            
            result = await agent.run()
            
            # 检查 agent 是否成功完成任务
            # 如果结果中有错误信息，应该反映到工具结果中
            result_str = str(result)
            has_items_error = 'items' in result_str
            has_consecutive_failures = 'consecutive failures' in result_str
            
            if has_items_error or has_consecutive_failures:
                return ToolResult(
                    success=False,  # 实际上任务失败了
                    error=f"浏览器操作未能完成: {result_str[:200]}...",
                    data={
                        "message": f"导航到 {url} 失败",
                        "url": url,
                        "new_tab": new_tab,
                        "result": result_str,
                        "error_details": "模型响应格式与browser-use不兼容导致任务失败"
                    }
                )
            else:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"成功导航到 {url} {'(新标签页)' if new_tab else '(当前标签页)'}",
                        "url": url,
                        "new_tab": new_tab,
                        "result": str(result)
                    }
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"导航失败: {str(e)}"
            )


class BrowserClickTool(BrowserActionTool):
    """浏览器点击工具"""
    
    def __init__(self):
        parameters = [
            ToolParameter(
                name="index",
                type="integer",
                description="要点击的元素索引号（通过页面分析获得）",
                required=True
            ),
            ToolParameter(
                name="text",
                type="string",
                description="要点击的元素文本（可选，用于坐标点击）",
                required=False
            ),
            ToolParameter(
                name="coordinate_x",
                type="integer",
                description="点击坐标的X值（可选，用于坐标点击）",
                required=False
            ),
            ToolParameter(
                name="coordinate_y",
                type="integer",
                description="点击坐标的Y值（可选，用于坐标点击）",
                required=False
            )
        ]
        
        super().__init__(
            name="browser_click",
            description="点击页面上的指定元素",
            parameters=parameters
        )
    
    def _execute_action(self, **kwargs) -> ToolResult:
        """执行点击操作"""
        # 同步版本，我们调用异步版本
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        async def run_async():
            return await self._execute_action_async(**kwargs)
        
        return loop.run_until_complete(run_async())
    
    async def _execute_action_async(self, **kwargs) -> ToolResult:
        """执行点击操作（异步）"""
        from browser_use import Agent
        
        index = kwargs.get("index")
        text = kwargs.get("text")
        coord_x = kwargs.get("coordinate_x")
        coord_y = kwargs.get("coordinate_y")
        
        try:
            # 获取适配后的LLM
            llm = self.llm_service.get_browser_use_llm_with_adaptation(
                model=browser_default_chat_model()
            )
            
            # 构建任务描述
            if text:
                task_desc = f"点击文本为 '{text}' 的元素"
            elif coord_x is not None and coord_y is not None:
                task_desc = f"点击坐标 ({coord_x}, {coord_y}) 处的元素"
            else:
                task_desc = f"点击索引为 {index} 的元素"
            
            # 创建 agent 执行点击
            agent = Agent(
                task=task_desc,
                llm=llm,
            )
            
            result = await agent.run()
            
            # 检查 agent 是否成功完成任务
            result_str = str(result)
            has_items_error = 'items' in result_str
            has_consecutive_failures = 'consecutive failures' in result_str
            
            if has_items_error or has_consecutive_failures:
                return ToolResult(
                    success=False,  # 实际上任务失败了
                    error=f"浏览器操作未能完成: {result_str[:200]}...",
                    data={
                        "message": f"点击元素 {task_desc} 失败",
                        "index": index,
                        "text": text,
                        "coordinate": (coord_x, coord_y) if coord_x is not None and coord_y is not None else None,
                        "result": result_str,
                        "error_details": "模型响应格式与browser-use不兼容导致任务失败"
                    }
                )
            else:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"成功点击元素: {task_desc}",
                        "index": index,
                        "text": text,
                        "coordinate": (coord_x, coord_y) if coord_x is not None and coord_y is not None else None,
                        "result": str(result)
                    }
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"点击失败: {str(e)}"
            )


class BrowserFillTool(BrowserActionTool):
    """浏览器表单填充工具"""
    
    def __init__(self):
        parameters = [
            ToolParameter(
                name="index",
                type="integer",
                description="输入框元素的索引号",
                required=True
            ),
            ToolParameter(
                name="text",
                type="string",
                description="要填入的文本内容",
                required=True
            ),
            ToolParameter(
                name="clear",
                type="boolean",
                description="是否先清除现有内容，默认为true",
                required=False,
                default=True
            )
        ]
        
        super().__init__(
            name="browser_fill",
            description="在页面输入框中填入文本",
            parameters=parameters
        )
    
    def _execute_action(self, **kwargs) -> ToolResult:
        """执行填充操作"""
        # 同步版本，我们调用异步版本
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        async def run_async():
            return await self._execute_action_async(**kwargs)
        
        return loop.run_until_complete(run_async())
    
    async def _execute_action_async(self, **kwargs) -> ToolResult:
        """执行填充操作（异步）"""
        from browser_use import Agent
        
        index = kwargs.get("index")
        text = kwargs.get("text")
        clear = kwargs.get("clear", True)
        
        try:
            # 获取适配后的LLM
            llm = self.llm_service.get_browser_use_llm_with_adaptation(
                model=browser_default_chat_model()
            )
            
            # 构建任务描述
            task_desc = f"在索引为 {index} 的输入框中填入文本 '{text}'{' (先清空)' if clear else ''}"
            
            # 创建 agent 执行填充
            agent = Agent(
                task=task_desc,
                llm=llm,
            )
            
            result = await agent.run()
            
            # 检查 agent 是否成功完成任务
            result_str = str(result)
            has_items_error = 'items' in result_str
            has_consecutive_failures = 'consecutive failures' in result_str
            
            if has_items_error or has_consecutive_failures:
                return ToolResult(
                    success=False,  # 实际上任务失败了
                    error=f"浏览器操作未能完成: {result_str[:200]}...",
                    data={
                        "message": f"填充输入框 {task_desc} 失败",
                        "index": index,
                        "text": text,
                        "clear": clear,
                        "result": result_str,
                        "error_details": "模型响应格式与browser-use不兼容导致任务失败"
                    }
                )
            else:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"成功填充输入框: {task_desc}",
                        "index": index,
                        "text": text,
                        "clear": clear,
                        "result": str(result)
                    }
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"填充失败: {str(e)}"
            )


class BrowserSearchTool(BrowserActionTool):
    """浏览器搜索工具"""
    
    def __init__(self):
        parameters = [
            ToolParameter(
                name="query",
                type="string",
                description="搜索查询词",
                required=True
            ),
            ToolParameter(
                name="engine",
                type="string",
                description="搜索引擎，可选值: duckduckgo, google, bing，默认为google",
                required=False,
                default="google"
            )
        ]
        
        super().__init__(
            name="browser_search",
            description="在指定搜索引擎中搜索内容",
            parameters=parameters
        )
    
    def _execute_action(self, **kwargs) -> ToolResult:
        """执行搜索操作"""
        # 同步版本，我们调用异步版本
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        async def run_async():
            return await self._execute_action_async(**kwargs)
        
        return loop.run_until_complete(run_async())
    
    async def _execute_action_async(self, **kwargs) -> ToolResult:
        """执行搜索操作（异步）"""
        from browser_use import Agent
        
        query = kwargs.get("query")
        engine = kwargs.get("engine", "google")
        
        try:
            # 获取适配后的LLM
            llm = self.llm_service.get_browser_use_llm_with_adaptation(
                model=browser_default_chat_model()
            )
            
            # 构建任务描述
            task_desc = f"使用 {engine} 搜索 '{query}'"
            
            # 创建 agent 执行搜索
            agent = Agent(
                task=task_desc,
                llm=llm,
            )
            
            result = await agent.run()
            
            # 检查 agent 是否成功完成任务
            result_str = str(result)
            has_items_error = 'items' in result_str
            has_consecutive_failures = 'consecutive failures' in result_str
            
            if has_items_error or has_consecutive_failures:
                return ToolResult(
                    success=False,  # 实际上任务失败了
                    error=f"浏览器操作未能完成: {result_str[:200]}...",
                    data={
                        "message": f"搜索 {task_desc} 失败",
                        "query": query,
                        "engine": engine,
                        "result": result_str,
                        "error_details": "模型响应格式与browser-use不兼容导致任务失败"
                    }
                )
            else:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"成功搜索: {task_desc}",
                        "query": query,
                        "engine": engine,
                        "result": str(result)
                    }
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"搜索失败: {str(e)}"
            )


class BrowserExtractTool(BrowserActionTool):
    """浏览器内容提取工具"""
    
    def __init__(self):
        parameters = [
            ToolParameter(
                name="query",
                type="string",
                description="要提取的信息查询描述",
                required=True
            ),
            ToolParameter(
                name="extract_links",
                type="boolean",
                description="是否同时提取链接，默认为false",
                required=False,
                default=False
            )
        ]
        
        super().__init__(
            name="browser_extract",
            description="从当前页面提取指定信息",
            parameters=parameters
        )
    
    def _execute_action(self, **kwargs) -> ToolResult:
        """执行内容提取操作"""
        # 同步版本，我们调用异步版本
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        async def run_async():
            return await self._execute_action_async(**kwargs)
        
        return loop.run_until_complete(run_async())
    
    async def _execute_action_async(self, **kwargs) -> ToolResult:
        """执行内容提取操作（异步）"""
        from browser_use import Agent
        
        query = kwargs.get("query")
        extract_links = kwargs.get("extract_links", False)
        
        try:
            # 获取适配后的LLM
            llm = self.llm_service.get_browser_use_llm_with_adaptation(
                model=browser_default_chat_model()
            )
            
            # 构建任务描述
            task_desc = f"从当前页面提取信息: {query}{' (包括链接)' if extract_links else ''}"
            
            # 创建 agent 执行提取
            agent = Agent(
                task=task_desc,
                llm=llm,
            )
            
            result = await agent.run()
            
            # 检查 agent 是否成功完成任务
            result_str = str(result)
            has_items_error = 'items' in result_str
            has_consecutive_failures = 'consecutive failures' in result_str
            
            if has_items_error or has_consecutive_failures:
                return ToolResult(
                    success=False,  # 实际上任务失败了
                    error=f"浏览器操作未能完成: {result_str[:200]}...",
                    data={
                        "message": f"提取信息 {task_desc} 失败",
                        "query": query,
                        "extract_links": extract_links,
                        "result": result_str,
                        "error_details": "模型响应格式与browser-use不兼容导致任务失败"
                    }
                )
            else:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"成功提取信息: {task_desc}",
                        "query": query,
                        "extract_links": extract_links,
                        "result": str(result)
                    }
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"提取失败: {str(e)}"
            )
