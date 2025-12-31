"""集成测试"""
import pytest
import asyncio
from multiprocessing import Process
import time
import httpx
from backend.main import main as backend_main
from shared.platform_utils import load_port

def start_backend():
    """启动后端服务（用于测试）"""
    backend_main()

@pytest.fixture
def backend_server():
    """后端服务器 fixture"""
    backend_process = Process(target=start_backend)
    backend_process.start()
    
    # 等待后端启动
    time.sleep(2)
    
    yield backend_process
    
    # 清理
    backend_process.terminate()
    backend_process.join(timeout=5)
    if backend_process.is_alive():
        backend_process.kill()

def test_backend_health(backend_server):
    """测试后端健康检查"""
    port = load_port()
    response = httpx.get(f"http://127.0.0.1:{port}/health", timeout=5.0)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_backend_chat_api(backend_server):
    """测试后端聊天 API"""
    port = load_port()
    response = httpx.post(
        f"http://127.0.0.1:{port}/api/chat",
        json={"message": "测试消息"},
        timeout=10.0
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "status" in data

