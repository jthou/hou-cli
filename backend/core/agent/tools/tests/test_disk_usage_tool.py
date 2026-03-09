"""disk_usage 工具测试"""
import pytest

from backend.core.agent.tools.builtin.disk_usage_tool import DiskUsageTool


class TestDiskUsageTool:
    def test_tool_implements_interface(self):
        tool = DiskUsageTool()
        assert tool.name == "disk_usage"
        assert hasattr(tool, "execute")

    def test_execute_root_path(self):
        tool = DiskUsageTool()
        result = tool.execute(path="/")
        assert result.success
        assert result.data is not None
        summary = result.data.get("summary", {})
        assert "total_gb" in summary
        assert "used_gb" in summary
        assert "free_gb" in summary
        assert "used_percent" in summary
        assert summary["total_gb"] > 0
        assert result.data.get("report")

    def test_execute_invalid_path(self):
        tool = DiskUsageTool()
        result = tool.execute(path="/nonexistent_path_xyz_123")
        assert not result.success
        assert result.error

    def test_execute_default_path(self):
        tool = DiskUsageTool()
        result = tool.execute()
        assert result.success
        assert result.data["path"] == "/"
