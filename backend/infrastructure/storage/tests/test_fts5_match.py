"""fts5_match：MATCH 子句构造单测。"""
from backend.infrastructure.storage.fts5_match import build_fts5_match_query


def test_build_fts5_match_query_or_segments():
    q = build_fts5_match_query("wiki 同步任务")
    assert "OR" in q
    assert "wiki" in q


def test_build_fts5_match_query_quoted_cjk():
    q = build_fts5_match_query("如何做wiki")
    assert '"' in q


def test_build_fts5_match_query_empty():
    assert build_fts5_match_query("") == ""
    assert build_fts5_match_query("x") == ""
