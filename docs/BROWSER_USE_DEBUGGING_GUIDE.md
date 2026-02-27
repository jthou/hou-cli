# Browser-Use 集成调试指南

browser-use 现通过 **pip 安装**（`pip install browser-use`），源码位于当前环境的 `site-packages/browser_use/`。若需在源码中下断点，可在该目录或使用 `pip install -e <clone_path>` 从本地 clone 安装。

## 📁 源码位置（pip 安装后或本地 clone）

```
site-packages/browser_use/  或  <clone>/browser_use/
├── browser/
│   ├── session.py          # 浏览器会话管理（CDP 连接在这里）
│   ├── watchdogs/
│   │   └── local_browser_watchdog.py  # 本地浏览器启动
│   └── ...
```

## 🔧 调试方法

### 方法 1: 使用 Python 调试器 (pdb)

在 browser-use 源码中添加断点：

```python
# browser_use/browser/session.py
# 在 connect() 方法中添加断点

async def connect(self, cdp_url: str | None = None) -> None:
    import pdb; pdb.set_trace()  # 添加断点
    
    if not self.cdp_url.startswith('ws'):
        # ... 现有代码
```

运行测试时会自动进入调试器：

```bash
pytest backend/core/agent/tools/tests/test_browser_tool.py::TestBrowserTool::test_execute_simple_task -v -s
```

### 方法 2: 使用 IDE 调试器（推荐）

#### VS Code / Cursor

1. **创建调试配置** (`.vscode/launch.json`):

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Debug Browser Tool Test",
            "type": "debugpy",
            "request": "launch",
            "program": "${workspaceFolder}/venv/bin/pytest",
            "args": [
                "backend/core/agent/tools/tests/test_browser_tool.py::TestBrowserTool::test_execute_simple_task",
                "-v",
                "-s"
            ],
            "console": "integratedTerminal",
            "justMyCode": false,  // 重要：允许调试外部库代码
            "python": "${workspaceFolder}/venv/bin/python",
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        },
        {
            "name": "Python: Debug CDP Connection",
            "type": "debugpy",
            "request": "launch",
            "program": "${workspaceFolder}/venv/bin/pytest",
            "args": [
                "backend/core/agent/tools/tests/test_browser_cdp_diagnosis.py::TestBrowserCDPDiagnosis::test_manual_cdp_connection",
                "-v",
                "-s"
            ],
            "console": "integratedTerminal",
            "justMyCode": false,
            "python": "${workspaceFolder}/venv/bin/python",
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        }
    ]
}
```

2. **设置断点**:
   - 在 `browser_use/browser/session.py` 的 `connect()` 方法中设置断点
   - 在 `browser_use/browser/watchdogs/local_browser_watchdog.py` 的 `_launch_browser()` 方法中设置断点

3. **开始调试**:
   - 按 `F5` 或点击"开始调试"
   - 选择 "Python: Debug Browser Tool Test" 或 "Python: Debug CDP Connection"

#### PyCharm

1. **创建运行配置**:
   - Run → Edit Configurations
   - 添加 Python tests → pytest
   - Script path: `backend/core/agent/tools/tests/test_browser_tool.py`
   - Pattern: `test_execute_simple_task`
   - Working directory: 项目根目录

2. **设置断点**:
   - 在 browser-use 源码中直接点击行号设置断点

3. **开始调试**:
   - 点击调试按钮（绿色虫子图标）

### 方法 3: 使用日志调试

在 browser-use 源码中添加详细日志：

```python
# browser_use/browser/session.py

async def connect(self, cdp_url: str | None = None) -> None:
    self.logger.debug(f'🔍 [DEBUG] connect() called with cdp_url={cdp_url}')
    self.logger.debug(f'🔍 [DEBUG] self.cdp_url={self.cdp_url}')
    
    if not self.cdp_url.startswith('ws'):
        # ... 现有代码
        self.logger.debug(f'🔍 [DEBUG] Fetching CDP URL from: {url}')
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            version_info = await client.get(url, headers=headers)
            self.logger.debug(f'🔍 [DEBUG] Response status: {version_info.status_code}')
            self.logger.debug(f'🔍 [DEBUG] Response text: {version_info.text[:500]}')
```

运行测试时查看日志：

```bash
pytest backend/core/agent/tools/tests/test_browser_tool.py -v -s --log-cli-level=DEBUG
```

## 🎯 关键调试位置

### 1. CDP 连接问题

**文件**: `browser_use/browser/session.py`

**关键方法**:
- `connect()` (约 1507 行) - CDP 连接逻辑
- `on_BrowserStartEvent()` (约 604 行) - 浏览器启动事件处理

**调试点**:
```python
# 在 connect() 方法中
async def connect(self, cdp_url: str | None = None) -> None:
    # 设置断点在这里
    if not self.cdp_url.startswith('ws'):
        # 检查 CDP URL 获取逻辑
        version_info = await client.get(url, headers=headers)
        # 检查响应内容
        self.browser_profile.cdp_url = version_data['webSocketDebuggerUrl']
```

### 2. 浏览器启动问题

**文件**: `browser_use/browser/watchdogs/local_browser_watchdog.py`

**关键方法**:
- `_launch_browser()` (约 91 行) - 启动浏览器进程
- `_wait_for_cdp_url()` (约 372 行) - 等待 CDP 端点就绪

**调试点**:
```python
# 在 _launch_browser() 方法中
async def _launch_browser(self, max_retries: int = 3):
    # 检查浏览器路径
    browser_path = self._find_installed_browser_path()
    
    # 检查启动参数
    subprocess = await asyncio.create_subprocess_exec(
        browser_path,
        *launch_args,
        # ...
    )
    
    # 检查 CDP URL 获取
    cdp_url = await self._wait_for_cdp_url(debug_port)
```

### 3. CDP URL 获取问题

**文件**: `browser_use/browser/watchdogs/local_browser_watchdog.py`

**调试点**:
```python
# 在 _wait_for_cdp_url() 方法中
@staticmethod
async def _wait_for_cdp_url(port: int, timeout: float = 30) -> str:
    # 检查 CDP 端点响应
    async with aiohttp.ClientSession() as session:
        async with session.get(f'http://127.0.0.1:{port}/json/version') as resp:
            if resp.status == 200:
                # 检查响应内容
                return f'http://127.0.0.1:{port}/'
```

## 🔍 调试技巧

### 1. 检查浏览器进程

在调试过程中，可以检查浏览器进程状态：

```python
# 在断点处执行
import psutil
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    if 'chrome' in proc.info['name'].lower() or 'chromium' in proc.info['name'].lower():
        print(f"Browser process: {proc.info}")
```

### 2. 检查 CDP 端点

```python
# 在断点处执行
import httpx
import asyncio

async def check_cdp():
    async with httpx.AsyncClient() as client:
        response = await client.get('http://127.0.0.1:9222/json/version')
        print(f"Status: {response.status_code}")
        print(f"Content: {response.text}")

asyncio.run(check_cdp())
```

### 3. 检查环境变量

```python
# 在断点处执行
import os
print(f"DEEPSEEK_API_KEY: {os.getenv('DEEPSEEK_API_KEY', 'NOT SET')[:20]}...")
```

### 4. 检查浏览器配置

```python
# 在断点处执行
print(f"Browser profile: {self.browser_profile}")
print(f"CDP URL: {self.cdp_url}")
print(f"Is local: {self.is_local}")
```

## 📝 调试示例

### 示例 1: 调试 CDP 连接失败

```python
# 在 browser_use/browser/session.py
# connect() 方法中添加调试代码

async def connect(self, cdp_url: str | None = None) -> None:
    import pdb; pdb.set_trace()  # 断点
    
    if not self.cdp_url.startswith('ws'):
        # ... 现有代码
        
        # 添加详细日志
        self.logger.debug(f'🔍 [DEBUG] CDP URL: {url}')
        self.logger.debug(f'🔍 [DEBUG] Headers: {headers}')
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                version_info = await client.get(url, headers=headers)
                self.logger.debug(f'🔍 [DEBUG] Response: {version_info.status_code}')
                self.logger.debug(f'🔍 [DEBUG] Content: {version_info.text[:500]}')
            except Exception as e:
                self.logger.error(f'🔍 [DEBUG] Error: {e}', exc_info=True)
                raise
```

### 示例 2: 调试浏览器启动

```python
# 在 browser_use/browser/watchdogs/local_browser_watchdog.py
# _launch_browser() 方法中添加调试代码

async def _launch_browser(self, max_retries: int = 3):
    import pdb; pdb.set_trace()  # 断点
    
    browser_path = self._find_installed_browser_path()
    self.logger.debug(f'🔍 [DEBUG] Browser path: {browser_path}')
    
    debug_port = self._find_free_port()
    self.logger.debug(f'🔍 [DEBUG] Debug port: {debug_port}')
    
    # ... 启动浏览器
    
    # 检查进程
    import psutil
    process = psutil.Process(subprocess.pid)
    self.logger.debug(f'🔍 [DEBUG] Browser PID: {process.pid}')
    self.logger.debug(f'🔍 [DEBUG] Browser status: {process.status()}')
```

## 🚀 快速调试命令

```bash
# 运行测试并进入调试器
pytest backend/core/agent/tools/tests/test_browser_tool.py::TestBrowserTool::test_execute_simple_task -v -s --pdb

# 运行测试并显示详细日志
pytest backend/core/agent/tools/tests/test_browser_tool.py -v -s --log-cli-level=DEBUG

# 运行特定测试并捕获输出
pytest backend/core/agent/tools/tests/test_browser_cdp_diagnosis.py::TestBrowserCDPDiagnosis::test_manual_cdp_connection -v -s
```

## 📚 相关文档

- [Browser CDP 测试和修复指南](BROWSER_CDP_TESTING_AND_FIXING.md)
- [如何测试 Tools](how-to-test-tools.md)
- [测试快速开始](TESTING_QUICK_START.md)

## 💡 提示

1. **修改源码后**: 若使用 `pip install -e <clone>` 从本地安装，修改后立即生效；否则需改 site-packages 或重新安装
2. **使用 justMyCode: false**: 在 IDE 调试配置中设置 `justMyCode: false` 以允许调试外部库
3. **查看日志**: 使用 `--log-cli-level=DEBUG` 查看详细日志
4. **检查进程**: 在调试过程中检查浏览器进程状态
5. **验证 CDP 端点**: 手动测试 CDP 端点是否可访问

---

**最后更新**: 2026-01-20  
**维护者**: 项目团队




