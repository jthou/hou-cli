"""_skip_tool_recommended_model_switch 行为（深度思考 / 显式 model）。"""
# 时间：2026-03-14；理由：深度思考不因 google_search 等工具元数据改模型；方法：单测辅助函数

from backend.core.agent.orchestrator import _skip_tool_recommended_model_switch


def test_skip_when_deep_thinking():
    assert _skip_tool_recommended_model_switch({"deep_thinking": True, "model": "reasoning"}) is True


def test_skip_when_user_model_set():
    assert _skip_tool_recommended_model_switch({"model": "qwen3-max"}) is True


def test_no_skip_when_empty_context():
    assert _skip_tool_recommended_model_switch({}) is False
    assert _skip_tool_recommended_model_switch(None) is False
