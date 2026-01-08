# LLM 浏览器自动化方案

本文档总结了能让 LLM 使用、交互并查看浏览器内容的多种技术方案。

## 方案概览

### 1. Playwright + LangChain（推荐）

**特点：**
- ✅ 功能强大，支持现代浏览器（Chrome、Firefox、Safari）
- ✅ 支持无头和有头模式
- ✅ 可以截图、获取 DOM、执行 JavaScript
- ✅ LangChain 已有现成的工具集
- ✅ 异步支持，性能好

**实现方式：**
```python
from playwright.async_api import async_playwright
from langchain_community.tools.playwright import (
    ClickTool,
    NavigateTool,
    ExtractTextTool,
    GetElementsTool
)

# 初始化浏览器
async with async_playwright() as p:
    browser = await p.chromium.launch(headless=False)
    page = await browser.new_page()
    
    # 导航到页面
    await page.goto("https://example.com")
    
    # 获取页面内容
    content = await page.content()
    screenshot = await page.screenshot()
    
    # 执行操作
    await page.click("button#submit")
```

**项目集成：**
- 项目中已安装 `langchain_community`，包含 Playwright 工具
- 可以创建 `browser_tool.py` 封装 Playwright 功能

**依赖：**
```bash
pip install playwright langchain-community
playwright install chromium
```

---

### 2. Browser-use（专为 LLM 设计）⭐ **强烈推荐**

**特点：**
- ✅ **专门为 LLM 设计的浏览器工具**，提供最高层次的抽象
- ✅ **无代码门槛**：通过自然语言指令直接控制浏览器
- ✅ **语义定位元素**：通过语义理解网页元素，适应页面变化
- ✅ **实时执行**：指令输入后立即执行
- ✅ **支持多种 LLM**：OpenAI、Google Gemini、DeepSeek、Claude 等
- ✅ **提供 TUI 模式**：交互式终端界面，便于测试和调试
- ✅ **基于 MCP 协议**：标准化接口，易于集成
- ✅ **结合计算机视觉和 HTML 解析**：更智能的元素识别

**GitHub:** https://github.com/browser-use/browser-use

**实现方式：**
```python
from browser_use import Agent
from langchain_openai import ChatOpenAI

# 创建 LLM 实例
llm = ChatOpenAI(model="gpt-4", temperature=0)

# 创建浏览器 Agent
agent = Agent(
    task="搜索 Python 教程并总结前 3 个结果",
    llm=llm,
    browser_config={
        "headless": False,  # 显示浏览器窗口
        "save_conversation_path": "./browser_conversations"  # 保存对话
    }
)

# 执行任务
result = await agent.run()
print(result)
```

**高级用法：**
```python
# 自定义浏览器配置
agent = Agent(
    task="在 GitHub 上搜索 Python 项目",
    llm=llm,
    browser_config={
        "headless": False,
        "viewport": {"width": 1920, "height": 1080},
        "user_agent": "Mozilla/5.0...",
        "timeout": 30000
    },
    # 可以指定具体的操作步骤
    instructions=[
        "导航到 github.com",
        "在搜索框输入 'python'",
        "点击搜索按钮",
        "提取前 5 个结果"
    ]
)
```

**核心优势：**
1. **LLM 原生设计**：API 完全围绕 LLM 使用场景设计
2. **智能元素定位**：不需要精确的 CSS 选择器，通过语义理解定位
3. **任务级抽象**：直接描述任务，自动处理交互细节
4. **多 LLM 支持**：轻松切换不同的 LLM 提供商
5. **对话式交互**：支持多轮对话，可以逐步完成任务
6. **错误自动恢复**：内置错误处理和重试机制
7. **可视化调试**：TUI 模式可以实时查看执行过程

**适用场景：**
- ✅ LLM Agent 需要自动化网页操作
- ✅ 需要处理动态内容和复杂交互
- ✅ 希望减少底层浏览器 API 的复杂性
- ✅ 需要快速原型开发和测试

---

### 3. MCP Browser（Model Context Protocol）

**特点：**
- ✅ 基于 MCP 协议，标准化接口
- ✅ 支持浏览器快照（accessibility snapshot）
- ✅ 可以点击、输入、导航等操作
- ✅ 项目已有 MCP 集成基础

**实现方式：**
```python
# MCP Browser 提供以下功能：
# - browser_navigate: 导航到 URL
# - browser_snapshot: 获取页面可访问性快照
# - browser_click: 点击元素
# - browser_type: 输入文本
# - browser_take_screenshot: 截图
```

**优势：**
- 标准化协议，易于集成
- 快照功能提供结构化页面信息
- 适合与现有 MCP 服务器集成

**注意：** 项目代码中已有 MCP 相关实现，可以扩展支持浏览器功能

---

### 4. Selenium WebDriver

**特点：**
- ✅ 成熟稳定，生态丰富
- ✅ 支持多种浏览器
- ✅ 有丰富的文档和社区支持

**缺点：**
- ❌ 性能相对较慢
- ❌ 配置相对复杂
- ❌ 主要面向传统自动化测试

**实现方式：**
```python
from selenium import webdriver
from selenium.webdriver.common.by import By

driver = webdriver.Chrome()
driver.get("https://example.com")
element = driver.find_element(By.ID, "search")
element.send_keys("Python")
driver.quit()
```

---

### 5. Puppeteer（Node.js）

**特点：**
- ✅ 性能优秀
- ✅ 支持 Chrome DevTools Protocol
- ✅ 适合 Node.js 环境

**缺点：**
- ❌ 需要 Node.js 环境
- ❌ Python 项目集成需要额外桥接

---

## 推荐方案对比

| 方案 | 易用性 | 性能 | LLM 适配 | 项目集成难度 | 开发效率 | 推荐度 |
|------|--------|------|----------|--------------|----------|--------|
| **Browser-use** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **MCP Browser** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Playwright + LangChain** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Selenium** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |

**关键差异：**
- **Browser-use**：专为 LLM 设计，提供任务级抽象，开发最快
- **MCP Browser**：标准化协议，适合已有 MCP 架构的项目
- **Playwright**：功能最强大，但需要更多底层代码
- **Selenium**：传统方案，适合测试场景

## 针对本项目的建议

### 方案 1：使用 Browser-use（最推荐）⭐

**理由：**
1. **专为 LLM 设计**：API 完全符合 LLM Agent 的使用场景
2. **开发效率最高**：任务级抽象，无需处理底层浏览器 API
3. **智能元素定位**：语义理解，适应页面变化，减少维护成本
4. **多 LLM 支持**：项目已支持多种 LLM，可以无缝集成
5. **错误处理完善**：内置重试和错误恢复机制
6. **易于调试**：TUI 模式可以实时查看执行过程
7. **基于 MCP**：项目已有 MCP 基础，可以复用架构

**实现步骤：**
1. 安装 browser-use：`pip install browser-use`
2. 在 `backend/core/agent/tools/builtin/` 创建 `browser_tool.py`
3. 封装 Browser-use Agent 为 Tool
4. 集成到现有的 LLM 服务（支持 OpenAI、DeepSeek 等）
5. 注册到工具注册表

**集成示例：**
```python
# backend/core/agent/tools/builtin/browser_tool.py
from browser_use import Agent
from backend.services.llm.llm_service import LLMService

class BrowserTool(Tool):
    def __init__(self, llm_service: LLMService):
        # 使用项目现有的 LLM 服务
        self.llm = llm_service.get_llm()
        # ... 参数定义
```

### 方案 2：使用 MCP Browser

**理由：**
1. 项目已有 MCP 集成基础（`6b942abc` 提交显示已添加 MCP 服务器集成支持）
2. MCP Browser 提供标准化接口，易于维护
3. 快照功能提供结构化信息，适合 LLM 理解
4. 可以复用现有的 MCP 架构

**实现步骤：**
1. 配置 MCP Browser 服务器
2. 在 `backend/core/agent/tools/` 创建 `browser_tool.py`
3. 封装 MCP Browser 功能为 Tool
4. 注册到工具注册表

### 方案 3：使用 Playwright + LangChain

**理由：**
1. 项目中已安装 `langchain_community`，包含 Playwright 工具
2. 功能强大，可以满足复杂需求
3. 有丰富的文档和示例

**实现步骤：**
1. 安装 Playwright：`pip install playwright && playwright install chromium`
2. 创建 `backend/core/agent/tools/builtin/browser_tool.py`
3. 封装 LangChain Playwright 工具
4. 注册到工具注册表

### 方案 3：使用 Browser-use

**理由：**
1. 专为 LLM 设计，API 简洁
2. 内置高级功能，减少开发量

**实现步骤：**
1. 安装：`pip install browser-use`
2. 创建工具封装
3. 集成到现有工具系统

## 功能需求分析

### 核心功能
- ✅ 导航到 URL
- ✅ 获取页面内容（文本、HTML、截图）
- ✅ 点击元素
- ✅ 输入文本
- ✅ 滚动页面
- ✅ 等待元素加载
- ✅ 执行 JavaScript

### 高级功能
- ✅ 表单填写和提交
- ✅ 文件上传/下载
- ✅ Cookie 和会话管理
- ✅ 多标签页管理
- ✅ 网络请求拦截

### LLM 特定需求
- ✅ 页面内容结构化提取
- ✅ 视觉快照（accessibility snapshot）
- ✅ 元素定位和描述
- ✅ 操作结果反馈

## 实现示例

### 示例 1：使用 Browser-use（推荐）

```python
# backend/core/agent/tools/builtin/browser_tool.py
from typing import Dict, Any, Optional
from browser_use import Agent
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from backend.services.llm.llm_service import LLMService

class BrowserTool(Tool):
    """浏览器工具 - 基于 Browser-use"""
    
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        parameters = [
            ToolParameter(
                name="task",
                type="string",
                description="要执行的浏览器任务，用自然语言描述，例如：'搜索 Python 教程'、'在 GitHub 上查找项目'",
                required=True
            ),
            ToolParameter(
                name="headless",
                type="boolean",
                description="是否使用无头模式（默认 False，显示浏览器窗口）",
                required=False,
                default=False
            ),
            ToolParameter(
                name="instructions",
                type="array",
                description="可选的操作步骤列表，用于更精确的控制",
                required=False
            )
        ]
        super().__init__(
            name="browser",
            description="浏览器自动化工具，支持通过自然语言指令控制浏览器执行各种任务",
            parameters=parameters
        )
    
    async def _execute_async(self, **kwargs) -> ToolResult:
        try:
            task = kwargs.get("task")
            headless = kwargs.get("headless", False)
            instructions = kwargs.get("instructions")
            
            # 获取 LLM 实例
            llm = await self.llm_service.get_llm_async()
            
            # 创建 Browser-use Agent
            agent = Agent(
                task=task,
                llm=llm,
                browser_config={
                    "headless": headless,
                    "save_conversation_path": "./data/browser_conversations"
                },
                instructions=instructions
            )
            
            # 执行任务
            result = await agent.run()
            
            return ToolResult(
                success=True,
                data={
                    "result": result,
                    "task": task,
                    "message": "浏览器任务执行成功"
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"浏览器任务执行失败: {str(e)}"
            )
```

### 示例 2：使用 MCP Browser

```python
# backend/core/agent/tools/builtin/browser_tool.py
from typing import Dict, Any, Optional
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter

class BrowserTool(Tool):
    """浏览器工具 - 基于 MCP Browser"""
    
    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        parameters = [
            ToolParameter(
                name="action",
                type="string",
                description="操作类型：navigate, snapshot, click, type, screenshot",
                required=True,
                enum=["navigate", "snapshot", "click", "type", "screenshot"]
            ),
            ToolParameter(
                name="url",
                type="string",
                description="要访问的 URL（navigate 操作必需）",
                required=False
            ),
            # ... 其他参数
        ]
        super().__init__(
            name="browser",
            description="浏览器自动化工具，支持导航、点击、输入等操作",
            parameters=parameters
        )
    
    async def _execute_async(self, **kwargs) -> ToolResult:
        action = kwargs.get("action")
        
        if action == "navigate":
            url = kwargs.get("url")
            await self.mcp_client.browser_navigate(url=url)
            return ToolResult(success=True, data={"message": f"已导航到 {url}"})
        
        elif action == "snapshot":
            snapshot = await self.mcp_client.browser_snapshot()
            return ToolResult(success=True, data={"snapshot": snapshot})
        
        # ... 其他操作
```

### 示例 3：使用 Playwright

```python
# backend/core/agent/tools/builtin/browser_tool.py
from playwright.async_api import async_playwright
from typing import Dict, Any

class BrowserTool(Tool):
    """浏览器工具 - 基于 Playwright"""
    
    def __init__(self):
        # ... 参数定义
        self.browser = None
        self.page = None
    
    async def _initialize_browser(self):
        """初始化浏览器"""
        if not self.browser:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=False)
            self.page = await self.browser.new_page()
    
    async def _execute_async(self, **kwargs) -> ToolResult:
        await self._initialize_browser()
        action = kwargs.get("action")
        
        if action == "navigate":
            url = kwargs.get("url")
            await self.page.goto(url)
            content = await self.page.content()
            return ToolResult(success=True, data={"url": url, "content": content})
        
        elif action == "screenshot":
            screenshot = await self.page.screenshot()
            return ToolResult(success=True, data={"screenshot": screenshot})
        
        # ... 其他操作
```

## 注意事项

### 安全性
- ⚠️ 浏览器工具可能访问任意网站，需要权限控制
- ⚠️ 避免执行恶意 JavaScript
- ⚠️ 限制文件系统访问

### 性能
- ⚠️ 浏览器实例占用内存较大
- ⚠️ 考虑使用浏览器池复用实例
- ⚠️ 长时间运行需要清理资源

### 稳定性
- ⚠️ 页面加载时间不确定，需要超时处理
- ⚠️ 元素可能动态加载，需要等待机制
- ⚠️ 网络错误需要优雅处理

## 下一步行动

1. **选择方案**：**强烈推荐使用 Browser-use**（专为 LLM 设计，开发效率最高）
2. **安装依赖**：`pip install browser-use`
3. **创建工具**：在 `backend/core/agent/tools/builtin/` 创建 `browser_tool.py`
4. **集成 LLM**：使用项目现有的 LLM 服务（支持 OpenAI、DeepSeek 等）
5. **编写测试**：创建单元测试和集成测试
6. **文档更新**：更新工具文档和使用示例
7. **注册工具**：在工具注册表中注册浏览器工具

## 为什么 Browser-use 更适合？

### 1. 开发效率对比

**Browser-use（任务级）：**
```python
agent = Agent(task="搜索 Python 教程", llm=llm)
result = await agent.run()  # 一行代码完成复杂任务
```

**Playwright（操作级）：**
```python
await page.goto("https://google.com")
await page.fill("input[name='q']", "Python 教程")
await page.click("button[type='submit']")
await page.wait_for_selector(".result")
results = await page.query_selector_all(".result")
# ... 需要编写大量代码
```

### 2. 智能程度对比

- **Browser-use**：语义理解元素，自动适应页面变化
- **Playwright**：需要精确的 CSS 选择器，页面变化需要手动更新

### 3. 错误处理对比

- **Browser-use**：内置重试和错误恢复机制
- **Playwright**：需要手动实现错误处理和重试逻辑

### 4. LLM 集成对比

- **Browser-use**：原生支持多种 LLM，API 设计完全围绕 LLM
- **Playwright**：需要自己封装 LLM 调用逻辑

## 参考资源

- [Playwright 官方文档](https://playwright.dev/python/)
- [LangChain Playwright 工具](https://python.langchain.com/docs/integrations/tools/playwright)
- [Browser-use GitHub](https://github.com/browser-use/browser-use)
- [MCP Browser 规范](https://modelcontextprotocol.io/)
- [Selenium 文档](https://www.selenium.dev/documentation/)

