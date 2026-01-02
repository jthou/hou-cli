# TODO-007: 调试日志和思考过程输出实现

## 任务概述

实现开发环境的调试输出功能，包括：
1. 模型的思考过程输出（如果 LLM 支持）
2. 后端的 debug 流程输出（Orchestrator 处理流程）
3. 上下文过程输出（ContextManager 操作）
4. 环境区分（开发环境默认开启，生产环境默认关闭）

**优先级**: P0（高优先级）  
**预计工时**: 1-2 天  
**创建时间**: 2025-01-02  
**状态**: ✅ 已完成

---

## 需求分析

### 1. 模型的思考过程输出

**需求**:
- 如果 LLM 支持思考过程（如 DeepSeek R1），需要输出思考过程
- 思考过程应该在开发环境中显示，帮助理解模型推理

**当前状态**:
- 使用 `deepseek-chat` 模型（不支持思考过程）
- 如果切换到 `deepseek-r1` 模型，可能支持思考过程

**实现方案**:
- 检测模型是否支持思考过程
- 在开发环境中输出思考过程
- 思考过程使用特殊的格式显示（如缩进、不同颜色）

### 2. 后端 Debug 流程输出

**需求**:
- 在开发环境中输出 Orchestrator 的处理流程
- 包括：任务接收、上下文获取、LLM 调用、结果返回等步骤

**输出内容**:
- 任务接收日志
- 会话 ID 处理日志
- 历史消息获取日志
- LLM 调用参数日志
- 响应处理日志

### 3. 上下文过程输出

**需求**:
- 在开发环境中输出 ContextManager 的操作
- 包括：会话创建、消息添加、历史获取等

**输出内容**:
- 会话创建日志
- 消息添加日志（角色、内容摘要）
- 历史消息获取日志（消息数量、内容摘要）
- 会话清理日志

### 4. 环境区分

**需求**:
- 开发环境：默认开启调试输出
- 生产环境：默认关闭调试输出
- 可通过环境变量控制

**实现方案**:
- 使用 `DEBUG` 或 `ENV` 环境变量
- 默认值：开发环境 `DEBUG=true`，生产环境 `DEBUG=false`

---

## 任务分解

### 阶段 1: 环境配置和日志系统（P0）

#### 任务 1.1: 添加调试配置

**文件**: `shared/config.py`, `env.example`

**实现步骤**:

1. **更新 `shared/config.py`**
   ```python
   @dataclass
   class Config:
       # ... 现有配置 ...
       
       # 调试配置
       debug: bool = os.getenv("DEBUG", "false").lower() == "true"
       env: str = os.getenv("ENV", "development")  # development/production
       
       @property
       def is_development(self) -> bool:
           """判断是否为开发环境"""
           return self.env.lower() == "development" or self.debug
   ```

2. **更新 `env.example`**
   ```bash
   # 开发环境配置
   # 默认值：development（开发环境）
   ENV=development
   
   # 调试模式
   # 默认值：false（生产环境关闭）
   # 开发环境建议：true
   DEBUG=true
   ```

**验收标准**:
- [ ] 配置类支持 DEBUG 和 ENV 环境变量
- [ ] 默认值正确（开发环境开启，生产环境关闭）
- [ ] `env.example` 已更新

---

#### 任务 1.2: 创建调试输出工具

**文件**: `shared/debug_utils.py`（新建）

**实现步骤**:

1. **创建调试输出工具类**
   ```python
   """调试输出工具"""
   import logging
   from typing import Optional, Any, Dict, List
   from rich.console import Console
   from rich.panel import Panel
   from rich.text import Text
   from shared.config import Config
   
   config = Config()
   console = Console()
   logger = logging.getLogger(__name__)
   
   class DebugOutput:
       """调试输出类"""
       
       def __init__(self, enabled: Optional[bool] = None):
           """
           初始化调试输出
           
           Args:
               enabled: 是否启用调试输出，None 时使用配置
           """
           self.enabled = enabled if enabled is not None else config.is_development
       
       def log(self, message: str, level: str = "info"):
           """输出调试日志"""
           if not self.enabled:
               return
           
           # 使用 logger 记录
           if level == "debug":
               logger.debug(message)
           elif level == "info":
               logger.info(message)
           elif level == "warning":
               logger.warning(message)
           elif level == "error":
               logger.error(message)
           
           # 使用 Rich 输出到控制台（开发环境）
           if config.is_development:
               style = {
                   "debug": "dim cyan",
                   "info": "dim blue",
                   "warning": "yellow",
                   "error": "red"
               }.get(level, "dim")
               console.print(f"[{style}][DEBUG][/{style}] {message}")
       
       def log_orchestrator_step(self, step: str, details: Optional[Dict] = None):
           """输出 Orchestrator 处理步骤"""
           if not self.enabled:
               return
           
           message = f"Orchestrator: {step}"
           if details:
               detail_str = ", ".join([f"{k}={v}" for k, v in details.items()])
               message += f" ({detail_str})"
           
           self.log(message, level="debug")
       
       def log_context_operation(self, operation: str, session_id: str, details: Optional[Dict] = None):
           """输出上下文操作"""
           if not self.enabled:
               return
           
           message = f"ContextManager: {operation} (session_id={session_id[:8]}...)"
           if details:
               detail_str = ", ".join([f"{k}={v}" for k, v in details.items()])
               message += f" ({detail_str})"
           
           self.log(message, level="debug")
       
       def log_llm_request(self, system_prompt: str, user_prompt: str, model: str):
           """输出 LLM 请求信息"""
           if not self.enabled:
               return
           
           # 截断长文本用于显示
           system_preview = system_prompt[:50] + "..." if len(system_prompt) > 50 else system_prompt
           user_preview = user_prompt[:100] + "..." if len(user_prompt) > 100 else user_prompt
           
           self.log(f"LLM Request: model={model}", level="debug")
           self.log(f"  System: {system_preview}", level="debug")
           self.log(f"  User: {user_preview}", level="debug")
       
       def log_llm_response(self, response: str, model: str):
           """输出 LLM 响应信息"""
           if not self.enabled:
               return
           
           preview = response[:100] + "..." if len(response) > 100 else response
           self.log(f"LLM Response: model={model}, length={len(response)}", level="debug")
           self.log(f"  Preview: {preview}", level="debug")
       
       def log_llm_thinking(self, thinking: str):
           """输出 LLM 思考过程（如果支持）"""
           if not self.enabled:
               return
           
           # 使用 Panel 显示思考过程
           console.print(Panel(
               thinking,
               border_style="dim cyan",
               title="[dim cyan]🤔 模型思考过程[/dim cyan]",
               padding=(1, 2)
           ))
   ```

**验收标准**:
- [ ] 调试输出工具类已创建
- [ ] 支持环境检测
- [ ] 支持多种日志级别
- [ ] 支持格式化输出

---

### 阶段 2: 集成调试输出（P0）

#### 任务 2.1: Orchestrator 集成调试输出

**文件**: `backend/core/agent/orchestrator.py`

**实现步骤**:

1. **导入调试工具**
   ```python
   from shared.debug_utils import DebugOutput
   ```

2. **在 `__init__` 中创建调试输出实例**
   ```python
   def __init__(self):
       self.coordinator = AgentCoordinator()
       self.llm_service = LLMService()
       self.context_manager = ContextManager(max_history=10)
       self.debug = DebugOutput()  # 调试输出
   ```

3. **在 `process_dynamic` 中添加调试输出**
   ```python
   async def process_dynamic(self, task: str, context: Optional[Dict] = None) -> str:
       """动态编排执行"""
       self.debug.log_orchestrator_step("开始处理任务", {"task": task[:50]})
       
       # 获取会话 ID
       session_id = context.get("session_id") if context else None
       self.debug.log_context_operation("获取会话ID", session_id or "new", {"provided": session_id is not None})
       
       # 如果没有会话 ID，创建新会话
       if not session_id:
           session_id = self.context_manager.create_session()
           self.debug.log_context_operation("创建新会话", session_id)
       
       # 获取历史消息
       history = self.context_manager.get_history_for_llm(session_id)
       self.debug.log_context_operation("获取历史消息", session_id, {"count": len(history)})
       
       # 构建消息
       system_prompt = "你是一个智能助手，能够帮助用户解决各种问题。"
       # ... 构建 user_prompt ...
       
       # LLM 调用
       self.debug.log_llm_request(system_prompt, user_prompt, "deepseek-chat")
       response = await self.llm_service.chat(
           system_prompt=system_prompt,
           user_prompt=user_prompt
       )
       self.debug.log_llm_response(response, "deepseek-chat")
       
       # 保存消息
       self.context_manager.add_message(session_id, "user", task)
       self.context_manager.add_message(session_id, "assistant", response)
       self.debug.log_context_operation("保存消息", session_id, {"user": True, "assistant": True})
       
       self.debug.log_orchestrator_step("任务处理完成", {"response_length": len(response)})
       return response
   ```

4. **在 `stream_process` 中添加调试输出**
   ```python
   async def stream_process(self, task: str, context: Optional[Dict] = None) -> AsyncIterator[str]:
       """流式处理任务"""
       self.debug.log_orchestrator_step("开始流式处理任务", {"task": task[:50]})
       
       # ... 类似的处理 ...
       
       # 流式调用 LLM
       self.debug.log_llm_request(system_prompt, user_prompt, "deepseek-chat")
       full_response = ""
       
       async for chunk in self.llm_service.stream_chat(...):
           full_response += chunk
           yield chunk
       
       self.debug.log_llm_response(full_response, "deepseek-chat")
       # ... 保存消息 ...
   ```

**验收标准**:
- [ ] Orchestrator 的关键步骤都有调试输出
- [ ] 输出信息清晰有用
- [ ] 开发环境显示，生产环境不显示

---

#### 任务 2.2: ContextManager 集成调试输出

**文件**: `backend/core/agent/context_manager.py`

**实现步骤**:

1. **导入调试工具**
   ```python
   from shared.debug_utils import DebugOutput
   ```

2. **在 `__init__` 中创建调试输出实例**
   ```python
   def __init__(self, max_history: int = 10):
       self.max_history = max_history
       self.sessions: Dict[str, deque] = {}
       self.debug = DebugOutput()
   ```

3. **在关键方法中添加调试输出**
   ```python
   def create_session(self) -> str:
       """创建新会话"""
       session_id = str(uuid.uuid4())
       self.sessions[session_id] = deque(maxlen=self.max_history)
       self.debug.log_context_operation("创建会话", session_id)
       return session_id
   
   def add_message(self, session_id: str, role: str, content: str):
       """添加消息到会话历史"""
       if session_id not in self.sessions:
           self.sessions[session_id] = deque(maxlen=self.max_history)
           self.debug.log_context_operation("自动创建会话", session_id)
       
       self.sessions[session_id].append({
           "role": role,
           "content": content
       })
       
       # 调试输出（截断长内容）
       content_preview = content[:50] + "..." if len(content) > 50 else content
       self.debug.log_context_operation(
           "添加消息",
           session_id,
           {"role": role, "content_length": len(content), "preview": content_preview}
       )
   
   def get_history(self, session_id: str) -> List[Dict[str, str]]:
       """获取会话历史"""
       history = list(self.sessions[session_id]) if session_id in self.sessions else []
       self.debug.log_context_operation(
           "获取历史",
           session_id,
           {"count": len(history), "max_history": self.max_history}
       )
       return history
   ```

**验收标准**:
- [ ] ContextManager 的关键操作都有调试输出
- [ ] 输出信息包含有用的上下文信息
- [ ] 开发环境显示，生产环境不显示

---

#### 任务 2.3: LLM Service 集成调试输出和思考过程

**文件**: `backend/services/llm/llm_service.py`

**实现步骤**:

1. **导入调试工具**
   ```python
   from shared.debug_utils import DebugOutput
   ```

2. **在 `__init__` 中创建调试输出实例**
   ```python
   def __init__(self, temperature: float = 0.7, max_tokens: int = 2000):
       # ... 现有代码 ...
       self.debug = DebugOutput()
       self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")  # 支持切换模型
   ```

3. **检测模型是否支持思考过程**
   ```python
   @property
   def supports_thinking(self) -> bool:
       """检测模型是否支持思考过程"""
       # DeepSeek R1 模型支持思考过程
       return "r1" in self.model.lower() or "reasoning" in self.model.lower()
   ```

4. **在 `chat` 方法中添加调试输出和思考过程处理**
   ```python
   async def chat(self, system_prompt: str = "", user_prompt: str = "") -> str:
       """聊天（非流式）"""
       messages = []
       if system_prompt:
           messages.append({"role": "system", "content": system_prompt})
       messages.append({"role": "user", "content": user_prompt})
       
       # 调试输出：请求信息
       self.debug.log_llm_request(system_prompt, user_prompt, self.model)
       
       # ... 重试逻辑 ...
       
       response = await self.client.chat.completions.create(
           model=self.model,
           messages=messages,
           stream=False,
           temperature=self.temperature,
           max_tokens=self.max_tokens
       )
       
       # 处理思考过程（如果支持）
       result = response.choices[0].message
       content = result.content
       
       # 检查是否有思考过程（DeepSeek R1 格式）
       if self.supports_thinking and hasattr(result, 'reasoning_content'):
           thinking = result.reasoning_content
           if thinking:
               self.debug.log_llm_thinking(thinking)
       
       # 调试输出：响应信息
       self.debug.log_llm_response(content, self.model)
       
       return content
   ```

5. **在 `stream_chat` 方法中添加思考过程处理**
   ```python
   async def stream_chat(self, system_prompt: str = "", user_prompt: str = "", timeout: int = 60) -> AsyncIterator[str]:
       """流式聊天"""
       # ... 现有代码 ...
       
       # 调试输出：请求信息
       self.debug.log_llm_request(system_prompt, user_prompt, self.model)
       
       stream = await asyncio.wait_for(
           self.client.chat.completions.create(
               model=self.model,
               messages=messages,
               stream=True,
               temperature=self.temperature,
               max_tokens=self.max_tokens
           ),
           timeout=timeout
       )
       
       # 收集思考过程（如果支持）
       thinking_chunks = []
       content_chunks = []
       
       async for chunk in stream:
           # 处理思考过程（DeepSeek R1 格式）
           if self.supports_thinking:
               if hasattr(chunk.choices[0].delta, 'reasoning_content'):
                   thinking_chunk = chunk.choices[0].delta.reasoning_content
                   if thinking_chunk:
                       thinking_chunks.append(thinking_chunk)
           
           # 处理内容
           if chunk.choices[0].delta.content:
               yield chunk.choices[0].delta.content
       
       # 如果有思考过程，输出完整思考过程
       if thinking_chunks:
           thinking = "".join(thinking_chunks)
           self.debug.log_llm_thinking(thinking)
   ```

**验收标准**:
- [ ] LLM 请求和响应都有调试输出
- [ ] 支持思考过程检测和输出
- [ ] 思考过程使用特殊格式显示
- [ ] 开发环境显示，生产环境不显示

---

### 阶段 3: 日志系统配置（P1）

#### 任务 3.1: 配置日志系统

**文件**: `backend/main.py`

**实现步骤**:

1. **配置日志系统**
   ```python
   import logging
   from shared.config import Config
   
   config = Config()
   
   # 配置日志
   log_level = logging.DEBUG if config.is_development else logging.INFO
   logging.basicConfig(
       level=log_level,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
       datefmt='%Y-%m-%d %H:%M:%S'
   )
   ```

2. **在启动时输出环境信息**
   ```python
   def main():
       """启动 IPC 服务器"""
       # ... 现有代码 ...
       
       # 输出环境信息（开发环境）
       if config.is_development:
           console.print(f"[dim]环境: 开发模式[/dim]")
           console.print(f"[dim]调试输出: 已启用[/dim]")
           console.print(f"[dim]日志级别: DEBUG[/dim]\n")
       
       print(f"后端服务启动在 http://127.0.0.1:{port}")
       # ...
   ```

**验收标准**:
- [ ] 日志系统正确配置
- [ ] 开发环境使用 DEBUG 级别
- [ ] 生产环境使用 INFO 级别

---

## 实现计划

### 阶段 1: 环境配置和工具（0.5 天）

1. ✅ 任务 1.1: 添加调试配置
2. ✅ 任务 1.2: 创建调试输出工具

### 阶段 2: 集成调试输出（0.5 天）

3. ✅ 任务 2.1: Orchestrator 集成调试输出
4. ✅ 任务 2.2: ContextManager 集成调试输出
5. ✅ 任务 2.3: LLM Service 集成调试输出和思考过程

### 阶段 3: 日志系统配置（0.5 天）

6. ✅ 任务 3.1: 配置日志系统

---

## 详细实现步骤

### 步骤 1: 更新配置系统

**文件**: `shared/config.py`

```python
@dataclass
class Config:
    # ... 现有配置 ...
    
    # 调试配置
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    env: str = os.getenv("ENV", "development")  # development/production
    
    @property
    def is_development(self) -> bool:
        """判断是否为开发环境"""
        return self.env.lower() == "development" or self.debug
    
    @property
    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return not self.is_development
```

**文件**: `env.example`

```bash
# 开发环境配置
# 可选值：development（开发环境）, production（生产环境）
# 默认值：development
ENV=development

# 调试模式
# 可选值：true（启用）, false（禁用）
# 默认值：false（生产环境关闭）
# 开发环境建议：true
DEBUG=true
```

---

### 步骤 2: 创建调试输出工具

**文件**: `shared/debug_utils.py`（新建）

完整实现见任务 1.2。

---

### 步骤 3: 集成到 Orchestrator

**文件**: `backend/core/agent/orchestrator.py`

在关键位置添加调试输出，见任务 2.1。

---

### 步骤 4: 集成到 ContextManager

**文件**: `backend/core/agent/context_manager.py`

在关键操作添加调试输出，见任务 2.2。

---

### 步骤 5: 集成到 LLM Service

**文件**: `backend/services/llm/llm_service.py`

添加调试输出和思考过程处理，见任务 2.3。

---

## 测试计划

### 单元测试

1. **调试输出工具测试**
   - 测试环境检测
   - 测试输出控制
   - 测试格式化输出

2. **配置系统测试**
   - 测试环境变量读取
   - 测试默认值
   - 测试环境判断

### 集成测试

1. **开发环境测试**
   - 设置 `DEBUG=true` 或 `ENV=development`
   - 启动后端，验证调试输出
   - 发送请求，验证流程输出

2. **生产环境测试**
   - 设置 `DEBUG=false` 或 `ENV=production`
   - 启动后端，验证无调试输出
   - 发送请求，验证正常功能

3. **思考过程测试**（如果使用 R1 模型）
   - 切换到 `deepseek-r1` 模型
   - 发送请求，验证思考过程输出

---

## 验收标准

### 功能验收

- [ ] 开发环境默认显示调试输出
- [ ] 生产环境默认不显示调试输出
- [ ] 可通过环境变量控制
- [ ] Orchestrator 流程有调试输出
- [ ] ContextManager 操作有调试输出
- [ ] LLM 请求/响应有调试输出
- [ ] 思考过程正确输出（如果支持）

### 代码质量验收

- [ ] 代码符合项目规范
- [ ] 添加必要的注释
- [ ] 性能影响最小（生产环境无影响）
- [ ] 测试覆盖充分

---

## 输出示例

### 开发环境输出示例

```
[dim][DEBUG][/dim] Orchestrator: 开始处理任务 (task=你好)
[dim][DEBUG][/dim] ContextManager: 获取会话ID (session_id=12345678..., provided=False)
[dim][DEBUG][/dim] ContextManager: 创建会话 (session_id=12345678...)
[dim][DEBUG][/dim] ContextManager: 获取历史消息 (session_id=12345678..., count=0)
[dim][DEBUG][/dim] LLM Request: model=deepseek-chat
[dim][DEBUG][/dim]   System: 你是一个智能助手，能够帮助用户解决各种问题。
[dim][DEBUG][/dim]   User: 你好
[dim][DEBUG][/dim] LLM Response: model=deepseek-chat, length=50
[dim][DEBUG][/dim]   Preview: 你好！我是你的 AI 助手。
[dim][DEBUG][/dim] ContextManager: 添加消息 (session_id=12345678..., role=user, content_length=2)
[dim][DEBUG][/dim] ContextManager: 添加消息 (session_id=12345678..., role=assistant, content_length=50)
[dim][DEBUG][/dim] Orchestrator: 任务处理完成 (response_length=50)
```

### 思考过程输出示例（如果支持）

```
┌─ 🤔 模型思考过程 ─────────────────────────────────────┐
│                                                       │
│  用户问"你好"，这是一个简单的问候。我应该友好地回应，│
│  介绍自己，并询问如何帮助用户。                      │
│                                                       │
└───────────────────────────────────────────────────────┘
```

---

## 相关文档

- [环境变量配置指南](../design/03-env-configuration.md)
- [前端 UI 改进实现](./006-frontend-ui-improvements-implementation.md)

---

## 注意事项

1. **性能考虑**
   - 调试输出不应影响生产环境性能
   - 使用条件判断，避免不必要的字符串操作

2. **安全性**
   - 调试输出不应包含敏感信息（如完整 API Key）
   - 长文本应截断显示

3. **可配置性**
   - 支持细粒度控制（如只输出某些模块的调试信息）
   - 支持日志级别控制

---

**创建时间**: 2025-01-02  
**优先级**: P0  
**状态**: ✅ 已完成  
**完成时间**: 2025-01-02
