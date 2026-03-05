"""长文本转图片提示词工具 - 将长文本提炼为适合文生图的短提示词"""
import asyncio
import logging
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter

logger = logging.getLogger(__name__)

TEXT_TO_PROMPT_SYSTEM = """你是图片提示词专家。将用户提供的长文本提炼成适合文生图模型的短提示词。

要求：
- 输出 50–200 字，描述画面主体、风格、氛围
- 只输出提示词本身，不要解释
- 保留关键视觉元素（人物、场景、物体、光线等）
- 适合 DALL-E、Stable Diffusion、通义万相等模型"""


class TextToImagePromptTool(Tool):
    """将长文本提炼为适合文生图的短提示词"""

    def __init__(self):
        super().__init__(
            name="text_to_image_prompt",
            description=(
                "将长文本（文章、摘要等）提炼成适合文生图的短提示词。"
                "当用户提供长文本并要求生成配图时，先调用此工具得到短提示词，"
                "再调用 image_generation。"
            ),
            parameters=[
                ToolParameter("text", "string", "要提炼的长文本", required=True),
                ToolParameter(
                    "max_length", "integer", "提示词最大字数，默认 150",
                    required=False, default=150
                ),
                ToolParameter(
                    "style_hint", "string", "风格提示，如写实、动漫、水彩",
                    required=False
                ),
            ],
            recommended_model="chat",
        )
        from backend.services.llm.llm_service import LLMService
        self.llm_service = LLMService()

    def execute(self, **kwargs) -> ToolResult:
        """同步执行：orchestrator 使用 execute_async"""
        return asyncio.run(self._execute_async(**kwargs))

    async def _execute_async(self, **kwargs) -> ToolResult:
        """异步执行：调用 LLM 提炼提示词"""
        text = (kwargs.get("text") or "").strip()
        if not text:
            return ToolResult(success=False, error="text 不能为空")

        max_length = kwargs.get("max_length") or 150
        style_hint = (kwargs.get("style_hint") or "").strip()

        user_prompt = text
        if style_hint:
            user_prompt = f"风格要求：{style_hint}\n\n待提炼文本：\n{text}"
        if max_length and max_length != 150:
            user_prompt = f"{user_prompt}\n\n（提示词请控制在 {max_length} 字以内）"

        try:
            response = await self.llm_service.chat(
                system_prompt=TEXT_TO_PROMPT_SYSTEM,
                user_prompt=user_prompt,
            )
        except Exception as e:
            logger.exception("提炼提示词失败")
            return ToolResult(success=False, error=str(e))

        prompt = (response or "").strip()
        if not prompt:
            return ToolResult(success=False, error="LLM 未返回有效提示词")

        return ToolResult(success=True, data={"prompt": prompt})
