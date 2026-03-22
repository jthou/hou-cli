# 时间：2026-03-22；理由：通用对话误匹配视频技能导致缺 input_file；方法：_general_chat_allows_skill_prematch 行为单测（pytest --noconftest 可避根 conftest）
from __future__ import annotations

import os

import pytest

from backend.core.agent.general_chat_skill_gate import general_chat_allows_skill_prematch


def test_allows_prematch_false_for_news_style_paste():
    text = (
        "苹果 CEO 库克：人工智能是对人能力的放大，而不是对人的取代\n"
        "2026/3/21 19:27:09 来源：IT之家\n"
        "库克表示：「现在是一个非常令人兴奋的时代……」"
    )
    assert general_chat_allows_skill_prematch(text) is False


def test_allows_prematch_true_for_url():
    assert general_chat_allows_skill_prematch("请下载 https://www.bilibili.com/video/BV1xx 的字幕") is True


def test_allows_prematch_true_for_local_path():
    assert general_chat_allows_skill_prematch("剪辑 /Users/me/Videos/a.mp4 00:01:00 到 00:02:00") is True


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("off", False),
        ("never", False),
        ("on", True),
        ("always", True),
    ],
)
def test_env_general_chat_skill_prematch(mode, expected, monkeypatch):
    monkeypatch.setenv("GENERAL_CHAT_SKILL_PREMATCH", mode)
    t = "随便聊聊人工智能"
    assert general_chat_allows_skill_prematch(t) is expected
