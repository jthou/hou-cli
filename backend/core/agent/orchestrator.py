"""统一智能编排器"""
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
from backend.core.agent.planning.task_decomposer import TaskDecomposer
from backend.core.agent.planning.execution_planner import ExecutionPlanner
from backend.core.agent.planning.model_switcher import ModelSwitcher
from backend.core.agent.planning.adaptive_strategy import AdaptiveStrategy, ExecutionMetrics
from backend.core.agent.planning.autonomous_executor import AutonomousExecutor
from backend.api.stream_sender import SSEFormatter, LongTaskMonitor, StreamMessageBuilder
from backend.core.agent.task_manager import task_manager


class UnifiedOrchestrator:
    """统一智能编排器，使用推理模型智能选择和协调agents及tools"""
    
    def __init__(self):
        self.llm_service = LLMService()
        self.context_manager = FullContextManager()
        self.tool_registry = ToolRegistry()
        self.debug = DebugOutput()  # 调试输出
        
        # 初始化技能系统
        self.skill_registry = SkillRegistry()
        self.skill_executor = SkillExecutor(self.tool_registry, self.llm_service)
        
        # 代码执行相关组件
        self.auto_code_executor = None
        self.auto_execute_code = True  # 配置项：是否自动执行代码块
        
        # 规划文件管理
        import os
        planning_enabled = os.getenv("ENABLE_PLANNING", "true").lower() == "true"
        self.enable_planning = planning_enabled
        
        # 对话评估功能
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
            # 初始化对话评估器
            self.evaluator = ConversationEvaluator(llm_service=self.llm_service)
            
            # 初始化自主执行器
            autonomous_execution_enabled = (
                os.getenv("ENABLE_AUTONOMOUS_EXECUTION", "false").lower() == "true"
            )
            if autonomous_execution_enabled:
                self.autonomous_executor = AutonomousExecutor(
                    llm_service=self.llm_service,
                    tool_registry=self.tool_registry,
                    planning_manager=self.planning_manager
                )
                logger.info("自主执行功能已启用（替代传统规划文件模式）")
            else:
                self.autonomous_executor = None
                logger.info("自主执行功能已禁用（使用传统规划文件模式）")
            
            # 初始化任务分解器和执行计划生成器
            task_decomposition_enabled = os.getenv("ENABLE_TASK_DECOMPOSITION", "false").lower() == "true"
            if task_decomposition_enabled:
                self.task_decomposer = TaskDecomposer(
                    llm_service=self.llm_service,
                    tool_registry=self.tool_registry,
                    complexity_analyzer=self.complexity_analyzer
                )
                self.execution_planner = ExecutionPlanner(llm_service=self.llm_service)
                logger.info("任务分解功能已启用")
            else:
                self.task_decomposer = None
                self.execution_planner = None
                logger.info("任务分解功能已禁用")
            
            # 定期清理旧文件
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
            
            # 即使规划功能禁用，如果任务分解启用，仍然初始化分解器
            task_decomposition_enabled = os.getenv("ENABLE_TASK_DECOMPOSITION", "false").lower() == "true"
            if task_decomposition_enabled:
                # 创建一个简单的复杂度分析器（不依赖规划功能）
                self.complexity_analyzer = TaskComplexityAnalyzer(
                    min_task_length=int(os.getenv("PLANNING_MIN_TASK_LENGTH", "20")),
                    complexity_threshold=float(os.getenv("PLANNING_COMPLEXITY_THRESHOLD", "0.3")),
                    llm_service=self.llm_service,
                    use_llm=os.getenv("PLANNING_USE_LLM", "false").lower() == "true"
                )
                self.task_decomposer = TaskDecomposer(
                    llm_service=self.llm_service,
                    tool_registry=self.tool_registry,
                    complexity_analyzer=self.complexity_analyzer
                )
                self.execution_planner = ExecutionPlanner(llm_service=self.llm_service)
                logger.info("任务分解功能已启用（规划功能已禁用）")
            else:
                self.task_decomposer = None
                self.execution_planner = None
        
        # 初始化动态模型切换器（始终启用）
        self.model_switcher = ModelSwitcher()
        logger.info("动态模型切换功能已启用")
        
        # 初始化自适应策略管理器（可选）
        adaptive_strategy_enabled = os.getenv("ENABLE_ADAPTIVE_STRATEGY", "false").lower() == "true"
        if adaptive_strategy_enabled:
            self.adaptive_strategy = AdaptiveStrategy(model_switcher=self.model_switcher)
            logger.info("自适应策略功能已启用")
        else:
            self.adaptive_strategy = None
            logger.info("自适应策略功能已禁用")
        
        # 注册工具和技能
        self._register_tools()
        self._register_skills()
        
        # 初始化自动代码执行器
        self._init_auto_code_executor()
        
        # 统一的技能匹配服务
        self.skill_matcher = SkillMatcher(self.skill_registry)
    
    async def process(self, task: str, context: Optional[Dict] = None) -> str:
        """智能处理任务，使用LLM决定如何协调agents和tools"""
        # 优先检查是否有匹配的技能
        matched_skill = None
        if self.skill_registry is not None:
            matched_skill = await self.skill_matcher.match(task)
        
        if matched_skill:
            logger.info(f"检测到匹配的技能: {matched_skill.name}，优先使用技能执行")
            self.debug.log_orchestrator_step("技能匹配", {"skill": matched_skill.name})
            
            # 提取技能参数
            skill_params = self._extract_skill_parameters(task, matched_skill)
            
            # 执行技能
            try:
                # 设置上下文
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
                    # 技能执行失败，继续使用LLM处理
            except Exception as e:
                logger.error(f"技能 {matched_skill.name} 执行异常: {str(e)}", exc_info=True)
                # 技能执行异常，继续使用LLM处理
        
        # 如果没有匹配到技能或技能执行失败，使用LLM智能编排
        return await self._intelligent_orchestration(task, context)
    
    async def _intelligent_orchestration(self, task: str, context: Optional[Dict] = None) -> str:
        """使用LLM智能编排agents和tools"""
        # 获取会话ID
        session_id = context.get("session_id") if context else None
        if not session_id:
            session_id = self.context_manager.create_session()
        
        # 获取历史消息
        history = self.context_manager.get_messages_for_llm(
            session_id,
            max_messages=None,
            max_tokens=None
        )
        
        # 获取所有可用的agents和tools
        available_agents = ["chat_agent", "code_agent", "filesystem_agent", "pdf_agent", "writing_blog_agent"]
        available_tools = [tool.name for tool in self.tool_registry.get_all_tools()]
        
        # 构建智能编排的系统提示
        system_prompt = f"""你是智能编排助手，根据用户的需求智能选择和协调agents和tools来完成任务。

可用agents: {', '.join(available_agents)}
可用tools: {', '.join(available_tools)}

编排原则：
1. 分析用户需求的本质和目标
2. 选择最适合的agent或tool组合
3. 如果需要多个步骤，规划执行序列
4. 优先选择能直接解决问题的agent或tool
5. 如果需要复杂操作，考虑组合使用多个工具

请按以下JSON格式返回你的编排计划：
{{
    "selected_component": "选择的组件类型 (agent/tool)",
    "component_name": "组件名称",
    "action": "具体操作",
    "parameters": {{}},
    "reason": "选择此组件的理由"
}}
"""
        
        # 构建用户提示
        if history:
            history_text = "\n".join([
                f"{msg['role'].upper()}: {msg['content']}" 
                for msg in history[-5:]  # 只取最近5条消息
            ])
            user_prompt = f"历史对话:\n{history_text}\n\n当前任务：{task}"
        else:
            user_prompt = f"任务：{task}"
        
        try:
            # 使用LLM决定编排策略
            orchestration_plan = await self.llm_service.chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            # 解析编排计划
            import json
            plan = json.loads(orchestration_plan)
            
            component_type = plan.get("selected_component")
            component_name = plan.get("component_name")
            action = plan.get("action")
            params = plan.get("parameters", {})
            
            if component_type == "agent":
                return await self._execute_agent(component_name, task, params, session_id)
            elif component_type == "tool":
                return await self._execute_tool(component_name, params, session_id)
            else:
                # 如果LLM没有给出明确的编排方案，使用默认处理
                return await self._default_processing(task, session_id)
        
        except Exception as e:
            logger.warning(f"智能编排失败，使用默认处理: {e}")
            return await self._default_processing(task, session_id)
    
    async def _execute_agent(self, agent_name: str, task: str, params: Dict, session_id: str) -> str:
        """执行指定的agent"""
        # 这里可以根据agent名称动态调用相应的agent
        # 暂时使用通用处理方式
        logger.info(f"执行agent: {agent_name}，任务: {task}")
        
        # 根据agent类型执行不同的逻辑
        if agent_name == "writing_blog_agent":
            from backend.core.agent.agents.writing_blog_agent import BlogWritingAgent
            agent = BlogWritingAgent(self.llm_service, self.tool_registry)
            # 使用参数执行博客写作
            result = await agent.execute(params)
            return result
        elif agent_name == "code_agent":
            # 代码agent处理逻辑
            pass
        elif agent_name == "filesystem_agent":
            # 文件系统agent处理逻辑
            pass
        elif agent_name == "pdf_agent":
            # PDF agent处理逻辑
            pass
        elif agent_name == "chat_agent":
            # 聊天agent处理逻辑
            pass
        
        # 默认处理
        return await self._default_processing(task, session_id)
    
    async def _execute_tool(self, tool_name: str, params: Dict, session_id: str) -> str:
        """执行指定的tool"""
        # 从工具注册表获取工具并执行
        tool = self.tool_registry.get_tool(tool_name)
        if tool:
            try:
                result = await tool.execute(**params)
                if result.success:
                    return str(result.data) if result.data else result.message
                else:
                    return f"工具执行失败: {result.error}"
            except Exception as e:
                logger.error(f"工具 {tool_name} 执行失败: {e}")
                return f"工具执行出错: {str(e)}"
        else:
            return f"未找到工具: {tool_name}"
    
    async def _default_processing(self, task: str, session_id: str) -> str:
        """默认处理逻辑"""
        # 获取历史消息
        history = self.context_manager.get_messages_for_llm(
            session_id,
            max_messages=None,
            max_tokens=None
        )
        
        # 构建系统提示
        system_prompt = "你是一个智能助手，能够帮助用户解决各种问题。"
        
        # 构建用户提示
        if history:
            history_text = "\n".join([
                f"{msg['role'].upper()}: {msg['content']}" 
                for msg in history[-5:]
            ])
            user_prompt = f"{history_text}\n\n新任务：{task}"
        else:
            user_prompt = task
        
        # 使用LLM生成回复
        response = await self.llm_service.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        # 保存消息到历史
        self.context_manager.add_message(session_id, MessageRole.USER, task)
        self.context_manager.add_message(session_id, MessageRole.ASSISTANT, response)
        
        return response
    
    async def stream_process(self, task: str, context: Optional[Dict] = None) -> AsyncIterator[str]:
        """流式处理任务"""
        # 发送调试信息：开始技能匹配
        debug_info = {
            "type": "debug",
            "category": "orchestrator",
            "message": "开始技能匹配",
            "details": {"task": task[:50] + "..." if len(task) > 50 else task}
        }
        yield StreamMessageBuilder.build_debug(debug_info)
        
        # 优先检查是否有匹配的技能
        matched_skill = None
        if self.skill_registry is not None:
            matched_skill = await self.skill_matcher.match(task)
        
        if matched_skill:
            logger.info(f"检测到匹配的技能: {matched_skill.name}，优先使用技能执行")
            debug_info = {
                "type": "debug",
                "category": "orchestrator",
                "message": "技能匹配",
                "details": {"skill": matched_skill.name}
            }
            yield StreamMessageBuilder.build_debug(debug_info)
            
            # 提取技能参数
            skill_params = self._extract_skill_parameters(task, matched_skill)
            
            # 执行技能
            try:
                # 设置上下文
                session_id = context.get("session_id") if context else None
                if not session_id:
                    session_id = self.context_manager.create_session()
                
                # 创建进度回调
                def progress_callback(message: str):
                    progress_msg = {
                        "type": "progress",
                        "message": message,
                        "skill": matched_skill.name
                    }
                    yield StreamMessageBuilder.build_progress(progress_msg)
                
                skill_context = {
                    'tool_registry': self.tool_registry,
                    'llm_service': self.llm_service,
                    'context_manager': self.context_manager,
                    'session_id': session_id,
                    'progress_callback': progress_callback
                }
                
                skill_result = await matched_skill.execute(skill_params, skill_context)
                
                if skill_result.success:
                    logger.info(f"技能 {matched_skill.name} 执行成功")
                    result_text = self._format_skill_result(matched_skill, skill_result)
                    for char in result_text:
                        yield char
                else:
                    logger.warning(f"技能 {matched_skill.name} 执行失败: {skill_result.error}")
                    error_msg = f"技能执行失败: {skill_result.error}，将使用LLM处理\n\n"
                    for char in error_msg:
                        yield char
            except Exception as e:
                logger.error(f"技能 {matched_skill.name} 执行异常: {str(e)}", exc_info=True)
                error_msg = f"技能执行异常: {str(e)}，将使用LLM处理\n\n"
                for char in error_msg:
                    yield char
        
        # 如果没有匹配到技能或技能执行失败，使用流式智能编排
        async for chunk in self._stream_intelligent_orchestration(task, context):
            yield chunk
    
    async def _stream_intelligent_orchestration(self, task: str, context: Optional[Dict] = None) -> AsyncIterator[str]:
        """流式智能编排agents和tools"""
        # 获取会话ID
        session_id = context.get("session_id") if context else None
        if not session_id:
            session_id = self.context_manager.create_session()
        
        # 获取历史消息
        history = self.context_manager.get_messages_for_llm(
            session_id,
            max_messages=None,
            max_tokens=None
        )
        
        # 获取所有可用的agents和tools
        available_agents = ["chat_agent", "code_agent", "filesystem_agent", "pdf_agent", "writing_blog_agent"]
        available_tools = [tool.name for tool in self.tool_registry._tools.values()]
        
        # 构建智能编排的系统提示
        system_prompt = f"""你是智能编排助手，根据用户的需求智能选择和协调agents和tools来完成任务。

可用agents: {', '.join(available_agents)}
可用tools: {', '.join(available_tools)}

编排原则：
1. 分析用户需求的本质和目标
2. 选择最适合的agent或tool组合
3. 如果需要多个步骤，规划执行序列
4. 优先选择能直接解决问题的agent或tool
5. 如果需要复杂操作，考虑组合使用多个工具

请按以下JSON格式返回你的编排计划：
{{
    "selected_component": "选择的组件类型 (agent/tool)",
    "component_name": "组件名称",
    "action": "具体操作",
    "parameters": {{}},
    "reason": "选择此组件的理由"
}}
"""
        
        # 构建用户提示
        if history:
            history_text = "\n".join([
                f"{msg['role'].upper()}: {msg['content']}" 
                for msg in history[-5:]
            ])
            user_prompt = f"历史对话:\n{history_text}\n\n当前任务：{task}"
        else:
            user_prompt = f"任务：{task}"
        
        try:
            # 使用LLM决定编排策略
            orchestration_plan = await self.llm_service.chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            # 解析编排计划
            import json
            plan = json.loads(orchestration_plan)
            
            component_type = plan.get("selected_component")
            component_name = plan.get("component_name")
            action = plan.get("action")
            params = plan.get("parameters", {})
            
            if component_type == "agent":
                async for chunk in self._stream_execute_agent(component_name, task, params, session_id):
                    yield chunk
            elif component_type == "tool":
                async for chunk in self._stream_execute_tool(component_name, params, session_id):
                    yield chunk
            else:
                # 如果LLM没有给出明确的编排方案，使用默认处理
                async for chunk in self._stream_default_processing(task, session_id):
                    yield chunk
        
        except Exception as e:
            logger.warning(f"智能编排失败，使用默认处理: {e}")
            async for chunk in self._stream_default_processing(task, session_id):
                yield chunk
    
    async def _stream_execute_agent(self, agent_name: str, task: str, params: Dict, session_id: str) -> AsyncIterator[str]:
        """流式执行指定的agent"""
        logger.info(f"流式执行agent: {agent_name}，任务: {task}")
        # 这里可以根据agent名称动态调用相应的agent
        # 暂时使用通用处理方式
        yield f"执行 {agent_name} 代理... "
        result = await self._execute_agent(agent_name, task, params, session_id)
        for char in result:
            yield char
    
    async def _stream_execute_tool(self, tool_name: str, params: Dict, session_id: str) -> AsyncIterator[str]:
        """流式执行指定的tool"""
        logger.info(f"流式执行tool: {tool_name}，参数: {params}")
        # 从工具注册表获取工具并执行
        tool = self.tool_registry.get_tool(tool_name)
        if tool:
            try:
                result = await tool.execute(**params)
                if result.success:
                    result_str = str(result.data) if result.data else result.message
                    for char in f"工具 {tool_name} 执行成功: ":
                        yield char
                    for char in result_str:
                        yield char
                else:
                    error_msg = f"工具执行失败: {result.error}"
                    for char in error_msg:
                        yield char
            except Exception as e:
                error_msg = f"工具 {tool_name} 执行失败: {e}"
                for char in error_msg:
                    yield char
        else:
            error_msg = f"未找到工具: {tool_name}"
            for char in error_msg:
                yield char
    
    async def _stream_default_processing(self, task: str, session_id: str) -> AsyncIterator[str]:
        """流式默认处理逻辑"""
        # 获取历史消息
        history = self.context_manager.get_messages_for_llm(
            session_id,
            max_messages=None,
            max_tokens=None
        )
        
        # 构建系统提示
        system_prompt = "你是一个智能助手，能够帮助用户解决各种问题。"
        
        # 构建用户提示
        if history:
            history_text = "\n".join([
                f"{msg['role'].upper()}: {msg['content']}" 
                for msg in history[-5:]
            ])
            user_prompt = f"{history_text}\n\n新任务：{task}"
        else:
            user_prompt = task
        
        # 使用LLM生成回复
        response = await self.llm_service.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        # 保存消息到历史
        self.context_manager.add_message(session_id, MessageRole.USER, task)
        self.context_manager.add_message(session_id, MessageRole.ASSISTANT, response)
        
        # 流式返回响应
        for char in response:
            yield char
    
    def _extract_skill_parameters(self, task: str, skill) -> Dict[str, Any]:
        """提取技能参数"""
        # 简单的参数提取逻辑，实际实现可能更复杂
        return {"input": task}
    
    def _format_skill_result(self, skill, result) -> str:
        """格式化技能执行结果"""
        if isinstance(result.output, dict):
            import json
            return json.dumps(result.output, ensure_ascii=False, indent=2)
        else:
            return str(result.output)
    
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
            
            # 健康检查：确保工具可用且 API 兼容
            is_available, health_error = BrowserTool.check_health()
            if not is_available:
                error_msg = f"Browser tool 健康检查失败: {health_error}. Browser tool will not be available."
                self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
                logger.warning(error_msg)
            else:
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
        
        # 注册细粒度浏览器操作工具（可选，根据配置决定是否启用）
        enable_fine_grained_browser_tools = os.getenv("BROWSER_TOOL_ENABLE_FINE_GRAINED_TOOLS", "false").lower() == "true"
        if enable_fine_grained_browser_tools:
            try:
                from backend.core.agent.tools.builtin.browser_action_tool import (
                    BrowserNavigateTool,
                    BrowserClickTool,
                    BrowserFillTool,
                    BrowserSearchTool,
                    BrowserExtractTool
                )
                
                # 注册细粒度浏览器工具
                fine_grained_tools = [
                    BrowserNavigateTool(),
                    BrowserClickTool(),
                    BrowserFillTool(),
                    BrowserSearchTool(),
                    BrowserExtractTool()
                ]
                
                for tool in fine_grained_tools:
                    self.tool_registry.register(tool)
                    logger.info(f"细粒度浏览器工具已注册: {tool.name}")
                
                self.debug.log_orchestrator_step("细粒度浏览器工具注册", {
                    "count": len(fine_grained_tools),
                    "tools": [tool.name for tool in fine_grained_tools]
                })
            except ImportError as e:
                error_msg = f"细粒度浏览器工具导入失败: {str(e)}. 细粒度浏览器工具将不可用."
                self.debug.log_orchestrator_step("细粒度浏览器工具注册失败", {"error": error_msg})
                logger.warning(error_msg)
            except Exception as e:
                error_msg = f"细粒度浏览器工具注册失败: {str(e)}. 细粒度浏览器工具将不可用."
                self.debug.log_orchestrator_step("细粒度浏览器工具注册失败", {"error": error_msg})
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
        
        # 注册视频下载工具（媒体处理）
        try:
            from backend.core.agent.tools.builtin.video_downloader_tool import VideoDownloaderTool
            video_downloader_tool = VideoDownloaderTool()
            self.tool_registry.register(video_downloader_tool)
            self.debug.log_orchestrator_step("注册工具", {"video_downloader_tool": "registered"})
            logger.info("Video downloader tool registered successfully")
        except ImportError as e:
            error_msg = f"Video downloader dependencies not installed: {str(e)}. Video downloader tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        except Exception as e:
            error_msg = f"Failed to register video downloader tool: {str(e)}. Video downloader tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        
        # 注册 Whisper 语音转文字工具（音频处理）
        try:
            from backend.core.agent.tools.builtin.whisper_tool import WhisperTool
            whisper_tool = WhisperTool()
            self.tool_registry.register(whisper_tool)
            self.debug.log_orchestrator_step("注册工具", {"whisper_tool": "registered"})
            logger.info("Whisper tool registered successfully")
        except ImportError as e:
            error_msg = f"Whisper dependencies not installed: {str(e)}. Whisper tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        except Exception as e:
            error_msg = f"Failed to register Whisper tool: {str(e)}. Whisper tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        
        # 注册 FFmpeg 工具（音视频处理）
        try:
            from backend.core.agent.tools.builtin.ffmpeg_tool import FFmpegTool
            ffmpeg_tool = FFmpegTool()
            self.tool_registry.register(ffmpeg_tool)
            self.debug.log_orchestrator_step("注册工具", {"ffmpeg_tool": "registered"})
            logger.info("FFmpeg tool registered successfully")
        except ImportError as e:
            error_msg = f"FFmpeg dependencies not installed: {str(e)}. FFmpeg tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        except Exception as e:
            error_msg = f"Failed to register FFmpeg tool: {str(e)}. FFmpeg tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        
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

    def _register_skills(self):
        """注册所有可用技能
        
        技能注册顺序优化原则：
        1. 通用技能放在前面
        2. 专业技能放在后面
        3. 按照技能的重要性和使用频率排序
        """
        try:
            # 导入所有技能类
            from backend.core.agent.skills.video_downloader.skill import VideoDownloaderSkill
            from backend.core.agent.skills.video_cut.skill import VideoCutSkill
            from backend.core.agent.skills.video_extract_srt.skill import VideoExtractSRTSkill
            from backend.core.agent.skills.blog_writing.skill import BlogWritingSkill
            
            # 创建技能实例
            skills_to_register = [
                (VideoDownloaderSkill(), "video_downloader"),
                (VideoCutSkill(), "video_cut"),
                (VideoExtractSRTSkill(), "video_extract_srt"),
                (BlogWritingSkill(), "blog_writing"),
            ]
            
            # 注册所有技能
            for skill, skill_name in skills_to_register:
                try:
                    self.skill_registry.register(skill)
                    logger.info(f"技能注册成功: {skill_name}")
                    self.debug.log_orchestrator_step("技能注册", {"skill": skill_name, "status": "success"})
                except Exception as e:
                    logger.error(f"技能注册失败: {skill_name}, 错误: {str(e)}")
                    self.debug.log_orchestrator_step("技能注册", {"skill": skill_name, "status": "failed", "error": str(e)})
        
        except ImportError as e:
            logger.warning(f"某些技能模块未安装，部分技能不可用: {str(e)}")
        except Exception as e:
            logger.error(f"注册技能时发生错误: {str(e)}")
            self.debug.log_orchestrator_step("技能注册", {"status": "failed", "error": str(e)})
    
    def _init_auto_code_executor(self):
        """初始化自动代码执行器"""
        try:
            from backend.infrastructure.execution import AutoCodeExecutor
            self.auto_code_executor = AutoCodeExecutor()
            logger.info("Auto code executor initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize auto code executor: {str(e)}")
            self.auto_code_executor = None


class SkillMatcher:
    """统一的技能匹配服务"""
    
    def __init__(self, skill_registry):
        self.skill_registry = skill_registry
        
    async def match(self, task: str) -> Optional[SkillResult]:
        """
        Use LLM to intelligently match the most suitable skill
        
        Args:
            task: User task description
            
        Returns:
            Matched skill or None
        """
        # 获取所有可用技能列表
        available_skills = list(self.skill_registry._skills.keys())
        
        if not available_skills:
            return None
        
        # 构建技能描述
        skills_description = "\n".join([
            f"- {skill_name}: {self.skill_registry._skills[skill_name].description}" 
            for skill_name in available_skills
        ])
        
        system_prompt = f"""You are an intelligent skill matching assistant. Based on the user's request, select the most suitable skill from the following available skills.

Available skills list:
{skills_description}

Selection principles:
1. Match based on semantic understanding of user needs, not just keyword matching
2. Select the skill that best fits the user's intent
3. Avoid selecting related skills if the user explicitly indicates they don't want a specific skill
4. Return the most relevant skill name, or return 'none' if no skill is appropriate

Please return strictly in the following JSON format:
{{
    "skill_name": "matched skill name or 'none'",
    "reason": "matching reason"
}}
"""
        
        user_prompt = f"用户需求：{task}"
        
        try:
            from backend.services.llm.llm_service import LLMService
            llm_service = LLMService()
            response = await llm_service.chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            import json
            result = json.loads(response)
            
            skill_name = result.get("skill_name", "none")
            if skill_name != "none" and skill_name in self.skill_registry._skills:
                return self.skill_registry._skills[skill_name]
            else:
                return None
        except Exception as e:
            logger.warning(f"技能匹配失败，回退到传统匹配: {e}")
            # 回退到传统技能匹配
            return await self.skill_registry.match(task)


        
    
    
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
        matched_skill = None
        if self.skill_registry is not None:
            matched_skill = await self.skill_registry.match(task)
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

【核心执行原则】：
1. **必须使用工具执行任务**：当用户要求执行操作（如下载、搜索、执行命令等）时，必须使用相应的工具来执行，不要只提供文字指导或操作步骤
2. **不要只提供指导**：如果任务可以通过工具完成，必须直接调用工具执行，而不是告诉用户如何操作
3. **工具调用优先级**：优先使用工具执行，只有在工具不可用时才提供替代方案
4. **禁止行为**：
   - ❌ 不要只提供操作步骤或指导（如"你可以使用 xxx 工具"）
   - ❌ 不要只列出命令而不执行
   - ❌ 不要告诉用户"使用 you-get 下载"而不实际调用工具
   - ✅ 必须直接调用工具执行任务
   - ✅ 基于工具执行结果给出回复

重要原则：
- 对于简单的命令执行任务（如显示文件、查看目录、执行脚本等），严格按照用户指令执行，不要添加额外的探索、检查或推理
- 用户要求执行什么命令，就执行什么命令，不要自作主张添加其他操作
- 例如：用户要求"显示 /home 下的所有文件"，直接执行 "ls /home"，不要去找 /dev、/Users 等其他路径
- 不要过度思考，不要添加用户没有要求的额外功能

【重要】工具选择规则（必须使用工具执行，不要只提供指导）：
1. **浏览器工具（browser）**：当用户要求"打开"、"访问"、"查看"网站时，必须使用 browser 工具
   - 例如："打开 www.google.com" → 必须调用 browser 工具
   - 例如："访问 www.example.com 并查看网页" → 必须调用 browser 工具
   - 例如："打开网站" → 必须调用 browser 工具
   - 如果用户提到具体的网站地址（如 www.google.com、example.com），优先使用 browser

2. **Google 搜索工具（google_search）**：当用户要求"搜索"、"查找"网络信息时，必须使用 google_search 工具
   - 例如："搜索 Python 教程" → 必须调用 google_search 工具
   - 例如："查找关于 AI 的最新信息" → 必须调用 google_search 工具
   - 不要只提供搜索建议，必须直接执行搜索

3. **视频下载工具（video_downloader）**：当用户要求下载视频时，必须使用 video_downloader 工具
   - 例如："下载这个视频 https://..." → 必须调用 video_downloader 工具
   - 例如："用 you-get 下载视频" → 必须调用 video_downloader 工具（工具会自动选择 you-get）
   - 例如："下载视频并提取音频" → 必须调用 video_downloader 工具，设置 extract_audio_only=true
   - 例如："下载视频并提取字幕" → 必须调用 video_downloader 工具，设置 subtitle_languages
   - **重要**：不要只告诉用户如何使用 you-get 或 yt-dlp，必须直接调用工具执行下载

4. **代码执行工具（execute_code）**：当用户要求执行命令或代码时，必须使用 execute_code 工具
   - 例如："执行 ls /home" → 必须调用 execute_code 工具
   - 例如："运行 Python 脚本" → 必须调用 execute_code 工具
   - 不要只提供命令，必须直接执行

5. **Whisper 语音转文字工具（whisper）**：当用户要求语音转文字、音频转字幕、生成字幕时，必须使用 whisper 工具
   - 例如："将这个音频文件转成字幕" → 必须调用 whisper 工具，设置 output_format='srt'
   - 例如："提取这个音频的文字" → 必须调用 whisper 工具
   - 例如："为这个视频生成字幕" → 必须调用 whisper 工具（需要先提取音频）
   - 例如："声音转文字"、"语音转字幕"、"音频转字幕" → 必须调用 whisper 工具
   - **重要**：不要只告诉用户如何使用 Whisper，必须直接调用工具执行

6. **FFmpeg 工具（ffmpeg）**：当用户要求处理音视频文件（提取音频、转换格式、剪切等）时，必须使用 ffmpeg 工具
   - 例如："从视频中提取音频" → 必须调用 ffmpeg 工具
   - 例如："转换视频格式" → 必须调用 ffmpeg 工具
   - 例如："剪切视频" → 必须调用 ffmpeg 工具
   - **重要**：不要只提供 FFmpeg 命令，必须直接调用工具执行

7. **天气工具（get_weather）**：当用户询问天气信息时，必须使用 get_weather 工具来获取实时天气数据。绝对不要编造或猜测天气信息。如果工具调用失败，请明确告诉用户工具调用失败，不要生成虚假的天气信息。

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
        
        # 智能模型选择：使用推理模型分析任务，决定使用哪个模型
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
                # 检查是否使用自主执行模式
                autonomous_execution_enabled = (
                    os.getenv("ENABLE_AUTONOMOUS_EXECUTION", "false").lower() == "true"
                )
                
                if autonomous_execution_enabled and self.autonomous_executor:
                    # 使用自主执行模式
                    try:
                        debug_info = {
                            "type": "debug",
                            "category": "autonomous_execution",
                            "message": "检测到复杂任务，使用自主执行模式",
                            "details": {}
                        }
                        yield StreamMessageBuilder.build_debug(debug_info)
                        logger.info("使用自主执行模式处理复杂任务")
                        
                        # 使用自主执行器执行任务
                        async for output in self.autonomous_executor.execute(
                            task=task,
                            context=context,
                            session_id=session_id
                        ):
                            yield output
                        
                        return  # 自主执行完成，直接返回
                    except Exception as e:
                        logger.error(f"自主执行失败: {str(e)}", exc_info=True)
                        debug_info = {
                            "type": "debug",
                            "category": "autonomous_execution",
                            "message": "自主执行失败，降级到传统模式",
                            "details": {"error": str(e)}
                        }
                        yield StreamMessageBuilder.build_debug(debug_info)
                
                # 传统规划文件模式
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
        
        # 4.5. 任务分解（阶段2：如果启用）
        execution_plan = None
        if self.task_decomposer and self.execution_planner:
            task_decomposition_enabled = os.getenv("ENABLE_TASK_DECOMPOSITION", "false").lower() == "true"
            if task_decomposition_enabled:
                try:
                    debug_info = {
                        "type": "debug",
                        "category": "task_decomposition",
                        "message": "开始任务分解",
                        "details": {}
                    }
                    yield StreamMessageBuilder.build_debug(debug_info)
                    
                    # 分解任务
                    subtasks = await self.task_decomposer.decompose_task(task, context)
                    logger.info(f"任务分解完成，共 {len(subtasks)} 个子任务")
                    
                    if len(subtasks) > 1:
                        # 验证子任务
                        is_valid, error_msg = self.task_decomposer.validate_subtasks(subtasks)
                        if not is_valid:
                            logger.warning(f"子任务验证失败: {error_msg}，继续使用原始任务")
                            subtasks = [subtasks[0]]  # 降级到第一个子任务
                        
                        # 创建执行计划
                        execution_plan = self.execution_planner.plan_execution(
                            subtasks=subtasks,
                            task_description=task
                        )
                        
                        debug_info = {
                            "type": "debug",
                            "category": "task_decomposition",
                            "message": "任务分解完成",
                            "details": {
                                "subtask_count": len(subtasks),
                                "parallel_groups": len(execution_plan.parallel_groups),
                                "estimated_time": execution_plan.estimated_total_time
                            }
                        }
                        yield StreamMessageBuilder.build_debug(debug_info)
                        
                        # 更新 system_prompt 以包含执行计划信息
                        plan_summary = "\n".join([
                            f"{i+1}. {st.name}: {st.description}" 
                            for i, st in enumerate(subtasks[:5])  # 只显示前5个
                        ])
                        if len(subtasks) > 5:
                            plan_summary += f"\n... 还有 {len(subtasks) - 5} 个子任务"
                        
                        planning_context += f"""

【任务分解结果】
任务已分解为 {len(subtasks)} 个子任务：
{plan_summary}

请按照执行计划逐步完成每个子任务。
"""
                        logger.info(f"执行计划创建完成: {len(execution_plan.parallel_groups)} 个并行组")
                    else:
                        logger.debug("任务不需要分解或只有一个子任务")
                except Exception as e:
                    logger.error(f"任务分解失败: {e}", exc_info=True)
                    debug_info = {
                        "type": "debug",
                        "category": "task_decomposition",
                        "message": "任务分解失败，使用原始任务",
                        "details": {"error": str(e)}
                    }
                    yield StreamMessageBuilder.build_debug(debug_info)
        
        # 5. 检查是否启用自主执行（优先于技能匹配）
        autonomous_execution_enabled = (
            os.getenv("ENABLE_AUTONOMOUS_EXECUTION", "false").lower() == "true"
        )
        
        if autonomous_execution_enabled and self.autonomous_executor:
            # 如果启用了自主执行，优先使用自主执行（不依赖复杂度判断）
            try:
                debug_info = {
                    "type": "debug",
                    "category": "autonomous_execution",
                    "message": "启用自主执行模式，跳过技能匹配",
                    "details": {}
                }
                yield StreamMessageBuilder.build_debug(debug_info)
                logger.info("启用自主执行模式，跳过技能匹配")
                
                # 使用自主执行器执行任务
                async for output in self.autonomous_executor.execute(
                    task=task,
                    context=context,
                    session_id=session_id
                ):
                    yield output
                
                return  # 自主执行完成，直接返回
            except Exception as e:
                logger.error(f"自主执行失败: {str(e)}", exc_info=True)
                debug_info = {
                    "type": "debug",
                    "category": "autonomous_execution",
                    "message": "自主执行失败，降级到技能匹配",
                    "details": {"error": str(e)}
                }
                yield StreamMessageBuilder.build_debug(debug_info)
                # 继续执行，尝试技能匹配
        
        # 6. 优先尝试匹配技能（集成任务管理和规划更新）
        # #region agent log
        try:
            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"orchestrator.py:stream_process:before_skill_match","message":"准备进行技能匹配","data":{},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
        except: pass
        # #endregion
        
        matched_skill = None
        if self.skill_registry is not None:
            matched_skill = await self.skill_registry.match(task)
        
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
        
        # 提取本地文件路径（适用于 video_extract_srt、video_cut 等需要本地文件路径的技能）
        # 使用 file_search_tool 来查找文件，而不是复杂的正则表达式
        local_files = []
        
        # 检查技能是否需要文件路径参数
        file_path_params = [p for p in skill.parameters if 'file' in p.name.lower() or 'path' in p.name.lower()]
        if file_path_params:
            # 从用户输入中提取文件名关键词（简化提取）
            # 尝试提取文件名模式（包含扩展名）
            filename_pattern = r'([\w\u4e00-\u9fff【】！×\s\-_]+\.(?:mp4|avi|mkv|mov|flv|webm|m4v|3gp|ts|mts|vob|ogv|rm|rmvb|asf|f4v|m2v|mpg|mpeg|mpe|mpv|m2ts|mts|mxf|divx|amv|qt|yuv|bik|drc|gifv|mng|nsv|roq|svi|viv|wmv|y4m|mp3|wav|m4a|aac|ogg|flac|srt|vtt|ass|ssa))'
            filename_matches = re.findall(filename_pattern, task, re.IGNORECASE)
            
            if filename_matches:
                # 使用 file_search_tool 搜索文件
                try:
                    file_search_tool = self.tool_registry.get_tool('file_search')
                    if file_search_tool:
                        # 提取文件名关键词（去掉扩展名，用于搜索）
                        search_query = filename_matches[0].split('.')[0].strip()
                        # 如果文件名包含特殊字符，尝试使用完整文件名
                        if len(search_query) < 5:
                            search_query = filename_matches[0]
                        
                        # 执行文件搜索
                        search_result = file_search_tool.execute(
                            query=search_query,
                            file_type=f"*.{filename_matches[0].split('.')[-1]}" if '.' in filename_matches[0] else None,
                            limit=5
                        )
                        
                        if search_result.success and search_result.data:
                            results = search_result.data.get('results', [])
                            if results:
                                # 使用第一个匹配的文件
                                local_files = [results[0]['path']]
                                logger.info(f"使用 file_search_tool 找到文件: {local_files[0]}")
                            else:
                                logger.warning(f"file_search_tool 未找到匹配文件: {search_query}")
                        else:
                            logger.warning(f"file_search_tool 搜索失败: {search_result.error if hasattr(search_result, 'error') else 'unknown error'}")
                    else:
                        logger.warning("file_search_tool 未注册，无法使用文件搜索")
                except Exception as e:
                    logger.warning(f"使用 file_search_tool 搜索文件失败: {e}", exc_info=True)
        
        # #region agent log
        try:
            import json
            import time
            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"J","location":"orchestrator.py:_extract_skill_parameters:after_file_search","message":"使用file_search_tool查找文件后","data":{"local_files":local_files,"local_files_count":len(local_files),"skill_name":skill.name},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                f.flush()
        except: pass
        # #endregion
        
        # 对于 video_extract_srt 技能，如果检测到本地文件路径，使用 video_path 参数
        if local_files and skill.name == 'video_extract_srt':
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
        
        # 对于 video_cut 技能，提取 input_file、segments 和 output_file 参数
        if skill.name == 'video_cut':
            if local_files and len(local_files) >= 1:
                # 设置 input_file 参数
                parameters['input_file'] = local_files[0]
                
                # 提取时间范围（格式：HH:MM:SS 或 MM:SS）
                time_pattern = r'(\d{1,2}:\d{2}:\d{2}|\d{1,2}:\d{2})'
                times = re.findall(time_pattern, task)
                
                if len(times) >= 2:
                    # 找到两个时间点，作为开始和结束时间
                    start_time = times[0]
                    end_time = times[1]
                    
                    # 确保时间格式为 HH:MM:SS
                    def normalize_time(t):
                        parts = t.split(':')
                        if len(parts) == 2:
                            # MM:SS -> 00:MM:SS
                            return f"00:{parts[0]}:{parts[1]}"
                        return t
                    
                    start_time = normalize_time(start_time)
                    end_time = normalize_time(end_time)
                    
                    # 构建 segments 数组
                    parameters['segments'] = [{
                        'start_time': start_time,
                        'end_time': end_time
                    }]
                    
                    # 生成输出文件名（基于输入文件名和时间范围）
                    from pathlib import Path
                    input_path = Path(parameters['input_file'])
                    # 移除时间中的冒号，用于文件名
                    time_str = f"{start_time.replace(':', '')}-{end_time.replace(':', '')}"
                    output_name = f"{input_path.stem}_cut_{time_str}{input_path.suffix}"
                    parameters['output_file'] = str(input_path.parent / output_name)
                    
                    logger.info(f"提取 video_cut 参数: input_file={parameters['input_file']}, segments={parameters['segments']}, output_file={parameters['output_file']}")
                elif len(times) == 1:
                    # 只有一个时间点，可能是开始时间，需要提示用户
                    logger.warning(f"只检测到一个时间点: {times[0]}，video_cut 需要开始和结束时间")
                else:
                    logger.warning("未检测到时间范围，video_cut 需要时间段信息")
        
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
            
            # ===== 自适应策略：收集执行指标（阶段2） =====
            import time
            execution_start_time = time.time()
            tool_call_count = 0
            tool_success_count = 0
            tool_failure_count = 0
            model_switch_count = 0
            task_complexity = None
            
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
                    
                    # ===== 根据工具类型选择模型（新增） =====
                    # 检测工具调用时，根据工具元数据选择最合适的模型
                    from backend.core.agent.tools.metadata import tool_metadata_registry
                    from backend.services.llm.model_config import get_model_config_manager
                    
                    # 收集所有工具推荐的模型类型
                    recommended_models = set()
                    for tool_call in response.tool_calls:
                        tool_name = tool_call.function.name
                        metadata = tool_metadata_registry.get_metadata(tool_name)
                        if metadata and metadata.recommended_model:
                            recommended_models.add(metadata.recommended_model)
                    
                    # 如果所有工具都推荐同一个模型类型，切换到该模型
                    if len(recommended_models) == 1:
                        recommended_model_type = list(recommended_models)[0]
                        config_manager = get_model_config_manager()
                        current_model = self.llm_service.model
                        
                        # 根据推荐模型类型切换
                        if recommended_model_type == "code":
                            target_model = config_manager.get_code_model()
                        elif recommended_model_type == "reasoning":
                            target_model = config_manager.get_reasoning_model()
                        elif recommended_model_type == "chat":
                            target_model = config_manager.get_chat_model()
                        else:
                            target_model = None
                        
                        # 如果目标模型与当前模型不同，进行切换
                        if target_model and target_model != current_model:
                            logger.info(f"工具调用检测：切换到 {recommended_model_type} 模型 ({target_model})")
                            self.llm_service.set_model(target_model)
                            debug_info = {
                                "type": "debug",
                                "category": "orchestrator",
                                "message": "模型切换",
                                "details": {
                                    "reason": "工具类型推荐",
                                    "from": current_model,
                                    "to": target_model,
                                    "tools": [tc.function.name for tc in response.tool_calls]
                                }
                            }
                            yield StreamMessageBuilder.build_debug(debug_info)
                            self.debug.log_orchestrator_step(
                                "模型切换",
                                {
                                    "reason": "工具类型推荐",
                                    "from": current_model,
                                    "to": target_model,
                                    "tools": [tc.function.name for tc in response.tool_calls]
                                }
                            )
                    elif len(recommended_models) > 1:
                        # 多个工具推荐不同模型，选择优先级最高的（reasoning > code > chat）
                        config_manager = get_model_config_manager()
                        current_model = self.llm_service.model
                        
                        if "reasoning" in recommended_models:
                            target_model = config_manager.get_reasoning_model()
                            recommended_model_type = "reasoning"
                        elif "code" in recommended_models:
                            target_model = config_manager.get_code_model()
                            recommended_model_type = "code"
                        else:
                            target_model = config_manager.get_chat_model()
                            recommended_model_type = "chat"
                        
                        if target_model != current_model:
                            logger.info(f"工具调用检测：多个工具推荐不同模型，选择 {recommended_model_type} 模型 ({target_model})")
                            self.llm_service.set_model(target_model)
                            debug_info = {
                                "type": "debug",
                                "category": "orchestrator",
                                "message": "模型切换",
                                "details": {
                                    "reason": "多工具推荐（选择优先级最高）",
                                    "from": current_model,
                                    "to": target_model,
                                    "recommended_models": list(recommended_models),
                                    "tools": [tc.function.name for tc in response.tool_calls]
                                }
                            }
                            yield StreamMessageBuilder.build_debug(debug_info)
                            self.debug.log_orchestrator_step(
                                "模型切换",
                                {
                                    "reason": "多工具推荐（选择优先级最高）",
                                    "from": current_model,
                                    "to": target_model,
                                    "recommended_models": list(recommended_models),
                                    "tools": [tc.function.name for tc in response.tool_calls]
                                }
                            )
                    
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
                        
                        # ===== 自适应策略：收集工具执行指标（阶段2） =====
                        tool_call_count += 1
                        if tool_result.success:
                            tool_success_count += 1
                        else:
                            tool_failure_count += 1
                        
                        # ===== 动态模型切换：根据执行结果分析是否需要切换模型（阶段2） =====
                        if self.model_switcher and hasattr(self, 'complexity_analyzer') and self.complexity_analyzer:
                            try:
                                # 分析执行结果
                                task_complexity = None
                                if hasattr(self.complexity_analyzer, 'analyze_task'):
                                    # 尝试获取任务复杂度（如果可用）
                                    pass  # 暂时跳过，因为需要任务描述
                                
                                # 分析是否需要切换模型
                                tool_result_dict = {
                                    "success": tool_result.success,
                                    "data": tool_result.data if tool_result.success else None,
                                    "error": tool_result.error if not tool_result.success else None
                                }
                                
                                current_model = self.llm_service.model
                                target_model = self.model_switcher.analyze_execution_result(
                                    tool_name=tool_name,
                                    tool_result=tool_result_dict,
                                    current_model=current_model,
                                    task_complexity=task_complexity
                                )
                                
                                # 检查是否应该切换（限制切换次数）
                                switch_count = len([r for r in self.model_switcher.switch_history 
                                                   if r.to_model != current_model])
                                if self.model_switcher.should_switch_model(
                                    current_model=current_model,
                                    target_model=target_model,
                                    switch_count=switch_count,
                                    max_switches=3
                                ):
                                    logger.info(f"根据执行结果切换模型: {current_model} -> {target_model}")
                                    self.llm_service.set_model(target_model)
                                    model_switch_count += 1
                                    
                                    # 记录切换
                                    self.model_switcher.record_switch(
                                        from_model=current_model,
                                        to_model=target_model,
                                        reason=f"工具 {tool_name} 执行结果分析",
                                        context={
                                            "tool_name": tool_name,
                                            "tool_success": tool_result.success,
                                            "task_complexity": task_complexity.value if task_complexity else None
                                        }
                                    )
                                    
                                    # 发送调试信息
                                    debug_info = {
                                        "type": "debug",
                                        "category": "model_switcher",
                                        "message": "模型切换",
                                        "details": {
                                            "reason": "执行结果分析",
                                            "from": current_model,
                                            "to": target_model,
                                            "tool_name": tool_name,
                                            "tool_success": tool_result.success
                                        }
                                    }
                                    yield StreamMessageBuilder.build_debug(debug_info)
                            except Exception as e:
                                logger.warning(f"动态模型切换分析失败: {e}", exc_info=True)
                        
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
                    # ===== 自适应策略：记录执行指标并分析（阶段2） =====
                    if self.adaptive_strategy and tool_call_count > 0:
                        execution_time = time.time() - execution_start_time
                        metrics = ExecutionMetrics(
                            tool_call_count=tool_call_count,
                            tool_success_count=tool_success_count,
                            tool_failure_count=tool_failure_count,
                            model_switch_count=model_switch_count,
                            execution_time=execution_time,
                            average_tool_time=execution_time / tool_call_count if tool_call_count > 0 else 0.0,
                            complexity=task_complexity
                        )
                        
                        # 记录执行指标
                        self.adaptive_strategy.record_execution(metrics, user_prompt)
                        
                        # 分析并调整策略
                        adjustments = self.adaptive_strategy.analyze_and_adjust(metrics)
                        if adjustments:
                            for adjustment in adjustments:
                                debug_info = {
                                    "type": "debug",
                                    "category": "adaptive_strategy",
                                    "message": "策略调整建议",
                                    "details": adjustment.to_dict()
                                }
                                yield StreamMessageBuilder.build_debug(debug_info)
                                logger.info(f"策略调整建议: {adjustment.reason}")
                    
                    yield response.content
                    return
                
                # 如果都没有，返回空字符串
                yield ""
                return
            
            # 达到最大迭代次数，返回错误信息
            # ===== 自适应策略：记录执行指标（阶段2） =====
            if self.adaptive_strategy and tool_call_count > 0:
                execution_time = time.time() - execution_start_time
                metrics = ExecutionMetrics(
                    tool_call_count=tool_call_count,
                    tool_success_count=tool_success_count,
                    tool_failure_count=tool_failure_count,
                    model_switch_count=model_switch_count,
                    execution_time=execution_time,
                    average_tool_time=execution_time / tool_call_count if tool_call_count > 0 else 0.0,
                    complexity=task_complexity
                )
                self.adaptive_strategy.record_execution(metrics, user_prompt)
                adjustments = self.adaptive_strategy.analyze_and_adjust(metrics)
                if adjustments:
                    for adjustment in adjustments:
                        logger.info(f"策略调整建议: {adjustment.reason}")
            
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
                    
                    # ===== 根据工具类型选择模型（新增） =====
                    # 检测工具调用时，根据工具元数据选择最合适的模型
                    from backend.core.agent.tools.metadata import tool_metadata_registry
                    from backend.services.llm.model_config import get_model_config_manager
                    
                    # 收集所有工具推荐的模型类型
                    recommended_models = set()
                    for tool_call in response.tool_calls:
                        tool_name = tool_call.function.name
                        metadata = tool_metadata_registry.get_metadata(tool_name)
                        if metadata and metadata.recommended_model:
                            recommended_models.add(metadata.recommended_model)
                    
                    # 如果所有工具都推荐同一个模型类型，切换到该模型
                    if len(recommended_models) == 1:
                        recommended_model_type = list(recommended_models)[0]
                        config_manager = get_model_config_manager()
                        current_model = self.llm_service.model
                        
                        # 根据推荐模型类型切换
                        if recommended_model_type == "code":
                            target_model = config_manager.get_code_model()
                        elif recommended_model_type == "reasoning":
                            target_model = config_manager.get_reasoning_model()
                        elif recommended_model_type == "chat":
                            target_model = config_manager.get_chat_model()
                        else:
                            target_model = None
                        
                        # 如果目标模型与当前模型不同，进行切换
                        if target_model and target_model != current_model:
                            logger.info(f"工具调用检测：切换到 {recommended_model_type} 模型 ({target_model})")
                            self.llm_service.set_model(target_model)
                            self.debug.log_orchestrator_step(
                                "模型切换",
                                {
                                    "reason": "工具类型推荐",
                                    "from": current_model,
                                    "to": target_model,
                                    "tools": [tc.function.name for tc in response.tool_calls]
                                }
                            )
                    elif len(recommended_models) > 1:
                        # 多个工具推荐不同模型，选择优先级最高的（reasoning > code > chat）
                        config_manager = get_model_config_manager()
                        current_model = self.llm_service.model
                        
                        if "reasoning" in recommended_models:
                            target_model = config_manager.get_reasoning_model()
                            recommended_model_type = "reasoning"
                        elif "code" in recommended_models:
                            target_model = config_manager.get_code_model()
                            recommended_model_type = "code"
                        else:
                            target_model = config_manager.get_chat_model()
                            recommended_model_type = "chat"
                        
                        if target_model != current_model:
                            logger.info(f"工具调用检测：多个工具推荐不同模型，选择 {recommended_model_type} 模型 ({target_model})")
                            self.llm_service.set_model(target_model)
                            self.debug.log_orchestrator_step(
                                "模型切换",
                                {
                                    "reason": "多工具推荐（选择优先级最高）",
                                    "from": current_model,
                                    "to": target_model,
                                    "recommended_models": list(recommended_models),
                                    "tools": [tc.function.name for tc in response.tool_calls]
                                }
                            )
                    
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
        使用推理模型智能选择最适合的模型
        
        Args:
            task: 用户任务
            
        Returns:
            选定的模型名称（从配置的 CHAT_MODEL、CODE_MODEL、REASONING_MODEL 中选择）
        """
        import os
        from backend.services.llm.model_config import get_model_config_manager
        from backend.core.agent.models import TaskComplexity
        
        # 如果禁用了智能模型选择，直接返回默认模型
        if os.getenv("DISABLE_SMART_MODEL_SELECTION", "false").lower() == "true":
            config_manager = get_model_config_manager()
            return config_manager.get_chat_model()
        
        config_manager = get_model_config_manager()
        
        # 获取配置的模型
        chat_model = config_manager.get_chat_model()
        code_model = config_manager.get_code_model()
        reasoning_model = config_manager.get_reasoning_model()
        
        # ===== 1. 任务复杂度评估（新增） =====
        # 使用复杂度分析器评估任务复杂度
        if self.complexity_analyzer:
            try:
                complexity_analysis = self.complexity_analyzer.analyze_task(task)
                complexity_score = complexity_analysis.get("score", 0.0)
                
                # 根据复杂度分数映射到 TaskComplexity 枚举
                if complexity_score >= 0.5:
                    # 复杂任务（score >= 0.5）→ 优先使用推理模型
                    logger.debug(f"任务复杂度: COMPLEX (score={complexity_score:.2f}), 选择推理模型")
                    return reasoning_model
                elif complexity_score < 0.2:
                    # 简单任务（score < 0.2）→ 继续使用快速规则判断
                    logger.debug(f"任务复杂度: SIMPLE (score={complexity_score:.2f}), 使用快速规则判断")
                    # 继续执行下面的快速规则判断
                else:
                    # 中等复杂度任务（0.2 <= score < 0.5）→ 结合快速规则和复杂度判断
                    logger.debug(f"任务复杂度: MEDIUM (score={complexity_score:.2f}), 结合快速规则判断")
                    # 继续执行下面的快速规则判断
            except Exception as e:
                logger.warning(f"复杂度评估失败: {e}，继续使用快速规则判断")
                # 评估失败时降级到快速规则判断
        
        # ===== 2. 快速规则判断（避免 LLM 调用） =====
        task_lower = task.lower()
        
        # 代码相关关键词（具体操作类）- 扩展列表
        code_keywords = [
            # 执行操作
            "执行", "execute", "运行", "run", "启动", "start",
            # 命令操作
            "ls", "cat", "cd", "mkdir", "rm", "mv", "cp", "grep", "find", "ps", "kill",
            # 编程操作
            "编写", "write", "创建", "create", "生成代码", "generate code",
            # 函数和脚本
            "函数", "function", "方法", "method", "脚本", "script", "程序", "program",
            # 代码相关
            "代码", "code", "编程", "programming", "开发", "develop",
            # 调试和测试
            "调试", "debug", "测试", "test", "单元测试", "unit test",
            # 编译和构建
            "编译", "compile", "构建", "build", "打包", "package"
        ]
        
        # 代码生成相关关键词（需要区分）- 扩展列表
        code_generation_keywords = [
            "代码", "code", "编程", "program", "程序", "programming",
            "实现", "implement", "开发", "develop", "创建", "create"
        ]
        
        # 推理相关关键词（优先级更高）- 扩展列表
        reasoning_keywords = [
            # 分析类
            "分析", "analyze", "分析", "analysis", "解析", "parse", "理解", "understand",
            # 推理类
            "推理", "reasoning", "思考", "think", "思考", "thinking", "推断", "infer",
            # 策略类
            "策略", "strategy", "计划", "plan", "规划", "planning", "设计", "design",
            # 解决类
            "解决", "solve", "处理", "handle", "应对", "deal with",
            # 问题类
            "为什么", "why", "如何", "how", "什么", "what", "哪里", "where",
            # 报告类
            "报告", "report", "总结", "summary", "概述", "overview", "评估", "evaluate",
            # 研究类
            "研究", "research", "调研", "investigate", "调查", "investigation", "探索", "explore",
            # 多步骤类
            "然后", "then", "接着", "next", "最后", "finally", "首先", "first", "其次", "second",
            "多步骤", "multi-step", "步骤", "step", "流程", "process",
            # 比较类
            "比较", "compare", "对比", "contrast", "评估", "evaluate", "判断", "judge",
            # 优化类
            "优化", "optimize", "改进", "improve", "提升", "enhance", "重构", "refactor"
        ]
        
        # 优先判断：如果任务包含推理关键词，使用推理模型
        # 注意：推理关键词检查要在代码关键词之前，避免"分析代码结构"被误判
        reasoning_keyword_count = sum(1 for keyword in reasoning_keywords if keyword in task_lower)
        if reasoning_keyword_count > 0:
            # 但如果同时包含代码生成关键词，需要更智能的判断
            # 例如："写代码" vs "分析代码结构"
            code_gen_count = sum(1 for keyword in code_generation_keywords if keyword in task_lower)
            
            # 如果推理关键词明显多于代码生成关键词，使用推理模型
            # 或者包含明确的推理动作词（如"分析"、"研究"、"报告"）
            strong_reasoning_keywords = ["分析", "analyze", "研究", "research", "报告", "report", 
                                        "评估", "evaluate", "比较", "compare", "优化", "optimize",
                                        "总结", "summary", "概述", "overview", "判断", "judge"]
            has_strong_reasoning = any(kw in task_lower for kw in strong_reasoning_keywords)
            
            if has_strong_reasoning or reasoning_keyword_count > code_gen_count:
                logger.debug(f"推理关键词匹配: count={reasoning_keyword_count}, 选择推理模型")
                return reasoning_model
        
        # 检查复杂模式（如"生成.*文章"、"生成.*报告"）- 扩展模式
        import re
        reasoning_patterns = [
            r"生成.*文章",
            r"生成.*报告",
            r"生成.*分析",
            r"撰写.*报告",
            r"编写.*报告",
            r"创建.*报告",
            r"制作.*报告",
            r"输出.*报告",
            r"生成.*总结",
            r"生成.*评估",
            r"生成.*对比",
            r"生成.*比较"
        ]
        if any(re.search(pattern, task_lower) for pattern in reasoning_patterns):
            logger.debug("推理模式匹配，选择推理模型")
            return reasoning_model
        
        # 判断：如果任务包含代码操作关键词，使用代码模型
        code_keyword_count = sum(1 for keyword in code_keywords if keyword in task_lower)
        if code_keyword_count > 0:
            # 如果同时包含推理关键词，需要判断优先级
            if reasoning_keyword_count == 0 or code_keyword_count > reasoning_keyword_count * 2:
                logger.debug(f"代码关键词匹配: count={code_keyword_count}, 选择代码模型")
                return code_model
        
        # 判断：如果任务包含代码生成关键词，使用代码模型
        code_gen_count = sum(1 for keyword in code_generation_keywords if keyword in task_lower)
        if code_gen_count > 0 and reasoning_keyword_count == 0:
            logger.debug(f"代码生成关键词匹配: count={code_gen_count}, 选择代码模型")
            return code_model
        
        # 如果任务很短（少于20字符），默认使用对话模型，避免 LLM 调用
        if len(task.strip()) < 20:
            return chat_model
        
        # 对于复杂任务，使用 LLM 分析（但设置超时）
        model_selection_prompt = f"""分析以下任务，决定应该使用哪个模型：

任务：{task}

可选模型：
1. {chat_model}: 适用于日常对话、文本生成、翻译、信息检索等一般性任务
2. {reasoning_model}: 适用于需要复杂推理的任务，如数学推理、逻辑分析、策略制定、问题解决、工具选择决策等
3. {code_model}: 适用于代码生成、代码补全、代码修复、代码审查、编程相关任务，以及简单的命令执行（如 ls、cat、cd 等）

重要提示：
- 如果任务是执行简单的系统命令（如显示文件、查看目录、执行脚本等），应该使用 {code_model}
- 如果任务需要复杂的逻辑推理、多步骤分析、策略制定、工具选择，使用 {reasoning_model}
- 如果任务只是简单的命令执行，不要使用 {reasoning_model}，避免过度思考
- 如果任务是一般性对话或文本生成，使用 {chat_model}

请只返回模型名称（{chat_model}、{reasoning_model} 或 {code_model}），不要返回其他内容。"""

        try:
            # 临时切换到推理模型进行分析（设置较短的超时）
            original_model = self.llm_service.model
            original_timeout = None
            
            # 临时设置较短的超时（10秒）
            if hasattr(self.llm_service, '_init_client'):
                # 保存原始超时设置
                pass
            
            self.llm_service.set_model(reasoning_model)
            
            # 使用推理模型分析（添加超时保护）
            import asyncio
            try:
                analysis = await asyncio.wait_for(
                    self.llm_service.chat(
                        system_prompt="你是一个模型选择助手，根据任务类型选择最合适的模型。",
                        user_prompt=model_selection_prompt
                    ),
                    timeout=10.0  # 10秒超时
                )
            except asyncio.TimeoutError:
                logger.warning("模型选择 LLM 调用超时，使用默认对话模型")
                self.llm_service.set_model(original_model)
                return chat_model
            
            # 恢复原模型
            self.llm_service.set_model(original_model)
            
            # 解析返回的模型名称
            analysis = analysis.strip().lower()
            if reasoning_model.lower() in analysis or "reasoner" in analysis or "reasoning" in analysis:
                return reasoning_model
            elif code_model.lower() in analysis or "coder" in analysis or "code" in analysis:
                return code_model
            else:
                # 默认使用对话模型
                return chat_model
                
        except Exception as e:
            logger.warning(f"模型选择失败，使用默认对话模型: {e}")
            return chat_model
    
    def get_chat_model(self) -> str:
        """获取对话模型配置"""
        from backend.services.llm.model_config import get_model_config_manager
        return get_model_config_manager().get_chat_model()
    
    def get_code_model(self) -> str:
        """获取编码模型配置"""
        from backend.services.llm.model_config import get_model_config_manager
        return get_model_config_manager().get_code_model()
    
    def get_reasoning_model(self) -> str:
        """获取推理模型配置"""
        from backend.services.llm.model_config import get_model_config_manager
        return get_model_config_manager().get_reasoning_model()




# 为了向后兼容，提供 Orchestrator 类别名
Orchestrator = UnifiedOrchestrator