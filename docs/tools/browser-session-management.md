# Browser 工具会话管理指南

## 概述

Browser 工具支持通过 `user_data_dir` 参数保存和复用浏览器会话，包括登录状态、cookies、浏览器设置等。这使得可以操控需要登录的网站（如知乎、GitHub、微博等）。

## 核心功能

### 会话持久化

通过 `user_data_dir` 参数，可以：
- ✅ 保存登录状态和 cookies
- ✅ 复用已登录的浏览器会话
- ✅ 保持浏览器设置和偏好
- ✅ 支持多站点独立会话（每个站点使用不同的目录）

## 使用场景

### 场景1：首次登录并保存会话

**步骤：**
1. 第一次使用时，指定 `user_data_dir` 参数
2. 在任务描述中明确要求登录
3. 登录后，会话会自动保存到指定目录

**示例：**
```
用户：打开知乎并登录，然后搜索"Python教程"
```

AI 会调用：
```python
browser(
    task="打开 https://www.zhihu.com，登录账号，然后搜索'Python教程'",
    user_data_dir="~/.browser-profiles/zhihu",
    headless=False  # 可视化模式，方便观察登录过程
)
```

### 场景2：复用已登录的会话

**步骤：**
1. 使用相同的 `user_data_dir` 参数
2. 浏览器会自动加载之前保存的登录状态

**示例：**
```
用户：在知乎上搜索"机器学习"
```

AI 会调用：
```python
browser(
    task="在知乎上搜索'机器学习'",
    user_data_dir="zhihu"  # 复用之前的登录状态（自动使用项目配置目录）
)
```

### 场景3：多站点独立会话

**步骤：**
为每个站点使用不同的 `user_data_dir`

**示例：**
```python
# 知乎会话（使用站点名称，自动使用项目配置目录）
browser(task="...", user_data_dir="zhihu")

# GitHub 会话
browser(task="...", user_data_dir="github")

# 微博会话
browser(task="...", user_data_dir="weibo")
```

## 工具参数

### `user_data_dir`（可选）

**说明：** 浏览器用户数据目录路径

**用途：**
- 保存登录状态和 cookies
- 保存浏览器设置和偏好
- 复用已登录的会话

**示例值：**
- `zhihu` - 站点名称（推荐），会自动使用项目配置目录
- `github` - 站点名称（推荐），会自动使用项目配置目录
- `~/Library/Application Support/hou-cli/browser-profiles/zhihu` - 完整路径（macOS）
- `~/.local/share/hou-cli/browser-profiles/zhihu` - 完整路径（Linux）
- `/tmp/browser-session-123` - 临时会话（完整路径）

**推荐方式：**
- **使用站点名称**（如 `zhihu`、`github`）：工具会自动使用项目配置目录
  - macOS: `~/Library/Application Support/hou-cli/browser-profiles/{site_name}`
  - Linux: `~/.local/share/hou-cli/browser-profiles/{site_name}`
  - Windows: `%LOCALAPPDATA%\hou-cli\browser-profiles\{site_name}`

**注意：**
- 如果目录不存在，会自动创建
- 使用站点名称更简洁，且跨平台兼容
- 不同站点建议使用不同站点名称

### `keep_alive`（可选）

**说明：** 是否保持浏览器会话存活

**用途：**
- `True`: 任务完成后保持浏览器打开，支持链式任务
- `False`: 任务完成后关闭浏览器（默认）

**使用场景：**
- 需要多次操作同一网站时，使用 `keep_alive=True`
- 单次任务完成后，使用 `keep_alive=False`

### `headless`（可选）

**说明：** 是否使用无头模式

**建议：**
- 首次登录：使用 `headless=False`（可视化模式），方便观察和手动处理验证码
- 已登录会话：可以使用 `headless=True`（无头模式），提高速度

## 完整使用示例

### 示例1：知乎搜索（需要登录）

**第一次使用（需要登录）：**
```
用户：打开知乎，登录我的账号，然后搜索"Python教程"
```

AI 调用：
```python
browser(
    task="打开 https://www.zhihu.com，登录账号（如果需要），然后搜索'Python教程'",
    user_data_dir="zhihu",  # 使用站点名称
    headless=False  # 可视化模式，方便登录
)
```

**后续使用（已登录）：**
```
用户：在知乎上搜索"机器学习"
```

AI 调用：
```python
browser(
    task="在知乎上搜索'机器学习'",
    user_data_dir="zhihu"  # 自动使用已保存的登录状态
)
```

### 示例2：访问需要登录的页面

```
用户：访问 https://zhida.zhihu.com/search/3707579171380201696 并获取内容
```

AI 调用：
```python
browser(
    task="访问 https://zhida.zhihu.com/search/3707579171380201696 并提取页面内容",
    user_data_dir="zhihu",  # 使用站点名称，自动使用项目配置目录
    headless=False
)
```

如果已经登录，浏览器会自动使用保存的 cookies，无需再次登录。

## 工作原理

### 会话保存机制

1. **首次使用**：
   - 创建新的浏览器实例
   - 使用指定的 `user_data_dir`
   - 浏览器会在此目录保存所有数据（cookies、localStorage、sessionStorage等）
   - 登录后，登录状态自动保存

2. **后续使用**：
   - 使用相同的 `user_data_dir`
   - 浏览器自动加载之前保存的数据
   - 登录状态自动恢复，无需重新登录

### 数据存储位置

`user_data_dir` 目录中会保存：
- `Cookies` - 网站 cookies（包括登录 token）
- `Local Storage` - 本地存储数据
- `Session Storage` - 会话存储数据
- `Preferences` - 浏览器偏好设置
- `History` - 浏览历史（可选）

## 最佳实践

### 1. 目录命名规范

**推荐：使用站点名称（自动使用项目配置目录）**
```
zhihu          # 知乎 → 自动使用 ~/.local/share/hou-cli/browser-profiles/zhihu
github         # GitHub → 自动使用 ~/.local/share/hou-cli/browser-profiles/github
weibo          # 微博 → 自动使用 ~/.local/share/hou-cli/browser-profiles/weibo
```

**或使用完整路径（如果需要自定义位置）**
```
~/Library/Application Support/hou-cli/browser-profiles/zhihu  # macOS
~/.local/share/hou-cli/browser-profiles/zhihu                 # Linux
%LOCALAPPDATA%\hou-cli\browser-profiles\zhihu                 # Windows
```

### 2. 首次登录流程

1. **使用可视化模式**（`headless=False`）
   - 方便观察登录过程
   - 可以手动处理验证码
   - 确认登录成功

2. **明确登录要求**
   - 在任务描述中包含"登录"关键词
   - 提供账号信息（如果需要）

3. **验证登录状态**
   - 登录后，可以执行一个简单操作验证
   - 确认 cookies 已保存

### 3. 会话复用

1. **使用相同的 user_data_dir**
   - 确保每次使用相同的目录路径
   - 可以使用环境变量或配置文件管理

2. **定期检查登录状态**
   - 如果登录过期，需要重新登录
   - 可以设置任务超时时间

### 4. 安全考虑

1. **保护用户数据目录**
   - 设置适当的文件权限
   - 不要将目录提交到版本控制

2. **清理临时会话**
   - 任务完成后，可以删除临时目录
   - 长期会话建议定期备份

## 故障排查

### 问题1：登录状态未保存

**症状：** 每次都需要重新登录

**解决方案：**
1. 检查 `user_data_dir` 是否正确设置
2. 确认目录有写入权限
3. 检查浏览器是否正常关闭（异常退出可能不会保存）

### 问题2：登录状态过期

**症状：** 使用已保存的会话，但仍提示需要登录

**解决方案：**
1. 登录 token 可能已过期，需要重新登录
2. 网站可能更新了登录机制
3. 可以删除旧的用户数据目录，重新登录

### 问题3：多任务冲突

**症状：** 同时运行多个任务时，会话冲突

**解决方案：**
1. 每个任务使用独立的 `user_data_dir`
2. 或使用 `keep_alive=True` 保持会话，避免重复启动浏览器

## 技术细节

### Browser-use 支持的功能

根据 browser-use 的 API，支持以下会话管理功能：

- ✅ `user_data_dir` - 用户数据目录
- ✅ `profile_directory` - 配置文件目录
- ✅ `storage_state` - 存储状态（cookies、localStorage等）
- ✅ `keep_alive` - 保持浏览器存活
- ✅ `cookie_whitelist_domains` - Cookie 白名单域名

### 与 Playwright 的关系

browser-use 基于 Playwright，因此：
- 完全兼容 Playwright 的会话管理功能
- 支持所有 Playwright 的浏览器配置选项
- 可以手动导出和导入 cookies（如果需要）

## 参考链接

- Browser-use 文档：https://docs.browser-use.com/
- Playwright 会话管理：https://playwright.dev/python/docs/auth

