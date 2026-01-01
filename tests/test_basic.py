"""平台工具函数测试"""
import pytest
from shared.platform_utils import get_app_data_dir, save_port, load_port

def test_platform_utils():
    """测试平台工具函数"""
    data_dir = get_app_data_dir()
    assert data_dir.exists() or data_dir.parent.exists()
    
    # 测试端口保存和加载
    test_port = 12345
    save_port(test_port)
    loaded_port = load_port()
    assert loaded_port == test_port

