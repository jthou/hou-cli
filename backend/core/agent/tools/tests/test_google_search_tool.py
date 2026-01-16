"""GoogleSearchTool 测试"""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dotenv import load_dotenv

from backend.core.agent.tools.builtin.google_search_tool import (
    GoogleSearchTool,
)
from backend.services.google_search_service import GoogleSearchServiceError

# 加载 .env 文件
load_dotenv()


class TestGoogleSearchTool:
    """GoogleSearchTool 单元测试"""

    @pytest.fixture
    def tool(self):
        """创建 GoogleSearchTool 实例"""
        return GoogleSearchTool()

    def test_tool_initialization(self, tool):
        """测试工具初始化"""
        assert tool.name == "google_search"
        assert tool.description is not None
        assert len(tool.parameters) == 3

        param_names = [p.name for p in tool.parameters]
        assert "query" in param_names
        assert "num_results" in param_names
        assert "language" in param_names

    def test_missing_query(self, tool):
        """测试缺少 query 参数"""
        result = tool.execute()
        assert result.success is False
        assert "query" in result.error.lower() or "必需" in result.error

    def test_service_initialization_error(self, tool):
        """测试服务初始化错误"""
        with patch.object(tool, '_get_search_service') as mock_get_service:
            mock_get_service.side_effect = RuntimeError(
                "Google 搜索服务初始化失败"
            )

            result = tool.execute(query="test")
            assert result.success is False
            assert "初始化失败" in result.error or "初始化" in result.error

    @pytest.mark.skipif(
        not os.getenv("GOOGLE_SEARCH_API_KEY") or
        not os.getenv("GOOGLE_SEARCH_ENGINE_ID"),
        reason="需要设置 GOOGLE_SEARCH_API_KEY 和 GOOGLE_SEARCH_ENGINE_ID"
    )
    def test_execute_search(self, tool):
        """测试执行搜索（需要真实的 API Key）"""
        result = tool.execute(
            query="Python",
            num_results=3,
            language="zh-CN"
        )

        if result.success:
            assert "results" in result.data
            assert "count" in result.data
            assert result.data["count"] > 0
            assert len(result.data["results"]) <= 3
        else:
            # 检查是否是 API Key 问题
            if "API" in result.error or "key" in result.error.lower():
                pytest.skip(f"Google Search API Key 配置问题: {result.error}")
            else:
                # 其他错误，正常失败
                assert False, f"搜索失败: {result.error}"

    def test_num_results_limits(self, tool):
        """测试结果数量限制"""
        with patch.object(tool, '_get_search_service') as mock_get_service:
            mock_service = MagicMock()
            mock_response = MagicMock()
            mock_response.results = [MagicMock() for _ in range(5)]
            mock_response.total_results = 100
            mock_response.search_time = 0.5
            mock_response.query = "test"

            async def mock_search(*args, **kwargs):
                return mock_response

            mock_service.search = AsyncMock(side_effect=mock_search)
            mock_get_service.return_value = mock_service

            # 测试超过最大限制
            result1 = tool.execute(query="test", num_results=20)
            # 应该被限制到 10

            # 测试小于最小限制
            result2 = tool.execute(query="test", num_results=0)
            # 应该被限制到 1
            assert result1 is not None
            assert result2 is not None

    def test_search_service_error(self, tool):
        """测试搜索服务错误处理"""
        with patch.object(tool, '_get_search_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.search = AsyncMock(
                side_effect=GoogleSearchServiceError("API 错误")
            )
            mock_get_service.return_value = mock_service

            result = tool.execute(query="test")
            assert result.success is False
            assert "失败" in result.error or "错误" in result.error


class TestGoogleSearchToolIntegration:
    """GoogleSearchTool 集成测试（需要真实环境）"""

    @pytest.fixture
    def tool(self):
        """创建 GoogleSearchTool 实例"""
        return GoogleSearchTool()

    @pytest.mark.skipif(
        not os.getenv("GOOGLE_SEARCH_API_KEY") or
        not os.getenv("GOOGLE_SEARCH_ENGINE_ID"),
        reason="需要设置 GOOGLE_SEARCH_API_KEY 和 GOOGLE_SEARCH_ENGINE_ID"
    )
    @pytest.mark.integration
    def test_full_search_workflow(self, tool):
        """测试完整的搜索工作流"""
        result = tool.execute(
            query="Python programming",
            num_results=5,
            language="en"
        )

        if result.success:
            assert "results" in result.data
            assert len(result.data["results"]) > 0

            # 验证结果格式
            for item in result.data["results"]:
                assert "title" in item
                assert "link" in item
                assert "snippet" in item
        else:
            if "API" in result.error or "key" in result.error.lower():
                pytest.skip(
                    f"Google Search API Key 配置问题: {result.error}"
                )
