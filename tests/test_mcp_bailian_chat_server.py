# 时间：2026-04-04；理由：MCP 脚本内百炼模型校验与列表工具逻辑需回归；方法：无网络、仅 import 与纯函数路径
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.mark.asyncio
async def test_mcp_registers_bailian_chat_tools():
    from scripts.mcp_bailian_chat_server import _build_mcp

    mcp = _build_mcp()
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert "hou_bailian_complete" in names
    assert "hou_bailian_complete_vision" in names
    assert "hou_bailian_list_models" in names
    assert "hou_bailian_ping" in names
    assert "hou_bailian_text_to_image" in names
    assert "hou_bailian_text_to_video" in names
    assert "hou_bailian_tts" in names
    assert "hou_bailian_speech_to_text" in names


def test_require_bailian_model_rejects_gpt_style():
    from scripts import mcp_bailian_chat_server as mod

    with pytest.raises(ValueError, match="仅支持百炼"):
        mod._require_bailian_model("gpt-4o")


def test_require_bailian_model_accepts_qwen3_max():
    from scripts import mcp_bailian_chat_server as mod

    mod._require_bailian_model("qwen3-max")


def test_require_bailian_model_accepts_bailian_prefix():
    from scripts import mcp_bailian_chat_server as mod

    mod._require_bailian_model("bailian-qwen3-max")


def test_parse_vision_image_urls_https():
    from scripts import mcp_bailian_chat_server as mod

    assert mod._parse_vision_image_urls(["https://a.com/x.png"]) == ["https://a.com/x.png"]


def test_parse_vision_image_urls_rejects_file_scheme():
    from scripts import mcp_bailian_chat_server as mod

    with pytest.raises(ValueError, match="非法项"):
        mod._parse_vision_image_urls(["file:///tmp/x.png"])


def test_parse_vision_image_urls_max_n():
    from scripts import mcp_bailian_chat_server as mod

    with pytest.raises(ValueError, match="超过上限"):
        mod._parse_vision_image_urls(
            ["https://a.com/1.png", "https://a.com/2.png"],
            max_n=1,
        )
