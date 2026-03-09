"""ProcessRegistry 测试"""
import pytest
from backend.infrastructure.execution.process_registry import (
    ProcessRegistry,
    ProcessSession,
    get_process_registry,
)


class TestProcessRegistry:
    """ProcessRegistry 测试"""

    @pytest.fixture
    def registry(self):
        return ProcessRegistry(ttl_minutes=60)

    def test_add_get(self, registry):
        """add → get 应返回相同 session"""
        s = ProcessSession(
            id="ps_test1",
            command="echo hi",
            pid=123,
            cwd="/tmp",
            started_at=0
        )
        registry.add(s)
        got = registry.get("ps_test1")
        assert got is s
        assert got.command == "echo hi"

    def test_list_running(self, registry):
        """list_running 应返回会话"""
        s = ProcessSession(id="ps_1", command="ls", pid=1, cwd="/", started_at=0)
        registry.add(s)
        items = registry.list_running()
        assert len(items) == 1
        assert items[0].id == "ps_1"

    def test_mark_backgrounded(self, registry):
        """mark_backgrounded 应设置 backgrounded=True"""
        s = ProcessSession(id="ps_1", command="ls", pid=1, cwd="/", started_at=0)
        registry.add(s)
        registry.mark_backgrounded("ps_1")
        assert registry.get("ps_1").backgrounded is True

    def test_append_output(self, registry):
        """append_output 应累积到 aggregated"""
        s = ProcessSession(id="ps_1", command="ls", pid=1, cwd="/", started_at=0)
        registry.add(s)
        registry.append_output("ps_1", "hello\n", "")
        registry.append_output("ps_1", "world\n", "err\n")
        assert "hello" in s.aggregated
        assert "world" in s.aggregated
        assert "err" in s.aggregated

    def test_tail(self, registry):
        """tail 应返回最后 N 字符"""
        s = ProcessSession(id="ps_1", command="ls", pid=1, cwd="/", started_at=0)
        registry.add(s)
        registry.append_output("ps_1", "x" * 5000, "")
        t = registry.tail_output("ps_1", 100)
        assert len(t) == 100
        assert t == "x" * 100

    def test_remove_exited(self, registry):
        """remove 仅可移除已退出的"""
        s = ProcessSession(id="ps_1", command="ls", pid=1, cwd="/", started_at=0, exited=True)
        registry.add(s)
        ok = registry.remove("ps_1")
        assert ok is True
        assert registry.get("ps_1") is None

    def test_remove_running_fails(self, registry):
        """remove 运行中的应失败"""
        s = ProcessSession(id="ps_1", command="ls", pid=1, cwd="/", started_at=0, exited=False)
        registry.add(s)
        ok = registry.remove("ps_1")
        assert ok is False
        assert registry.get("ps_1") is not None
