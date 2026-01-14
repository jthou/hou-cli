"""技能基类和接口定义"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from pathlib import Path


@dataclass
class SkillParameter:
    """技能参数定义"""
    name: str
    type: str  # "string", "integer", "number", "boolean", "object", "array"
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None  # 可选值列表


@dataclass
class SkillResult:
    """技能执行结果"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    intermediate_results: Optional[Dict[str, Any]] = None  # 中间结果


class Skill(ABC):
    """技能基类，所有技能继承此类"""
    
    def __init__(
        self,
        name: str,
        description: str,
        version: str = "1.0.0",
        category: str = "general",
        priority: str = "P1",
        parameters: Optional[List[SkillParameter]] = None,
        dependencies: Optional[Dict[str, List[str]]] = None
    ):
        """
        初始化技能
        
        Args:
            name: 技能名称
            description: 技能描述
            version: 技能版本
            category: 技能类别
            priority: 技能优先级（P0 > P1 > P2），用于技能匹配排序
            parameters: 技能参数列表
            dependencies: 技能依赖（工具和子技能）
        """
        self.name = name
        self.description = description
        self.version = version
        self.category = category
        self.priority = priority
        self.parameters = parameters or []
        self.dependencies = dependencies or {}
        self.progress_callback: Optional[callable] = None
    
    def set_progress_callback(self, callback: Optional[callable]):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def report_progress(self, message: str):
        """报告进度（如果设置了回调）"""
        if self.progress_callback:
            self.progress_callback(message)
    
    @abstractmethod
    async def execute(self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> SkillResult:
        """
        执行技能
        
        Args:
            parameters: 技能参数
            context: 执行上下文（包含工具注册表、LLM服务等）
        
        Returns:
            SkillResult: 执行结果
        """
        pass
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        验证参数
        
        Args:
            parameters: 待验证的参数
        
        Returns:
            (是否有效, 错误信息)
        """
        # 检查必需参数
        for param in self.parameters:
            if param.required and param.name not in parameters:
                if param.default is None:
                    return False, f"缺少必需参数: {param.name}"
                parameters[param.name] = param.default
        
        # 检查参数类型和枚举值
        for param in self.parameters:
            if param.name in parameters:
                value = parameters[param.name]
                
                # 类型检查
                if param.type == "integer" and not isinstance(value, int):
                    try:
                        parameters[param.name] = int(value)
                    except (ValueError, TypeError):
                        return False, f"参数 {param.name} 必须是整数"
                
                elif param.type == "number" and not isinstance(value, (int, float)):
                    try:
                        parameters[param.name] = float(value)
                    except (ValueError, TypeError):
                        return False, f"参数 {param.name} 必须是数字"
                
                elif param.type == "boolean" and not isinstance(value, bool):
                    if isinstance(value, str):
                        parameters[param.name] = value.lower() in ('true', '1', 'yes', 'on')
                    else:
                        return False, f"参数 {param.name} 必须是布尔值"
                
                # 枚举值检查
                if param.enum and value not in param.enum:
                    return False, f"参数 {param.name} 必须是以下值之一: {', '.join(map(str, param.enum))}"
        
        return True, None
    
    def get_parameter_schema(self) -> Dict[str, Any]:
        """获取参数模式（用于 LLM 工具描述）"""
        properties = {}
        required = []
        
        for param in self.parameters:
            param_schema = {
                "type": param.type,
                "description": param.description
            }
            
            if param.default is not None:
                param_schema["default"] = param.default
            
            if param.enum:
                param_schema["enum"] = param.enum
            
            properties[param.name] = param_schema
            
            if param.required:
                required.append(param.name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }




