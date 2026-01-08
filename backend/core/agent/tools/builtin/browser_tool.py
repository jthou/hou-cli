"""浏览器自动化工具实现 - 基于 Browser-use"""
import asyncio
import os
import logging
from typing import Dict, Any, Optional, TYPE_CHECKING
from pathlib import Path
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from backend.services.llm.llm_service import LLMService

try:
    from browser_use import Agent, Browser, BrowserProfile
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    BROWSER_USE_AVAILABLE = True
except ImportError:
    BROWSER_USE_AVAILABLE = False
    Agent = None
    Browser = None
    BrowserProfile = None
    ChatOpenAI = None
    HumanMessage = None


class BrowserTool(Tool):
    """浏览器自动化工具 - 基于 Browser-use
    
    允许 AI 助手通过自然语言指令控制浏览器执行各种任务，
    如网页搜索、表单填写、数据提取等。
    """
    
    def __init__(self, llm_service: Optional['LLMService'] = None):
        """
        初始化浏览器工具
        
        Args:
            llm_service: LLM 服务实例（可选，当前实现内部创建 LangChain LLM）
        """
        # 注意：即使 browser-use 未安装，也允许注册工具
        # 这样工具会出现在列表中，但执行时会返回错误提示安装依赖
        
        parameters = [
            ToolParameter(
                name="task",
                type="string",
                description=(
                    "要执行的浏览器任务，用自然语言描述。必须包含网站地址和具体操作。"
                    "\n典型场景示例："
                    "- '打开 www.jthou.com/mediawiki 网站，搜索与 TOF 泳池机器人相关的页面'"
                    "- '访问 www.example.com/blog 并查找关于 AI 的文章'"
                    "- '在 GitHub 上搜索 Python 项目，按 stars 排序，提取前 5 个'"
                    "- '打开 example.com 并提取页面标题和主要内容'"
                    "- '访问 news.example.com 并搜索最新的 AI 新闻'"
                    "\n重要提示："
                    "- 必须包含完整的网站地址（如：www.example.com 或 https://example.com）"
                    "- 明确说明要执行的操作（搜索、浏览、提取等）"
                    "- 如果要在网站内搜索，明确说明搜索关键词和位置"
                    "- 可以指定多个步骤，用逗号或分号分隔"
                    "\n适用场景："
                    "- 访问特定网站（优先使用 browser 而非 google_search）"
                    "- 在网站内搜索内容（如 MediaWiki、博客、论坛等）"
                    "- 浏览和提取特定页面内容"
                ),
                required=True
            ),
            ToolParameter(
                name="headless",
                type="boolean",
                description=(
                    "是否使用无头模式（默认 False，显示浏览器窗口）。"
                    "\n- False: 显示浏览器窗口，可以看到所有操作过程（推荐用于调试和观察）"
                    "\n- True: 无头模式，不显示浏览器窗口，后台运行（适合自动化任务）"
                    "\n注意：设置为 False 时，浏览器窗口会弹出，您可以直接观察操作过程"
                ),
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
        
        # 根据依赖是否可用，调整工具描述
        if BROWSER_USE_AVAILABLE:
            description = (
                "【重要】浏览器自动化工具 - 当用户要求'打开'、'访问'、'查看'网站时，必须使用此工具！"
                "\n\n核心功能："
                "- ✅ 访问特定网站并浏览页面（如：打开 www.google.com 并查看网页）"
                "- ✅ 在网站内搜索内容（如：在 MediaWiki 中搜索特定主题）"
                "- ✅ 提取和总结网页内容"
                "- ✅ 表单填写和提交"
                "- ✅ 多步骤任务自动化"
                "\n\n【使用场景 - 必须使用 browser 工具】："
                "- 用户说'打开 www.example.com' → 使用 browser"
                "- 用户说'访问 www.google.com 并查看网页' → 使用 browser"
                "- 用户说'打开网站' → 使用 browser"
                "- 用户说'查看某个网站' → 使用 browser"
                "- 用户说'在网站内搜索' → 使用 browser"
                "- 用户说'浏览页面' → 使用 browser"
                "\n\n【与 google_search 的区别】："
                "- google_search: 用于在 Google 上搜索网络信息，获取搜索结果列表（用户说'搜索'或'查找'时使用）"
                "- browser: 用于访问特定网站、在网站内搜索、浏览和提取页面内容（用户说'打开'、'访问'、'查看'时使用）"
                "\n\n【关键判断标准】："
                "- 如果用户提到具体的网站地址（如 www.google.com、example.com）→ 使用 browser"
                "- 如果用户说'打开'、'访问'、'查看'网站 → 使用 browser"
                "- 如果用户说'搜索'但没有指定网站 → 使用 google_search"
                "\n\n优势："
                "- 语义理解：通过自然语言描述任务，自动处理交互细节"
                "- 智能定位：自动识别页面元素，适应页面变化"
                "- 错误恢复：内置重试和错误处理机制"
                "\n\n注意："
                "- 任务描述要清晰具体，包含网站地址和要执行的操作"
                "- 示例：'打开 www.google.com 并查看网页'"
                "- 默认显示浏览器窗口，便于观察执行过程"
            )
        else:
            description = (
                "浏览器自动化工具（需要安装依赖）。"
                "\n要使用此工具，请先安装："
                "pip install browser-use langchain-openai playwright"
                "\n然后运行：playwright install chromium"
            )
        
        super().__init__(
            name="browser",
            description=description,
            parameters=parameters
        )
        
        self.llm_service = llm_service
        # 创建对话保存目录
        self.conversation_path = Path("data/browser_conversations")
        self.conversation_path.mkdir(parents=True, exist_ok=True)
    
    def _create_llm(self):
        """创建 LangChain LLM 实例并包装以兼容 browser-use"""
        # 从环境变量获取 API Key（与项目配置一致）
        api_key = os.environ.get('DEEPSEEK_API_KEY')
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY 环境变量未设置")
        
        # 配置验证：API Key 格式验证
        api_key = api_key.strip()
        if not api_key or len(api_key) < 10:
            raise ValueError("API Key 格式无效：长度不足或为空")
        
        # 使用 LangChain 的 OpenAI 兼容接口
        # DeepSeek 兼容 OpenAI API
        # base_url 可以使用 https://api.deepseek.com 或 https://api.deepseek.com/v1
        # 根据 DeepSeek 文档，两种格式都可以，使用 /v1 路径以提高兼容性
        base_url = "https://api.deepseek.com/v1"
        model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        
        logger.info(f"创建 ChatOpenAI 实例: base_url={base_url}, model={model_name}")
        
        # 创建 ChatOpenAI 实例
        # 注意：ChatOpenAI 可能不支持直接传递 http_async_client 参数
        # 如果需要跳过代理，可能需要通过环境变量或 LangChain 的其他配置方式
        original_llm = ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model_name,
            temperature=0.7,
            max_tokens=2000
        )
        
        logger.info(f"✅ ChatOpenAI 实例创建成功")
        
        # browser-use 使用 Pydantic 验证，期望 LLM 对象有 provider 字段
        # 但 ChatOpenAI 没有这个字段，而且 ainvoke 是方法不是字段
        # 解决方案：创建一个完整的包装类，代理所有属性和方法
        
        class LLMWrapper:
            """完整包装 ChatOpenAI 以兼容 browser-use 的 BaseChatModel 接口"""
            def __init__(self, llm_instance):
                # 使用 object.__setattr__ 绕过 Pydantic 验证
                object.__setattr__(self, '_llm', llm_instance)
                # browser-use 的 BaseChatModel 需要的字段
                object.__setattr__(self, 'provider', 'openai')
                object.__setattr__(self, 'model_name', getattr(llm_instance, 'model_name', getattr(llm_instance, 'model', 'deepseek-chat')))
                object.__setattr__(self, 'name', getattr(llm_instance, 'name', 'ChatOpenAI'))
                # 确保 ainvoke 和 invoke 方法可以被访问（作为属性引用）
                if hasattr(llm_instance, 'ainvoke'):
                    object.__setattr__(self, 'ainvoke', llm_instance.ainvoke)
                if hasattr(llm_instance, 'invoke'):
                    object.__setattr__(self, 'invoke', llm_instance.invoke)
            
            def __getattribute__(self, name):
                """确保所有需要的字段能被直接访问，避免无限递归"""
                # 先检查是否是内部属性（避免无限递归）
                if name == '_llm':
                    return object.__getattribute__(self, '_llm')
                
                # browser-use 需要的字段
                if name == 'provider':
                    return 'openai'
                
                if name == 'model_name':
                    try:
                        return object.__getattribute__(self, 'model_name')
                    except AttributeError:
                        llm = object.__getattribute__(self, '_llm')
                        # ChatOpenAI 可能有 model_name 或 model 属性
                        return getattr(llm, 'model_name', getattr(llm, 'model', 'deepseek-chat'))
                
                # browser-use 可能也会访问 model 属性
                if name == 'model':
                    llm = object.__getattribute__(self, '_llm')
                    # 尝试从原始 LLM 获取 model，如果没有则返回 model_name
                    return getattr(llm, 'model', getattr(llm, 'model_name', 'deepseek-chat'))
                
                if name == 'name':
                    try:
                        return object.__getattribute__(self, 'name')
                    except AttributeError:
                        llm = object.__getattribute__(self, '_llm')
                        return getattr(llm, 'name', 'ChatOpenAI')
                
                # 先检查是否是内部存储的属性
                if name in ('ainvoke', 'invoke'):
                    try:
                        return object.__getattribute__(self, name)
                    except AttributeError:
                        # 如果内部没有，从原始 LLM 获取
                        llm = object.__getattribute__(self, '_llm')
                        return getattr(llm, name)
                
                # 其他属性：先尝试从包装类获取，再从原始 LLM 获取
                try:
                    return object.__getattribute__(self, name)
                except AttributeError:
                    llm = object.__getattribute__(self, '_llm')
                    return getattr(llm, name)
            
            def __setattr__(self, name, value):
                """设置属性"""
                if name in ('_llm', 'provider', 'model_name', 'name', 'ainvoke', 'invoke'):
                    object.__setattr__(self, name, value)
                else:
                    setattr(object.__getattribute__(self, '_llm'), name, value)
        
        # 始终使用包装类，确保兼容性
        llm = LLMWrapper(original_llm)
        
        # 验证关键属性（browser-use 的 BaseChatModel 需要的字段）
        required_fields = ['provider', 'model_name', 'name', 'ainvoke']
        missing_fields = [field for field in required_fields if not hasattr(llm, field)]
        if missing_fields:
            raise RuntimeError(f"包装类缺少必需的字段: {missing_fields}")
        
        logger.info(f"✅ LLM 包装完成，类型: {type(llm)}")
        logger.info(f"   - provider: {getattr(llm, 'provider', 'N/A')}")
        logger.info(f"   - model_name: {getattr(llm, 'model_name', 'N/A')}")
        logger.info(f"   - name: {getattr(llm, 'name', 'N/A')}")
        logger.info(f"   - 有 ainvoke: {hasattr(llm, 'ainvoke')}")
        return llm
    
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
                error=(
                    "browser-use is not installed. "
                    "Please install it with: pip install browser-use && playwright install chromium"
                )
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
            # 检查 Playwright 浏览器是否已安装
            try:
                import subprocess
                result = subprocess.run(
                    ["playwright", "install", "--dry-run", "chromium"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode != 0:
                    logger.warning("⚠️ Playwright Chromium 可能未正确安装，建议运行: playwright install chromium")
            except Exception as check_error:
                logger.warning(f"⚠️ 无法检查 Playwright 安装状态: {check_error}")
            
            # 确保使用本地浏览器：设置环境变量（如果 browser-use 检查环境变量）
            # 注意：这不会覆盖已设置的环境变量，但可以确保 Browser 使用本地模式
            import os as os_module
            # 如果 BROWSER_USE_API_KEY 未设置，确保 browser-use 使用本地浏览器
            if "BROWSER_USE_API_KEY" not in os_module.environ:
                logger.info("✅ 未设置 BROWSER_USE_API_KEY，将使用本地 Playwright 浏览器")
            else:
                logger.warning("⚠️ 检测到 BROWSER_USE_API_KEY 环境变量，browser-use 可能尝试使用云浏览器")
            
            # 创建 LLM 实例
            llm = self._create_llm()
            
            # LLM 已经在 _create_llm 中包装，确保有 provider 和 ainvoke
            # 不需要额外处理
            
            # 根据 browser-use 文档，正确的用法是：
            # 1. 先创建 Browser 实例（headless 是 Browser 的参数）
            # 2. 然后创建 Agent 实例（传入 browser 和 llm）
            
            # 如果 headless=False，添加日志提示
            if not headless:
                logger.info("浏览器将以有界面模式运行，您可以看到浏览器操作过程")
                logger.info(f"任务: {task}")
            else:
                logger.info("浏览器将以无头模式运行（不显示窗口）")
            
            # 创建 Browser 实例
            # 根据 browser-use 文档和错误分析，问题可能在于 Browser 的创建方式
            # 尝试使用最简单的配置，让 browser-use 自动处理 CDP 连接
            
            # 检查环境变量
            import os as os_module
            has_api_key = "BROWSER_USE_API_KEY" in os_module.environ
            if has_api_key:
                logger.warning("⚠️ 检测到 BROWSER_USE_API_KEY 环境变量，browser-use 可能尝试使用云浏览器")
            else:
                logger.info("✅ 未设置 BROWSER_USE_API_KEY，将使用本地 Playwright 浏览器")
            
            # 使用最简单的配置，避免复杂的参数导致问题
            # 根据测试，Browser 创建时 browser_profile 设置是正确的
            # 问题可能在于 browser-use 内部获取 CDP URL 的方式
            browser_kwargs = {
                "headless": headless,
                "is_local": True,  # 明确指定使用本地浏览器
                "use_cloud": False,  # 明确禁用云浏览器
            }
            
            # 不设置太多参数，让 browser-use 使用默认值
            # 避免 window_size、viewport 等参数可能导致的问题
            
            logger.info(f"创建 Browser 实例，参数: {browser_kwargs}")
            
            # 创建 Browser 实例（不重试，直接创建）
            browser = Browser(**browser_kwargs)
            logger.info("✅ Browser 实例创建成功")
            
            # 验证并修复 Browser 的 browser_profile 设置
            # 根据 browser-use 源代码，BrowserSession.on_BrowserStartEvent 检查 browser_profile.use_cloud
            # 需要确保 browser_profile.use_cloud = False, is_local = True
            logger.info("🔍 验证 Browser 的 browser_profile 设置...")
            try:
                # 确保 browser_profile 设置正确
                if hasattr(browser, 'browser_profile'):
                    browser_profile = browser.browser_profile
                    logger.info(f"   - browser_profile.use_cloud: {getattr(browser_profile, 'use_cloud', 'N/A')}")
                    logger.info(f"   - browser_profile.is_local: {getattr(browser_profile, 'is_local', 'N/A')}")
                    logger.info(f"   - browser_profile.cloud_browser_params: {getattr(browser_profile, 'cloud_browser_params', 'N/A')}")
                    
                    # 确保 use_cloud 是 False
                    if hasattr(browser_profile, 'use_cloud') and browser_profile.use_cloud:
                        logger.warning("⚠️ browser_profile.use_cloud 是 True，强制设置为 False")
                        browser_profile.use_cloud = False
                    
                    # 确保 cloud_browser_params 是 None
                    if hasattr(browser_profile, 'cloud_browser_params') and browser_profile.cloud_browser_params is not None:
                        logger.warning("⚠️ browser_profile.cloud_browser_params 不是 None，强制设置为 None")
                        browser_profile.cloud_browser_params = None
                    
                    # 确保 is_local 是 True
                    if hasattr(browser_profile, 'is_local') and not browser_profile.is_local:
                        logger.warning("⚠️ browser_profile.is_local 是 False，强制设置为 True")
                        browser_profile.is_local = True
                    
                    logger.info("✅ Browser browser_profile 验证完成")
            except Exception as profile_error:
                logger.warning(f"⚠️ 无法验证 browser_profile: {profile_error}")
            
            # 创建 Agent 实例
            # 根据文档，Agent 的参数包括：task, llm, browser, tools 等
            # 注意：根据文档，Agent 没有 instructions 参数
            # 如果需要额外的指令，应该包含在 task 描述中，或使用 extend_system_message
            
            agent_kwargs = {
                "task": task,
                "llm": llm,
                "browser": browser,  # 传入 Browser 实例
            }
            
            # 如果提供了 instructions，可以通过 extend_system_message 添加
            # 或者将它们合并到 task 中
            if instructions:
                # 将 instructions 合并到 task 中
                instructions_text = "\n".join([f"- {inst}" for inst in instructions])
                agent_kwargs["task"] = f"{task}\n\n额外指令：\n{instructions_text}"
                logger.debug("已将 instructions 合并到 task 中")
            
            # 验证 LLM 是否正常（在创建 Agent 之前）
            logger.info(f"🔍 创建 Agent 前验证 LLM，类型: {type(llm)}")
            required_fields = ['provider', 'model_name', 'name', 'ainvoke']
            for field in required_fields:
                has_field = hasattr(llm, field)
                logger.info(f"   - 有 {field}: {has_field}")
                if has_field:
                    value = getattr(llm, field)
                    logger.info(f"     {field} 值/类型: {value if isinstance(value, str) else type(value)}")
            
            # 如果缺少必需字段，抛出错误
            missing_fields = [field for field in required_fields if not hasattr(llm, field)]
            if missing_fields:
                raise RuntimeError(f"LLM 缺少必需的字段: {missing_fields}")
            
            # 测试 LLM API 是否能正常工作（提前发现问题）
            logger.info("🧪 测试 LLM API 调用...")
            try:
                # 使用简单的字符串测试 LLM API
                # ChatOpenAI 的 ainvoke 可以接受字符串或消息列表
                if HumanMessage is not None:
                    test_message = HumanMessage(content="Hello")
                    test_result = await llm.ainvoke([test_message])
                else:
                    # 如果 HumanMessage 不可用，尝试直接使用字符串
                    # 注意：某些版本的 ChatOpenAI 可能需要消息列表
                    test_result = await llm.ainvoke("Hello")
                logger.info(f"✅ LLM API 测试成功，响应类型: {type(test_result)}")
            except Exception as test_error:
                error_msg = str(test_error)
                logger.error(f"❌ LLM API 测试失败: {error_msg}")
                # 如果是 JSON 解析错误，提供更详细的错误信息
                if "Expecting value" in error_msg or "JSON" in error_msg or "line 1 column 1" in error_msg:
                    # 获取 base_url 信息
                    base_url_info = "N/A"
                    try:
                        if hasattr(llm, '_llm'):
                            base_url_info = getattr(llm._llm, 'openai_api_base', 'N/A')
                        else:
                            base_url_info = getattr(llm, 'openai_api_base', 'N/A')
                    except:
                        pass
                    raise ValueError(
                        f"LLM API 配置错误，无法解析响应（JSON 解析失败）\n"
                        f"错误详情: {error_msg}\n"
                        f"可能的原因：\n"
                        f"1. API Key 无效或已过期\n"
                        f"2. base_url 配置错误（当前: {base_url_info}）\n"
                        f"3. 网络连接问题或代理配置问题\n"
                        f"4. DeepSeek API 服务暂时不可用\n"
                        f"请检查 API Key 和网络连接"
                    )
                raise
            
            logger.debug(f"创建 Agent，参数: task, llm (类型: {type(llm)}), browser (headless={headless})")
            agent = Agent(**agent_kwargs)
            
            logger.info("Browser-use Agent 已创建，开始执行任务...")
            
            # 执行任务（带超时控制）
            logger.info(f"开始执行浏览器任务，超时时间: {timeout}秒")
            result = await asyncio.wait_for(
                agent.run(),
                timeout=timeout
            )
            
            logger.info("浏览器任务执行完成")
            result_str = str(result) if result else "任务执行完成"
            
            return ToolResult(
                success=True,
                data={
                    "result": result_str,
                    "task": task,
                    "message": "浏览器任务执行成功",
                    "headless": headless,
                    "note": "如果 headless=False，您应该能看到浏览器窗口的操作过程"
                }
            )
            
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                error=f"浏览器任务执行超时（{timeout}秒）"
            )
        except ValueError as e:
            # API Key 配置错误
            return ToolResult(
                success=False,
                error=f"LLM 配置错误: {str(e)}"
            )
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            # 如果是 CDP 连接相关的错误，提供更详细的诊断信息
            if "Expecting value" in error_msg or "JSONDecodeError" in error_type or "CDP" in error_msg:
                detailed_error = (
                    f"浏览器 CDP 连接失败: {error_msg}\n"
                    f"\n可能的原因：\n"
                    f"1. Playwright Chromium 浏览器未正确安装\n"
                    f"   解决方案：运行 'playwright install chromium'\n"
                    f"2. 浏览器启动后 CDP 端点未准备好\n"
                    f"   解决方案：等待几秒后重试，或检查系统资源\n"
                    f"3. 浏览器进程冲突\n"
                    f"   解决方案：关闭其他浏览器实例后重试\n"
                    f"\n错误类型: {error_type}"
                )
                logger.error(detailed_error)
                return ToolResult(
                    success=False,
                    error=detailed_error
                )
            
            return ToolResult(
                success=False,
                error=f"浏览器任务执行失败: {error_msg} (类型: {error_type})"
            )

