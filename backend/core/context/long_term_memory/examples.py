"""
长期记忆模块使用示例

本文件包含长期记忆模块的使用示例，展示如何使用 FileLongTermMemory 和与 ContextManager 集成。
"""
import sys
from pathlib import Path

# 添加项目根目录到路径（用于直接运行）
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from backend.core.context.long_term_memory import FileLongTermMemory, Memory, MemoryType
from backend.core.context import ContextManager, MessageRole


def example_basic_usage():
    """示例 1: 基本使用"""
    print("=" * 60)
    print("示例 1: 基本使用")
    print("=" * 60)
    
    # 创建长期记忆
    memory_store = FileLongTermMemory(storage_dir=Path("data/long_term_memory_example"))
    
    # 创建记忆
    memory = Memory(
        memory_id="mem_1",
        memory_type=MemoryType.KNOWLEDGE,
        content="Python 是一种高级编程语言",
        summary="Python 编程语言简介",
        tags=["python", "programming"]
    )
    
    # 保存记忆
    memory_store.save_memory(memory)
    print(f"保存记忆: {memory.memory_id}")
    
    # 获取记忆
    retrieved = memory_store.get_memory("mem_1")
    print(f"获取记忆: {retrieved.content}")
    print(f"访问次数: {retrieved.access_count}")


def example_search():
    """示例 2: 搜索记忆"""
    print("\n" + "=" * 60)
    print("示例 2: 搜索记忆")
    print("=" * 60)
    
    memory_store = FileLongTermMemory(storage_dir=Path("data/long_term_memory_example"))
    
    # 创建多个记忆
    memories = [
        Memory(
            memory_id=f"mem_{i}",
            memory_type=MemoryType.KNOWLEDGE,
            content=f"Knowledge {i}: Python programming",
            tags=["python", "knowledge"]
        )
        for i in range(1, 4)
    ]
    
    for mem in memories:
        memory_store.save_memory(mem)
    
    # 搜索记忆
    results = memory_store.search_memories("Python", top_k=5)
    print(f"搜索 'Python' 找到 {len(results)} 条记忆:")
    for mem in results:
        print(f"  - {mem.content}")


def example_context_manager_integration():
    """示例 3: 与 ContextManager 集成"""
    print("\n" + "=" * 60)
    print("示例 3: 与 ContextManager 集成")
    print("=" * 60)
    
    # 创建长期记忆
    long_term_memory = FileLongTermMemory(storage_dir=Path("data/long_term_memory_example"))
    
    # 创建带长期记忆的 ContextManager
    context_manager = ContextManager(
        storage_dir=Path("data/contexts_example"),
        long_term_memory=long_term_memory,
        auto_save_to_memory=True  # 自动保存到长期记忆
    )
    
    # 创建会话
    session_id = context_manager.create_session()
    print(f"创建会话: {session_id}")
    
    # 添加消息（自动保存到长期记忆）
    context_manager.add_message(session_id, MessageRole.USER, "I like using Python for data analysis")
    print("添加消息（自动保存到长期记忆）")
    
    # 从长期记忆检索相关信息
    relevant = context_manager.get_relevant_memories("Python", top_k=5)
    print(f"检索到 {len(relevant)} 条相关记忆:")
    for mem in relevant:
        print(f"  - {mem.content}")


def example_manual_save():
    """示例 4: 手动保存到长期记忆"""
    print("\n" + "=" * 60)
    print("示例 4: 手动保存到长期记忆")
    print("=" * 60)
    
    long_term_memory = FileLongTermMemory(storage_dir=Path("data/long_term_memory_example"))
    
    context_manager = ContextManager(
        storage_dir=Path("data/contexts_example"),
        long_term_memory=long_term_memory,
        auto_save_to_memory=False  # 不自动保存
    )
    
    session_id = context_manager.create_session()
    
    # 手动保存到长期记忆
    context_manager.add_message(
        session_id,
        MessageRole.USER,
        "Important information about machine learning",
        save_to_memory=True  # 手动指定保存
    )
    
    # 验证已保存
    memories = long_term_memory.search_memories("machine learning", top_k=5)
    print(f"手动保存后，搜索到 {len(memories)} 条记忆")


if __name__ == "__main__":
    """运行所有示例"""
    example_basic_usage()
    example_search()
    example_context_manager_integration()
    example_manual_save()
    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)

