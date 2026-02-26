"""管道解析逻辑单元测试（设计 7.1 追溯表 3.4 验证方式）。"""
import pytest
from backend.infrastructure.pipeline_resolve import resolve_input_bindings_from_result


class TestResolveInputBindingsFromResult:
    """resolve_input_bindings_from_result 单元测试"""

    def test_empty_bindings_returns_empty(self):
        assert resolve_input_bindings_from_result({"data": {}}, None) == {}
        assert resolve_input_bindings_from_result({"data": {}}, {}) == {}

    def test_single_path_result_data_output_file(self):
        upstream = {"status": "success", "data": {"output_file": "/path/to/out.mp3"}}
        bindings = {"input_file": "result.data.output_file"}
        # 路径以 result 为根，即 upstream 自身是 result，所以 data.output_file
        out = resolve_input_bindings_from_result(upstream, bindings)
        assert out == {"input_file": "/path/to/out.mp3"}

    def test_path_with_result_prefix_stripped(self):
        upstream = {"data": {"output_file": "/out.mp3"}}
        bindings = {"input_file": "result.data.output_file"}
        assert resolve_input_bindings_from_result(upstream, bindings) == {"input_file": "/out.mp3"}

    def test_multiple_bindings(self):
        upstream = {"data": {"output_file": "/a.mp3", "format": "mp3"}, "summary": "ok"}
        bindings = {
            "input_file": "result.data.output_file",
            "format": "result.data.format",
            "summary": "result.summary",
        }
        out = resolve_input_bindings_from_result(upstream, bindings)
        assert out == {"input_file": "/a.mp3", "format": "mp3", "summary": "ok"}

    def test_missing_path_returns_partial(self):
        upstream = {"data": {"output_file": "/a.mp3"}}
        bindings = {
            "input_file": "result.data.output_file",
            "missing": "result.data.nonexistent",
        }
        out = resolve_input_bindings_from_result(upstream, bindings)
        assert out == {"input_file": "/a.mp3"}
        assert "missing" not in out

    def test_upstream_result_as_json_string(self):
        upstream = '{"data":{"output_file":"/from_string.mp3"}}'
        bindings = {"input_file": "result.data.output_file"}
        out = resolve_input_bindings_from_result(upstream, bindings)
        assert out == {"input_file": "/from_string.mp3"}

    def test_invalid_json_string_returns_empty(self):
        out = resolve_input_bindings_from_result("not json", {"k": "result.x"})
        assert out == {}

    def test_non_dict_upstream_returns_empty(self):
        assert resolve_input_bindings_from_result([], {"k": "result.x"}) == {}
        assert resolve_input_bindings_from_result("[]", {"k": "result.x"}) == {}
