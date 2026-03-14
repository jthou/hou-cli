#!/usr/bin/env python3
"""简单测试脚本 - 验证前后端连接和基本功能

不执行实际任务，只验证连接和配置
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from shared.load_env import load_env
load_env(project_root)

def test_backend_connection():
    """测试后端连接"""
    print("=" * 80)
    print("测试后端连接")
    print("=" * 80)
    print()
    
    try:
        from frontend.client.ipc_client import IPCClient
        client = IPCClient()
        print("✅ 后端连接成功")
        print(f"   后端地址: {client.base_url}")
        return True
    except Exception as e:
        print(f"❌ 后端连接失败: {e}")
        print()
        print("请检查：")
        print("1. 后端服务是否正在运行")
        print("2. 端口配置是否正确（默认 6080）")
        print("3. .env 文件中的 BACKEND_PORT 配置")
        return False


def test_environment():
    """测试环境配置"""
    print()
    print("=" * 80)
    print("测试环境配置")
    print("=" * 80)
    print()
    
    checks = {
        "BACKEND_PORT": os.getenv("BACKEND_PORT", "未设置"),
        "ENABLE_AUTONOMOUS_EXECUTION": os.getenv("ENABLE_AUTONOMOUS_EXECUTION", "未设置"),
        "STREAM_TIMEOUT": os.getenv("STREAM_TIMEOUT", "未设置"),
        "DEEPSEEK_API_KEY": "已设置" if os.getenv("DEEPSEEK_API_KEY") else "未设置",
    }
    
    all_ok = True
    for key, value in checks.items():
        if key == "DEEPSEEK_API_KEY":
            status = "✅" if value == "已设置" else "⚠️"
        else:
            status = "✅" if value != "未设置" else "⚠️"
        print(f"{status} {key}: {value}")
        if value == "未设置" and key != "DEEPSEEK_API_KEY":
            all_ok = False
    
    return all_ok


def test_frontend_code():
    """测试前端代码导入"""
    print()
    print("=" * 80)
    print("测试前端代码")
    print("=" * 80)
    print()
    
    try:
        from frontend.ui.stream_handler import StreamRenderer
        renderer = StreamRenderer()
        print("✅ StreamRenderer 导入成功")
        print(f"   状态行跟踪: {'已启用' if hasattr(renderer, 'current_status_line') else '未启用'}")
        return True
    except Exception as e:
        print(f"❌ 前端代码导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print()
    print("简单功能测试")
    print()
    
    results = []
    
    # 测试环境配置
    results.append(("环境配置", test_environment()))
    
    # 测试前端代码
    results.append(("前端代码", test_frontend_code()))
    
    # 测试后端连接
    results.append(("后端连接", test_backend_connection()))
    
    # 汇总结果
    print()
    print("=" * 80)
    print("测试结果汇总")
    print("=" * 80)
    print()
    
    all_passed = True
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
        if not result:
            all_passed = False
    
    print()
    if all_passed:
        print("✅ 所有测试通过")
        print()
        print("可以开始执行实际任务测试：")
        print("  python -m frontend.main chat '你的任务描述'")
    else:
        print("❌ 部分测试失败，请检查配置")
    
    return all_passed


if __name__ == "__main__":
    # 设置环境变量
    os.environ.setdefault("BACKEND_PORT", "6080")
    os.environ.setdefault("ENABLE_AUTONOMOUS_EXECUTION", "true")
    os.environ.setdefault("STREAM_TIMEOUT", "600")
    
    success = main()
    sys.exit(0 if success else 1)




