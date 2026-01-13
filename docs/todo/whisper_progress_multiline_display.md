# Whisper 进度多行显示实现方案

## 目标

实现 Whisper 工具执行过程中的进度信息多行显示，让用户能够实时看到转录进度。

## 设计原则

1. **简单实现**：使用多行显示，每条进度消息独立一行
2. **不干扰主要内容**：进度信息显示在独立区域，不影响主要对话内容
3. **保留历史**：所有进度消息都保留在屏幕上，方便查看完整进度
4. **兼容现有代码**：最小化修改，不影响现有功能

## 实现方案

### 1. 后端改进：捕获 Whisper 实时输出

#### 1.1 问题分析
- Whisper 的 `verbose=True` 会将进度输出到 stderr
- 当前实现无法捕获这些实时输出
- 需要重定向 stderr 并解析进度信息

#### 1.2 实现方式

**方案A：使用 contextlib.redirect_stderr（推荐）**

```python
# backend/core/agent/tools/builtin/whisper_tool.py

import contextlib
import sys
from io import StringIO
import re
import threading

class WhisperProgressCapture:
    """捕获 Whisper 的 stderr 输出并解析进度"""
    
    def __init__(self, progress_callback):
        self.progress_callback = progress_callback
        self.buffer = StringIO()
        self.capture_thread = None
        self.stop_event = threading.Event()
    
    def __enter__(self):
        # 保存原始 stderr
        self.original_stderr = sys.stderr
        # 重定向到缓冲区
        sys.stderr = self.buffer
        # 启动后台线程读取缓冲区
        self.capture_thread = threading.Thread(
            target=self._read_buffer,
            daemon=True
        )
        self.capture_thread.start()
        return self
    
    def __exit__(self, *args):
        # 恢复原始 stderr
        sys.stderr = self.original_stderr
        # 停止读取线程
        self.stop_event.set()
        if self.capture_thread:
            self.capture_thread.join(timeout=1)
    
    def _read_buffer(self):
        """后台线程读取缓冲区内容"""
        last_pos = 0
        while not self.stop_event.is_set():
            try:
                content = self.buffer.getvalue()
                if len(content) > last_pos:
                    new_content = content[last_pos:]
                    # 解析进度信息
                    progress_msg = self._parse_progress(new_content)
                    if progress_msg and self.progress_callback:
                        self.progress_callback(progress_msg)
                    last_pos = len(content)
                time.sleep(0.5)  # 每0.5秒检查一次
            except Exception as e:
                logger.warning(f"进度捕获错误: {e}")
                break
    
    def _parse_progress(self, content: str) -> Optional[str]:
        """解析 Whisper 进度输出
        
        Whisper 输出格式示例：
        [00:00 > 00:05, 0.00x]  # 已处理时间 > 总时间, 速度倍数
        [00:00 > 00:05, 0.00x, ?]  # 带问号表示不确定
        
        返回格式化的进度消息
        """
        # 匹配进度格式：[HH:MM > HH:MM, X.XXx]
        pattern = r'\[(\d{2}:\d{2})\s*>\s*(\d{2}:\d{2}),\s*([\d.]+)x'
        matches = re.findall(pattern, content)
        
        if matches:
            # 取最后一个匹配（最新的进度）
            current_time, total_time, speed = matches[-1]
            return f"转录进行中... [{current_time} / {total_time}, {speed}x]"
        
        return None
```

**方案B：使用 subprocess 包装（备选）**

如果方案A不够稳定，可以考虑使用 subprocess 包装 Whisper 调用，但这需要更多修改。

#### 1.3 集成到 WhisperTool.execute()

```python
# 在 execute() 方法中

# 创建进度捕获器
progress_capture = WhisperProgressCapture(
    progress_callback=lambda msg: self.report_progress(msg)
)

# 在转录时使用
with progress_capture:
    result = model.transcribe(
        str(audio_path),
        language=language,
        word_timestamps=False,
        verbose=True,  # 启用详细输出
        fp16=False,
        temperature=0.0,
        best_of=1,
        beam_size=1
    )
```

### 2. 前端实现：处理进度消息

#### 2.1 添加进度消息处理

**在 `frontend/ui/stream_handler.py` 中：**

```python
# 在 render_stream() 方法中，添加进度消息处理

elif line.startswith("__PROGRESS__:"):
    try:
        json_str = line[12:]  # 移除 "__PROGRESS__:" 前缀
        json_str = self._clean_unicode(json_str)
        progress_data = json.loads(json_str)
        self._render_progress_info(progress_data, console)
    except (json.JSONDecodeError, KeyError, UnicodeDecodeError) as e:
        # JSON 解析失败，跳过
        logger.debug(f"进度消息解析失败: {e}")
        pass
```

#### 2.2 实现进度渲染方法

```python
def _render_progress_info(self, progress_data: dict, console: Console):
    """渲染进度信息（多行显示）
    
    Args:
        progress_data: 进度数据，格式：
            {
                "type": "progress",
                "category": "tool",
                "tool_name": "whisper",
                "message": "转录进行中... 已用时: 00:30"
            }
        console: Rich Console 实例
    """
    tool_name = progress_data.get("tool_name", "unknown")
    message = progress_data.get("message", "")
    category = progress_data.get("category", "tool")
    
    # 根据工具名称选择图标和颜色
    tool_icons = {
        "whisper": "🎤",
        "video_downloader": "📥",
        "ffmpeg": "🎬",
        "jupyter": "📓",
    }
    
    icon = tool_icons.get(tool_name, "📊")
    
    # 根据消息类型选择样式
    if "完成" in message or "完成" in message:
        # 完成消息，使用绿色
        style = "green"
    elif "错误" in message or "失败" in message:
        # 错误消息，使用红色
        style = "red"
    elif "进行中" in message or "加载" in message:
        # 进行中消息，使用青色
        style = "cyan"
    else:
        # 默认样式
        style = "dim cyan"
    
    # 多行显示：每条消息独立一行
    console.print(f"[{style}]{icon} {tool_name}[/{style}]: {message}")
```

#### 2.3 优化显示格式

**可选：添加时间戳**

```python
from datetime import datetime

def _render_progress_info(self, progress_data: dict, console: Console):
    """渲染进度信息（带时间戳）"""
    tool_name = progress_data.get("tool_name", "unknown")
    message = progress_data.get("message", "")
    
    # 添加时间戳（可选）
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    icon = tool_icons.get(tool_name, "📊")
    style = self._get_progress_style(message)
    
    # 格式：时间戳 + 图标 + 工具名 + 消息
    console.print(
        f"[dim]{timestamp}[/dim] "
        f"[{style}]{icon} {tool_name}[/{style}]: {message}"
    )
```

### 3. 进度消息格式规范

#### 3.1 消息类型

1. **开始消息**：`"正在加载 Whisper 模型: base..."`
2. **进行中消息**：`"转录进行中... 已用时: 00:30, 估算进度: 15.5%"`
3. **完成消息**：`"转录完成！总用时: 02:15"`
4. **错误消息**：`"转录失败: 错误信息"`

#### 3.2 消息格式建议

- **简洁明了**：消息不要太长，避免换行
- **包含关键信息**：时间、进度百分比（如果可获取）
- **用户友好**：使用中文，避免技术术语

### 4. 实现步骤

#### 阶段1：基础实现（快速验证）

1. ✅ 后端已支持进度回调（无需修改）
2. ⚠️ 改进 Whisper 工具的进度报告
   - 添加 `WhisperProgressCapture` 类
   - 集成到 `execute()` 方法
   - 测试进度捕获是否正常工作
3. ⚠️ 前端添加 `__PROGRESS__` 消息处理
   - 在 `render_stream()` 中添加处理逻辑
   - 实现 `_render_progress_info()` 方法
   - 测试进度显示是否正常

**预计时间**：1-2 小时

#### 阶段2：优化改进（后续）

1. 优化进度解析：更准确地解析 Whisper 输出
2. 添加进度百分比计算（如果可能）
3. 优化显示格式：添加时间戳、图标等
4. 处理多工具同时执行的情况

**预计时间**：2-3 小时

### 5. 测试方案

#### 5.1 单元测试

```python
# tests/test_whisper_progress.py

def test_progress_capture():
    """测试进度捕获"""
    messages = []
    
    def callback(msg):
        messages.append(msg)
    
    capture = WhisperProgressCapture(callback)
    # 模拟 Whisper 输出
    # 验证消息是否正确捕获
```

#### 5.2 集成测试

1. 使用真实的音频文件测试
2. 验证进度消息是否正确发送到前端
3. 验证前端是否正确显示进度

### 6. 注意事项

1. **线程安全**：进度捕获在后台线程中，确保线程安全
2. **性能影响**：进度更新不要太频繁（建议每1-2秒一次）
3. **错误处理**：如果进度解析失败，应该降级到简单文本显示
4. **用户体验**：进度信息应该清晰、不干扰主要内容显示
5. **兼容性**：确保不影响现有功能

### 7. 参考实现

- **视频下载工具**：`backend/core/agent/tools/builtin/video_downloader_tool.py`
  - 已实现进度回调机制
  - 可以参考其实现方式

- **Orchestrator 进度处理**：`backend/core/agent/orchestrator.py`
  - 已实现进度消息发送机制
  - 使用 `__PROGRESS__:` 前缀

### 8. 后续优化方向

1. **进度条显示**：如果能够解析百分比，可以使用 Rich Progress 组件
2. **进度历史记录**：保存进度历史，方便查看
3. **多工具进度管理**：多个工具同时执行时的进度管理
4. **进度估算**：基于音频时长和已用时间估算剩余时间

## 文件清单

需要修改的文件：
1. `backend/core/agent/tools/builtin/whisper_tool.py` - 添加进度捕获
2. `frontend/ui/stream_handler.py` - 添加进度消息处理

需要创建的文件：
1. `tests/test_whisper_progress.py` - 进度捕获测试（可选）

## 验收标准

1. ✅ Whisper 执行时，进度消息能够实时显示在前端
2. ✅ 进度消息格式清晰、易读
3. ✅ 不影响现有功能（调试信息、工具调用等）
4. ✅ 多行显示，每条消息独立一行
5. ✅ 进度消息包含关键信息（时间、状态等）

