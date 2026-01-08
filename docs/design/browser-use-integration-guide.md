# Browser-use 快速集成指南

## 快速开始

### 1. 安装依赖

```bash
pip install browser-use
playwright install chromium
```

### 2. 创建 BrowserTool（简化版）

由于 Browser-use 需要 LangChain 兼容的 LLM，而项目使用 AsyncOpenAI，有两种方案：

#### 方案 A: 使用 LangChain OpenAI（推荐，最简单）

直接使用 LangChain 的 OpenAI 包装器，复用项目的 API Key：

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
    from langchain_openai import ChatOpenAI
    BROWSER_USE_AVAILABLE = True
except ImportError:
    BROWSER_USE_AVAILABLE = False
    Agent = None
    ChatOpenAI = None


class BrowserTool(Tool):
    """浏览器自动化工具 - 基于 Browser-use"""
    
    def __init__(self, llm_service: Optional['LLMService'] = None):
        """初始化浏览器工具"""
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
                ),
                required=True
            ),
            ToolParameter(
                name="headless",
                type="boolean",
                description="是否使用无头模式（默认 False）",
                required=False,
                default=False
            ),
            ToolParameter(
                name="timeout",
                type="integer",
                description="任务超时时间（秒），默认 60",
                required=False,
                default=60
            )
        ]
        
        super().__init__(
            name="browser",
            description=(
                "浏览器自动化工具，支持通过自然语言指令控制浏览器执行各种任务。"
                "可以用于网页搜索、信息提取、表单填写等场景。"
            ),
            parameters=parameters
        )
        
        self.llm_service = llm_service
        self.conversation_path = Path("data/browser_conversations")
        self.conversation_path.mkdir(parents=True, exist_ok=True)
    
    def _create_llm(self):
        """创建 LangChain LLM 实例"""
        # 从环境变量获取 API Key（与项目配置一致）
        api_key = os.environ.get('DEEPSEEK_API_KEY')
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY 环境变量未设置")
        
        # 使用 LangChain 的 OpenAI 兼容接口
        # DeepSeek 兼容 OpenAI API
        return ChatOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            temperature=0.7
        )
    
    def execute(self, **kwargs) -> ToolResult:
        """执行浏览器任务"""
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self._execute_async(**kwargs)
                )
                timeout = kwargs.get("timeout", 60) + 10
                return future.result(timeout=timeout)
        except RuntimeError:
            return asyncio.run(self._execute_async(**kwargs))
    
    async def _execute_async(self, **kwargs) -> ToolResult:
        """异步执行浏览器任务"""
        if not BROWSER_USE_AVAILABLE:
            return ToolResult(
                success=False,
                error="browser-use is not installed"
            )
        
        task = kwargs.get("task")
        if not task:
            return ToolResult(success=False, error="Task parameter is required")
        
        headless = kwargs.get("headless", False)
        timeout = kwargs.get("timeout", 60)
        
        try:
            # 创建 LLM 实例
            llm = self._create_llm()
            
            # 创建 Browser-use Agent
            agent = Agent(
                task=task,
                llm=llm,
                browser_config={
                    "headless": headless,
                    "save_conversation_path": str(self.conversation_path),
                    "timeout": timeout * 1000
                }
            )
            
            # 执行任务
            result = await asyncio.wait_for(
                agent.run(),
                timeout=timeout
            )
            
            return ToolResult(
                success=True,
                data={
                    "result": str(result) if result else "任务执行完成",
                    "task": task
                }
            )
            
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                error=f"任务执行超时（{timeout}秒）"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"任务执行失败: {str(e)}"
            )
```

#### 方案 B: 创建 LLM 适配器（更复杂但更灵活）

如果需要完全复用项目的 LLMService，可以创建适配器（见完整集成文档）。

### 3. 在 Orchestrator 中注册

```python
# backend/core/agent/orchestrator.py
# 在 _register_tools() 方法中添加：

# 注册浏览器工具
try:
    from backend.core.agent.tools.builtin.browser_tool import BrowserTool
    browser_tool = BrowserTool()  # 不需要传递 llm_service，内部会创建
    self.tool_registry.register(browser_tool)
    self.debug.log_orchestrator_step("注册工具", {"browser_tool": "registered"})
    logger.info("Browser tool registered successfully")
except ImportError as e:
    error_msg = f"Browser-use not installed: {str(e)}. Browser tool will not be available."
    logger.warning(error_msg)
except Exception as e:
    error_msg = f"Failed to register browser tool: {str(e)}. Browser tool will not be available."
    logger.warning(error_msg)
```

### 4. 更新工具导出

```python
# backend/core/agent/tools/builtin/__init__.py
from .browser_tool import BrowserTool

__all__ = [
    # ... 其他工具
    "BrowserTool",
]
```

## 使用示例

### 示例 1: 简单搜索

用户输入：
```
帮我搜索一下 Python 教程
```

LLM 会调用：
```json
{
    "name": "browser",
    "arguments": {
        "task": "搜索 Python 教程并总结前 3 个结果"
    }
}
```

### 示例 2: 复杂任务

用户输入：
```
在 GitHub 上找一些 Python 项目，按 stars 排序
```

LLM 会调用：
```json
{
    "name": "browser",
    "arguments": {
        "task": "在 GitHub 上搜索 Python 项目，按 stars 排序，提取前 5 个项目的名称和描述",
        "headless": false,
        "timeout": 120
    }
}
```

## 配置

### 环境变量

确保 `.env` 文件中有：
```bash
DEEPSEEK_API_KEY=your_api_key
DEEPSEEK_MODEL=deepseek-chat  # 可选，默认 deepseek-chat
```

### 浏览器配置

可以在 `BrowserTool.__init__()` 中自定义：
```python
browser_config = {
    "headless": False,  # 显示浏览器窗口
    "viewport": {"width": 1920, "height": 1080},
    "timeout": 30000,
    "save_conversation_path": "./data/browser_conversations"
}
```

## 优势

1. **简单集成**：使用 LangChain OpenAI 包装器，无需复杂的适配
2. **复用配置**：使用项目现有的 API Key 和模型配置
3. **易于调试**：默认显示浏览器窗口，可以观察执行过程
4. **自动处理**：Browser-use 自动处理页面交互、元素定位等

## 注意事项

1. **API Key**：确保 `DEEPSEEK_API_KEY` 已设置
2. **浏览器安装**：运行 `playwright install chromium`
3. **超时设置**：复杂任务建议增加超时时间
4. **内存占用**：浏览器实例占用内存较大，注意资源管理

## 故障排查

### 问题：ImportError: browser-use not installed

```bash
pip install browser-use
playwright install chromium
```

### 问题：浏览器启动失败

```bash
# 重新安装浏览器
playwright install --force chromium
```

### 问题：API Key 错误

检查 `.env` 文件中的 `DEEPSEEK_API_KEY` 是否正确设置。

## 下一步

1. ✅ 实现 BrowserTool（方案 A）
2. ⏳ 在 Orchestrator 中注册
3. ⏳ 测试基本功能
4. ⏳ 优化错误处理
5. ⏳ 添加单元测试


