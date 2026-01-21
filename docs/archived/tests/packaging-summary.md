# 打包发布方案总结

## 概述

本项目已配置完整的跨平台打包发布方案，支持：
- ✅ Windows (Windows 10+)
- ✅ Linux (Ubuntu 20.04+)
- ✅ macOS (macOS 10.15+)

## 文件结构

```
hou-cli/
├── build/                          # 打包相关文件
│   ├── hou-cli.spec               # PyInstaller 配置
│   ├── build.py                   # 跨平台打包脚本
│   ├── build-windows.bat          # Windows 打包脚本
│   ├── build-linux.sh             # Linux 打包脚本
│   ├── build-macos.sh             # macOS 打包脚本
│   └── README.md                  # 构建说明
├── .github/
│   └── workflows/
│       └── release.yml            # CI/CD 自动发布配置
├── docs/
│   ├── PACKAGING.md               # 详细打包文档
│   ├── packaging-quickstart.md    # 快速开始指南
│   └── packaging-summary.md       # 本文档
└── RELEASE.md                     # 发布指南
```

## 快速开始

### 方式 1: 使用平台脚本（推荐）

**Windows:**
```cmd
build\build-windows.bat
```

**Linux:**
```bash
chmod +x build/build-linux.sh
./build/build-linux.sh
```

**macOS:**
```bash
chmod +x build/build-macos.sh
./build/build-macos.sh
```

### 方式 2: 使用 Python 脚本

```bash
# 安装依赖
pip install pyinstaller build setuptools wheel

# 打包可执行文件
python build/build.py --type exe

# 打包所有类型
python build/build.py --type all
```

## 打包类型

1. **可执行文件** (`--type exe`)
   - 使用 PyInstaller 打包
   - 用户无需安装 Python
   - 输出: `dist/hou-cli` 或 `dist/hou-cli.exe`

2. **Python Wheel** (`--type wheel`)
   - 标准 Python 包格式
   - 适用于已安装 Python 的用户
   - 输出: `dist/hou-cli-*.whl`

3. **源码分发包** (`--type sdist`)
   - 源码压缩包
   - 适用于开发者
   - 输出: `dist/hou-cli-*.tar.gz`

## 自动化发布

### GitHub Actions CI/CD

当推送 Git 标签（格式: `v*`）时，会自动：
1. 在三个平台构建可执行文件
2. 构建 Python 包
3. 创建 GitHub Release
4. 上传所有发布包

**使用方法:**
```bash
# 1. 更新版本号
# 编辑 pyproject.toml: version = "0.1.1"

# 2. 提交并推送
git add pyproject.toml
git commit -m "Bump version to 0.1.1"
git push

# 3. 创建标签（触发 CI/CD）
git tag -a v0.1.1 -m "Release v0.1.1"
git push origin v0.1.1
```

## 输出文件

打包完成后，`dist/` 目录结构：

```
dist/
├── hou-cli(.exe)                  # 可执行文件
├── hou-cli-*.whl                  # Wheel 包
├── hou-cli-*.tar.gz               # 源码包
└── hou-cli-{platform}-release/    # 发布包目录
    ├── hou-cli(.exe)              # 可执行文件
    ├── README.md                  # 说明文档
    ├── LICENSE                    # 许可证
    ├── env.example                # 配置示例
    └── INSTALL.md                 # 安装指南
```

## 自定义配置

### 修改打包配置

编辑 `build/hou-cli.spec`:
- `datas`: 添加数据文件
- `hiddenimports`: 添加隐藏导入
- `excludes`: 排除不需要的模块

### 修改 CI/CD

编辑 `.github/workflows/release.yml`:
- 修改构建矩阵
- 添加测试步骤
- 自定义发布流程

## 测试

### 本地测试

```bash
# 测试可执行文件
./dist/hou-cli --help
./dist/hou-cli chat "Hello"

# 测试 Python 包
pip install dist/hou-cli-*.whl
hou-cli --help
```

### 跨平台测试

建议在以下环境测试：
- Windows 10/11
- Ubuntu 20.04/22.04
- macOS 11/12/13

## 常见问题

### 1. 打包体积过大

**解决**: 
- 检查 `hou-cli.spec` 中的 `excludes` 列表
- 使用 UPX 压缩（需要安装 UPX）
- 排除开发依赖

### 2. 运行时缺少模块

**解决**:
- 在 `hou-cli.spec` 的 `hiddenimports` 中添加缺失模块
- 使用 `--collect-all` 选项

### 3. 浏览器功能无法使用

**解决**:
- 提示用户安装 Playwright: `playwright install chromium`
- 或在安装脚本中自动安装

### 4. macOS 代码签名

**解决**:
```bash
codesign -s "Developer ID Application: Your Name" dist/hou-cli
```

## 下一步

1. **测试打包**: 在目标平台上测试打包结果
2. **配置 CI/CD**: 设置 GitHub Actions secrets（如需要）
3. **创建 Release**: 按照 [RELEASE.md](../../RELEASE.md) 创建发布版本
4. **分发**: 上传到 GitHub Releases 或其他平台

## 参考文档

- [详细打包文档](PACKAGING.md)
- [快速开始指南](packaging-quickstart.md)
- [发布指南](../../RELEASE.md)
- [PyInstaller 文档](https://pyinstaller.org/)
- [Python Packaging 指南](https://packaging.python.org/)

## 支持

如有问题，请：
1. 查看 [PACKAGING.md](PACKAGING.md) 中的故障排除部分
2. 检查 GitHub Issues
3. 提交新的 Issue

