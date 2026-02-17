# IPC 通信和打包方案

## 概述

本文档说明系统的 IPC（进程间通信）实现和跨平台打包方案。系统使用 IPC 作为前后端通信方式，支持 Windows、Mac、Linux 三个平台，并可打包成安装程序。

## IPC 通信方案

### 选择：TCP Localhost

考虑到跨平台性和打包需求，**推荐使用 TCP localhost** 作为 IPC 方案。

**优点**：
- ✅ 跨平台兼容性最好（Windows、Mac、Linux）
- ✅ 实现简单，易于维护
- ✅ 支持流式输出
- ✅ 易于调试和测试
- ✅ 打包后稳定可靠
- ✅ 无需额外的 IPC 库依赖

### 实现方案

#### 后端 IPC 服务器

```python
# backend/ipc/server.py
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from backend.agent.orchestrator import Orchestrator
from shared.platform_utils import save_port
import socket

app = FastAPI()
orchestrator = Orchestrator()

@app.post("/api/chat")
async def chat(request: dict):
    """处理聊天请求"""
    try:
        response = await orchestrator.process(request["message"])
        return JSONResponse({"response": response, "status": "success"})
    except Exception as e:
        return JSONResponse(
            {"response": None, "status": "error", "error": str(e)},
            status_code=500
        )

@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}

def find_free_port() -> int:
    """查找可用端口"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

def main():
    """启动 IPC 服务器"""
    # 查找可用端口
    port = find_free_port()
    
    # 保存端口号（供前端读取）
    save_port(port)
    
    # 启动服务器（仅监听 localhost）
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main()
```

#### 前端 IPC 客户端

```python
# frontend/ipc/client.py
import httpx
from pathlib import Path
import platform
import time

class IPCClient:
    """跨平台 IPC 客户端"""
    
    def __init__(self, max_retries: int = 5, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.port = None
        self.base_url = None
        self.client = None
        self._connect()
    
    def _get_port_file(self) -> Path:
        """获取端口文件路径（跨平台）"""
        if platform.system() == "Windows":
            base = Path.home() / "AppData" / "Local" / "hou-cli"
        elif platform.system() == "Darwin":  # macOS
            base = Path.home() / "Library" / "Application Support" / "hou-cli"
        else:  # Linux
            base = Path.home() / ".local" / "share" / "hou-cli"
        
        base.mkdir(parents=True, exist_ok=True)
        return base / "port.txt"
    
    def _load_port(self) -> int:
        """加载端口号"""
        port_file = self._get_port_file()
        
        # 重试读取端口文件
        for _ in range(self.max_retries):
            if port_file.exists():
                try:
                    port = int(port_file.read_text().strip())
                    return port
                except (ValueError, FileNotFoundError):
                    pass
            time.sleep(self.retry_delay)
        
        raise ConnectionError("无法连接到后端服务：端口文件不存在")
    
    def _connect(self):
        """连接到后端服务"""
        self.port = self._load_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.client = httpx.Client(timeout=30.0)
        
        # 验证连接
        if not self.health_check():
            raise ConnectionError(f"无法连接到后端服务：{self.base_url}")
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            response = self.client.get(f"{self.base_url}/health", timeout=5.0)
            return response.status_code == 200
        except:
            return False
    
    async def send(self, message: str) -> str:
        """发送消息"""
        try:
            response = self.client.post(
                f"{self.base_url}/api/chat",
                json={"message": message},
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            
            if result["status"] == "success":
                return result["response"]
            else:
                raise Exception(result.get("error", "未知错误"))
        
        except httpx.RequestError as e:
            raise ConnectionError(f"连接错误：{str(e)}")
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP 错误：{e.response.status_code}")
    
    def close(self):
        """关闭客户端"""
        if self.client:
            self.client.close()
```

#### 平台工具函数

```python
# shared/platform_utils.py
import platform
from pathlib import Path
from typing import Path as PathType

def get_app_data_dir() -> PathType:
    """获取应用数据目录（跨平台）"""
    system = platform.system()
    
    if system == "Windows":
        return Path.home() / "AppData" / "Local" / "hou-cli"
    elif system == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "hou-cli"
    else:  # Linux
        return Path.home() / ".local" / "share" / "hou-cli"

def get_port_file() -> PathType:
    """获取端口文件路径"""
    data_dir = get_app_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "port.txt"

def save_port(port: int):
    """保存端口号"""
    port_file = get_port_file()
    port_file.write_text(str(port))

def load_port() -> int:
    """加载端口号"""
    port_file = get_port_file()
    if port_file.exists():
        return int(port_file.read_text().strip())
    return 8000  # 默认端口

def get_config_file() -> PathType:
    """获取配置文件路径"""
    data_dir = get_app_data_dir()
    return data_dir / "config.yaml"

def get_log_file() -> PathType:
    """获取日志文件路径"""
    data_dir = get_app_data_dir()
    return data_dir / "logs" / "hou-cli.log"
```

## 打包方案

### 方案 1：PyInstaller（推荐）

**优点**：
- ✅ 跨平台支持（Windows、Mac、Linux）
- ✅ 打包成单个可执行文件
- ✅ 自动处理依赖
- ✅ 支持图标和版本信息

#### 安装

```bash
pip install pyinstaller
```

#### 打包配置

**build.spec**（PyInstaller 配置文件）：

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 前端应用
frontend = Analysis(
    ['frontend/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('workflows', 'workflows'),  # 包含工作流文件
        ('shared', 'shared'),
    ],
    hiddenimports=[
        'rich',
        'httpx',
        'fastapi',
        'uvicorn',
        'pydantic',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 后端服务
backend = Analysis(
    ['backend/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('workflows', 'workflows'),
        ('shared', 'shared'),
    ],
    hiddenimports=[
        'fastapi',
        'uvicorn',
        'langchain',
        'openai',
        'langchain_ollama',
        'langchain_community',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 打包成可执行文件
frontend_exe = EXE(
    frontend,
    name='hou-cli',
    icon='assets/icon.ico' if platform.system() == 'Windows' else 'assets/icon.icns',
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

backend_exe = EXE(
    backend,
    name='hou-cli-server',
    icon='assets/icon.ico' if platform.system() == 'Windows' else 'assets/icon.icns',
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

#### 打包脚本

**build.py**（跨平台打包脚本）：

```python
#!/usr/bin/env python3
"""跨平台打包脚本"""
import subprocess
import sys
import platform
import shutil
from pathlib import Path

def clean():
    """清理构建目录"""
    dirs = ['build', 'dist', '__pycache__']
    for d in dirs:
        if Path(d).exists():
            shutil.rmtree(d)
    
    # 清理 .spec 文件
    for spec in Path('.').glob('*.spec'):
        spec.unlink()

def build_windows():
    """Windows 打包"""
    print("Building for Windows...")
    
    # 前端
    subprocess.run([
        'pyinstaller',
        '--onefile',
        '--name', 'hou-cli',
        '--icon', 'assets/icon.ico',
        '--add-data', 'workflows;workflows',
        '--add-data', 'shared;shared',
        '--hidden-import', 'rich',
        '--hidden-import', 'httpx',
        'frontend/main.py'
    ], check=True)
    
    # 后端
    subprocess.run([
        'pyinstaller',
        '--onefile',
        '--name', 'hou-cli-server',
        '--icon', 'assets/icon.ico',
        '--add-data', 'workflows;workflows',
        '--add-data', 'shared;shared',
        '--hidden-import', 'fastapi',
        '--hidden-import', 'uvicorn',
        'backend/main.py'
    ], check=True)

def build_macos():
    """macOS 打包"""
    print("Building for macOS...")
    
    # 前端
    subprocess.run([
        'pyinstaller',
        '--onefile',
        '--name', 'hou-cli',
        '--icon', 'assets/icon.icns',
        '--add-data', 'workflows:workflows',
        '--add-data', 'shared:shared',
        'frontend/main.py'
    ], check=True)
    
    # 后端
    subprocess.run([
        'pyinstaller',
        '--onefile',
        '--name', 'hou-cli-server',
        '--icon', 'assets/icon.icns',
        '--add-data', 'workflows:workflows',
        '--add-data', 'shared:shared',
        'backend/main.py'
    ], check=True)

def build_linux():
    """Linux 打包"""
    print("Building for Linux...")
    
    # 前端
    subprocess.run([
        'pyinstaller',
        '--onefile',
        '--name', 'hou-cli',
        '--add-data', 'workflows:workflows',
        '--add-data', 'shared:shared',
        'frontend/main.py'
    ], check=True)
    
    # 后端
    subprocess.run([
        'pyinstaller',
        '--onefile',
        '--name', 'hou-cli-server',
        '--add-data', 'workflows:workflows',
        '--add-data', 'shared:shared',
        'backend/main.py'
    ], check=True)

def main():
    """主函数"""
    system = platform.system()
    
    clean()
    
    if system == "Windows":
        build_windows()
    elif system == "Darwin":
        build_macos()
    elif system == "Linux":
        build_linux()
    else:
        print(f"Unsupported platform: {system}")
        sys.exit(1)
    
    print("Build completed!")

if __name__ == "__main__":
    main()
```

**build.sh**（Shell 脚本）：

```bash
#!/bin/bash
# 跨平台打包脚本

set -e

# 清理
echo "Cleaning..."
rm -rf build dist __pycache__ *.spec

# 根据平台打包
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo "Building for Windows..."
    pyinstaller --onefile --name hou-cli --icon assets/icon.ico frontend/main.py
    pyinstaller --onefile --name hou-cli-server --icon assets/icon.ico backend/main.py
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Building for macOS..."
    pyinstaller --onefile --name hou-cli --icon assets/icon.icns frontend/main.py
    pyinstaller --onefile --name hou-cli-server --icon assets/icon.icns backend/main.py
else
    echo "Building for Linux..."
    pyinstaller --onefile --name hou-cli frontend/main.py
    pyinstaller --onefile --name hou-cli-server backend/main.py
fi

echo "Build completed!"
```

### 方案 2：创建安装程序

#### Windows - Inno Setup

**setup.iss**：

```inno
[Setup]
AppName=Hou CLI
AppVersion=1.0.0
AppPublisher=Your Company
DefaultDirName={pf}\HouCLI
DefaultGroupName=Hou CLI
OutputDir=installer
OutputBaseFilename=hou-cli-setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin

[Files]
Source: "dist\hou-cli.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\hou-cli-server.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "workflows\*"; DestDir: "{app}\workflows"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Hou CLI"; Filename: "{app}\hou-cli.exe"
Name: "{commondesktop}\Hou CLI"; Filename: "{app}\hou-cli.exe"
Name: "{group}\Uninstall"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\hou-cli.exe"; Description: "Launch Hou CLI"; Flags: nowait postinstall skipifsilent
```

#### macOS - create-dmg

```bash
# 安装 create-dmg
npm install -g create-dmg

# 创建 DMG
create-dmg \
  --volname "Hou CLI" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "Hou CLI.app" 200 190 \
  --hide-extension "Hou CLI.app" \
  --app-drop-link 600 185 \
  "dist/hou-cli.dmg" \
  "dist/Hou CLI.app"
```

#### Linux - AppImage

```bash
# 创建 AppDir 结构
mkdir -p dist/hou-cli.AppDir/usr/bin
mkdir -p dist/hou-cli.AppDir/usr/share/applications
mkdir -p dist/hou-cli.AppDir/usr/share/icons

# 复制文件
cp dist/hou-cli dist/hou-cli.AppDir/usr/bin/
cp dist/hou-cli-server dist/hou-cli.AppDir/usr/bin/
cp assets/icon.png dist/hou-cli.AppDir/usr/share/icons/

# 创建 .desktop 文件
cat > dist/hou-cli.AppDir/hou-cli.desktop << EOF
[Desktop Entry]
Name=Hou CLI
Exec=hou-cli
Icon=icon
Type=Application
Categories=Utility;
EOF

# 使用 appimagetool 打包
wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool-x86_64.AppImage
./appimagetool-x86_64.AppImage dist/hou-cli.AppDir dist/hou-cli.AppImage
```

### 统一启动入口

```python
# cli.py - 统一启动入口
import subprocess
import sys
import os
import time
from pathlib import Path

def get_executable_path(name: str) -> Path:
    """获取可执行文件路径（跨平台）"""
    if getattr(sys, 'frozen', False):
        # 打包后的路径
        base_dir = Path(sys.executable).parent
    else:
        # 开发环境
        base_dir = Path(__file__).parent
    
    if sys.platform == "win32":
        return base_dir / f"{name}.exe"
    else:
        return base_dir / name

def main():
    """主入口"""
    backend_exe = get_executable_path("hou-cli-server")
    frontend_exe = get_executable_path("hou-cli")
    
    # 检查文件是否存在
    if not backend_exe.exists():
        print(f"错误：找不到后端可执行文件 {backend_exe}")
        sys.exit(1)
    
    if not frontend_exe.exists():
        print(f"错误：找不到前端可执行文件 {frontend_exe}")
        sys.exit(1)
    
    # 启动后端
    print("启动后端服务...")
    backend_process = subprocess.Popen(
        [str(backend_exe)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # 等待后端启动
    time.sleep(2)
    
    # 检查后端是否还在运行
    if backend_process.poll() is not None:
        stdout, stderr = backend_process.communicate()
        print(f"后端启动失败：{stderr.decode()}")
        sys.exit(1)
    
    # 启动前端
    print("启动前端界面...")
    try:
        frontend_process = subprocess.Popen([str(frontend_exe)])
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\n正在关闭...")
    finally:
        # 清理后端
        backend_process.terminate()
        backend_process.wait()
        print("已关闭")

if __name__ == "__main__":
    main()
```

## 目录结构（打包后）

```
hou-cli/
├── hou-cli              # 前端可执行文件（Linux/Mac）
├── hou-cli.exe          # 前端可执行文件（Windows）
├── hou-cli-server        # 后端可执行文件（Linux/Mac）
├── hou-cli-server.exe    # 后端可执行文件（Windows）
├── workflows/            # SOP 流程定义文件
│   ├── pdf_analysis_sop.yaml
│   └── ...
└── README.txt            # 使用说明
```

## 依赖管理

**requirements.txt**：

```txt
# 核心依赖
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
rich>=13.7.0
httpx>=0.25.0
pydantic>=2.0.0

# LLM 相关
openai>=1.0.0
langchain>=0.1.0
langchain-ollama>=0.1.0
langchain-community>=0.0.20

# 打包工具（开发依赖）
pyinstaller>=6.0.0
```

**requirements.txt**：

```txt
-r requirements.txt
pytest>=7.0.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.0.0
```

## 跨平台注意事项

1. **路径分隔符**：始终使用 `pathlib.Path` 而不是字符串拼接
2. **权限管理**：Linux/Mac 需要确保可执行文件有执行权限
3. **配置文件位置**：不同平台使用不同的应用数据目录
4. **端口管理**：使用文件存储端口，避免端口冲突
5. **日志文件**：使用平台特定的日志目录
6. **环境变量**：注意不同平台的环境变量差异

## 测试

### 本地测试

```bash
# 启动后端
python -m backend.main

# 启动前端（另一个终端）
python -m frontend.main
```

### 打包后测试

```bash
# 打包
python build.py

# 测试可执行文件
./dist/hou-cli-server
./dist/hou-cli
```

## 总结

- ✅ **IPC 通信**：使用 TCP localhost，跨平台兼容
- ✅ **打包工具**：PyInstaller 支持三个平台
- ✅ **安装程序**：Windows (Inno Setup)、macOS (DMG)、Linux (AppImage)
- ✅ **统一入口**：提供统一的启动脚本
- ✅ **配置管理**：跨平台的配置和端口管理

这种方案确保了系统可以在 Windows、Mac、Linux 三个平台上稳定运行，并且可以打包成易于分发的安装程序。

