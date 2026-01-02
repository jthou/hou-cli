"""
上下文存储模块使用示例

本文件包含 ContextManager 的使用示例，展示如何使用上下文存储和整理功能。

运行方式:
    # 从项目根目录运行
    python -m backend.core.context.examples
    
    # 或设置 PYTHONPATH
    PYTHONPATH=. python backend/core/context/examples.py
"""
import sys
from pathlib import Path

# 添加项目根目录到路径（用于直接运行）
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from backend.core.context import ContextManager, MessageRole
from backend.core.context.compression.token_limit import TokenLimitCompression
from backend.core.context.compression.importance import ImportanceScoringCompression


def example_basic_usage():
    """示例 1: 基本使用"""
    print("=" * 60)
    print("示例 1: 基本使用")
    print("=" * 60)
    
    # 创建上下文管理器（使用默认配置）
    context_manager = ContextManager()
    
    # 创建会话
    session_id = context_manager.create_session()
    print(f"创建会话: {session_id}")
    
    # 添加消息
    context_manager.add_message(session_id, MessageRole.USER, "你好")
    context_manager.add_message(session_id, MessageRole.ASSISTANT, "你好！有什么可以帮助你的？")
    
    # 获取消息
    messages = context_manager.get_messages(session_id)
    print(f"会话包含 {len(messages)} 条消息")
    for msg in messages:
        print(f"  - {msg.role.value}: {msg.content}")
    
    # 获取用于 LLM 的格式
    llm_messages = context_manager.get_messages_for_llm(session_id)
    print(f"\nLLM 格式消息: {llm_messages}")


def example_file_storage():
    """示例 2: 使用文件存储"""
    print("\n" + "=" * 60)
    print("示例 2: 使用文件存储（持久化）")
    print("=" * 60)
    
    # 创建文件存储后端
    storage_dir = Path("data/contexts_example")
    context_manager = ContextManager(storage_dir=storage_dir)
    
    # 创建会话
    session_id = context_manager.create_session()
    print(f"创建会话: {session_id}")
    
    # 添加消息
    context_manager.add_message(session_id, MessageRole.USER, "消息内容")
    
    # 验证持久化：重新创建 ContextManager
    new_context_manager = ContextManager(storage_dir=storage_dir)
    messages = new_context_manager.get_messages(session_id)
    print(f"重启后恢复消息: {len(messages)} 条")
    for msg in messages:
        print(f"  - {msg.content}")


def example_compression():
    """示例 3: 使用压缩策略"""
    print("\n" + "=" * 60)
    print("示例 3: 消息压缩")
    print("=" * 60)
    
    context_manager = ContextManager(default_max_messages=5)
    
    session_id = context_manager.create_session()
    
    # 添加 10 条消息
    for i in range(10):
        context_manager.add_message(session_id, MessageRole.USER, f"消息 {i}")
    
    # 获取消息（自动压缩到 5 条）
    messages = context_manager.get_messages(session_id)
    print(f"压缩后消息数: {len(messages)}")
    print("保留的消息:")
    for msg in messages:
        print(f"  - {msg.content}")


def example_search():
    """示例 4: 搜索消息"""
    print("\n" + "=" * 60)
    print("示例 4: 搜索消息")
    print("=" * 60)
    
    context_manager = ContextManager()
    session_id = context_manager.create_session()
    
    # 添加多条消息
    context_manager.add_message(session_id, MessageRole.USER, "Python 编程")
    context_manager.add_message(session_id, MessageRole.ASSISTANT, "Python 是一种高级编程语言")
    context_manager.add_message(session_id, MessageRole.USER, "Java 开发")
    context_manager.add_message(session_id, MessageRole.ASSISTANT, "Java 是面向对象的编程语言")
    
    # 搜索包含 "Python" 的消息
    results = context_manager.search_messages(session_id, "Python", top_k=3)
    print(f"搜索 'Python' 找到 {len(results)} 条消息:")
    for msg in results:
        print(f"  - {msg.role.value}: {msg.content}")


def example_session_management():
    """示例 5: 会话管理"""
    print("\n" + "=" * 60)
    print("示例 5: 会话管理")
    print("=" * 60)
    
    context_manager = ContextManager()
    
    # 创建多个会话
    session_ids = []
    for i in range(3):
        session_id = context_manager.create_session(metadata={"topic": f"主题{i}"})
        session_ids.append(session_id)
        context_manager.add_message(session_id, MessageRole.USER, f"会话 {i} 的消息")
    
    # 列出所有会话
    sessions = context_manager.list_sessions()
    print(f"共有 {len(sessions)} 个会话:")
    for session in sessions:
        print(f"  - {session.session_id}: {session.metadata}")
    
    # 清除一个会话
    context_manager.clear_session(session_ids[0])
    print(f"\n清除会话后，剩余 {len(context_manager.list_sessions())} 个会话")


def example_token_limit_compression():
    """示例 6: Token 限制压缩"""
    print("\n" + "=" * 60)
    print("示例 6: Token 限制压缩")
    print("=" * 60)
    
    # 使用 TokenLimitCompression
    compression = TokenLimitCompression()
    context_manager = ContextManager(
        compression_strategy=compression,
        default_max_tokens=100
    )
    
    session_id = context_manager.create_session()
    
    # 添加多条长消息
    for i in range(10):
        context_manager.add_message(
            session_id,
            MessageRole.USER,
            f"消息 {i}: " + "x" * 50  # 每条约 12.5 tokens
        )
    
    # 获取消息（自动压缩到 100 tokens 以内）
    messages = context_manager.get_messages(session_id)
    print(f"压缩后消息数: {len(messages)}")
    print("保留的消息（优先保留系统消息，然后从后往前）:")
    for msg in messages:
        print(f"  - {msg.role.value}: {msg.content[:30]}...")


def example_importance_scoring_compression():
    """示例 7: 重要性评分压缩"""
    print("\n" + "=" * 60)
    print("示例 7: 重要性评分压缩")
    print("=" * 60)
    
    # 使用 ImportanceScoringCompression
    compression = ImportanceScoringCompression()
    context_manager = ContextManager(
        compression_strategy=compression,
        default_max_messages=5
    )
    
    session_id = context_manager.create_session()
    
    # 添加系统消息（高优先级）
    context_manager.add_message(session_id, MessageRole.SYSTEM, "系统配置信息")
    
    # 添加普通消息
    for i in range(8):
        context_manager.add_message(session_id, MessageRole.USER, f"普通消息 {i}")
    
    # 添加包含关键词的重要消息
    context_manager.add_message(session_id, MessageRole.USER, "重要的问题需要解决")
    context_manager.add_message(session_id, MessageRole.USER, "关键的错误发生了")
    
    # 获取消息（按重要性压缩）
    messages = context_manager.get_messages(session_id)
    print(f"压缩后消息数: {len(messages)}")
    print("保留的消息（按重要性排序）:")
    for msg in messages:
        print(f"  - {msg.role.value}: {msg.content}")
    
    # 验证重要消息被保留
    assert any(msg.role == MessageRole.SYSTEM for msg in messages)
    assert any("问题" in msg.content or "错误" in msg.content for msg in messages)


if __name__ == "__main__":
    """运行所有示例"""
    example_basic_usage()
    example_file_storage()
    example_compression()
    example_search()
    example_session_management()
    example_token_limit_compression()
    example_importance_scoring_compression()
    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)

