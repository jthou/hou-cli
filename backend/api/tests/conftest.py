"""pytest 配置文件 - 提供测试 fixtures 和配置"""
import os
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient

# 在导入任何模块之前设置测试环境变量
os.environ.setdefault('DEEPSEEK_API_KEY', 'test_key_for_testing_1234567890')
os.environ.setdefault('TESTING', 'true')

@pytest.fixture(scope="session")
def app():
    """创建测试应用实例"""
    from backend.main import app
    return app

@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)

@pytest.fixture
def mock_orchestrator():
    """创建模拟的 Orchestrator"""
    mock = MagicMock()
    mock.process = AsyncMock(return_value="测试响应")
    
    async def mock_stream_process(task, context=None):
        yield "chunk1"
        yield "chunk2"
        yield "chunk3"
    
    mock.stream_process = mock_stream_process
    return mock

@pytest.fixture
def mock_context_manager():
    """创建模拟的 ContextManager"""
    from datetime import datetime
    from backend.core.context.models import Session
    
    mock = MagicMock()
    
    # 模拟会话列表
    mock_sessions = [
        Session(
            session_id="test_session_1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={}
        ),
        Session(
            session_id="test_session_2",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={}
        )
    ]
    
    mock.list_sessions = MagicMock(return_value=mock_sessions)
    mock.get_session = MagicMock(return_value=mock_sessions[0] if mock_sessions else None)
    mock.get_session_preview = MagicMock(return_value={
        "session_id": "test_session_1",
        "preview": "测试预览",
        "message_count": 5,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "metadata": {}
    })
    mock.clear_session = MagicMock(return_value=True)
    mock.create_session = MagicMock(return_value="new_session_id")
    mock.get_messages = MagicMock(return_value=[])
    
    return mock

@pytest.fixture
def mock_search_service():
    """创建模拟的 FileSearchService"""
    from backend.services.file_search_service.models import FileSearchResponse, FileSearchResult
    
    mock = MagicMock()
    mock.check_availability = MagicMock(return_value=(True, None))
    
    mock_response = FileSearchResponse(
        results=[
            FileSearchResult(
                path="/test/file1.py",
                name="file1.py",
                size=1024,
                modified_time=1234567890.0
            )
        ],
        total=1,
        limit=100,
        offset=0
    )
    mock.search = MagicMock(return_value=mock_response)
    
    return mock

@pytest.fixture
def mock_mediawiki_client():
    """创建模拟的 MediaWikiClientService"""
    from datetime import datetime
    from backend.services.mediawiki_client_service.models import MediaWikiPage, MediaWikiSearchResult
    
    mock = MagicMock()
    
    # 模拟搜索结果
    mock_search_results = [
        MediaWikiSearchResult(
            title="测试页面",
            snippet="这是测试内容",
            url="http://example.com/测试页面",
            score=0.95
        )
    ]
    mock.search_pages = MagicMock(return_value=mock_search_results)
    
    # 模拟页面
    mock_page = MediaWikiPage(
        title="测试页面",
        content="这是页面内容",
        url="http://example.com/测试页面",
        categories=["测试"],
        links=["链接1", "链接2"],
        last_modified=datetime.now(),
        revision_id=12345
    )
    mock.get_page = MagicMock(return_value=mock_page)
    mock.edit_page = MagicMock(return_value=True)
    mock.connect = MagicMock()
    
    return mock

@pytest.fixture
def mock_storage_manager():
    """创建模拟的 StorageManager"""
    from pathlib import Path
    
    mock = MagicMock()
    mock.get_data_dir = MagicMock(return_value=Path("/test/data"))
    mock.get_db_dir = MagicMock(return_value=Path("/test/data/databases"))
    mock.get_chroma_dir = MagicMock(return_value=Path("/test/data/chroma"))
    mock.get_sqlite_path = MagicMock(return_value=Path("/test/data/databases/sessions.db"))
    
    # 模拟数据库文件
    mock_db_path = MagicMock()
    mock_db_path.exists = MagicMock(return_value=True)
    mock_db_path.stat = MagicMock(return_value=MagicMock(st_size=1024 * 1024))  # 1MB
    
    mock.get_sqlite_path.return_value = mock_db_path
    
    # 模拟 ChromaDB 客户端
    mock_chroma_client = MagicMock()
    mock_collection = MagicMock()
    mock_collection.name = "test_collection"
    mock_collection.count = MagicMock(return_value=10)
    mock_collection.metadata = {}
    mock_chroma_client.list_collections = MagicMock(return_value=[mock_collection])
    mock.get_chroma_client = MagicMock(return_value=mock_chroma_client)
    
    return mock

@pytest.fixture
def mock_heartbeat_monitor():
    """创建模拟的 HeartbeatMonitor"""
    mock = MagicMock()
    mock.get_status = MagicMock(return_value={
        "uptime_seconds": 3600,
        "heartbeat_count": 120,
        "cpu_percent": 25.5,
        "memory_mb": 512.0,
        "last_heartbeat": "2024-01-01T12:00:00"
    })
    return mock
