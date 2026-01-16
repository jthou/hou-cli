# Browser-use 集成方案

本文档详细说明如何将 Browser-use 集成到现有的工具系统中。

## 架构概览

```
┌─────────────────┐
│  Orchestrator   │
│  - LLMService   │
│  - ToolRegistry │
└────────┬────────┘
         │
         ├─> 注册 BrowserTool
         │
         ├─> LLM Function Calling
         │
         └─> 执行 BrowserTool
              │
              └─> Browser-use Agent
                   │
                   └─> Playwright Browser
```

## 集成步骤

### 1. 安装依赖

```bash
pip install browser-use
```

Browser-use 会自动安装 Playwright，但需要安装浏览器：

```bash
playwright install chromium
```

### 2. 创建 BrowserTool

在 `backend/core/agent/tools/builtin/browser_tool.py` 创建工具。

### 3. 注册工具

在 `orchestrator.py` 的 `_register_tools()` 方法中添加注册逻辑。

### 4. LLM 适配

Browser-use 需要 LangChain 兼容的 LLM 实例，需要适配项目现有的 LLMService。

## 详细实现

### 步骤 1: LLM 适配器

Browser-use 需要 LangChain 兼容的 LLM，但项目使用 AsyncOpenAI。需要创建适配器：

```python
# backend/core/agent/tools/builtin/browser_tool.py
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.callbacks import CallbackManagerForLLMRun
from typing import Optional, List, Any
from backend.services.llm.llm_service import LLMService

class LLMServiceAdapter(BaseChatModel):
    """将项目的 LLMService 适配为 LangChain 兼容的 LLM"""
    
    def __init__(self, llm_service: LLMService):
        super().__init__()
        self.llm_service = llm_service
    
    @property
    def _llm_type(self) -> str:
        return "llm_service_adapter"
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ):
        # 转换为项目格式
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                formatted_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                formatted_messages.append({"role": "assistant", "content": msg.content})
        
        # 调用 LLM 服务（同步包装异步）
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # 如果已经在事件循环中，使用线程池
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self.llm_service.chat(messages=formatted_messages)
                )
                response = future.result(timeout=60)
        except RuntimeError:
            response = asyncio.run(self.llm_service.chat(messages=formatted_messages))
        
        # 转换为 LangChain 格式
        from langchain_core.outputs import ChatGeneration, ChatResult
        generation = ChatGeneration(message=AIMessage(content=response))
        return ChatResult(generations=[generation])
    
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ):
        # 转换为项目格式
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                formatted_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                formatted_messages.append({"role": "assistant", "content": msg.content})
        
        # 异步调用 LLM 服务
        response = await self.llm_service.chat(messages=formatted_messages)
        
        # 转换为 LangChain 格式
        from langchain_core.outputs import ChatGeneration, ChatResult
        generation = ChatGeneration(message=AIMessage(content=response))
        return ChatResult(generations=[generation])
```

### 步骤 2: BrowserTool 实现

```python
# backend/core/agent/tools/builtin/browser_tool.py
import asyncio
import os
from typing import Dict, Any, Optional, TYPE_CHECKING
from pathlib import Path
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter

if TYPE_CHECKING:
    from backend.services.llm.llm_service import LLMService

try:
    from browser_use import Agent
    from langchain_core.language_models import BaseChatModel
    BROWSER_USE_AVAILABLE = True
except ImportError:
    BROWSER_USE_AVAILABLE = False
    Agent = None
    BaseChatModel = None


class BrowserTool(Tool):
    """浏览器自动化工具 - 基于 Browser-use
    
    允许 AI 助手通过自然语言指令控制浏览器执行各种任务，
    如网页搜索、表单填写、数据提取等。
    """
    
    def __init__(self, llm_service: Optional['LLMService'] = None):
        """
        初始化浏览器工具
        
        Args:
            llm_service: LLM 服务实例（可选，如果未提供则在执行时获取）
        """
        if not BROWSER_USE_AVAILABLE:
            raise ImportError(
                "browser-use is not installed. "
                "Please install it with: pip install browser-use"
            )
        
        parameters = [
            ToolParameter(
                name="task",
                type="string",
                description=(
                    "要执行的浏览器任务，用自然语言描述。"
                    "\n示例："
                    "- '搜索 Python 教程并总结前 3 个结果'"
                    "- '在 GitHub 上查找 Python 项目，按 stars 排序'"
                    "- '访问 example.com 并提取页面标题和主要内容'"
                    "- '填写表单：姓名=张三，邮箱=zhang@example.com'"
                    "\n注意："
                    "- 描述要清晰具体，包含关键信息"
                    "- 可以指定多个步骤，用逗号或分号分隔"
                ),
                required=True
            ),
            ToolParameter(
                name="headless",
                type="boolean",
                description="是否使用无头模式（默认 False，显示浏览器窗口，便于调试）",
                required=False,
                default=False
            ),
            ToolParameter(
                name="instructions",
                type="array",
                description=(
                    "可选的操作步骤列表，用于更精确的控制。"
                    "如果提供，将覆盖 task 参数中的步骤。"
                    "\n示例：['导航到 google.com', '在搜索框输入 Python', '点击搜索按钮']"
                ),
                required=False
            ),
            ToolParameter(
                name="timeout",
                type="integer",
                description="任务超时时间（秒），默认 60，最大 300",
                required=False,
                default=60
            )
        ]
        
        super().__init__(
            name="browser",
            description=(
                "浏览器自动化工具，支持通过自然语言指令控制浏览器执行各种任务。"
                "\n核心功能："
                "- 网页导航和搜索"
                "- 表单填写和提交"
                "- 数据提取和总结"
                "- 多步骤任务自动化"
                "\n使用场景："
                "- 网页搜索和信息收集"
                "- 在线表单填写"
                "- 数据抓取和分析"
                "- 网站交互和测试"
                "\n优势："
                "- 语义理解：通过自然语言描述任务，自动处理交互细节"
                "- 智能定位：自动识别页面元素，适应页面变化"
                "- 错误恢复：内置重试和错误处理机制"
                "\n注意："
                "- 任务描述要清晰具体"
                "- 复杂任务建议分步骤执行"
                "- 默认显示浏览器窗口，便于观察执行过程"
            ),
            parameters=parameters
        )
        
        self.llm_service = llm_service
        # 创建对话保存目录
        self.conversation_path = Path("data/browser_conversations")
        self.conversation_path.mkdir(parents=True, exist_ok=True)
    
    def _get_llm_service(self) -> 'LLMService':
        """获取 LLM 服务实例"""
        if self.llm_service:
            return self.llm_service
        
        # 如果没有提供，尝试从环境获取
        # 注意：这需要确保在正确的上下文中调用
        from backend.services.llm.llm_service import LLMService
        return LLMService()
    
    def _create_llm_adapter(self, llm_service: 'LLMService') -> BaseChatModel:
        """创建 LangChain 兼容的 LLM 适配器"""
        from backend.core.agent.tools.builtin.browser_tool import LLMServiceAdapter
        return LLMServiceAdapter(llm_service)
    
    def execute(self, **kwargs) -> ToolResult:
        """执行浏览器任务（同步包装异步方法）"""
        try:
            # 尝试获取当前事件循环
            loop = asyncio.get_running_loop()
            # 如果已经在事件循环中，使用线程池执行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self._execute_async(**kwargs)
                )
                timeout = kwargs.get("timeout", 60) + 10  # 超时时间+10秒缓冲
                return future.result(timeout=timeout)
        except RuntimeError:
            # 没有运行中的事件循环，直接创建新的
            return asyncio.run(self._execute_async(**kwargs))
    
    async def _execute_async(self, **kwargs) -> ToolResult:
        """异步执行浏览器任务"""
        if not BROWSER_USE_AVAILABLE:
            return ToolResult(
                success=False,
                error="browser-use is not installed. Please install it with: pip install browser-use"
            )
        
        task = kwargs.get("task")
        if not task:
            return ToolResult(
                success=False,
                error="Task parameter is required"
            )
        
        headless = kwargs.get("headless", False)
        instructions = kwargs.get("instructions")
        timeout = kwargs.get("timeout", 60)
        
        # 验证超时时间
        if timeout < 1 or timeout > 300:
            timeout = 60
        
        try:
            # 获取 LLM 服务并创建适配器
            llm_service = self._get_llm_service()
            llm = self._create_llm_adapter(llm_service)
            
            # 创建 Browser-use Agent
            agent = Agent(
                task=task,
                llm=llm,
                browser_config={
                    "headless": headless,
                    "save_conversation_path": str(self.conversation_path),
                    "viewport": {"width": 1920, "height": 1080},
                    "timeout": timeout * 1000  # 转换为毫秒
                },
                instructions=instructions
            )
            
            # 执行任务（带超时控制）
            result = await asyncio.wait_for(
                agent.run(),
                timeout=timeout
            )
            
            return ToolResult(
                success=True,
                data={
                    "result": str(result) if result else "任务执行完成",
                    "task": task,
                    "message": "浏览器任务执行成功"
                }
            )
            
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                error=f"浏览器任务执行超时（{timeout}秒）"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"浏览器任务执行失败: {str(e)}"
            )
```

### 步骤 3: 在 Orchestrator 中注册

```python
# backend/core/agent/orchestrator.py
# 在 _register_tools() 方法中添加：

# 注册浏览器工具
try:
    from backend.core.agent.tools.builtin.browser_tool import BrowserTool
    browser_tool = BrowserTool(llm_service=self.llm_service)
    self.tool_registry.register(browser_tool)
    self.debug.log_orchestrator_step("注册工具", {"browser_tool": "registered"})
    logger.info("Browser tool registered successfully")
except ImportError as e:
    error_msg = f"Browser-use not installed: {str(e)}. Browser tool will not be available."
    self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
    logger.warning(error_msg)
except Exception as e:
    error_msg = f"Failed to register browser tool: {str(e)}. Browser tool will not be available."
    self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
    logger.warning(error_msg)
```

### 步骤 4: 更新工具模块导出

```python
# backend/core/agent/tools/builtin/__init__.py
from .browser_tool import BrowserTool

__all__ = [
    # ... 其他工具
    "BrowserTool",
]
```

## 使用示例

### 示例 1: 简单搜索任务

```python
# LLM 会调用：
{
    "name": "browser",
    "arguments": {
        "task": "搜索 Python 教程并总结前 3 个结果"
    }
}
```

### 示例 2: 复杂多步骤任务

```python
# LLM 会调用：
{
    "name": "browser",
    "arguments": {
        "task": "在 GitHub 上搜索 Python 项目，按 stars 排序，提取前 5 个项目的名称和描述",
        "headless": false,
        "timeout": 120
    }
}
```

### 示例 3: 使用指令列表

```python
# LLM 会调用：
{
    "name": "browser",
    "arguments": {
        "task": "访问示例网站并提取信息",
        "instructions": [
            "导航到 https://example.com",
            "等待页面加载完成",
            "提取页面标题",
            "提取主要内容区域",
            "返回提取的信息"
        ]
    }
}
```

## 配置选项

### 环境变量

可以在 `.env` 文件中配置：

```bash
# Browser-use 配置
BROWSER_HEADLESS=false  # 是否使用无头模式
BROWSER_TIMEOUT=60      # 默认超时时间（秒）
BROWSER_CONVERSATION_PATH=data/browser_conversations  # 对话保存路径
```

### 浏览器配置

可以在 `BrowserTool.__init__()` 中自定义浏览器配置：

```python
browser_config = {
    "headless": False,
    "viewport": {"width": 1920, "height": 1080},
    "user_agent": "Mozilla/5.0...",
    "timeout": 30000,
    "save_conversation_path": "./data/browser_conversations"
}
```

## 注意事项

### 1. 性能考虑

- 浏览器实例占用内存较大，建议复用
- 长时间运行的任务需要设置合理的超时时间
- 无头模式性能更好，但调试时建议使用有头模式

### 2. 安全性

- 浏览器工具可以访问任意网站，需要权限控制
- 避免执行恶意 JavaScript
- 限制文件系统访问

### 3. 错误处理

- 页面加载时间不确定，需要超时处理
- 元素可能动态加载，Browser-use 会自动等待
- 网络错误需要优雅处理

### 4. LLM 适配

- Browser-use 需要 LangChain 兼容的 LLM
- 需要创建适配器将项目的 LLMService 转换为 LangChain 格式
- 确保异步调用正确处理

## 测试

### 单元测试

```python
# tests/test_browser_tool.py
import pytest
from backend.core.agent.tools.builtin.browser_tool import BrowserTool
from backend.services.llm.llm_service import LLMService

@pytest.mark.asyncio
async def test_browser_tool_simple_task():
    llm_service = LLMService()
    tool = BrowserTool(llm_service=llm_service)
    
    result = await tool._execute_async(
        task="访问 https://example.com 并提取页面标题",
        headless=True,
        timeout=30
    )
    
    assert result.success
    assert "example" in result.data["result"].lower()
```

### 集成测试

```python
@pytest.mark.asyncio
async def test_browser_tool_integration():
    from backend.core.agent.orchestrator import Orchestrator
    
    orchestrator = Orchestrator()
    
    # 检查工具是否注册
    assert "browser" in orchestrator.tool_registry.list_tools()
    
    # 测试工具执行
    tool = orchestrator.tool_registry.get_tool("browser")
    result = await tool._execute_async(
        task="搜索 Python",
        headless=True,
        timeout=30
    )
    
    assert result.success
```

## 故障排查

### 问题 1: ImportError: browser-use not installed

**解决方案：**
```bash
pip install browser-use
playwright install chromium
```

### 问题 2: LLM 适配器错误

**解决方案：**
- 检查 LLMService 是否正确初始化
- 确保异步调用正确处理
- 查看日志了解详细错误

### 问题 3: 浏览器启动失败

**解决方案：**
- 确保已安装 Playwright 浏览器：`playwright install chromium`
- 检查系统权限
- 尝试使用无头模式

### 问题 4: 任务执行超时

**解决方案：**
- 增加超时时间
- 简化任务描述
- 检查网络连接

## 下一步

1. ✅ 实现 BrowserTool
2. ✅ 创建 LLM 适配器
3. ✅ 在 Orchestrator 中注册
4. ⏳ 编写单元测试
5. ⏳ 编写集成测试
6. ⏳ 更新文档
7. ⏳ 性能优化
8. ⏳ 错误处理完善




