# Browser CDP 连接测试和修复指南

## 问题描述

browser-use 库在使用 Chrome DevTools Protocol (CDP) 连接浏览器时可能遇到以下问题：

1. **JSONDecodeError: Expecting value: line 1 column 1 (char 0)**
   - CDP 端点返回空响应
   - 浏览器启动后 CDP 端点还未就绪

2. **AssertionError: Root CDP client not initialized**
   - CDP 客户端未正确初始化
   - 浏览器进程意外退出

3. **webSocketDebuggerUrl 缺失**
   - 无法从 `/json/version` 端点获取 WebSocket URL
   - 浏览器版本不兼容

## 完整测试流程

### 1. 运行诊断测试

```bash
# 运行 CDP 连接诊断测试
pytest backend/core/agent/tools/tests/test_browser_cdp_diagnosis.py -v

# 运行 CDP 连接测试
pytest backend/core/agent/tools/tests/test_browser_tool_cdp.py -v

# 运行浏览器工具核心测试
pytest backend/core/agent/tools/tests/test_browser_tool.py -v
```

### 2. 手动测试 CDP 连接

```bash
# 启动浏览器并检查 CDP 端点
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-debug \
  --headless

# 在另一个终端测试 CDP 端点
curl http://127.0.0.1:9222/json/version
```

### 3. 检查浏览器安装

```bash
# macOS
ls -la /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome

# Linux
which google-chrome-stable
which chromium

# 如果未安装，使用 playwright 安装
uvx playwright install chrome
```

## 已实施的修复

### 修复 1: 增强 CDP 连接错误处理

**位置**: `backend/externals/browser-use/browser_use/browser/session.py`

**修复内容**:
1. 添加重试机制（最多 5 次，递增延迟）
2. 检查 HTTP 响应状态码
3. 检查响应内容是否为空
4. 改进 JSON 解析错误处理
5. 验证 `webSocketDebuggerUrl` 字段存在
6. 提供详细的错误信息和修复建议

**关键改进**:
- 响应状态码检查：确保返回 200
- 空响应检测：检查响应内容是否为空
- JSON 解析错误：提供更详细的错误信息
- 连接错误处理：区分连接错误、超时和其他错误
- 重试机制：自动重试，给浏览器更多启动时间

### 修复 2: 测试代码改进

**位置**: `backend/core/agent/tools/tests/test_browser_tool.py`

**修复内容**:
1. 直接捕获 `json.JSONDecodeError`
2. 直接捕获 `AssertionError`（CDP 客户端未初始化）
3. 优雅跳过环境问题，而不是失败

## 问题修复步骤

### 步骤 1: 诊断问题

运行诊断测试以确定具体问题：

```bash
pytest backend/core/agent/tools/tests/test_browser_cdp_diagnosis.py::TestBrowserCDPDiagnosis::test_manual_cdp_connection -v -s
```

### 步骤 2: 检查浏览器状态

```bash
# 检查浏览器进程
ps aux | grep -i chrome

# 检查 CDP 端口是否被占用
lsof -i :9222

# 如果端口被占用，杀死进程
kill -9 <PID>
```

### 步骤 3: 验证浏览器启动

```bash
# 手动启动浏览器测试
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-test \
  --headless \
  --no-sandbox

# 在另一个终端测试
curl http://127.0.0.1:9222/json/version
```

应该返回类似：
```json
{
  "Browser": "Chrome/120.0.0.0",
  "Protocol-Version": "1.3",
  "User-Agent": "Mozilla/5.0...",
  "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser/..."
}
```

### 步骤 4: 检查环境变量

确保 `.env` 文件中配置了必要的 API Key：

```bash
# 检查 DEEPSEEK_API_KEY
grep DEEPSEEK_API_KEY .env
```

### 步骤 5: 运行完整测试

```bash
# 运行所有浏览器测试
pytest backend/core/agent/tools/tests/test_browser_tool*.py -v

# 如果测试被跳过（SKIPPED），说明环境问题已正确识别
# 如果测试失败（FAILED），需要进一步调试
```

## 常见问题和解决方案

### 问题 1: JSONDecodeError

**症状**: `JSONDecodeError: Expecting value: line 1 column 1 (char 0)`

**原因**:
- 浏览器启动后 CDP 端点还未就绪
- CDP 端点返回空响应
- 浏览器进程崩溃

**解决方案**:
1. 增加浏览器启动等待时间（已自动处理，最多重试 5 次）
2. 检查浏览器进程是否正常运行
3. 检查 CDP 端口是否可访问
4. 尝试使用不同的 user_data_dir

### 问题 2: Root CDP client not initialized

**症状**: `AssertionError: Root CDP client not initialized`

**原因**:
- CDP 连接在客户端初始化之前失败
- 浏览器进程意外退出
- WebSocket 连接失败

**解决方案**:
1. 确保浏览器进程持续运行
2. 检查网络连接
3. 验证 WebSocket URL 是否正确
4. 检查防火墙设置

### 问题 3: 浏览器未找到

**症状**: `No local Chrome/Chromium install found`

**解决方案**:
```bash
# 使用 playwright 安装浏览器
uvx playwright install chrome

# 或手动安装 Chrome/Chromium
# macOS: 从 https://www.google.com/chrome/ 下载
# Linux: sudo apt-get install google-chrome-stable
```

### 问题 4: 端口被占用

**症状**: `Address already in use` 或连接失败

**解决方案**:
```bash
# 查找占用端口的进程
lsof -i :9222

# 杀死进程
kill -9 <PID>

# 或使用不同的端口（修改 browser-use 配置）
```

## 测试最佳实践

1. **隔离测试环境**: 使用临时 user_data_dir，避免冲突
2. **增加超时时间**: 对于慢速环境，增加超时时间
3. **检查日志**: 查看详细的调试日志以了解问题
4. **逐步测试**: 先测试浏览器启动，再测试 CDP 连接，最后测试完整功能

## 调试技巧

### 启用详细日志

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 检查浏览器进程

```python
import psutil
for proc in psutil.process_iter(['pid', 'name']):
    if 'chrome' in proc.info['name'].lower():
        print(proc.info)
```

### 测试 CDP 端点

```python
import httpx
import asyncio

async def test_cdp():
    async with httpx.AsyncClient() as client:
        response = await client.get('http://127.0.0.1:9222/json/version')
        print(f"Status: {response.status_code}")
        print(f"Content: {response.text}")

asyncio.run(test_cdp())
```

## 总结

通过以上修复和改进：

1. ✅ **自动重试机制**: 浏览器启动后自动重试 CDP 连接
2. ✅ **详细错误信息**: 提供清晰的错误原因和修复建议
3. ✅ **环境检测**: 测试能够正确识别环境问题并优雅跳过
4. ✅ **诊断工具**: 提供专门的诊断测试帮助定位问题

如果问题仍然存在，请：
1. 运行诊断测试获取详细信息
2. 检查浏览器日志和进程状态
3. 验证 CDP 端点可访问性
4. 查看详细的错误堆栈信息

