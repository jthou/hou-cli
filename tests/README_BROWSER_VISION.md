# Browser Tool 视觉模型测试指南

## 概述

本指南说明如何测试 Browser Tool 的视觉模型功能（Qwen-VL 系列）。

## 前置条件

### 1. 环境变量配置

在 `.env` 文件中配置以下环境变量：

```bash
# DeepSeek（必需，默认模型）
DEEPSEEK_API_KEY=your_deepseek_api_key

# 百炼平台（可选，用于视觉功能）
BAILIAN_API_KEY=your_bailian_api_key
BAILIAN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1  # 可选

# Browser Tool 视觉模型配置（可选）
BROWSER_TOOL_VISION_MODEL=qwen-vl-max-2025-08-13  # 默认值
BROWSER_TOOL_USE_VISION=false  # 是否强制启用视觉功能
```

### 2. 获取 API Key

- **DeepSeek API Key**: 访问 [DeepSeek 官网](https://www.deepseek.com/) 获取
- **百炼平台 API Key**: 访问 [阿里云百炼控制台](https://bailian.console.aliyun.com/) 获取

## 测试方法

### 方法 1: 简单测试脚本（推荐）

运行简单的测试脚本，快速验证配置和功能：

```bash
python tests/test_browser_vision_simple.py
```

**测试内容**：
1. ✅ 视觉功能自动检测（关键词匹配）
2. ✅ LLM 创建（DeepSeek 和 Qwen-VL）
3. ⏭️ 浏览器任务执行（可选，需要设置 `TEST_BROWSER_VISION=true`）

**执行实际浏览器测试**：
```bash
TEST_BROWSER_VISION=true python tests/test_browser_vision_simple.py
```

### 方法 2: 完整测试脚本

运行完整的测试脚本，包含更多测试用例：

```bash
python tests/test_browser_qwen_vision.py
```

**执行实际浏览器测试**：
```bash
TEST_BROWSER_QWEN=true python tests/test_browser_qwen_vision.py
```

### 方法 3: 手动测试

在 Python 交互式环境中手动测试：

```python
import os
import asyncio
from backend.core.agent.tools.builtin.browser_tool import BrowserTool

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 创建工具实例
tool = BrowserTool()

# 测试 1: 视觉功能检测
task1 = "打开网页并截图"
needs_vision1 = tool._needs_vision(task1)
print(f"任务: {task1}")
print(f"需要视觉功能: {needs_vision1}")

# 测试 2: LLM 创建
llm_vision = tool._create_llm(use_vision=True)
print(f"视觉模型: {llm_vision.model}")

llm_normal = tool._create_llm(use_vision=False)
print(f"默认模型: {llm_normal.model}")

# 测试 3: 执行浏览器任务（可选）
async def test_task():
    result = await tool._execute_async(
        task="打开 www.baidu.com 并查看页面内容",
        headless=False,
        timeout=60
    )
    print(f"执行结果: {result.success}")

# asyncio.run(test_task())
```

## 测试用例

### 1. 视觉功能自动检测

以下任务会自动使用视觉模型（包含视觉关键词）：

- ✅ "打开网页并截图，告诉我页面内容"
- ✅ "使用视觉分析页面布局"
- ✅ "打开 www.baidu.com 并识别页面元素"
- ✅ "访问 example.com 并查看页面"
- ✅ "screenshot and analyze"

以下任务不会使用视觉模型（简单导航）：

- ❌ "打开 www.baidu.com"
- ❌ "navigate to example.com"

### 2. 强制启用视觉功能

设置环境变量 `BROWSER_TOOL_USE_VISION=true` 后，所有任务都会使用视觉模型。

### 3. 模型选择

- **DeepSeek**：普通任务（无视觉关键词）
- **Qwen-VL**：视觉任务（包含视觉关键词或强制启用）

## 预期结果

### 成功标志

1. ✅ 配置检查通过
2. ✅ 视觉检测功能正常
3. ✅ LLM 创建成功（DeepSeek 和 Qwen-VL）
4. ✅ 浏览器任务执行成功（如果执行实际测试）

### 日志输出

成功时会看到以下日志：

```
使用视觉模型: qwen-vl-max-2025-08-13
视觉模型配置: provider=bailian, base_url=https://dashscope.aliyuncs.com/compatible-mode/v1
检测到视觉关键词 '查看页面'，启用视觉功能
```

## 故障排查

### 问题 1: BAILIAN_API_KEY 未设置

**错误信息**：
```
⚠️  BAILIAN_API_KEY 未设置，视觉功能将不可用
```

**解决方案**：
- 检查 `.env` 文件中是否设置了 `BAILIAN_API_KEY`
- 确保 API Key 格式正确

### 问题 2: 视觉模型创建失败

**错误信息**：
```
❌ 视觉模型 LLM 创建失败: ...
```

**解决方案**：
- 检查 `BAILIAN_API_KEY` 是否有效
- 检查 `BROWSER_TOOL_VISION_MODEL` 配置的模型名称是否正确
- 检查网络连接是否正常

### 问题 3: 视觉功能未启用

**可能原因**：
1. 任务描述中不包含视觉相关关键词
2. `BROWSER_TOOL_USE_VISION` 未设置为 `true`

**解决方案**：
- 在任务描述中添加视觉相关关键词（如"截图"、"查看页面"等）
- 或设置 `BROWSER_TOOL_USE_VISION=true`

## 相关文档

- [Browser Tool 设计文档](../../docs/design/browser-tool-model-selection.md)
- [Browser Tool 故障排查](../../docs/troubleshooting/browser-use-qwen-vision-support.md)
- [环境变量配置](../../env.example)

