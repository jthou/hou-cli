"""基础功能测试"""
import pytest
from backend.core.agent.orchestrator import Orchestrator
from backend.core.agent.coordinator import AgentCoordinator
from shared.platform_utils import get_app_data_dir, save_port, load_port

def test_orchestrator_creation():
    """测试 Orchestrator 创建"""
    orchestrator = Orchestrator()
    assert orchestrator is not None
    assert orchestrator.coordinator is not None

def test_coordinator_creation():
    """测试 Coordinator 创建"""
    coordinator = AgentCoordinator()
    assert coordinator is not None

def test_platform_utils():
    """测试平台工具函数"""
    data_dir = get_app_data_dir()
    assert data_dir.exists() or data_dir.parent.exists()
    
    # 测试端口保存和加载
    test_port = 12345
    save_port(test_port)
    loaded_port = load_port()
    assert loaded_port == test_port

@pytest.mark.asyncio
async def test_orchestrator_process():
    """测试 Orchestrator 处理任务"""
    orchestrator = Orchestrator()
    result = await orchestrator.process("测试任务")
    assert result is not None
    assert isinstance(result, str)

