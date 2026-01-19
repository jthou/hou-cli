# Whisper 进度显示设计方案

## 当前状态

### 后端（已实现）
- ✅ Orchestrator 已支持进度回调机制
- ✅ 通过 `__PROGRESS__:` 前缀发送进度消息到流式响应
- ✅ Whisper 工具已实现 `report_progress` 方法
- ⚠️ Whisper 进度报告基于时间估算，不够准确

### 前端（待实现）
- ❌ 未处理 `__PROGRESS__:` 消息
- ❌ 未显示进度信息

## 设计方案

### 1. 后端改进：捕获 Whisper 的实时输出

**问题**：Whisper 的 `verbose=True` 会将进度输出到 stderr，但当前实现无法捕获。

**解决方案**：
- 重定向 Whisper 的 stderr 输出
- 解析进度信息（如 `[00:00 > 00:05, 0.00x]`）
- 通过 `report_progress` 发送到前端

**实现方式**：
```python
# 在 whisper_tool.py 中
import subprocess
import sys
from io import StringIO

# 方法1：使用 threading 捕获 stderr
class StderrCapture:
    def __init__(self):
        self.buffer = StringIO()
        self.original_stderr = sys.stderr
    
    def __enter__(self):
        sys.stderr = self.buffer
        return self
    
    def __exit__(self, *args):
        sys.stderr = self.original_stderr
    
    def get_output(self):
        return self.buffer.getvalue()

# 方法2：使用 subprocess 包装（如果可能）
# 或者使用 contextlib.redirect_stderr
```

**进度解析**：
- Whisper 输出格式：`[00:00 > 00:05, 0.00x]` 或 `[00:00 > 00:05, 0.00x, ?]`
- 解析时间戳和速度信息
- 计算百分比（如果可能）

### 2. 前端实现：处理进度消息

**在 `stream_handler.py` 中添加**：
```python
elif line.startswith("__PROGRESS__:"):
    try:
        json_str = line[12:]  # 移除 "__PROGRESS__:" 前缀
        json_str = self._clean_unicode(json_str)
        progress_data = json.loads(json_str)
        self._render_progress_info(progress_data, console)
    except (json.JSONDecodeError, KeyError) as e:
        pass  # 解析失败，跳过
```

**渲染进度信息**：
```python
def _render_progress_info(self, progress_data: dict, console: Console):
    """渲染进度信息"""
    tool_name = progress_data.get("tool_name", "unknown")
    message = progress_data.get("message", "")
    category = progress_data.get("category", "tool")
    
    # 使用 Rich 的 Status 或 Progress 组件
    # 对于 Whisper，可以显示：
    # - 当前阶段（加载模型、转录中）
    # - 已用时间
    # - 估算进度（如果可解析）
    
    console.print(f"[dim cyan]📊 {tool_name}[/dim cyan]: {message}")
```

### 3. 进度显示优化

**方案A：简单文本显示**（推荐，快速实现）
- 直接显示进度消息
- 使用 Rich 的 `Status` 组件显示当前状态
- 优点：简单、快速
- 缺点：不够美观

**方案B：进度条显示**（更美观）
- 使用 Rich 的 `Progress` 组件
- 需要解析百分比信息
- 优点：美观、直观
- 缺点：需要解析 Whisper 输出格式

**方案C：混合显示**（最佳）
- 对于有百分比的情况，显示进度条
- 对于只有文本的情况，显示状态文本
- 动态切换显示方式

## 实现步骤

### 阶段1：基础进度显示（快速实现）
1. ✅ 后端已支持进度回调（无需修改）
2. ⚠️ 改进 Whisper 工具的进度报告（捕获 stderr）
3. ⚠️ 前端添加 `__PROGRESS__` 消息处理
4. ⚠️ 前端简单文本显示进度

### 阶段2：优化进度显示（后续改进）
1. 解析 Whisper 输出格式，提取百分比
2. 使用 Rich Progress 组件显示进度条
3. 添加进度历史记录（显示最近几条进度消息）

## 技术细节

### Whisper 输出格式示例
```
[00:00 > 00:05, 0.00x]  # 已处理时间 > 总时间, 速度倍数
[00:00 > 00:05, 0.00x, ?]  # 带问号表示不确定
```

### 进度消息格式
```json
{
  "type": "progress",
  "category": "tool",
  "tool_name": "whisper",
  "message": "转录进行中... 已用时: 00:30, 估算进度: 15.5%"
}
```

### 前端显示示例
```
📊 whisper: 正在加载 Whisper 模型: base...
📊 whisper: 模型加载完成: base
📊 whisper: 转录进行中... 已用时: 00:30, 估算进度: 15.5%
📊 whisper: 转录完成！总用时: 02:15
```

## 注意事项

1. **线程安全**：Whisper 的进度报告在后台线程中，需要确保线程安全
2. **性能**：进度更新不要太频繁（建议每1-2秒一次）
3. **错误处理**：如果进度解析失败，应该降级到简单文本显示
4. **用户体验**：进度信息应该清晰、不干扰主要内容显示

## 参考实现

- 视频下载工具已实现进度报告（`video_downloader_tool.py`）
- 可以参考其实现方式

