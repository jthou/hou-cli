"""user_facing_error 单元测试（2026-03-21）"""
import pytest
from backend.services.llm.user_facing_error import (
    insufficient_balance_user_message,
    is_insufficient_balance_error,
    llm_error_message_for_user,
)


class _E402:
    status_code = 402


def test_insufficient_balance_402():
    msg = llm_error_message_for_user(
        Exception("Error code: 402 - {'error': {'message': 'Insufficient Balance'}}")
    )
    assert msg is not None
    assert "余额不足" in msg


def test_status_code_attr():
    assert llm_error_message_for_user(_E402()) is not None
    assert "余额不足" in llm_error_message_for_user(_E402())


def test_unknown_returns_none():
    assert llm_error_message_for_user(Exception("random failure")) is None


def test_insufficient_balance_user_message_contains_provider_model():
    m = insufficient_balance_user_message("deepseek", "deepseek-chat")
    assert "DeepSeek" in m
    assert "deepseek-chat" in m
    assert "deepseek" in m


def test_is_insufficient_balance_error():
    assert is_insufficient_balance_error(Exception("Error code: 402 - Insufficient Balance"))
    assert not is_insufficient_balance_error(Exception("timeout"))
