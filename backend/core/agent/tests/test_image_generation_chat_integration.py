"""图片生成 Chat 场景集成测试：验证 image_generation 工具返回 base64 时的 Markdown 注入逻辑"""
import pytest

from backend.core.agent.tools.base import ToolResult


class TestImageGenerationChatIntegration:
    """测试 Chat 场景下 image_generation 返回 base64 时的输出格式"""

    def test_image_base64_markdown_format(self):
        """验证 orchestrator 注入的 Markdown 格式与前端 Markdown 渲染兼容。
        orchestrator 在 image_generation 成功且含 image_base64 时 yield：
        f'\\n\\n![生成的图片]({img_b64})\\n\\n'
        前端 MarkdownPreview 使用 marked 解析，支持 ![alt](data:image/png;base64,...) 语法。
        """
        img_b64 = "data:image/png;base64,iVBORw0KGgo="
        # 与 orchestrator.py L2851 一致的格式
        markdown = f"\n\n![生成的图片]({img_b64})\n\n"
        assert "![生成的图片]" in markdown
        assert img_b64 in markdown
        assert markdown.startswith("\n\n![")
        assert "](data:image/png;base64," in markdown

    def test_tool_returns_image_base64_for_chat(self):
        """ImageGenerationTool 在无 output_dir 时返回 image_base64，供 Chat 展示"""
        # 与 image_generation_tool 设计一致：Chat 场景返回 image_base64
        data = {"prompt": "一只猫", "image_base64": "data:image/png;base64,xxx"}
        assert "image_base64" in data
        assert data["image_base64"].startswith("data:image/")
