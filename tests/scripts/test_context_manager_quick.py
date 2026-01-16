#!/usr/bin/env python3
"""快速测试上下文管理器"""
import os
import sys
from pathlib import Path

# 设置测试环境变量
os.environ.setdefault('DEEPSEEK_API_KEY', 'test_key_for_testing_1234567890')

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("上下文管理器测试")
print("=" * 60)

try:
    from backend.core.agent.context_manager import ContextManager
    
    # 测试 1: 创建会话
    print("\n✅ 测试 1: 创建会话")
    cm = ContextManager(max_history=10)
    session_id = cm.create_session()
    print(f"   会话 ID: {session_id[:20]}...")
    assert session_id in cm.sessions
    print("   ✅ 通过")
    
    # 测试 2: 添加消息
    print("\n✅ 测试 2: 添加消息")
    cm.add_message(session_id, "user", "你好")
    history = cm.get_history(session_id)
    assert len(history) == 1
    assert history[0]["role"] == "user"
    print("   ✅ 通过")
    
    # 测试 3: 历史限制
    print("\n✅ 测试 3: 历史消息数量限制")
    for i in range(15):
        cm.add_message(session_id, "user", f"消息{i}")
    history = cm.get_history(session_id)
    assert len(history) == 10
    print(f"   历史消息数: {len(history)} (预期: 10)")
    print("   ✅ 通过")
    
    # 测试 4: 多轮对话
    print("\n✅ 测试 4: 多轮对话")
    session_id2 = cm.create_session()
    cm.add_message(session_id2, "user", "第一轮")
    cm.add_message(session_id2, "assistant", "回复1")
    cm.add_message(session_id2, "user", "第二轮")
    history = cm.get_history(session_id2)
    assert len(history) == 3
    print(f"   历史消息数: {len(history)}")
    print("   ✅ 通过")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
