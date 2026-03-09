"""Allowlist 评估器测试"""
import pytest
from backend.infrastructure.execution.allowlist import AllowlistEvaluator, AllowlistResult


class TestAllowlistEvaluator:
    """AllowlistEvaluator 测试"""

    @pytest.fixture
    def evaluator(self):
        return AllowlistEvaluator()

    def test_match_ls(self, evaluator):
        """ls 命令应命中"""
        r = evaluator.evaluate("ls -la /tmp", language="zsh")
        assert r.satisfied is True
        assert r.matched_pattern == "ls"

    def test_match_rm_tmp(self, evaluator):
        """rm -rf /tmp/foo 应命中"""
        r = evaluator.evaluate("rm -rf /tmp/foo", language="zsh")
        assert r.satisfied is True

    def test_match_rm_rel(self, evaluator):
        """rm -rf ./build 应命中"""
        r = evaluator.evaluate("rm -rf ./build", language="zsh")
        assert r.satisfied is True

    def test_match_rm_rel_no_slash(self, evaluator):
        """rm -rf build 应命中"""
        r = evaluator.evaluate("rm -rf build", language="zsh")
        assert r.satisfied is True

    def test_no_match_rm_root(self, evaluator):
        """rm -rf / 不应命中"""
        r = evaluator.evaluate("rm -rf /", language="zsh")
        assert r.satisfied is False

    def test_no_match_rm_etc(self, evaluator):
        """rm -rf /etc 不应命中"""
        r = evaluator.evaluate("rm -rf /etc", language="zsh")
        assert r.satisfied is False

    def test_match_cat(self, evaluator):
        """cat 文件应命中"""
        r = evaluator.evaluate("cat /tmp/test.txt", language="zsh")
        assert r.satisfied is True
        assert r.matched_pattern == "cat"

    def test_match_pwd(self, evaluator):
        """pwd 应命中"""
        r = evaluator.evaluate("pwd", language="zsh")
        assert r.satisfied is True

    def test_empty_command(self, evaluator):
        """空命令不应命中"""
        r = evaluator.evaluate("", language="zsh")
        assert r.satisfied is False
        r = evaluator.evaluate("   ", language="zsh")
        assert r.satisfied is False
