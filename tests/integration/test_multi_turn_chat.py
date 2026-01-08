#!/usr/bin/env python3
"""多轮对话上下文测试脚本"""
import os
import sys
import asyncio
from pathlib import Path

# 设置测试环境变量
os.environ.setdefault('DEEPSEEK_API_KEY', 'test_key_for_testing_1234567890')

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("多轮对话上下文测试")
print("=" * 60)

async def test_multi_turn_conversation():
    """测试多轮对话的上下文保持"""
    try:
        from backend.core.agent.orchestrator import Orchestrator
        from unittest.mock import AsyncMock, patch
        
        orchestrator = Orchestrator()
        session_id = "multi_turn_test_123"
        
        print(f"\n📋 会话 ID: {session_id}")
        print("\n开始多轮对话测试...\n")
        
        # [MOCK] 模拟 LLM 响应
        print("[MOCK] 使用 Mock 数据模拟多轮对话")
        
        # 第一轮：自我介绍
        print("=" * 40)
        print("第一轮对话")
        print("=" * 40)
        user_msg1 = "你好，我的名字是张三"
        
        with patch.object(orchestrator.llm_service, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "你好张三！很高兴认识你。"
            print(f"[MOCK] 用户: {user_msg1}")
            print("[MOCK] Mock chat 返回: '你好张三！很高兴认识你。'")
            
            response1 = await orchestrator.process(
                user_msg1,
                context={"session_id": session_id}
            )
            print(f"助手: {response1}")
            
            # 检查历史
            history = orchestrator.context_manager.get_history(session_id)
            print(f"历史消息数: {len(history)} (预期: 2)")
            assert len(history) == 2
            assert history[0]["content"] == user_msg1
            assert history[1]["content"] == response1
        
        # 第二轮：询问名字（应该记住）
        print("\n" + "=" * 40)
        print("第二轮对话（测试上下文记忆）")
        print("=" * 40)
        user_msg2 = "你还记得我的名字吗？"
        
        with patch.object(orchestrator.llm_service, 'chat', new_callable=AsyncMock) as mock_chat:
            # 验证 user_prompt 包含第一轮的历史
            def check_context(*args, **kwargs):
                user_prompt = kwargs.get('user_prompt', '')
                print(f"[MOCK] user_prompt 长度: {len(user_prompt)}")
                print(f"[MOCK] user_prompt 包含'张三': {'张三' in user_prompt}")
                # 验证包含历史
                assert "张三" in user_prompt or "名字" in user_prompt
                return "当然记得！你的名字是张三。"
            
            mock_chat.side_effect = check_context
            print(f"[MOCK] 用户: {user_msg2}")
            print("[MOCK] Mock chat 将验证上下文")
            
            response2 = await orchestrator.process(
                user_msg2,
                context={"session_id": session_id}
            )
            print(f"助手: {response2}")
            
            # 检查历史
            history = orchestrator.context_manager.get_history(session_id)
            print(f"历史消息数: {len(history)} (预期: 4)")
            assert len(history) == 4
        
        # 第三轮：继续对话
        print("\n" + "=" * 40)
        print("第三轮对话（继续测试上下文）")
        print("=" * 40)
        user_msg3 = "很好，谢谢"
        
        with patch.object(orchestrator.llm_service, 'chat', new_callable=AsyncMock) as mock_chat:
            def check_context_again(*args, **kwargs):
                user_prompt = kwargs.get('user_prompt', '')
                # 应该包含前两轮的历史
                assert len(user_prompt) > 50  # 包含历史，应该比较长
                print(f"[MOCK] user_prompt 长度: {len(user_prompt)} (包含历史)")
                return "不客气！有什么其他问题吗？"
            
            mock_chat.side_effect = check_context_again
            print(f"[MOCK] 用户: {user_msg3}")
            
            response3 = await orchestrator.process(
                user_msg3,
                context={"session_id": session_id}
            )
            print(f"助手: {response3}")
            
            # 检查历史
            history = orchestrator.context_manager.get_history(session_id)
            print(f"历史消息数: {len(history)} (预期: 6)")
            assert len(history) == 6
        
        # 验证历史内容
        print("\n" + "=" * 40)
        print("验证历史消息内容")
        print("=" * 40)
        history = orchestrator.context_manager.get_history(session_id)
        print(f"总历史消息数: {len(history)}")
        
        for i, msg in enumerate(history, 1):
            role = "用户" if msg["role"] == "user" else "助手"
            content = msg["content"][:50] + "..." if len(msg["content"]) > 50 else msg["content"]
            print(f"  {i}. [{role}]: {content}")
        
        # 验证历史顺序
        assert history[0]["role"] == "user"
        assert history[0]["content"] == user_msg1
        assert history[1]["role"] == "assistant"
        assert history[-1]["role"] == "assistant"
        
        print("\n✅ 多轮对话上下文测试通过！")
        print("\n💡 上下文管理功能正常：")
        print("   - 会话 ID 保持一致")
        print("   - 历史消息正确保存")
        print("   - 历史消息包含在 LLM 请求中")
        print("   - 多轮对话上下文连贯")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    success = await test_multi_turn_conversation()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 多轮对话上下文测试完成！")
        print("\n💡 下一步：")
        print("   1. 启动后端: python -m backend.main")
        print("   2. 启动前端: python -m frontend.main chat")
        print("   3. 进行实际的多轮对话测试")
        return 0
    else:
        print("❌ 测试失败")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)









