"""
统一的输入参数解析器
清晰地区分不同类型的参数，采用不同的处理策略
"""
import re
import logging
from typing import Dict, Any, Optional, Union
from enum import Enum

logger = logging.getLogger(__name__)


class InputType(Enum):
    """输入参数类型枚举"""
    LITERAL = "literal"  # 字面量，不进行任何处理
    EXPRESSION = "expression"  # 表达式，需要进行表达式求值
    CODE = "code"  # 代码字符串，只替换变量引用，不进行表达式求值


class InputResolver:
    """
    输入参数解析器
    
    设计原则：
    1. 根据参数类型和上下文，自动识别参数的处理方式
    2. 代码字符串：只替换变量引用，不进行表达式求值
    3. 表达式字符串：进行表达式求值
    4. 字面量字符串：直接使用，不进行任何处理
    """
    
    def __init__(self, context: Dict[str, Any]):
        """
        初始化输入解析器
        
        Args:
            context: 执行上下文，包含 input, config, step_results 等
        """
        self.context = context
    
    def resolve(self, inputs: Dict[str, Any], tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        解析输入参数
        
        Args:
            inputs: 原始输入参数
            tool_name: 工具名称（用于特殊处理，如 code_executor）
            
        Returns:
            解析后的输入参数
        """
        resolved = {}
        
        for key, value in inputs.items():
            # 确定参数的处理类型
            input_type = self._determine_input_type(key, value, tool_name)
            
            # 根据类型进行处理
            if input_type == InputType.CODE:
                resolved[key] = self._resolve_code_string(value)
            elif input_type == InputType.EXPRESSION:
                resolved[key] = self._resolve_expression(value)
            else:  # LITERAL
                resolved[key] = value
        
        return resolved
    
    def _determine_input_type(self, key: str, value: Any, tool_name: Optional[str] = None) -> InputType:
        """
        确定输入参数的处理类型
        
        规则：
        1. 如果参数名是 'code'，且工具是 code_executor/execute_code，则为 CODE 类型
        2. 如果值是字符串且包含 ${...}，则为 EXPRESSION 类型
        3. 否则为 LITERAL 类型
        
        Args:
            key: 参数名
            value: 参数值
            tool_name: 工具名称
            
        Returns:
            输入类型
        """
        # 规则1: code 参数（代码字符串）
        if key == 'code' and tool_name in ('code_executor', 'execute_code'):
            return InputType.CODE
        
        # 规则2: 包含变量引用的字符串（表达式）
        if isinstance(value, str) and '${' in value:
            return InputType.EXPRESSION
        
        # 规则3: 其他情况（字面量）
        return InputType.LITERAL
    
    def _resolve_code_string(self, code: str) -> str:
        """
        解析代码字符串：只替换变量引用，不进行表达式求值
        
        Args:
            code: 代码字符串
            
        Returns:
            替换变量引用后的代码字符串
        """
        if not isinstance(code, str):
            return code
        
        def replace_var_in_code(match: re.Match) -> str:
            """替换代码字符串中的变量引用"""
            var_expr = match.group(1)
            
            # 只替换明确的变量引用（${input.}, ${steps[}, ${config.}）
            if not (var_expr.startswith('input.') or 
                    var_expr.startswith('steps[') or 
                    var_expr.startswith('config.')):
                return match.group(0)  # 保持原样
            
            # 获取变量值
            try:
                actual_value = self._get_variable_value(var_expr)
            except Exception as e:
                logger.warning(f"获取变量值失败: {var_expr}, 错误: {e}")
                return match.group(0)  # 保持原样
            
            # 如果变量不存在，保留原始变量引用
            if actual_value is None:
                logger.warning(f"变量不存在: {var_expr}，保留原始变量引用")
                return match.group(0)  # 保持原样
            
            # 格式化变量值为代码字符串
            return self._format_value_for_code(actual_value, code, match)
        
        # 替换变量引用
        resolved_code = re.sub(r'\$\{([^}]+)\}', replace_var_in_code, code)
        
        # 验证替换后的代码是否有效
        if not resolved_code or resolved_code.strip() == "":
            logger.error("代码字符串替换后为空，保留原始代码")
            return code
        
        return resolved_code
    
    def _resolve_expression(self, expression: str) -> Any:
        """
        解析表达式：进行表达式求值
        
        Args:
            expression: 表达式字符串
            
        Returns:
            求值结果
        """
        if not isinstance(expression, str):
            return expression
        
        try:
            from backend.core.agent.utils.expression_utils import ExpressionEvaluator
            evaluator = ExpressionEvaluator(self.context)
            result = evaluator.evaluate(expression)
            
            # 如果表达式求值返回 None，保留原始表达式
            if result is None:
                logger.warning(f"表达式求值返回 None: {expression}，保留原始值")
                return expression
            
            return result
        except Exception as e:
            logger.warning(f"表达式求值失败: {expression}，错误: {e}，保留原始值")
            return expression
    
    def _get_variable_value(self, var_expr: str) -> Any:
        """
        获取变量值
        
        Args:
            var_expr: 变量表达式（如 steps[0].video_path）
            
        Returns:
            变量值，如果不存在则返回 None
        """
        from backend.core.agent.utils.expression_utils import ExpressionEvaluator
        evaluator = ExpressionEvaluator(self.context)
        
        if var_expr.startswith('steps['):
            return evaluator._get_steps_value(var_expr)
        elif var_expr.startswith('input.'):
            return evaluator._get_input_value(var_expr)
        elif var_expr.startswith('config.'):
            return evaluator._get_config_value(var_expr)
        else:
            return None
    
    def _format_value_for_code(self, value: Any, code: str, match: re.Match) -> str:
        """
        将变量值格式化为代码字符串中的字符串字面量
        
        Args:
            value: 变量值
            code: 原始代码字符串
            match: 正则匹配对象
            
        Returns:
            格式化后的字符串（不包含引号，因为代码中已经有引号）
        """
        if isinstance(value, str):
            # 检测代码中使用的引号类型
            quote_char = self._detect_quote_char(code, match)
            
            # 根据引号类型转义字符串
            if quote_char == '"':
                # 使用双引号，转义双引号、反斜杠和换行符
                escaped = value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
            else:
                # 使用单引号，转义单引号、反斜杠和换行符
                escaped = value.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n').replace('\r', '\\r')
            
            return escaped
        elif isinstance(value, bool):
            return 'True' if value else 'False'
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            return str(value)
    
    def _detect_quote_char(self, code: str, match: re.Match) -> str:
        """
        检测代码中使用的引号类型
        
        Args:
            code: 代码字符串
            match: 正则匹配对象
            
        Returns:
            引号字符（' 或 "）
        """
        match_start = match.start()
        match_end = match.end()
        
        # 向前查找引号
        if match_start > 0:
            char_before = code[match_start - 1]
            if char_before in ("'", '"'):
                return char_before
        
        # 向后查找引号
        if match_end < len(code):
            char_after = code[match_end]
            if char_after in ("'", '"'):
                return char_after
        
        # 默认使用双引号
        return '"'

