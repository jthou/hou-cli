#!/usr/bin/env python3
"""端到端对话测试脚本"""
import os
import sys
import asyncio
import time
from pathlib import Path

# 设置测试环境变量
os.environ.setdefault('DEEPSEEK_API_KEY', 'test_key_for_testing_1234567890')

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("端到端对话测试")
print("=" * 60)

async def test_orchestrator_with_context():
    """测试 Orchestrator 的上下文管理"""
    print("\n📋 测试 1: Orchestrator 上下文管理")
    
    try:
        from backend.core.agent.orchestrator import Orchestrator
        from unittest.mock import AsyncMock, patch
        
        orchestrator = Orchestrator()
        
        # [MOCK] 模拟 LLM Service
        print("[MOCK] 使用 Mock 数据模拟 LLM Service")
        
        # 第一轮对话
        print("\n  第一轮对话...")
        with patch.object(orchestrator.llm_service, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "你好！我是智能助手。"
            print("[MOCK] Mock chat 返回: '你好！我是智能助手。'")
            
            response1 = await orchestrator.process("你好", context={"session_id": "test_session_123"})
            assert response1 == "你好！我是智能助手。"
            print(f"   ✅ 第一轮回复: {response1}")
            
            # 检查历史
            history = orchestrator.context_manager.get_history("test_session_123")
            assert len(history) == 2  # user + assistant
            print(f"   ✅ 历史消息数: {len(history)}")
        
        # 第二轮对话（应该包含历史）
        print("\n  第二轮对话（包含历史）...")
        with patch.object(orchestrator.llm_service, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "我刚才说我是智能助手。"
            print("[MOCK] Mock chat 返回: '我刚才说我是智能助手。'")
            
            # 验证 user_prompt 包含历史
            def check_history_in_prompt(*args, **kwargs):
                user_prompt = kwargs.get('user_prompt', '')
                assert "你好" in user_prompt or "智能助手" in user_prompt
                print(f"[MOCK] user_prompt 包含历史: {len(user_prompt) > 10}")
                return "我刚才说我是智能助手。"
            
            mock_chat.side_effect = check_history_in_prompt
            
            response2 = await orchestrator.process("我刚才说了什么？", context={"session_id": "test_session_123"})
            print(f"   ✅ 第二轮回复: {response2}")
            
            # 检查历史
            history = orchestrator.context_manager.get_history("test_session_123")
            assert len(history) == 4  # 2轮对话，每轮2条消息
            print(f"   ✅ 历史消息数: {len(history)}")
        
        print("\n  ✅ Orchestrator 上下文管理测试通过")
        return True
        
    except Exception as e:
        print(f"\n  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_stream_with_context():
    """测试流式响应的上下文管理"""
    print("\n📋 测试 2: 流式响应上下文管理")
    
    try:
        from backend.core.agent.orchestrator import Orchestrator
        from unittest.mock import AsyncMock, patch
        
        orchestrator = Orchestrator()
        
        # [MOCK] 模拟流式响应
        print("[MOCK] 使用 Mock 数据模拟流式响应")
        
        async def mock_stream():
            yield "流式"
            yield "回复"
            yield "内容"
        
        with patch.object(orchestrator.llm_service, 'stream_chat', return_value=mock_stream()):
            chunks = []
            async for chunk in orchestrator.stream_process("测试", context={"session_id": "test_stream_123"}):
                chunks.append(chunk)
            
            assert chunks == ["流式", "回复", "内容"]
            print(f"   ✅ 流式响应: {''.join(chunks)}")
            
            # 检查历史
            history = orchestrator.context_manager.get_history("test_stream_123")
            assert len(history) == 2  # user + assistant
            print(f"   ✅ 历史消息数: {len(history)}")
        
        print("\n  ✅ 流式响应上下文管理测试通过")
        return True
        
    except Exception as e:
        print(f"\n  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_context_manager():
    """测试上下文管理器"""
    print("\n📋 测试 3: 上下文管理器基础功能")
    
    try:
        from backend.core.agent.context_manager import ContextManager
        
        cm = ContextManager(max_history=10)
        
        # 创建会话
        session_id = cm.create_session()
        assert session_id in cm.sessions
        print(f"   ✅ 会话创建成功: {session_id[:20]}...")
        
        # 添加消息
        cm.add_message(session_id, "user", "消息1")
        cm.add_message(session_id, "assistant", "回复1")
        history = cm.get_history(session_id)
        assert len(history) == 2
        print(f"   ✅ 历史消息数: {len(history)}")
        
        # 测试历史限制
        for i in range(15):
            cm.add_message(session_id, "user", f"消息{i}")
        history = cm.get_history(session_id)
        assert len(history) == 10
        print(f"   ✅ 历史限制生效: {len(history)} 条")
        
        print("\n  ✅ 上下文管理器测试通过")
        return True
        
    except Exception as e:
        print(f"\n  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    results = []
    
    # 测试上下文管理器
    results.append(test_context_manager())
    
    # 测试 Orchestrator 上下文管理
    results.append(await test_orchestrator_with_context())
    
    # 测试流式响应上下文管理
    results.append(await test_stream_with_context())
    
    # 总结
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("✅ 所有测试通过！")
        print("\n💡 下一步：启动前后端进行实际对话测试")
        print("   1. 启动后端: python -m backend.main")
        print("   2. 启动前端: python -m frontend.main chat")
        return 0
    else:
        print("❌ 部分测试失败")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)








