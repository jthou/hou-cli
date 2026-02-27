"""浏览器自动化工具实现 - 基于 Browser-use（pip 包 browser-use）"""
import asyncio
import os
import logging
from typing import Optional, TYPE_CHECKING
from pathlib import Path
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from shared.platform_utils import get_app_data_dir

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from backend.services.llm.llm_service import LLMService

try:
    from browser_use import Agent, Browser
    BROWSER_USE_AVAILABLE = True
except ImportError as e:
    BROWSER_USE_AVAILABLE = False
    Agent = None
    Browser = None
    logger.warning(f"Failed to import browser-use: {e}. Install with: pip install browser-use")


class BrowserTool(Tool):
    """浏览器自动化工具 - 基于 Browser-use

    允许 AI 助手通过自然语言指令控制浏览器执行各种任务。
    支持可视化和无头模式两种模式。
    """

    def __init__(self, llm_service: Optional['LLMService'] = None):
        """初始化浏览器工具"""
        parameters = [
            ToolParameter(
                name="task",
                type="string",
                description=(
                    "要执行的浏览器任务，用自然语言描述。"
                    "例如：'打开 www.baidu.com 并搜索 Python'"
                ),
                required=True
            ),
            ToolParameter(
                name="headless",
                type="boolean",
                description=(
                    "是否使用无头模式。"
                    "False: 显示浏览器窗口（可视化模式）"
                    "True: 无头模式，不显示窗口"
                ),
                required=False,
                default=False
            ),
            ToolParameter(
                name="timeout",
                type="integer",
                description="任务超时时间（秒），默认 60",
                required=False,
                default=60
            ),
            ToolParameter(
                name="keep_alive",
                type="boolean",
                description=(
                    "是否保持浏览器会话存活。"
                    "True: 任务完成后保持浏览器打开，支持链式任务"
                    "False: 任务完成后关闭浏览器（默认）"
                ),
                required=False,
                default=False
            ),
            ToolParameter(
                name="extend_system_message",
                type="string",
                description=(
                    "扩展系统提示信息，用于优化 LLM 行为。"
                    "例如：'速度优化：尽可能简洁直接，快速达到目标'"
                ),
                required=False,
                default=None
            ),
            ToolParameter(
                name="user_data_dir",
                type="string",
                description=(
                    "浏览器用户数据目录路径（可选）。"
                    "用于保存登录状态、cookies、浏览器设置等。"
                    "如果不提供，每次启动都是新的浏览器会话（无登录状态）。"
                    "如果提供，会复用该目录中的登录状态和 cookies。"
                    "\n推荐路径（跨平台）："
                    "- macOS: ~/Library/Application Support/hou-cli/browser-profiles/{site_name}"
                    "- Linux: ~/.local/share/hou-cli/browser-profiles/{site_name}"
                    "- Windows: %LOCALAPPDATA%\\hou-cli\\browser-profiles\\{site_name}"
                    "\n示例："
                    "- 知乎: 'zhihu' 或完整路径"
                    "- GitHub: 'github' 或完整路径"
                    "\n如果只提供站点名称（如 'zhihu'），会自动使用项目配置目录。"
                ),
                required=False,
                default=None
            ),
            ToolParameter(
                name="save_session",
                type="boolean",
                description=(
                    "是否保存当前会话的登录状态（默认 false）。"
                    "如果为 true，会在 user_data_dir 中保存 cookies 和登录信息，"
                    "下次使用相同的 user_data_dir 时会自动恢复登录状态。"
                ),
                required=False,
                default=False
            )
        ]

        description = (
            "浏览器自动化工具。"
            "当用户要求'打开'、'访问'、'查看'网站时使用此工具。"
            "支持可视化和无头模式两种模式。"
            "\n会话管理："
            "- 支持通过 user_data_dir 参数保存登录状态和 cookies"
            "- 可以复用已登录的浏览器会话，适合需要登录的网站（如知乎、GitHub等）"
            "- 使用示例：user_data_dir='/path/to/profile' 来保存和复用登录状态"
        ) if BROWSER_USE_AVAILABLE else (
            "浏览器自动化工具（需要安装依赖）"
        )

        super().__init__(
            name="browser",
            description=description,
            parameters=parameters
        )

        self.llm_service = llm_service
    
    @classmethod
    def check_health(cls) -> tuple[bool, Optional[str]]:
        """
        检查 BrowserTool 是否可用（健康检查）
        
        检查项目：
        1. 环境变量控制（BROWSER_TOOL_ENABLED）
        2. browser-use 库是否已安装
        3. LLM API 配置是否完整
        4. 已知的 API 兼容性问题
        
        Returns:
            (is_available, error_message): 
            - is_available: True 表示工具可用，False 表示不可用
            - error_message: 如果不可用，返回错误原因；如果可用，返回 None
        """
        # 0. 检查环境变量控制
        enabled = os.getenv("BROWSER_TOOL_ENABLED", "true").lower()
        if enabled == "false":
            return False, "BROWSER_TOOL_ENABLED=false，工具已禁用"
        
        # 1. 检查 browser-use 是否安装
        if not BROWSER_USE_AVAILABLE:
            return False, "browser-use 库未安装"
        
        # 2. 检查 LLM API 配置
        try:
            from backend.services.llm.llm_service import LLMService
            llm_service = LLMService()
            
            # 检查默认模型配置
            default_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
            api_key = os.getenv("DEEPSEEK_API_KEY")
            
            if not api_key:
                return False, "DEEPSEEK_API_KEY 未设置"
            
            # 3. 检查已知的 API 兼容性问题
            # browser-use 库使用的 response_format 参数不被 DeepSeek API 支持
            # 但现在我们有了适配层，所以不再需要完全禁用 DeepSeek
            base_url = os.getenv("DEEPSEEK_BASE_URL", "")
            is_deepseek = "deepseek" in default_model.lower() or "deepseek" in base_url.lower()
            
            # 不再完全禁用 DeepSeek，因为我们有适配层
            # 如果是 DeepSeek，我们会使用适配层来绕过 response_format 限制
            if is_deepseek:
                logger.info("检测到 DeepSeek API，将使用适配层绕过 response_format 限制")
            
            # 尝试创建 LLM 实例（不实际调用 API，只检查配置）
            try:
                # 使用适配版本的 LLM 创建方法
                browser_llm = llm_service.get_browser_use_llm_with_adaptation(model=default_model)
                # 如果成功创建，说明配置正确
                # 注意：实际的 API 兼容性会在第一次使用时验证
                return True, None
            except ValueError as e:
                # API Key 未设置或其他配置问题
                error_msg = str(e)
                if "API key" in error_msg.lower() or "未设置" in error_msg:
                    return False, f"LLM API 配置错误: {error_msg}"
                raise
        except ImportError as e:
            return False, f"LLM 服务导入失败: {str(e)}"
        except Exception as e:
            # 其他错误
            error_str = str(e)
            if "response_format" in error_str.lower() or "unavailable" in error_str.lower():
                return False, f"LLM API 不兼容: browser-use 使用的 response_format 参数不被当前 LLM API 支持。错误: {error_str[:200]}"
            return False, f"健康检查失败: {str(e)}"
    
    def _get_browser_profile_dir(self, site_name: Optional[str] = None) -> Path:
        """
        获取浏览器配置文件目录（跨平台）
        
        Args:
            site_name: 站点名称（如 'zhihu'、'github'），如果提供，会创建子目录
            
        Returns:
            配置文件目录路径
        """
        from shared.platform_utils import get_app_data_dir
        base = get_app_data_dir()
        profile_dir = base / "browser-profiles"
        if site_name:
            profile_dir = profile_dir / site_name
        
        profile_dir.mkdir(parents=True, exist_ok=True)
        return profile_dir

    def _needs_vision(self, task: str) -> bool:
        """
        检测任务是否需要视觉功能
        
        Args:
            task: 任务描述
            
        Returns:
            bool: 是否需要视觉功能
        """
        # 检查强制启用标志
        force_vision = os.getenv("BROWSER_TOOL_USE_VISION", "false").lower() == "true"
        if force_vision:
            logger.info("BROWSER_TOOL_USE_VISION=true，强制启用视觉功能")
            return True
        
        # 关键词检测（明确的视觉关键词）
        vision_keywords = [
            "截图", "图片", "图像", "视觉", "识别", "视觉分析", "页面截图",
            "页面内容", "页面布局", "页面元素", "页面结构", "页面样式", "分析页面",
            "screenshot", "image", "visual", "recognize", "see", "view"
        ]
        
        task_lower = task.lower()
        for keyword in vision_keywords:
            if keyword in task_lower:
                logger.info(f"检测到视觉关键词 '{keyword}'，启用视觉功能")
                return True
        
        return False

    def _create_llm(self, use_vision: bool = False):
        """
        创建 LLM 实例（使用 LLMService 统一管理）
        
        Args:
            use_vision: 是否需要视觉功能
            
        Returns:
            LLM 实例（browser-use 兼容的 BaseChatModel）
        """
        # 使用 LLMService 统一管理模型配置
        if self.llm_service is None:
            from backend.services.llm.llm_service import LLMService
            self.llm_service = LLMService()
        
        # 如果需要视觉功能，直接使用视觉模型
        if use_vision:
            vision_model = os.getenv("BROWSER_TOOL_VISION_MODEL", "qwen-vl-max-2025-08-13")
            logger.info(f"使用视觉模型: {vision_model}")
            
            try:
                # 通过 LLMService 获取 browser-use 兼容的 LLM 实例
                browser_llm = self.llm_service.get_browser_use_llm_with_adaptation(model=vision_model)
                logger.info(f"视觉模型已创建: {vision_model}")
                return browser_llm
            except Exception as e:
                logger.warning(f"无法创建视觉模型，回退到 DeepSeek: {e}")
                # 回退到 DeepSeek
                default_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
                return self.llm_service.get_browser_use_llm_with_adaptation(
                    model=default_model,
                    disable_response_schema=True  # 防止 response_format 相关错误
                )
        
        # 使用默认模型（如果没有任务特定的智能选择需求）
        default_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        logger.info(f"使用默认模型: {default_model}")
        return self.llm_service.get_browser_use_llm_with_adaptation(
            model=default_model,
            disable_response_schema=True  # 防止 response_format 相关错误
        )

    def execute(self, **kwargs) -> ToolResult:
        """执行浏览器任务（同步包装异步方法）"""
        # 注意：Orchestrator 会优先使用 execute_async()，这个方法主要用于向后兼容
        # 如果已经在异步上下文中，不应该调用这个方法
        # 使用线程池执行，避免嵌套事件循环导致超时计算错误
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run,
                self._execute_async(**kwargs)
            )
            timeout = kwargs.get("timeout", 60) + 10
            return future.result(timeout=timeout)

    async def _execute_async(self, **kwargs) -> ToolResult:
        """异步执行浏览器任务"""
        if not BROWSER_USE_AVAILABLE:
            raise ImportError("browser-use 不可用，请检查依赖安装")

        task = kwargs.get("task")
        if not task:
            raise ValueError("task 参数是必需的")

        headless = kwargs.get("headless", False)
        timeout = kwargs.get("timeout", 60)
        keep_alive = kwargs.get("keep_alive", False)
        extend_system_message = kwargs.get("extend_system_message", None)
        user_data_dir = kwargs.get("user_data_dir", None)
        save_session = kwargs.get("save_session", False)

        # 限制超时时间范围：最小10秒，最大300秒（5分钟）
        if timeout < 10:
            timeout = 10
        elif timeout > 300:
            timeout = 300

        # 检测是否需要视觉功能
        use_vision = self._needs_vision(task)
        
        # 创建 LLM
        try:
            llm = self._create_llm(use_vision=use_vision)
        except Exception as e:
            # 如果 LLM 创建失败，记录错误但继续执行
            logger.error(f"创建 LLM 失败: {e}")
            raise

        # 创建 Browser 实例（根据官方文档推荐的方式）
        # 优化：根据 headless 模式调整等待时间
        # 无头模式可以更快，可视化模式需要稍长等待以确保渲染
        browser_kwargs = {
            "headless": headless,
            "is_local": True,
            "use_cloud": False,
            "keep_alive": keep_alive,  # 支持链式任务
        }
        
        # 在 macOS 上，显式设置 Chrome 路径以避免查找问题
        import platform
        if platform.system() == "Darwin":  # macOS
            import os
            macos_chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            if os.path.exists(macos_chrome_path):
                browser_kwargs["executable_path"] = macos_chrome_path
                logger.info(f"已设置 Chrome 可执行文件路径: {macos_chrome_path}")
        
        # 如果提供了 user_data_dir，使用它来保存登录状态
        if user_data_dir:
            # 如果 user_data_dir 是相对路径或简单的站点名称，使用项目配置目录
            user_data_path = Path(user_data_dir)
            if not user_data_path.is_absolute() and '/' not in str(user_data_path) and '\\' not in str(user_data_path):
                # 看起来是站点名称（如 'zhihu'），使用项目配置目录
                user_data_path = self._get_browser_profile_dir(user_data_dir)
                logger.info(f"使用站点名称 '{user_data_dir}'，配置文件目录: {user_data_path}")
            else:
                # 是完整路径，直接使用（支持 ~ 展开）
                user_data_path = user_data_path.expanduser()
                user_data_path.mkdir(parents=True, exist_ok=True)
            
            browser_kwargs["user_data_dir"] = str(user_data_path.resolve())
            logger.info(f"使用用户数据目录保存登录状态: {browser_kwargs['user_data_dir']}")

        if headless:
            # 无头模式：减少等待时间以提高速度
            browser_kwargs.update({
                "minimum_wait_page_load_time": 0.1,
                "wait_between_actions": 0.1,
            })
        else:
            # 可视化模式：稍长等待以确保页面渲染
            browser_kwargs.update({
                "minimum_wait_page_load_time": 0.25,
                "wait_between_actions": 0.5,
            })

        browser = Browser(**browser_kwargs)

        # 使用 asyncio.Event 来实现任务完成时的立即通知
        task_completed = asyncio.Event()
        final_result = None

        # 定义完成回调：任务成功完成时立即通知（调用 done 操作）
        async def on_task_done(history):
            nonlocal final_result, task_completed
            final_result = history
            task_completed.set()
            logger.info("✅ 浏览器任务成功完成（done 操作），立即返回结果")

        # 创建 Agent 并执行任务（根据官方文档）
        # 优化：使用 flash_mode 提高速度（跳过 LLM 思考过程）
        # 对于简单任务，flash_mode 可以显著提高执行速度
        # 优化：减少 step_timeout，避免不必要的长时间等待
        agent_kwargs = {
            "task": task,
            "llm": llm,
            "browser": browser,  # 使用 browser 参数而不是 browser_profile
            "flash_mode": True,  # 启用快速模式，跳过思考过程
            "step_timeout": 30,  # 减少单步超时时间（默认 120s，改为 30s）
            "register_done_callback": on_task_done,
            "use_vision": use_vision,  # 根据任务需求启用视觉功能
        }

        # 如果提供了扩展系统消息，添加到 Agent
        if extend_system_message:
            agent_kwargs["extend_system_message"] = extend_system_message

        agent = Agent(**agent_kwargs)

        logger.info(f"开始执行浏览器任务: {task}")

        # 创建任务来运行 agent.run()（默认 max_steps=100）
        run_task = asyncio.create_task(agent.run(max_steps=100))

        # 等待任务完成或超时
        # 同时等待：
        # 1. task_completed 事件（任务成功完成，调用了 done）
        # 2. run_task 完成（任务结束，无论成功还是失败）
        # 3. 超时
        try:
            wait_tasks = [
                asyncio.create_task(task_completed.wait()),
                run_task,  # 直接等待 run_task，这样无论成功还是失败都能捕获
                asyncio.create_task(asyncio.sleep(timeout)),
            ]
            done, pending = await asyncio.wait(
                wait_tasks,
                return_when=asyncio.FIRST_COMPLETED
            )

            # 取消未完成的等待任务（除了 run_task）
            for wait_task in pending:
                if wait_task is not run_task:
                    wait_task.cancel()
                    try:
                        await wait_task
                    except asyncio.CancelledError:
                        pass

            # 检查完成原因
            if task_completed.is_set() and final_result:
                # 任务成功完成（调用了 done）
                result = final_result
                logger.info("✅ 任务成功完成，立即返回结果（不等待 agent.run() 完全结束）")
            elif run_task.done():
                # 任务结束（成功或失败）
                result = await run_task
                logger.info("✅ 任务结束（agent.run() 完成），返回结果")
            else:
                # 超时了
                run_task.cancel()
                try:
                    await run_task
                except (asyncio.CancelledError, Exception):
                    pass
                raise asyncio.TimeoutError(f"任务超时（{timeout}秒）")
        except asyncio.CancelledError:
            raise
        except asyncio.TimeoutError:
            raise
        except Exception:
            if not run_task.done():
                run_task.cancel()
                try:
                    await run_task
                except (asyncio.CancelledError, Exception):
                    pass
            raise

        # 确定最终结果
        if task_completed.is_set() and final_result:
            result = final_result
        elif run_task.done():
            result = await run_task
        else:
            raise RuntimeError("无法确定任务结果：回调未触发且任务未完成")

        # 分析结果（根据官方文档使用 AgentHistoryList 的方法）
        # result 是 AgentHistoryList 对象
        success = True
        result_str = "任务执行完成"

        # 检查任务是否完成
        if hasattr(result, 'is_done') and callable(result.is_done):
            is_done = result.is_done()
            if is_done:
                # 任务完成，检查是否成功
                if (hasattr(result, 'is_successful') and
                        callable(result.is_successful)):
                    success_result = result.is_successful()
                    if success_result is not None:
                        success = success_result

                # 获取最终结果（根据官方文档推荐）
                if (hasattr(result, 'final_result') and
                        callable(result.final_result)):
                    final_result_text = result.final_result()
                    if final_result_text:
                        result_str = final_result_text
                    else:
                        raise ValueError("任务完成但 final_result() 返回 None")
                else:
                    raise AttributeError("result 对象没有 final_result() 方法")
            else:
                # 任务未完成（可能失败或超时）
                success = False
                if hasattr(result, 'errors') and callable(result.errors):
                    errors = result.errors()
                    if errors:
                        error_messages = [
                            str(e) for e in errors if e is not None
                        ]
                        if error_messages:
                            raise RuntimeError(
                                f"任务未完成。错误: "
                                f"{'; '.join(error_messages)}"
                            )
                raise RuntimeError("任务未完成且无错误信息")

        return ToolResult(
            success=success,
            data={
                "result": result_str,
                "task": task,
                "headless": headless,
                "keep_alive": keep_alive,
            }
        )
