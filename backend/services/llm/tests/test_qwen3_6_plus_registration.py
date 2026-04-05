import pytest
from openai.types.chat.chat_completion_chunk import ChoiceDelta

from backend.services.llm.llm_service import LLMService, extract_chat_completion_delta_reasoning
from backend.services.llm.model_registry import ModelRegistry
from backend.services.llm.model_token_limits import get_model_limits


def test_qwen3_6_plus_registered_in_registry_and_token_limits():
    assert "qwen3.6-plus" in ModelRegistry.BAILIAN_MODELS

    provider, actual = ModelRegistry.parse_model_name("qwen3.6-plus")
    assert provider == "bailian"
    assert actual == "qwen3.6-plus"

    assert get_model_limits("qwen3.6-plus") == (32_000, 8_000)


def test_qwen3_6_plus_supports_thinking(monkeypatch):
    # LLMService 初始化会读取 provider 的 API Key（这里避免依赖真实 .env）
    monkeypatch.setenv("DEEPSEEK_API_KEY", "dummy-deepseek-key-12345")
    monkeypatch.setenv("BAILIAN_API_KEY", "dummy-bailian-key-1234567890")

    llm = LLMService(model="qwen3.6-plus", provider="bailian")
    assert llm.supports_thinking is True


def test_bailian_enable_thinking_extra_body_only_for_thinking_models(monkeypatch):
    """时间：2026-04-04；理由：百炼须 extra_body 才有流式 reasoning_content；方法：与 llm_service._bailian_enable_thinking_extra_body 对齐"""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "dummy-deepseek-key-12345")
    monkeypatch.setenv("BAILIAN_API_KEY", "dummy-bailian-key-1234567890")

    plus = LLMService(model="qwen3.6-plus", provider="bailian")
    assert plus._bailian_enable_thinking_extra_body() == {"enable_thinking": True}

    plain = LLMService(model="qwen3-max", provider="bailian")
    assert plain._bailian_enable_thinking_extra_body() is None


def test_bailian_enable_thinking_respects_env_off(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "dummy-deepseek-key-12345")
    monkeypatch.setenv("BAILIAN_API_KEY", "dummy-bailian-key-1234567890")
    monkeypatch.setenv("BAILIAN_ENABLE_THINKING", "false")
    llm = LLMService(model="qwen3.6-plus", provider="bailian")
    assert llm._bailian_enable_thinking_extra_body() is None


def test_extract_chat_completion_delta_reasoning():
    d = ChoiceDelta.model_validate({"content": None, "reasoning_content": "step"})
    assert extract_chat_completion_delta_reasoning(d) == "step"
    assert extract_chat_completion_delta_reasoning(None) is None

