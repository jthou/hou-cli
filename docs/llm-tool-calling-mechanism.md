# LLM 工具调用机制详解

## 问题

Externals 中的第三方库（如 `browser-use`、`whisper`、`yt-dlp`、`ffmpeg`）如何被 LLM 调用？是通过编程的方式吗？

## 答案：通过 Function Calling 机制，间接调用

### 核心机制：Function Calling（函数调用）

LLM **不是直接调用** externals，而是通过以下调用链：

```
用户输入（自然语言）
  ↓
LLM（理解任务，决定调用哪个工具）
  ↓ Function Calling（函数调用机制）
Tools（工具层，实现 Tool 接口）
  ↓ 直接调用（编程方式）
Services 或 Externals（底层实现）
```

## 详细调用流程

### 1. 工具注册（启动时）

```python
# backend/core/agent/orchestrator.py

class Orchestrator:
    def _register_tools(self):
        """注册所有工具"""
        # 注册 whisper_tool
        from backend.core.agent.tools.builtin.whisper_tool import WhisperTool
        whisper_tool = WhisperTool()
        self.tool_registry.register(whisper_tool)
        
        # 注册 video_downloader_tool
        from backend.core.agent.tools.builtin.video_downloader_tool import VideoDownloaderTool
        video_tool = VideoDownloaderTool()
        self.tool_registry.register(video_tool)
```

### 2. 工具转换为 Function Calling 格式

```python
# backend/core/agent/tools/base.py

class Tool(ABC):
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 LLM Function Calling）"""
        return {
            "type": "function",
            "function": {
                "name": self.name,  # 例如："whisper_transcribe"
                "description": self.description,  # 工具描述
                "parameters": {
                    "type": "object",
                    "properties": {
                        "audio_file": {"type": "string", "description": "音频文件路径"},
                        "language": {"type": "string", "description": "语言代码"},
                        # ...
                    },
                    "required": ["audio_file"]
                }
            }
        }
```

### 3. LLM 调用（Function Calling）

```python
# backend/core/agent/orchestrator.py

async def process_dynamic(self, task: str):
    # 1. 获取工具定义（转换为 Function Calling 格式）
    tools = self.tool_registry.get_tools_for_llm()
    # tools = [
    #     {
    #         "type": "function",
    #         "function": {
    #             "name": "whisper_transcribe",
    #             "description": "Whisper 语音转文字工具",
    #             "parameters": {...}
    #         }
    #     },
    #     ...
    # ]
    
    # 2. 调用 LLM，传入工具定义
    response = await self.llm_service.chat(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        tools=tools  # ✅ 工具定义传递给 LLM
    )
    
    # 3. LLM 返回工具调用请求
    # response.tool_calls = [
    #     {
    #         "id": "call_123",
    #         "type": "function",
    #         "function": {
    #             "name": "whisper_transcribe",
    #             "arguments": '{"audio_file": "/path/to/audio.mp3", "language": "zh"}'
    #         }
    #     }
    # ]
```

### 4. 执行工具（编程方式）

```python
# backend/core/agent/orchestrator.py

# 4. 解析工具调用
for tool_call in response.tool_calls:
    tool_name = tool_call.function.name  # "whisper_transcribe"
    tool_args = json.loads(tool_call.function.arguments)
    
    # 5. 从注册表获取工具实例
    tool = self.tool_registry.get_tool(tool_name)
    
    # 6. 执行工具（编程方式调用）
    result = await tool.execute_async(**tool_args)
```

### 5. 工具内部使用 Externals（编程方式）

```python
# backend/core/agent/tools/builtin/whisper_tool.py

class WhisperTool(Tool):
    async def execute_async(self, **kwargs):
        """执行语音转文字"""
        audio_file = kwargs.get("audio_file")
        
        # ✅ 直接使用 externals 中的 whisper 库（编程方式）
        import whisper  # 从 externals/whisper/ 导入
        model = whisper.load_model("base")
        result = model.transcribe(audio_file)
        
        return ToolResult(success=True, data={"text": result["text"]})
```

## 完整调用链示例

### 示例：用户说"把这个音频转成文字"

```
1. 用户输入
   "把这个音频转成文字：/path/to/audio.mp3"
   
2. Orchestrator 准备工具
   tools = [
       {
           "type": "function",
           "function": {
               "name": "whisper_transcribe",
               "description": "Whisper 语音转文字工具",
               "parameters": {
                   "audio_file": {"type": "string", ...},
                   "language": {"type": "string", ...}
               }
           }
       },
       ...
   ]
   
3. LLM 调用（Function Calling）
   await llm_service.chat(
       user_prompt="把这个音频转成文字：/path/to/audio.mp3",
       tools=tools
   )
   
4. LLM 返回工具调用
   {
       "tool_calls": [{
           "function": {
               "name": "whisper_transcribe",
               "arguments": '{"audio_file": "/path/to/audio.mp3", "language": "auto"}'
           }
       }]
   }
   
5. Orchestrator 执行工具（编程方式）
   tool = tool_registry.get_tool("whisper_transcribe")
   result = await tool.execute_async(
       audio_file="/path/to/audio.mp3",
       language="auto"
   )
   
6. WhisperTool 使用 externals（编程方式）
   import whisper  # 从 externals/whisper/ 导入
   model = whisper.load_model("base")
   transcription = model.transcribe("/path/to/audio.mp3")
   
7. 返回结果给 LLM
   {
       "role": "tool",
       "tool_call_id": "call_123",
       "content": '{"text": "这是转录的文字内容..."}'
   }
   
8. LLM 生成最终回复
   "转录结果：这是转录的文字内容..."
```

## 关键点

### 1. LLM 不直接调用 Externals

- ❌ LLM 不会直接 `import whisper` 或调用 `ffmpeg`
- ✅ LLM 通过 Function Calling 机制调用 Tools
- ✅ Tools 内部使用编程方式调用 Externals

### 2. Function Calling 机制

**什么是 Function Calling？**
- OpenAI 等 LLM 提供商提供的标准机制
- LLM 可以"决定"调用哪个函数（工具）
- LLM 返回函数名称和参数（JSON 格式）
- 系统执行函数，将结果返回给 LLM
- LLM 基于结果生成最终回复

**格式：**
```json
{
  "type": "function",
  "function": {
    "name": "tool_name",
    "arguments": "{\"param1\": \"value1\", \"param2\": \"value2\"}"
  }
}
```

### 3. Tools 使用 Externals 的方式

**编程方式（直接调用）：**
```python
# whisper_tool.py
import whisper  # 从 externals/whisper/ 导入
model = whisper.load_model("base")
result = model.transcribe(audio_file)
```

**命令行方式（subprocess）：**
```python
# ffmpeg_tool.py
subprocess.run([
    "ffmpeg",  # 从 externals/ffmpeg/ 调用
    "-i", input_file,
    "-o", output_file
])
```

## 总结

### 调用方式

| 层级 | 调用方式 | 说明 |
|------|---------|------|
| **LLM → Tools** | Function Calling | LLM 通过标准协议调用工具 |
| **Tools → Services** | 编程方式 | Python 函数调用 |
| **Tools → Externals** | 编程方式 | Python import 或 subprocess |

### 关键理解

1. **LLM 不直接调用 Externals**
   - LLM 通过 Function Calling 调用 Tools
   - Tools 内部使用编程方式调用 Externals

2. **Function Calling 是标准协议**
   - OpenAI Function Calling 格式
   - 所有支持 Function Calling 的 LLM 都使用相同格式

3. **Tools 是桥梁**
   - 将 LLM 的 Function Calling 转换为实际的代码执行
   - 封装 Externals，提供统一的接口

### 类比

- **LLM** = 指挥官（通过命令调用工具）
- **Tools** = 工具（接收命令，执行任务）
- **Externals** = 实际工具（whisper、ffmpeg 等，被 Tools 使用）

指挥官（LLM）不会直接使用锤子（whisper），而是命令工人（Tool）使用锤子完成任务。

