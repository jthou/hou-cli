# browser-use 异步等待机制说明

## 重要：不要使用 sleep 等待！

browser-use 使用**事件驱动架构**，有完善的异步通知机制。**永远不要使用 `sleep()` 来等待任务完成**，这是非常愚蠢和低效的做法。

## browser-use 的异步通知机制

### 1. 页面加载完成通知

browser-use 通过以下机制检测页面加载完成：

- **NavigationCompleteEvent**：导航完成事件
  - 当页面导航完成时触发
  - 包含 URL、状态码、错误信息等

- **CDP Lifecycle Events**：Chrome DevTools Protocol 生命周期事件
  - `load`：页面加载完成
  - `networkIdle`：网络空闲（所有请求完成）
  - `DOMContentLoaded`：DOM 内容加载完成

- **BrowserSession 监听**：
  - BrowserSession 通过 CDP 监听这些事件
  - 在 `_navigate_and_wait()` 中轮询检查事件
  - 检测到 `networkIdle` 或 `load` 事件时返回

### 2. Agent.run() 是异步方法

```python
async def run(
    self,
    max_steps: int = 100,
    on_step_start: AgentHookFunc | None = None,
    on_step_end: AgentHookFunc | None = None,
) -> AgentHistoryList[AgentStructuredOutput]:
```

**关键点**：
- `agent.run()` 是 `async def`，会等待所有步骤完成
- 返回 `AgentHistoryList` 时，任务已经完成
- **无需额外的 sleep 或等待**

### 3. 正确的使用方式

```python
import asyncio
from browser_use import Agent, BrowserProfile
from browser_use.llm.deepseek.chat import ChatDeepSeek

async def test():
    # 创建 Agent
    llm = ChatDeepSeek(model='deepseek-chat', api_key=api_key)
    agent = Agent(
        task="打开 www.baidu.com 并搜索",
        llm=llm,
        browser_profile=BrowserProfile(headless=True),
    )
    
    # ✅ 正确：直接 await，会等待任务完成
    history = await agent.run(max_steps=50)
    
    # 这里 history 返回时，任务已经完成
    print(f"执行步数: {len(history.all_results)}")
    print(f"是否成功: {not history.errors()}")

# 运行
asyncio.run(test())
```

### 4. 错误的使用方式（不要这样做！）

```python
# ❌ 错误：使用 sleep 等待
async def test():
    agent = Agent(...)
    task = asyncio.create_task(agent.run(max_steps=50))
    await asyncio.sleep(180)  # 愚蠢的等待！
    # 不知道任务是否完成，可能还在运行，也可能已经完成很久了

# ❌ 错误：在同步代码中使用 sleep
def test():
    agent = Agent(...)
    asyncio.run(agent.run(max_steps=50))  # 启动任务
    time.sleep(180)  # 非常愚蠢的等待！
    # 完全不知道任务状态
```

## 回调机制（可选）

browser-use 还提供了回调机制，可以在任务执行过程中接收通知：

```python
async def on_step(browser_state, agent_output, step_num):
    print(f"步骤 {step_num} 完成")

async def on_done(history):
    print(f"任务完成，共 {len(history.all_results)} 步")

agent = Agent(
    task="...",
    llm=llm,
    register_new_step_callback=on_step,  # 每步完成时调用
    register_done_callback=on_done,      # 任务完成时调用
)

# 即使有回调，run() 仍然会等待完成
history = await agent.run(max_steps=50)
```

## 总结

1. **browser-use 有完善的异步通知机制**，不需要 sleep
2. **`agent.run()` 是异步方法**，会等待任务完成
3. **直接 `await agent.run()`**，任务完成后才会继续执行
4. **永远不要使用 `sleep()` 等待任务完成**，这是非常愚蠢的设计

## 相关代码位置

- Agent.run(): `backend/externals/browser-use/browser_use/agent/service.py:2169`
- NavigationCompleteEvent: `backend/externals/browser-use/browser_use/browser/events.py:447`
- BrowserSession._navigate_and_wait(): `backend/externals/browser-use/browser_use/browser/session.py:796`
- CDP lifecycle events: `backend/externals/browser-use/browser_use/browser/session_manager.py:830`

