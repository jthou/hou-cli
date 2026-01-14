# 视频下载工具问题分析

## 问题 1: you-get RuntimeWarning

### 问题现象
```
RuntimeWarning: 'you_get.__main__' found in sys.modules after import of package 'you_get', 
but prior to execution of 'you_get.__main__'; this may result in unpredictable behaviour
```

### 根本原因分析

1. **模块导入冲突**：
   - 在 `YouGetDownloader.is_available()` 方法中（第 105-109 行），代码直接导入了 `you_get` 模块
   - 这会在当前 Python 进程中加载 `you_get` 模块到 `sys.modules`
   - 然后在 `download()` 方法中，虽然使用了 `subprocess.run()` 和 `python -m you_get`，但由于是在同一个 Python 进程中，`you_get` 模块已经在 `sys.modules` 中了
   - 当子进程尝试执行 `python -m you_get` 时，Python 发现 `you_get` 已经在 `sys.modules` 中，但 `you_get.__main__` 还没有执行，就会产生 RuntimeWarning

2. **执行流程**：
   ```
   1. _select_downloader() 调用 downloader.is_available()
   2. is_available() 导入 you_get 模块 → you_get 进入 sys.modules
   3. download() 方法执行 subprocess.run(['python', '-m', 'you_get'])
   4. 子进程启动，发现 you_get 已在 sys.modules 中，但 __main__ 未执行
   5. Python 发出 RuntimeWarning
   ```

### 解决方案

**方案 1：不在 is_available() 中导入模块**
- 改为通过检查文件存在性和运行测试命令来验证可用性
- 避免在检查阶段就导入模块

**方案 2：使用独立的 Python 进程**
- 在 subprocess.run() 中使用 `-S` 参数（不导入 site 模块）
- 或者使用 `-I` 参数（隔离模式）

**方案 3：清理 sys.modules**
- 在 download() 之前清理 you_get 相关的模块
- 但这可能影响其他功能

## 问题 2: yt-dlp HTTP 412 错误

### 问题现象
```
ERROR: [BiliBili] Unable to download webpage: HTTP Error 412: Precondition Failed
```

### 根本原因分析

1. **哔哩哔哩反爬虫机制**：
   - 哔哩哔哩使用了复杂的反爬虫机制，包括：
     - 请求头验证（User-Agent, Referer, Origin 等）
     - Cookie 验证（可能需要登录状态）
     - 时间戳验证
     - 签名验证
     - IP 频率限制

2. **当前代码的问题**：
   - 虽然添加了 headers，但可能不够完整
   - 缺少必要的 cookies
   - 可能需要更真实的浏览器指纹
   - yt-dlp 版本可能过旧，不支持最新的反爬虫机制

3. **yt-dlp 的 headers 设置**：
   - 代码中设置了 `http_headers`，但 yt-dlp 可能还需要其他配置
   - 可能需要设置 `cookiefile` 或 `cookiesfrombrowser`

### 解决方案

**方案 1：更新 yt-dlp 到最新版本**
- 最新版本通常包含最新的反爬虫绕过机制

**方案 2：添加 cookies 支持**
- 允许用户提供 cookies 文件
- 或者从浏览器中提取 cookies

**方案 3：使用更真实的浏览器指纹**
- 添加更多浏览器相关的 headers
- 使用真实的浏览器 User-Agent

**方案 4：降级到 you-get**
- you-get 对哔哩哔哩的支持可能更好
- 但需要先解决 you-get 的 RuntimeWarning 问题

## 推荐修复方案

### 优先级 1：修复 you-get RuntimeWarning
1. 修改 `is_available()` 方法，不导入模块，改为检查文件存在性
2. 或者使用 subprocess 运行测试命令来验证可用性

### 优先级 2：增强 yt-dlp 的哔哩哔哩支持
1. ✅ 更新 yt-dlp：源码位于 `backend/externals/yt-dlp`，使用 `git pull` 更新
2. ✅ 添加 cookies 支持（已完成）
3. ✅ 增强 headers 配置（已完成）
4. ✅ 添加重试机制（已完成）

### 优先级 3：改进错误处理和降级策略
1. 当 yt-dlp 失败时，自动尝试 you-get
2. 提供更清晰的错误信息
3. 记录详细的调试信息

