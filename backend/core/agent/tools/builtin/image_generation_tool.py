"""图像生成工具 - 根据文本描述生成图片"""
import asyncio
import logging
from typing import Optional

from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter

logger = logging.getLogger(__name__)


class ImageGenerationTool(Tool):
    """文生图工具，供 chat agent 调用，内部调用 ImageGenService"""

    def __init__(self):
        super().__init__(
            name="image_generation",
            description=(
                "根据文本描述生成图片。支持万相、通义等模型。"
                "当用户要求画图、生成图片、文生图时使用此工具。"
                "提示词建议 50–200 字，描述画面主体、风格、氛围。"
            ),
            parameters=[
                ToolParameter("prompt", "string", "图片描述（必填，建议 50–200 字）", required=True),
                ToolParameter(
                    "model",
                    "string",
                    "模型，默认 wan2.6-t2i",
                    required=False,
                    default="wan2.6-t2i",
                    enum=["wan2.6-t2i", "wan2.6-image", "qwen-image-max-2025-12-30", "qwen-image-plus-2026-01-09"],
                ),
                ToolParameter(
                    "size",
                    "string",
                    "尺寸",
                    required=False,
                    default="1024*1024",
                    enum=["1024*1024", "1280*720", "720*1280", "1280*1280"],
                ),
                ToolParameter("output_dir", "string", "保存目录（可选，不填则返回 base64 便于 Chat 展示）", required=False),
            ],
            recommended_model="chat",
        )

    def execute(self, **kwargs) -> ToolResult:
        """同步执行：orchestrator 使用 execute_async，此处供测试等同步场景"""
        return asyncio.run(self._execute_async(**kwargs))

    async def _execute_async(self, **kwargs) -> ToolResult:
        """异步执行"""
        prompt = (kwargs.get("prompt") or "").strip()
        if not prompt:
            return ToolResult(success=False, error="prompt 不能为空")

        model = kwargs.get("model") or "wan2.6-t2i"
        size = kwargs.get("size") or "1024*1024"
        output_dir = (kwargs.get("output_dir") or "").strip() or None

        try:
            from backend.services.llm.image_gen_service import ImageGenService

            svc = ImageGenService()
            result = await svc.generate(
                prompt=prompt,
                model=model,
                size=size,
                n=1,
                output_dir=output_dir,
            )
        except Exception as e:
            logger.exception("图像生成失败")
            return ToolResult(success=False, error=str(e))

        images = result.get("images") or []
        if not images:
            return ToolResult(success=False, error="未生成图片")

        # Chat 场景：无 output_dir 时返回 base64 便于前端直接展示
        data = {
            "prompt": prompt,
            "output_file": result.get("output_file") or "",
            "output_dir": result.get("output_dir") or "",
        }
        if not output_dir and images:
            img_src = images[0]
            if img_src.startswith(("http://", "https://")):
                # 下载为 base64 供 Chat 展示
                import httpx
                async with httpx.AsyncClient(timeout=60.0) as client:
                    r = await client.get(img_src)
                    r.raise_for_status()
                    import base64
                    data["image_base64"] = f"data:image/png;base64,{base64.b64encode(r.content).decode()}"
            elif img_src.startswith("data:"):
                data["image_base64"] = img_src
            else:
                data["image_base64"] = img_src

        return ToolResult(success=True, data=data)
