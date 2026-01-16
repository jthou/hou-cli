"""技能执行器 - 执行技能工作流"""
import logging
import re
import os
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from backend.core.agent.skills.base import Skill, SkillResult
from backend.core.agent.tools.registry import ToolRegistry
from backend.services.llm.llm_service import LLMService

logger = logging.getLogger(__name__)

# 获取调试日志路径（相对于项目根目录）
# executor.py 在 backend/core/agent/skills/executor.py
# 项目根目录在 executor.py 的 ../../../../../
# 即: backend/core/agent/skills -> backend/core/agent -> backend/core -> backend -> 项目根目录
_DEBUG_LOG_PATH = Path(__file__).resolve().parent.parent.parent.parent.parent / '.cursor' / 'debug.log'


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
    
    def _is_simple_expression(self, expression: str) -> bool:
        """
        判断表达式是否简单（可以使用规则式求值）
        
        简单表达式特征：
        - 单个变量引用：${variable}
        - 简单的字段访问：${steps[0].field}, ${input.field}, ${config.field}
        - 不包含复杂逻辑运算符或嵌套表达式
        """
        if not expression or not isinstance(expression, str):
            return True
        
        # 检查是否包含复杂操作符
        complex_ops = [' and ', ' or ', ' not ', '==', '!=', '<', '>', '<=', '>=', 'file_exists(']
        if any(op in expression for op in complex_ops):
            return False
        
        # 检查嵌套深度（多个 ${}）
        import re
        matches = re.findall(r'\$\{[^}]+\}', expression)
        if len(matches) > 1:
            return False
        
        # 单个变量引用，简单
        return True
    
    async def _evaluate_expression_with_llm(self, expression: str, context: Dict[str, Any]) -> Any:
        """
        使用 LLM 求值表达式
        
        优势：
        - 可以理解复杂的表达式逻辑
        - 更好的错误处理
        - 更容易扩展新语法
        """
        import json
        
        logger.debug(f"[表达式求值-LLM] 开始求值表达式: {expression}")
        
        # 准备上下文信息（限制大小，避免 token 过多）
        context_info = {
            'input': context.get('input', {}),
            'config': context.get('config', {}),
            'step_results': context.get('step_results', [])[:5],  # 只取前5个步骤
        }
        
        prompt = f"""
根据以下上下文求值表达式：

表达式: {expression}

上下文:
- input: {json.dumps(context_info['input'], ensure_ascii=False, default=str)[:1000]}
- config: {json.dumps(context_info['config'], ensure_ascii=False, default=str)[:1000]}
- step_results: {json.dumps(context_info['step_results'], ensure_ascii=False, default=str)[:2000]}

支持的语法：
- ${{steps[N].field}}: 访问步骤结果（step_results 是列表，索引从 0 开始）
- ${{input.field}}: 访问输入参数
- ${{config.field}}: 访问配置参数
- ${{result.field}}: 访问工具执行结果
- ${{file_exists(path)}}: 文件存在检查（返回 True/False）
- 逻辑运算符: ==, !=, <, >, <=, >=, and, or, not
- 布尔值: true, false

重要规则：
1. 如果变量不存在或为 None，返回 None 或 False（根据上下文）
2. 布尔值比较时，注意类型转换（字符串 "true" 应视为 True）
3. 文件路径检查时，注意路径格式（可能包含引号）

请返回求值结果（JSON 格式）：
{{"result": <求值结果>, "type": "<结果类型: bool|int|float|str|None>"}}

只返回 JSON，不要包含其他说明文字。
"""
        
        try:
            response = await self.llm_service.chat(
                system_prompt="你是一个表达式求值专家。请根据上下文求值表达式，返回 JSON 格式的结果。确保结果类型正确（布尔值、数字、字符串等）。",
                user_prompt=prompt,
                model='bailian-kimi-k2-thinking'
            )
            
            # 解析响应
            # 尝试提取 JSON
            import re
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group(0))
                result = result_data.get('result')
                result_type = result_data.get('type', 'unknown')
                
                logger.debug(f"[表达式求值-LLM] 求值成功: {expression} -> {result} (type: {result_type})")
                
                # 根据类型转换结果
                if result_type == 'bool' and isinstance(result, str):
                    return result.lower() in ('true', '1', 'yes', 'on')
                elif result_type == 'int' and isinstance(result, str):
                    try:
                        return int(result)
                    except ValueError:
                        pass
                elif result_type == 'float' and isinstance(result, str):
                    try:
                        return float(result)
                    except ValueError:
                        pass
                
                return result
            else:
                # 如果没有找到 JSON，尝试直接解析响应
                logger.warning(f"[表达式求值-LLM] 无法从响应中提取 JSON: {response[:200]}")
                # 回退到规则式
                return None
                
        except Exception as e:
            logger.warning(f"[表达式求值-LLM] LLM 求值失败: {expression}, 错误: {e}")
            # 回退到规则式
            return None
    
    def _evaluate_expression(self, expression: str, context: Dict[str, Any]) -> Any:
        """
        计算表达式（简单的变量替换和条件判断）
        
        使用混合策略：
        - 简单表达式：使用规则式（快速）
        - 复杂表达式：使用 LLM（灵活）
        
        支持的语法：
        - ${variable} - 变量替换
        - ${steps[N].field} - 步骤结果字段
        - ${input.field} - 输入参数
        - ${file_exists(path)} - 文件存在检查
        - ${not condition} - 逻辑非
        """
        # #region agent log
        import json
        with open(str(_DEBUG_LOG_PATH), 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"H","location":"executor.py:45","message":"_evaluate_expression 开始","data":{"expression":expression,"has_config":"config" in context,"config_keys":list(context.get('config',{}).keys()) if 'config' in context else []},"timestamp":int(__import__('time').time()*1000)}) + '\n')
        # #endregion
        logger.debug(f"[表达式求值] 开始求值表达式: {expression}")
        logger.debug(f"[表达式求值] context keys: {list(context.keys())}")
        if 'step_results' in context:
            logger.debug(f"[表达式求值] step_results type: {type(context.get('step_results'))}, value: {context.get('step_results')}")
        if 'steps' in context:
            logger.debug(f"[表达式求值] steps type: {type(context.get('steps'))}, value: {context.get('steps')}")
        
        # 判断表达式复杂度
        is_simple = self._is_simple_expression(expression)
        logger.debug(f"[表达式求值] 表达式复杂度: {'简单' if is_simple else '复杂'}")
        
        # 简单表达式：使用规则式（快速）
        if is_simple:
            try:
                from backend.core.agent.utils.expression_utils import ExpressionEvaluator
                evaluator = ExpressionEvaluator(context)
                result = evaluator.evaluate(expression)
                logger.debug(f"[表达式求值] 规则式求值结果: {result}")
                return result
            except Exception as e:
                logger.warning(f"[表达式求值] 规则式求值失败，尝试 LLM: {e}")
                # 如果规则式失败，尝试 LLM
        
        # 复杂表达式：回退到规则式（LLM 调用需要在异步上下文中）
        # 注意：复杂表达式的 LLM 求值需要在异步方法中调用 _evaluate_expression_async
        logger.debug(f"[表达式求值] 复杂表达式，使用规则式求值: {expression}")
        
        # 回退到规则式（保留原有逻辑作为后备）
        try:
            from backend.core.agent.utils.expression_utils import ExpressionEvaluator
            evaluator = ExpressionEvaluator(context)
            result = evaluator.evaluate(expression)
            logger.debug(f"[表达式求值] 规则式求值结果: {result}")
            return result
        except Exception as e:
            logger.warning(f"[表达式求值] 规则式求值失败: {e}")
            # 回退到旧的实现（保留原有逻辑作为后备）
    
    async def _evaluate_expression_async(self, expression: str, context: Dict[str, Any]) -> Any:
        """
        异步版本的表达式求值（支持 LLM）
        
        在异步上下文中使用此方法，可以充分利用 LLM 求值复杂表达式
        """
        # 判断表达式复杂度
        is_simple = self._is_simple_expression(expression)
        logger.debug(f"[表达式求值-异步] 表达式复杂度: {'简单' if is_simple else '复杂'}")
        
        # 简单表达式：使用规则式（快速）
        if is_simple:
            try:
                from backend.core.agent.utils.expression_utils import ExpressionEvaluator
                evaluator = ExpressionEvaluator(context)
                result = evaluator.evaluate(expression)
                logger.debug(f"[表达式求值-异步] 规则式求值结果: {result}")
                return result
            except Exception as e:
                logger.warning(f"[表达式求值-异步] 规则式求值失败，尝试 LLM: {e}")
        
        # 复杂表达式：使用 LLM
        try:
            result = await self._evaluate_expression_with_llm(expression, context)
            if result is not None:
                logger.debug(f"[表达式求值-异步] LLM 求值结果: {result}")
                return result
        except Exception as e:
            logger.warning(f"[表达式求值-异步] LLM 求值失败，回退到规则式: {e}")
        
        # 回退到规则式
        try:
            from backend.core.agent.utils.expression_utils import ExpressionEvaluator
            evaluator = ExpressionEvaluator(context)
            result = evaluator.evaluate(expression)
            logger.debug(f"[表达式求值-异步] 规则式求值结果: {result}")
            return result
        except Exception as e:
            logger.warning(f"[表达式求值-异步] 规则式求值失败: {e}")
            return None
        
        # 替换变量（旧实现，作为后备）
        def replace_var(match):
            var_expr = match.group(1)
            
            # 处理 steps[N].field
            if var_expr.startswith('steps['):
                match_steps = re.match(r'steps\[(\d+)\]\.(.+)', var_expr)
                if match_steps:
                    step_idx = int(match_steps.group(1))
                    field = match_steps.group(2)
                    # #region agent log
                    import json
                    with open(str(_DEBUG_LOG_PATH), 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"executor.py:69","message":"replace_var: 访问 steps","data":{"step_idx":step_idx,"step_idx_type":str(type(step_idx)),"field":field,"has_step_results":"step_results" in context},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                    # #endregion
                    # 检查 step_results 是否存在且是列表
                    step_results = context.get('step_results') or context.get('steps')
                    # #region agent log
                    with open(str(_DEBUG_LOG_PATH), 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"executor.py:76","message":"replace_var: 获取 step_results","data":{"step_results_type":str(type(step_results)),"step_results_str":str(step_results)[:200] if step_results else None,"is_list":isinstance(step_results,(list,tuple))},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                    # #endregion
                    if step_results and isinstance(step_results, (list, tuple)):
                        # #region agent log
                        with open(str(_DEBUG_LOG_PATH), 'a') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"executor.py:76","message":"replace_var: 准备比较","data":{"step_idx":step_idx,"step_idx_type":str(type(step_idx)),"step_results_len":len(step_results),"step_results_len_type":str(type(len(step_results)))},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                        # #endregion
                        try:
                            if step_idx < len(step_results):
                                step_result = step_results[step_idx]
                                if isinstance(step_result, dict):
                                    return str(step_result.get(field, ''))
                        except TypeError as te:
                            # #region agent log
                            with open(str(_DEBUG_LOG_PATH), 'a') as f:
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"executor.py:76","message":"replace_var: 比较失败 - TypeError","data":{"error":str(te),"step_idx":step_idx,"step_idx_type":str(type(step_idx)),"step_results_len":len(step_results) if hasattr(step_results,'__len__') else "N/A"},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                            # #endregion
                            logger.error(f"[表达式求值] replace_var: 类型错误 - step_idx={step_idx} (type={type(step_idx)}), step_results len={len(step_results) if hasattr(step_results,'__len__') else 'N/A'}, error={te}")
                            raise
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
        # 但不包含比较操作符（==, !=, <, >, <=, >=）或逻辑操作符（and, or, not）
        single_var_match = re.match(r'^\$\{([^}]+)\}$', expression.strip())
        if single_var_match:
            var_expr = single_var_match.group(1)
            
            # 如果包含比较操作符或逻辑操作符，不是单个变量引用，继续下面的处理
            if any(op in var_expr for op in ['==', '!=', '<', '>', '<=', '>=', ' and ', ' or ', ' not ']):
                # 不是单个变量引用，继续下面的表达式求值
                pass
            else:
                # 是单个变量引用，直接返回原始值
                # 处理 steps[N].field
                match_steps = re.match(r'steps\[(\d+)\]\.(.+)', var_expr)
                if match_steps:
                    step_idx = int(match_steps.group(1))
                    field = match_steps.group(2)
                    # #region agent log
                    import json
                    with open(str(_DEBUG_LOG_PATH), 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"executor.py:141","message":"单个变量: 访问 steps","data":{"step_idx":step_idx,"step_idx_type":str(type(step_idx)),"field":field},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                    # #endregion
                    # 检查 step_results 是否存在且是列表
                    step_results = context.get('step_results') or context.get('steps')
                    # #region agent log
                    with open(str(_DEBUG_LOG_PATH), 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"executor.py:150","message":"单个变量: 获取 step_results","data":{"step_results_type":str(type(step_results)),"step_results_str":str(step_results)[:200] if step_results else None,"is_list":isinstance(step_results,(list,tuple))},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                    # #endregion
                    if step_results and isinstance(step_results, (list, tuple)):
                        # #region agent log
                        with open(str(_DEBUG_LOG_PATH), 'a') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"executor.py:155","message":"单个变量: 准备比较","data":{"step_idx":step_idx,"step_idx_type":str(type(step_idx)),"step_results_len":len(step_results),"step_results_len_type":str(type(len(step_results)))},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                        # #endregion
                        try:
                            if step_idx < len(step_results):
                                step_result = step_results[step_idx]
                                if isinstance(step_result, dict):
                                    return step_result.get(field)
                        except TypeError as te:
                            # #region agent log
                            with open(str(_DEBUG_LOG_PATH), 'a') as f:
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"executor.py:161","message":"单个变量: 比较失败 - TypeError","data":{"error":str(te),"step_idx":step_idx,"step_idx_type":str(type(step_idx)),"step_results_len":len(step_results) if hasattr(step_results,'__len__') else "N/A"},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                            # #endregion
                            logger.error(f"[表达式求值] 单个变量: 类型错误 - step_idx={step_idx} (type={type(step_idx)}), step_results len={len(step_results) if hasattr(step_results,'__len__') else 'N/A'}, error={te}")
                            raise
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
                        value = context['config'].get(field)
                        # #region agent log
                        import json
                        with open(str(_DEBUG_LOG_PATH), 'a') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"executor.py:186","message":"单个变量: 访问 config.field","data":{"field":field,"value":value,"value_type":str(type(value)) if value is not None else None,"config_keys":list(context['config'].keys())},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                        # #endregion
                        return value
                    return None
                
                # 处理 result.field（工具执行结果）
                if var_expr.startswith('result.'):
                    field = var_expr[7:]
                    if 'result' in context and isinstance(context['result'], dict):
                        return context['result'].get(field)
                    return None
                
                # 直接变量
                if var_expr in context:
                    return context[var_expr]
                
                return None
        
        # 替换所有 ${...} 表达式，但保留原始类型
        def replace_var_preserve_type(match):
            var_expr = match.group(1)
            
            # 如果 var_expr 包含比较操作符，这是一个表达式，需要分别替换其中的变量
            if any(op in var_expr for op in ['==', '!=', '<', '>', '<=', '>=', ' and ', ' or ', ' not ']):
                # 这是一个表达式，不是单个变量引用
                # 递归替换表达式中的变量部分
                # 例如：${steps[0].download_success == true} 
                # 应该替换为：True == True
                def replace_var_in_expr(expr):
                    """在表达式中替换变量"""
                    # 匹配 steps[N].field 模式
                    def replace_steps_var(m):
                        step_var = m.group(0)
                        logger.debug(f"[表达式求值] replace_steps_var: 匹配到 {step_var}")
                        # #region agent log
                        import json
                        with open(str(_DEBUG_LOG_PATH), 'a') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"executor.py:163","message":"replace_steps_var 开始","data":{"step_var":step_var},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                        # #endregion
                        step_match = re.match(r'steps\[(\d+)\]\.([^.==!<> ]+)', step_var)
                        if step_match:
                            step_idx_str = step_match.group(1)
                            step_idx = int(step_idx_str)
                            field = step_match.group(2)
                            logger.debug(f"[表达式求值] replace_steps_var: step_idx={step_idx}, field={field}")
                            # #region agent log
                            with open(str(_DEBUG_LOG_PATH), 'a') as f:
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"executor.py:169","message":"提取 step_idx 和 field","data":{"step_idx_str":step_idx_str,"step_idx":step_idx,"step_idx_type":str(type(step_idx)),"field":field},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                            # #endregion
                            step_results = context.get('step_results') or context.get('steps')
                            logger.debug(f"[表达式求值] replace_steps_var: step_results type={type(step_results)}, value={step_results}")
                            # #region agent log
                            with open(str(_DEBUG_LOG_PATH), 'a') as f:
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"executor.py:170","message":"获取 step_results","data":{"step_results_type":str(type(step_results)),"step_results_str":str(step_results)[:200],"is_list":isinstance(step_results,(list,tuple)),"has_step_results":"step_results" in context,"has_steps":"steps" in context},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                            # #endregion
                            if step_results and isinstance(step_results, (list, tuple)):
                                logger.debug(f"[表达式求值] replace_steps_var: step_results 是列表/元组，长度={len(step_results)}, step_idx={step_idx}, step_idx type={type(step_idx)}")
                                # #region agent log
                                with open(str(_DEBUG_LOG_PATH), 'a') as f:
                                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"executor.py:171","message":"准备比较 step_idx < len(step_results)","data":{"step_idx":step_idx,"step_idx_type":str(type(step_idx)),"step_results_len":len(step_results),"step_results_len_type":str(type(len(step_results)))},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                                # #endregion
                                try:
                                    comparison_result = step_idx < len(step_results)
                                    # #region agent log
                                    with open(str(_DEBUG_LOG_PATH), 'a') as f:
                                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"executor.py:171","message":"比较成功","data":{"comparison_result":comparison_result},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                                    # #endregion
                                except TypeError as te:
                                    # #region agent log
                                    with open(str(_DEBUG_LOG_PATH), 'a') as f:
                                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"executor.py:171","message":"比较失败 - TypeError","data":{"error":str(te),"step_idx":step_idx,"step_idx_type":str(type(step_idx)),"step_results_len":len(step_results) if hasattr(step_results,'__len__') else "N/A","step_results_len_type":str(type(len(step_results))) if hasattr(step_results,'__len__') else "N/A"},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                                    # #endregion
                                    raise
                                if step_idx < len(step_results):
                                    step_result = step_results[step_idx]
                                    logger.debug(f"[表达式求值] replace_steps_var: step_result[{step_idx}]={step_result}, type={type(step_result)}")
                                    if isinstance(step_result, dict):
                                        value = step_result.get(field)
                                        logger.debug(f"[表达式求值] replace_steps_var: value={value}, type={type(value)}")
                                        if isinstance(value, bool):
                                            result = 'True' if value else 'False'
                                            logger.debug(f"[表达式求值] replace_steps_var: 布尔值转换 {value} -> {result}")
                                            return result
                                        elif isinstance(value, str):
                                            if value.lower() == 'true':
                                                return 'True'
                                            elif value.lower() == 'false':
                                                return 'False'
                                            else:
                                                # 如果字符串值本身已经包含引号，移除外层引号（避免双重引号）
                                                # 然后使用 repr() 来正确转义字符串（用于表达式求值）
                                                clean_value = value
                                                if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
                                                    clean_value = value[1:-1]
                                                return repr(clean_value)
                                        elif isinstance(value, (int, float)):
                                            result = str(value)
                                            logger.debug(f"[表达式求值] replace_steps_var: 数字转换 {value} -> {result}")
                                            return result
                                        elif value is None:
                                            # #region agent log
                                            import json
                                            with open(str(_DEBUG_LOG_PATH), 'a') as f:
                                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E4","location":"executor.py:291","message":"replace_steps_var: value is None","data":{"step_idx":step_idx,"field":field,"step_result":str(step_result)[:200],"step_result_keys":list(step_result.keys()) if isinstance(step_result,dict) else None},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                                            # #endregion
                                            return 'None'
                                        else:
                                            return repr(value)
                                else:
                                    logger.warning(f"[表达式求值] replace_steps_var: step_idx {step_idx} >= len(step_results) {len(step_results)}")
                                    # #region agent log
                                    import json
                                    with open(str(_DEBUG_LOG_PATH), 'a') as f:
                                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E1","location":"executor.py:295","message":"replace_steps_var: step_idx >= len(step_results)","data":{"step_idx":step_idx,"step_results_len":len(step_results),"step_var":step_var},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                                    # #endregion
                            else:
                                logger.warning(f"[表达式求值] replace_steps_var: step_results 不是列表/元组: type={type(step_results)}, value={step_results}")
                                # #region agent log
                                import json
                                with open(str(_DEBUG_LOG_PATH), 'a') as f:
                                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E2","location":"executor.py:297","message":"replace_steps_var: step_results 不是列表/元组","data":{"step_results_type":str(type(step_results)),"step_results_str":str(step_results)[:200],"step_var":step_var},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                                # #endregion
                        # #region agent log
                        import json
                        with open(str(_DEBUG_LOG_PATH), 'a') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E3","location":"executor.py:299","message":"replace_steps_var: 返回原始 step_var","data":{"step_var":step_var,"step_match_found":step_match is not None if 'step_match' in locals() else False},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                        # #endregion
                        return step_var
                    
                    # 替换 steps[N].field
                    # #region agent log
                    import json
                    with open(str(_DEBUG_LOG_PATH), 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E5","location":"executor.py:301","message":"replace_var_in_expr: 准备替换 steps[N].field","data":{"expr_before":expr,"pattern":"steps[\\d+]\\.[^.==!<> ]+"},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                    # #endregion
                    expr = re.sub(r'steps\[\d+\]\.[^.==!<> ]+', replace_steps_var, expr)
                    # #region agent log
                    import json
                    with open(str(_DEBUG_LOG_PATH), 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E5","location":"executor.py:302","message":"replace_var_in_expr: 替换 steps[N].field 后","data":{"expr_after":expr},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                    # #endregion
                    
                    # 替换 true/false 字面量
                    expr = re.sub(r'\btrue\b', 'True', expr, flags=re.IGNORECASE)
                    expr = re.sub(r'\bfalse\b', 'False', expr, flags=re.IGNORECASE)
                    
                    # 替换 config.field, input.field, result.field
                    def replace_field_access(m):
                        field_expr = m.group(0)
                        if field_expr.startswith('config.'):
                            field = field_expr[7:]
                            if 'config' in context:
                                value = context['config'].get(field)
                                if isinstance(value, bool):
                                    return 'True' if value else 'False'
                                elif isinstance(value, str):
                                    if value.lower() == 'true':
                                        return 'True'
                                    elif value.lower() == 'false':
                                        return 'False'
                                    else:
                                        return repr(value)
                                elif isinstance(value, (int, float)):
                                    return str(value)
                                elif value is None:
                                    return 'None'
                                else:
                                    return repr(value)
                        elif field_expr.startswith('input.'):
                            field = field_expr[6:]
                            if 'input' in context:
                                value = context['input'].get(field)
                                if isinstance(value, bool):
                                    return 'True' if value else 'False'
                                elif isinstance(value, str):
                                    if value.lower() == 'true':
                                        return 'True'
                                    elif value.lower() == 'false':
                                        return 'False'
                                    else:
                                        # 如果字符串值本身已经包含引号，直接返回（避免双重引号）
                                        # 否则使用 repr() 来正确转义字符串
                                        if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
                                            # 字符串值已经带引号，直接返回（移除外层引号）
                                            return value[1:-1]
                                        else:
                                            return repr(value)
                                elif isinstance(value, (int, float)):
                                    return str(value)
                                elif value is None:
                                    return 'None'
                                else:
                                    return repr(value)
                        elif field_expr.startswith('result.'):
                            field = field_expr[7:]
                            if 'result' in context and isinstance(context['result'], dict):
                                value = context['result'].get(field)
                                if isinstance(value, bool):
                                    return 'True' if value else 'False'
                                elif isinstance(value, str):
                                    if value.lower() == 'true':
                                        return 'True'
                                    elif value.lower() == 'false':
                                        return 'False'
                                    else:
                                        # 如果字符串值本身已经包含引号，直接返回（避免双重引号）
                                        # 否则使用 repr() 来正确转义字符串
                                        if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
                                            # 字符串值已经带引号，直接返回（移除外层引号）
                                            return value[1:-1]
                                        else:
                                            return repr(value)
                                elif isinstance(value, (int, float)):
                                    return str(value)
                                elif value is None:
                                    return 'None'
                                else:
                                    return repr(value)
                        return field_expr
                    
                    expr = re.sub(r'(config|input|result)\.[^.==!<> ]+', replace_field_access, expr)
                    
                    return expr
                
                # 替换表达式中的变量
                return replace_var_in_expr(var_expr)
            
            # 处理单个变量引用（不包含比较操作符）
            # 处理 steps[N].field
            if var_expr.startswith('steps['):
                # 只匹配字段名部分，不包含比较操作符
                match_steps = re.match(r'steps\[(\d+)\]\.([^.==!<> ]+)', var_expr)
                if match_steps:
                    step_idx = int(match_steps.group(1))
                    field = match_steps.group(2)
                    # 检查 step_results 是否存在且是列表
                    step_results = context.get('step_results') or context.get('steps')
                    # #region agent log
                    import json
                    with open(str(_DEBUG_LOG_PATH), 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"executor.py:375","message":"获取 step_results (单个变量)","data":{"step_results_type":str(type(step_results)),"step_results_str":str(step_results)[:200],"is_list":isinstance(step_results,(list,tuple)),"has_step_results":"step_results" in context,"has_steps":"steps" in context,"step_idx":step_idx,"step_idx_type":str(type(step_idx))},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                    # #endregion
                    if step_results and isinstance(step_results, (list, tuple)):
                        # 确保 step_idx 是有效的整数
                        try:
                            # #region agent log
                            with open(str(_DEBUG_LOG_PATH), 'a') as f:
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"executor.py:295","message":"准备比较 step_idx < len(step_results) (单个变量)","data":{"step_idx":step_idx,"step_idx_type":str(type(step_idx)),"step_results_len":len(step_results),"step_results_len_type":str(type(len(step_results)))},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                            # #endregion
                            comparison_result = step_idx < len(step_results)
                            # #region agent log
                            with open(str(_DEBUG_LOG_PATH), 'a') as f:
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"executor.py:295","message":"比较成功 (单个变量)","data":{"comparison_result":comparison_result},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                            # #endregion
                            if comparison_result:
                                step_result = step_results[step_idx]
                                if isinstance(step_result, dict):
                                    value = step_result.get(field)
                                    # 处理布尔值：统一转换为 Python 布尔字面量
                                    if isinstance(value, bool):
                                        return 'True' if value else 'False'
                                    # 处理字符串 "true"/"false" -> True/False
                                    elif isinstance(value, str):
                                        if value.lower() == 'true':
                                            return 'True'
                                        elif value.lower() == 'false':
                                            return 'False'
                                        else:
                                            # 如果字符串值本身已经包含引号，移除外层引号（避免双重引号）
                                            # 然后直接返回原始值（不添加引号），因为这是单个变量引用，应该返回原始值
                                            clean_value = value
                                            if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
                                                clean_value = value[1:-1]
                                            return clean_value  # 单个变量引用返回原始值，不添加引号
                                    elif isinstance(value, (int, float)):
                                        return str(value)
                                    elif value is None:
                                        return 'None'
                                    else:
                                        return repr(value)
                        except (TypeError, IndexError, ValueError) as e:
                            logger.warning(f"访问 steps[{step_idx}].{field} 失败: {e}")
                    return 'None'
            
            # 处理 input.field
            if var_expr.startswith('input.'):
                field = var_expr[6:]
                if 'input' in context:
                    value = context['input'].get(field)
                    # 处理布尔值
                    if isinstance(value, bool):
                        return 'True' if value else 'False'
                    # 处理字符串 "true"/"false"
                    elif isinstance(value, str):
                        if value.lower() == 'true':
                            return 'True'
                        elif value.lower() == 'false':
                            return 'False'
                        else:
                            # 如果字符串值本身已经包含引号，直接返回（避免双重引号）
                            # 否则使用 repr() 来正确转义字符串
                            if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
                                # 字符串值已经带引号，直接返回（移除外层引号）
                                return value[1:-1]
                            else:
                                return repr(value)
                    elif isinstance(value, (int, float)):
                        return str(value)
                    elif value is None:
                        return 'None'
                    else:
                        return repr(value)
                return 'None'
            
            # 处理 config.field
            if var_expr.startswith('config.'):
                field = var_expr[7:]
                if 'config' in context:
                    value = context['config'].get(field)
                    # 处理布尔值
                    if isinstance(value, bool):
                        return 'True' if value else 'False'
                    # 处理字符串 "true"/"false"
                    elif isinstance(value, str):
                        if value.lower() == 'true':
                            return 'True'
                        elif value.lower() == 'false':
                            return 'False'
                        else:
                            # 如果字符串值本身已经包含引号，直接返回（避免双重引号）
                            # 否则使用 repr() 来正确转义字符串
                            if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
                                # 字符串值已经带引号，直接返回（移除外层引号）
                                return value[1:-1]
                            else:
                                return repr(value)
                    elif isinstance(value, (int, float)):
                        return str(value)
                    elif value is None:
                        return 'None'
                    else:
                        return repr(value)
                return 'None'
            
            # 处理 result.field（工具执行结果）
            if var_expr.startswith('result.'):
                field = var_expr[7:]
                if 'result' in context and isinstance(context['result'], dict):
                    value = context['result'].get(field)
                    # 处理布尔值
                    if isinstance(value, bool):
                        return 'True' if value else 'False'
                    # 处理字符串 "true"/"false"
                    elif isinstance(value, str):
                        if value.lower() == 'true':
                            return 'True'
                        elif value.lower() == 'false':
                            return 'False'
                        else:
                            # 如果字符串值本身已经包含引号，直接返回（避免双重引号）
                            # 否则使用 repr() 来正确转义字符串
                            if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
                                # 字符串值已经带引号，直接返回（移除外层引号）
                                return value[1:-1]
                            else:
                                return repr(value)
                    elif isinstance(value, (int, float)):
                        return str(value)
                    elif value is None:
                        return 'None'
                    else:
                        return repr(value)
                return 'None'
            
            # 处理布尔字面量
            if var_expr.lower() == 'true':
                return 'True'
            elif var_expr.lower() == 'false':
                return 'False'
            
            # 直接变量
            if var_expr in context:
                value = context[var_expr]
                # 处理布尔值
                if isinstance(value, bool):
                    return 'True' if value else 'False'
                # 处理字符串 "true"/"false"
                elif isinstance(value, str):
                    if value.lower() == 'true':
                        return 'True'
                    elif value.lower() == 'false':
                        return 'False'
                    else:
                        # 如果字符串值本身已经包含引号，直接返回（避免双重引号）
                        # 否则使用 repr() 来正确转义字符串
                        if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
                            # 字符串值已经带引号，直接返回（移除外层引号）
                            return value[1:-1]
                        else:
                            return repr(value)
                elif isinstance(value, (int, float)):
                    return str(value)
                elif value is None:
                    return 'None'
                else:
                    return repr(value)
            
            return 'None'
        
        # 替换所有 ${...} 表达式
        result = re.sub(r'\$\{([^}]+)\}', replace_var_preserve_type, expression)
        
        # 处理函数调用
        # file_exists(path)
        def replace_file_exists(match):
            path_str = match.group(1).strip('"\'')
            # 如果路径是 None 或空字符串，返回 False
            if not path_str or path_str == 'None':
                return 'False'
            try:
                path = Path(path_str)
                return 'True' if path.exists() else 'False'
            except Exception:
                return 'False'
        
        result = re.sub(r'file_exists\(([^)]+)\)', replace_file_exists, result)
        
        # 处理逻辑运算符（Python 语法）
        result = result.replace(' and ', ' and ').replace(' or ', ' or ').replace(' not ', ' not ')
        
        # 调试：记录替换后的表达式
        logger.debug(f"表达式求值: {expression} -> {result}")
        
        # 尝试安全地评估表达式
        logger.debug(f"[表达式求值] 替换后的表达式: {result}")
        try:
            # 只允许简单的比较和逻辑操作
            # 检查是否包含比较操作符
            has_comparison = any(op in result for op in ['==', '!=', '<', '>', '<=', '>=', ' and ', ' or ', ' not '])
            logger.debug(f"[表达式求值] 是否包含比较操作符: {has_comparison}")
            if has_comparison:
                # 在 eval 之前，尝试转换字符串数字为数字
                # 匹配引号内的字符串或数字
                def convert_literals(m):
                    """将字符串字面量转换为 Python 对象"""
                    s = m.group(0)
                    # 如果是引号字符串，保持原样
                    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
                        return s
                    # 如果是 True/False，保持原样
                    if s in ('True', 'False', 'None'):
                        return s
                    # 如果是数字字符串，保持原样（eval 会自动转换）
                    try:
                        float(s)
                        return s
                    except ValueError:
                        pass
                    return s
                
                # 使用 eval 但限制可用的内置函数
                safe_dict = {
                    'True': True,
                    'False': False,
                    'None': None,
                }
                # 安全地评估表达式
                try:
                    evaluated = eval(result, {"__builtins__": {}}, safe_dict)
                    # 确保返回布尔值用于条件判断
                    if isinstance(evaluated, bool):
                        return evaluated
                    elif isinstance(evaluated, (int, float)):
                        return bool(evaluated)
                    else:
                        # 如果不是布尔值，尝试转换为布尔值
                        return bool(evaluated)
                except TypeError as te:
                    # 类型错误，记录详细信息
                    logger.error(f"表达式类型错误: {expression} -> {result}, 错误: {te}")
                    # 尝试修复：将所有字符串转换为数字（如果可能）
                    raise ValueError(f"表达式类型不匹配: {result}")
                except Exception as e:
                    logger.error(f"表达式评估异常: {expression} -> {result}, 错误: {e}")
                    raise
            else:
                # 没有比较操作符，直接返回布尔值或原始值
                if result.strip().lower() in ('true', '1', 'yes', 'on'):
                    return True
                elif result.strip().lower() in ('false', '0', 'no', 'off', ''):
                    return False
                # 尝试转换为数字
                try:
                    if '.' in result:
                        return float(result)
                    else:
                        return int(result)
                except ValueError:
                    # 不是数字，返回字符串（去掉引号）
                    if result.startswith("'") and result.endswith("'"):
                        return result[1:-1]
                    elif result.startswith('"') and result.endswith('"'):
                        return result[1:-1]
                    return result
        except Exception as e:
            logger.warning(f"表达式评估失败: {expression} -> {result}, 错误: {e}")
            # 如果评估失败，返回原始表达式的字符串形式
            return result
    
    def _resolve_inputs(self, inputs: Dict[str, Any], context: Dict[str, Any], tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        解析输入参数
        
        使用统一的输入解析器，清晰地区分不同类型的参数：
        - CODE: 代码字符串，只替换变量引用，不进行表达式求值
        - EXPRESSION: 表达式字符串，进行表达式求值
        - LITERAL: 字面量，不进行任何处理
        
        Args:
            inputs: 原始输入参数
            context: 执行上下文
            tool_name: 工具名称（用于特殊处理）
            
        Returns:
            解析后的输入参数
        """
        from backend.core.agent.skills.utils.input_resolver import InputResolver
        
        resolver = InputResolver(context)
        resolved = resolver.resolve(inputs, tool_name)
        
        # 特殊处理：对于 code_executor 工具的 code 参数，只替换代码中的 ${...} 表达式
        # 而不是对整个代码字符串进行表达式求值
        if tool_name == 'execute_code' and 'code' in resolved:
            code_value = resolved['code']
            if isinstance(code_value, str) and '${' in code_value:
                # 代码字符串中包含 ${...} 表达式，需要替换
                import re
                
                def is_in_string_literal(code: str, pos: int):
                    """
                    检测位置 pos 是否在字符串字面量中
                    
                    Returns:
                        (是否在字符串中, 字符串引号类型: 'single'/'double'/'triple_single'/'triple_double'/None)
                    """
                    # 向前查找最近的引号
                    before = code[:pos]
                    
                    # 查找三引号字符串（优先级最高）
                    triple_double_before = before.rfind('"""')
                    triple_single_before = before.rfind("'''")
                    
                    # 查找最近的引号类型
                    last_triple = max(triple_double_before, triple_single_before)
                    if last_triple >= 0:
                        # 检查是否在三引号字符串中
                        after_triple = code[last_triple + 3:]
                        next_triple_double = after_triple.find('"""')
                        next_triple_single = after_triple.find("'''")
                        
                        # 检查下一个三引号是否在当前表达式之后
                        expr_start = pos
                        if triple_double_before >= triple_single_before:
                            if next_triple_double >= 0:
                                next_triple_pos = last_triple + 3 + next_triple_double
                                if next_triple_pos > expr_start:
                                    return True, 'triple_double'
                        else:
                            if next_triple_single >= 0:
                                next_triple_pos = last_triple + 3 + next_triple_single
                                if next_triple_pos > expr_start:
                                    return True, 'triple_single'
                    
                    # 查找单引号和双引号（需要排除三引号的情况）
                    # 简单方法：统计引号数量（奇数表示在字符串中）
                    single_quotes = before.count("'") - before.count("'''") * 3
                    double_quotes = before.count('"') - before.count('"""') * 3
                    
                    # 检查是否在单引号字符串中
                    if single_quotes % 2 == 1:
                        # 检查是否在三引号中（已处理）
                        if last_triple < 0 or triple_single_before < last_triple:
                            return True, 'single'
                    
                    # 检查是否在双引号字符串中
                    if double_quotes % 2 == 1:
                        # 检查是否在三引号中（已处理）
                        if last_triple < 0 or triple_double_before < last_triple:
                            return True, 'double'
                    
                    return False, None
                
                def replace_expr_in_code(match):
                    """替换代码中的表达式（上下文感知）"""
                    expr = match.group(0)  # 完整的 ${...} 表达式
                    expr_start = match.start()
                    
                    try:
                        from backend.core.agent.utils.expression_utils import ExpressionEvaluator
                        evaluator = ExpressionEvaluator(context)
                        result = evaluator.evaluate(expr)
                        
                        # 如果求值成功，替换为结果
                        if result is not None:
                            # 检测表达式是否在字符串字面量中
                            in_string, quote_type = is_in_string_literal(code_value, expr_start)
                            
                            if in_string:
                                # 在字符串字面量中：直接替换为值（不添加引号）
                                if isinstance(result, str):
                                    # 字符串：直接返回（已经在字符串字面量中）
                                    return result
                                elif isinstance(result, (dict, list)):
                                    # 字典或列表：序列化为 JSON 字符串（不添加引号）
                                    import json
                                    return json.dumps(result, ensure_ascii=False)
                                else:
                                    # 其他类型：转换为字符串
                                    return str(result)
                            else:
                                # 不在字符串字面量中：根据类型格式化（添加引号）
                                if isinstance(result, str):
                                    # 字符串：使用 repr 确保引号正确
                                    return repr(result)
                                elif isinstance(result, (dict, list)):
                                    # 字典或列表：使用 json.dumps（会添加引号）
                                    import json
                                    return json.dumps(result, ensure_ascii=False)
                                else:
                                    return repr(result)
                        else:
                            # 如果求值失败，保留原始表达式
                            logger.warning(f"代码中的表达式求值返回 None: {expr}，保留原始表达式")
                            return expr
                    except Exception as e:
                        logger.debug(f"替换代码中的表达式失败: {expr}, 错误: {e}，保留原始表达式")
                        return expr
                
                # 替换所有 ${...} 表达式
                resolved['code'] = re.sub(r'\$\{[^}]+\}', replace_expr_in_code, code_value)
                logger.debug(f"已替换代码中的表达式: {len(re.findall(r'\$\{[^}]+\}', code_value))} 个表达式")
        
        # #region agent log
        try:
            import json
            import time
            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"K","location":"executor.py:_resolve_inputs:after_resolve","message":"输入参数解析完成","data":{"tool_name":tool_name,"inputs_keys":list(inputs.keys()),"resolved_keys":list(resolved.keys()),"has_code":"code" in resolved,"code_type":type(resolved.get('code')).__name__ if 'code' in resolved else None},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                f.flush()
        except: pass
        # #endregion
        
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
        
        # #region agent log
        try:
            import json
            import time
            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"L","location":"executor.py:execute_workflow_step:entry","message":"执行工作流步骤","data":{"step_index":step_index,"step_name":step_name,"step_type":step_type,"has_condition":"condition" in step,"has_skip_if":"skip_if" in step,"has_skip_outputs":"skip_outputs" in step},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                f.flush()
        except: pass
        # #endregion
        
        try:
            # 检查条件
            if 'condition' in step:
                condition_expr = step['condition']
                logger.debug(f"[步骤执行] {step_name} 检查 condition: {condition_expr}")
                logger.debug(f"[步骤执行] {step_name} 当前 context: step_results type={type(context.get('step_results'))}, steps type={type(context.get('steps'))}")
                condition = await self._evaluate_expression_async(condition_expr, context)
                logger.debug(f"[步骤执行] {step_name} condition 结果: {condition}, type: {type(condition)}")
                
                # #region agent log
                try:
                    import json
                    import time
                    with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"L","location":"executor.py:execute_workflow_step:condition_check","message":"检查condition条件","data":{"step_name":step_name,"condition_expr":condition_expr,"condition_result":condition,"condition_type":type(condition).__name__},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                        f.flush()
                except: pass
                # #endregion
                
                if not condition:
                    logger.info(f"步骤 {step_name} 条件不满足，跳过")
                    # 处理 skip_outputs
                    if 'skip_outputs' in step:
                        skip_outputs = self._resolve_inputs(step['skip_outputs'], context)
                        # #region agent log
                        try:
                            import json
                            import time
                            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"L","location":"executor.py:execute_workflow_step:condition_false_skip_outputs","message":"condition不满足，使用skip_outputs","data":{"step_name":step_name,"skip_outputs":skip_outputs},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                                f.flush()
                        except: pass
                        # #endregion
                        return skip_outputs
                    return {}
            
            # 检查 skip_if
            if 'skip_if' in step:
                skip_expr = step['skip_if']
                logger.debug(f"[步骤执行] {step_name} 检查 skip_if: {skip_expr}")
                logger.debug(f"[步骤执行] {step_name} 当前 context: step_results type={type(context.get('step_results'))}, steps type={type(context.get('steps'))}")
                skip_condition = await self._evaluate_expression_async(skip_expr, context)
                logger.debug(f"[步骤执行] {step_name} skip_if 结果: {skip_condition}, type: {type(skip_condition)}")
                
                # #region agent log
                try:
                    import json
                    import time
                    with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"L","location":"executor.py:execute_workflow_step:skip_if_check","message":"检查skip_if条件","data":{"step_name":step_name,"skip_expr":skip_expr,"skip_condition_result":skip_condition,"skip_condition_type":type(skip_condition).__name__},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                        f.flush()
                except: pass
                # #endregion
                
                if skip_condition:
                    logger.info(f"步骤 {step_name} skip_if 条件满足，跳过")
                    if 'skip_outputs' in step:
                        skip_outputs = self._resolve_inputs(step['skip_outputs'], context)
                        # #region agent log
                        try:
                            import json
                            import time
                            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"L","location":"executor.py:execute_workflow_step:skip_if_true_skip_outputs","message":"skip_if条件满足，使用skip_outputs","data":{"step_name":step_name,"skip_outputs":skip_outputs},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                                f.flush()
                        except: pass
                        # #endregion
                        return skip_outputs
                    return {}
            
            # 根据步骤类型执行
            # conditional 类型的步骤实际上应该使用 tool 来执行
            if step_type == 'tool' or step_type == 'conditional':
                if step_type == 'conditional':
                    # conditional 类型必须有 tool 字段
                    if 'tool' not in step:
                        raise ValueError(f"conditional 类型的步骤必须指定 tool: {step_name}")
                    # #region agent log
                    try:
                        import json
                        import time
                        with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"L","location":"executor.py:execute_workflow_step:conditional_execute_tool","message":"conditional类型步骤，执行tool","data":{"step_name":step_name,"tool":step.get('tool')},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                            f.flush()
                    except: pass
                    # #endregion
                return await self._execute_tool_step(step, context)
            elif step_type == 'llm_call':
                return await self._execute_llm_step(step, context)
            elif step_type == 'code_executor' or step_type == 'llm_code_generator':
                # code_executor 已废弃，统一使用 llm_code_generator
                return await self._execute_llm_code_generator_step(step, context)
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
        
        # 工具名称映射（兼容技能 YAML 中的工具名称）
        tool_name_mapping = {
            'code_executor': 'execute_code',  # code_executor -> execute_code
        }
        actual_tool_name = tool_name_mapping.get(tool_name, tool_name)
        
        tool = self.tool_registry.get_tool(actual_tool_name)
        if not tool:
            raise ValueError(f"工具未找到: {tool_name} (映射为: {actual_tool_name})")
        
        # 解析输入参数（传入工具名称用于特殊处理）
        inputs = self._resolve_inputs(step.get('inputs', {}), context, tool_name=actual_tool_name)
        
        # #region agent log
        try:
            import json
            import time
            with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"I","location":"executor.py:_execute_tool_step:after_resolve_inputs","message":"解析输入参数后","data":{"tool_name":tool_name,"actual_tool_name":actual_tool_name,"inputs_keys":list(inputs.keys()),"has_language":"language" in inputs,"has_code":"code" in inputs,"code_type":type(inputs.get('code')).__name__ if 'code' in inputs else None,"code_is_none":inputs.get('code') is None if 'code' in inputs else None},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                f.flush()
        except: pass
        # #endregion
        
        # 验证必需参数（特别是 code_executor 工具的 code 参数）
        if actual_tool_name == 'execute_code':
            code_value = inputs.get('code')
            if not code_value or (isinstance(code_value, str) and not code_value.strip()):
                error_msg = f"code_executor 工具的 code 参数无效: {code_value}"
                logger.error(error_msg)
                # #region agent log
                try:
                    import json
                    import time
                    with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"K","location":"executor.py:_execute_tool_step:code_validation_failed","message":"code参数验证失败","data":{"code_value":str(code_value)[:200] if code_value else None,"code_type":type(code_value).__name__ if code_value else None,"original_inputs":str(step.get('inputs', {}).get('code', ''))[:200]},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                        f.flush()
                except: pass
                # #endregion
                raise ValueError(error_msg)
        
        # 特殊处理：code_executor 工具需要 language 参数，如果缺失则设置默认值
        if actual_tool_name == 'execute_code' and 'language' not in inputs:
            # #region agent log
            try:
                import json
                import time
                with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"I","location":"executor.py:_execute_tool_step:before_add_language","message":"检测到缺少language参数，准备添加默认值","data":{"tool_name":tool_name,"actual_tool_name":actual_tool_name},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                    f.flush()
            except: pass
            # #endregion
            # 从代码内容推断语言，或使用默认值 python
            code = inputs.get('code', '')
            if isinstance(code, str):
                # 检查代码中的关键字来推断语言
                if any(keyword in code for keyword in ['import ', 'from ', 'def ', 'class ', 'print(']):
                    inputs['language'] = 'python'
                else:
                    # 默认使用 python（因为大多数技能代码都是 Python）
                    inputs['language'] = 'python'
            else:
                inputs['language'] = 'python'
            # #region agent log
            try:
                import json
                import time
                with open('/home/robo/justin/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"I","location":"executor.py:_execute_tool_step:after_add_language","message":"已添加language参数","data":{"language":inputs.get('language'),"inputs_keys":list(inputs.keys())},"timestamp":int(time.time()*1000)}, ensure_ascii=False) + '\n')
                    f.flush()
            except: pass
            # #endregion
        
        # 如果 context 中有 progress_callback，传递给工具（如果工具支持）
        if 'progress_callback' in context and hasattr(tool, 'set_progress_callback'):
            tool.set_progress_callback(context['progress_callback'])
        
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
            # 创建包含 tool_result 的上下文
            result_context = context.copy()
            result_context['result'] = {
                'success': tool_result.success,  # 确保 success 是布尔值
                'data': tool_result.data or {},
                'error': tool_result.error
            }
            
            for output_key, output_expr in step['outputs'].items():
                # 从 tool_result 中提取字段
                if isinstance(output_expr, str) and output_expr.startswith('${result.'):
                    field = output_expr[9:-1]  # 移除 ${result. 和 }
                    # 优先从 result 字典获取（包含 success, data, error）
                    if field in result_context['result']:
                        value = result_context['result'][field]
                        # 确保布尔值保持为布尔类型
                        outputs[output_key] = value
                    elif tool_result.data and field in tool_result.data:
                        value = tool_result.data[field]
                        # 确保布尔值保持为布尔类型
                        outputs[output_key] = value
                    else:
                        outputs[output_key] = None
                else:
                    outputs[output_key] = await self._evaluate_expression_async(str(output_expr), result_context)
        
        return outputs
    
    async def _execute_llm_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行 LLM 调用步骤"""
        # 优先从 inputs 中获取（标准格式），如果没有则从 step 中获取（向后兼容）
        inputs = step.get('inputs', {})
        prompt = step.get('prompt', '') or inputs.get('prompt', '')
        
        # 解析 prompt 中的变量
        resolved_prompt = await self._evaluate_expression_async(prompt, context)
        
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
                    outputs[output_key] = await self._evaluate_expression_async(str(output_expr), context)
        
        return outputs
    
    async def _execute_llm_code_generator_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行 LLM 代码生成步骤（替代静态代码执行）"""
        import json
        
        # 1. 获取 prompt 和 code（code 可能在 inputs 中，也可能直接在 step 中）
        # 优先从 inputs 中获取（标准格式），如果没有则从 step 中获取（向后兼容）
        inputs = step.get('inputs', {})
        prompt = step.get('prompt', '') or inputs.get('prompt', '')
        code = step.get('code', '') or inputs.get('code', '')
        
        # 如果提供了 code，说明是旧的 code_executor 格式，需要转换为 prompt
        if code and not prompt:
            # 先替换代码中的表达式（${...} 语法）
            # 使用正则表达式替换代码中的所有 ${...} 表达式（上下文感知）
            import re
            resolved_code = code
            
            def is_in_string_literal(code: str, pos: int):
                """
                检测位置 pos 是否在字符串字面量中
                
                Returns:
                    (是否在字符串中, 字符串引号类型: 'single'/'double'/'triple_single'/'triple_double'/None)
                """
                # 向前查找最近的引号
                before = code[:pos]
                
                # 查找三引号字符串（优先级最高）
                triple_double_before = before.rfind('"""')
                triple_single_before = before.rfind("'''")
                
                # 查找最近的引号类型
                last_triple = max(triple_double_before, triple_single_before)
                if last_triple >= 0:
                    # 检查是否在三引号字符串中
                    after_triple = code[last_triple + 3:]
                    next_triple_double = after_triple.find('"""')
                    next_triple_single = after_triple.find("'''")
        
                    # 检查下一个三引号是否在当前表达式之后
                    expr_start = pos
                    if triple_double_before >= triple_single_before:
                        if next_triple_double >= 0:
                            next_triple_pos = last_triple + 3 + next_triple_double
                            if next_triple_pos > expr_start:
                                return True, 'triple_double'
                    else:
                        if next_triple_single >= 0:
                            next_triple_pos = last_triple + 3 + next_triple_single
                            if next_triple_pos > expr_start:
                                return True, 'triple_single'
                
                # 查找单引号和双引号（需要排除三引号的情况）
                # 简单方法：统计引号数量（奇数表示在字符串中）
                single_quotes = before.count("'") - before.count("'''") * 3
                double_quotes = before.count('"') - before.count('"""') * 3
                
                # 检查是否在单引号字符串中
                if single_quotes % 2 == 1:
                    # 检查是否在三引号中（已处理）
                    if last_triple < 0 or triple_single_before < last_triple:
                        return True, 'single'
                
                # 检查是否在双引号字符串中
                if double_quotes % 2 == 1:
                    # 检查是否在三引号中（已处理）
                    if last_triple < 0 or triple_double_before < last_triple:
                        return True, 'double'
                
                return False, None
            
            def replace_expr_in_code(match):
                """替换代码中的表达式（上下文感知）"""
                expr = match.group(0)  # 完整的 ${...} 表达式
                expr_start = match.start()
                
                try:
                    # 使用同步版本的表达式求值（因为这是在字符串替换中）
                    from backend.core.agent.utils.expression_utils import ExpressionEvaluator
                    evaluator = ExpressionEvaluator(context)
                    result = evaluator.evaluate(expr)
                    
                    # 如果求值成功，替换为结果
                    if result is not None:
                        # 检测表达式是否在字符串字面量中
                        in_string, quote_type = is_in_string_literal(code, expr_start)
                        
                        if in_string:
                            # 在字符串字面量中：直接替换为值（不添加引号）
                            if isinstance(result, str):
                                # 字符串：直接返回（已经在字符串字面量中）
                                return result
                            elif isinstance(result, (dict, list)):
                                # 字典或列表：序列化为 JSON 字符串（不添加引号）
                                import json
                                return json.dumps(result, ensure_ascii=False)
                            else:
                                # 其他类型：转换为字符串
                                return str(result)
                        else:
                            # 不在字符串字面量中：根据类型格式化（添加引号）
                            if isinstance(result, str):
                                # 字符串：使用 repr 确保引号正确
                                return repr(result)
                            elif isinstance(result, (dict, list)):
                                # 字典或列表：使用 json.dumps（会添加引号）
                                import json
                                return json.dumps(result, ensure_ascii=False)
                            else:
                                return repr(result)
                    else:
                        # 如果求值失败，保留原始表达式
                        logger.warning(f"代码中的表达式求值返回 None: {expr}，保留原始表达式")
                        return expr
                except Exception as e:
                    logger.debug(f"替换代码中的表达式失败: {expr}, 错误: {e}，保留原始表达式")
                    return expr
            
            # 替换所有 ${...} 表达式
            resolved_code = re.sub(r'\$\{[^}]+\}', replace_expr_in_code, resolved_code)
            
            # 将静态代码转换为 prompt，让 LLM 理解任务并生成代码
            prompt = f"""
请根据以下代码逻辑生成 Python 代码来完成相同的任务。

原始代码（已替换变量）：
```python
{resolved_code}
```

任务说明：
- 这段代码需要处理输入参数和上下文数据
- 请生成功能相同的代码，但使用更健壮的错误处理
- 代码应该返回 JSON 格式的结果
- 重要：代码中应该直接使用变量名（如 input, steps），而不是使用 ${{...}} 语法

可用变量（已注入到执行环境，直接使用即可）：
- input: 输入参数（字典）
- steps: 之前步骤的结果（列表）
- config: 配置信息（字典）
"""
        
        if not prompt:
            raise ValueError("llm_code_generator 步骤必须提供 prompt 或 code 参数")
        
        # 2. 解析 prompt 中的变量（如果 prompt 中还有 ${...} 表达式）
        resolved_prompt = await self._evaluate_expression_async(prompt, context)
        
        # 3. 构建完整的 prompt（包含上下文信息）
        context_info = {
            'input': context.get('input', {}),
            'steps': context.get('step_results', []),
            'config': context.get('config', {})
        }
        
        full_prompt = f"""
{resolved_prompt}

可用变量（已注入到执行环境，直接使用即可）：
- input: {json.dumps(context_info['input'], ensure_ascii=False, default=str)[:500]}
- steps: 之前步骤的结果列表（长度为 {len(context_info['steps'])}）
- config: {json.dumps(context_info['config'], ensure_ascii=False, default=str)[:500]}

代码要求：
1. 使用上述变量（不需要导入，它们已经在作用域中）
2. 返回 JSON 格式的结果（使用 json.dumps）
3. 包含详细的错误处理和异常捕获
4. 代码应该可以直接执行，不需要额外的依赖
5. 如果遇到错误，返回包含 'error' 字段的字典

请只返回 Python 代码，不要包含其他说明文字。
"""
        
        # 4. 调用 LLM 生成代码
        # 优先从 inputs 中获取（标准格式），如果没有则从 step 中获取（向后兼容）
        model = inputs.get('model') or step.get('model', 'bailian-kimi-k2-thinking')
        logger.info(f"🎯 选择代码生成模型: {model}")

        # 先设置模型，然后调用 chat
        self.llm_service.set_model(model)
        response = await self.llm_service.chat(
            system_prompt="你是一个专业的 Python 代码生成专家。请根据用户的需求生成可执行的 Python 代码。代码应该健壮、包含错误处理，并返回 JSON 格式的结果。",
            user_prompt=full_prompt
        )
        
        # 5. 提取代码（从 markdown code block 中提取）
        generated_code = self._extract_code_from_response(response)
        
        if not generated_code:
            raise ValueError(f"LLM 未能生成有效代码。响应: {response[:200]}")
        
        logger.debug(f"生成的代码:\n{generated_code[:500]}")
        
        # 6. 准备执行环境（注入变量）
        execution_code = self._prepare_execution_environment(context, generated_code)
        
        # 7. 执行代码
        code_executor = self.tool_registry.get_tool('execute_code')
        if not code_executor:
            raise ValueError("execute_code 工具未找到")
        
        if hasattr(code_executor, '_execute_async'):
            tool_result = await code_executor._execute_async(
                code=execution_code,
                language='python',
                timeout=300,
                explanation='LLM 生成的代码执行'
            )
        else:
            import asyncio
            import concurrent.futures
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    code_executor.execute,
                    code=execution_code,
                    language='python',
                    timeout=300
                )
                tool_result = await loop.run_in_executor(None, future.result)
        
        if not tool_result.success:
            error_msg = tool_result.error or "代码执行失败"
            logger.error(f"代码执行失败: {error_msg}")
            logger.error(f"生成的代码:\n{generated_code}")
            raise Exception(f"代码执行失败: {error_msg}")
        
        # 8. 解析输出（JSON）
        output_text = tool_result.data.get('output', '') or tool_result.data.get('stdout', '')
        parsed_result = self._parse_json_output(output_text)
        
        # 9. 处理输出
        outputs = {}
        if 'outputs' in step:
            for output_key, output_expr in step['outputs'].items():
                # 构建包含 result 的上下文
                result_context = {'result': parsed_result, **context}
                outputs[output_key] = await self._evaluate_expression_async(
                    str(output_expr), 
                    result_context
                )
        else:
            # 如果没有定义 outputs，将整个 parsed_result 作为输出
            outputs = parsed_result if isinstance(parsed_result, dict) else {'result': parsed_result}
        
        return outputs
    
    def _extract_code_from_response(self, response: str) -> str:
        """从 LLM 响应中提取代码"""
        import re
        
        # 方法1: 提取 markdown code block 中的代码
        pattern = r'```(?:python)?\n?(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            code = matches[0].strip()
            if code:
                return code
        
        # 方法2: 如果没有 code block，尝试提取代码行（以 import 或 def 开头）
        lines = response.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            stripped = line.strip()
            # 检测代码开始
            if (stripped.startswith('import ') or 
                stripped.startswith('from ') or 
                stripped.startswith('def ') or 
                stripped.startswith('class ') or
                stripped.startswith('#') or
                (stripped and not stripped.startswith('请'))):
                in_code = True
            
            if in_code:
                code_lines.append(line)
        
        if code_lines:
            code = '\n'.join(code_lines).strip()
            if code:
                return code
        
        # 方法3: 如果都没有，返回整个响应（可能是纯代码）
        return response.strip()
    
    def _prepare_execution_environment(self, context: Dict[str, Any], code: str) -> str:
        """准备代码执行环境（注入变量）"""
        import json
        
        injection = []
        has_json_import = False
        
        # 注入 input
        if 'input' in context:
            try:
                input_json = json.dumps(context['input'], ensure_ascii=False, default=str)
                if not has_json_import:
                    injection.append("import json")
                    has_json_import = True
                injection.append(f"input = json.loads({json.dumps(input_json)})")
            except Exception as e:
                logger.warning(f"序列化 input 失败: {e}")
                injection.append("input = {}")
        else:
            injection.append("input = {}")
        
        # 注入 steps
        steps_data = context.get('step_results', context.get('steps', []))
        try:
            steps_json = json.dumps(steps_data, ensure_ascii=False, default=str)
            if not has_json_import:
                injection.append("import json")
                has_json_import = True
            injection.append(f"steps = json.loads({json.dumps(steps_json)})")
        except Exception as e:
            logger.warning(f"序列化 steps 失败: {e}")
            injection.append("steps = []")
        
        # 注入 config
        if 'config' in context:
            try:
                config_json = json.dumps(context['config'], ensure_ascii=False, default=str)
                if not has_json_import:
                    injection.append("import json")
                    has_json_import = True
                injection.append(f"config = json.loads({json.dumps(config_json)})")
            except Exception as e:
                logger.warning(f"序列化 config 失败: {e}")
                injection.append("config = {}")
        else:
            injection.append("config = {}")
        
        # 组合代码
        return '\n'.join(injection) + '\n\n' + code
    
    def _parse_json_output(self, output_text: str) -> Dict[str, Any]:
        """解析代码输出的 JSON"""
        import json
        import re
        
        if not output_text:
            return {}
        
        # 尝试从输出中提取 JSON
        lines = output_text.strip().split('\n')
        for line in reversed(lines):
            line = line.strip()
            if line.startswith('{') or line.startswith('['):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        
        # 如果没有找到完整的 JSON，尝试提取 JSON 对象（可能跨多行）
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, output_text, re.DOTALL)
        for match in reversed(matches):
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        # 如果都没有找到，返回空字典
        logger.warning(f"无法从输出中解析 JSON: {output_text[:200]}")
        return {}
    
    async def _execute_loop_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行循环步骤"""
        # 优先从 inputs 中获取（标准格式），如果没有则从 step 中获取（向后兼容）
        inputs = step.get('inputs', {})
        items = step.get('items') or inputs.get('items')
        item_var = step.get('item_var') or inputs.get('item_var', 'item')
        loop_steps = step.get('steps', [])
        
        if not items:
            logger.warning("循环步骤没有 items，跳过")
            return {}
        
        # 解析 items（可能是表达式）
        if isinstance(items, str):
            # #region agent log
            import json
            with open(str(_DEBUG_LOG_PATH), 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"executor.py:1136","message":"循环步骤: 开始解析 items","data":{"items_expr":items,"has_config":"config" in context,"config_keys":list(context.get('config',{}).keys()) if 'config' in context else []},"timestamp":int(__import__('time').time()*1000)}) + '\n')
            # #endregion
            # #region agent log
            if 'config' in context:
                config = context.get('config', {})
                with open(str(_DEBUG_LOG_PATH), 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"executor.py:1140","message":"循环步骤: 检查 config","data":{"config_urls":config.get('urls'),"config_urls_type":str(type(config.get('urls'))) if 'urls' in config else None,"config_keys":list(config.keys())},"timestamp":int(__import__('time').time()*1000)}) + '\n')
            # #endregion
            items = await self._evaluate_expression_async(items, context)
            # #region agent log
            with open(str(_DEBUG_LOG_PATH), 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"executor.py:1128","message":"循环步骤: items 解析结果","data":{"items_type":str(type(items)),"items_value":str(items)[:200] if items else None,"is_list":isinstance(items,(list,tuple))},"timestamp":int(__import__('time').time()*1000)}) + '\n')
            # #endregion
        
        # 验证 items 是否为可迭代对象
        if items is None:
            logger.warning("循环步骤 items 解析为 None，跳过")
            return {}
        
        # 确保 items 是可迭代的
        if not isinstance(items, (list, tuple)):
            # #region agent log
            with open(str(_DEBUG_LOG_PATH), 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"executor.py:1135","message":"循环步骤: items 不是列表/元组，尝试转换","data":{"items_type":str(type(items)),"items_value":str(items)[:200]},"timestamp":int(__import__('time').time()*1000)}) + '\n')
            # #endregion
            # 如果不是列表或元组，尝试转换为列表
            if isinstance(items, (str, int, float, bool)):
                # 基本类型，包装成列表
                items = [items]
            else:
                try:
                    # 尝试转换为列表
                    items = list(items)
                except (TypeError, ValueError) as e:
                    # #region agent log
                    with open(str(_DEBUG_LOG_PATH), 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"executor.py:1142","message":"循环步骤: items 转换失败","data":{"items_type":str(type(items)),"error":str(e)},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                    # #endregion
                    logger.error(f"循环步骤 items 无法转换为列表: {type(items)}, 错误: {e}")
                    return {}
        
        # #region agent log
        with open(str(_DEBUG_LOG_PATH), 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"executor.py:1148","message":"循环步骤: 准备遍历 items","data":{"items_len":len(items) if hasattr(items,'__len__') else "N/A","items_type":str(type(items))},"timestamp":int(__import__('time').time()*1000)}) + '\n')
        # #endregion
        
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
            # #region agent log
            import json
            with open(str(_DEBUG_LOG_PATH), 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"executor.py:1159","message":"循环步骤开始","data":{"loop_index":i,"item":str(item)[:100],"item_results_len":len(item_results)},"timestamp":int(__import__('time').time()*1000)}) + '\n')
            # #endregion
            for loop_step in loop_steps:
                try:
                    # 将之前的步骤结果添加到上下文中，供后续步骤使用
                    loop_context['steps'] = item_results
                    # #region agent log
                    with open(str(_DEBUG_LOG_PATH), 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"executor.py:1190","message":"设置 loop_context['steps']","data":{"steps_type":str(type(item_results)),"steps_len":len(item_results),"steps_content":str(item_results)[:200]},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                    # #endregion
                    step_result = await self.execute_workflow_step(loop_step, loop_context, len(item_results))
                    item_results.append(step_result)
                    # 更新上下文中的步骤结果
                    loop_context['steps'] = item_results
                    # #region agent log
                    with open(str(_DEBUG_LOG_PATH), 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"executor.py:1198","message":"更新 loop_context['steps']","data":{"steps_type":str(type(item_results)),"steps_len":len(item_results),"step_result_type":str(type(step_result)),"step_result":str(step_result)[:200]},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                    # #endregion
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
                outputs[output_key] = await self._evaluate_expression_async(str(output_expr), context)
        
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
            logger.error(f"[工作流执行] 工作流执行失败: {type(e).__name__}: {e}", exc_info=True)
            logger.error(f"[工作流执行] 错误详情: 类型={type(e).__name__}, 消息={str(e)}")
            logger.error(f"[工作流执行] 当前 context keys: {list(context.keys())}")
            logger.error(f"[工作流执行] step_results type={type(context.get('step_results'))}, step_results={context.get('step_results')}")
            logger.error(f"[工作流执行] steps type={type(context.get('steps'))}, steps={context.get('steps')}")
            if 'step_results' in context:
                step_results = context['step_results']
                if step_results:
                    logger.error(f"[工作流执行] step_results 长度: {len(step_results) if hasattr(step_results, '__len__') else 'N/A'}")
                    if isinstance(step_results, (list, tuple)) and len(step_results) > 0:
                        logger.error(f"[工作流执行] step_results[0]: {step_results[0]}, type: {type(step_results[0])}")
            # 提取错误信息：只取错误类型和消息，不包含完整的 traceback
            error_msg = f"{type(e).__name__}: {str(e)}"
            # 如果错误信息为空，使用默认消息
            if not str(e):
                error_msg = f"{type(e).__name__} occurred"
            logger.error(f"[工作流执行] 返回错误信息: {error_msg}")
            return SkillResult(
                success=False,
                error=error_msg,
                intermediate_results=intermediate_results
            )

