"""Tool 基类和接口定义"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Callable


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
    
    def __init__(self, name: str, description: str, parameters: Optional[List[ToolParameter]] = None):
        """
        初始化工具
        
        Args:
            name: 工具名称
            description: 工具描述
            parameters: 工具参数列表
        """
        self.name = name
        self.description = description
        self.parameters = parameters or []
        self.progress_callback: Optional[Callable[[str], None]] = None
    
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
        
        # 检查参数类型
        for param in self.parameters:
            if param.name in kwargs:
                value = kwargs[param.name]
                if not self._validate_type(value, param.type):
                    return f"Parameter {param.name} has wrong type. Expected {param.type}, got {type(value).__name__}"
                
                # 检查枚举值
                if param.enum and value not in param.enum:
                    return f"Parameter {param.name} must be one of {param.enum}, got {value}"
        
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
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        param.name: {
                            "type": param.type,
                            "description": param.description,
                        }
                        for param in self.parameters
                    },
                    "required": [param.name for param in self.parameters if param.required],
                }
            }
        }

