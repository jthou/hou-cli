"""Agent 编排器"""
import os
import logging
import time
import re
from pathlib import Path
from typing import Optional, Dict, Any, AsyncIterator, Tuple
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# 加载 .env 文件（在导入 LLMService 之前）
env_path = Path(__file__).parent.parent.parent.parent / '.env'
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
from shared.debug_utils import DebugOutput
from backend.core.agent.skills.registry import SkillRegistry
from backend.core.agent.skills.executor import SkillExecutor
from backend.core.agent.evaluator import ConversationEvaluator
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
        
        # 初始化对话评估器
        self.evaluator = ConversationEvaluator(llm_service=self.llm_service)
        self.enable_evaluation = True  # 配置项：是否启用对话评估
        
        # 代码执行相关组件
        self.auto_code_executor = None
        self.auto_execute_code = True  # 配置项：是否自动执行代码块
        
        # 注册天气工具（如果配置了 JWT）
        self._register_tools()
        
        # 初始化自动代码执行器
        self._init_auto_code_executor()
        
        # 初始化技能系统
        self.skill_registry = SkillRegistry()
        self.skill_executor = SkillExecutor(self.tool_registry, self.llm_service)
        self._register_skills()
        
        # self.workflow_identifier = WorkflowIdentifier()
        # self.workflow_engine = WorkflowEngine(self)
    
    def _register_skills(self):
        """注册所有可用技能
        
        自动从 skills 目录加载所有技能：
        - 每个技能一个子目录
        - 子目录中包含 skill.yaml 和 __init__.py
        """
        skills_dir = Path(__file__).parent / "skills"
        
        # 遍历技能目录
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and not skill_dir.name.startswith('_'):
                try:
                    # 尝试导入技能模块
                    module_name = f"backend.core.agent.skills.{skill_dir.name}"
                    skill_module = __import__(module_name, fromlist=[''])
                    
                    # 查找技能类（通常是技能目录名转换为类名）
                    skill_class_name = ''.join(word.capitalize() for word in skill_dir.name.split('_')) + 'Skill'
                    
                    if hasattr(skill_module, skill_class_name):
                        skill_class = getattr(skill_module, skill_class_name)
                        skill_instance = skill_class(self.skill_executor)
                        self.skill_registry.register(skill_instance)
                        logger.info(f"技能已注册: {skill_instance.name} (v{skill_instance.version})")
                    else:
                        logger.warning(f"技能目录 {skill_dir.name} 中未找到技能类 {skill_class_name}")
                except Exception as e:
                    logger.warning(f"注册技能 {skill_dir.name} 失败: {e}", exc_info=True)
    
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
    
    def _format_skill_result(self, skill_result) -> str:
        """
        格式化技能执行结果，包含文件路径信息
        
        Args:
            skill_result: SkillResult 对象
            
        Returns:
            格式化后的结果文本
        """
        import json
        
        if not skill_result.success:
            return f"❌ 技能执行失败: {skill_result.error}"
        
        data = skill_result.data or {}
        result_parts = []
        
        # 提取文件路径信息（如果存在）
        output_files_info = None
        if 'output_files' in data:
            output_files_text = data['output_files']
            if isinstance(output_files_text, str):
                # 解析纯文本格式的文件路径信息
                lines = output_files_text.split('\n')
                output_files_info = {}
                for line in lines:
                    line = line.strip()
                    if line.startswith('OUTPUT_DIR:'):
                        output_files_info['output_dir'] = line.split(':', 1)[1].strip()
                    elif line.startswith('SUMMARY_FILE:'):
                        output_files_info['summary_file'] = line.split(':', 1)[1].strip()
                    elif line.startswith('TIMESTAMP_MAPPING_FILE:'):
                        output_files_info['timestamp_mapping_file'] = line.split(':', 1)[1].strip()
                    elif line.startswith('ARTICLE_FILE:'):
                        output_files_info['article_file'] = line.split(':', 1)[1].strip()
                    elif line.startswith('EXTRACTED_PARAGRAPHS_FILE:'):
                        output_files_info['extracted_paragraphs_file'] = line.split(':', 1)[1].strip()
            elif isinstance(output_files_text, dict):
                output_files_info = output_files_text
        
        # 添加文件路径信息到输出（优先显示，让用户知道文件位置）
        if output_files_info:
            result_parts.append("\n" + "=" * 80)
            result_parts.append("📁 生成的文件路径（可直接打开）")
            result_parts.append("=" * 80 + "\n")
            
            # 收集所有文件路径
            file_paths = []
            
            if output_files_info.get('output_dir'):
                output_dir = output_files_info['output_dir']
                # 转换为绝对路径
                try:
                    from pathlib import Path
                    output_dir = str(Path(output_dir).resolve())
                except:
                    pass
                result_parts.append(f"📁 输出目录: {output_dir}\n\n")
            
            if output_files_info.get('summary_file'):
                summary_file = output_files_info['summary_file']
                try:
                    from pathlib import Path
                    summary_file = str(Path(summary_file).resolve())
                except:
                    pass
                file_paths.append(("📄 摘要文件", summary_file))
            
            if output_files_info.get('timestamp_mapping_file'):
                timestamp_file = output_files_info['timestamp_mapping_file']
                try:
                    from pathlib import Path
                    timestamp_file = str(Path(timestamp_file).resolve())
                except:
                    pass
                file_paths.append(("📋 时间戳映射文件", timestamp_file))
            
            if output_files_info.get('article_file'):
                article_file = output_files_info['article_file']
                try:
                    from pathlib import Path
                    article_file = str(Path(article_file).resolve())
                except:
                    pass
                file_paths.append(("📝 文章文件", article_file))
            
            if output_files_info.get('extracted_paragraphs_file'):
                paragraphs_file = output_files_info['extracted_paragraphs_file']
                try:
                    from pathlib import Path
                    paragraphs_file = str(Path(paragraphs_file).resolve())
                except:
                    pass
                file_paths.append(("📑 提取的完整段落文件", paragraphs_file))
            
            # 显示所有文件路径（带编号，方便引用）
            if file_paths:
                result_parts.append("### 📁 **生成的文件**\n")
                for i, (label, file_path) in enumerate(file_paths, 1):
                    # 提取文件名
                    try:
                        from pathlib import Path
                        file_name = Path(file_path).name
                    except:
                        file_name = file_path.split('/')[-1] if '/' in file_path else file_path.split('\\')[-1]
                    
                    result_parts.append(f"{i}. **`{file_name}`** - {label.replace('📄 ', '').replace('📋 ', '').replace('📝 ', '')}\n")
                    result_parts.append(f"   完整路径: `{file_path}`\n\n")
            
            result_parts.append("=" * 80 + "\n")
        
        # 添加摘要内容（如果有）
        if 'summary' in data:
            result_parts.append("\n" + "=" * 80)
            result_parts.append("📝 生成的摘要")
            result_parts.append("=" * 80 + "\n\n")
            summary = data['summary']
            if isinstance(summary, str):
                result_parts.append(summary)
            else:
                result_parts.append(str(summary))
            result_parts.append("\n")
        
        # 添加文章内容（如果有）
        if 'article' in data:
            result_parts.append("\n" + "=" * 80)
            result_parts.append("📄 生成的文章")
            result_parts.append("=" * 80 + "\n\n")
            article = data['article']
            if isinstance(article, str):
                result_parts.append(article)
            else:
                result_parts.append(str(article))
            result_parts.append("\n")
        
        # 如果没有特定内容，返回完整数据
        if not result_parts:
            result_parts.append("✅ 技能执行成功\n\n")
            result_parts.append(json.dumps(data, ensure_ascii=False, indent=2))
        
        return ''.join(result_parts)
    
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
        
        # 发送调试信息：开始处理
        debug_info = {
            "type": "debug",
            "category": "orchestrator",
            "message": "开始流式处理任务",
            "details": {"task": task[:50] + "..." if len(task) > 50 else task}
        }
        yield f"__DEBUG__:{json.dumps(debug_info, ensure_ascii=False)}\n"
        
        self.debug.log_orchestrator_step("开始流式处理任务", {"task": task[:50] + "..." if len(task) > 50 else task})
        
        # 获取会话 ID（如果提供）
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
            yield f"__DEBUG__:{json.dumps(debug_info, ensure_ascii=False)}\n"
            self.debug.log_context_operation("创建新会话", session_id)
        
        # 获取历史消息（不压缩，保留完整历史）
        # 注意：当 max_messages 和 max_tokens 都为 None 时，get_messages_for_llm 会获取完整历史
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
        yield f"__DEBUG__:{json.dumps(debug_info, ensure_ascii=False)}\n"
        self.debug.log_context_operation("获取历史消息", session_id, {"count": len(history), "has_history": len(history) > 0})
        
        # 对话评估：对上一轮对话进行评估（如果有）
        if self.enable_evaluation and len(history) >= 2:
            # 检查是否有上一轮完整的对话（user + assistant）
            last_user_idx = None
            last_assistant_idx = None
            
            # 从后往前查找最后一对 user-assistant
            for i in range(len(history) - 1, -1, -1):
                if history[i]["role"] == "assistant" and last_assistant_idx is None:
                    last_assistant_idx = i
                elif history[i]["role"] == "user" and last_assistant_idx is not None:
                    last_user_idx = i
                    break
            
            # 如果找到上一轮对话，且上一轮 assistant 消息还没有评估过
            if last_user_idx is not None and last_assistant_idx is not None:
                # 获取上一轮对话的完整消息对象（用于更新 metadata）
                all_messages = self.context_manager.get_messages(session_id, compressed=False)
                last_assistant_msg = None
                for msg in reversed(all_messages):
                    if msg.role.value == "assistant":
                        last_assistant_msg = msg
                        break
                
                # 检查是否已经评估过
                if last_assistant_msg and "evaluation" not in last_assistant_msg.metadata:
                    try:
                        # 获取上一轮对话内容
                        last_user_msg = history[last_user_idx]["content"]
                        last_assistant_msg_content = history[last_assistant_idx]["content"]
                        
                        # 获取上下文（上一轮之前的消息）
                        context = history[:last_user_idx] if last_user_idx > 0 else []
                        
                        # 进行评估
                        debug_info = {
                            "type": "debug",
                            "category": "evaluation",
                            "message": "开始评估上一轮对话",
                            "details": {}
                        }
                        yield f"__DEBUG__:{json.dumps(debug_info, ensure_ascii=False)}\n"
                        
                        evaluation_result = await self.evaluator.evaluate_conversation_turn(
                            user_message=last_user_msg,
                            assistant_message=last_assistant_msg_content,
                            context=context if context else None
                        )
                        
                        # 将评估结果保存到消息的 metadata 中
                        if last_assistant_msg:
                            if "evaluation" not in last_assistant_msg.metadata:
                                last_assistant_msg.metadata["evaluation"] = evaluation_result
                                # 更新消息（保存评估结果）
                                self.context_manager.storage.save_message(session_id, last_assistant_msg)
                        
                        # 发送评估结果到前端
                        eval_info = {
                            "type": "evaluation",
                            "overall_score": evaluation_result.get("overall_score", 0),
                            "dimension_scores": evaluation_result.get("dimension_scores", {}),
                            "evaluation": evaluation_result.get("evaluation", ""),
                            "timestamp": evaluation_result.get("timestamp", "")
                        }
                        yield f"__EVALUATION__:{json.dumps(eval_info, ensure_ascii=False)}\n"
                        
                        self.debug.log(f"对话评估完成，分数: {evaluation_result.get('overall_score', 0)}/100", level="info")
                        
                    except Exception as e:
                        logger.error(f"对话评估失败: {str(e)}", exc_info=True)
                        # 评估失败不影响对话继续
                        pass
        
        # 构建消息列表（与 process 方法保持一致）
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

3. **天气工具（get_weather）**：当用户询问天气信息时，必须使用 get_weather 工具来获取实时天气数据。绝对不要编造或猜测天气信息，也不要从历史对话记录中提取旧的天气信息。如果工具调用失败，请明确告诉用户工具调用失败，不要生成虚假的天气信息。

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
- 根据风力等级选择合适的风力图标"""
        
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
        
        # 先尝试匹配技能
        matched_skill = self.skill_registry.match(task)
        if matched_skill:
            debug_info = {
                "type": "debug",
                "category": "orchestrator",
                "message": "匹配到技能",
                "details": {"skill_name": matched_skill.name, "skill_description": matched_skill.description}
            }
            yield f"__DEBUG__:{json.dumps(debug_info, ensure_ascii=False)}\n"
            self.debug.log_orchestrator_step("匹配技能", {"skill_name": matched_skill.name})
            
            # 执行技能
            try:
                # 创建进度消息队列
                progress_messages = []
                
                # 设置进度回调
                def progress_callback(msg: str):
                    progress_messages.append(msg)
                
                matched_skill.set_progress_callback(progress_callback)
                self.skill_executor.set_progress_callback(progress_callback)
                
                # 执行技能（这里需要从用户输入中提取参数，简化处理）
                # TODO: 从用户输入中智能提取技能参数
                skill_parameters = self._extract_skill_parameters(task, matched_skill)
                
                skill_result = await matched_skill.execute(
                    parameters=skill_parameters,
                    context={
                        'progress_callback': progress_callback,
                        'tool_registry': self.tool_registry,
                        'llm_service': self.llm_service
                    }
                )
                
                # 输出进度消息
                for msg in progress_messages:
                    progress_info = {
                        "type": "progress",
                        "category": "skill",
                        "tool_name": matched_skill.name,
                        "message": msg
                    }
                    yield f"__PROGRESS__:{json.dumps(progress_info, ensure_ascii=False)}\n"
                
                if skill_result.success:
                    # 格式化技能结果
                    result_text = self._format_skill_result(skill_result)
                    yield result_text
                    return
                else:
                    # 技能执行失败，回退到工具调用
                    error_info = {
                        "type": "debug",
                        "category": "orchestrator",
                        "message": f"技能执行失败: {skill_result.error}，回退到工具调用"
                    }
                    yield f"__DEBUG__:{json.dumps(error_info, ensure_ascii=False)}\n"
            except Exception as e:
                logger.error(f"技能执行失败: {e}", exc_info=True)
                error_info = {
                    "type": "debug",
                    "category": "orchestrator",
                    "message": f"技能执行异常: {str(e)}，回退到工具调用"
                }
                yield f"__DEBUG__:{json.dumps(error_info, ensure_ascii=False)}\n"
        
        # 获取工具定义（LLM Function Calling 格式）
        tools = self.tool_registry.get_tools_for_llm()
        tool_names = [t.get("function", {}).get("name", "unknown") for t in tools] if tools else []
        debug_info = {
            "type": "debug",
            "category": "orchestrator",
            "message": "准备工具",
            "details": {"tool_count": len(tools), "tools": tool_names}
        }
        yield f"__DEBUG__:{json.dumps(debug_info, ensure_ascii=False)}\n"
        self.debug.log_orchestrator_step("准备工具", {"tool_count": len(tools), "tools": tool_names})
        
        # 智能模型选择：使用 chat 模型分析任务，决定使用哪个模型
        selected_model = await self._select_model(task)
        if selected_model != self.llm_service.model:
            self.llm_service.set_model(selected_model)
            self.debug.log_orchestrator_step("模型选择", {"selected_model": selected_model})
            debug_info = {
                "type": "debug",
                "category": "orchestrator",
                "message": "模型选择",
                "details": {"selected_model": selected_model}
            }
            yield f"__DEBUG__:{json.dumps(debug_info, ensure_ascii=False)}\n"
        
        # 发送模型信息（每次对话都显示）
        model_info = self.llm_service.get_model_info()
        model_data = {
            "provider": model_info.get("provider", "unknown"),
            "model": model_info.get("normalized_name", self.llm_service.model),
            "full_name": model_info.get("full_name", f"{model_info.get('provider', 'unknown')}-{self.llm_service.model}")
        }
        yield f"__MODEL__:{json.dumps(model_data, ensure_ascii=False)}\n"
        
        # 如果有工具可用，先完成工具调用（非流式），然后流式返回最终结果
        if tools:
            try:
                # 使用工具调用获取完整响应（带调试信息）
                full_response = ""
                async for chunk in self._chat_with_tools_stream(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    tools=tools
                ):
                    # 检查是否是调试信息、工具调用信息或进度信息
                    if chunk.startswith("__DEBUG__:") or chunk.startswith("__TOOL__:") or chunk.startswith("__PROGRESS__:"):
                        # 这些消息只用于前端显示，不存入上下文
                        yield chunk
                    else:
                        # 内容块（存入上下文）
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
        
        # 保存消息到历史
        self.context_manager.add_message(session_id, MessageRole.USER, task)
        self.context_manager.add_message(session_id, MessageRole.ASSISTANT, full_response)
        self.debug.log_context_operation("保存消息", session_id, {"user": True, "assistant": True})
        
        debug_info = {
            "type": "debug",
            "category": "orchestrator",
            "message": "流式任务处理完成",
            "details": {"response_length": len(full_response)}
        }
        yield f"__DEBUG__:{json.dumps(debug_info, ensure_ascii=False)}\n"
        self.debug.log_orchestrator_step("流式任务处理完成", {"response_length": len(full_response)})
    
    async def _chat_with_tools_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: Optional[list] = None
    ) -> AsyncIterator[str]:
        """
        带工具调用的聊天（流式版本，包含调试信息）
        
        Args:
            system_prompt: 系统提示
            user_prompt: 用户提示
            tools: 工具定义列表
            
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
                yield f"__DEBUG__:{json.dumps(debug_info, ensure_ascii=False)}\n"
                self.debug.log_orchestrator_step(f"工具调用循环第 {iteration} 轮", {})
                
                try:
                    # 调用 LLM（使用 messages 而不是 system_prompt/user_prompt）
                    response = await self.llm_service.chat(messages=messages, tools=tools)
                except Exception as e:
                    error_str = str(e)
                    # 检查是否是超时错误
                    if "timeout" in error_str.lower() or "timed out" in error_str.lower():
                        logger.error(f"LLM 调用超时: {str(e)}", exc_info=True)
                        # 如果是超时，尝试清理消息历史（保留最近的几轮）
                        if len(messages) > 10:
                            logger.warning(f"消息历史过长（{len(messages)} 条），清理旧消息")
                            # 保留系统消息、最后 3 轮对话（assistant + tool + user）
                            new_messages = []
                            # 保留系统消息
                            for msg in messages:
                                if msg.get("role") == "system":
                                    new_messages.append(msg)
                            # 保留最后 9 条消息（3 轮对话）
                            new_messages.extend(messages[-9:])
                            messages = new_messages
                            logger.info(f"消息历史已清理，剩余 {len(messages)} 条消息")
                            # 重试一次
                            try:
                                response = await self.llm_service.chat(messages=messages, tools=tools)
                            except Exception as retry_e:
                                logger.error(f"重试后仍然失败: {str(retry_e)}", exc_info=True)
                                yield f"抱歉，处理您的请求时出现超时错误。请尝试简化请求或稍后重试。错误详情：{str(retry_e)}"
                                return
                        else:
                            yield f"抱歉，处理您的请求时出现超时错误。请尝试简化请求或稍后重试。错误详情：{str(e)}"
                            return
                    else:
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
                    yield f"__DEBUG__:{json.dumps(debug_info, ensure_ascii=False)}\n"
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
                        yield f"__DEBUG__:{json.dumps(debug_info, ensure_ascii=False)}\n"
                        self.debug.log_orchestrator_step("执行工具", {"name": tool_name, "args": tool_args_str})
                        
                        # 解析参数（带容错处理）
                        def repair_json(json_str: str) -> str:
                            """尝试修复常见的 JSON 错误"""
                            # 1. 处理未转义的换行符
                            json_str = json_str.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                            
                            # 2. 处理未转义的双引号（在字符串值中）
                            # 查找字符串值中的未转义引号
                            import re
                            # 匹配 "key": "value" 中的 value 部分
                            def fix_string_value(match):
                                key = match.group(1)
                                value_start = match.group(2)  # 开头的引号
                                value_content = match.group(3)  # 内容
                                
                                # 转义内容中的引号和反斜杠
                                fixed_content = value_content.replace('\\', '\\\\').replace('"', '\\"')
                                return f'"{key}": {value_start}{fixed_content}"'
                            
                            # 尝试修复字符串值中的未转义引号
                            # 匹配 "key": "value" 格式，其中 value 可能包含未转义的引号
                            pattern = r'"([^"]+)":\s*"([^"]*)"'
                            # 更复杂的模式：匹配可能包含未转义引号的字符串值
                            # 先尝试简单的修复：转义字符串中的反斜杠和引号
                            
                            return json_str
                        
                        def fix_json_control_characters(json_str: str) -> str:
                            """修复 JSON 字符串值中的控制字符（参考 browser-use 的实现）"""
                            result = []
                            i = 0
                            in_string = False
                            escaped = False
                            
                            while i < len(json_str):
                                char = json_str[i]
                                
                                if not in_string:
                                    # 在字符串外
                                    if char == '"':
                                        in_string = True
                                    result.append(char)
                                else:
                                    # 在字符串内
                                    if escaped:
                                        # 前一个字符是反斜杠，当前字符已转义
                                        result.append(char)
                                        escaped = False
                                    elif char == '\\':
                                        # 这是转义字符
                                        result.append(char)
                                        escaped = True
                                    elif char == '"':
                                        # 字符串结束
                                        result.append(char)
                                        in_string = False
                                    elif char == '\n':
                                        # 未转义的换行符
                                        result.append('\\n')
                                    elif char == '\r':
                                        # 未转义的回车符
                                        result.append('\\r')
                                    elif char == '\t':
                                        # 未转义的制表符
                                        result.append('\\t')
                                    elif ord(char) < 32:
                                        # 其他控制字符
                                        result.append(f'\\u{ord(char):04x}')
                                    else:
                                        # 普通字符
                                        result.append(char)
                                
                                i += 1
                            
                            return ''.join(result)
                        
                        def try_parse_json(json_str: str) -> Tuple[Optional[dict], Optional[str]]:
                            """尝试解析 JSON，如果失败则尝试修复"""
                            # 第一次尝试：直接解析
                            try:
                                return json.loads(json_str), None
                            except json.JSONDecodeError as e:
                                error_msg = str(e)
                                
                                # 第二次尝试：修复控制字符
                                try:
                                    repaired = fix_json_control_characters(json_str)
                                    return json.loads(repaired), "修复了控制字符"
                                except json.JSONDecodeError:
                                    pass
                                
                                # 第三次尝试：对于 execute_code，使用正则表达式直接提取参数
                                if tool_name == "execute_code":
                                    result = {}
                                    
                                    # 提取 language（相对简单）
                                    language_match = re.search(r'"language"\s*:\s*"([^"]+)"', json_str)
                                    if language_match:
                                        result['language'] = language_match.group(1)
                                    else:
                                        result['language'] = 'python'  # 默认值
                                    
                                    # 提取 code（更复杂，因为可能包含未转义的引号和换行符）
                                    # 尝试多种模式
                                    code_patterns = [
                                        r'"code"\s*:\s*"((?:[^"\\]|\\.)*)"',  # 标准 JSON 字符串
                                        r'"code"\s*:\s*"(.+?)(?:"\s*[,}])',  # 未终止的字符串，查找下一个引号
                                        r'"code"\s*:\s*"(.+)"',  # 最宽松的匹配
                                    ]
                                    
                                    code_value = None
                                    for pattern in code_patterns:
                                        code_match = re.search(pattern, json_str, re.DOTALL)
                                        if code_match:
                                            code_value = code_match.group(1)
                                            break
                                    
                                    # 如果还是找不到，尝试从 "code": 开始到字符串结束
                                    if not code_value:
                                        code_start = json_str.find('"code"')
                                        if code_start >= 0:
                                            # 找到 "code": " 的位置
                                            value_start = json_str.find('"', code_start + 6)  # 跳过 "code"
                                            if value_start >= 0:
                                                value_start += 1  # 跳过开头的引号
                                                # 尝试找到结束引号（可能不存在）
                                                value_end = json_str.find('"', value_start)
                                                if value_end < 0:
                                                    # 没有结束引号，取到字符串末尾
                                                    value_end = len(json_str)
                                                code_value = json_str[value_start:value_end]
                                    
                                    if code_value:
                                        # 处理转义序列（反转义）
                                        code_value = (code_value
                                                    .replace('\\n', '\n')
                                                    .replace('\\r', '\r')
                                                    .replace('\\t', '\t')
                                                    .replace('\\"', '"')
                                                    .replace('\\\\', '\\'))
                                        result['code'] = code_value
                                        
                                        if result:
                                            return result, "使用容错解析提取参数（execute_code）"
                                
                                return None, f"JSON 解析失败: {error_msg}"
                        
                        tool_args, parse_warning = try_parse_json(tool_args_str)
                        if tool_args is None:
                            logger.error(
                                f"工具参数 JSON 解析失败: {tool_name}, "
                                f"错误: {parse_warning}, "
                                f"参数长度: {len(tool_args_str)}, "
                                f"前500字符: {repr(tool_args_str[:500])}"
                            )
                            # JSON 解析失败时，返回错误而不是使用空字典
                            tool_result = ToolResult(
                                success=False,
                                error=f"工具参数 JSON 解析失败: {parse_warning}。请检查参数格式是否正确。"
                            )
                            tool_info = {
                                "type": "tool",
                                "name": tool_name,
                                "args": {},
                                "success": False,
                                "error": tool_result.error
                            }
                            yield f"__TOOL__:{json.dumps(tool_info, ensure_ascii=False)}\n"
                            
                            # 重要：即使失败也要添加 tool message，确保每个 tool_call 都有对应的 tool message
                            tool_result_content = json.dumps({
                                "error": tool_result.error,
                                "success": False,
                                "note": "工具参数 JSON 解析失败，请检查参数格式是否正确。"
                            }, ensure_ascii=False)
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
                                    "success": False,
                                    "error": tool_result.error
                                }
                            }
                            yield f"__DEBUG__:{json.dumps(debug_info, ensure_ascii=False)}\n"
                            self.debug.log_orchestrator_step("工具执行完成", {
                                "name": tool_name,
                                "success": False,
                                "error": tool_result.error
                            })
                            continue
                        
                        if parse_warning:
                            logger.warning(f"工具参数解析使用了容错处理: {tool_name}, {parse_warning}")
                        
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
                                
                                # 定期检查进度并发送（包含心跳机制）
                                last_heartbeat_time = time.time()
                                heartbeat_interval = 10  # 每10秒发送一次心跳
                                
                                while not tool_future.done():
                                    try:
                                        # 检查进度队列
                                        has_progress = False
                                        while not progress_queue.empty():
                                            progress_msg = progress_queue.get_nowait()
                                            progress_info = {
                                                "type": "progress",
                                                "category": "tool",
                                                "tool_name": tool_name,
                                                "message": progress_msg
                                            }
                                            yield f"__PROGRESS__:{json.dumps(progress_info, ensure_ascii=False)}\n"
                                            has_progress = True
                                            last_heartbeat_time = time.time()  # 有进度消息时重置心跳时间
                                        
                                        # 如果没有进度消息且超过心跳间隔，发送心跳消息
                                        current_time = time.time()
                                        if not has_progress and (current_time - last_heartbeat_time) >= heartbeat_interval:
                                            heartbeat_info = {
                                                "type": "progress",
                                                "category": "tool",
                                                "tool_name": tool_name,
                                                "message": "正在处理中，请稍候..."
                                            }
                                            yield f"__PROGRESS__:{json.dumps(heartbeat_info, ensure_ascii=False)}\n"
                                            last_heartbeat_time = current_time
                                        
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
                            # 重要：即使需要确认也要添加 tool message，确保每个 tool_call 都有对应的 tool message
                            tool_result_content = json.dumps({
                                "error": "需要用户确认",
                                "requires_confirmation": True,
                                "success": False,
                                "note": "工具执行需要用户确认，请等待用户响应。"
                            }, ensure_ascii=False)
                            tool_results.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tool_name,
                                "content": tool_result_content
                            })
                            
                            debug_info = {
                                "type": "debug",
                                "category": "orchestrator",
                                "message": "工具执行完成（需要确认）",
                                "details": {
                                    "name": tool_name,
                                    "success": False,
                                    "requires_confirmation": True
                                }
                            }
                            yield f"__DEBUG__:{json.dumps(debug_info, ensure_ascii=False)}\n"
                            self.debug.log_orchestrator_step("工具执行完成（需要确认）", {
                                "name": tool_name,
                                "success": False,
                                "requires_confirmation": True
                            })
                            continue
                        
                        # 发送工具调用信息
                        # 使用安全的 JSON 序列化，清理不可序列化的对象
                        def safe_serialize_tool_result(obj):
                            """安全序列化工具结果，清理不可序列化的对象"""
                            if obj is None:
                                return None
                            if isinstance(obj, (str, int, float, bool)):
                                return obj
                            if isinstance(obj, dict):
                                cleaned = {}
                                for k, v in obj.items():
                                    try:
                                        # 尝试序列化值
                                        json.dumps(v, ensure_ascii=False)
                                        cleaned[k] = safe_serialize_tool_result(v)
                                    except (TypeError, ValueError):
                                        # 不可序列化，转换为字符串描述
                                        cleaned[k] = f"[{type(v).__name__}对象]"
                                return cleaned
                            if isinstance(obj, list):
                                cleaned = []
                                for item in obj:
                                    try:
                                        json.dumps(item, ensure_ascii=False)
                                        cleaned.append(safe_serialize_tool_result(item))
                                    except (TypeError, ValueError):
                                        cleaned.append(f"[{type(item).__name__}对象]")
                                return cleaned
                            # 其他类型，尝试转换为字符串
                            return str(obj)
                        
                        tool_info = {
                            "type": "tool",
                            "name": tool_name,
                            "args": tool_args,
                            "success": tool_result.success,
                            "result": safe_serialize_tool_result(tool_result.data) if tool_result.success else None,
                            "error": tool_result.error if not tool_result.success else None
                        }
                        yield f"__TOOL__:{json.dumps(tool_info, ensure_ascii=False)}\n"
                        
                        # 记录详细的执行结果
                        if not tool_result.success:
                            debug_info = {
                                "type": "debug",
                                "category": "orchestrator",
                                "message": "工具执行失败",
                                "details": {"name": tool_name, "error": tool_result.error}
                            }
                            yield f"__DEBUG__:{json.dumps(debug_info, ensure_ascii=False)}\n"
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
                            try:
                                with open('/System/Volumes/Data/justin/dev/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                                    json_module.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"orchestrator.py:safe_json_dumps","message":"JSON序列化开始","data":{"obj_type":type(obj).__name__,"is_dict":isinstance(obj,dict)},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                                    f.write('\n')
                            except: pass
                            # #endregion
                            try:
                                result = json.dumps(obj, ensure_ascii=False, **kwargs)
                                # #region agent log
                                try:
                                    with open('/System/Volumes/Data/justin/dev/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                                        json_module.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"orchestrator.py:safe_json_dumps","message":"JSON序列化成功","data":{"result_len":len(result)},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                                        f.write('\n')
                                except: pass
                                # #endregion
                                return result
                            except (UnicodeEncodeError, TypeError, UnicodeDecodeError) as e:
                                # #region agent log
                                try:
                                    with open('/System/Volumes/Data/justin/dev/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
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
                                                    with open('/System/Volumes/Data/justin/dev/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
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
                                                with open('/System/Volumes/Data/justin/dev/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
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
                            # 对于失败的工具，明确传递错误信息，避免 LLM 创建模拟数据
                            tool_result_content = safe_json_dumps({
                                "error": tool_result.error,
                                "success": False,
                                "note": "工具执行失败，请勿创建模拟或虚假数据。如果任务需要此工具，请先修复工具问题。"
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
                        yield f"__DEBUG__:{json.dumps(debug_info, ensure_ascii=False)}\n"
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
                    
                    # 验证：确保每个 tool_call 都有对应的 tool message
                    if len(tool_results) != len(response.tool_calls):
                        logger.error(
                            f"工具调用数量不匹配: tool_calls={len(response.tool_calls)}, "
                            f"tool_results={len(tool_results)}"
                        )
                        # 为缺失的 tool_call 添加错误消息
                        tool_call_ids = {tc.id for tc in response.tool_calls}
                        tool_result_ids = {tr.get("tool_call_id") for tr in tool_results}
                        missing_ids = tool_call_ids - tool_result_ids
                        for missing_id in missing_ids:
                            # 找到对应的 tool_call
                            missing_tool_call = next(tc for tc in response.tool_calls if tc.id == missing_id)
                            tool_results.append({
                                "role": "tool",
                                "tool_call_id": missing_id,
                                "name": missing_tool_call.function.name,
                                "content": json.dumps({
                                    "error": "工具执行过程中出现错误，未生成结果",
                                    "success": False
                                }, ensure_ascii=False)
                            })
                    
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
            yield f"__DEBUG__:{json.dumps(debug_info, ensure_ascii=False)}\n"
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
                    error_msg = f"抱歉，处理您的请求时出现错误：{str(e)}"
                    yield error_msg
                    return
                
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
                                yield response
                                return
                        except Exception as e:
                            logger.error(f"自动代码执行失败: {str(e)}", exc_info=True)
                            # 执行失败，返回原始回复
                            yield response
                            return
                    else:
                        # 未启用自动代码执行，直接返回
                        yield response
                        return
                
                # 检查是否有工具调用
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    self.debug.log_orchestrator_step("检测到工具调用", {"count": len(response.tool_calls)})
                    
                    # 执行所有工具调用
                    tool_results = []
                    for tool_call in response.tool_calls:
                        tool_name = tool_call.function.name
                    tool_args_str = tool_call.function.arguments
                    
                    self.debug.log_orchestrator_step("执行工具", {"name": tool_name, "args": tool_args_str[:200] + "..." if len(tool_args_str) > 200 else tool_args_str})
                    
                    # 解析参数
                    try:
                        tool_args = json.loads(tool_args_str)
                    except json.JSONDecodeError as e:
                        logger.error(
                            f"工具参数 JSON 解析失败: {tool_name}, "
                            f"错误: {str(e)}, "
                            f"参数长度: {len(tool_args_str)}, "
                            f"前500字符: {repr(tool_args_str[:500])}"
                        )
                        # JSON 解析失败时，返回错误而不是使用空字典
                        tool_result = ToolResult(
                            success=False,
                            error=f"工具参数 JSON 解析失败: {str(e)}。请检查参数格式是否正确。"
                        )
                        tool_info = {
                            "type": "tool",
                            "name": tool_name,
                            "args": {},
                            "success": False,
                            "error": tool_result.error
                        }
                        yield f"__TOOL__:{json.dumps(tool_info, ensure_ascii=False)}\n"
                        
                        # 重要：即使失败也要添加 tool message，确保每个 tool_call 都有对应的 tool message
                        tool_result_content = json.dumps({
                            "error": tool_result.error,
                            "success": False,
                            "note": "工具参数 JSON 解析失败，请检查参数格式是否正确。"
                        }, ensure_ascii=False)
                        tool_results.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": tool_result_content
                        })
                        
                        self.debug.log_orchestrator_step("工具执行完成", {
                            "name": tool_name,
                            "success": False,
                            "error": tool_result.error
                        })
                        continue
                    
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
                                
                                # 定期检查进度并发送（包含心跳机制）
                                last_heartbeat_time = time.time()
                                heartbeat_interval = 10  # 每10秒发送一次心跳
                                
                                while not tool_future.done():
                                    try:
                                        # 检查进度队列并发送所有进度消息
                                        has_progress = False
                                        while not progress_queue.empty():
                                            try:
                                                progress_msg = progress_queue.get_nowait()
                                                progress_info = {
                                                    "type": "progress",
                                                    "category": "tool",
                                                    "tool_name": tool_name,
                                                    "message": progress_msg
                                                }
                                                yield f"__PROGRESS__:{json.dumps(progress_info, ensure_ascii=False)}\n"
                                                has_progress = True
                                                last_heartbeat_time = time.time()  # 有进度消息时重置心跳时间
                                            except queue.Empty:
                                                break
                                        
                                        # 如果没有进度消息且超过心跳间隔，发送心跳消息
                                        current_time = time.time()
                                        if not has_progress and (current_time - last_heartbeat_time) >= heartbeat_interval:
                                            heartbeat_info = {
                                                "type": "progress",
                                                "category": "tool",
                                                "tool_name": tool_name,
                                                "message": "正在处理中，请稍候..."
                                            }
                                            yield f"__PROGRESS__:{json.dumps(heartbeat_info, ensure_ascii=False)}\n"
                                            last_heartbeat_time = current_time
                                        
                                        # 等待一小段时间
                                        if has_progress:
                                            await asyncio.sleep(0.1)  # 有进度时快速检查
                                        else:
                                            await asyncio.sleep(1)  # 无进度时正常检查
                                    except Exception as e:
                                        logger.warning(f"进度检查错误: {e}")
                                        await asyncio.sleep(1)
                                
                                # 发送剩余的进度消息
                                while not progress_queue.empty():
                                    try:
                                        progress_msg = progress_queue.get_nowait()
                                        progress_info = {
                                            "type": "progress",
                                            "category": "tool",
                                            "tool_name": tool_name,
                                            "message": progress_msg
                                        }
                                        yield f"__PROGRESS__:{json.dumps(progress_info, ensure_ascii=False)}\n"
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
                    
                    # 验证：确保每个 tool_call 都有对应的 tool message
                    if len(tool_results) != len(response.tool_calls):
                        logger.error(
                            f"工具调用数量不匹配: tool_calls={len(response.tool_calls)}, "
                            f"tool_results={len(tool_results)}"
                        )
                        # 为缺失的 tool_call 添加错误消息
                        tool_call_ids = {tc.id for tc in response.tool_calls}
                        tool_result_ids = {tr.get("tool_call_id") for tr in tool_results}
                        missing_ids = tool_call_ids - tool_result_ids
                        for missing_id in missing_ids:
                            # 找到对应的 tool_call
                            missing_tool_call = next(tc for tc in response.tool_calls if tc.id == missing_id)
                            tool_results.append({
                                "role": "tool",
                                "tool_call_id": missing_id,
                                "name": missing_tool_call.function.name,
                                "content": json.dumps({
                                    "error": "工具执行过程中出现错误，未生成结果",
                                    "success": False
                                }, ensure_ascii=False)
                            })
                    
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
            self.debug.log_orchestrator_step("达到最大工具调用迭代次数", {"max_iterations": max_iterations})
            yield "抱歉，工具调用未能成功获取信息。"
            return
        except Exception as e:
            logger.error(f"_chat_with_tools_stream 执行失败: {str(e)}", exc_info=True)
            yield f"抱歉，处理您的请求时出现错误：{str(e)}"
            return
    
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
