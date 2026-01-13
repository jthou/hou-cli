"""技能执行器 - 执行技能工作流"""
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from backend.core.agent.skills.base import Skill, SkillResult
from backend.core.agent.tools.registry import ToolRegistry
from backend.services.llm.llm_service import LLMService

logger = logging.getLogger(__name__)


class SkillExecutor:
    """技能执行器，负责执行技能的工作流"""
    
    def __init__(self, tool_registry: ToolRegistry, llm_service: LLMService):
        """
        初始化技能执行器
        
        Args:
            tool_registry: 工具注册表
            llm_service: LLM 服务
        """
        self.tool_registry = tool_registry
        self.llm_service = llm_service
        self.progress_callback: Optional[Callable[[str], None]] = None
    
    def set_progress_callback(self, callback: Optional[Callable[[str], None]]):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def report_progress(self, message: str):
        """报告进度"""
        if self.progress_callback:
            self.progress_callback(message)
    
    def _evaluate_expression(self, expression: str, context: Dict[str, Any]) -> Any:
        """
        计算表达式（简单的变量替换和条件判断）
        
        支持的语法：
        - ${variable} - 变量替换
        - ${steps[N].field} - 步骤结果字段
        - ${input.field} - 输入参数
        - ${file_exists(path)} - 文件存在检查
        - ${not condition} - 逻辑非
        - ${condition and condition} - 逻辑与
        - ${condition or condition} - 逻辑或
        """
        # 替换变量
        def replace_var(match):
            var_expr = match.group(1)
            
            # 处理 steps[N].field
            if var_expr.startswith('steps['):
                match_steps = re.match(r'steps\[(\d+)\]\.(.+)', var_expr)
                if match_steps:
                    step_idx = int(match_steps.group(1))
                    field = match_steps.group(2)
                    if 'step_results' in context and step_idx < len(context['step_results']):
                        step_result = context['step_results'][step_idx]
                        if isinstance(step_result, dict):
                            return str(step_result.get(field, ''))
                    return ''
            
            # 处理 input.field
            if var_expr.startswith('input.'):
                field = var_expr[6:]
                if 'input' in context:
                    return str(context['input'].get(field, ''))
                return ''
            
            # 处理 config.field
            if var_expr.startswith('config.'):
                field = var_expr[7:]
                if 'config' in context:
                    return str(context['config'].get(field, ''))
                return ''
            
            # 直接变量
            if var_expr in context:
                return str(context[var_expr])
            
            return ''
        
        # 替换所有 ${...} 表达式
        result = re.sub(r'\$\{([^}]+)\}', replace_var, expression)
        
        # 处理函数调用
        # file_exists(path)
        def replace_file_exists(match):
            path_str = match.group(1).strip('"\'')
            path = Path(path_str)
            return str(path.exists())
        
        result = re.sub(r'file_exists\(([^)]+)\)', replace_file_exists, result)
        
        # 处理逻辑运算符
        result = result.replace(' and ', ' && ').replace(' or ', ' || ').replace(' not ', ' ! ')
        
        # 简单的布尔值评估
        if result.lower() in ('true', '1', 'yes', 'on'):
            return True
        elif result.lower() in ('false', '0', 'no', 'off', ''):
            return False
        
        return result
    
    def _resolve_inputs(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """解析输入参数"""
        resolved = {}
        for key, value in inputs.items():
            if isinstance(value, str):
                resolved[key] = self._evaluate_expression(value, context)
            else:
                resolved[key] = value
        return resolved
    
    async def execute_workflow_step(
        self,
        step: Dict[str, Any],
        context: Dict[str, Any],
        step_index: int
    ) -> Dict[str, Any]:
        """
        执行工作流步骤
        
        Args:
            step: 步骤定义
            context: 执行上下文
            step_index: 步骤索引
        
        Returns:
            步骤执行结果
        """
        step_name = step.get('name', f'step_{step_index}')
        step_type = step.get('type', 'tool')
        
        logger.info(f"执行步骤 {step_index}: {step_name} (类型: {step_type})")
        self.report_progress(f"执行步骤 {step_index + 1}: {step_name}")
        
        try:
            # 检查条件
            if 'condition' in step:
                condition = self._evaluate_expression(step['condition'], context)
                if not condition:
                    logger.info(f"步骤 {step_name} 条件不满足，跳过")
                    # 处理 skip_outputs
                    if 'skip_outputs' in step:
                        return self._resolve_inputs(step['skip_outputs'], context)
                    return {}
            
            # 检查 skip_if
            if 'skip_if' in step:
                skip_condition = self._evaluate_expression(step['skip_if'], context)
                if skip_condition:
                    logger.info(f"步骤 {step_name} skip_if 条件满足，跳过")
                    if 'skip_outputs' in step:
                        return self._resolve_inputs(step['skip_outputs'], context)
                    return {}
            
            # 根据步骤类型执行
            if step_type == 'tool':
                return await self._execute_tool_step(step, context)
            elif step_type == 'llm_call':
                return await self._execute_llm_step(step, context)
            elif step_type == 'code_executor':
                return await self._execute_code_step(step, context)
            else:
                logger.warning(f"未知的步骤类型: {step_type}")
                return {}
        
        except Exception as e:
            logger.error(f"步骤 {step_name} 执行失败: {e}", exc_info=True)
            
            # 错误处理
            error_handling = step.get('error_handling', {})
            on_error = error_handling.get('on_error', 'fail')
            
            if on_error == 'skip':
                logger.warning(f"步骤 {step_name} 失败，跳过")
                return {}
            elif on_error == 'retry':
                max_retries = error_handling.get('max_retries', 1)
                # TODO: 实现重试逻辑
                return {}
            elif on_error == 'fallback':
                fallback = error_handling.get('fallback', '')
                return {'error': str(e), 'fallback': fallback}
            else:  # fail
                raise
    
    async def _execute_tool_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具步骤"""
        tool_name = step.get('tool')
        if not tool_name:
            raise ValueError("工具步骤必须指定 tool 名称")
        
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            raise ValueError(f"工具未找到: {tool_name}")
        
        # 解析输入参数
        inputs = self._resolve_inputs(step.get('inputs', {}), context)
        
        # 执行工具
        tool_result = await tool.execute(inputs)
        
        if not tool_result.success:
            raise Exception(f"工具执行失败: {tool_result.error}")
        
        # 处理输出
        outputs = {}
        if 'outputs' in step:
            for output_key, output_expr in step['outputs'].items():
                # 从 tool_result.data 中提取字段
                if isinstance(output_expr, str) and output_expr.startswith('${result.'):
                    field = output_expr[9:-1]  # 移除 ${result. 和 }
                    outputs[output_key] = tool_result.data.get(field) if tool_result.data else None
                else:
                    outputs[output_key] = self._evaluate_expression(str(output_expr), context)
        
        return outputs
    
    async def _execute_llm_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行 LLM 调用步骤"""
        prompt = step.get('prompt', '')
        
        # 解析 prompt 中的变量
        resolved_prompt = self._evaluate_expression(prompt, context)
        
        # 调用 LLM
        response = await self.llm_service.chat(
            system_prompt="你是一个专业的AI助手，请根据用户的要求完成任务。",
            user_prompt=resolved_prompt
        )
        
        # 处理输出
        outputs = {}
        if 'outputs' in step:
            for output_key, output_expr in step['outputs'].items():
                if output_expr == '${result.text}':
                    outputs[output_key] = response
                else:
                    outputs[output_key] = self._evaluate_expression(str(output_expr), context)
        
        return outputs
    
    async def _execute_code_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行代码执行步骤"""
        code = step.get('code', '')
        if isinstance(code, str):
            # 对于多行代码字符串，先尝试解析变量，但如果解析后不是字符串，保持原样
            # 注意：代码中的 ${...} 表达式需要特殊处理，不能全部替换
            # 这里只替换明确的变量引用，保留代码结构
            resolved_code = code
            # 只替换明确的变量引用（如 ${input.field}, ${steps[N].field}）
            # 但不替换代码中的其他 ${...} 结构
            import re
            def replace_var_safe(match):
                var_expr = match.group(1)
                # 只替换明确的变量引用
                if var_expr.startswith('input.') or var_expr.startswith('steps[') or var_expr.startswith('config.'):
                    return self._evaluate_expression(f"${{{var_expr}}}", context)
                return match.group(0)  # 保持原样
            
            # 替换变量引用
            resolved_code = re.sub(r'\$\{(input\.|steps\[|config\.)([^}]+)\}', replace_var_safe, code)
        else:
            resolved_code = str(code) if code else ''
        
        # 使用 code_executor 工具执行代码
        code_executor = self.tool_registry.get_tool('execute_code')
        if not code_executor:
            raise ValueError("code_executor 工具未找到")
        
        # CodeExecutorTool 有 _execute_async 方法，直接调用
        if hasattr(code_executor, '_execute_async'):
            # 需要提供 language 参数
            tool_result = await code_executor._execute_async(
                code=resolved_code,
                language='python',
                timeout=300,
                explanation='技能工作流步骤：代码执行'
            )
        else:
            # 使用同步方法（在线程池中执行）
            import asyncio
            import concurrent.futures
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    code_executor.execute,
                    code=resolved_code,
                    language='python',
                    timeout=300
                )
                tool_result = await loop.run_in_executor(None, future.result)
        
        if not tool_result.success:
            raise Exception(f"代码执行失败: {tool_result.error}")
        
        # 处理输出
        outputs = {}
        if 'outputs' in step:
            for output_key, output_expr in step['outputs'].items():
                if output_expr == '${result.stdout}' or output_expr == '${result.output}':
                    # 从代码执行结果中提取输出
                    # 优先使用 output，如果没有则使用 stdout
                    if tool_result.data:
                        if 'output' in tool_result.data:
                            outputs[output_key] = tool_result.data['output']
                        elif 'stdout' in tool_result.data:
                            outputs[output_key] = tool_result.data['stdout']
                        else:
                            outputs[output_key] = ''
                    else:
                        outputs[output_key] = ''
                else:
                    outputs[output_key] = self._evaluate_expression(str(output_expr), context)
        
        return outputs
    
    async def execute_workflow(
        self,
        workflow: Dict[str, Any],
        parameters: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> SkillResult:
        """
        执行工作流
        
        Args:
            workflow: 工作流定义
            parameters: 技能参数
            config: 配置参数
        
        Returns:
            SkillResult: 执行结果
        """
        steps = workflow.get('steps', [])
        context = {
            'input': parameters,
            'config': config or {},
            'step_results': []
        }
        
        intermediate_results = {}
        
        try:
            for i, step in enumerate(steps):
                step_result = await self.execute_workflow_step(step, context, i)
                context['step_results'].append(step_result)
                
                # 保存中间结果
                step_name = step.get('name', f'step_{i}')
                intermediate_results[step_name] = step_result
            
            # 收集最终输出
            final_outputs = {}
            for i, step in enumerate(steps):
                if 'outputs' in step:
                    step_result = context['step_results'][i]
                    for output_key in step['outputs'].keys():
                        if output_key in step_result:
                            final_outputs[output_key] = step_result[output_key]
            
            return SkillResult(
                success=True,
                data=final_outputs,
                intermediate_results=intermediate_results
            )
        
        except Exception as e:
            logger.error(f"工作流执行失败: {e}", exc_info=True)
            return SkillResult(
                success=False,
                error=str(e),
                intermediate_results=intermediate_results
            )

