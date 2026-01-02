"""
数据库存储后端使用示例

本文件展示如何使用 DatabaseStorageBackend 和与 ContextManager 集成。
"""
import sys
from pathlib import Path

# 添加项目根目录到路径（用于直接运行）
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from backend.core.context import ContextManager, MessageRole
from backend.core.context.storage.database import DatabaseStorageBackend


def example_basic_usage():
    """示例 1: 基本使用"""
    print("=" * 60)
    print("示例 1: 基本使用（DatabaseStorageBackend）")
    print("=" * 60)
    
    # 创建数据库存储后端
    storage = DatabaseStorageBackend(db_path="data/contexts_example.db")
    
    # 创建使用数据库存储的 ContextManager
    context_manager = ContextManager(storage_backend=storage)
    
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


def example_persistence():
    """示例 2: 数据持久化"""
    print("\n" + "=" * 60)
    print("示例 2: 数据持久化")
    print("=" * 60)
    
    db_path = "data/contexts_persistence.db"
    
    # 第一次使用
    storage1 = DatabaseStorageBackend(db_path=db_path)
    manager1 = ContextManager(storage_backend=storage1)
    
    session_id = manager1.create_session()
    manager1.add_message(session_id, MessageRole.USER, "持久化测试消息")
    print(f"保存消息到数据库: {db_path}")
    
    # 重新创建（模拟重启）
    storage2 = DatabaseStorageBackend(db_path=db_path)
    manager2 = ContextManager(storage_backend=storage2)
    
    messages = manager2.get_messages(session_id)
    print(f"重启后恢复消息: {len(messages)} 条")
    for msg in messages:
        print(f"  - {msg.content}")


def example_storage_backend_switching():
    """示例 3: 存储后端切换"""
    print("\n" + "=" * 60)
    print("示例 3: 存储后端切换")
    print("=" * 60)
    
    from backend.core.context.storage.file import FileStorageBackend
    
    # 使用文件存储
    print("使用 FileStorageBackend:")
    file_storage = FileStorageBackend(storage_dir=Path("data/contexts_file"))
    file_manager = ContextManager(storage_backend=file_storage)
    session1 = file_manager.create_session()
    file_manager.add_message(session1, MessageRole.USER, "文件存储消息")
    print(f"  会话 {session1}: 文件存储")
    
    # 切换到数据库存储
    print("\n切换到 DatabaseStorageBackend:")
    db_storage = DatabaseStorageBackend(db_path="data/contexts_switch.db")
    db_manager = ContextManager(storage_backend=db_storage)
    session2 = db_manager.create_session()
    db_manager.add_message(session2, MessageRole.USER, "数据库存储消息")
    print(f"  会话 {session2}: 数据库存储")
    
    # 验证两个存储后端都正常工作
    print("\n验证两个存储后端:")
    print(f"  文件存储: {len(file_manager.get_messages(session1))} 条消息")
    print(f"  数据库存储: {len(db_manager.get_messages(session2))} 条消息")


if __name__ == "__main__":
    """运行所有示例"""
    example_basic_usage()
    example_persistence()
    example_storage_backend_switching()
    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)

