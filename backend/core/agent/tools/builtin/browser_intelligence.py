"""Browser Intelligence - 浏览器工具智能决策模块"""
import os
import logging
from typing import Dict, Optional
from backend.services.llm.llm_service import LLMService


logger = logging.getLogger(__name__)


class BrowserIntelligence:
    """浏览器工具智能决策类
    
    负责根据任务类型智能选择最适合的模型和工具策略
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        """初始化浏览器智能决策器
        
        Args:
            llm_service: LLM 服务实例，如果为 None 则创建新的实例
        """
        self.llm_service = llm_service or LLMService()
        
        # 视觉任务关键词
        self.vision_keywords = [
            "截图", "图片", "图像", "视觉", "识别", "视觉分析", "页面截图",
            "页面内容", "页面布局", "页面元素", "页面结构", "页面样式", "分析页面",
            "screenshot", "image", "visual", "recognize", "see", "view",
            "按钮位置", "元素位置", "颜色", "形状", "图标", "logo"
        ]
        
        # 精确操作关键词
        self.precise_operation_keywords = [
            "点击", "click", "fill", "填写", "输入", "navigate", "导航", 
            "定位", "选择", "select", "勾选", "check", "submit", "提交"
        ]
        
        # 复杂任务关键词
        self.complex_task_keywords = [
            "复杂", "多步骤", "multi-step", "长时间", "持久化", "保持登录", 
            "会话", "session", "cookie", "复杂流程", "连续操作"
        ]
        
        # 数据提取关键词
        self.data_extraction_keywords = [
            "提取", "抽取", "爬取", "抓取", "收集", "gather", "extract", 
            "数据", "information", "details", "详情", "列表", "表格", "价格"
        ]
    
    def analyze_task_type(self, task: str) -> Dict[str, any]:
        """分析任务类型，决定使用哪种策略
        
        Args:
            task: 用户任务描述
            
        Returns:
            包含任务分析结果的字典
        """
        task_lower = task.lower()
        
        analysis = {
            "requires_vision": False,
            "requires_precise_operation": False,
            "is_complex_task": False,
            "requires_data_extraction": False,
            "recommended_model": None,
            "confidence": 0.0
        }
        
        # 检查视觉需求
        vision_matches = [
            kw for kw in self.vision_keywords 
            if kw.lower() in task_lower
        ]
        if vision_matches:
            analysis["requires_vision"] = True
            analysis["confidence"] += 0.3
        
        # 检查精确操作需求
        precise_matches = [
            kw for kw in self.precise_operation_keywords 
            if kw.lower() in task_lower
        ]
        if precise_matches:
            analysis["requires_precise_operation"] = True
            analysis["confidence"] += 0.2
        
        # 检查复杂任务
        complex_matches = [
            kw for kw in self.complex_task_keywords 
            if kw.lower() in task_lower
        ]
        if complex_matches:
            analysis["is_complex_task"] = True
            analysis["confidence"] += 0.2
        
        # 检查数据提取
        extraction_matches = [
            kw for kw in self.data_extraction_keywords 
            if kw.lower() in task_lower
        ]
        if extraction_matches:
            analysis["requires_data_extraction"] = True
            analysis["confidence"] += 0.2
        
        # 根据分析结果推荐模型
        if analysis["requires_vision"]:
            analysis["recommended_model"] = os.getenv(
                "BROWSER_TOOL_VISION_MODEL", "qwen-vl-max-2025-08-13"
            )
        elif analysis["is_complex_task"]:
            from backend.core.agent.tools.builtin.browser_llm_defaults import browser_default_reasoning_model

            analysis["recommended_model"] = os.getenv(
                "BROWSER_TOOL_REASONING_MODEL", ""
            ).strip() or browser_default_reasoning_model()
        else:
            from backend.core.agent.tools.builtin.browser_llm_defaults import browser_default_chat_model

            analysis["recommended_model"] = os.getenv(
                "BROWSER_TOOL_CHAT_MODEL", ""
            ).strip() or browser_default_chat_model()
        
        # 确保置信度不超过1.0
        analysis["confidence"] = min(1.0, analysis["confidence"])
        
        logger.info(f"任务分析结果: {analysis}")
        return analysis
    
    def get_optimal_llm_for_task(self, task: str) -> any:
        """根据任务获取最优的 LLM 实例
        
        Args:
            task: 用户任务描述
            
        Returns:
            适合任务的 LLM 实例
        """
        analysis = self.analyze_task_type(task)
        recommended_model = analysis["recommended_model"]
        
        logger.info(f"为任务 '{task[:50]}...' 选择模型: {recommended_model}")
        
        # 使用适配后的 LLM 创建方法
        return self.llm_service.get_browser_use_llm_with_adaptation(
            model=recommended_model
        )
    
    def should_use_fine_grained_tools(self, task: str) -> bool:
        """决定是否应该使用细粒度工具
        
        Args:
            task: 用户任务描述
            
        Returns:
            是否使用细粒度工具
        """
        analysis = self.analyze_task_type(task)
        
        # 如果任务需要精确操作或数据提取，则更适合使用细粒度工具
        return (analysis["requires_precise_operation"] or 
                analysis["requires_data_extraction"] or
                analysis["confidence"] > 0.5)  # 高置信度时也使用细粒度工具
    
    def get_task_complexity_score(self, task: str) -> float:
        """获取任务复杂度评分
        
        Args:
            task: 用户任务描述
            
        Returns:
            复杂度评分 (0.0-1.0)
        """
        analysis = self.analyze_task_type(task)
        
        # 基础复杂度分数
        base_score = analysis["confidence"]
        
        # 根据关键词数量增加复杂度
        task_lower = task.lower()
        keyword_count = sum([
            len([
                kw for kw in self.vision_keywords 
                if kw.lower() in task_lower
            ]),
            len([
                kw for kw in self.precise_operation_keywords 
                if kw.lower() in task_lower
            ]),
            len([
                kw for kw in self.complex_task_keywords 
                if kw.lower() in task_lower
            ]),
            len([
                kw for kw in self.data_extraction_keywords 
                if kw.lower() in task_lower
            ])
        ])
        
        # 每个关键词增加0.05分，最多增加0.5分
        keyword_bonus = min(0.5, keyword_count * 0.05)
        
        # 根据任务长度增加复杂度（假设更长的任务更复杂）
        length_bonus = min(0.2, len(task) / 1000)  # 最多增加0.2分
        
        complexity_score = min(1.0, base_score + keyword_bonus + length_bonus)
        
        logger.debug(
            f"任务复杂度评分: {complexity_score} "
            f"(基础: {base_score}, "
            f"关键词奖励: {keyword_bonus}, "
            f"长度奖励: {length_bonus})"
        )
        return complexity_score


# 全局实例
_browser_intelligence = None


def get_browser_intelligence(llm_service: Optional[LLMService] = None) -> BrowserIntelligence:
    """获取浏览器智能决策器全局实例
    
    Args:
        llm_service: LLM 服务实例，如果为 None 则使用默认实例
        
    Returns:
        浏览器智能决策器实例
    """
    global _browser_intelligence
    if _browser_intelligence is None:
        _browser_intelligence = BrowserIntelligence(llm_service)
    return _browser_intelligence