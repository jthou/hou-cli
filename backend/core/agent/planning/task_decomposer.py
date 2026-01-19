"""任务分解器 - 使用推理模型将复杂任务分解为子任务"""
import logging
import json
import re
import uuid
from typing import List, Dict, Any, Optional
from backend.core.agent.models import SubTask, TaskComplexity
from backend.core.agent.planning.complexity import TaskComplexityAnalyzer
from backend.services.llm.llm_service import LLMService
from backend.services.llm.model_config import get_model_config_manager
from backend.core.agent.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class TaskDecomposer:
    """任务分解器
    
    使用推理模型将复杂任务分解为可执行的子任务，识别依赖关系和推荐模型类型。
    """
    
    def __init__(
        self,
        llm_service: LLMService,
        tool_registry: ToolRegistry,
        complexity_analyzer: Optional[TaskComplexityAnalyzer] = None
    ):
        """
        初始化任务分解器
        
        Args:
            llm_service: LLM 服务实例
            tool_registry: 工具注册表
            complexity_analyzer: 复杂度分析器（可选）
        """
        self.llm_service = llm_service
        self.tool_registry = tool_registry
        self.complexity_analyzer = complexity_analyzer or TaskComplexityAnalyzer()
        self.config_manager = get_model_config_manager()
    
    def _format_tools_for_llm(self) -> str:
        """格式化工具列表供 LLM 使用"""
        tools = self.tool_registry.list_tools()
        tool_descriptions = []
        
        for tool_name in tools:
            tool = self.tool_registry.get_tool(tool_name)
            if tool:
                desc = f"- {tool.name}: {tool.description}"
                if tool.parameters:
                    params = ", ".join([p.name for p in tool.parameters])
                    desc += f" (参数: {params})"
                tool_descriptions.append(desc)
        
        return "\n".join(tool_descriptions)
    
    def _parse_subtasks(self, response: str, original_task: str) -> List[SubTask]:
        """
        解析 LLM 返回的子任务列表
        
        Args:
            response: LLM 响应文本
            original_task: 原始任务描述
            
        Returns:
            子任务列表
        """
        subtasks = []
        
        try:
            # 尝试从 JSON 代码块中提取
            json_match = re.search(r"```json\n(.*?)\n```", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析
                json_str = response
            
            # 解析 JSON
            data = json.loads(json_str)
            
            # 处理不同的响应格式
            if isinstance(data, dict):
                if "subtasks" in data:
                    subtasks_data = data["subtasks"]
                elif "tasks" in data:
                    subtasks_data = data["tasks"]
                else:
                    # 假设整个字典是一个子任务
                    subtasks_data = [data]
            elif isinstance(data, list):
                subtasks_data = data
            else:
                logger.warning(f"无法解析 LLM 响应格式: {type(data)}")
                return [SubTask(name="主任务", description=original_task)]
            
            # 转换为 SubTask 对象
            for task_data in subtasks_data:
                if isinstance(task_data, str):
                    # 如果是字符串，直接作为描述
                    subtasks.append(SubTask(
                        name=f"子任务 {len(subtasks) + 1}",
                        description=task_data
                    ))
                elif isinstance(task_data, dict):
                    # 解析子任务数据
                    name = task_data.get("name", f"子任务 {len(subtasks) + 1}")
                    description = task_data.get("description", task_data.get("desc", ""))
                    required_tools = task_data.get("required_tools", task_data.get("tools", []))
                    dependencies = task_data.get("dependencies", task_data.get("deps", []))
                    
                    # 解析复杂度
                    complexity_str = task_data.get("estimated_complexity", task_data.get("complexity", "simple"))
                    try:
                        complexity = TaskComplexity(complexity_str.lower())
                    except ValueError:
                        complexity = TaskComplexity.SIMPLE
                    
                    # 推荐模型
                    recommended_model = task_data.get("recommended_model", task_data.get("model"))
                    
                    # 预估时间
                    estimated_time = task_data.get("estimated_time", task_data.get("time"))
                    
                    subtasks.append(SubTask(
                        name=name,
                        description=description,
                        required_tools=required_tools if isinstance(required_tools, list) else [],
                        dependencies=dependencies if isinstance(dependencies, list) else [],
                        estimated_complexity=complexity,
                        recommended_model=recommended_model,
                        estimated_time=estimated_time,
                        metadata=task_data.get("metadata", {})
                    ))
            
            logger.info(f"成功解析 {len(subtasks)} 个子任务")
            
        except json.JSONDecodeError as e:
            logger.error(f"解析 JSON 失败: {e}\n响应内容: {response[:500]}")
            # 降级：尝试从文本中提取子任务
            subtasks = self._parse_subtasks_from_text(response, original_task)
        
        except Exception as e:
            logger.error(f"解析子任务失败: {e}", exc_info=True)
            # 降级：返回原始任务作为单个子任务
            subtasks = [SubTask(name="主任务", description=original_task)]
        
        # 如果没有解析到子任务，返回原始任务
        if not subtasks:
            subtasks = [SubTask(name="主任务", description=original_task)]
        
        return subtasks
    
    def _parse_subtasks_from_text(self, text: str, original_task: str) -> List[SubTask]:
        """从文本中提取子任务（降级方案）"""
        subtasks = []
        
        # 尝试查找编号列表
        pattern = r"(?:^|\n)\s*(?:\d+[\.\)]|[-*])\s*(.+?)(?=\n\s*(?:\d+[\.\)]|[-*])|$)"
        matches = re.findall(pattern, text, re.MULTILINE)
        
        if matches:
            for i, match in enumerate(matches, 1):
                subtasks.append(SubTask(
                    name=f"子任务 {i}",
                    description=match.strip()
                ))
        else:
            # 最后降级：返回原始任务
            subtasks.append(SubTask(name="主任务", description=original_task))
        
        return subtasks
    
    async def decompose_task(self, task: str, context: Optional[Dict[str, Any]] = None) -> List[SubTask]:
        """
        使用推理模型分解复杂任务
        
        Args:
            task: 任务描述
            context: 任务上下文（可选）
            
        Returns:
            子任务列表
        """
        # 1. 检查是否需要分解
        if not self.complexity_analyzer.is_complex_task(task):
            logger.debug(f"任务 '{task[:50]}...' 不需要分解，返回单个子任务")
            return [SubTask(
                name="主任务",
                description=task,
                estimated_complexity=TaskComplexity.SIMPLE
            )]
        
        logger.info(f"开始分解任务: '{task[:50]}...'")
        
        # 2. 获取推理模型
        reasoning_model = self.config_manager.get_reasoning_model()
        
        # 3. 格式化工具列表
        tools_description = self._format_tools_for_llm()
        
        # 4. 构建提示词
        prompt = f"""分析以下任务，将其分解为可执行的子任务：

任务：{task}

可用工具：
{tools_description}

请返回 JSON 格式的子任务列表，每个子任务包含以下字段：
- name: 子任务名称（简短明确）
- description: 子任务描述（详细说明要做什么）
- required_tools: 需要的工具列表（工具名称数组，如 ["google_search", "browser"]）
- dependencies: 依赖的其他子任务名称列表（如果此任务需要等待其他任务完成）
- estimated_complexity: 复杂度评估（"simple"、"medium" 或 "complex"）
- recommended_model: 推荐的模型类型（"chat"、"code" 或 "reasoning"）
- estimated_time: 预估执行时间（秒，可选）

请确保：
1. 子任务粒度适中（不要太细也不要太粗）
2. 明确标识任务之间的依赖关系
3. 为每个子任务推荐合适的模型类型
4. 考虑工具的使用顺序和组合

返回格式示例：
{{
  "subtasks": [
    {{
      "name": "搜索相关信息",
      "description": "使用搜索工具查找相关文档和资料",
      "required_tools": ["google_search"],
      "dependencies": [],
      "estimated_complexity": "simple",
      "recommended_model": "chat",
      "estimated_time": 30
    }},
    {{
      "name": "分析代码结构",
      "description": "分析项目代码结构并生成报告",
      "required_tools": ["file_search", "browser"],
      "dependencies": ["搜索相关信息"],
      "estimated_complexity": "complex",
      "recommended_model": "reasoning",
      "estimated_time": 120
    }}
  ]
}}"""
        
        try:
            # 5. 调用推理模型
            response = await self.llm_service.chat(
                model=reasoning_model,
                system_prompt="你是一个任务规划专家，擅长将复杂任务分解为可执行的子任务。请确保返回有效的 JSON 格式。",
                user_prompt=prompt,
                temperature=0.3  # 降低温度以获得更稳定的结果
            )
            
            logger.debug(f"LLM 响应: {response[:200]}...")
            
            # 6. 解析响应
            subtasks = self._parse_subtasks(response, task)
            
            logger.info(f"任务分解完成，共 {len(subtasks)} 个子任务")
            
            return subtasks
            
        except Exception as e:
            logger.error(f"任务分解失败: {e}", exc_info=True)
            # 降级：返回原始任务作为单个子任务
            return [SubTask(name="主任务", description=task)]
    
    def validate_subtasks(self, subtasks: List[SubTask]) -> tuple[bool, Optional[str]]:
        """
        验证子任务列表的有效性
        
        Args:
            subtasks: 子任务列表
            
        Returns:
            (是否有效, 错误信息)
        """
        if not subtasks:
            return False, "子任务列表为空"
        
        # 检查任务名称唯一性
        names = [task.name for task in subtasks]
        if len(names) != len(set(names)):
            return False, "存在重复的子任务名称"
        
        # 检查依赖关系
        task_names = set(names)
        for task in subtasks:
            for dep in task.dependencies:
                if dep not in task_names:
                    return False, f"子任务 '{task.name}' 依赖不存在的任务 '{dep}'"
        
        # 检查循环依赖（简单检查）
        # 更复杂的检查可以在 ExecutionPlanner 中实现
        
        return True, None

