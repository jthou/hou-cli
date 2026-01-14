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
                    value = context['config'].get(field)
                    # 返回原始值，不转换为字符串
                    return value if value is not None else ''
                return ''
            
            # 直接变量
            if var_expr in context:
                # 返回原始值，不转换为字符串
                return context[var_expr]
            
            return ''
        
        # 检查表达式是否只包含一个变量引用（如 ${config.urls}）
        single_var_match = re.match(r'^\$\{([^}]+)\}$', expression.strip())
        if single_var_match:
            # 如果是单个变量引用，直接返回原始值
            var_expr = single_var_match.group(1)
            
            # 处理 steps[N].field
            match_steps = re.match(r'steps\[(\d+)\]\.(.+)', var_expr)
            if match_steps:
                step_idx = int(match_steps.group(1))
                field = match_steps.group(2)
                if 'step_results' in context and step_idx < len(context['step_results']):
                    step_result = context['step_results'][step_idx]
                    if isinstance(step_result, dict):
                        return step_result.get(field)
                return None
            
            # 处理 input.field
            if var_expr.startswith('input.'):
                field = var_expr[6:]
                if 'input' in context:
                    return context['input'].get(field)
                return None
            
            # 处理 config.field
            if var_expr.startswith('config.'):
                field = var_expr[7:]
                if 'config' in context:
                    return context['config'].get(field)
                return None
            
            # 直接变量
            if var_expr in context:
                return context[var_expr]
            
            return None
        
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
            elif step_type == 'loop':
                return await self._execute_loop_step(step, context)
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
        
        # 执行工具（注意：execute 方法接受 **kwargs，需要解包字典）
        # 检查工具是否有异步方法
        if hasattr(tool, '_execute_async'):
            tool_result = await tool._execute_async(**inputs)
        elif hasattr(tool, 'execute'):
            # 同步方法，需要在线程池中执行
            import asyncio
            import concurrent.futures
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(tool.execute, **inputs)
                tool_result = await loop.run_in_executor(None, future.result)
        else:
            raise ValueError(f"工具 {tool_name} 没有 execute 方法")
        
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
        
        # 注入变量到代码执行环境（input, config, context）
        # 这些变量需要在代码执行时可用，但不能与 Python 内置函数冲突
        # 解决方案：在代码开头注入变量定义，只注入可序列化的数据
        import json
        injection_code = []
        
        # 确保 json 模块已导入
        has_json_import = False
        
        # 注入 input 变量（从 context['input'] 获取）
        if 'input' in context:
            input_data = context['input']
            # 只序列化可序列化的数据
            try:
                # 尝试 JSON 序列化（只支持基本类型）
                input_json = json.dumps(input_data, ensure_ascii=False, default=str)
                if not has_json_import:
                    injection_code.append("import json")
                    has_json_import = True
                injection_code.append(f"input = json.loads({json.dumps(input_json)})")
            except:
                # 如果 JSON 序列化失败，创建一个空字典
                injection_code.append("input = {}")
        else:
            injection_code.append("input = {}")
        
        # 注入 config 变量（从 context['config'] 获取，如果不存在则创建空字典）
        if 'config' in context:
            config_data = context['config']
            # config 需要是可变的字典，使用 JSON 序列化
            try:
                config_json = json.dumps(config_data, ensure_ascii=False, default=str)
                if not has_json_import:
                    injection_code.append("import json")
                    has_json_import = True
                injection_code.append(f"config = json.loads({json.dumps(config_json)})")
            except:
                injection_code.append("config = {}")
        else:
            injection_code.append("config = {}")
        
        # 注入 steps 变量（从 context['step_results'] 或 context['steps'] 获取）
        # steps 用于在代码中访问之前步骤的结果
        steps_data = []
        if 'steps' in context:
            # 如果 context 中有 steps（循环步骤中的步骤结果）
            steps_data = context['steps']
        elif 'step_results' in context:
            # 否则使用 step_results
            steps_data = context['step_results']
        
        # 序列化 steps 数据
        try:
            steps_json = json.dumps(steps_data, ensure_ascii=False, default=str)
            if not has_json_import:
                injection_code.append("import json")
                has_json_import = True
            injection_code.append(f"steps = json.loads({json.dumps(steps_json)})")
        except:
            injection_code.append("steps = []")
        
        # 注入 context 变量（从 context 获取，但排除 input、config、step_results、steps 避免循环）
        # 只注入可序列化的基本类型，对象类型跳过（因为它们无法在独立执行环境中使用）
        # 但是，我们需要提供一个机制让代码可以访问 tool_registry
        context_data = {}
        for k, v in context.items():
            if k in ['input', 'config', 'step_results', 'steps']:
                continue
            # 只保留可序列化的基本类型
            if isinstance(v, (str, int, float, bool, type(None))):
                context_data[k] = v
            elif isinstance(v, (dict, list)):
                # 尝试序列化字典和列表（递归检查内容是否可序列化）
                try:
                    json.dumps(v, default=str)  # 测试是否可以序列化
                    context_data[k] = v
                except:
                    # 如果无法序列化，跳过（不转换为字符串，因为字符串表示无法使用）
                    pass
            # 对于对象类型（如 tool_registry, llm_service 等），完全跳过
            # 因为这些对象无法在独立的 subprocess 中使用
        
        # 特殊处理：为 tool_registry 创建一个代理机制
        # 在代码中，可以通过一个特殊的函数来调用工具
        # 由于代码在独立的 subprocess 中执行，我们需要通过代码注入来实现工具调用
        if 'tool_registry' in context:
            tool_registry = context['tool_registry']
            # 注入一个工具调用函数，通过序列化工具参数和结果来实现
            # 注意：这需要在代码执行时通过某种机制来实现
            # 暂时先跳过，后续可以通过修改代码执行逻辑来实现
            # 但是，我们可以通过修改代码来使用 tool 类型步骤，而不是在代码中直接调用工具
            pass
        
        # 序列化 context_data
        try:
            context_json = json.dumps(context_data, ensure_ascii=False, default=str)
            if not has_json_import:
                injection_code.append("import json")
                has_json_import = True
            injection_code.append(f"context = json.loads({json.dumps(context_json)})")
        except:
            # 如果序列化失败，创建最小化的 context
            context_minimal = {k: str(v) for k, v in context_data.items() if isinstance(v, (str, int, float, bool, type(None)))}
            if context_minimal:
                context_json = json.dumps(context_minimal, ensure_ascii=False)
                if not has_json_import:
                    injection_code.append("import json")
                    has_json_import = True
                injection_code.append(f"context = json.loads({json.dumps(context_json)})")
            else:
                injection_code.append("context = {}")
        
        # 特殊处理：如果代码中需要访问 tool_registry，我们需要注入一个工具调用机制
        # 由于代码在独立的 subprocess 中执行，无法直接访问对象
        # 我们通过注入一个工具调用函数来实现：通过 JSON 输出特殊标记，由 SkillExecutor 拦截并执行
        if 'tool_registry' in context:
            tool_registry = context['tool_registry']
            # 在代码开头注入一个工具调用函数
            # 这个函数会通过 JSON 输出特殊标记，SkillExecutor 会拦截并执行工具调用
            tool_call_code = """
import json
import sys

# 工具调用代理函数（通过 JSON 输出特殊标记）
def call_tool(tool_name, **kwargs):
    \"\"\"调用工具（通过 JSON 输出特殊标记）\"\"\"
    # 输出特殊标记，SkillExecutor 会拦截并执行
    call_request = {
        '__tool_call__': True,
        'tool_name': tool_name,
        'kwargs': kwargs
    }
    print(json.dumps(call_request, ensure_ascii=False))
    sys.stdout.flush()
    # 从 stdin 读取结果（SkillExecutor 会写入）
    # 注意：这需要 SkillExecutor 支持双向通信
    # 暂时返回占位符
    return {'success': False, 'error': '工具调用需要 SkillExecutor 支持'}

# 为了兼容性，提供一个占位符
tool_registry = None  # 在代码执行环境中不可用，请使用 call_tool() 函数
"""
            resolved_code = tool_call_code + "\n" + resolved_code
        
        # 将注入代码添加到代码开头
        if injection_code:
            resolved_code = "\n".join(injection_code) + "\n" + resolved_code
        
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
        
        # 处理工具调用请求（如果代码中调用了 call_tool）
        if tool_result.data:
            output_text = tool_result.data.get('output', '') or tool_result.data.get('stdout', '')
            if output_text:
                import json
                lines = output_text.strip().split('\n')
                tool_calls = []
                other_output = []
                
                # 解析输出，分离工具调用请求和其他输出
                for line in lines:
                    line = line.strip()
                    if line.startswith('{') and '__tool_call__' in line:
                        try:
                            call_request = json.loads(line)
                            if call_request.get('__tool_call__'):
                                tool_calls.append(call_request)
                                continue
                        except json.JSONDecodeError:
                            pass
                    other_output.append(line)
                
                # 执行工具调用
                if tool_calls and 'tool_registry' in context:
                    tool_registry = context['tool_registry']
                    tool_results = []
                    for call_request in tool_calls:
                        tool_name = call_request.get('tool_name')
                        kwargs = call_request.get('kwargs', {})
                        if tool_name:
                            try:
                                # 执行工具（同步调用，因为我们在异步上下文中）
                                tool = tool_registry.get_tool(tool_name)
                                if tool:
                                    # 使用 asyncio 执行异步工具
                                    import asyncio
                                    if hasattr(tool, 'execute'):
                                        # 同步工具
                                        result = tool.execute(**kwargs)
                                    elif hasattr(tool, '_execute_async'):
                                        # 异步工具
                                        result = asyncio.run(tool._execute_async(**kwargs))
                                    else:
                                        result = None
                                    tool_results.append({
                                        'tool_name': tool_name,
                                        'success': result.success if result else False,
                                        'data': result.data if result else None,
                                        'error': result.error if result and not result.success else None
                                    })
                                else:
                                    tool_results.append({
                                        'tool_name': tool_name,
                                        'success': False,
                                        'error': f"工具未找到: {tool_name}"
                                    })
                            except Exception as e:
                                tool_results.append({
                                    'tool_name': tool_name,
                                    'success': False,
                                    'error': str(e)
                                })
                    
                    # 将工具调用结果添加到 context，供代码使用
                    context['_tool_call_results'] = tool_results
                
                # 尝试从其他输出中解析 JSON（最终结果）
                parsed_result = None
                for line in reversed(other_output):
                    line = line.strip()
                    if line.startswith('{') or line.startswith('['):
                        try:
                            parsed_result = json.loads(line)
                            break
                        except json.JSONDecodeError:
                            continue
        
        # 将解析的结果添加到 context 中，供后续步骤使用
        if parsed_result:
            context['_code_result'] = parsed_result
            
            # 如果代码输出了 config_updates，同步更新 context['config']
            if 'config_updates' in parsed_result and 'config' in context:
                config_updates = parsed_result['config_updates']
                if isinstance(config_updates, dict):
                    context['config'].update(config_updates)
                    logger.debug(f"同步 config 更新: {list(config_updates.keys())}")
        
        # 处理输出
        outputs = {}
        if 'outputs' in step:
            for output_key, output_expr in step['outputs'].items():
                # 如果表达式是 ${result.field}，从解析的 JSON 中提取
                if parsed_result and output_expr.startswith('${result.'):
                    field = output_expr[9:-1]  # 移除 ${result. 和 }
                    if field in parsed_result:
                        outputs[output_key] = parsed_result[field]
                    else:
                        # 尝试使用点号分隔的嵌套字段
                        parts = field.split('.')
                        value = parsed_result
                        for part in parts:
                            if isinstance(value, dict) and part in value:
                                value = value[part]
                            else:
                                value = None
                                break
                        outputs[output_key] = value
                elif output_expr == '${result.stdout}' or output_expr == '${result.output}':
                    # 从代码执行结果中提取输出
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
    
    async def _execute_loop_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行循环步骤"""
        items = step.get('items')
        item_var = step.get('item_var', 'item')
        loop_steps = step.get('steps', [])
        
        if not items:
            logger.warning("循环步骤没有 items，跳过")
            return {}
        
        # 解析 items（可能是表达式）
        if isinstance(items, str):
            items = self._evaluate_expression(items, context)
        
        # 验证 items 是否为可迭代对象
        if items is None:
            logger.warning("循环步骤 items 解析为 None，跳过")
            return {}
        
        # 确保 items 是可迭代的
        if not isinstance(items, (list, tuple)):
            # 如果不是列表或元组，尝试转换为列表
            if isinstance(items, (str, int, float, bool)):
                # 基本类型，包装成列表
                items = [items]
            else:
                try:
                    # 尝试转换为列表
                    items = list(items)
                except (TypeError, ValueError) as e:
                    logger.error(f"循环步骤 items 无法转换为列表: {type(items)}, 错误: {e}")
                    return {}
        
        # 执行循环
        loop_results = []
        for i, item in enumerate(items):
            # 创建循环上下文
            loop_context = context.copy()
            loop_context[item_var] = item
            loop_context['_loop_index'] = i
            loop_context['_loop_total'] = len(items)
            
            # 执行循环内的步骤
            item_results = []
            for loop_step in loop_steps:
                try:
                    # 将之前的步骤结果添加到上下文中，供后续步骤使用
                    loop_context['steps'] = item_results
                    step_result = await self.execute_workflow_step(loop_step, loop_context, len(item_results))
                    item_results.append(step_result)
                    # 更新上下文中的步骤结果
                    loop_context['steps'] = item_results
                except Exception as e:
                    logger.error(f"循环步骤执行失败 (item {i}): {e}", exc_info=True)
                    error_result = {'error': str(e)}
                    item_results.append(error_result)
                    loop_context['steps'] = item_results
            
            loop_results.append({
                'item': item,
                'index': i,
                'results': item_results
            })
        
        # 处理输出
        outputs = {}
        if 'outputs' in step:
            for output_key, output_expr in step['outputs'].items():
                outputs[output_key] = self._evaluate_expression(str(output_expr), context)
        
        # 将循环结果添加到 context
        context['_loop_results'] = loop_results
        
        return outputs
    
    async def execute_workflow(
        self,
        workflow: Dict[str, Any],
        parameters: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
        external_context: Optional[Dict[str, Any]] = None
    ) -> SkillResult:
        """
        执行工作流
        
        Args:
            workflow: 工作流定义
            parameters: 技能参数
            config: 配置参数
            external_context: 外部上下文（包含 tool_registry, llm_service 等）
        
        Returns:
            SkillResult: 执行结果
        """
        steps = workflow.get('steps', [])
        context = {
            'input': parameters,
            'config': config or {},
            'step_results': []
        }
        
        # 合并外部上下文（如 tool_registry, llm_service 等）
        if external_context:
            context.update(external_context)
        
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

