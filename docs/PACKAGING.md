# 打包发布方案

本文档说明如何为 Hou CLI 创建跨平台的打包发布版本。

## 支持的平台

- **Windows** (Windows 10+)
- **Linux** (Ubuntu 20.04+)
- **macOS** (macOS 10.15+)

## 打包方式

### 方式 1: 可执行文件（推荐）

使用 PyInstaller 将 Python 应用打包成独立的可执行文件，用户无需安装 Python。

#### Windows

```bash
# 使用批处理脚本（推荐）
build\build-windows.bat

# 或手动运行
python build\build.py --type exe
```

输出: `dist\hou-cli.exe`

#### Linux

```bash
# 使用 Shell 脚本（推荐）
chmod +x build/build-linux.sh
./build/build-linux.sh

# 或手动运行
python3 build/build.py --type exe
```

输出: `dist/hou-cli`

#### macOS

```bash
# 使用 Shell 脚本（推荐）
chmod +x build/build-macos.sh
./build/build-macos.sh

# 或手动运行
python3 build/build.py --type exe
```

输出: `dist/hou-cli`

### 方式 2: Python Wheel 包

适用于已安装 Python 的用户。

```bash
python build/build.py --type wheel
```

输出: `dist/hou-cli-*.whl`

安装:
```bash
pip install dist/hou-cli-*.whl
```

### 方式 3: 源码分发包

适用于开发者或需要从源码安装的用户。

```bash
python build/build.py --type sdist
```

输出: `dist/hou-cli-*.tar.gz`

安装:
```bash
pip install dist/hou-cli-*.tar.gz
```

## 打包前准备

### 1. 安装依赖

```bash
# 激活虚拟环境
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 安装打包依赖
pip install pyinstaller build setuptools wheel
```

### 2. 检查项目配置

确保以下文件存在且配置正确：
- `pyproject.toml` - 项目元数据
- `requirements.txt` - 生产依赖
- `build/hou-cli.spec` - PyInstaller 配置

### 3. 清理旧构建（可选）

```bash
python build/build.py --type exe --no-clean  # 保留旧构建
```

## 打包流程详解

### PyInstaller 打包流程

1. **分析依赖**: PyInstaller 分析代码，找出所有依赖
2. **收集文件**: 收集 Python 文件、数据文件、二进制文件
3. **打包**: 将所有文件打包成单个可执行文件
4. **压缩**: 使用 UPX 压缩（如果可用）

### 自定义打包配置

编辑 `build/hou-cli.spec` 文件可以自定义打包行为：

- **添加数据文件**: 在 `datas` 列表中添加
- **添加隐藏导入**: 在 `hiddenimports` 列表中添加
- **排除模块**: 在 `excludes` 列表中添加
- **UPX 压缩**: 设置 `upx=True`（需要安装 UPX）

## 发布包结构

打包完成后，会在 `dist/` 目录下创建发布包：

```
dist/
├── hou-cli.exe              # Windows 可执行文件
├── hou-cli                  # Linux/macOS 可执行文件
├── hou-cli-*.whl           # Python Wheel 包
├── hou-cli-*.tar.gz        # 源码分发包
└── hou-cli-{platform}-release/  # 发布包目录
    ├── hou-cli(.exe)       # 可执行文件
    ├── README.md           # 说明文档
    ├── LICENSE             # 许可证
    ├── env.example         # 配置示例
    └── INSTALL.md          # 安装指南
```

## 测试打包结果

### 基本测试

```bash
# Windows
dist\hou-cli.exe --help

# Linux/macOS
./dist/hou-cli --help
```

### 功能测试

```bash
# 测试聊天功能
./dist/hou-cli chat "Hello"

# 测试后端启动
./dist/hou-cli start
```

## 创建发布版本

### 1. 创建压缩包

**Windows:**
```powershell
Compress-Archive -Path dist\hou-cli-windows-release\* -DestinationPath dist\hou-cli-windows-amd64.zip
```

**Linux:**
```bash
cd dist/hou-cli-linux-release
tar -czf ../hou-cli-linux-amd64.tar.gz *
```

**macOS:**
```bash
cd dist/hou-cli-macos-release
tar -czf ../hou-cli-macos-universal.tar.gz *
```

### 2. 计算校验和

```bash
# SHA256
sha256sum dist/hou-cli-*.tar.gz
sha256sum dist/hou-cli-*.zip

# MD5 (可选)
md5sum dist/hou-cli-*.tar.gz
```

### 3. 创建发布说明

创建 `RELEASE_NOTES.md`:

```markdown
# Hou CLI v0.1.0 发布说明

## 下载

- Windows: [hou-cli-windows-amd64.zip](...)
- Linux: [hou-cli-linux-amd64.tar.gz](...)
- macOS: [hou-cli-macos-universal.tar.gz](...)

## 安装

详见各平台的 `INSTALL.md` 文件。

## 变更日志

- 初始发布
- 支持 Windows、Linux、macOS
```

## 常见问题

### 1. 打包体积过大

**原因**: 包含了很多不必要的依赖

**解决**:
- 在 `hou-cli.spec` 的 `excludes` 中添加不需要的模块
- 使用 UPX 压缩（需要安装 UPX）
- 检查是否有重复的依赖

### 2. 运行时缺少模块

**原因**: PyInstaller 未检测到某些动态导入的模块

**解决**:
- 在 `hou-cli.spec` 的 `hiddenimports` 中添加缺失的模块
- 使用 `--collect-all` 选项收集整个包

### 3. 浏览器功能无法使用

**原因**: Playwright 浏览器未安装

**解决**:
- 在安装说明中提示用户安装 Playwright
- 或创建安装脚本自动安装浏览器

### 4. macOS 代码签名

**问题**: macOS 可能阻止未签名的应用运行

**解决**:
```bash
# 使用开发者证书签名
codesign -s "Developer ID Application: Your Name" dist/hou-cli

# 验证签名
codesign -v dist/hou-cli
```

### 5. Linux 依赖问题

**问题**: 某些 Linux 发行版缺少系统库

**解决**:
- 使用 AppImage 格式（需要额外配置）
- 或提供 `.deb` / `.rpm` 包（需要系统依赖）

## 自动化发布（CI/CD）

### GitHub Actions 示例

创建 `.github/workflows/release.yml`:

```yaml
name: Build and Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [windows-latest, ubuntu-20.04, macos-latest]
    
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pyinstaller build
      
      - name: Build
        run: |
          python build/build.py --type exe
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: hou-cli-${{ matrix.os }}
          path: dist/
```

## 版本管理

### 更新版本号

1. 编辑 `pyproject.toml`:
```toml
[project]
version = "0.1.1"
```

2. 重新打包:
```bash
python build/build.py --type all
```

### 发布标签

```bash
# 创建 Git 标签
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

## 参考资源

- [PyInstaller 文档](https://pyinstaller.org/)
- [Python Packaging 指南](https://packaging.python.org/)
- [UPX 压缩工具](https://upx.github.io/)

