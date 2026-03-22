#!/usr/bin/env python3
"""
批量删除功能验证脚本
"""
import json
import tempfile
import shutil
from pathlib import Path

def test_batch_delete_features():
    print("开始测试批量删除功能...")

    # 动态导入，避免潜在的缓存问题
    from backend.core.context.storage.file import FileStorageBackend
    from backend.core.context.models import Message, MessageRole, Session
    from backend.core.context.manager import ContextManager

    # 创建临时目录用于测试
    temp_dir = Path(tempfile.mkdtemp())
    print(f"使用临时目录: {temp_dir}")

    try:
        # 创建存储实例
        storage = FileStorageBackend(storage_dir=temp_dir)
        context_manager = ContextManager(storage_backend=storage)

        print(f"ContextManager methods containing 'delete': {[m for m in dir(context_manager) if 'delete' in m]}")

        # 测试1: 批量删除消息
        print("\n1. 测试批量删除消息...")
        session_id = context_manager.create_session()
        print(f"   创建会话: {session_id}")

        # 添加多条消息
        message_ids = []
        for i in range(5):
            msg_id = context_manager.add_message(
                session_id,
                MessageRole.USER,
                f"测试消息 {i}",
                metadata={"index": i}
            )
            message_ids.append(msg_id)
            print(f"   创建消息 {i}: {msg_id}")

        print(f"   总共创建了 {len(message_ids)} 条消息")

        # 获取所有消息确认都存在
        messages = context_manager.get_messages(session_id)
        print(f"   当前会话有 {len(messages)} 条消息")

        # 确认批量删除方法存在
        if not hasattr(context_manager, 'delete_messages'):
            print("   ❌ delete_messages 方法不存在！")
            return
        else:
            print("   ✅ delete_messages 方法存在")

        # 批量删除其中2条消息
        ids_to_delete = message_ids[:2]
        print(f"   准备批量删除消息: {ids_to_delete}")

        result = context_manager.delete_messages(session_id, ids_to_delete)
        print(f"   批量删除结果: {result}")

        # 检查删除后剩余的消息数量
        remaining_messages = context_manager.get_messages(session_id)
        print(f"   删除后剩余消息数: {len(remaining_messages)}")

        # 测试2: 批量删除会话
        print("\n2. 测试批量删除会话...")

        if not hasattr(context_manager, 'delete_sessions'):
            print("   ❌ delete_sessions 方法不存在！")
            return
        else:
            print("   ✅ delete_sessions 方法存在")

        session_ids = []
        for i in range(3):
            sid = context_manager.create_session()
            session_ids.append(sid)
            # 在每个会话中添加一些消息
            context_manager.add_message(sid, MessageRole.USER, f"会话{i}的消息")
            print(f"   创建会话 {i}: {sid}")

        # 验证会话都存在
        all_sessions = context_manager.list_sessions()
        print(f"   总共有 {len(all_sessions)} 个会话")

        # 批量删除会话
        print(f"   准备批量删除会话: {session_ids[:2]}")  # 只删除前2个
        result = context_manager.delete_sessions(session_ids[:2])
        print(f"   批量删除会话结果: {result}")

        # 验证删除结果
        remaining_sessions = context_manager.list_sessions()
        print(f"   删除后剩余会话数: {len(remaining_sessions)}")

        print("\n✅ 所有批量删除功能测试完成！")

    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
        print(f"已清理临时目录: {temp_dir}")

if __name__ == "__main__":
    test_batch_delete_features()