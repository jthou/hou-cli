# Browser Tool 支持 Qwen-VL 视觉功能

## 概述

Browser Tool 现在支持使用 Qwen-VL 模型来处理需要视觉理解的任务，解决了 DeepSeek 不支持 `use_vision=True` 的问题。

## 配置方法

### 1. 环境变量配置

在 `.env` 文件中添加以下配置：

```bash
# DeepSeek（默认，必需）
DEEPSEEK_API_KEY=your_deepseek_api_key

# 百炼平台（可选，用于视觉功能）
BAILIAN_API_KEY=your_bailian_api_key
BAILIAN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1  # 可选

# Browser Tool 视觉模型配置（可选）
BROWSER_TOOL_VISION_MODEL=qwen-vl-max-2025-08-13  # 默认值
BROWSER_TOOL_USE_VISION=false  # 强制启用视觉功能（默认 false，自动检测）
```

### 2. 获取百炼平台 API Key

1. 访问 [阿里云百炼控制台](https://bailian.console.aliyun.com/)
2. 创建 API Key
3. 将 API Key 添加到 `.env` 文件（使用 `BAILIAN_API_KEY`）

## 使用方式

### 自动检测（推荐）

Browser Tool 会自动检测任务是否需要视觉功能。如果任务描述中包含以下关键词，会自动使用 Qwen-VL：

- 中文：截图、图片、图像、视觉、识别、查看页面、页面内容、页面布局、页面元素、页面结构、页面样式、识别、分析页面、页面截图、视觉分析
- 英文：screenshot, image, visual, recognize, see, view

**示例：**
```python
# 自动使用 Qwen-VL（因为包含"截图"关键词）
tool.execute(task="打开网页并截图，告诉我页面内容")

# 自动使用 Qwen-VL（因为包含"视觉"关键词）
tool.execute(task="使用视觉分析页面布局")

# 使用 DeepSeek（普通任务）
tool.execute(task="打开 www.baidu.com")
```

### 强制启用视觉功能

设置环境变量 `BROWSER_TOOL_USE_VISION=true` 后，所有任务都会尝试使用 Qwen-VL（如果 `BAILIAN_API_KEY` 已设置）。

## 工作原理

1. **任务分析**: 检查任务描述中是否包含视觉相关关键词
2. **模型选择**: 
   - 如果需要视觉功能且 `BAILIAN_API_KEY` 已设置 → 使用 Qwen-VL（通过 `BROWSER_TOOL_VISION_MODEL` 配置）
   - 否则 → 使用 DeepSeek（默认）
3. **自动回退**: 如果 Qwen 不可用，自动回退到 DeepSeek

## 优势

1. **向后兼容**: 默认使用 DeepSeek，不影响现有功能
2. **自动选择**: 根据任务自动选择最合适的模型
3. **灵活配置**: 支持环境变量配置，易于部署
4. **错误处理**: 如果 Qwen 不可用，自动回退到 DeepSeek

## 注意事项

1. **API Key**: 需要同时配置 DeepSeek 和百炼平台的 API Key（`BAILIAN_API_KEY`）
2. **成本**: Qwen-VL 可能比 DeepSeek 更昂贵，需要权衡
3. **兼容性**: Qwen-VL 兼容 OpenAI API，与 browser-use 兼容
4. **性能**: 视觉模型可能响应更慢，需要合理设置超时时间
5. **模型选择**: 通过 `BROWSER_TOOL_VISION_MODEL` 配置视觉模型，支持 "平台-模型" 格式（如 `bailian-qwen-vl-max-2025-08-13`）

## 故障排查

### 问题 1: 百炼平台 API Key 未设置

**错误信息:**
```
WARNING [browser_tool] BAILIAN_API_KEY 未设置，无法使用视觉功能，回退到 DeepSeek
```

**解决方案:**
- 检查 `.env` 文件中是否设置了 `BAILIAN_API_KEY`
- 确保 API Key 格式正确

### 问题 2: 百炼平台 API Key 格式无效

**错误信息:**
```
WARNING [browser_tool] BAILIAN_API_KEY 格式无效，回退到 DeepSeek
```

**解决方案:**
- 检查 API Key 长度是否足够（至少 10 个字符）
- 确保 API Key 没有多余的空格

### 问题 3: 视觉功能未启用

**可能原因:**
1. 任务描述中不包含视觉相关关键词
2. `BROWSER_TOOL_USE_VISION` 未设置为 `true`

**解决方案:**
- 在任务描述中添加视觉相关关键词
- 或设置 `BROWSER_TOOL_USE_VISION=true`

## 测试

### 测试视觉功能检测

```python
tool = BrowserTool()

# 测试自动检测
needs_vision = tool._needs_vision("打开网页并截图")
print(f"需要视觉功能: {needs_vision}")  # 应该返回 True

needs_vision = tool._needs_vision("打开 www.baidu.com")
print(f"需要视觉功能: {needs_vision}")  # 应该返回 False
```

### 测试模型选择

```python
# 设置环境变量
import os
os.environ['BAILIAN_API_KEY'] = 'your_bailian_api_key'
os.environ['BROWSER_TOOL_VISION_MODEL'] = 'qwen-vl-max-2025-08-13'

# 测试视觉任务（应该使用 Qwen-VL）
result = tool.execute(task="打开网页并截图，分析页面布局")

# 测试普通任务（应该使用 DeepSeek）
result = tool.execute(task="打开 www.baidu.com")
```

## 相关文档

- [Browser-use 当前问题](./browser-use-current-issues.md)
- [Browser-use 执行问题分析](./browser-use-issues.md)
- [Browser Tool 设计文档](../design/browser-tool-qwen-vision-support.md)

