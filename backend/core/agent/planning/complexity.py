"""任务复杂度判断模块"""
import logging
import re
import hashlib
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class TaskComplexityAnalyzer:
    """任务复杂度分析器
    
    判断任务是否需要规划文件，基于以下标准：
    1. 任务描述长度
    2. 关键词检测
    3. 历史对话中的工具调用次数
    4. 任务包含多个步骤
    5. 用户明确要求规划
    """
    
    # 复杂任务关键词
    COMPLEX_KEYWORDS = [
        "实现", "开发", "创建", "构建", "重构", "设计",
        "implement", "develop", "create", "build", "refactor", "design",
        "编写", "制作", "完成", "解决",
        "write", "make", "complete", "solve"
    ]
    
    # 多步骤关键词
    MULTI_STEP_KEYWORDS = [
        "然后", "接着", "最后", "首先", "其次", "再次",
        "then", "next", "finally", "first", "second", "again",
        "之后", "之后", "接下来"
    ]
    
    # 规划相关关键词
    PLANNING_KEYWORDS = [
        "规划", "计划", "安排", "组织",
        "plan", "planning", "organize", "arrange"
    ]
    
    # 简单任务关键词（如果只有这些，可能是简单任务）
    SIMPLE_KEYWORDS = [
        "显示", "查看", "列出", "读取", "打开",
        "show", "view", "list", "read", "open",
        "查询", "搜索", "查找",
        "query", "search", "find"
    ]
    
    def __init__(self, 
                 min_task_length: int = 20,
                 complexity_threshold: float = 0.3,
                 llm_service: Optional[Any] = None,
                 use_llm: bool = False):
        """
        初始化复杂度分析器
        
        Args:
            min_task_length: 最小任务长度（字符数），超过此长度才可能复杂
            complexity_threshold: 复杂度阈值（0-1），超过此值认为是复杂任务
            llm_service: LLM 服务实例（用于 LLM 辅助判断）
            use_llm: 是否使用 LLM 辅助判断
        """
        self.min_task_length = min_task_length
        self.complexity_threshold = complexity_threshold
        self.llm_service = llm_service
        self.use_llm = use_llm
        
        # 判断结果缓存
        self._judgment_cache: Dict[str, bool] = {}
        self._cache_max_size = 1000  # 最大缓存数量
    
    def _get_cache_key(self, task: str) -> str:
        """生成缓存键"""
        # 使用任务的前100个字符作为缓存键
        task_key = task[:100].strip().lower()
        return hashlib.md5(task_key.encode('utf-8')).hexdigest()
    
    async def _is_complex_by_llm(self, task: str) -> Optional[bool]:
        """
        使用 LLM 判断任务复杂度
        
        Args:
            task: 任务描述
        
        Returns:
            是否为复杂任务，如果判断失败返回 None
        """
        if not self.llm_service:
            return None
        
        try:
            prompt = f"""判断以下任务是否需要详细规划（创建 task_plan.md、findings.md、progress.md）：

任务：{task}

请分析任务复杂度，考虑：
1. 任务步骤数量（是否需要多个步骤）
2. 所需工具数量（是否需要多个工具）
3. 是否需要研究（是否需要搜索、查找资料）
4. 是否需要多轮对话（是否需要多次交互）
5. 任务复杂度（简单查询 vs 复杂开发）

只返回 "是" 或 "否"，不要返回其他内容。"""
            
            response = await self.llm_service.chat(user_prompt=prompt)
            response_lower = response.lower().strip()
            
            # 解析响应
            if "是" in response_lower or "yes" in response_lower or "true" in response_lower:
                return True
            elif "否" in response_lower or "no" in response_lower or "false" in response_lower:
                return False
            else:
                logger.warning(f"LLM 返回格式异常: {response}")
                return None
        except Exception as e:
            logger.warning(f"LLM 判断失败: {str(e)}")
            return None
    
    def is_complex_task(self, 
                       task: str, 
                       history: List[Dict[str, Any]] = None,
                       tool_call_count: int = 0) -> bool:
        """
        判断任务是否复杂（同步版本，使用规则判断）
        
        Args:
            task: 任务描述
            history: 历史对话记录
            tool_call_count: 已执行的工具调用次数
        
        Returns:
            是否为复杂任务
        """
        if not task or len(task.strip()) < self.min_task_length:
            return False
        
        # 检查缓存
        cache_key = self._get_cache_key(task)
        if cache_key in self._judgment_cache:
            return self._judgment_cache[cache_key]
        
        # 计算复杂度分数
        score = 0.0
        
        # 1. 任务长度（0-0.2）
        task_length_score = min(len(task) / 200, 0.2)
        score += task_length_score
        
        # 2. 复杂关键词检测（0-0.3）
        complex_keyword_count = sum(1 for kw in self.COMPLEX_KEYWORDS if kw in task.lower())
        if complex_keyword_count > 0:
            score += min(complex_keyword_count * 0.1, 0.3)
        
        # 3. 多步骤关键词检测（0-0.2）
        multi_step_count = sum(1 for kw in self.MULTI_STEP_KEYWORDS if kw in task.lower())
        if multi_step_count > 0:
            score += min(multi_step_count * 0.1, 0.2)
        
        # 4. 规划关键词检测（0-0.2）
        planning_count = sum(1 for kw in self.PLANNING_KEYWORDS if kw in task.lower())
        if planning_count > 0:
            score += 0.2  # 明确要求规划，直接认为是复杂任务
        
        # 5. 工具调用次数（0-0.1）
        if tool_call_count > 5:
            score += 0.1
        
        # 6. 历史对话长度（0-0.1）
        if history and len(history) > 10:
            score += 0.1
        
        # 7. 简单任务关键词惩罚（-0.1）
        simple_count = sum(1 for kw in self.SIMPLE_KEYWORDS if kw in task.lower())
        if simple_count > 0 and complex_keyword_count == 0:
            score -= 0.1
        
        # 确保分数在 0-1 之间
        score = max(0.0, min(1.0, score))
        
        is_complex = score >= self.complexity_threshold
        
        # 缓存结果
        if len(self._judgment_cache) >= self._cache_max_size:
            # 清除最旧的缓存（简单策略：清除一半）
            keys_to_remove = list(self._judgment_cache.keys())[:self._cache_max_size // 2]
            for key in keys_to_remove:
                del self._judgment_cache[key]
        
        self._judgment_cache[cache_key] = is_complex
        
        logger.debug(
            f"任务复杂度分析: task='{task[:50]}', "
            f"score={score:.2f}, threshold={self.complexity_threshold}, "
            f"is_complex={is_complex}"
        )
        
        return is_complex
    
    async def is_complex_task_async(self, 
                                    task: str, 
                                    history: List[Dict[str, Any]] = None,
                                    tool_call_count: int = 0) -> bool:
        """
        判断任务是否复杂（异步版本，支持 LLM 辅助判断）
        
        Args:
            task: 任务描述
            history: 历史对话记录
            tool_call_count: 已执行的工具调用次数
        
        Returns:
            是否为复杂任务
        """
        if not task or len(task.strip()) < self.min_task_length:
            return False
        
        # 检查缓存
        cache_key = self._get_cache_key(task)
        if cache_key in self._judgment_cache:
            return self._judgment_cache[cache_key]
        
        # 先用规则判断
        rule_result = self.is_complex_task(task, history, tool_call_count)
        
        # 如果使用 LLM 且规则判断不确定（接近阈值），使用 LLM 辅助判断
        if self.use_llm and self.llm_service:
            # 如果规则判断接近阈值（±0.1），使用 LLM 确认
            rule_score = self.analyze_task(task, history).get("score", 0.0)
            if abs(rule_score - self.complexity_threshold) < 0.1:
                llm_result = await self._is_complex_by_llm(task)
                if llm_result is not None:
                    # 使用 LLM 结果
                    self._judgment_cache[cache_key] = llm_result
                    logger.info(f"LLM 辅助判断: task='{task[:50]}', result={llm_result}")
                    return llm_result
        
        # 使用规则判断结果
        return rule_result
    
    def analyze_task(self, task: str, history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        分析任务，返回详细信息
        
        Args:
            task: 任务描述
            history: 历史对话记录
        
        Returns:
            分析结果字典
        """
        result = {
            "is_complex": False,
            "score": 0.0,
            "reasons": [],
            "task_length": len(task),
            "complex_keywords": [],
            "multi_step_keywords": [],
            "planning_keywords": []
        }
        
        if not task or len(task.strip()) < self.min_task_length:
            return result
        
        score = 0.0
        
        # 检测复杂关键词
        found_complex = [kw for kw in self.COMPLEX_KEYWORDS if kw in task.lower()]
        if found_complex:
            score += min(len(found_complex) * 0.1, 0.3)
            result["complex_keywords"] = found_complex
            result["reasons"].append(f"包含复杂任务关键词: {', '.join(found_complex[:3])}")
        
        # 检测多步骤关键词
        found_multi = [kw for kw in self.MULTI_STEP_KEYWORDS if kw in task.lower()]
        if found_multi:
            score += min(len(found_multi) * 0.1, 0.2)
            result["multi_step_keywords"] = found_multi
            result["reasons"].append(f"包含多步骤关键词: {', '.join(found_multi[:3])}")
        
        # 检测规划关键词
        found_planning = [kw for kw in self.PLANNING_KEYWORDS if kw in task.lower()]
        if found_planning:
            score += 0.2
            result["planning_keywords"] = found_planning
            result["reasons"].append(f"明确要求规划: {', '.join(found_planning)}")
        
        # 任务长度
        task_length_score = min(len(task) / 200, 0.2)
        score += task_length_score
        if len(task) > 100:
            result["reasons"].append(f"任务描述较长 ({len(task)} 字符)")
        
        # 历史对话
        if history and len(history) > 10:
            score += 0.1
            result["reasons"].append(f"历史对话较长 ({len(history)} 条)")
        
        result["score"] = max(0.0, min(1.0, score))
        result["is_complex"] = result["score"] >= self.complexity_threshold
        
        return result

