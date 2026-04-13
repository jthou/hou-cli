from backend.services.wechat_mp_service.article_markdown_html import (
    article_markdown_to_wechat_html,
    digest_clamp,
    title_from_first_atx_heading,
)


def test_title_from_first_atx_heading():
    assert title_from_first_atx_heading("# 你好\n\n正文") == "你好"
    assert title_from_first_atx_heading("无标题") == ""


def test_article_markdown_to_wechat_html_wraps_section():
    html = article_markdown_to_wechat_html("# T\n\n段落")
    assert "data-hou-cli" in html
    assert "<h1" in html or "<h1>" in html.lower()
    assert "段落" in html


def test_digest_clamp():
    assert digest_clamp(None) is None
    assert digest_clamp("a" * 200) == "a" * 120
