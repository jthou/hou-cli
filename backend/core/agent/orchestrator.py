"""Agent 编排器"""
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, AsyncIterator
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# 获取项目根目录
def get_project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).parent.parent.parent.parent

PROJECT_ROOT = get_project_root()

# 加载 .env 文件（在导入 LLMService 之前）
env_path = PROJECT_ROOT / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # 尝试从当前目录加载
    load_dotenv()

from backend.core.agent.coordinator import AgentCoordinator
from backend.core.context.manager import ContextManager as FullContextManager
from backend.core.context.models import MessageRole
from backend.core.agent.tools.registry import ToolRegistry
from backend.core.agent.tools.base import ToolResult
from backend.core.agent.tools.auth.jwt_auth import JWTAuth, JWTAuthError
from backend.core.agent.tools.builtin.weather_tool import get_weather_tool
from backend.services.llm.llm_service import LLMService
from backend.core.agent.evaluator import ConversationEvaluator
from backend.core.agent.skills.registry import SkillRegistry
from backend.core.agent.skills.executor import SkillExecutor
from backend.core.agent.skills.base import SkillResult
from shared.debug_utils import DebugOutput
from backend.core.agent.planning.manager import PlanningManager
from backend.core.agent.planning.complexity import TaskComplexityAnalyzer
from backend.core.agent.evaluator import ConversationEvaluator
from backend.api.stream_sender import StreamSender, LongTaskMonitor, StreamMessageBuilder
from backend.core.agent.task_manager import task_manager
# from backend.core.workflow.workflow_identifier import WorkflowIdentifier
# from backend.core.workflow.workflow_engine import WorkflowEngine

class Orchestrator:
    """Agent 编排器，负责任务分解和 Agent 协调"""
    
    def __init__(self):
        self.coordinator = AgentCoordinator()
        self.llm_service = LLMService()
        self.context_manager = FullContextManager()
        self.tool_registry = ToolRegistry()
        self.debug = DebugOutput()  # 调试输出
        
        # 初始化技能系统
        from backend.core.agent.skills.registry import SkillRegistry
        from backend.core.agent.skills.executor import SkillExecutor
        self.skill_registry = SkillRegistry()
        self.skill_executor = SkillExecutor(self.tool_registry, self.llm_service)
        
        # 代码执行相关组件
        self.auto_code_executor = None
        self.auto_execute_code = True  # 配置项：是否自动执行代码块
        
        # 规划文件管理（方案2：集成到 Orchestrator）
        import os
        planning_enabled = os.getenv("ENABLE_PLANNING", "true").lower() == "true"
        self.enable_planning = planning_enabled
        
        # 对话评估功能（可以独立于规划功能启用）
        evaluation_enabled = os.getenv("ENABLE_EVALUATION", "true").lower() == "true"
        self.enable_evaluation = evaluation_enabled
        
        if self.enable_planning:
            # 获取规划文件工作目录
            planning_work_dir = os.getenv("PLANNING_WORK_DIR", None)
            if planning_work_dir:
                from pathlib import Path
                planning_work_dir = Path(planning_work_dir)
            else:
                planning_work_dir = PROJECT_ROOT / "plans"
            
            self.planning_manager = PlanningManager(work_dir=planning_work_dir)
            self.complexity_analyzer = TaskComplexityAnalyzer(
                min_task_length=int(os.getenv("PLANNING_MIN_TASK_LENGTH", "20")),
                complexity_threshold=float(os.getenv("PLANNING_COMPLEXITY_THRESHOLD", "0.3")),
                llm_service=self.llm_service,
                use_llm=os.getenv("PLANNING_USE_LLM", "false").lower() == "true"
            )
            # 初始化对话评估器（用于评估对话质量并记录到规划文件）
            self.evaluator = ConversationEvaluator(llm_service=self.llm_service)
            
            # 定期清理旧文件（每100次任务后清理一次）
            self._planning_cleanup_counter = 0
            self._planning_cleanup_interval = int(os.getenv("PLANNING_CLEANUP_INTERVAL", "100"))
            self._planning_max_age_days = int(os.getenv("PLANNING_MAX_AGE_DAYS", "7"))
            self._planning_max_files = int(os.getenv("PLANNING_MAX_FILES", "100"))
            
            logger.info("规划功能已启用")
        else:
            self.planning_manager = None
            self.complexity_analyzer = None
            # 即使规划功能禁用，如果评估功能启用，仍然初始化评估器
            if self.enable_evaluation:
                self.evaluator = ConversationEvaluator(
                    llm_service=self.llm_service
                )
            else:
                self.evaluator = None
            logger.info("规划功能已禁用")
        
        # 注册天气工具（如果配置了 JWT）
        self._register_tools()
        
        # 注册技能（优先于工具）
        self._register_skills()
        
        # 初始化自动代码执行器
        self._init_auto_code_executor()
        
        # self.workflow_identifier = WorkflowIdentifier()
        # self.workflow_engine = WorkflowEngine(self)
    
    def _register_tools(self):
        """注册所有可用工具
        
        工具注册顺序优化原则：
        1. 最常用、最基础的工具放在前面（代码执行、文件搜索）
        2. 网络搜索工具按通用性排序（google_search > browser > wikipedia > mediawiki）
        3. 特定功能工具放在后面（天气、编辑器）
        """
        # ===== 1. 基础工具（最常用） =====
        
        # 注册代码执行工具（最基础、最常用）
        try:
            from backend.core.agent.tools.builtin.code_executor_tool import CodeExecutorTool
            code_executor_tool = CodeExecutorTool()
            self.tool_registry.register(code_executor_tool)
            self.debug.log_orchestrator_step("注册工具", {"code_executor_tool": "registered"})
            logger.info("Code executor tool registered successfully")
        except Exception as e:
            error_msg = f"Failed to register code executor tool: {str(e)}. Code executor tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        
        # 注册 Jupyter 工具（交互式代码执行）
        try:
            from backend.core.agent.tools.builtin.jupyter_tool import JupyterTool
            jupyter_tool = JupyterTool()
            self.tool_registry.register(jupyter_tool)
            self.debug.log_orchestrator_step("注册工具", {"jupyter_tool": "registered"})
            logger.info("Jupyter tool registered successfully")
        except ImportError as e:
            error_msg = f"Jupyter-client not installed: {str(e)}. Jupyter tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        except Exception as e:
            error_msg = f"Failed to register Jupyter tool: {str(e)}. Jupyter tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        
        # 注册文件搜索工具（本地操作）
        try:
            from backend.core.agent.tools.builtin.file_search_tool import FileSearchTool
            file_search_tool = FileSearchTool()
            self.tool_registry.register(file_search_tool)
            self.debug.log_orchestrator_step("注册工具", {"file_search_tool": "registered"})
            logger.info("File search tool registered successfully")
        except Exception as e:
            error_msg = f"Failed to register file search tool: {str(e)}. File search tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        
        # 注册文件整理工具（本地操作）
        try:
            from backend.core.agent.tools.builtin.file_organizer_tool import FileOrganizerTool
            file_organizer_tool = FileOrganizerTool()
            self.tool_registry.register(file_organizer_tool)
            self.debug.log_orchestrator_step("注册工具", {"file_organizer_tool": "registered"})
            logger.info("File organizer tool registered successfully")
        except ImportError as e:
            error_msg = f"Local-File-Organizer not installed: {str(e)}. File organizer tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        except Exception as e:
            error_msg = f"Failed to register file organizer tool: {str(e)}. File organizer tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        
        # 注册PDF解析工具（文档处理）
        try:
            from backend.core.agent.tools.builtin.pdf_parser_tool import PDFParserTool
            pdf_parser_tool = PDFParserTool()
            self.tool_registry.register(pdf_parser_tool)
            self.debug.log_orchestrator_step("注册工具", {"pdf_parser_tool": "registered"})
            logger.info("PDF parser tool registered successfully")
        except ImportError as e:
            error_msg = f"PDF parser dependencies not installed: {str(e)}. PDF parser tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        except Exception as e:
            error_msg = f"Failed to register PDF parser tool: {str(e)}. PDF parser tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        
        # 注册知乎直达工具（知识库）
        try:
            from backend.core.agent.tools.builtin.zhihu_zhida_tool import ZhihuZhidaTool
            zhihu_zhida_tool = ZhihuZhidaTool()
            self.tool_registry.register(zhihu_zhida_tool)
            self.debug.log_orchestrator_step("注册工具", {"zhihu_zhida_tool": "registered"})
            logger.info("Zhihu Zhida tool registered successfully")
        except ImportError as e:
            error_msg = f"Zhihu Zhida tool dependencies not available: {str(e)}. Zhihu Zhida tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        except Exception as e:
            error_msg = f"Failed to register Zhihu Zhida tool: {str(e)}. Zhihu Zhida tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        
        # ===== 2. 网络搜索工具（按使用场景排序） =====
        
        # 注册浏览器工具（访问特定网站，放在 google_search 之前，优先使用）
        # 当用户要求"打开"、"访问"、"查看"网站时，必须使用 browser 工具
        try:
            from backend.core.agent.tools.builtin.browser_tool import BrowserTool
            browser_tool = BrowserTool()
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
        
        # 注册 Google 搜索工具（用于在 Google 上搜索网络信息）
        try:
            from backend.core.agent.tools.builtin.google_search_tool import GoogleSearchTool
            google_search_tool = GoogleSearchTool()
            self.tool_registry.register(google_search_tool)
            self.debug.log_orchestrator_step("注册工具", {"google_search_tool": "registered"})
            logger.info("Google search tool registered successfully")
        except Exception as e:
            error_msg = f"Failed to register Google search tool: {str(e)}. Google search tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        
        # 注册 Wikipedia 搜索工具（特定网站搜索）
        try:
            from backend.core.agent.tools.builtin.wikipedia_tool import WikipediaTool
            wikipedia_tool = WikipediaTool()
            self.tool_registry.register(wikipedia_tool)
            self.debug.log_orchestrator_step("注册工具", {"wikipedia_tool": "registered"})
            logger.info("Wikipedia search tool registered successfully")
        except Exception as e:
            error_msg = f"Failed to register Wikipedia search tool: {str(e)}. Wikipedia search tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        
        # 注册 MediaWiki 工具（特定网站搜索）
        try:
            from backend.core.agent.tools.builtin.mediawiki_tool import MediaWikiTool
            mediawiki_tool = MediaWikiTool()
            self.tool_registry.register(mediawiki_tool)
            self.debug.log_orchestrator_step("注册工具", {"mediawiki_tool": "registered"})
            logger.info("MediaWiki tool registered successfully")
        except Exception as e:
            error_msg = f"Failed to register MediaWiki tool: {str(e)}. MediaWiki tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        
        # ===== 3. 特定功能工具 =====
        
        # 注册天气工具
        try:
            jwt_auth = JWTAuth.from_env()
            weather_tool = get_weather_tool(jwt_auth)
            self.tool_registry.register(weather_tool)
            self.debug.log_orchestrator_step("注册工具", {"weather_tool": "registered"})
        except JWTAuthError as e:
            error_msg = f"JWT authentication configuration error: {str(e)}. Weather tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        except Exception as e:
            error_msg = f"Failed to register weather tool: {str(e)}. Weather tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        
        # 注册 Gvim 工具（编辑器工具）
        try:
            from backend.core.agent.tools.builtin.gvim_tool import GvimTool
            gvim_tool = GvimTool()
            self.tool_registry.register(gvim_tool)
            self.debug.log_orchestrator_step("注册工具", {"gvim_tool": "registered"})
            logger.info("Gvim tool registered successfully")
        except Exception as e:
            error_msg = f"Failed to register Gvim tool: {str(e)}. Gvim tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        
        # 注册视频下载工具
        try:
            from backend.core.agent.tools.builtin.video_downloader_tool import VideoDownloaderTool
            video_downloader_tool = VideoDownloaderTool()
            self.tool_registry.register(video_downloader_tool)
            self.debug.log_orchestrator_step("注册工具", {"video_downloader_tool": "registered"})
            logger.info("Video downloader tool registered successfully")
        except Exception as e:
            error_msg = f"Failed to register video downloader tool: {str(e)}. Video downloader tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        
        # 注册 FFmpeg 工具
        try:
            from backend.core.agent.tools.builtin.ffmpeg_tool import FFmpegTool
            ffmpeg_tool = FFmpegTool()
            self.tool_registry.register(ffmpeg_tool)
            self.debug.log_orchestrator_step("注册工具", {"ffmpeg_tool": "registered"})
            logger.info("FFmpeg tool registered successfully")
        except Exception as e:
            error_msg = f"Failed to register FFmpeg tool: {str(e)}. FFmpeg tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        
        # 注册 Whisper 工具（语音转文字）
        try:
            from backend.core.agent.tools.builtin.whisper_tool import WhisperTool
            whisper_tool = WhisperTool()
            self.tool_registry.register(whisper_tool)
            self.debug.log_orchestrator_step("注册工具", {"whisper_tool": "registered"})
            logger.info("Whisper tool registered successfully")
        except Exception as e:
            error_msg = f"Failed to register Whisper tool: {str(e)}. Whisper tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
    
    def _register_skills(self):
        """注册所有可用技能
        
        技能优先于工具，当用户请求匹配到技能时，优先使用技能执行
        从目录自动加载所有技能配置并注册
        """
        try:
            from pathlib import Path
            skills_dir = Path(__file__).parent.parent.parent / "core" / "agent" / "skills"
            
            # 从目录加载所有技能配置
            self.skill_registry.load_from_directory(skills_dir)
            
            # 注册技能实例
            for skill_name in self.skill_registry._skill_configs.keys():
                try:
                    config = self.skill_registry.get_config(skill_name)
                    if config:
                        # 根据技能名称动态导入对应的技能类
                        if skill_name == 'video_downloader':
                            from backend.core.agent.skills.video_downloader.video_downloader_skill import VideoDownloaderSkill
                            skill = VideoDownloaderSkill(self.skill_executor)
                            self.skill_registry.register(skill)
                            logger.info(f"技能已注册: {skill_name}")
                        elif skill_name == 'video_summary':
                            from backend.core.agent.skills.video_summary import VideoSummarySkill
                            skill = VideoSummarySkill(self.skill_executor)
                            self.skill_registry.register(skill)
                            logger.info(f"技能已注册: {skill_name}")
                        elif skill_name == 'video_extract_srt':
                            from backend.core.agent.skills.video_extract_srt import VideoExtractSrtSkill
                            skill = VideoExtractSrtSkill(self.skill_executor)
                            self.skill_registry.register(skill)
                            logger.info(f"技能已注册: {skill_name}")
                        elif skill_name == 'video_cut':
                            from backend.core.agent.skills.video_editing.video_cut_skill import VideoCutSkill
                            skill = VideoCutSkill(self.skill_executor)
                            self.skill_registry.register(skill)
                            logger.info(f"技能已注册: {skill_name}")
                        elif skill_name == 'video_merge':
                            from backend.core.agent.skills.video_merge.video_merge_skill import VideoMergeSkill
                            skill = VideoMergeSkill(self.skill_executor)
                            self.skill_registry.register(skill)
                            logger.info(f"技能已注册: {skill_name}")
                        elif skill_name == 'video_subtitle_overlay':
                            from backend.core.agent.skills.video_subtitle_overlay.video_subtitle_overlay_skill import VideoSubtitleOverlaySkill
                            skill = VideoSubtitleOverlaySkill(self.skill_executor)
                            self.skill_registry.register(skill)
                            logger.info(f"技能已注册: {skill_name}")
                        else:
                            logger.warning(f"未知的技能名称: {skill_name}")
                except Exception as e:
                    logger.warning(f"注册技能 {skill_name} 失败: {str(e)}", exc_info=True)
        except Exception as e:
            logger.warning(f"加载技能失败: {str(e)}", exc_info=True)
    
    def _init_auto_code_executor(self):
        """初始化自动代码执行器"""
        try:
            from backend.infrastructure.execution import AutoCodeExecutor
            self.auto_code_executor = AutoCodeExecutor()
            logger.info("Auto code executor initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize auto code executor: {str(e)}")
            self.auto_code_executor = None
    
    def _build_execution_feedback(self, execution_results: list) -> str:
        """构建执行结果反馈消息"""
        feedback = "代码执行完成：\n\n"
        for result in execution_results:
            feedback += f"代码块 {result.get('index', '?')} ({result.get('language', 'unknown')}):\n"
            if "error" in result:
                feedback += f"  ❌ 执行失败: {result['error']}\n"
            else:
                exec_result = result.get("result", {})
                if exec_result.get("success"):
                    feedback += f"  ✅ 执行成功\n"
                    if exec_result.get("output"):
                        output = exec_result["output"][:500]  # 限制长度
                        feedback += f"  输出: {output}\n"
                else:
                    feedback += f"  ❌ 执行失败: {exec_result.get('error', 'Unknown error')}\n"
            feedback += "\n"
        return feedback
    
    async def process(self, task: str, context: Optional[Dict] = None) -> str:
        """处理任务，支持 SOP 和动态编排"""
        # TODO: 实现流程识别和 SOP 执行
        # 暂时使用动态编排
        return await self.process_dynamic(task, context)
    
    async def process_dynamic(self, task: str, context: Optional[Dict] = None) -> str:
        """
        动态编排执行
        
        Args:
            task: 用户任务/消息
            context: 上下文信息（可选，包含 session_id）
            
        Returns:
            LLM 生成的回复
        """
        self.debug.log_orchestrator_step("开始处理任务", {"task": task[:50] + "..." if len(task) > 50 else task})
        
        # 优先检查是否有匹配的技能
        matched_skill = self.skill_registry.match(task)
        if matched_skill:
            logger.info(f"检测到匹配的技能: {matched_skill.name}，优先使用技能执行")
            self.debug.log_orchestrator_step("技能匹配", {"skill": matched_skill.name})
            
            # 提取技能参数
            skill_params = self._extract_skill_parameters(task, matched_skill)
            
            # 执行技能
            try:
                # 设置上下文（包含 tool_registry）
                session_id = context.get("session_id") if context else None
                if not session_id:
                    session_id = self.context_manager.create_session()
                
                skill_context = {
                    'tool_registry': self.tool_registry,
                    'llm_service': self.llm_service,
                    'context_manager': self.context_manager,
                    'session_id': session_id
                }
                
                skill_result = await matched_skill.execute(skill_params, skill_context)
                
                if skill_result.success:
                    logger.info(f"技能 {matched_skill.name} 执行成功")
                    result_text = self._format_skill_result(matched_skill, skill_result)
                    return result_text
                else:
                    logger.warning(f"技能 {matched_skill.name} 执行失败: {skill_result.error}")
                    # 技能执行失败，继续使用 LLM 处理
            except Exception as e:
                logger.error(f"技能 {matched_skill.name} 执行异常: {str(e)}", exc_info=True)
                # 技能执行异常，继续使用 LLM 处理
        
        # 获取会话 ID（如果提供）
        session_id = context.get("session_id") if context else None
        self.debug.log_context_operation("获取会话ID", session_id or "new", {"provided": session_id is not None})
        
        # 如果没有会话 ID，创建新会话
        if not session_id:
            session_id = self.context_manager.create_session()
            self.debug.log_context_operation("创建新会话", session_id)
        
        # 获取历史消息（不压缩，保留完整历史）
        history = self.context_manager.get_messages_for_llm(
            session_id,
            max_messages=None,  # 不限制消息数量
            max_tokens=None     # 不限制 token 数量
        )
        self.debug.log_context_operation("获取历史消息", session_id, {"count": len(history), "has_history": len(history) > 0})
        
        # 构建消息列表
        system_prompt = """你是一个智能助手，能够帮助用户解决各种问题。当用户提供历史对话记录时，请基于历史对话内容来理解和回答当前问题。

重要原则：
- 对于简单的命令执行任务（如显示文件、查看目录、执行脚本等），严格按照用户指令执行，不要添加额外的探索、检查或推理
- 用户要求执行什么命令，就执行什么命令，不要自作主张添加其他操作
- 例如：用户要求"显示 /home 下的所有文件"，直接执行 "ls /home"，不要去找 /dev、/Users 等其他路径
- 不要过度思考，不要添加用户没有要求的额外功能

【重要】工具选择规则：
1. **浏览器工具（browser）**：当用户要求"打开"、"访问"、"查看"网站时，必须使用 browser 工具
   - 例如："打开 www.google.com" → 使用 browser
   - 例如："访问 www.example.com 并查看网页" → 使用 browser
   - 例如："打开网站" → 使用 browser
   - 如果用户提到具体的网站地址（如 www.google.com、example.com），优先使用 browser

2. **Google 搜索工具（google_search）**：当用户要求"搜索"、"查找"网络信息时，使用 google_search
   - 例如："搜索 Python 教程" → 使用 google_search
   - 例如："查找关于 AI 的最新信息" → 使用 google_search

3. **天气工具（get_weather）**：当用户询问天气信息时，必须使用 get_weather 工具来获取实时天气数据。绝对不要编造或猜测天气信息。如果工具调用失败，请明确告诉用户工具调用失败，不要生成虚假的天气信息。

当展示天气信息时，请使用清晰、美观的 Markdown 格式，并添加天气和风力图标：

**天气图标对照表：**
- ☀️ 晴天
- ⛅ 多云
- ☁️ 阴天
- 🌧️ 雨天
- ⛈️ 雷雨
- 🌨️ 雪天
- 🌫️ 雾/霾
- 🌪️ 大风/龙卷风

**风力图标对照表：**
- 🍃 微风（1-3级）
- 💨 轻风（4-5级）
- 🌬️ 和风（6-7级）
- 💨💨 强风（8-9级）
- 🌪️ 狂风（10级以上）

**格式要求：**

1. **当前天气**：使用列表或简洁的段落展示，添加天气图标
   - 例如：☀️ 晴，温度 3°C，体感温度 0°C
   - 如果提供了空气质量数据，请显示雾霾指数（AQI）和空气质量等级
     * AQI 0-50：🟢 优
     * AQI 51-100：🟡 良
     * AQI 101-150：🟠 轻度污染
     * AQI 151-200：🔴 中度污染
     * AQI 201-300：🟣 重度污染
     * AQI >300：⚫ 严重污染
   - 例如：🌫️ 空气质量：AQI 85，🟡 良，PM2.5: 45μg/m³

2. **天气预报**：使用 Markdown 表格格式，在天气和风向列中添加图标，例如：
   | 日期 | 天气 | 最高温度 | 最低温度 | 风向 | 湿度 |
   |------|------|---------|---------|------|------|
   | 1月3日 | ☀️ 晴 | 6°C | -4°C | 🍃 西北风1-3级 | 24% |
   | 1月4日 | ☀️ 晴 | 5°C | -5°C | 🍃 东风1-3级 | 29% |
   | 1月5日 | ⛅ 多云 | 4°C | -4°C | 💨 西南风4-5级 | 35% |

3. **穿衣建议**：根据温度、天气状况和风力提供穿衣指数和建议
   - 使用温度范围判断：
     * 30°C以上：🔥 炎热，建议穿轻薄透气的短袖、短裤
     * 25-30°C：☀️ 温暖，建议穿T恤、薄长裤
     * 15-25°C：😊 舒适，建议穿长袖、薄外套
     * 5-15°C：🧥 凉爽，建议穿薄外套、长裤
     * 0-5°C：🧣 较冷，建议穿厚外套、毛衣
     * 0°C以下：❄️ 寒冷，建议穿羽绒服、厚毛衣、保暖内衣
   - 根据天气状况调整：
     * 雨天：🌧️ 建议穿防水外套或带雨具
     * 雪天：🌨️ 建议穿防滑鞋、保暖衣物
     * 大风：💨 建议穿防风外套

4. **带伞建议**：
   - 🌧️ 有雨：**建议带伞**
   - ⛈️ 雷雨：**强烈建议带伞**
   - 🌨️ 雪天：**建议带伞（防雪）**
   - ☀️ 晴天：无需带伞
   - ⛅ 多云：建议携带轻便雨具（以防突发降雨）

5. **总结**：使用标题（##）和列表（-）组织信息

请确保：
- 表格对齐整齐
- 信息层次清晰
- 使用适当的 Markdown 语法（标题、列表、表格、粗体）
- 根据实际天气状况选择合适的图标
- 根据风力等级选择合适的风力图标
- 穿衣建议和带伞建议要基于实际的温度、天气状况和降水概率"""
        
        # 构建 user_prompt（包含历史上下文）
        # 过滤掉 system 消息，只保留 user 和 assistant 消息
        filtered_history = [msg for msg in history if msg['role'] in ['user', 'assistant']]
        
        if filtered_history:
            # 将历史消息格式化为对话形式，明确标注历史对话
            history_text = "\n".join([
                f"{'用户' if msg['role'] == 'user' else '助手'}: {msg['content']}"
                for msg in filtered_history
            ])
            user_prompt = f"以下是历史对话记录：\n{history_text}\n\n当前用户问题：{task}"
            self.debug.log_orchestrator_step("构建用户提示", {"has_history": True, "history_count": len(filtered_history), "total_count": len(history)})
        else:
            user_prompt = task
            self.debug.log_orchestrator_step("构建用户提示", {"has_history": False})
        
        # 获取工具定义（LLM Function Calling 格式）
        tools = self.tool_registry.get_tools_for_llm()
        self.debug.log_orchestrator_step("准备工具", {"tool_count": len(tools)})
        
        # 智能模型选择：使用 chat 模型分析任务，决定使用哪个模型
        selected_model = await self._select_model(task)
        if selected_model != self.llm_service.model:
            self.llm_service.set_model(selected_model)
        # 总是显示模型选择信息（即使模型没有改变）
        self.debug.log_orchestrator_step("模型选择", {"selected_model": selected_model})
        
        # LLM 调用（支持工具调用）
        self.debug.log_llm_request(system_prompt, user_prompt, selected_model)
        response = await self._chat_with_tools(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=tools if tools else None
        )
        self.debug.log_llm_response(response, selected_model)
        
        # 重置为默认模型
        self.llm_service.reset_model()
        
        # 对话评估：评估上一轮对话（如果有）
        # 第一轮对话不评估，从第二轮开始评估上一轮
        if self.enable_evaluation:
            try:
                # 获取历史消息（在保存当前消息之前）
                history = self.context_manager.get_messages(session_id, compressed=False)
                
                # 检查是否有上一轮完整的对话（user + assistant）
                # 需要至少 2 条消息（一条 user，一条 assistant）才算上一轮
                if len(history) >= 2:
                    # 获取上一轮的 user 和 assistant 消息
                    prev_user_msg = None
                    prev_assistant_msg = None
                    
                    # 从后往前查找最后一对 user-assistant
                    for i in range(len(history) - 1, -1, -1):
                        msg = history[i]
                        if msg.role == MessageRole.ASSISTANT and prev_assistant_msg is None:
                            prev_assistant_msg = msg
                        elif msg.role == MessageRole.USER and prev_assistant_msg is not None:
                            prev_user_msg = msg
                            break
                    
                    # 如果找到上一轮对话，且 assistant 消息还没有评估过
                    if prev_user_msg and prev_assistant_msg:
                        # 检查是否已经评估过
                        prev_evaluation = prev_assistant_msg.metadata.get("evaluation") if prev_assistant_msg.metadata else None
                        if not prev_evaluation:
                            # 评估上一轮对话
                            evaluation_result = await self.evaluator.evaluate_conversation_turn(
                                user_message=prev_user_msg.content,
                                assistant_message=prev_assistant_msg.content,
                                context=None
                            )
                            
                            # 将评估结果保存到上一轮 assistant 消息的 metadata
                            if prev_assistant_msg.metadata is None:
                                prev_assistant_msg.metadata = {}
                            prev_assistant_msg.metadata["evaluation"] = evaluation_result
                            
                            # 更新上一轮 assistant 消息
                            self.context_manager.storage.save_message(session_id, prev_assistant_msg)
                            
                            logger.info(f"对话评估完成，分数: {evaluation_result.get('overall_score', 'N/A')}/100")
            except Exception as e:
                logger.warning(f"对话评估失败: {str(e)}", exc_info=True)
                # 评估失败不影响正常流程
        
        # 保存消息到历史
        self.context_manager.add_message(session_id, MessageRole.USER, task)
        self.context_manager.add_message(session_id, MessageRole.ASSISTANT, response)
        self.debug.log_context_operation("保存消息", session_id, {"user": True, "assistant": True})
        
        self.debug.log_orchestrator_step("任务处理完成", {"response_length": len(response)})
        return response
    
    async def stream_process(self, task: str, context: Optional[Dict] = None) -> AsyncIterator[str]:
        """
        流式处理任务
        
        Args:
            task: 用户任务/消息
            context: 上下文信息（可选，包含 session_id）
            
        Yields:
            流式数据块（格式：特殊标记 + JSON 或纯文本）
            - 调试信息：`__DEBUG__:{"type":"debug","category":"...","message":"..."}`
            - 工具调用：`__TOOL__:{"type":"tool","name":"...","args":{...},"result":{...}}`
            - 内容：纯文本
        """
        import json
        import time
        
        # #region agent log
        try:
            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"orchestrator.py:stream_process:entry","message":"stream_process被调用","data":{"task_length":len(task) if task else 0,"has_context":context is not None},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                f.flush()
        except Exception as log_err:
            logger.error(f"日志写入失败: {log_err}")
        # #endregion
        
        # 发送调试信息：开始处理
        debug_info = {
            "type": "debug",
            "category": "orchestrator",
            "message": "开始流式处理任务",
            "details": {"task": task[:50] + "..." if len(task) > 50 else task}
        }
        
        # #region agent log
        try:
            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"orchestrator.py:stream_process:before_first_yield","message":"准备yield第一个消息","data":{},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                f.flush()
        except Exception as log_err:
            logger.error(f"日志写入失败: {log_err}")
        # #endregion
        
        first_msg = StreamMessageBuilder.build_debug(debug_info)
        
        # #region agent log
        try:
            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"orchestrator.py:stream_process:before_yield_first_msg","message":"准备yield第一个消息内容","data":{"msg_preview":first_msg[:50] if first_msg else None},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                f.flush()
        except Exception as log_err:
            logger.error(f"日志写入失败: {log_err}")
        # #endregion
        
        yield first_msg
        
        # #region agent log
        try:
            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"orchestrator.py:stream_process:after_first_yield","message":"第一个消息已yield","data":{},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                f.flush()
        except Exception as log_err:
            logger.error(f"日志写入失败: {log_err}")
        # #endregion
        
        self.debug.log_orchestrator_step("开始流式处理任务", {"task": task[:50] + "..." if len(task) > 50 else task})
        
        # 1. 获取会话 ID（如果提供）
        session_id = context.get("session_id") if context else None
        self.debug.log_context_operation("获取会话ID", session_id or "new", {"provided": session_id is not None})
        
        # 如果没有会话 ID，创建新会话
        if not session_id:
            session_id = self.context_manager.create_session()
            debug_info = {
                "type": "debug",
                "category": "context",
                "message": "创建新会话",
                "details": {"session_id": session_id[:8] + "..."}
            }
            yield StreamMessageBuilder.build_debug(debug_info)
            self.debug.log_context_operation("创建新会话", session_id)
        
        # 2. 获取历史消息（不压缩，保留完整历史）
        history = self.context_manager.get_messages_for_llm(
            session_id,
            max_messages=None,  # 不限制消息数量
            max_tokens=None     # 不限制 token 数量
        )
        debug_info = {
            "type": "debug",
            "category": "context",
            "message": "获取历史消息",
            "details": {"count": len(history), "has_history": len(history) > 0}
        }
        yield StreamMessageBuilder.build_debug(debug_info)
        self.debug.log_context_operation("获取历史消息", session_id, {"count": len(history), "has_history": len(history) > 0})
        
        # 3. 规划功能：检测复杂任务并创建规划文件
        planning_files = None
        task_plan_content = None
        if self.enable_planning and self.planning_manager and self.complexity_analyzer:
            # 发送调试信息：开始复杂度分析
            debug_info = {
                "type": "debug",
                "category": "planning",
                "message": "开始分析任务复杂度",
                "details": {}
            }
            yield StreamMessageBuilder.build_debug(debug_info)
            
            # #region agent log
            try:
                with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"orchestrator.py:stream_process:before_complexity_check","message":"准备进行复杂度分析","data":{"use_llm":self.complexity_analyzer.use_llm},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
            except: pass
            # #endregion
            
            # 判断任务复杂度（支持 LLM 辅助判断）
            try:
                if self.complexity_analyzer.use_llm:
                    # #region agent log
                    try:
                        with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"orchestrator.py:stream_process:before_is_complex_async","message":"准备调用is_complex_task_async","data":{},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                    except: pass
                    # #endregion
                    is_complex = await self.complexity_analyzer.is_complex_task_async(task, history)
                    # #region agent log
                    try:
                        with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"orchestrator.py:stream_process:after_is_complex_async","message":"is_complex_task_async完成","data":{"is_complex":is_complex},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                    except: pass
                    # #endregion
                else:
                    # #region agent log
                    try:
                        with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"orchestrator.py:stream_process:before_is_complex","message":"准备调用is_complex_task","data":{},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                    except: pass
                    # #endregion
                    is_complex = self.complexity_analyzer.is_complex_task(task, history)
                    # #region agent log
                    try:
                        with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"orchestrator.py:stream_process:after_is_complex","message":"is_complex_task完成","data":{"is_complex":is_complex},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                    except: pass
                    # #endregion
            except Exception as e:
                logger.warning(f"复杂度分析失败: {str(e)}", exc_info=True)
                # 分析失败时，默认不创建规划文件，继续执行
                is_complex = False
            
            if is_complex:
                try:
                    # 创建规划文件
                    planning_files = self.planning_manager.create_planning_files(task, session_id)
                    
                    # 读取规划文件内容，准备注入到 system_prompt
                    task_plan_content = self.planning_manager.read_task_plan(session_id)
                    
                    debug_info = {
                        "type": "debug",
                        "category": "planning",
                        "message": "检测到复杂任务，已创建规划文件",
                        "details": {
                            "task_plan": str(planning_files.task_plan),
                            "findings": str(planning_files.findings),
                            "progress": str(planning_files.progress)
                        }
                    }
                    yield StreamMessageBuilder.build_debug(debug_info)
                    logger.info(f"为复杂任务创建规划文件: {planning_files.task_plan}")
                except Exception as e:
                    logger.error(f"创建规划文件失败: {str(e)}", exc_info=True)
                    debug_info = {
                        "type": "debug",
                        "category": "planning",
                        "message": "创建规划文件失败",
                        "details": {"error": str(e)}
                    }
                    yield StreamMessageBuilder.build_debug(debug_info)
        
        # 4. 构建 system_prompt（包含规划内容）
        planning_context = ""
        if planning_files and task_plan_content:
            planning_context = f"""

【重要】任务规划文件已创建，请遵循以下规划执行任务：

{task_plan_content[:2000]}  # 限制长度，避免上下文过长

请在执行任务时：
1. 参考 task_plan.md 中的目标和阶段
2. 完成每个阶段后，更新阶段状态
3. 将研究发现记录到 findings.md
4. 将操作记录到 progress.md
5. 遇到错误时，记录到 task_plan.md 的错误表
"""
        
        system_prompt = f"""你是一个智能助手，能够帮助用户解决各种问题。当用户提供历史对话记录时，请基于历史对话内容来理解和回答当前问题。{planning_context}

重要原则：
- 对于简单的命令执行任务（如显示文件、查看目录、执行脚本等），严格按照用户指令执行，不要添加额外的探索、检查或推理
- 用户要求执行什么命令，就执行什么命令，不要自作主张添加其他操作
- 例如：用户要求"显示 /home 下的所有文件"，直接执行 "ls /home"，不要去找 /dev、/Users 等其他路径
- 不要过度思考，不要添加用户没有要求的额外功能

【重要】工具选择规则：
1. **浏览器工具（browser）**：当用户要求"打开"、"访问"、"查看"网站时，必须使用 browser 工具
   - 例如："打开 www.google.com" → 使用 browser
   - 例如："访问 www.example.com 并查看网页" → 使用 browser
   - 例如："打开网站" → 使用 browser
   - 如果用户提到具体的网站地址（如 www.google.com、example.com），优先使用 browser

2. **Google 搜索工具（google_search）**：当用户要求"搜索"、"查找"网络信息时，使用 google_search
   - 例如："搜索 Python 教程" → 使用 google_search
   - 例如："查找关于 AI 的最新信息" → 使用 google_search

3. **天气工具（get_weather）**：当用户询问天气信息时，必须使用 get_weather 工具来获取实时天气数据。绝对不要编造或猜测天气信息。如果工具调用失败，请明确告诉用户工具调用失败，不要生成虚假的天气信息。

当展示天气信息时，请使用清晰、美观的 Markdown 格式，并添加天气和风力图标：

**天气图标对照表：**
- ☀️ 晴天
- ⛅ 多云
- ☁️ 阴天
- 🌧️ 雨天
- ⛈️ 雷雨
- 🌨️ 雪天
- 🌫️ 雾/霾
- 🌪️ 大风/龙卷风

**风力图标对照表：**
- 🍃 微风（1-3级）
- 💨 轻风（4-5级）
- 🌬️ 和风（6-7级）
- 💨💨 强风（8-9级）
- 🌪️ 狂风（10级以上）

**格式要求：**

1. **当前天气**：使用列表或简洁的段落展示，添加天气图标
   - 例如：☀️ 晴，温度 3°C，体感温度 0°C
   - 如果提供了空气质量数据，请显示雾霾指数（AQI）和空气质量等级
     * AQI 0-50：🟢 优
     * AQI 51-100：🟡 良
     * AQI 101-150：🟠 轻度污染
     * AQI 151-200：🔴 中度污染
     * AQI 201-300：🟣 重度污染
     * AQI >300：⚫ 严重污染
   - 例如：🌫️ 空气质量：AQI 85，🟡 良，PM2.5: 45μg/m³

2. **天气预报**：使用 Markdown 表格格式，在天气和风向列中添加图标，例如：
   | 日期 | 天气 | 最高温度 | 最低温度 | 风向 | 湿度 |
   |------|------|---------|---------|------|------|
   | 1月3日 | ☀️ 晴 | 6°C | -4°C | 🍃 西北风1-3级 | 24% |
   | 1月4日 | ☀️ 晴 | 5°C | -5°C | 🍃 东风1-3级 | 29% |
   | 1月5日 | ⛅ 多云 | 4°C | -4°C | 💨 西南风4-5级 | 35% |

3. **穿衣建议**：根据温度、天气状况和风力提供穿衣指数和建议
   - 使用温度范围判断：
     * 30°C以上：🔥 炎热，建议穿轻薄透气的短袖、短裤
     * 25-30°C：☀️ 温暖，建议穿T恤、薄长裤
     * 15-25°C：😊 舒适，建议穿长袖、薄外套
     * 5-15°C：🧥 凉爽，建议穿薄外套、长裤
     * 0-5°C：🧣 较冷，建议穿厚外套、毛衣
     * 0°C以下：❄️ 寒冷，建议穿羽绒服、厚毛衣、保暖内衣
   - 根据天气状况调整：
     * 雨天：🌧️ 建议穿防水外套或带雨具
     * 雪天：🌨️ 建议穿防滑鞋、保暖衣物
     * 大风：💨 建议穿防风外套

4. **带伞建议**：
   - 🌧️ 有雨：**建议带伞**
   - ⛈️ 雷雨：**强烈建议带伞**
   - 🌨️ 雪天：**建议带伞（防雪）**
   - ☀️ 晴天：无需带伞
   - ⛅ 多云：建议携带轻便雨具（以防突发降雨）

5. **总结**：使用标题（##）和列表（-）组织信息

请确保：
- 表格对齐整齐
- 信息层次清晰
- 使用适当的 Markdown 语法（标题、列表、表格、粗体）
- 根据实际天气状况选择合适的图标
- 根据风力等级选择合适的风力图标
- 穿衣建议和带伞建议要基于实际的温度、天气状况和降水概率"""
        
        # 构建 user_prompt（包含历史上下文）
        filtered_history = [msg for msg in history if msg['role'] in ['user', 'assistant']]
        
        if filtered_history:
            history_text = "\n".join([
                f"{'用户' if msg['role'] == 'user' else '助手'}: {msg['content']}"
                for msg in filtered_history
            ])
            user_prompt = f"以下是历史对话记录：\n{history_text}\n\n当前用户问题：{task}"
            self.debug.log_orchestrator_step("构建用户提示", {"has_history": True, "history_count": len(filtered_history), "total_count": len(history)})
        else:
            user_prompt = task
            self.debug.log_orchestrator_step("构建用户提示", {"has_history": False})
        
        # 5. 优先尝试匹配技能（集成任务管理和规划更新）
        # #region agent log
        try:
            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"orchestrator.py:stream_process:before_skill_match","message":"准备进行技能匹配","data":{},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
        except: pass
        # #endregion
        
        matched_skill = self.skill_registry.match(task)
        
        # #region agent log
        try:
            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"orchestrator.py:stream_process:after_skill_match","message":"技能匹配完成","data":{"matched":matched_skill is not None,"skill_name":matched_skill.name if matched_skill else None},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
        except: pass
        # #endregion
        
        if matched_skill:
            logger.info(f"检测到匹配的技能: {matched_skill.name}，优先使用技能执行")
            debug_info = {
                "type": "debug",
                "category": "orchestrator",
                "message": "技能匹配",
                "details": {"skill": matched_skill.name}
            }
            yield StreamMessageBuilder.build_debug(debug_info)
            self.debug.log_orchestrator_step("技能匹配", {"skill": matched_skill.name})
            
            # 提取技能参数
            skill_params = self._extract_skill_parameters(task, matched_skill)
            
            # 执行技能
            try:
                # 检测是否是长任务（需要进度监控）
                is_long_task = matched_skill.name in ['video_downloader']  # 可以扩展其他长任务
                
                # 创建任务记录（任务管理功能）
                task_id = None
                if is_long_task:
                    import uuid
                    from backend.core.agent.task_manager import TaskInfo, TaskStatus
                    from datetime import datetime
                    
                    task_id = str(uuid.uuid4())
                    task_info = TaskInfo(
                        task_id=task_id,
                        task_name=f"{matched_skill.name}: {task[:50]}",
                        status=TaskStatus.RUNNING,
                        started_at=datetime.now()
                    )
                    task_manager._tasks[task_id] = task_info
                    
                    # 发送任务创建通知
                    status_data = {
                        "task": task_info.task_name,
                        "progress": 0,
                        "message": "任务已创建，准备执行...",
                        "elapsed_time": 0,
                        "task_id": task_id
                    }
                    yield StreamMessageBuilder.build_status(status_data)
                
                # 设置技能上下文（包含任务管理和规划功能）
                skill_context = {
                    'tool_registry': self.tool_registry,
                    'llm_service': self.llm_service,
                    'context_manager': self.context_manager,
                    'session_id': session_id,
                    'task_id': task_id,
                    'task_manager': task_manager,
                    'planning_files': planning_files,  # 添加规划文件引用
                    'planning_manager': self.planning_manager if self.enable_planning else None
                }
                
                # 创建进度回调（同时更新任务管理和规划文件）
                import asyncio
                import queue as queue_module
                progress_queue = queue_module.Queue()  # 使用线程安全的队列
                
                def integrated_progress_callback(progress_or_message, message: str = ""):
                    """集成的进度回调（同时更新任务管理和规划文件）"""
                    try:
                        # 更新任务管理器
                        if task_manager and task_id:
                            if isinstance(progress_or_message, str):
                                # 只传递消息，保持当前进度
                                current_task = task_manager._tasks.get(task_id)
                                if current_task:
                                    current_progress = current_task.progress if hasattr(current_task, 'progress') else 0
                                    task_manager.update_task_progress(task_id, current_progress, progress_or_message)
                            else:
                                # 传递进度值和消息
                                task_manager.update_task_progress(task_id, progress_or_message, message)
                        
                        # 更新规划文件
                        if self.enable_planning and self.planning_manager and planning_files:
                            progress_msg = message if message else (progress_or_message if isinstance(progress_or_message, str) else f"进度: {progress_or_message}%")
                            self.planning_manager.add_progress(
                                f"进度更新: {progress_msg}",
                                files_modified=[],
                                session_id=session_id
                            )
                        
                        # 将更新放入队列（用于发送 SSE 消息）
                        progress_queue.put_nowait((progress_or_message, message))
                    except Exception as e:
                        logger.warning(f"进度回调执行失败: {e}")
                
                skill_context['progress_callback'] = integrated_progress_callback
                
                # 执行技能（非流式，但可以转换为流式输出）
                # 在后台任务中处理进度更新队列
                async def process_progress_updates():
                    """处理进度更新队列并发送 SSE 消息"""
                    import time
                    while True:
                        try:
                            # 从队列获取进度更新（非阻塞）
                            try:
                                progress_or_message, message = progress_queue.get_nowait()
                            except queue_module.Empty:
                                # 队列为空，检查任务是否还在运行
                                if task_id:
                                    task_info = task_manager.get_task(task_id)
                                    if not task_info or task_info.status.value in ['completed', 'failed', 'cancelled']:
                                        break
                                await asyncio.sleep(0.5)  # 等待一段时间再检查
                                continue
                            
                            # 更新任务进度
                            if task_manager and task_id:
                                if isinstance(progress_or_message, str):
                                    # 只传递消息，保持当前进度
                                    current_task = task_manager._tasks.get(task_id)
                                    if current_task:
                                        current_progress = current_task.progress if hasattr(current_task, 'progress') else 0
                                        task_manager.update_task_progress(task_id, current_progress, progress_or_message)
                                else:
                                    # 传递进度值和消息
                                    task_manager.update_task_progress(task_id, progress_or_message, message)
                                
                                # 获取任务信息并发送状态更新
                                task_info = task_manager.get_task(task_id)
                                if task_info:
                                    elapsed_time = (time.time() - task_info.started_at.timestamp()) if task_info.started_at else 0
                                    status_data = {
                                        "task": task_info.task_name,
                                        "progress": task_info.progress,
                                        "message": task_info.message or message or "处理中...",
                                        "elapsed_time": round(elapsed_time, 2),
                                        "task_id": task_id
                                    }
                                    if task_info.progress > 0:
                                        estimated_total = elapsed_time / (task_info.progress / 100)
                                        estimated_remaining = max(0, estimated_total - elapsed_time)
                                        status_data["estimated_remaining"] = round(estimated_remaining, 2)
                                    status_str = StreamMessageBuilder.build_status(status_data)
                                    yield status_str
                        except Exception as e:
                            logger.error(f"处理进度更新失败: {e}", exc_info=True)
                            break
                
                # 创建一个列表来收集进度更新（用于在技能执行期间发送）
                progress_updates_list = []
                progress_updates_lock = asyncio.Lock()
                
                # 启动进度更新处理任务（在后台运行）
                async def collect_progress_updates():
                    """收集进度更新到列表"""
                    async for status_update in process_progress_updates():
                        async with progress_updates_lock:
                            progress_updates_list.append(status_update)
                
                progress_collector_task = None
                if task_id:
                    progress_collector_task = asyncio.create_task(collect_progress_updates())
                
                # 执行技能（异步执行，但我们需要在期间处理进度更新）
                # 创建一个任务来执行技能
                skill_task = asyncio.create_task(matched_skill.execute(skill_params, skill_context))
                
                # 在技能执行期间，定期检查并发送进度更新
                while not skill_task.done():
                    # 检查并发送进度更新
                    async with progress_updates_lock:
                        while progress_updates_list:
                            status_update = progress_updates_list.pop(0)
                            yield status_update
                    
                    # 短暂休眠，然后检查技能是否完成
                    await asyncio.sleep(0.2)
                
                # 获取技能执行结果
                skill_result = await skill_task
                
                # 发送所有剩余的进度更新
                if progress_collector_task:
                    # 等待一小段时间，让进度收集器完成
                    await asyncio.sleep(0.5)
                    progress_collector_task.cancel()
                    try:
                        await progress_collector_task
                    except asyncio.CancelledError:
                        pass
                
                # 发送剩余的进度更新
                async with progress_updates_lock:
                    while progress_updates_list:
                        status_update = progress_updates_list.pop(0)
                        yield status_update
                
                if skill_result.success:
                    # 更新规划文件
                    if self.enable_planning and self.planning_manager and planning_files:
                        self.planning_manager.add_progress(
                            f"技能 {matched_skill.name} 执行成功",
                            files_modified=[],
                            session_id=session_id
                        )
                    
                    # 格式化结果
                    result_text = self._format_skill_result(matched_skill, skill_result)
                    # 流式输出结果
                    for char in result_text:
                        yield char
                    full_result = result_text
                    
                    # 更新任务状态
                    if task_id:
                        task_info = task_manager.get_task(task_id)
                        if task_info:
                            task_info.status = TaskStatus.COMPLETED
                            task_info.progress = 100
                            task_info.message = "任务完成"
                            task_info.result = full_result
                            from datetime import datetime
                            task_info.completed_at = datetime.now()
                else:
                    # 更新规划文件（记录错误）
                    if self.enable_planning and self.planning_manager and planning_files:
                        self.planning_manager.add_error(
                            f"技能 {matched_skill.name} 执行失败",
                            attempt=1,
                            resolution=skill_result.error or "未知错误",
                            session_id=session_id
                        )
                    
                    # 格式化错误信息，确保完整且可读
                    error_detail = skill_result.error or '未知错误'
                    # 如果错误信息很长，只取第一行（通常是错误类型和消息）
                    if '\n' in error_detail:
                        error_lines = error_detail.split('\n')
                        error_detail = error_lines[0]  # 只取第一行
                        if len(error_lines) > 1:
                            # 如果有更多信息，添加提示
                            error_detail += f"（完整错误信息已记录到日志）"
                    
                    error_msg = f"技能执行失败: {error_detail}\n"
                    yield error_msg
                    full_result = error_msg
                    
                    # 记录完整错误信息到日志
                    if skill_result.error and '\n' in skill_result.error:
                        logger.error(f"技能 {matched_skill.name} 执行失败（完整错误）:\n{skill_result.error}")
                    
                    # 更新任务状态
                    if task_id:
                        task_info = task_manager.get_task(task_id)
                        if task_info:
                            task_info.status = TaskStatus.FAILED
                            task_info.error = skill_result.error
                            task_info.message = f"任务失败: {skill_result.error}"
                            from datetime import datetime
                            task_info.completed_at = datetime.now()
                
                # 保存消息到历史
                self.context_manager.add_message(session_id, MessageRole.USER, task)
                self.context_manager.add_message(session_id, MessageRole.ASSISTANT, full_result)
                self.debug.log_context_operation("保存消息", session_id, {"user": True, "assistant": True})
                
                # 对话评估并记录到规划文件（集成规划功能）
                if self.enable_planning and self.evaluator and planning_files:
                    try:
                        # 评估当前对话
                        evaluation_result = await self.evaluator.evaluate_conversation_turn(
                            user_message=task,
                            assistant_message=full_result,
                            context=None
                        )
                        
                        # 记录评估结果到 findings.md
                        overall_score = evaluation_result.get("overall_score", 0)
                        dimension_scores = evaluation_result.get("dimension_scores", {})
                        evaluation_text = evaluation_result.get("evaluation", "")
                        
                        # 格式化评估结果
                        eval_summary = f"总体分数: {overall_score}/100\n"
                        for dim_id, score in dimension_scores.items():
                            dim_name = self.evaluator.EVALUATION_DIMENSIONS.get(dim_id, {}).get("name", dim_id)
                            eval_summary += f"{dim_name}: {score}/100\n"
                        if evaluation_text:
                            eval_summary += f"评估说明: {evaluation_text}\n"
                        
                        self.planning_manager.add_finding(
                            f"对话评估结果:\n{eval_summary}",
                            category="Technical Decisions",
                            session_id=session_id
                        )
                        
                        # 如果分数较低，记录到错误表
                        if overall_score < 60:
                            self.planning_manager.add_error(
                                f"对话质量评分较低: {overall_score}/100",
                                attempt=1,
                                resolution=evaluation_text or "需要改进回答质量",
                                session_id=session_id
                            )
                        
                        # 发送评估结果
                        evaluation_info = {
                            "type": "evaluation",
                            "evaluation": evaluation_result
                        }
                        yield StreamMessageBuilder.build_evaluation(evaluation_info)
                        logger.info(f"对话评估完成，分数: {overall_score}/100")
                    except Exception as e:
                        logger.warning(f"对话评估失败: {str(e)}", exc_info=True)
                elif self.enable_evaluation:
                    # 如果没有规划功能，使用原来的评估逻辑
                    try:
                        history = self.context_manager.get_messages(session_id, compressed=False)
                        if len(history) >= 2:
                            prev_user_msg = None
                            prev_assistant_msg = None
                            for i in range(len(history) - 1, -1, -1):
                                msg = history[i]
                                if msg.role == MessageRole.ASSISTANT and prev_assistant_msg is None:
                                    prev_assistant_msg = msg
                                elif msg.role == MessageRole.USER and prev_assistant_msg is not None:
                                    prev_user_msg = msg
                                    break
                            
                            if prev_user_msg and prev_assistant_msg:
                                prev_evaluation = prev_assistant_msg.metadata.get("evaluation") if prev_assistant_msg.metadata else None
                                if not prev_evaluation:
                                    evaluation_result = await self.evaluator.evaluate_conversation_turn(
                                        user_message=prev_user_msg.content,
                                        assistant_message=prev_assistant_msg.content,
                                        context=None
                                    )
                                    if prev_assistant_msg.metadata is None:
                                        prev_assistant_msg.metadata = {}
                                    prev_assistant_msg.metadata["evaluation"] = evaluation_result
                                    self.context_manager.storage.save_message(session_id, prev_assistant_msg)
                                    evaluation_info = {
                                        "type": "evaluation",
                                        "evaluation": evaluation_result
                                    }
                                    yield StreamMessageBuilder.build_evaluation(evaluation_info)
                                    logger.info(f"对话评估完成，分数: {evaluation_result.get('overall_score', 'N/A')}/100")
                    except Exception as e:
                        logger.warning(f"对话评估失败: {str(e)}", exc_info=True)
                
                return  # 技能执行完成，直接返回
            except Exception as e:
                logger.error(f"技能 {matched_skill.name} 执行异常: {str(e)}", exc_info=True)
                
                # 更新任务状态（如果是长任务）
                if 'task_id' in locals() and task_id:
                    from backend.core.agent.task_manager import TaskStatus
                    task_info = task_manager.get_task(task_id)
                    if task_info:
                        task_info.status = TaskStatus.FAILED
                        task_info.error = str(e)
                        task_info.message = f"任务异常: {str(e)}"
                        from datetime import datetime
                        task_info.completed_at = datetime.now()
                
                # 技能执行异常，继续使用 LLM 处理
                error_msg = f"技能执行失败: {str(e)}，将使用 LLM 处理"
                yield f"[错误] {error_msg}\n\n"
        
        # 6. 如果没有匹配到技能，使用工具（规划功能和会话ID已在前面处理）
        # system_prompt 和 user_prompt 已在前面构建
        
        # 发送调试信息：开始工具调用流程
        debug_info = {
            "type": "debug",
            "category": "orchestrator",
            "message": "未匹配到技能，使用工具处理",
            "details": {}
        }
        yield StreamMessageBuilder.build_debug(debug_info)
        
        # 获取工具定义（LLM Function Calling 格式）
        tools = self.tool_registry.get_tools_for_llm()
        tool_names = [t.get("function", {}).get("name", "unknown") for t in tools] if tools else []
        debug_info = {
            "type": "debug",
            "category": "orchestrator",
            "message": "准备工具",
            "details": {"tool_count": len(tools), "tools": tool_names}
        }
        yield StreamMessageBuilder.build_debug(debug_info)
        self.debug.log_orchestrator_step("准备工具", {"tool_count": len(tools), "tools": tool_names})
        
        # 智能模型选择：使用 chat 模型分析任务，决定使用哪个模型
        debug_info = {
            "type": "debug",
            "category": "orchestrator",
            "message": "开始模型选择",
            "details": {}
        }
        yield StreamMessageBuilder.build_debug(debug_info)
        
        selected_model = await self._select_model(task)
        if selected_model != self.llm_service.model:
            self.llm_service.set_model(selected_model)
        # 总是显示模型选择信息（即使模型没有改变）
        self.debug.log_orchestrator_step("模型选择", {"selected_model": selected_model})
        debug_info = {
            "type": "debug",
            "category": "orchestrator",
            "message": "模型选择",
            "details": {"selected_model": selected_model}
        }
        yield StreamMessageBuilder.build_debug(debug_info)
        
        # 如果有工具可用，先完成工具调用（非流式），然后流式返回最终结果
        if tools:
            try:
                # 发送调试信息：开始工具调用
                debug_info = {
                    "type": "debug",
                    "category": "orchestrator",
                    "message": "开始调用LLM进行工具选择",
                    "details": {}
                }
                yield StreamMessageBuilder.build_debug(debug_info)
                
                # 使用工具调用获取完整响应（带调试信息）
                full_response = ""
                async for chunk in self._chat_with_tools_stream(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    tools=tools,
                    planning_files=planning_files,
                    session_id=session_id
                ):
                    # 检查是否是调试信息、工具调用信息或状态更新
                    if chunk.startswith("__DEBUG__:") or chunk.startswith("__TOOL__:") or chunk.startswith("__STATUS__:"):
                        yield chunk
                    else:
                        # 内容块
                        full_response += chunk
                        yield chunk
                
                # 确保 full_response 是字符串
                if full_response is None:
                    full_response = ""
                else:
                    full_response = str(full_response)
                
                # full_response 已经在上面流式输出了
                self.debug.log_llm_response(full_response, "deepseek-chat")
            except Exception as e:
                logger.error(f"流式处理工具调用失败: {str(e)}", exc_info=True)
                error_msg = f"处理请求时出错：{str(e)}"
                for char in error_msg:
                    yield char
                # 不重新抛出异常，让流式响应正常完成
        else:
            # 没有工具，直接流式调用 LLM
            self.debug.log_llm_request(system_prompt, user_prompt, "deepseek-chat")
            full_response = ""
            
            async for chunk in self.llm_service.stream_chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            ):
                full_response += chunk
                yield chunk
            
            self.debug.log_llm_response(full_response, "deepseek-chat")
        
        # 重置为默认模型
        self.llm_service.reset_model()
        
        # 对话评估：评估上一轮对话（如果有）
        # 第一轮对话不评估，从第二轮开始评估上一轮
        if self.enable_evaluation:
            try:
                # 获取历史消息（在保存当前消息之前）
                history = self.context_manager.get_messages(session_id, compressed=False)
                
                # 检查是否有上一轮完整的对话（user + assistant）
                # 需要至少 2 条消息（一条 user，一条 assistant）才算上一轮
                if len(history) >= 2:
                    # 获取上一轮的 user 和 assistant 消息
                    prev_user_msg = None
                    prev_assistant_msg = None
                    
                    # 从后往前查找最后一对 user-assistant
                    for i in range(len(history) - 1, -1, -1):
                        msg = history[i]
                        if msg.role == MessageRole.ASSISTANT and prev_assistant_msg is None:
                            prev_assistant_msg = msg
                        elif msg.role == MessageRole.USER and prev_assistant_msg is not None:
                            prev_user_msg = msg
                            break
                    
                    # 如果找到上一轮对话，且 assistant 消息还没有评估过
                    if prev_user_msg and prev_assistant_msg:
                        # 检查是否已经评估过
                        prev_evaluation = prev_assistant_msg.metadata.get("evaluation") if prev_assistant_msg.metadata else None
                        if not prev_evaluation:
                            # 评估上一轮对话
                            evaluation_result = await self.evaluator.evaluate_conversation_turn(
                                user_message=prev_user_msg.content,
                                assistant_message=prev_assistant_msg.content,
                                context=None
                            )
                            
                            # 将评估结果保存到上一轮 assistant 消息的 metadata
                            if prev_assistant_msg.metadata is None:
                                prev_assistant_msg.metadata = {}
                            prev_assistant_msg.metadata["evaluation"] = evaluation_result
                            
                            # 更新上一轮 assistant 消息
                            self.context_manager.storage.save_message(session_id, prev_assistant_msg)
                            
                            # 发送评估结果到前端
                            evaluation_info = {
                                "type": "evaluation",
                                "evaluation": evaluation_result
                            }
                            yield StreamMessageBuilder.build_evaluation(evaluation_info)
                            logger.info(f"对话评估完成，分数: {evaluation_result.get('overall_score', 'N/A')}/100")
            except Exception as e:
                logger.warning(f"对话评估失败: {str(e)}", exc_info=True)
                # 评估失败不影响正常流程
        
        # 保存消息到历史
        self.context_manager.add_message(session_id, MessageRole.USER, task)
        self.context_manager.add_message(session_id, MessageRole.ASSISTANT, full_response)
        self.debug.log_context_operation("保存消息", session_id, {"user": True, "assistant": True})
        
        # 规划功能：对话完成后评估并记录到规划文件（方案2）
        if self.enable_planning and self.evaluator and planning_files:
            try:
                # 评估对话质量
                evaluation_result = await self.evaluator.evaluate_conversation_turn(
                    user_message=task,
                    assistant_message=full_response,
                    context=history[-5:] if history else None  # 使用最近5条作为上下文
                )
                
                # 记录评估结果到 findings.md
                overall_score = evaluation_result.get("overall_score", 0)
                dimension_scores = evaluation_result.get("dimension_scores", {})
                evaluation_text = evaluation_result.get("evaluation", "")
                
                # 格式化评估结果
                eval_summary = f"总体分数: {overall_score}/100\n"
                for dim_id, score in dimension_scores.items():
                    dim_name = self.evaluator.EVALUATION_DIMENSIONS.get(dim_id, {}).get("name", dim_id)
                    eval_summary += f"{dim_name}: {score}/100\n"
                if evaluation_text:
                    eval_summary += f"评估说明: {evaluation_text}\n"
                
                self.planning_manager.add_finding(
                    f"对话评估结果:\n{eval_summary}",
                    category="Technical Decisions",
                    session_id=session_id
                )
                
                # 如果分数较低，记录到错误表
                if overall_score < 60:
                    self.planning_manager.add_error(
                        f"对话质量评分较低: {overall_score}/100",
                        attempt=1,
                        resolution=evaluation_text or "需要改进回答质量",
                        session_id=session_id
                    )
                
                debug_info = {
                    "type": "debug",
                    "category": "planning",
                    "message": "对话评估完成并记录到规划文件",
                    "details": {"overall_score": overall_score}
                }
                yield StreamMessageBuilder.build_debug(debug_info)
                logger.info(f"对话评估完成，分数: {overall_score}/100")
            except Exception as e:
                logger.warning(f"对话评估失败: {str(e)}", exc_info=True)
                # 评估失败不影响主流程
        
        # 规划功能：刷新待更新的操作，确保数据持久化
        if self.enable_planning and self.planning_manager and planning_files:
            try:
                self.planning_manager.flush_updates()
                
                # 定期清理旧文件
                self._planning_cleanup_counter += 1
                if self._planning_cleanup_counter >= self._planning_cleanup_interval:
                    self._planning_cleanup_counter = 0
                    cleanup_stats = self.planning_manager.cleanup_old_files(
                        max_age_days=self._planning_max_age_days,
                        max_files=self._planning_max_files
                    )
                    if cleanup_stats["total_deleted"] > 0:
                        logger.info(f"规划文件清理完成: {cleanup_stats}")
            except Exception as e:
                logger.warning(f"刷新规划文件更新失败: {str(e)}")
        
        debug_info = {
            "type": "debug",
            "category": "orchestrator",
            "message": "流式任务处理完成",
            "details": {"response_length": len(full_response)}
        }
        yield StreamMessageBuilder.build_debug(debug_info)
        self.debug.log_orchestrator_step("流式任务处理完成", {"response_length": len(full_response)})
    
    def _extract_skill_parameters(self, task: str, skill) -> Dict[str, Any]:
        """
        从用户任务中提取技能参数
        
        Args:
            task: 用户任务描述
            skill: 技能对象
            
        Returns:
            参数字典
        """
        import re
        from urllib.parse import urlparse
        
        parameters = {}
        
        # 提取 URL（适用于 video_summary 等需要 URL 的技能）
        # 改进的 URL 正则：匹配 http:// 或 https:// 开头的 URL，直到遇到空格、引号、逗号、句号等
        url_pattern = r'https?://[^\s"\'\),。，、]+'
        raw_urls = re.findall(url_pattern, task)
        
        # 清理 URL：移除末尾的标点符号
        urls = []
        for url in raw_urls:
            # 移除末尾的常见标点符号
            url = url.rstrip('.,;:!?)\'"）')
            # 确保 URL 是有效的
            if url.startswith('http://') or url.startswith('https://'):
                urls.append(url)
        
        if urls:
            # 如果是单个 URL，使用 url 参数
            if len(urls) == 1:
                parameters['url'] = urls[0]
            # 如果是多个 URL，根据技能类型处理
            elif len(urls) > 1:
                # 对于 video_downloader 技能，支持批量下载
                if skill.name == 'video_downloader':
                    parameters['urls'] = urls
                    logger.info(f"检测到多个 URL（共 {len(urls)} 个），video_downloader 技能支持批量下载")
                # 对于 video_summary 技能，目前只支持单个 URL，先处理第一个
                elif skill.name == 'video_summary':
                    parameters['url'] = urls[0]
                    logger.warning(f"检测到多个 URL（共 {len(urls)} 个），video_summary 技能目前只支持单个 URL，将处理第一个: {urls[0]}")
                    logger.info(f"其他 URL: {urls[1:]}")
                # 对于其他技能，可以支持多个 URL（如果技能支持）
                else:
                    # 如果技能参数支持数组类型的 url，使用所有 URL
                    url_param = next((p for p in skill.parameters if p.name == 'url' or p.name == 'urls'), None)
                    if url_param and url_param.type == 'array':
                        parameters[url_param.name] = urls
                    else:
                        # 否则只使用第一个
                        parameters['url'] = urls[0]
                        logger.warning(f"检测到多个 URL（共 {len(urls)} 个），但技能不支持数组参数，将处理第一个: {urls[0]}")
        
        # 提取本地文件路径（适用于 video_summary 等需要本地文件路径的技能）
        # 使用统一的路径提取工具，确保鲁棒性
        from backend.core.agent.utils.path_utils import PathExtractor
        local_files = PathExtractor.extract_paths(task)
        
        # #region agent log
        try:
            import json
            import time
            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"J","location":"orchestrator.py:_extract_skill_parameters:after_extract_local_files","message":"提取本地文件路径后","data":{"local_files":local_files,"local_files_count":len(local_files),"skill_name":skill.name},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                f.flush()
        except: pass
        # #endregion
        
        # 对于 video_summary 技能，如果检测到本地文件路径，使用 video_path 参数
        if local_files and skill.name == 'video_summary':
            # 如果只有一个文件，使用 video_path
            if len(local_files) == 1:
                parameters['video_path'] = local_files[0]
                # #region agent log
                try:
                    import json
                    import time
                    with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"J","location":"orchestrator.py:_extract_skill_parameters:single_file","message":"单个文件，设置video_path","data":{"video_path":local_files[0]},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                        f.flush()
                except: pass
                # #endregion
            # 如果有多个文件，使用 video_paths（如果技能支持）或只使用第一个
            elif len(local_files) > 1:
                # 检查技能是否支持 video_paths 参数
                video_paths_param = next((p for p in skill.parameters if p.name == 'video_paths'), None)
                if video_paths_param and video_paths_param.type == 'array':
                    parameters['video_paths'] = local_files
                    # #region agent log
                    try:
                        import json
                        import time
                        with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"J","location":"orchestrator.py:_extract_skill_parameters:multiple_files","message":"多个文件，设置video_paths","data":{"video_paths":local_files},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                            f.flush()
                    except: pass
                    # #endregion
                else:
                    # 否则只使用第一个文件
                    parameters['video_path'] = local_files[0]
                    logger.warning(f"检测到多个本地文件（共 {len(local_files)} 个），但技能不支持数组参数，将处理第一个: {local_files[0]}")
                    # #region agent log
                    try:
                        import json
                        import time
                        with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"J","location":"orchestrator.py:_extract_skill_parameters:multiple_files_first_only","message":"多个文件但只使用第一个","data":{"video_path":local_files[0],"total_files":len(local_files)},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                            f.flush()
                    except: pass
                    # #endregion
        
        # 使用默认值填充可选参数
        for param in skill.parameters:
            if param.name not in parameters:
                if param.default is not None:
                    parameters[param.name] = param.default
        
        logger.info(f"提取的技能参数: {parameters}")
        return parameters
    
    def _format_skill_result(self, skill, skill_result: 'SkillResult') -> str:
        """
        格式化技能执行结果为文本
        
        Args:
            skill: 技能对象
            skill_result: 技能执行结果
        
        Returns:
            格式化的文本结果
        """
        if not skill_result.success:
            return f"❌ 技能执行失败: {skill_result.error or '未知错误'}"
        
        data = skill_result.data or {}
        
        # 根据技能类型格式化结果
        if skill.name == 'video_downloader':
            results = data.get('results', [])
            errors = data.get('errors', [])
            total = data.get('total', 0)
            success_count = data.get('success', 0)
            failed_count = data.get('failed', 0)
            
            result_text = f"## 📥 视频下载完成\n\n"
            result_text += f"**总计**: {total} 个视频\n"
            result_text += f"**成功**: {success_count} 个\n"
            result_text += f"**失败**: {failed_count} 个\n\n"
            
            if results:
                result_text += "### ✅ 成功下载的视频：\n"
                for i, result in enumerate(results, 1):
                    url = result.get('url', 'N/A')
                    output_file = result.get('output_file', '')
                    subtitle_file = result.get('subtitle_file', '')
                    retry_with_cookies = result.get('retry_with_cookies', False)
                    
                    result_text += f"{i}. {url}\n"
                    if output_file:
                        result_text += f"   📹 视频文件: {output_file}\n"
                    if subtitle_file:
                        result_text += f"   📝 字幕文件: {subtitle_file}\n"
                    if retry_with_cookies:
                        result_text += f"   💡 使用 cookies 重试成功\n"
                    result_text += "\n"
            
            if errors:
                result_text += "### ❌ 下载失败的视频：\n"
                for i, error in enumerate(errors, 1):
                    url = error.get('url', 'N/A')
                    error_msg = error.get('error', '未知错误')
                    result_text += f"{i}. {url}\n"
                    result_text += f"   错误: {error_msg}\n\n"
            
            return result_text
        else:
            # 其他技能，使用通用格式
            if data:
                import json
                return json.dumps(data, ensure_ascii=False, indent=2)
            return "✅ 技能执行完成"
    
    async def _chat_with_tools_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: Optional[list] = None,
        planning_files: Optional[Any] = None,
        session_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        带工具调用的聊天（流式版本，包含调试信息）
        
        Args:
            system_prompt: 系统提示
            user_prompt: 用户提示
            tools: 工具定义列表
            planning_files: 规划文件对象（可选，用于记录工具调用进度）
            session_id: 会话ID（可选，用于规划文件记录）
            
        Yields:
            流式数据块（调试信息、工具调用信息或内容）
        """
        import json
        
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})
            
            max_iterations = 100  # 最多 100 轮工具调用循环
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                debug_info = {
                    "type": "debug",
                    "category": "orchestrator",
                    "message": f"工具调用循环第 {iteration} 轮",
                    "details": {}
                }
                yield StreamMessageBuilder.build_debug(debug_info)
                self.debug.log_orchestrator_step(f"工具调用循环第 {iteration} 轮", {})
                
                try:
                    # 调用 LLM（使用 messages 而不是 system_prompt/user_prompt）
                    response = await self.llm_service.chat(messages=messages, tools=tools)
                except Exception as e:
                    logger.error(f"LLM 调用失败: {str(e)}", exc_info=True)
                    yield f"抱歉，处理您的请求时出现错误：{str(e)}"
                    return
                
                # 检查响应类型
                if isinstance(response, str):
                    # 普通文本回复，直接返回
                    yield response
                    return
                
                # 检查是否有工具调用
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    debug_info = {
                        "type": "debug",
                        "category": "orchestrator",
                        "message": "检测到工具调用",
                        "details": {"count": len(response.tool_calls)}
                    }
                    yield StreamMessageBuilder.build_debug(debug_info)
                    self.debug.log_orchestrator_step("检测到工具调用", {"count": len(response.tool_calls)})
                    
                    # 执行所有工具调用
                    tool_results = []
                    for tool_call in response.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args_str = tool_call.function.arguments
                        
                        debug_info = {
                            "type": "debug",
                            "category": "orchestrator",
                            "message": "执行工具",
                            "details": {"name": tool_name, "args": tool_args_str}
                        }
                        yield StreamMessageBuilder.build_debug(debug_info)
                        self.debug.log_orchestrator_step("执行工具", {"name": tool_name, "args": tool_args_str})
                        
                        # 解析参数
                        try:
                            tool_args = json.loads(tool_args_str)
                        except json.JSONDecodeError:
                            tool_args = {}
                        
                        # 执行工具（支持进度报告）
                        try:
                            # 获取工具实例
                            tool = self.tool_registry.get_tool(tool_name)
                            
                            if tool and hasattr(tool, 'set_progress_callback'):
                                # 创建一个队列来收集进度消息
                                import queue
                                progress_queue = queue.Queue()
                                
                                def progress_callback(message: str):
                                    """工具进度回调（收集到队列）"""
                                    progress_queue.put(message)
                                
                                tool.set_progress_callback(progress_callback)
                                
                                # 在后台线程中执行工具，同时定期检查进度
                                import asyncio
                                import concurrent.futures
                                
                                loop = asyncio.get_event_loop()
                                executor = concurrent.futures.ThreadPoolExecutor()
                                
                                # 启动工具执行任务
                                tool_future = loop.run_in_executor(
                                    executor,
                                    lambda: self.tool_registry.execute(tool_name, **tool_args)
                                )
                                
                                # 定期检查进度并发送
                                while not tool_future.done():
                                    try:
                                        # 检查进度队列
                                        while not progress_queue.empty():
                                            progress_msg = progress_queue.get_nowait()
                                            progress_info = {
                                                "type": "progress",
                                                "category": "tool",
                                                "tool_name": tool_name,
                                                "message": progress_msg
                                            }
                                            yield f"__PROGRESS__:{json.dumps(progress_info, ensure_ascii=False)}\n"
                                        
                                        # 等待一小段时间
                                        await asyncio.sleep(1)
                                    except Exception as e:
                                        logger.warning(f"进度检查错误: {e}")
                                        break
                                
                                # 获取最终结果
                                tool_result = await tool_future
                                
                                # 发送剩余的进度消息
                                while not progress_queue.empty():
                                    progress_msg = progress_queue.get_nowait()
                                    progress_info = {
                                        "type": "progress",
                                        "category": "tool",
                                        "tool_name": tool_name,
                                        "message": progress_msg
                                    }
                                    yield f"__PROGRESS__:{json.dumps(progress_info, ensure_ascii=False)}\n"
                            else:
                                # 没有进度回调支持，直接执行
                                if hasattr(self.tool_registry, 'execute_async'):
                                    tool_result = await self.tool_registry.execute_async(tool_name, **tool_args)
                                else:
                                    tool_result = self.tool_registry.execute(tool_name, **tool_args)
                        except Exception as e:
                            logger.error(f"工具执行失败: {tool_name}, 错误: {str(e)}", exc_info=True)
                            tool_result = ToolResult(
                                success=False,
                                error=f"工具执行失败: {str(e)}"
                            )
                        
                        # 检查是否需要确认（针对 execute_code 工具）
                        if (tool_name == "execute_code" and 
                            tool_result.data and 
                            tool_result.data.get("requires_confirmation")):
                            # 发送确认请求
                            confirm_info = {
                                "type": "confirm",
                                "tool_name": tool_name,
                                "code": tool_result.data.get("code", ""),
                                "language": tool_result.data.get("language", ""),
                                "risk_level": tool_result.data.get("risk_level", ""),
                                "reason": tool_result.data.get("reason", ""),
                                "requires_password": tool_result.data.get("requires_password", False),
                                "explanation": tool_result.data.get("explanation", "")
                            }
                            yield f"__CONFIRM__:{json.dumps(confirm_info, ensure_ascii=False)}\n"
                            
                            # 等待确认结果（暂时跳过，由前端处理）
                            # 这里我们需要一个机制来等待前端响应
                            # 暂时标记为需要确认，不继续执行
                            tool_result_content = json.dumps({
                                "error": "需要用户确认",
                                "requires_confirmation": True,
                                "success": False
                            }, ensure_ascii=False)
                            tool_results.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tool_name,
                                "content": tool_result_content
                            })
                            continue
                        
                        # 发送工具调用信息
                        tool_info = {
                            "type": "tool",
                            "name": tool_name,
                            "args": tool_args,
                            "success": tool_result.success,
                            "result": tool_result.data if tool_result.success else None,
                            "error": tool_result.error if not tool_result.success else None
                        }
                        yield StreamMessageBuilder.build_tool(tool_info)
                        
                        # 记录详细的执行结果
                        if not tool_result.success:
                            debug_info = {
                                "type": "debug",
                                "category": "orchestrator",
                                "message": "工具执行失败",
                                "details": {"name": tool_name, "error": tool_result.error}
                            }
                            yield StreamMessageBuilder.build_debug(debug_info)
                            self.debug.log_orchestrator_step("工具执行失败", {
                                "name": tool_name,
                                "error": tool_result.error
                            })
                        
                        # 构建工具结果消息
                        # 如果工具执行失败，确保错误信息清晰
                        def safe_json_dumps(obj, **kwargs):
                            """安全的 JSON 序列化，处理编码错误"""
                            # #region agent log
                            import json as json_module
                            debug_log_path = PROJECT_ROOT / '.cursor' / 'debug.log'
                            try:
                                debug_log_path.parent.mkdir(parents=True, exist_ok=True)
                                with open(debug_log_path, 'a', encoding='utf-8') as f:
                                    json_module.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"orchestrator.py:safe_json_dumps","message":"JSON序列化开始","data":{"obj_type":type(obj).__name__,"is_dict":isinstance(obj,dict)},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                                    f.write('\n')
                            except: pass
                            # #endregion
                            try:
                                result = json.dumps(obj, ensure_ascii=False, **kwargs)
                                # #region agent log
                                try:
                                    debug_log_path.parent.mkdir(parents=True, exist_ok=True)
                                    with open(debug_log_path, 'a', encoding='utf-8') as f:
                                        json_module.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"orchestrator.py:safe_json_dumps","message":"JSON序列化成功","data":{"result_len":len(result)},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                                        f.write('\n')
                                except: pass
                                # #endregion
                                return result
                            except (UnicodeEncodeError, TypeError, UnicodeDecodeError) as e:
                                # #region agent log
                                try:
                                    debug_log_path.parent.mkdir(parents=True, exist_ok=True)
                                    with open(debug_log_path, 'a', encoding='utf-8') as f:
                                        json_module.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"orchestrator.py:safe_json_dumps","message":"JSON序列化失败","data":{"error_type":type(e).__name__,"error_msg":str(e)[:200]},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                                        f.write('\n')
                                except: pass
                                # #endregion
                                # 如果序列化失败，尝试清理数据
                                if isinstance(obj, dict):
                                    cleaned_obj = {}
                                    for k, v in obj.items():
                                        try:
                                            # 尝试清理值
                                            if isinstance(v, str):
                                                # #region agent log
                                                try:
                                                    debug_log_path.parent.mkdir(parents=True, exist_ok=True)
                                                    with open(debug_log_path, 'a', encoding='utf-8') as f:
                                                        json_module.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"orchestrator.py:safe_json_dumps","message":"清理字符串值","data":{"key":str(k)[:50],"value_len":len(v),"value_preview":v[:100]},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                                                        f.write('\n')
                                                except: pass
                                                # #endregion
                                                # 清理字符串中的无效字符
                                                cleaned_v = v.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                                            else:
                                                cleaned_v = v
                                            cleaned_obj[k] = cleaned_v
                                        except Exception as clean_e:
                                            # #region agent log
                                            try:
                                                debug_log_path.parent.mkdir(parents=True, exist_ok=True)
                                                with open(debug_log_path, 'a', encoding='utf-8') as f:
                                                    json_module.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"orchestrator.py:safe_json_dumps","message":"清理值失败","data":{"key":str(k)[:50],"error":str(clean_e)[:200]},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                                                    f.write('\n')
                                            except: pass
                                            # #endregion
                                            cleaned_obj[k] = f"[无法序列化: {type(v).__name__}]"
                                    return json.dumps(cleaned_obj, ensure_ascii=False, **kwargs)
                                else:
                                    # 对于非字典对象，返回错误信息
                                    return json.dumps({"error": f"序列化失败: {str(e)[:100]}"}, ensure_ascii=False)
                        
                        if not tool_result.success:
                            tool_result_content = safe_json_dumps({
                                "error": tool_result.error,
                                "success": False
                            })
                        else:
                            tool_result_content = safe_json_dumps(tool_result.data)
                        tool_results.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": tool_result_content
                        })
                        
                        debug_info = {
                            "type": "debug",
                            "category": "orchestrator",
                            "message": "工具执行完成",
                            "details": {
                                "name": tool_name,
                                "success": tool_result.success,
                                "error": tool_result.error if not tool_result.success else None
                            }
                        }
                        yield StreamMessageBuilder.build_debug(debug_info)
                        self.debug.log_orchestrator_step("工具执行完成", {
                            "name": tool_name,
                            "success": tool_result.success,
                            "error": tool_result.error if not tool_result.success else None
                        })
                        
                        # 规划功能：工具调用后，更新规划文件（方案2）
                        if self.enable_planning and self.planning_manager and planning_files:
                            try:
                                # 记录工具调用到 progress.md
                                self.planning_manager.add_progress(
                                    f"执行工具: {tool_name}",
                                    files_modified=[],
                                    session_id=session_id
                                )
                                
                                # 如果是研究类工具，记录到 findings.md
                                research_tools = ["google_search", "browser", "wikipedia", "web_fetch"]
                                if tool_name in research_tools and tool_result.success:
                                    result_summary = str(tool_result.data)[:200] if tool_result.data else "成功"
                                    self.planning_manager.add_finding(
                                        f"工具 {tool_name} 执行结果: {result_summary}",
                                        category="Research Findings",
                                        session_id=session_id
                                    )
                                
                                # 如果工具执行失败，记录错误
                                if not tool_result.success:
                                    self.planning_manager.add_error(
                                        f"工具 {tool_name} 执行失败",
                                        attempt=1,
                                        resolution=tool_result.error or "未知错误",
                                        session_id=session_id
                                    )
                            except Exception as e:
                                logger.warning(f"更新规划文件失败: {str(e)}")
                    
                    # 将助手消息添加到消息历史
                    assistant_message = {
                        "role": "assistant",
                        "content": response.content if response.content else None,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": tc.type,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in response.tool_calls
                        ]
                    }
                    messages.append(assistant_message)
                    
                    # 添加工具结果
                    messages.extend(tool_results)
                    
                    # 继续循环，让 LLM 基于工具结果生成回复
                    continue
                
                # 如果没有工具调用，返回内容
                if hasattr(response, 'content') and response.content:
                    yield response.content
                    return
                
                # 如果都没有，返回空字符串
                yield ""
                return
            
            # 达到最大迭代次数，返回错误信息
            debug_info = {
                "type": "debug",
                "category": "orchestrator",
                "message": "达到最大工具调用迭代次数",
                "details": {"max_iterations": max_iterations}
            }
            yield StreamMessageBuilder.build_debug(debug_info)
            self.debug.log_orchestrator_step("达到最大工具调用迭代次数", {"max_iterations": max_iterations})
            yield "抱歉，工具调用未能成功获取信息。"
        except Exception as e:
            logger.error(f"_chat_with_tools_stream 执行失败: {str(e)}", exc_info=True)
            yield f"抱歉，处理您的请求时出现错误：{str(e)}"
    
    async def _chat_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: Optional[list] = None
    ) -> str:
        """
        带工具调用的聊天（处理工具调用循环）
        
        Args:
            system_prompt: 系统提示
            user_prompt: 用户提示
            tools: 工具定义列表
            
        Returns:
            LLM 生成的最终回复
        """
        import json
        
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})
            
            max_iterations = 5  # 最多 5 轮工具调用循环
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                self.debug.log_orchestrator_step(f"工具调用循环第 {iteration} 轮", {})
                
                try:
                    # 调用 LLM（使用 messages 而不是 system_prompt/user_prompt）
                    response = await self.llm_service.chat(messages=messages, tools=tools)
                except Exception as e:
                    logger.error(f"LLM 调用失败: {str(e)}", exc_info=True)
                    return f"抱歉，处理您的请求时出现错误：{str(e)}"
                
                # 检查响应类型
                if isinstance(response, str):
                    # 普通文本回复
                    # 如果启用了自动代码执行，检查并执行代码块
                    if self.auto_execute_code and self.auto_code_executor:
                        try:
                            processed = await self.auto_code_executor.process_llm_output(
                                response,
                                auto_execute=True,
                                require_confirmation=False
                            )
                            
                            if processed["code_executed"]:
                                # 如果有代码执行，将结果反馈给 LLM
                                feedback_message = self._build_execution_feedback(processed["execution_results"])
                                
                                # 将执行结果添加到消息中，让 LLM 基于结果生成最终回复
                                messages.append({"role": "assistant", "content": response})
                                messages.append({
                                    "role": "user",
                                    "content": f"代码执行完成。执行结果：\n{feedback_message}\n\n请基于执行结果给出最终回复。"
                                })
                                
                                # 继续下一轮，让 LLM 基于执行结果生成回复
                                continue
                            else:
                                # 没有代码执行，直接返回
                                return response
                        except Exception as e:
                            logger.error(f"自动代码执行失败: {str(e)}", exc_info=True)
                            # 执行失败，返回原始回复
                            return response
                    else:
                        # 未启用自动代码执行，直接返回
                        return response
                
                # 检查是否有工具调用
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    self.debug.log_orchestrator_step("检测到工具调用", {"count": len(response.tool_calls)})
                    
                    # 执行所有工具调用
                    tool_results = []
                    for tool_call in response.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args_str = tool_call.function.arguments
                        
                        self.debug.log_orchestrator_step("执行工具", {"name": tool_name, "args": tool_args_str})
                        
                        # 解析参数
                        try:
                            tool_args = json.loads(tool_args_str)
                        except json.JSONDecodeError:
                            tool_args = {}
                        
                        # 执行工具（支持进度报告）
                        try:
                            # 获取工具实例
                            tool = self.tool_registry.get_tool(tool_name)
                            
                            if tool and hasattr(tool, 'set_progress_callback'):
                                # 创建进度队列和回调
                                import queue
                                progress_queue = queue.Queue()
                                
                                def progress_callback(message: str):
                                    """工具进度回调（收集到队列）"""
                                    progress_queue.put(message)
                                
                                tool.set_progress_callback(progress_callback)
                                
                                # 在后台线程中执行工具，同时定期检查进度
                                import asyncio
                                import concurrent.futures
                                
                                loop = asyncio.get_event_loop()
                                
                                # 启动工具执行任务（在线程池中）
                                tool_future = loop.run_in_executor(
                                    None,
                                    lambda: self.tool_registry.execute(tool_name, **tool_args)
                                )
                                
                                # 定期检查进度并发送
                                while not tool_future.done():
                                    try:
                                        # 检查进度队列并发送所有进度消息
                                        progress_sent = False
                                        while not progress_queue.empty():
                                            try:
                                                progress_msg = progress_queue.get_nowait()
                                                # 收集进度信息（非流式函数，不 yield）
                                                progress_sent = True
                                            except queue.Empty:
                                                break
                                        
                                        # 如果没有进度消息，等待一小段时间
                                        if not progress_sent:
                                            await asyncio.sleep(2)  # 每2秒检查一次
                                        else:
                                            await asyncio.sleep(0.1)  # 有进度时快速检查
                                    except Exception as e:
                                        logger.warning(f"进度检查错误: {e}")
                                        await asyncio.sleep(1)
                                
                                # 发送剩余的进度消息
                                while not progress_queue.empty():
                                    try:
                                        progress_msg = progress_queue.get_nowait()
                                        # 收集进度信息（非流式函数，不 yield）
                                        pass
                                    except queue.Empty:
                                        break
                                
                                # 获取最终结果
                                tool_result = await tool_future
                            else:
                                # 没有进度回调支持，直接执行
                                if hasattr(self.tool_registry, 'execute_async'):
                                    tool_result = await self.tool_registry.execute_async(tool_name, **tool_args)
                                else:
                                    tool_result = self.tool_registry.execute(tool_name, **tool_args)
                        except Exception as e:
                            logger.error(f"工具执行失败: {tool_name}, 错误: {str(e)}", exc_info=True)
                            tool_result = ToolResult(
                                success=False,
                                error=f"工具执行失败: {str(e)}"
                            )
                    
                    # 记录详细的执行结果
                    if not tool_result.success:
                        self.debug.log_orchestrator_step("工具执行失败", {
                            "name": tool_name,
                            "error": tool_result.error
                        })
                    
                    # 构建工具结果消息
                    # 如果工具执行失败，确保错误信息清晰
                    # 使用安全的 JSON 序列化
                    def safe_json_dumps(obj, **kwargs):
                        """安全的 JSON 序列化，处理编码错误"""
                        try:
                            return json.dumps(obj, ensure_ascii=False, **kwargs)
                        except (UnicodeEncodeError, TypeError) as e:
                            # 如果序列化失败，尝试清理数据
                            if isinstance(obj, dict):
                                cleaned_obj = {}
                                for k, v in obj.items():
                                    try:
                                        # 尝试清理值
                                        if isinstance(v, str):
                                            # 清理字符串中的无效字符
                                            cleaned_v = v.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                                        else:
                                            cleaned_v = v
                                        cleaned_obj[k] = cleaned_v
                                    except Exception:
                                        cleaned_obj[k] = f"[无法序列化: {type(v).__name__}]"
                                return json.dumps(cleaned_obj, ensure_ascii=False, **kwargs)
                            else:
                                # 对于非字典对象，返回错误信息
                                return json.dumps({"error": f"序列化失败: {str(e)[:100]}"}, ensure_ascii=False)
                    
                    if not tool_result.success:
                        tool_result_content = safe_json_dumps({
                            "error": tool_result.error,
                            "success": False
                        })
                    else:
                        tool_result_content = safe_json_dumps(tool_result.data)
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": tool_result_content
                    })
                    
                    self.debug.log_orchestrator_step("工具执行完成", {
                        "name": tool_name,
                        "success": tool_result.success,
                        "error": tool_result.error if not tool_result.success else None
                    })
                
                    # 将助手消息添加到消息历史
                    assistant_message = {
                        "role": "assistant",
                        "content": response.content if response.content else None,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": tc.type,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in response.tool_calls
                        ]
                    }
                    messages.append(assistant_message)
                    
                    # 添加工具结果
                    messages.extend(tool_results)
                    
                    # 继续循环，让 LLM 基于工具结果生成回复
                    continue
                
                # 如果没有工具调用，返回内容
                if hasattr(response, 'content') and response.content:
                    return response.content
                
                # 如果都没有，返回空字符串
                return ""
            
            # 达到最大迭代次数，返回错误信息
            self.debug.log_orchestrator_step("达到最大工具调用迭代次数", {"max_iterations": max_iterations})
            return "抱歉，工具调用未能成功获取信息。"
        except Exception as e:
            logger.error(f"_chat_with_tools 执行失败: {str(e)}", exc_info=True)
            return f"抱歉，处理您的请求时出现错误：{str(e)}"
    
    async def _select_model(self, task: str) -> str:
        """
        使用 chat 模型智能选择最适合的模型
        
        Args:
            task: 用户任务
            
        Returns:
            选定的模型名称: "deepseek-chat", "deepseek-reasoner", 或 "deepseek-coder"
        """
        # 使用 chat 模型分析任务类型
        model_selection_prompt = f"""分析以下任务，决定应该使用哪个 DeepSeek 模型：

任务：{task}

可选模型：
1. deepseek-chat: 适用于日常对话、文本生成、翻译、信息检索等一般性任务
2. deepseek-reasoner: 适用于需要复杂推理的任务，如数学推理、逻辑分析、策略制定、问题解决等
3. deepseek-coder: 适用于代码生成、代码补全、代码修复、代码审查、编程相关任务，以及简单的命令执行（如 ls、cat、cd 等）

重要提示：
- 如果任务是执行简单的系统命令（如显示文件、查看目录、执行脚本等），应该使用 deepseek-coder
- 如果任务需要复杂的逻辑推理、多步骤分析、策略制定，使用 deepseek-reasoner
- 如果任务只是简单的命令执行，不要使用 deepseek-reasoner，避免过度思考

请只返回模型名称（deepseek-chat、deepseek-reasoner 或 deepseek-coder），不要返回其他内容。"""

        try:
            # 临时切换到 chat 模型进行分析
            original_model = self.llm_service.model
            self.llm_service.set_model("deepseek-chat")
            
            # 使用 chat 模型分析
            analysis = await self.llm_service.chat(
                system_prompt="你是一个模型选择助手，根据任务类型选择最合适的模型。",
                user_prompt=model_selection_prompt
            )
            
            # 恢复原模型
            self.llm_service.set_model(original_model)
            
            # 解析返回的模型名称
            analysis = analysis.strip().lower()
            if "deepseek-reasoner" in analysis or "reasoner" in analysis:
                return "deepseek-reasoner"
            elif "deepseek-coder" in analysis or "coder" in analysis:
                return "deepseek-coder"
            else:
                # 默认使用 chat 模型
                return "deepseek-chat"
                
        except Exception as e:
            logger.warning(f"模型选择失败，使用默认模型: {e}")
            return "deepseek-chat"
