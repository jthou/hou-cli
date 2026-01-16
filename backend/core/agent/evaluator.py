"""对话评估器 - 对每一轮对话结果进行自动评估打分"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from backend.services.llm.llm_service import LLMService
from backend.core.context.models import Message, MessageRole

logger = logging.getLogger(__name__)


class ConversationEvaluator:
    """对话评估器，用于评估对话质量"""
    
    # 评估维度定义
    EVALUATION_DIMENSIONS = {
        "relevance": {
            "name": "相关性",
            "description": "回答是否与用户问题相关",
            "weight": 0.25
        },
        "accuracy": {
            "name": "准确性",
            "description": "回答的信息是否准确、可靠",
            "weight": 0.25
        },
        "helpfulness": {
            "name": "有用性",
            "description": "回答是否对用户有帮助",
            "weight": 0.20
        },
        "completeness": {
            "name": "完整性",
            "description": "回答是否完整，是否回答了用户的所有问题",
            "weight": 0.15
        },
        "clarity": {
            "name": "清晰度",
            "description": "回答是否清晰易懂",
            "weight": 0.15
        }
    }
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        初始化对话评估器
        
        Args:
            llm_service: LLM 服务实例，如果为 None 则自动创建
        """
        self.llm_service = llm_service or LLMService()
        logger.info("对话评估器已初始化")
    
    async def evaluate_conversation_turn(
        self,
        user_message: str,
        assistant_message: str,
        context: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        评估一轮对话的质量
        
        Args:
            user_message: 用户消息
            assistant_message: 助手回复
            context: 上下文消息列表（可选，用于理解对话背景）
            
        Returns:
            评估结果字典，包含：
            - overall_score: 总体分数 (0-100)
            - dimension_scores: 各维度分数
            - evaluation: 评估说明
            - timestamp: 评估时间
        """
        try:
            # 构建评估 prompt
            system_prompt = self._build_evaluation_system_prompt()
            user_prompt = self._build_evaluation_user_prompt(
                user_message, assistant_message, context
            )
            
            # 使用 LLM 进行评估
            evaluation_text = await self.llm_service.chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            # 解析评估结果
            evaluation_result = self._parse_evaluation_result(evaluation_text)
            
            # 添加时间戳
            evaluation_result["timestamp"] = datetime.now().isoformat()
            
            logger.info(f"对话评估完成，总体分数: {evaluation_result.get('overall_score', 'N/A')}")
            return evaluation_result
            
        except Exception as e:
            logger.error(f"对话评估失败: {str(e)}", exc_info=True)
            # 返回默认评估结果
            return self._get_default_evaluation_result()
    
    def _build_evaluation_system_prompt(self) -> str:
        """构建评估系统提示"""
        dimensions_text = "\n".join([
            f"- {dim_id}: {dim_info['name']} ({dim_info['description']})"
            for dim_id, dim_info in self.EVALUATION_DIMENSIONS.items()
        ])
        
        return f"""你是一个专业的对话质量评估专家。请根据以下维度对对话进行评估：

评估维度：
{dimensions_text}

评分标准：
- 每个维度评分范围：0-100 分
- 90-100: 优秀
- 80-89: 良好
- 70-79: 中等
- 60-69: 及格
- 0-59: 不及格

请以 JSON 格式返回评估结果，格式如下：
{{
    "overall_score": 85,
    "dimension_scores": {{
        "relevance": 90,
        "accuracy": 85,
        "helpfulness": 80,
        "completeness": 75,
        "clarity": 90
    }},
    "evaluation": "评估说明文字，简要说明各维度的评分理由"
}}

请确保：
1. 评分客观、公正
2. 评估说明简洁明了
3. 只返回 JSON 格式，不要添加其他文字"""
    
    def _build_evaluation_user_prompt(
        self,
        user_message: str,
        assistant_message: str,
        context: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """构建评估用户提示"""
        prompt_parts = []
        
        # 添加上下文（如果有）
        if context:
            context_text = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in context[-5:]  # 只使用最近 5 条上下文
            ])
            prompt_parts.append(f"对话上下文：\n{context_text}\n")
        
        # 添加当前对话
        prompt_parts.append(f"用户问题：\n{user_message}\n")
        prompt_parts.append(f"助手回复：\n{assistant_message}\n")
        prompt_parts.append("请对上述对话进行评估，返回 JSON 格式的评估结果。")
        
        return "\n".join(prompt_parts)
    
    def _parse_evaluation_result(self, evaluation_text: str) -> Dict[str, Any]:
        """
        解析评估结果文本
        
        Args:
            evaluation_text: LLM 返回的评估文本
            
        Returns:
            解析后的评估结果字典
        """
        import json
        import re
        
        try:
            # 方法1: 尝试提取代码块中的 JSON（```json ... ```）
            code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
            code_block_match = re.search(code_block_pattern, evaluation_text, re.DOTALL)
            if code_block_match:
                json_str = code_block_match.group(1)
                try:
                    result = json.loads(json_str)
                    return self._normalize_evaluation_result(result)
                except json.JSONDecodeError:
                    pass
            
            # 方法2: 尝试提取第一个完整的 JSON 对象（支持嵌套）
            # 使用更智能的方法：找到第一个 {，然后找到匹配的 }
            brace_count = 0
            start_idx = evaluation_text.find('{')
            if start_idx >= 0:
                for i in range(start_idx, len(evaluation_text)):
                    if evaluation_text[i] == '{':
                        brace_count += 1
                    elif evaluation_text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_str = evaluation_text[start_idx:i+1]
                            try:
                                result = json.loads(json_str)
                                return self._normalize_evaluation_result(result)
                            except json.JSONDecodeError:
                                break
            
            # 方法3: 尝试直接解析整个文本
            result = json.loads(evaluation_text)
            return self._normalize_evaluation_result(result)
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"解析评估结果失败，使用默认值: {str(e)}")
            logger.debug(f"评估文本内容: {evaluation_text[:500]}")
            return self._get_default_evaluation_result()
    
    def _normalize_evaluation_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        规范化评估结果
        
        Args:
            result: 原始评估结果
            
        Returns:
            规范化后的评估结果
        """
        # 确保有 overall_score
        if "overall_score" not in result:
            # 从维度分数计算总体分数
            dimension_scores = result.get("dimension_scores", {})
            if dimension_scores:
                weights = {
                    dim_id: dim_info["weight"]
                    for dim_id, dim_info in self.EVALUATION_DIMENSIONS.items()
                }
                overall = sum(
                    dimension_scores.get(dim_id, 0) * weights.get(dim_id, 0.2)
                    for dim_id in self.EVALUATION_DIMENSIONS.keys()
                )
                result["overall_score"] = round(overall, 2)
            else:
                result["overall_score"] = 0
        
        # 确保有所有维度分数
        if "dimension_scores" not in result:
            result["dimension_scores"] = {}
        
        for dim_id in self.EVALUATION_DIMENSIONS.keys():
            if dim_id not in result["dimension_scores"]:
                result["dimension_scores"][dim_id] = 0
        
        # 确保有评估说明
        if "evaluation" not in result:
            result["evaluation"] = "评估完成"
        
        # 限制分数范围
        result["overall_score"] = max(0, min(100, round(result["overall_score"], 2)))
        for dim_id in result["dimension_scores"]:
            result["dimension_scores"][dim_id] = max(
                0, min(100, round(result["dimension_scores"][dim_id], 2))
            )
        
        return result
    
    def _get_default_evaluation_result(self) -> Dict[str, Any]:
        """获取默认评估结果（评估失败时使用）"""
        return {
            "overall_score": 0,
            "dimension_scores": {
                dim_id: 0
                for dim_id in self.EVALUATION_DIMENSIONS.keys()
            },
            "evaluation": "评估失败，无法获取评估结果",
            "timestamp": datetime.now().isoformat(),
            "error": True
        }
    
    def format_evaluation_summary(self, evaluation_result: Dict[str, Any]) -> str:
        """
        格式化评估结果为可读文本
        
        Args:
            evaluation_result: 评估结果字典
            
        Returns:
            格式化的评估摘要文本
        """
        overall_score = evaluation_result.get("overall_score", 0)
        dimension_scores = evaluation_result.get("dimension_scores", {})
        evaluation = evaluation_result.get("evaluation", "")
        
        # 构建摘要
        summary_parts = [f"总体分数: {overall_score}/100\n"]
        
        # 添加各维度分数
        summary_parts.append("各维度分数：")
        for dim_id, dim_info in self.EVALUATION_DIMENSIONS.items():
            score = dimension_scores.get(dim_id, 0)
            summary_parts.append(f"  - {dim_info['name']}: {score}/100")
        
        # 添加评估说明
        if evaluation:
            summary_parts.append(f"\n评估说明：{evaluation}")
        
        return "\n".join(summary_parts)

