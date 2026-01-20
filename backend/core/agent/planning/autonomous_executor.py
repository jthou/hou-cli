"""自主执行器 - 推理模型自主使用工具通过多轮对话完成任务"""
import logging
from typing import Dict, Any, Optional, List, AsyncIterator
from backend.services.llm.llm_service import LLMService
from backend.services.llm.model_config import get_model_config_manager
from backend.core.agent.tools.registry import ToolRegistry
from backend.core.agent.planning.manager import PlanningManager

logger = logging.getLogger(__name__)


class AutonomousExecutor:
    """自主执行器
    
    使用推理模型自主分析任务、制定计划、调用工具，通过多轮对话完成任务。
    """
    
    def __init__(
        self,
        llm_service: LLMService,
        tool_registry: ToolRegistry,
        planning_manager: Optional[PlanningManager] = None
    ):
        """
        初始化自主执行器
        
        Args:
            llm_service: LLM 服务实例
            tool_registry: 工具注册表
            planning_manager: 规划管理器（可选）
        """
        self.llm_service = llm_service
        self.tool_registry = tool_registry
        self.planning_manager = planning_manager
        self.config_manager = get_model_config_manager()
        
        # 获取推理模型
        self.reasoning_model = self.config_manager.get_reasoning_model()
        
        # 执行状态
        self.max_iterations = 20  # 最多20轮对话
        self.current_iteration = 0
        self.execution_history: List[Dict[str, Any]] = []
    
    async def _analyze_task_and_plan(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        分析任务并制定执行计划
        
        Args:
            task: 任务描述
            context: 任务上下文（可选）
            
        Returns:
            执行计划字典，包含：
            - plan: 执行计划文本
            - steps: 执行步骤列表
            - estimated_tools: 预估需要的工具列表
        """
        # 切换到推理模型
        self.llm_service.set_model(self.reasoning_model)
        
        # 获取可用工具列表
        available_tools = self.tool_registry.list_tools()
        tools_description_parts = []
        for tool_name in available_tools:
            tool = self.tool_registry.get_tool(tool_name)
            if tool:
                tools_description_parts.append(
                    f"- {tool_name}: {tool.description}"
                )
        tools_description = "\n".join(tools_description_parts)
        
        # 构建提示词
        prompt = f"""你是一个智能任务执行助手。请分析以下任务，制定详细的执行计划。

任务：{task}

可用工具：
{tools_description}

请制定一个详细的执行计划，包括：
1. 任务分析：理解任务的核心需求和目标
2. 执行步骤：将任务分解为具体的执行步骤
3. 工具选择：为每个步骤推荐合适的工具
4. 预期结果：描述每个步骤的预期输出

请以结构化的方式返回计划，确保计划清晰、可执行。"""
        
        try:
            # 使用推理模型
            self.llm_service.set_model(self.reasoning_model)
            response = await self.llm_service.chat(
                system_prompt=(
                    "你是一个专业的任务规划专家，"
                    "擅长分析任务并制定详细的执行计划。"
                ),
                user_prompt=prompt
            )
            
            # 解析响应，提取计划信息
            if response:
                plan_text = str(response)
            else:
                plan_text = f"执行任务: {task}"

            steps = self._extract_steps_from_plan(plan_text)
            estimated_tools = self._extract_tools_from_plan(
                plan_text, available_tools
            )
            plan = {
                "plan": plan_text,
                "steps": steps,
                "estimated_tools": estimated_tools
            }

            logger.info(
                f"任务分析完成，制定了 {len(plan['steps'])} 个执行步骤"
            )
            return plan
            
        except Exception as e:
            logger.error(f"任务分析失败: {e}", exc_info=True)
            # 返回默认计划
            return {
                "plan": f"执行任务: {task}",
                "steps": [task],
                "estimated_tools": []
            }
    
    def _extract_steps_from_plan(self, plan_text: str) -> List[str]:
        """
        从计划文本中提取执行步骤
        
        Args:
            plan_text: 计划文本
            
        Returns:
            执行步骤列表
        """
        import re
        
        steps = []
        
        # 尝试匹配编号列表（1. 2. 3. 或 1) 2) 3)）
        pattern = (
            r'(?:^|\n)\s*(?:\d+[\.\)]|[-*])\s*(.+?)'
            r'(?=\n\s*(?:\d+[\.\)]|[-*])|$)'
        )
        matches = re.findall(pattern, plan_text, re.MULTILINE)
        
        if matches:
            steps = [match.strip() for match in matches]
        else:
            # 如果没有找到编号列表，尝试按段落分割
            paragraphs = [p.strip() for p in plan_text.split('\n\n') if p.strip()]
            steps = paragraphs[:10]  # 最多取10个步骤
        
        return steps if steps else [plan_text]
    
    def _extract_tools_from_plan(
        self,
        plan_text: str,
        available_tools: List[str]
    ) -> List[str]:
        """
        从计划文本中提取预估需要的工具
        
        Args:
            plan_text: 计划文本
            available_tools: 可用工具列表
            
        Returns:
            预估需要的工具列表
        """
        estimated_tools = []
        
        plan_lower = plan_text.lower()
        
        # 检查每个可用工具是否在计划中被提及
        for tool_name in available_tools:
            tool = self.tool_registry.get_tool(tool_name)
            if tool:
                # 检查工具名称或描述是否在计划中出现
                tool_desc_lower = tool.description.lower()
                if (tool_name.lower() in plan_lower or
                        tool_desc_lower in plan_lower):
                    estimated_tools.append(tool_name)

        return estimated_tools

    async def _execute_single_turn(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        执行单轮对话（包括工具调用）

        Args:
            messages: 消息历史
            tools: 工具定义列表（可选）

        Returns:
            执行结果字典，包含：
            - response: LLM 响应
            - tool_calls: 工具调用列表
            - tool_results: 工具执行结果列表
            - finished: 是否完成（True 表示任务完成，False 表示需要继续）
        """
        # 切换到推理模型
        self.llm_service.set_model(self.reasoning_model)

        try:
            # 调用 LLM
            response = await self.llm_service.chat(
                messages=messages,
                tools=tools
            )

            # 检查响应类型
            if isinstance(response, str):
                # 普通文本回复，任务可能完成
                return {
                    "response": response,
                    "tool_calls": [],
                    "tool_results": [],
                    "finished": True
                }

            # 检查是否有工具调用
            tool_calls = []
            tool_results = []
            reasoning_content = None

            # 提取 reasoning_content（推理模型特有）
            if response and hasattr(response, 'reasoning_content'):
                reasoning_content = response.reasoning_content

            if (response and
                    hasattr(response, 'tool_calls') and
                    response.tool_calls):
                tool_calls = response.tool_calls

                # 执行所有工具调用
                for tool_call in tool_calls:
                    tool_name = tool_call.function.name
                    tool_args_str = tool_call.function.arguments

                    # 解析参数
                    import json
                    try:
                        tool_args = json.loads(tool_args_str)
                    except json.JSONDecodeError:
                        tool_args = {}

                    # 执行工具
                    try:
                        tool_result = await self.tool_registry.execute_async(
                            tool_name, **tool_args
                        )
                        tool_results.append({
                            "tool_call_id": tool_call.id,
                            "tool_name": tool_name,
                            "success": tool_result.success,
                            "data": tool_result.data,
                            "error": tool_result.error
                        })

                        # 记录到规划文件
                        if self.planning_manager:
                            if tool_result.success:
                                self.planning_manager.add_progress(
                                    f"执行工具: {tool_name}",
                                    files_modified=[],
                                    session_id=None
                                )
                            else:
                                self.planning_manager.add_error(
                                    f"工具 {tool_name} 执行失败",
                                    attempt=1,
                                    resolution=tool_result.error or "未知错误",
                                    session_id=None
                                )

                    except Exception as e:
                        logger.error(
                            f"工具执行失败: {tool_name}, 错误: {e}",
                            exc_info=True
                        )
                        tool_results.append({
                            "tool_call_id": tool_call.id,
                            "tool_name": tool_name,
                            "success": False,
                            "data": None,
                            "error": str(e)
                        })

            # 判断是否完成
            response_str = (
                response if isinstance(response, str)
                else str(response) if response else ""
            )
            # 改进完成判断逻辑：只有当没有工具调用且明确说完成时才认为完成
            # 如果有工具调用，说明还需要继续执行
            finished = (
                not tool_calls and
                ("完成" in response_str or "任务完成" in response_str)
            )

            return {
                "response": response,
                "tool_calls": tool_calls,
                "tool_results": tool_results,
                "finished": finished,
                "reasoning_content": reasoning_content
            }

        except Exception as e:
            logger.error(f"执行单轮对话失败: {e}", exc_info=True)
            return {
                "response": None,
                "tool_calls": [],
                "tool_results": [],
                "finished": False,
                "error": str(e)
            }

    def _build_messages(
        self,
        task: str,
        plan: Dict[str, Any],
        execution_history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        构建消息历史（用于多轮对话）

        Args:
            task: 原始任务描述
            plan: 执行计划
            execution_history: 执行历史

        Returns:
            消息列表（OpenAI 格式）
        """
        messages = []

        # 系统提示：包含任务和计划
        steps_text = "\n".join([
            f'{i+1}. {step}'
            for i, step in enumerate(plan.get('steps', []))
        ])
        system_content = f"""你是一个智能任务执行助手。你的任务是自主使用工具完成用户的任务。

原始任务：{task}

执行计划：
{plan.get('plan', '')}

执行步骤列表：
{steps_text}

可用工具：{', '.join(plan.get('estimated_tools', []))}

**重要提醒**：
1. 必须完成所有计划步骤，不能遗漏任何步骤
2. 如果计划中提到需要调用某个工具（如whisper用于生成字幕），必须调用该工具
3. 只有当所有步骤都完成时，才能说"任务完成"
4. 如果某个步骤失败，需要重试或寻找替代方案

请按照计划逐步执行任务：
1. 分析当前步骤需要做什么
2. 选择合适的工具
3. 执行工具并获取结果
4. 根据结果决定下一步行动
5. 重复直到所有步骤完成

**判断任务完成的标准**：
- 所有计划步骤都已执行
- 所有必要的工具都已调用（特别是任务中明确提到的工具，如whisper用于生成字幕）
- 任务目标已达成

当且仅当所有步骤都完成时，请明确说明"任务完成"。"""

        messages.append({
            "role": "system",
            "content": system_content
        })

        # 添加执行历史
        for history_item in execution_history:
            if "user_message" in history_item:
                messages.append({
                    "role": "user",
                    "content": history_item["user_message"]
                })

            if "assistant_response" in history_item:
                messages.append({
                    "role": "assistant",
                    "content": history_item["assistant_response"]
                })

            # 添加工具调用和结果
            if "tool_calls" in history_item:
                # 这里需要根据实际的工具调用格式构建
                # 暂时简化处理
                pass

        return messages

    async def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        执行任务（主函数）- 通过多轮对话自主完成任务

        Args:
            task: 任务描述
            context: 任务上下文（可选）
            session_id: 会话ID（可选，用于规划文件）

        Yields:
            流式输出（执行过程、工具调用、结果等）
        """
        # 1. 分析任务并制定计划
        plan = await self._analyze_task_and_plan(task, context)

        # 记录计划到规划文件
        if self.planning_manager and session_id:
            try:
                planning_files = (
                    self.planning_manager.create_planning_files(
                        task, session_id
                    )
                )
                # 将计划写入 task_plan.md
                plan_content = f"""# 任务执行计划

## 原始任务
{task}

## 执行计划
{plan.get('plan', '')}

## 执行步骤
{chr(10).join([f'{i+1}. {step}' for i, step in enumerate(plan.get('steps', []))])}

## 预估工具
{', '.join(plan.get('estimated_tools', []))}
"""
                with open(planning_files.task_plan, 'w',
                          encoding='utf-8') as f:
                    f.write(plan_content)
            except Exception as e:
                logger.warning(f"写入规划文件失败: {e}")

        # 2. 获取工具定义
        tools = self.tool_registry.get_tools_for_llm()

        # 3. 初始化消息历史
        messages = self._build_messages(task, plan, [])

        # 4. 多轮对话循环
        self.current_iteration = 0
        self.execution_history = []
        
        # 导入时间模块用于心跳
        import time
        last_output_time = time.time()
        heartbeat_interval = 30.0  # 每30秒发送一次心跳

        while self.current_iteration < self.max_iterations:
            self.current_iteration += 1
            
            # 输出当前轮次开始信息
            yield f"\n[执行第 {self.current_iteration}/{self.max_iterations} 轮]\n"
            last_output_time = time.time()

            # 输出工具调用信息（在执行前）
            if self.current_iteration > 1:
                # 检查是否需要发送心跳（如果长时间没有输出）
                current_time = time.time()
                if current_time - last_output_time >= heartbeat_interval:
                    yield f"\n[状态] 正在处理中... (已用时 {int(current_time - last_output_time)} 秒)\n"
                    last_output_time = current_time
            
            # 执行单轮对话
            result = await self._execute_single_turn(messages, tools)
            
            # 输出工具调用和执行结果
            if result.get("tool_calls"):
                for tool_call in result.get("tool_calls", []):
                    if hasattr(tool_call, 'function'):
                        tool_name = tool_call.function.name
                        yield f"\n[工具调用] 正在执行: {tool_name}\n"
                        last_output_time = time.time()
            
            if result.get("tool_results"):
                for tool_result in result.get("tool_results", []):
                    tool_name = tool_result.get("tool_name", "未知工具")
                    if tool_result.get("success"):
                        yield f"[工具结果] {tool_name} 执行成功\n"
                    else:
                        error_msg = tool_result.get("error", "未知错误")
                        yield (
                            f"[工具结果] {tool_name} 执行失败: "
                            f"{error_msg}\n"
                        )
                    last_output_time = time.time()

            # 记录执行历史
            self.execution_history.append({
                "iteration": self.current_iteration,
                "result": result
            })

            # 更新消息历史
            if result.get("response"):
                # 添加助手响应
                response_str = (
                    result["response"] if isinstance(
                        result["response"], str
                    )
                    else str(result["response"])
                )

                assistant_msg: Dict[str, Any] = {
                    "role": "assistant",
                    "content": response_str
                }

                # 如果有工具调用，添加到消息中
                tool_calls = result.get("tool_calls", [])
                reasoning_content = result.get("reasoning_content")
                
                # 推理模型在工具调用时需要 reasoning_content
                if tool_calls and reasoning_content:
                    assistant_msg["reasoning_content"] = reasoning_content
                
                if tool_calls:
                    tool_calls_list = []
                    for tc in tool_calls:
                        if hasattr(tc, 'id') and hasattr(tc, 'function'):
                            tool_calls_list.append({
                                "id": tc.id,
                                "type": getattr(tc, 'type', 'function'),
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            })
                    if tool_calls_list:
                        assistant_msg["tool_calls"] = tool_calls_list

                messages.append(assistant_msg)

                # 添加工具结果
                if result.get("tool_results"):
                    for tool_result in result["tool_results"]:
                        import json
                        tool_result_content = json.dumps(
                            tool_result.get("data", {}),
                            ensure_ascii=False
                        ) if tool_result.get("success") else json.dumps(
                            {"error": tool_result.get("error", "")},
                            ensure_ascii=False
                        )

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_result.get(
                                "tool_call_id", ""
                            ),
                            "name": tool_result.get("tool_name", ""),
                            "content": tool_result_content
                        })

            # 输出当前轮次的结果
            if result.get("response"):
                response_str = (
                    result["response"] if isinstance(
                        result["response"], str
                    )
                    else str(result["response"])
                )
                yield f"[第 {self.current_iteration} 轮] {response_str}\n"

            # 检查是否完成
            if result.get("finished"):
                yield "\n✅ 任务完成！\n"
                break

            # 检查是否出错
            if result.get("error"):
                yield f"\n❌ 执行出错: {result['error']}\n"
                break

        # 如果达到最大迭代次数
        if self.current_iteration >= self.max_iterations:
            yield f"\n⚠️ 达到最大迭代次数 ({self.max_iterations})，任务可能未完全完成。\n"


