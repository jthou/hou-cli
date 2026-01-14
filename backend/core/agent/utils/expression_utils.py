"""
统一的表达式求值工具类
提供鲁棒的变量替换和表达式求值功能，避免 None 值导致的语法错误
"""
import re
import logging
from typing import Dict, Any, Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class ExpressionEvaluator:
    """表达式求值器 - 鲁棒地处理变量替换和表达式求值"""
    
    def __init__(self, context: Dict[str, Any]):
        """
        初始化表达式求值器
        
        Args:
            context: 上下文字典，包含 input, config, step_results 等
        """
        self.context = context
    
    def evaluate(self, expression: str) -> Any:
        """
        求值表达式
        
        Args:
            expression: 表达式字符串，支持 ${variable} 语法
            
        Returns:
            求值结果
        """
        if not expression:
            return None
        
        # 先替换所有嵌套的变量引用（包括 file_exists 函数调用中的变量）
        expression = self._replace_all_variables(expression)
        
        # 处理路径拼接（如 'path'.ext -> 'path.ext'）
        expression = self._process_path_concatenation(expression)
        
        # 处理 file_exists 函数调用中的路径拼接（如 ${steps[0].video_path}.srt）
        expression = self._process_file_exists_calls(expression)
        
        # 如果表达式只包含一个变量引用，直接返回替换后的值
        if not self._contains_operators(expression):
            # 移除引号（如果是字符串字面量）
            if expression.startswith("'") and expression.endswith("'"):
                return expression[1:-1]
            if expression.startswith('"') and expression.endswith('"'):
                return expression[1:-1]
            return expression
        
        # 否则尝试求值表达式
        try:
            # 添加 file_exists 函数支持
            def file_exists(path: str) -> bool:
                """检查文件是否存在"""
                if not path or path == 'None' or path == "''" or path == '""':
                    return False
                # 移除引号
                path = path.strip('"\'')
                if not path or path == 'None':
                    return False
                try:
                    return Path(path).exists()
                except Exception:
                    return False
            
            # 安全的求值环境
            safe_dict = {
                'True': True,
                'False': False,
                'None': None,
                'file_exists': file_exists,
                'Path': Path,
            }
            
            result = eval(expression, {"__builtins__": {}}, safe_dict)
            return result
        except Exception as e:
            logger.warning(f"表达式求值失败: {expression}, 错误: {e}")
            return None
    
    def _process_path_concatenation(self, expression: str) -> str:
        """
        处理路径拼接表达式
        
        例如：'path'.ext -> 'path.ext'
        注意：这个方法处理的是字符串字面量拼接，如 '/path'.srt
        
        Args:
            expression: 已替换变量的表达式
            
        Returns:
            处理后的表达式
        """
        # 匹配字符串字面量 + .扩展名 的模式（不在引号内）
        # 例如：'/path/to/file'.srt -> '/path/to/file.srt'
        # 但需要避免匹配 file_exists('path'.ext) 中的情况（这会在 _process_file_exists_calls 中处理）
        
        # 先处理不在函数调用中的路径拼接
        def replace_path_concat(match):
            quote = match.group(1)  # 引号类型
            base_path = match.group(2)  # 基础路径
            extension = match.group(3)  # 扩展名
            # 组合路径
            full_path = f"{base_path}.{extension}"
            return f"{quote}{full_path}{quote}"
        
        # 匹配不在函数调用中的 'path'.ext 或 "path".ext 模式
        # 使用负向前瞻，确保后面不是左括号（避免匹配函数调用）
        expression = re.sub(
            r"(['\"])([^'\"]+)\1\.([a-zA-Z0-9]+)(?!\s*\()",
            replace_path_concat,
            expression
        )
        
        return expression
    
    def _process_file_exists_calls(self, expression: str) -> str:
        """
        处理 file_exists 函数调用中的路径拼接
        
        例如：file_exists(${steps[0].video_path}.srt) -> file_exists('/path/to/file.srt')
        
        Args:
            expression: 已替换变量的表达式
            
        Returns:
            处理后的表达式
        """
        # 匹配 file_exists(...) 调用
        def replace_file_exists_path(match):
            full_match = match.group(0)
            path_expr = match.group(1).strip()  # file_exists 的参数部分
            
            # 处理字符串拼接：'path'.ext 或 "path".ext（在 file_exists 调用中）
            # 匹配引号内的路径 + .扩展名
            path_concatenation = re.match(r'^(["\'])([^"\']+)\1\.([a-zA-Z0-9]+)$', path_expr)
            if path_concatenation:
                quote = path_concatenation.group(1)
                base_path = path_concatenation.group(2)
                extension = path_concatenation.group(3)
                # 组合路径
                full_path = f"{base_path}.{extension}"
                return f"file_exists({quote}{full_path}{quote})"
            
            # 如果路径表达式已经是完整路径（带引号），直接返回
            if (path_expr.startswith("'") and path_expr.endswith("'")) or \
               (path_expr.startswith('"') and path_expr.endswith('"')):
                return full_match
            
            # 如果路径表达式是空字符串或 None，返回 False
            if path_expr == "''" or path_expr == '""' or path_expr == 'None':
                return 'False'
            
            # 如果路径表达式不包含引号，尝试添加引号
            if not path_expr.startswith(("'", '"')):
                return f"file_exists('{path_expr}')"
            
            return full_match
        
        # 替换 file_exists 调用中的路径拼接
        # 使用更精确的正则，匹配 file_exists(...) 调用，包括嵌套的括号
        # 先处理简单的 file_exists 调用
        expression = re.sub(
            r'file_exists\(([^()]+)\)',
            replace_file_exists_path,
            expression
        )
        
        return expression
    
    def _replace_all_variables(self, expression: str) -> str:
        """
        替换表达式中的所有变量引用
        
        优先替换最内层的变量引用，以正确处理嵌套情况
        
        Args:
            expression: 原始表达式
            
        Returns:
            替换后的表达式
        """
        # 递归替换所有 ${...} 变量引用
        # 优先替换最内层的变量引用（不包含其他 ${...} 的变量引用）
        max_iterations = 10  # 防止无限循环
        iteration = 0
        
        while '${' in expression and iteration < max_iterations:
            iteration += 1
            # 查找最内层的变量引用（不包含其他 ${...}）
            # 匹配 ${...}，其中 ... 不包含 ${ 或 }
            inner_var_pattern = r'\$\{([^${}]+)\}'
            
            def replace_inner_var(match):
                return self._replace_single_variable(match)
            
            new_expression = re.sub(inner_var_pattern, replace_inner_var, expression)
            
            # 如果没有变化，说明没有更多变量需要替换
            if new_expression == expression:
                break
            
            expression = new_expression
        
        return expression
    
    def _replace_single_variable(self, match: re.Match) -> str:
        """
        替换单个变量引用
        
        Args:
            match: 正则匹配对象
            
        Returns:
            替换后的值（字符串形式，用于表达式求值）
        """
        var_expr = match.group(1)
        
        # 如果变量表达式包含函数调用（如 file_exists(...)），不处理，保留原样
        # 这些会在后续的 _process_file_exists_calls 中处理
        if '(' in var_expr and ')' in var_expr:
            # 这是一个函数调用，保留原样（移除 ${} 包装，但保留函数调用）
            return var_expr
        
        # 处理 steps[N].field
        if var_expr.startswith('steps['):
            value = self._get_steps_value(var_expr)
            return self._format_value_for_expression(value)
        
        # 处理 input.field
        if var_expr.startswith('input.'):
            value = self._get_input_value(var_expr)
            return self._format_value_for_expression(value)
        
        # 处理 config.field
        if var_expr.startswith('config.'):
            value = self._get_config_value(var_expr)
            return self._format_value_for_expression(value)
        
        # 处理直接变量
        if var_expr in self.context:
            value = self.context[var_expr]
            return self._format_value_for_expression(value)
        
        # 未找到变量，返回空字符串（而不是 'None'，避免语法错误）
        return "''"
    
    def _get_steps_value(self, var_expr: str) -> Any:
        """
        获取 steps[N].field 的值
        
        Args:
            var_expr: 变量表达式，如 steps[0].video_path
            
        Returns:
            变量值
        """
        match = re.match(r'steps\[(\d+)\]\.(.+)', var_expr)
        if not match:
            return None
        
        step_idx = int(match.group(1))
        field = match.group(2)
        
        step_results = self.context.get('step_results') or self.context.get('steps')
        if not step_results or not isinstance(step_results, (list, tuple)):
            return None
        
        if step_idx >= len(step_results):
            return None
        
        step_result = step_results[step_idx]
        if not isinstance(step_result, dict):
            return None
        
        return step_result.get(field)
    
    def _get_input_value(self, var_expr: str) -> Any:
        """
        获取 input.field 的值
        
        Args:
            var_expr: 变量表达式，如 input.video_path
            
        Returns:
            变量值
        """
        field = var_expr[6:]  # 移除 "input."
        input_dict = self.context.get('input')
        if not isinstance(input_dict, dict):
            return None
        return input_dict.get(field)
    
    def _get_config_value(self, var_expr: str) -> Any:
        """
        获取 config.field 的值
        
        Args:
            var_expr: 变量表达式，如 config.model
            
        Returns:
            变量值
        """
        field = var_expr[7:]  # 移除 "config."
        config_dict = self.context.get('config')
        if not isinstance(config_dict, dict):
            return None
        return config_dict.get(field)
    
    def _format_value_for_expression(self, value: Any) -> str:
        """
        将值格式化为表达式中的字符串形式
        
        Args:
            value: 原始值
            
        Returns:
            格式化后的字符串（用于表达式求值）
        """
        if value is None:
            # None 值返回空字符串，避免语法错误（如 None.srt 会报错）
            # 但在表达式中，如果用于字符串拼接，应该返回空字符串
            return "''"
        
        if isinstance(value, bool):
            return 'True' if value else 'False'
        
        if isinstance(value, (int, float)):
            return str(value)
        
        if isinstance(value, str):
            # 移除多余的引号
            clean_value = value.strip('"\'')
            # 使用 repr() 来正确转义字符串
            return repr(clean_value)
        
        # 其他类型转换为字符串
        return repr(str(value))
    
    def _contains_operators(self, expression: str) -> bool:
        """
        检查表达式是否包含操作符
        
        Args:
            expression: 表达式字符串
            
        Returns:
            是否包含操作符
        """
        operators = ['==', '!=', '<', '>', '<=', '>=', ' and ', ' or ', ' not ', '+', '-', '*', '/', '%']
        return any(op in expression for op in operators) or 'file_exists(' in expression

