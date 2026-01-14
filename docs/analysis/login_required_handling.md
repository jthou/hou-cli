# 登录要求错误处理指南

## 问题描述

当下载某些平台的视频时（如 YouTube、Bilibili），可能会遇到登录要求错误：

```
LOGIN_REQUIRED: 請登入以確認你並非機械人 這有助保護我們的社群。
```

这通常是因为：
1. 平台的反爬虫机制要求验证用户身份
2. 需要登录才能访问某些视频
3. 平台检测到自动化访问，要求人工验证

## 解决方案

### 方案 1：使用 Cookies（推荐）

Cookies 可以让下载工具模拟已登录的浏览器会话。

#### 1.1 从浏览器提取 Cookies（最简单）

```python
# 使用 Chrome 浏览器的 cookies
video_downloader.execute(
    url="https://www.youtube.com/watch?v=...",
    cookies_from_browser="chrome"
)

# 支持其他浏览器
# cookies_from_browser="firefox"  # Firefox
# cookies_from_browser="safari"    # Safari
# cookies_from_browser="edge"      # Edge
```

**前提条件**：
- 已安装 `browser-cookie3`（已包含在 requirements.txt 中）
- 浏览器中已登录相应平台

#### 1.2 使用 Cookies 文件

```python
# 使用导出的 cookies 文件
video_downloader.execute(
    url="https://www.youtube.com/watch?v=...",
    cookies_file="/path/to/cookies.txt"
)
```

**如何导出 Cookies**：
1. 使用浏览器扩展（如 "Get cookies.txt LOCALLY"）
2. 使用开发者工具手动导出
3. 使用 `browser-cookie3` 命令行工具

### 方案 2：使用 yt-dlp（对 Cookies 支持更好）

yt-dlp 对 cookies 的支持通常比 you-get 更好：

```python
video_downloader.execute(
    url="https://www.youtube.com/watch?v=...",
    preferred_tool="yt-dlp",
    cookies_from_browser="chrome"
)
```

### 方案 3：手动登录后提取 Cookies

1. 在浏览器中登录相应平台（如 YouTube）
2. 保持浏览器打开（不要关闭）
3. 使用 `cookies_from_browser` 参数提取 cookies
4. 下载工具会使用这些 cookies 模拟登录状态

## 错误处理改进

### you-get 错误处理

- ✅ 自动过滤 RuntimeWarning（不影响功能）
- ✅ 识别 LOGIN_REQUIRED 错误并提供针对性建议
- ✅ 提供详细的解决方案说明

### yt-dlp 错误处理

- ✅ 识别 LOGIN_REQUIRED 错误
- ✅ 提供 cookies 使用建议
- ✅ 提供工具切换建议

## 常见问题

### Q: RuntimeWarning 会影响下载吗？

A: 不会。RuntimeWarning 只是警告，不影响功能。代码已自动过滤这些警告。

### Q: 为什么需要登录？

A: 平台的反爬虫机制要求验证用户身份，防止自动化访问。

### Q: Cookies 安全吗？

A: Cookies 包含登录信息，请妥善保管：
- 不要将 cookies 文件提交到版本控制
- 不要分享 cookies 文件
- 定期更新 cookies（登录状态可能过期）

### Q: 如何知道 Cookies 是否有效？

A: 如果下载成功，说明 cookies 有效。如果仍然失败，可能需要：
- 重新登录浏览器
- 更新 cookies
- 检查视频是否需要特殊权限

## 最佳实践

1. **优先使用浏览器 Cookies**：
   - 最简单、最可靠
   - 自动保持登录状态

2. **使用 yt-dlp**：
   - 对 cookies 支持更好
   - 功能更强大

3. **定期更新 Cookies**：
   - 登录状态可能过期
   - 重新登录后提取新的 cookies

4. **错误处理**：
   - 如果遇到 LOGIN_REQUIRED 错误，自动使用 cookies
   - 如果 cookies 无效，提示用户重新登录

## 代码示例

```python
# 完整的下载示例（带 cookies）
from backend.core.agent.tools.builtin.video_downloader_tool import VideoDownloaderTool

tool = VideoDownloaderTool()

# 使用浏览器 cookies 下载 YouTube 视频
result = tool.execute(
    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    output_dir="/path/to/downloads",
    cookies_from_browser="chrome",
    preferred_tool="yt-dlp"
)

if result.success:
    print(f"下载成功: {result.data}")
else:
    print(f"下载失败: {result.error}")
```

