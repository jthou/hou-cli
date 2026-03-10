"""动态模型切换器 - 根据执行结果动态调整模型选择"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from backend.services.llm.model_config import get_model_config_manager
from backend.core.agent.models import TaskComplexity

logger = logging.getLogger(__name__)


@dataclass
class ModelSwitchRecord:
    """模型切换记录"""
    timestamp: datetime
    from_model: str
    to_model: str
    reason: str
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "from_model": self.from_model,
            "to_model": self.to_model,
            "reason": self.reason,
            "context": self.context
        }


class ModelSwitcher:
    """动态模型切换器
    
    根据工具执行结果、任务复杂度、错误情况等因素，动态决定是否需要切换模型。
    """
    
    def __init__(self):
        self.config_manager = get_model_config_manager()
        self.switch_history: List[ModelSwitchRecord] = []
        self.max_history_size = 100  # 最多保存100条切换记录
    
    def analyze_execution_result(
        self,
        tool_name: str,
        tool_result: Dict[str, Any],
        current_model: str,
        task_complexity: Optional[TaskComplexity] = None
    ) -> Optional[str]:
        """
        分析执行结果，决定是否需要切换模型
        
        Args:
            tool_name: 工具名称
            tool_result: 工具执行结果（包含 success, data, error 等字段）
            current_model: 当前使用的模型
            task_complexity: 任务复杂度（可选）
            
        Returns:
            如果需要切换，返回目标模型名称；否则返回 None
        """
        # 1. 检查工具执行是否失败
        if not tool_result.get("success", True):
            error_msg = tool_result.get("error", "未知错误")
            logger.debug(f"工具 {tool_name} 执行失败: {error_msg}")
            
            # 如果当前使用的是 chat 模型，且任务需要推理，尝试切换到推理模型
            if self._is_chat_model(current_model) and task_complexity == TaskComplexity.COMPLEX:
                reasoning_model = self.config_manager.get_reasoning_model()
                if reasoning_model != current_model:
                    logger.info(f"工具执行失败，任务复杂度高，建议切换到推理模型: {reasoning_model}")
                    return reasoning_model
            
            # 如果当前使用的是 chat 模型，且工具需要代码能力，尝试切换到代码模型
            if self._is_chat_model(current_model):
                from backend.core.agent.tools.metadata import tool_metadata_registry
                metadata = tool_metadata_registry.get_metadata(tool_name)
                if metadata and metadata.requires_code:
                    code_model = self.config_manager.get_code_model()
                    if code_model != current_model:
                        logger.info(f"工具需要代码能力，建议切换到代码模型: {code_model}")
                        return code_model
        
        # 2. 检查任务复杂度变化
        if task_complexity == TaskComplexity.COMPLEX and self._is_chat_model(current_model):
            reasoning_model = self.config_manager.get_reasoning_model()
            if reasoning_model != current_model:
                logger.info(f"任务复杂度高，建议切换到推理模型: {reasoning_model}")
                return reasoning_model
        
        # 3. 检查是否需要代码生成
        # 这个逻辑已经在工具调用时处理了，这里可以添加额外的检查
        
        return None
    
    def should_switch_model(
        self,
        current_model: str,
        target_model: Optional[str],
    ) -> bool:
        """
        判断是否应该切换模型
        
        Args:
            current_model: 当前模型
            target_model: 目标模型
            
        Returns:
            是否应该切换
        """
        if not target_model:
            return False
        
        if target_model == current_model:
            return False
        
        return True
    
    def record_switch(
        self,
        from_model: str,
        to_model: str,
        reason: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        记录模型切换
        
        Args:
            from_model: 源模型
            to_model: 目标模型
            reason: 切换原因
            context: 上下文信息
        """
        record = ModelSwitchRecord(
            timestamp=datetime.now(),
            from_model=from_model,
            to_model=to_model,
            reason=reason,
            context=context or {}
        )
        
        self.switch_history.append(record)
        if len(self.switch_history) > self.max_history_size:
            self.switch_history = self.switch_history[-self.max_history_size:]

        logger.info(f"记录模型切换: {from_model} -> {to_model}, 原因: {reason}")
    
    def get_switch_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取切换历史
        
        Args:
            limit: 返回的记录数量限制
            
        Returns:
            切换历史记录列表
        """
        return [record.to_dict() for record in self.switch_history[-limit:]]
    
    def _is_chat_model(self, model: str) -> bool:
        """判断是否是对话模型"""
        chat_model = self.config_manager.get_chat_model()
        return model == chat_model
    
    def _is_code_model(self, model: str) -> bool:
        """判断是否是代码模型"""
        code_model = self.config_manager.get_code_model()
        return model == code_model
    
    def _is_reasoning_model(self, model: str) -> bool:
        """判断是否是推理模型"""
        reasoning_model = self.config_manager.get_reasoning_model()
        return model == reasoning_model
    
    def get_recommended_model(
        self,
        tool_name: str,
        task_complexity: Optional[TaskComplexity] = None,
        current_model: Optional[str] = None
    ) -> Optional[str]:
        """
        获取推荐的模型类型
        
        Args:
            tool_name: 工具名称
            task_complexity: 任务复杂度
            current_model: 当前模型（可选）
            
        Returns:
            推荐的模型名称
        """
        from backend.core.agent.tools.metadata import tool_metadata_registry
        
        # 1. 优先根据工具元数据推荐
        metadata = tool_metadata_registry.get_metadata(tool_name)
        if metadata and metadata.recommended_model:
            if metadata.recommended_model == "code":
                return self.config_manager.get_code_model()
            elif metadata.recommended_model == "reasoning":
                return self.config_manager.get_reasoning_model()
            elif metadata.recommended_model == "chat":
                return self.config_manager.get_chat_model()
        
        # 2. 根据任务复杂度推荐
        if task_complexity == TaskComplexity.COMPLEX:
            return self.config_manager.get_reasoning_model()
        
        # 3. 默认返回对话模型
        return self.config_manager.get_chat_model()

