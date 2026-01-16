"""
统一的输入参数解析器
清晰地区分不同类型的参数，采用不同的处理策略
"""
import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class InputType(Enum):
    """输入参数类型枚举"""
    LITERAL = "literal"  # 字面量，不进行任何处理
    EXPRESSION = "expression"  # 表达式，需要进行表达式求值


class InputResolver:
    """
    输入参数解析器
    
    设计原则：
    1. 根据参数类型和上下文，自动识别参数的处理方式
    2. 表达式字符串：进行表达式求值
    3. 字面量字符串：直接使用，不进行任何处理
    
    注意：CODE 类型已废弃，现在统一使用 LLM 生成代码（llm_code_generator）
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
            if input_type == InputType.EXPRESSION:
                resolved[key] = self._resolve_expression(value)
            else:  # LITERAL
                resolved[key] = value
        
        return resolved
    
    def _determine_input_type(self, key: str, value: Any, tool_name: Optional[str] = None) -> InputType:
        """
        确定输入参数的处理类型
        
        规则：
        1. 如果值是字符串且包含 ${...}，则为 EXPRESSION 类型
        2. 否则为 LITERAL 类型
        
        注意：CODE 类型已废弃，现在统一使用 LLM 生成代码（llm_code_generator）
        
        Args:
            key: 参数名
            value: 参数值
            tool_name: 工具名称（已废弃，保留以兼容旧代码）
            
        Returns:
            输入类型
        """
        # 规则1: 包含变量引用的字符串（表达式）
        if isinstance(value, str) and '${' in value:
            return InputType.EXPRESSION
        
        # 规则2: 其他情况（字面量）
        return InputType.LITERAL
    
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
    

