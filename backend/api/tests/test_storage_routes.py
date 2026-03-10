"""存储配置路由单元测试"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from fastapi.testclient import TestClient


class TestStorageRoutes:
    """存储配置路由测试类"""
    
    @pytest.fixture
    def mock_storage_manager(self):
        """创建模拟的 StorageManager"""
        mock = MagicMock()
        
        # 模拟数据目录
        mock.get_data_dir = MagicMock(return_value=Path("/test/data"))
        mock.get_db_dir = MagicMock(return_value=Path("/test/data/databases"))
        mock.get_chroma_dir = MagicMock(return_value=Path("/test/data/chroma"))
        
        # 模拟 SQLite 数据库路径
        mock_db_path = MagicMock()
        mock_db_path.exists = MagicMock(return_value=True)
        mock_db_path.stat = MagicMock(return_value=MagicMock(st_size=1024 * 1024))  # 1MB
        mock.get_sqlite_path = MagicMock(return_value=mock_db_path)
        
        # 模拟数据库目录
        mock_db_dir = MagicMock()
        mock_db_dir.exists = MagicMock(return_value=True)
        mock_db_file1 = MagicMock()
        mock_db_file1.name = "sessions.db"
        mock_db_file1.stat = MagicMock(return_value=MagicMock(st_size=1024 * 1024))
        mock_db_file2 = MagicMock()
        mock_db_file2.name = "other.db"
        mock_db_file2.stat = MagicMock(return_value=MagicMock(st_size=512 * 1024))
        mock_db_dir.glob = MagicMock(return_value=[mock_db_file1, mock_db_file2])
        
        mock.get_db_dir.return_value = mock_db_dir
        mock.get_sqlite_path.return_value = mock_db_path
        
        # 模拟 ChromaDB 目录
        mock_chroma_dir = MagicMock()
        mock_chroma_dir.exists = MagicMock(return_value=True)
        
        # 模拟 ChromaDB 文件
        mock_chroma_file1 = MagicMock()
        mock_chroma_file1.is_file = MagicMock(return_value=True)
        mock_chroma_file1.stat = MagicMock(return_value=MagicMock(st_size=2048 * 1024))
        mock_chroma_file2 = MagicMock()
        mock_chroma_file2.is_file = MagicMock(return_value=True)
        mock_chroma_file2.stat = MagicMock(return_value=MagicMock(st_size=1024 * 1024))
        mock_chroma_dir.rglob = MagicMock(return_value=[mock_chroma_file1, mock_chroma_file2])
        
        mock.get_chroma_dir.return_value = mock_chroma_dir
        
        # 模拟 ChromaDB 客户端
        mock_chroma_client = MagicMock()
        mock_collection1 = MagicMock()
        mock_collection1.name = "collection1"
        mock_collection1.count = MagicMock(return_value=10)
        mock_collection1.metadata = {}
        mock_collection2 = MagicMock()
        mock_collection2.name = "collection2"
        mock_collection2.count = MagicMock(return_value=20)
        mock_collection2.metadata = {"key": "value"}
        mock_chroma_client.list_collections = MagicMock(return_value=[mock_collection1, mock_collection2])
        mock.get_chroma_client = MagicMock(return_value=mock_chroma_client)
        
        return mock
    
    def test_get_storage_config_success(self, client, mock_storage_manager):
        """测试获取存储配置成功"""
        with patch('backend.api.storage_routes.get_storage_manager') as mock_get_manager:
            mock_get_manager.return_value = mock_storage_manager
            
            response = client.get("/api/storage/config")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data_dir"] == "/test/data"
            assert data["sqlite"]["enabled"] is True
            assert data["sqlite"]["default_db_exists"] is True
            assert data["sqlite"]["default_db_size_mb"] == 1.0
            assert len(data["sqlite"]["databases"]) == 2
            assert data["chromadb"]["enabled"] is True
            assert data["chromadb"]["exists"] is True
            assert data["chromadb"]["size_mb"] == 3.0  # 2MB + 1MB
            assert data["chromadb"]["collection_count"] == 2
    
    def test_get_storage_config_sqlite_not_exists(self, client):
        """测试 SQLite 数据库不存在的情况"""
        mock = MagicMock()
        mock.get_data_dir = MagicMock(return_value=Path("/test/data"))
        mock.get_db_dir = MagicMock(return_value=Path("/test/data/databases"))
        mock.get_chroma_dir = MagicMock(return_value=Path("/test/data/chroma"))
        
        # 模拟数据库文件不存在
        mock_db_path = MagicMock()
        mock_db_path.exists = MagicMock(return_value=False)
        mock.get_sqlite_path = MagicMock(return_value=mock_db_path)
        
        # 模拟数据库目录
        mock_db_dir = MagicMock()
        mock_db_dir.exists = MagicMock(return_value=True)
        mock_db_dir.glob = MagicMock(return_value=[])
        mock.get_db_dir.return_value = mock_db_dir
        
        # 模拟 ChromaDB
        mock_chroma_dir = MagicMock()
        mock_chroma_dir.exists = MagicMock(return_value=False)
        mock.get_chroma_dir.return_value = mock_chroma_dir
        
        with patch('backend.api.storage_routes.get_storage_manager') as mock_get_manager:
            mock_get_manager.return_value = mock
            
            response = client.get("/api/storage/config")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["sqlite"]["default_db_exists"] is False
            assert data["sqlite"]["default_db_size"] == 0 or data["sqlite"]["default_db_size_mb"] == 0
            assert data["chromadb"]["exists"] is False
    
    def test_get_storage_config_chromadb_error(self, client):
        """测试 ChromaDB 获取集合时出错"""
        mock = MagicMock()
        mock.get_data_dir = MagicMock(return_value=Path("/test/data"))
        mock.get_db_dir = MagicMock(return_value=Path("/test/data/databases"))
        mock.get_chroma_dir = MagicMock(return_value=Path("/test/data/chroma"))
        
        mock_db_path = MagicMock()
        mock_db_path.exists = MagicMock(return_value=False)
        mock.get_sqlite_path = MagicMock(return_value=mock_db_path)
        
        mock_db_dir = MagicMock()
        mock_db_dir.exists = MagicMock(return_value=True)
        mock_db_dir.glob = MagicMock(return_value=[])
        mock.get_db_dir.return_value = mock_db_dir
        
        # 模拟 ChromaDB 目录存在但获取集合失败
        mock_chroma_dir = MagicMock()
        mock_chroma_dir.exists = MagicMock(return_value=True)
        mock_chroma_dir.rglob = MagicMock(return_value=[])
        mock.get_chroma_dir.return_value = mock_chroma_dir
        
        mock_chroma_client = MagicMock()
        mock_chroma_client.list_collections = MagicMock(side_effect=Exception("ChromaDB 连接失败"))
        mock.get_chroma_client = MagicMock(return_value=mock_chroma_client)
        
        with patch('backend.api.storage_routes.get_storage_manager') as mock_get_manager:
            mock_get_manager.return_value = mock
            
            response = client.get("/api/storage/config")
            
            # 应该仍然返回成功，但集合列表为空
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["chromadb"]["collection_count"] == 0
    
    def test_get_storage_config_error(self, client):
        """测试获取存储配置错误处理"""
        with patch('backend.api.storage_routes.get_storage_manager') as mock_get_manager:
            mock_get_manager.side_effect = Exception("存储管理器初始化失败")
            
            response = client.get("/api/storage/config")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "存储管理器初始化失败" in data["error"]

    def test_get_storage_audit_success(self, client):
        """测试存储审计成功"""
        mock_audit = {
            "summary": {"total_bytes": 1024, "human": "1.00 KB"},
            "app_data": {"path": "/test/app", "size_bytes": 512, "human": "512 B"},
            "temp_root": {"path": "/test/tmp", "size_bytes": 256},
            "outputs": {"path": "/test/outputs", "size_bytes": 256},
            "databases": {"dir": "/test/db", "known": [], "tmp": [], "tmp_count": 0},
            "config": {"files": []},
            "chromadb": {"path": "/test/chroma", "size_bytes": 0},
        }
        with patch('backend.api.storage_routes.collect_storage_audit') as mock_collect:
            mock_collect.return_value = {"success": True, "audit": mock_audit}
            response = client.get("/api/storage/audit")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["summary"]["total_bytes"] == 1024
            assert data["app_data"]["path"] == "/test/app"

    def test_get_storage_audit_error(self, client):
        """测试存储审计失败"""
        with patch('backend.api.storage_routes.collect_storage_audit') as mock_collect:
            mock_collect.return_value = {"success": False, "error": "审计失败"}
            response = client.get("/api/storage/audit")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "审计失败" in data["error"]

    def test_cleanup_tmp_databases_success(self, client):
        """测试清理临时数据库成功"""
        with patch('backend.api.storage_routes.cleanup_tmp_databases') as mock_cleanup:
            mock_cleanup.return_value = {"success": True, "deleted_count": 5, "freed_bytes": 300000}
            response = client.post("/api/storage/audit/cleanup-tmp-dbs")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["deleted_count"] == 5
            assert data["freed_bytes"] == 300000

