# 浏览器工具设置指南

## 快速开始

### 1. 安装依赖

```bash
# 安装 Python 包
pip install browser-use langchain-openai playwright

# 安装浏览器驱动（必需）
playwright install chromium
```

或者使用项目的开发依赖（推荐）：

```bash
# 安装开发依赖（包含 browser-use）
pip install -r requirements.txt

# 安装浏览器驱动（必需）
playwright install chromium
```

**注意**：`browser-use` 需要较新的 LangChain 版本（>=0.3.25），这些依赖在 `requirements.txt` 中已配置。

### 2. 配置环境变量

确保 `.env` 文件中已配置：

```bash
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_MODEL=deepseek-chat  # 可选，默认 deepseek-chat
```

### 3. 验证安装

启动系统后，浏览器工具会自动注册（即使依赖未安装也会注册）。

**如果依赖已安装**，你会看到：
```
Browser tool registered successfully
```

**如果依赖未安装**，工具仍会注册，但执行时会提示：
```
browser-use is not installed. 
Please install it with: pip install browser-use && playwright install chromium
```

**验证方法**：
- 工具列表中应该包含 `browser` 工具（共 8 个工具）
- 尝试执行浏览器任务，如果依赖已安装会正常工作，否则会提示安装

## 使用示例

### 示例 1: 简单搜索

用户输入：
```
帮我搜索一下 Python 教程
```

系统会自动调用浏览器工具执行搜索任务。

### 示例 2: 复杂任务

用户输入：
```
在 GitHub 上找一些 Python 项目，按 stars 排序，告诉我前 5 个
```

系统会：
1. 打开浏览器
2. 导航到 GitHub
3. 搜索 Python 项目
4. 按 stars 排序
5. 提取前 5 个项目信息
6. 返回结果

### 示例 3: 数据提取

用户输入：
```
访问 https://example.com 并提取页面标题和主要内容
```

## 工具参数

浏览器工具支持以下参数：

- **task** (必需): 要执行的浏览器任务，用自然语言描述
- **headless** (可选): 是否使用无头模式，默认 `false`（显示浏览器窗口）
- **instructions** (可选): 详细的操作步骤列表
- **timeout** (可选): 任务超时时间（秒），默认 60，最大 300

## 配置选项

### 浏览器配置

可以在 `browser_tool.py` 中自定义浏览器配置：

```python
browser_config = {
    "headless": False,  # 显示浏览器窗口
    "viewport": {"width": 1920, "height": 1080},  # 视口大小
    "timeout": 30000,  # 超时时间（毫秒）
    "save_conversation_path": "./data/browser_conversations"  # 对话保存路径
}
```

### 对话保存

浏览器工具的对话记录会保存在 `data/browser_conversations/` 目录下，便于调试和问题排查。

## 故障排查

### 问题 1: ImportError: browser-use not installed

**解决方案：**
```bash
pip install browser-use
playwright install chromium
```

### 问题 2: 浏览器启动失败

**解决方案：**
```bash
# 重新安装浏览器驱动
playwright install --force chromium

# 检查系统权限
# macOS: 确保 Terminal 有辅助功能权限
# Linux: 可能需要安装额外的系统依赖
```

### 问题 3: API Key 错误

**解决方案：**
- 检查 `.env` 文件中的 `DEEPSEEK_API_KEY` 是否正确设置
- 确保 API Key 有效且有足够的额度

### 问题 4: 任务执行超时

**解决方案：**
- 增加超时时间（通过 `timeout` 参数）
- 简化任务描述
- 检查网络连接

### 问题 5: 浏览器窗口不显示

**解决方案：**
- 确保 `headless` 参数设置为 `false`
- 检查是否有其他浏览器实例在运行
- 尝试重启系统

## 性能优化

### 1. 使用无头模式

对于不需要观察执行过程的任务，可以设置 `headless: true` 以提高性能。

### 2. 合理设置超时时间

根据任务复杂度设置合适的超时时间，避免过长等待。

### 3. 任务描述优化

- 描述要清晰具体
- 避免过于复杂的多步骤任务
- 分步骤执行复杂任务

## 安全注意事项

1. **权限控制**: 浏览器工具可以访问任意网站，需要适当的权限控制
2. **资源限制**: 浏览器实例占用内存较大，注意资源管理
3. **网络安全**: 避免访问不安全的网站或执行恶意操作

## 下一步

- ✅ 工具已实现并注册
- ⏳ 测试基本功能
- ⏳ 优化错误处理
- ⏳ 添加单元测试
- ⏳ 性能优化

## 相关文档

- [浏览器自动化方案对比](docs/design/browser-automation-solutions.md)
- [Browser-use 集成指南](docs/design/browser-use-integration-guide.md)
- [完整集成方案](docs/design/browser-use-integration.md)

