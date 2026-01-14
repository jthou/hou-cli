# Google 搜索工具事件循环问题修复

## 问题描述

Google 搜索工具在执行时出现错误：
```
Google 搜索失败: 搜索失败: Event loop is closed
```

## 根本原因

### 问题分析

1. **事件循环冲突**：
   - Google 搜索工具使用异步方法 `service.search()`
   - 当工具在已有运行的事件循环的上下文中执行时（例如在异步框架中），代码尝试使用 `asyncio.run()` 创建新的事件循环
   - `asyncio.run()` 不能在已有事件循环的线程中运行，导致 "Event loop is closed" 错误

2. **原始代码问题**：
   ```python
   # 问题代码
   try:
       loop = asyncio.get_running_loop()
       # 如果已有运行的事件循环，使用线程池执行
       with concurrent.futures.ThreadPoolExecutor() as executor:
           future = executor.submit(
               lambda: asyncio.run(service.search(...))  # ❌ 这里会失败
           )
   ```

3. **为什么失败**：
   - `asyncio.run()` 会尝试创建新的事件循环
   - 但在已有事件循环的线程中，这会导致冲突
   - 即使在新线程中，如果线程已经关联了事件循环，也会失败

## 解决方案

### 修复方法

在新线程中创建**完全独立**的事件循环：

```python
def run_in_new_loop():
    """在新线程中创建独立的事件循环并运行"""
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    try:
        return new_loop.run_until_complete(service.search(...))
    finally:
        new_loop.close()

with concurrent.futures.ThreadPoolExecutor() as executor:
    future = executor.submit(run_in_new_loop)
    response = future.result(timeout=30)
```

### 关键改进

1. **使用 `asyncio.new_event_loop()`**：
   - 创建全新的事件循环，不依赖当前线程的事件循环状态

2. **使用 `loop.run_until_complete()`**：
   - 直接在新事件循环上运行异步函数
   - 避免使用 `asyncio.run()`（它会在内部创建和关闭事件循环）

3. **正确清理**：
   - 在 `finally` 块中关闭事件循环
   - 确保资源正确释放

## 修复后的代码流程

```
1. 检查是否有运行的事件循环
   ├─ 有 → 使用 ThreadPoolExecutor 在新线程中执行
   │        └─ 在新线程中创建独立的事件循环
   │           └─ 使用 loop.run_until_complete() 运行异步函数
   │              └─ 关闭事件循环
   └─ 没有 → 直接使用 asyncio.run()
```

## 测试建议

1. **在同步上下文中测试**：
   ```python
   tool = GoogleSearchTool()
   result = tool.execute(query="test")
   ```

2. **在异步上下文中测试**：
   ```python
   async def test():
       tool = GoogleSearchTool()
       result = tool.execute(query="test")
   ```

3. **在已有事件循环的线程中测试**：
   ```python
   import asyncio
   
   async def main():
       # 模拟已有事件循环
       tool = GoogleSearchTool()
       result = tool.execute(query="test")
   
   asyncio.run(main())
   ```

## 相关技术说明

### asyncio.run() vs loop.run_until_complete()

- **`asyncio.run()`**：
  - 创建新的事件循环
  - 运行异步函数
  - 关闭事件循环
  - **限制**：不能在已有事件循环的线程中运行

- **`loop.run_until_complete()`**：
  - 在指定的事件循环上运行异步函数
  - 不创建新的事件循环
  - **优势**：可以在新线程中创建独立的事件循环

### 事件循环的生命周期

1. **创建**：`asyncio.new_event_loop()`
2. **设置**：`asyncio.set_event_loop(loop)`
3. **运行**：`loop.run_until_complete(coro)`
4. **关闭**：`loop.close()`

## 注意事项

1. **线程安全**：
   - 每个线程应该有自己独立的事件循环
   - 不要在多个线程之间共享事件循环

2. **资源清理**：
   - 确保在 `finally` 块中关闭事件循环
   - 避免资源泄漏

3. **超时处理**：
   - 使用 `future.result(timeout=30)` 设置超时
   - 避免长时间阻塞

## 其他可能的解决方案

### 方案 1：使用 nest_asyncio（不推荐）

```python
import nest_asyncio
nest_asyncio.apply()

# 然后可以使用 asyncio.run()
```

**缺点**：
- 需要额外依赖
- 可能引入其他问题
- 不是最佳实践

### 方案 2：完全异步化工具（推荐用于新工具）

```python
async def execute_async(self, **kwargs) -> ToolResult:
    # 直接使用 await
    response = await service.search(...)
```

**优点**：
- 更符合异步编程模式
- 性能更好
- 不需要线程池

**缺点**：
- 需要修改工具接口
- 需要调用方也支持异步

## 总结

修复后的代码能够：
- ✅ 在同步上下文中正常工作
- ✅ 在异步上下文中正常工作
- ✅ 在已有事件循环的线程中正常工作
- ✅ 正确处理资源清理
- ✅ 提供超时保护

