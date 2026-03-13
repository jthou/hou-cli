"""Tool 基类和接口定义"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Callable
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str
    type: str  # "string", "integer", "number", "boolean", "object", "array"
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None  # 可选值列表


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class Tool(ABC):
    """Tool 基类，所有工具继承此类"""
    
    def __init__(
        self, 
        name: str, 
        description: str, 
        parameters: Optional[List[ToolParameter]] = None,
        requires_reasoning: bool = False,
        requires_code: bool = False,
        recommended_model: Optional[str] = None,
        can_parallel: bool = True
    ):
        """
        初始化工具
        
        Args:
            name: 工具名称
            description: 工具描述
            parameters: 工具参数列表
            requires_reasoning: 是否需要推理能力
            requires_code: 是否需要代码能力
            recommended_model: 推荐的模型类型（"chat", "code", "reasoning"）
            can_parallel: 是否可以并行执行
        """
        self.name = name
        self.description = description
        self.parameters = parameters or []
        self.progress_callback: Optional[Callable[[str], None]] = None
        
        # 工具元数据
        self.requires_reasoning = requires_reasoning
        self.requires_code = requires_code
        self.recommended_model = recommended_model
        self.can_parallel = can_parallel
    
    def set_progress_callback(self, callback: Optional[Callable[[str], None]]):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def report_progress(self, message: str):
        """报告进度（如果设置了回调）"""
        if self.progress_callback:
            self.progress_callback(message)
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        执行工具
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        pass
    
    def validate_parameters(self, **kwargs) -> Optional[str]:
        """
        验证参数
        
        Args:
            **kwargs: 待验证的参数
            
        Returns:
            None 如果验证通过，否则返回错误信息
        """
        # 检查必需参数
        for param in self.parameters:
            if param.required and param.name not in kwargs:
                if param.default is None:
                    return f"Missing required parameter: {param.name}"
        
        # 检查参数类型和值（增强版）
        for param in self.parameters:
            if param.name in kwargs:
                value = kwargs[param.name]
                
                # 类型验证（尝试自动转换）
                if not self._validate_type(value, param.type):
                    # 尝试类型转换
                    converted_value = self._try_convert_type(value, param.type)
                    if converted_value is not None:
                        # 转换成功，更新参数值
                        kwargs[param.name] = converted_value
                        logger.debug(f"参数类型转换: {param.name} from {type(value).__name__} to {param.type}")
                    else:
                        return f"Parameter {param.name} has wrong type. Expected {param.type}, got {type(value).__name__}"
                else:
                    # 类型正确，但可能需要进一步处理
                    value = kwargs[param.name]
                
                # 字符串参数清理（去除前后空格）
                if param.type == "string" and isinstance(value, str):
                    trimmed_value = value.strip()
                    if trimmed_value != value:
                        kwargs[param.name] = trimmed_value
                        logger.debug(f"参数值清理: {param.name} 去除前后空格")
                
                # 枚举值验证（支持大小写不敏感匹配）
                if param.enum and value not in param.enum:
                    # 尝试大小写不敏感匹配
                    if isinstance(value, str):
                        value_lower = value.lower()
                        enum_lower = [str(e).lower() if isinstance(e, str) else e for e in param.enum]
                        if value_lower in enum_lower:
                            # 找到匹配的枚举值，更新参数值
                            matched_index = enum_lower.index(value_lower)
                            kwargs[param.name] = param.enum[matched_index]
                            logger.debug(f"参数枚举值修正: {param.name} from '{value}' to '{param.enum[matched_index]}'")
                        else:
                            return f"Parameter {param.name} must be one of {param.enum}, got {value}"
                    else:
                        return f"Parameter {param.name} must be one of {param.enum}, got {value}"
        
        return None
    
    def _try_convert_type(self, value: Any, expected_type: str) -> Optional[Any]:
        """
        尝试转换参数类型
        
        Args:
            value: 待转换的值
            expected_type: 期望的类型
            
        Returns:
            转换后的值，如果无法转换返回 None
        """
        try:
            if expected_type == "integer" and isinstance(value, (str, float)):
                return int(float(value))  # 先转 float 再转 int，处理 "3.0" 这种情况
            elif expected_type == "number" and isinstance(value, str):
                return float(value)
            elif expected_type == "boolean" and isinstance(value, str):
                value_lower = value.lower()
                if value_lower in ("true", "1", "yes", "on", "是"):
                    return True
                elif value_lower in ("false", "0", "no", "off", "否"):
                    return False
            elif expected_type == "string" and not isinstance(value, str):
                return str(value)
        except (ValueError, TypeError):
            pass
        return None
    
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """验证值类型"""
        type_mapping = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "object": dict,
            "array": list,
        }
        
        expected = type_mapping.get(expected_type)
        if expected is None:
            return True  # 未知类型，不验证
        
        if isinstance(expected, tuple):
            return isinstance(value, expected)
        return isinstance(value, expected)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 LLM Function Calling）"""
        properties = {}
        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description,
            }
            # JSON Schema 要求 array 类型必须包含 items，否则 LLM API 返回 400
            if param.type == "array":
                prop["items"] = {"type": "string"}
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default
            properties[param.name] = prop
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": [param.name for param in self.parameters if param.required],
                }
            }
        }

