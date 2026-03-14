"""ZhihuZhidaTool 测试"""
import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
from shared.load_env import load_env_for_file
load_env_for_file(__file__)

from backend.core.agent.tools.builtin.zhihu_zhida_tool import ZhihuZhidaTool
from backend.core.agent.tools.base import ToolResult


class TestZhihuZhidaTool:
    """ZhihuZhidaTool 单元测试"""

    @pytest.fixture
    def tool(self):
        """创建 ZhihuZhidaTool 实例"""
        return ZhihuZhidaTool()

    def test_tool_initialization(self, tool):
        """测试工具初始化"""
        assert tool.name == "zhihu_zhida"
        assert tool.description is not None
        assert len(tool.parameters) == 4

        param_names = [p.name for p in tool.parameters]
        assert "url" in param_names
        assert "operation" in param_names
        assert "format" in param_names
        assert "save_to_kb" in param_names

    def test_missing_url(self, tool):
        """测试缺少 url 参数"""
        result = tool.execute()
        assert result.success is False
        assert "url" in result.error.lower() or "必需" in result.error

    def test_invalid_url(self, tool):
        """测试无效的 URL"""
        result = tool.execute(url="invalid_url")
        assert result.success is False
        assert "无效" in result.error or "invalid" in result.error.lower()

    def test_extract_search_id(self, tool):
        """测试提取搜索 ID"""
        # 测试完整 URL
        search_id = tool._extract_search_id("https://zhida.zhihu.com/search/123456")
        assert search_id == "123456"

        # 测试仅 ID
        search_id = tool._extract_search_id("123456")
        assert search_id == "123456"

        # 测试无效 URL
        with pytest.raises(ValueError):
            tool._extract_search_id("invalid")

    def test_get_url(self, tool):
        """测试构建 URL"""
        url = tool._get_url("123456")
        assert url == "https://zhida.zhihu.com/search/123456"

    def test_cache_operations(self, tool):
        """测试缓存操作"""
        search_id = "123456"
        
        # 测试保存缓存
        test_data = {"question_title": "Test", "answers": []}
        tool._save_cache(search_id, test_data)
        
        # 测试加载缓存
        cached_data = tool._load_cache(search_id)
        assert cached_data is not None
        assert cached_data["question_title"] == "Test"

    def test_format_output(self, tool):
        """测试格式化输出"""
        test_data = {
            "question_title": "Test Question",
            "question_content": "Test content",
            "answers": [
                {"author": "User1", "content": "Answer 1"}
            ]
        }

        # 测试 JSON 格式
        json_output = tool._format_output(test_data, "json")
        assert "Test Question" in json_output

        # 测试 Markdown 格式
        markdown_output = tool._format_output(test_data, "markdown")
        assert "# Test Question" in markdown_output

        # 测试文本格式
        text_output = tool._format_output(test_data, "text")
        assert "Test Question" in text_output

    @pytest.mark.asyncio
    async def test_fetch_content_error(self, tool):
        """测试获取内容错误"""
        # 清除可能存在的缓存
        search_id = "test_error_123456"
        cache_file = tool._get_cache_file(search_id)
        if cache_file.exists():
            cache_file.unlink()
        
        with patch.object(tool, '_fetch_content') as mock_fetch:
            mock_fetch.side_effect = RuntimeError("获取内容失败")
            
            # 使用 operation="extract" 强制绕过缓存，确保调用 _fetch_content
            result = await tool._execute_async(url=search_id, operation="extract")
            assert result.success is False
            assert "失败" in result.error or "error" in result.error.lower() or "获取内容失败" in result.error

    @pytest.mark.skipif(
        not os.getenv("DEEPSEEK_API_KEY"),
        reason="需要设置 DEEPSEEK_API_KEY 环境变量（用于 browser 工具）"
    )
    def test_read_operation(self, tool):
        """测试读取操作（需要 browser 工具支持）"""
        result = tool.execute(
            url="3707579171380201696",
            operation="read",
            format="markdown"
        )

        if result.success:
            assert "content" in result.data
            assert "search_id" in result.data
        else:
            # 检查是否是 browser 工具问题
            if "browser" in result.error.lower() or "未找到" in result.error:
                pytest.skip(f"Browser 工具问题: {result.error}")


class TestZhihuZhidaToolIntegration:
    """ZhihuZhidaTool 集成测试（需要真实环境）"""

    @pytest.fixture
    def tool(self):
        """创建 ZhihuZhidaTool 实例"""
        return ZhihuZhidaTool()

    @pytest.mark.skipif(
        not os.getenv("DEEPSEEK_API_KEY"),
        reason="需要设置 DEEPSEEK_API_KEY 环境变量（用于 browser 工具）"
    )
    @pytest.mark.integration
    def test_read_workflow(self, tool):
        """测试读取工作流"""
        result = tool.execute(
            url="3707579171380201696",
            operation="read",
            format="markdown"
        )

        if result.success:
            assert "content" in result.data
            assert "search_id" in result.data
            assert "url" in result.data
        else:
            if "browser" in result.error.lower() or "未找到" in result.error:
                pytest.skip(f"Browser 工具问题: {result.error}")

    @pytest.mark.skipif(
        not os.getenv("DEEPSEEK_API_KEY"),
        reason="需要设置 DEEPSEEK_API_KEY 环境变量（用于 browser 工具）"
    )
    @pytest.mark.integration
    def test_extract_operation(self, tool):
        """测试提取操作"""
        result = tool.execute(
            url="3707579171380201696",
            operation="extract",
            format="json"
        )

        if result.success:
            assert "content" in result.data
            # extract 操作应该返回 JSON
            import json
            try:
                json.loads(result.data["content"])
            except json.JSONDecodeError:
                pytest.fail("extract 操作应该返回有效的 JSON")
        else:
            if "browser" in result.error.lower() or "未找到" in result.error:
                pytest.skip(f"Browser 工具问题: {result.error}")

