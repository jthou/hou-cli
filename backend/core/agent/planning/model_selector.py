"""模型选择器：根据任务与用户指定智能选择 chat/code/reasoning 模型"""
import asyncio
import logging
import os
import re
from typing import Any, Dict, Optional

from backend.core.agent.system_prompt_templates import MODEL_SELECTOR_PROMPT

logger = logging.getLogger(__name__)


def resolve_user_model(model_spec: str) -> str:
    """
    解析用户指定的模型（chat/code/reasoning 或具体模型名）

    Args:
        model_spec: 用户指定，如 "chat"、"code"、"reasoning" 或 "deepseek-chat"

    Returns:
        解析后的模型名称

    Raises:
        ValueError: 无效的模型类型或无法校验的模型名
    """
    from backend.services.llm.model_config import get_model_config_manager

    spec = (model_spec or "").strip().lower()
    if not spec:
        raise ValueError("model 不能为空")
    config_manager = get_model_config_manager()
    if spec == "chat":
        return config_manager.get_chat_model()
    if spec == "code":
        return config_manager.get_code_model()
    if spec == "reasoning":
        return config_manager.get_reasoning_model()
    config = config_manager.get_model_config(spec)
    return config.model_name


async def select_model(
    task: str,
    context: Optional[Dict] = None,
    *,
    llm_service: Any,
    complexity_analyzer: Optional[Any] = None,
) -> str:
    """
    使用推理模型智能选择最适合的模型；若 context 含 model 则优先使用用户指定

    Args:
        task: 用户任务
        context: 上下文（可选），含 model 时使用用户指定
        llm_service: LLM 服务实例（需有 chat、set_model、model 属性）
        complexity_analyzer: 复杂度分析器（可选），需有 analyze_task 方法

    Returns:
        选定的模型名称
    """
    from backend.services.llm.model_config import get_model_config_manager

    # 用户指定模型时优先使用
    user_model = (context or {}).get("model")
    if user_model and str(user_model).strip():
        return resolve_user_model(str(user_model).strip())

    # 如果禁用了智能模型选择，直接返回默认模型
    if os.getenv("DISABLE_SMART_MODEL_SELECTION", "false").lower() == "true":
        config_manager = get_model_config_manager()
        return config_manager.get_chat_model()

    config_manager = get_model_config_manager()
    chat_model = config_manager.get_chat_model()
    code_model = config_manager.get_code_model()
    reasoning_model = config_manager.get_reasoning_model()

    # ===== 1. 任务复杂度评估 =====
    if complexity_analyzer:
        try:
            complexity_analysis = complexity_analyzer.analyze_task(task)
            complexity_score = complexity_analysis.get("score", 0.0)
            if complexity_score >= 0.5:
                logger.debug(f"任务复杂度: COMPLEX (score={complexity_score:.2f}), 选择推理模型")
                return reasoning_model
            elif complexity_score < 0.2:
                logger.debug(f"任务复杂度: SIMPLE (score={complexity_score:.2f}), 使用快速规则判断")
            else:
                logger.debug(f"任务复杂度: MEDIUM (score={complexity_score:.2f}), 结合快速规则判断")
        except Exception as e:
            logger.warning(f"复杂度评估失败: {e}，继续使用快速规则判断")

    # ===== 2. 快速规则判断 =====
    task_lower = task.lower()

    code_keywords = [
        "执行", "execute", "运行", "run", "启动", "start",
        "ls", "cat", "cd", "mkdir", "rm", "mv", "cp", "grep", "find", "ps", "kill",
        "编写", "write", "创建", "create", "生成代码", "generate code",
        "函数", "function", "方法", "method", "脚本", "script", "程序", "program",
        "代码", "code", "编程", "programming", "开发", "develop",
        "调试", "debug", "测试", "test", "单元测试", "unit test",
        "编译", "compile", "构建", "build", "打包", "package",
    ]
    code_generation_keywords = [
        "代码", "code", "编程", "program", "程序", "programming",
        "实现", "implement", "开发", "develop", "创建", "create",
    ]
    reasoning_keywords = [
        "分析", "analyze", "analysis", "解析", "parse", "理解", "understand",
        "推理", "reasoning", "思考", "think", "thinking", "推断", "infer",
        "策略", "strategy", "计划", "plan", "规划", "planning", "设计", "design",
        "解决", "solve", "处理", "handle", "应对", "deal with",
        "为什么", "why", "如何", "how", "什么", "what", "哪里", "where",
        "报告", "report", "总结", "summary", "概述", "overview", "评估", "evaluate",
        "研究", "research", "调研", "investigate", "调查", "investigation", "探索", "explore",
        "然后", "then", "接着", "next", "最后", "finally", "首先", "first", "其次", "second",
        "多步骤", "multi-step", "步骤", "step", "流程", "process",
        "比较", "compare", "对比", "contrast", "判断", "judge",
        "优化", "optimize", "改进", "improve", "提升", "enhance", "重构", "refactor",
    ]
    strong_reasoning_keywords = [
        "分析", "analyze", "研究", "research", "报告", "report",
        "评估", "evaluate", "比较", "compare", "优化", "optimize",
        "总结", "summary", "概述", "overview", "判断", "judge",
    ]
    reasoning_patterns = [
        r"生成.*文章", r"生成.*报告", r"生成.*分析", r"撰写.*报告",
        r"编写.*报告", r"创建.*报告", r"制作.*报告", r"输出.*报告",
        r"生成.*总结", r"生成.*评估", r"生成.*对比", r"生成.*比较",
    ]

    reasoning_keyword_count = sum(1 for kw in reasoning_keywords if kw in task_lower)
    if reasoning_keyword_count > 0:
        code_gen_count = sum(1 for kw in code_generation_keywords if kw in task_lower)
        has_strong_reasoning = any(kw in task_lower for kw in strong_reasoning_keywords)
        if has_strong_reasoning or reasoning_keyword_count > code_gen_count:
            logger.debug(f"推理关键词匹配: count={reasoning_keyword_count}, 选择推理模型")
            return reasoning_model

    if any(re.search(p, task_lower) for p in reasoning_patterns):
        logger.debug("推理模式匹配，选择推理模型")
        return reasoning_model

    code_keyword_count = sum(1 for kw in code_keywords if kw in task_lower)
    if code_keyword_count > 0:
        if reasoning_keyword_count == 0 or code_keyword_count > reasoning_keyword_count * 2:
            logger.debug(f"代码关键词匹配: count={code_keyword_count}, 选择代码模型")
            return code_model

    code_gen_count = sum(1 for kw in code_generation_keywords if kw in task_lower)
    if code_gen_count > 0 and reasoning_keyword_count == 0:
        logger.debug(f"代码生成关键词匹配: count={code_gen_count}, 选择代码模型")
        return code_model

    if len(task.strip()) < 20:
        return chat_model

    # ===== 3. LLM 分析 =====
    model_selection_prompt = f"""分析以下任务，决定应该使用哪个模型：

任务：{task}

可选模型：
1. {chat_model}: 适用于日常对话、文本生成、翻译、信息检索等一般性任务
2. {reasoning_model}: 适用于需要复杂推理的任务，如数学推理、逻辑分析、策略制定、问题解决、工具选择决策等
3. {code_model}: 适用于代码生成、代码补全、代码修复、代码审查、编程相关任务，以及简单的命令执行（如 ls、cat、cd 等）

重要提示：
- 如果任务是执行简单的系统命令（如显示文件、查看目录、执行脚本等），应该使用 {code_model}
- 如果任务需要复杂的逻辑推理、多步骤分析、策略制定、工具选择，使用 {reasoning_model}
- 如果任务只是简单的命令执行，不要使用 {reasoning_model}，避免过度思考
- 如果任务是一般性对话或文本生成，使用 {chat_model}

请只返回模型名称（{chat_model}、{reasoning_model} 或 {code_model}），不要返回其他内容。"""

    try:
        original_model = llm_service.model
        llm_service.set_model(reasoning_model)
        try:
            analysis = await asyncio.wait_for(
                llm_service.chat(
                    system_prompt=MODEL_SELECTOR_PROMPT,
                    user_prompt=model_selection_prompt,
                ),
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            logger.warning("模型选择 LLM 调用超时，使用默认对话模型")
            llm_service.set_model(original_model)
            return chat_model

        llm_service.set_model(original_model)
        analysis = analysis.strip().lower()
        if reasoning_model.lower() in analysis or "reasoner" in analysis or "reasoning" in analysis:
            return reasoning_model
        elif code_model.lower() in analysis or "coder" in analysis or "code" in analysis:
            return code_model
        return chat_model
    except Exception as e:
        logger.warning(f"模型选择失败，使用默认对话模型: {e}")
        return chat_model
