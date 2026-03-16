"""写作建议 API 单元测试"""
import pytest
from unittest.mock import patch, AsyncMock

from backend.api.writing_suggestions_routes import parse_suggestions_from_llm_response


class TestParseSuggestionsFromLlmResponse:
    """parse_suggestions_from_llm_response 纯函数测试"""

    def test_empty_response_returns_empty_list(self):
        assert parse_suggestions_from_llm_response("") == []
        assert parse_suggestions_from_llm_response("   ") == []
        assert parse_suggestions_from_llm_response(None) == []

    def test_valid_json_returns_suggestions(self):
        resp = '{"suggestions": ["建议一", "建议二", "建议三"]}'
        assert parse_suggestions_from_llm_response(resp) == ["建议一", "建议二", "建议三"]

    def test_json_with_extra_whitespace(self):
        resp = '  \n  {"suggestions": ["A", "B"]}  \n  '
        assert parse_suggestions_from_llm_response(resp) == ["A", "B"]

    def test_json_with_surrounding_text(self):
        resp = '这是前缀\n{"suggestions": ["续写一", "续写二"]}\n这是后缀'
        assert parse_suggestions_from_llm_response(resp) == ["续写一", "续写二"]

    def test_max_suggestions_limit(self):
        resp = '{"suggestions": ["a", "b", "c", "d", "e", "f"]}'
        assert parse_suggestions_from_llm_response(resp, max_suggestions=3) == ["a", "b", "c"]

    def test_fallback_line_parsing(self):
        resp = """建议第一行
建议第二行
建议第三行"""
        assert parse_suggestions_from_llm_response(resp) == ["建议第一行", "建议第二行", "建议第三行"]

    def test_fallback_skips_json_and_code_block_lines(self):
        # 使用无法解析为 JSON 的文本，触发回退按行解析
        resp = """```code```
建议行一
建议行二"""
        result = parse_suggestions_from_llm_response(resp)
        assert result == ["建议行一", "建议行二"]
        assert "```code```" not in result

    def test_empty_suggestions_array(self):
        resp = '{"suggestions": []}'
        assert parse_suggestions_from_llm_response(resp) == []

    def test_suggestions_with_whitespace_stripped(self):
        resp = '{"suggestions": ["  a  ", "  b  "]}'
        assert parse_suggestions_from_llm_response(resp) == ["a", "b"]

    def test_filters_falsy_suggestions(self):
        # 实现用 if s 过滤，空字符串被过滤；"  " 经 strip 后变 "" 仍会出现在结果中
        resp = '{"suggestions": ["a", "", "b", "c"]}'
        assert parse_suggestions_from_llm_response(resp) == ["a", "b", "c"]


class TestWritingSuggestionsApi:
    """POST /api/writing-suggestions 接口测试"""

    def test_empty_text_before_returns_empty_suggestions(self, client):
        response = client.post(
            "/api/writing-suggestions",
            json={"text_before": "", "text_after": "", "format": "markdown"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["suggestions"] == []

    def test_whitespace_only_text_before_returns_empty_suggestions(self, client):
        response = client.post(
            "/api/writing-suggestions",
            json={"text_before": "   \n\t  ", "text_after": "", "format": "markdown"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["suggestions"] == []

    def test_success_returns_suggestions(self, client):
        with patch(
            "backend.api.writing_suggestions_routes._call_writing_suggestions_llm",
            new_callable=AsyncMock,
            return_value=["续写建议一", "续写建议二"],
        ):
            response = client.post(
                "/api/writing-suggestions",
                json={
                    "text_before": "这是一段测试文本，光标在这里",
                    "text_after": "",
                    "format": "markdown",
                    "max_suggestions": 5,
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["suggestions"] == ["续写建议一", "续写建议二"]

    def test_format_wikitext_passed_to_llm(self, client):
        with patch(
            "backend.api.writing_suggestions_routes._call_writing_suggestions_llm",
            new_callable=AsyncMock,
            return_value=["wikitext 建议"],
        ) as mock_llm:
            response = client.post(
                "/api/writing-suggestions",
                json={
                    "text_before": "[[链接]]",
                    "text_after": "",
                    "format": "wikitext",
                },
            )
        assert response.status_code == 200
        mock_llm.assert_called_once()
        call_kw = mock_llm.call_args[1]
        assert call_kw["fmt"] == "wikitext"

    def test_max_suggestions_clamped(self, client):
        with patch(
            "backend.api.writing_suggestions_routes._call_writing_suggestions_llm",
            new_callable=AsyncMock,
            return_value=["a", "b"],
        ) as mock_llm:
            response = client.post(
                "/api/writing-suggestions",
                json={
                    "text_before": "测试",
                    "max_suggestions": 10,  # 应被限制为 5
                },
            )
        assert response.status_code == 200
        call_kw = mock_llm.call_args[1]
        assert call_kw["max_suggestions"] == 5

    def test_llm_exception_returns_500(self, client):
        with patch(
            "backend.api.writing_suggestions_routes._call_writing_suggestions_llm",
            new_callable=AsyncMock,
            side_effect=Exception("LLM 调用失败"),
        ):
            response = client.post(
                "/api/writing-suggestions",
                json={
                    "text_before": "测试文本",
                    "text_after": "",
                    "format": "markdown",
                },
            )
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "LLM" in data["detail"] or "失败" in data["detail"]
