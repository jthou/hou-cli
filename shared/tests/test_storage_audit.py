"""存储审计模块单元测试"""
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from shared.storage_audit import (
    collect_storage_audit,
    cleanup_tmp_databases,
    _dir_size_bytes,
    _file_size,
    _format_size,
    _is_tmp_db,
)


class TestFormatSize:
    def test_format_bytes(self):
        assert _format_size(100)["human"] == "100 B"
        assert _format_size(0)["bytes"] == 0

    def test_format_kb(self):
        r = _format_size(2048)
        assert "KB" in r["human"]
        assert r["bytes"] == 2048

    def test_format_mb(self):
        r = _format_size(2 * 1024 * 1024)
        assert "MB" in r["human"]
        assert r["bytes"] == 2 * 1024 * 1024


class TestDirSize:
    def test_nonexistent_returns_zero(self):
        assert _dir_size_bytes(Path("/nonexistent/path")) == 0

    def test_file_returns_zero(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            p = Path(f.name)
            try:
                assert _dir_size_bytes(p) == 0  # 非目录
            finally:
                p.unlink(missing_ok=True)

    def test_empty_dir_returns_zero(self):
        with tempfile.TemporaryDirectory() as d:
            assert _dir_size_bytes(Path(d)) == 0

    def test_dir_with_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.txt").write_text("x" * 100)
            (root / "b.txt").write_text("y" * 50)
            assert _dir_size_bytes(root) == 150


class TestCollectStorageAudit:
    def test_success_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / ".env").write_text("TEST=1")
            result = collect_storage_audit(project_root)
            assert result["success"] is True
            audit = result["audit"]
            assert "summary" in audit
            assert "app_data" in audit
            assert "temp_root" in audit
            assert "outputs" in audit
            assert "databases" in audit
            assert "known" in audit["databases"]
            assert "tmp" in audit["databases"]
            assert "config" in audit
            assert "chromadb" in audit
            assert "total_bytes" in audit["summary"]

    def test_error_handling(self):
        with patch("shared.storage_audit.get_storage_manager") as m:
            m.side_effect = RuntimeError("mock error")
            result = collect_storage_audit(Path("/tmp"))
            assert result["success"] is False
            assert "mock error" in result["error"]


class TestIsTmpDb:
    def test_tmp_db(self):
        assert _is_tmp_db("tmpabc123.db") is True
        assert _is_tmp_db("tmpxyz.db") is True

    def test_not_tmp_db(self):
        assert _is_tmp_db("task_queue.db") is False
        assert _is_tmp_db("tmp.db") is False
        assert _is_tmp_db("llm_audit.db") is False


class TestCleanupTmpDatabases:
    def test_cleanup_empty_dir(self):
        with tempfile.TemporaryDirectory() as d:
            db_dir = Path(d)
            with patch("shared.storage_audit.get_storage_manager") as m:
                mock_sm = MagicMock()
                mock_sm.get_db_dir.return_value = db_dir
                m.return_value = mock_sm
                result = cleanup_tmp_databases()
                assert result["success"] is True
                assert result["deleted_count"] == 0
