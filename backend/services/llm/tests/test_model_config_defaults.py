"""ModelConfigManager 默认与空环境变量行为。

时间：2026-03-13；理由：REASONING_MODEL 空串曾导致误用或需与 env.example 一致；方法：对 get_*_model 做单测。
"""
from __future__ import annotations

import pytest

import backend.services.llm.model_config as model_config_module


@pytest.fixture
def fresh_manager(monkeypatch):
    """各用例独立单例，避免跨用例污染。"""
    model_config_module._model_config_manager = None
    yield
    model_config_module._model_config_manager = None


def test_reasoning_model_unset_uses_qwen_default(fresh_manager, monkeypatch):
    monkeypatch.delenv("REASONING_MODEL", raising=False)
    m = model_config_module.get_model_config_manager()
    assert m.get_reasoning_model() == model_config_module.DEFAULT_REASONING_MODEL == "qwen3-max"


def test_reasoning_model_blank_uses_qwen_default(fresh_manager, monkeypatch):
    monkeypatch.setenv("REASONING_MODEL", "  \t  ")
    m = model_config_module.get_model_config_manager()
    assert m.get_reasoning_model() == "qwen3-max"


def test_chat_model_blank_uses_default(fresh_manager, monkeypatch):
    monkeypatch.setenv("CHAT_MODEL", "")
    m = model_config_module.get_model_config_manager()
    assert m.get_chat_model() == model_config_module.DEFAULT_CHAT_MODEL


def test_env_model_nonempty_helper(monkeypatch):
    assert model_config_module._env_model_nonempty("MISSING_KEY_XYZ_123", "fallback") == "fallback"
    monkeypatch.setenv("TMP_MODEL_KEY_FOR_TEST", "  ")
    assert model_config_module._env_model_nonempty("TMP_MODEL_KEY_FOR_TEST", "qwen3-max") == "qwen3-max"
